from django.db import models
from django.contrib.auth.models import User
from martor.models import MartorField


class Organizacao(models.Model):
    nome = models.CharField(max_length=255)
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='organizacao_principal')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome


class Cliente(models.Model):
    TIPO_CHOICES = [
        ('PF', 'Pessoa fisica'),
        ('PJ', 'Pessoa juridica'),
    ]

    nome = models.CharField(max_length=255)
    email = models.EmailField()
    tipo = models.CharField(max_length=2, choices=TIPO_CHOICES, default='PF')
    status = models.BooleanField(default=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.nome


class Documentos(models.Model):
    TIPO_CHOICES = [
        ('C', 'Contrato'),
        ('P', 'Petição'),
        ('CONT', 'Contestação'),
        ('R', 'Recursos'),
        ('O', 'Outro'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=255, choices=TIPO_CHOICES, default='O')
    arquivo = models.FileField(upload_to='documentos/')
    data_upload = models.DateTimeField()
    content = MartorField()

    def __str__(self):
        return self.tipo


def get_or_create_user_organization(user):
    organizacao, _ = Organizacao.objects.get_or_create(
        owner=user,
        defaults={'nome': f'Escritório de {user.username}'},
    )
    return organizacao
