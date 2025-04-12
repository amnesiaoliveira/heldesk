from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Chamado, Atualizacao, Historico
from .forms import ChamadoForm
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User

@login_required
def listar_chamados(request):
    chamados = Chamado.objects.filter(
        Q(usuario=request.user) | Q(responsavel=request.user)
    ).distinct()

    # Filtros
    status = request.GET.get('status', '')
    prioridade = request.GET.get('prioridade', '')
    data_inicio = request.GET.get('data_inicio', '')
    responsavel = request.GET.get('responsavel', '')
    busca = request.GET.get('busca', '')

    if status:
        chamados = chamados.filter(status=status)
    if prioridade:
        chamados = chamados.filter(prioridade=prioridade)
    if data_inicio:
        chamados = chamados.filter(criado_em__gte=data_inicio)
    if responsavel:
        chamados = chamados.filter(responsavel__username__icontains=responsavel)
    if busca:
        chamados = chamados.filter(
            Q(titulo__icontains=busca) | Q(descricao__icontains=busca)
        )

    # Ordenação
    ordenar_por = request.GET.get('ordenar_por', 'criado_em')
    ordenar_direcao = request.GET.get('direcao', 'desc')
    if ordenar_por in ['titulo', 'prioridade', 'status', 'criado_em']:
        if ordenar_direcao == 'desc':
            chamados = chamados.order_by(f'-{ordenar_por}')
        else:
            chamados = chamados.order_by(ordenar_por)

    # Paginação
    paginator = Paginator(chamados, 15)  # Ajustado para 15 por página
    page_number = request.GET.get('page')
    try:
        chamados_paginados = paginator.page(page_number)
    except PageNotAnInteger:
        chamados_paginados = paginator.page(1)
    except EmptyPage:
        chamados_paginados = paginator.page(paginator.num_pages)

    status_choices = Chamado.STATUS
    prioridade_choices = Chamado.PRIORIDADES

    return render(request, 'tickets/listar_chamados.html', {
        'chamados': chamados_paginados,
        'status_choices': status_choices,
        'prioridade_choices': prioridade_choices,
        'status': status,
        'prioridade': prioridade,
        'data_inicio': data_inicio,
        'responsavel': responsavel,
        'busca': busca,
        'ordenar_por': ordenar_por,
        'ordenar_direcao': ordenar_direcao,
    })

@login_required
def criar_chamado(request):
    if request.method == 'POST':
        form = ChamadoForm(request.POST)
        if form.is_valid():
            chamado = form.save(commit=False)
            chamado.usuario = request.user
            chamado.save()
            if chamado.responsavel and chamado.responsavel.email:
                send_mail(
                    subject=f'Novo Chamado Atribuído: {chamado.titulo}',
                    message=f'Olá, {chamado.responsavel.username},\n\nVocê foi atribuído como responsável pelo chamado "{chamado.titulo}".\nDescrição: {chamado.descricao}\n\nAcesse: http://localhost:8000/detalhes/{chamado.id}/',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[chamado.responsavel.email],
                    fail_silently=True,
                )
            return redirect('listar_chamados')
    else:
        form = ChamadoForm()
    return render(request, 'tickets/criar_chamado.html', {'form': form})

@login_required
def editar_chamado(request, id):
    chamado = get_object_or_404(Chamado, Q(id=id) & (Q(usuario=request.user) | Q(responsavel=request.user)))
    
    # Capturar valores antigos antes de qualquer alteração
    status_antigo = chamado.status
    prioridade_antiga = chamado.prioridade
    responsavel_antigo = chamado.responsavel
    
    if request.method == 'POST':
        form = ChamadoForm(request.POST, instance=chamado)
        if form.is_valid():
            chamado = form.save(commit=False)
            chamado.usuario = chamado.usuario  # Mantém o criador original
            chamado.save()

            # Registrar alterações no histórico
            if status_antigo != chamado.status:
                Historico.objects.create(
                    chamado=chamado,
                    campo='status',
                    valor_antigo=status_antigo,
                    valor_novo=chamado.status,
                    alterado_por=request.user
                )
            if prioridade_antiga != chamado.prioridade:
                Historico.objects.create(
                    chamado=chamado,
                    campo='prioridade',
                    valor_antigo=prioridade_antiga,
                    valor_novo=chamado.prioridade,
                    alterado_por=request.user
                )
            if (responsavel_antigo.id if responsavel_antigo else None) != (chamado.responsavel.id if chamado.responsavel else None):
                Historico.objects.create(
                    chamado=chamado,
                    campo='responsavel',
                    valor_antigo=responsavel_antigo.username if responsavel_antigo else None,
                    valor_novo=chamado.responsavel.username if chamado.responsavel else None,
                    alterado_por=request.user
                )

            return redirect('detalhes_chamado', id=chamado.id)
        else:
            # Mantém erros visíveis no template, mas sem print
            pass
    else:
        form = ChamadoForm(instance=chamado)
    usuarios = User.objects.all()
    return render(request, 'tickets/editar_chamado.html', {
        'form': form,
        'usuarios': usuarios,
        'chamado': chamado
    })

@login_required
def deletar_chamado(request, id):
    chamado = get_object_or_404(Chamado, id=id, usuario=request.user) if request.user == Chamado.objects.get(id=id).usuario else get_object_or_404(Chamado, id=id, responsavel=request.user)
    if request.method == 'POST':
        chamado.delete()
        return redirect('listar_chamados')
    return render(request, 'tickets/deletar_chamado.html', {'chamado': chamado})

@login_required
def detalhes_chamado(request, id):
    chamado = get_object_or_404(Chamado, id=id, usuario=request.user) if request.user == Chamado.objects.get(id=id).usuario else get_object_or_404(Chamado, id=id, responsavel=request.user)
    if request.method == 'POST':
        texto = request.POST.get('texto')
        documento = request.FILES.get('documento')
        if texto or documento:
            atualizacao = Atualizacao.objects.create(
                chamado=chamado,
                texto=texto,
                documento=documento,
                autor=request.user
            )
            channel_layer = get_channel_layer()
            documento_url = atualizacao.documento.url if documento else ''
            async_to_sync(channel_layer.group_send)(
                f'chat_{chamado.id}',
                {
                    'type': 'chat_message',
                    'texto': texto or '',
                    'documento_url': documento_url,
                    'autor': request.user.username,
                    'criado_em': atualizacao.criado_em.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_autor': False,
                }
            )
            destinatario = chamado.responsavel if request.user == chamado.usuario else chamado.usuario
            if destinatario and destinatario.email:
                send_mail(
                    subject=f'Nova Atualização no Chamado: {chamado.titulo}',
                    message=f'Olá, {destinatario.username},\n\nUma nova atualização foi adicionada ao chamado "{chamado.titulo}".\nMensagem: {texto or "Documento anexado"}\n\nAcesse: http://localhost:8000/detalhes/{chamado.id}/',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[destinatario.email],
                    fail_silently=True,
                )
    return render(request, 'tickets/detalhes_chamado.html', {
        'chamado': chamado,
        'historico': chamado.historico.all(),
    })

@login_required
def dashboard(request):
    chamados_abertos = Chamado.objects.filter(
        status='ABERTO',
        usuario=request.user
    ) | Chamado.objects.filter(
        status='ABERTO',
        responsavel=request.user
    )
    todos_chamados = Chamado.objects.filter(usuario=request.user) | Chamado.objects.filter(responsavel=request.user)

    # Dados para gráficos
    status_counts = todos_chamados.values('status').annotate(total=Count('id'))
    prioridade_counts = todos_chamados.values('prioridade').annotate(total=Count('id'))

    status_data = {status: 0 for status, _ in Chamado.STATUS}
    prioridade_data = {prioridade: 0 for prioridade, _ in Chamado.PRIORIDADES}

    for item in status_counts:
        status_data[item['status']] = item['total']
    for item in prioridade_counts:
        prioridade_data[item['prioridade']] = item['total']

    total_chamados = todos_chamados.count()
    total_abertos = chamados_abertos.count()

    return render(request, 'tickets/dashboard.html', {
        'chamados_abertos': chamados_abertos.distinct(),
        'status_labels': list(status_data.keys()),
        'status_values': list(status_data.values()),
        'prioridade_labels': list(prioridade_data.keys()),
        'prioridade_values': list(prioridade_data.values()),
        'total_chamados': total_chamados,
        'total_abertos': total_abertos,
    })