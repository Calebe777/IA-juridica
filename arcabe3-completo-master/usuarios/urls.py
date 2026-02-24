from django.urls import path
from . import views

urlpatterns = [
    path('cadastro/', views.cadastro, name='cadastro'),
    path("login/", views.login, name='login'),
    path("logout/", views.logout_view, name='logout'),
    path("clientes/", views.clientes, name='clientes'),
    path("cliente/<int:id>", views.cliente, name='cliente'),



]