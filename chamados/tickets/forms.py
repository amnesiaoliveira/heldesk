from django import forms
from .models import Chamado
from django.contrib.auth.models import User

class ChamadoForm(forms.ModelForm):
    responsavel = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label="Nenhum"
    )

    class Meta:
        model = Chamado
        fields = ['titulo', 'descricao', 'prioridade', 'status', 'responsavel']