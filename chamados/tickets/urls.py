from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('listar/', views.listar_chamados, name='listar_chamados'),
    path('novo/', views.criar_chamado, name='criar_chamado'),
    path('editar/<int:id>/', views.editar_chamado, name='editar_chamado'),
    path('deletar/<int:id>/', views.deletar_chamado, name='deletar_chamado'),
    path('detalhes/<int:id>/', views.detalhes_chamado, name='detalhes_chamado'),
]