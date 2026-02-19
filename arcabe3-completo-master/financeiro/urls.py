from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='financeiro_dashboard'),
    path('lancamentos/', views.lancamentos, name='financeiro_lancamentos'),
    path('contas/', views.contas, name='financeiro_contas'),
    path('categorias/', views.categorias, name='financeiro_categorias'),
    path('relatorios/', views.relatorios, name='financeiro_relatorios'),
    path('exportar/<str:formato>/', views.exportar, name='financeiro_exportar'),
    path('recibo/<int:lancamento_id>/', views.gerar_recibo, name='financeiro_recibo'),
    path('webhook/gateway/', views.webhook_gateway, name='financeiro_webhook_gateway'),
    path('juridico/', views.financeiro_juridico, name='financeiro_juridico'),
]
