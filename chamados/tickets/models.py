from django.db import models
from django.contrib.auth.models import User

class Chamado(models.Model):
    PRIORIDADES = (
        ('BAIXA', 'Baixa'),
        ('MEDIA', 'Média'),
        ('ALTA', 'Alta'),
    )
    STATUS = (
        ('ABERTO', 'Aberto'),
        ('ANDAMENTO', 'Em Andamento'),
        ('CONCLUIDO', 'Concluído'),
    )
    titulo = models.CharField(max_length=100)
    descricao = models.TextField()
    prioridade = models.CharField(max_length=10, choices=PRIORIDADES, default='MEDIA')
    status = models.CharField(max_length=10, choices=STATUS, default='ABERTO')
    criado_em = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chamados')
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='responsavel_chamados')

    def __str__(self):
        return self.titulo

class Atualizacao(models.Model):
    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name='atualizacoes')
    texto = models.TextField(blank=True, null=True)  # Tornando opcional
    documento = models.FileField(upload_to='documentos/', null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    autor = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Atualização em {self.chamado.titulo} - {self.criado_em}"

class Historico(models.Model):
    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name='historico')
    campo = models.CharField(max_length=50)  # Campo alterado (ex.: 'status', 'prioridade')
    valor_antigo = models.CharField(max_length=255, blank=True, null=True)
    valor_novo = models.CharField(max_length=255, blank=True, null=True)
    alterado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    alterado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.chamado.titulo} - {self.campo}: {self.valor_antigo} -> {self.valor_novo}"