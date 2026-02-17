from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models

from usuarios.models import Cliente, Organizacao


class FinancialAccess(models.Model):
    ROLE_NONE = 'NONE'
    ROLE_VIEWER = 'VIEWER'
    ROLE_FULL = 'FULL'
    ROLE_CHOICES = [
        (ROLE_NONE, 'Sem acesso'),
        (ROLE_VIEWER, 'Visualizador'),
        (ROLE_FULL, 'Completo'),
    ]

    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default=ROLE_FULL)

    class Meta:
        unique_together = ('organizacao', 'user')


class ContaFinanceira(models.Model):
    TIPO_CHOICES = [('BANCO', 'Banco'), ('CAIXA', 'Caixa'), ('CARTAO', 'Cartão'), ('GATEWAY', 'Gateway')]
    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    nome = models.CharField(max_length=120)
    tipo = models.CharField(max_length=16, choices=TIPO_CHOICES)
    saldo_inicial = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    ativa = models.BooleanField(default=True)


class CategoriaFinanceira(models.Model):
    TIPO_CHOICES = [('RECEITA', 'Receita'), ('DESPESA', 'Despesa')]
    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    nome = models.CharField(max_length=120)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    grupo_dre = models.CharField(max_length=120, blank=True)
    nao_entrar_dre = models.BooleanField(default=False)


class CentroCusto(models.Model):
    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    nome = models.CharField(max_length=120)


class Unidade(models.Model):
    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    nome = models.CharField(max_length=120)


class LancamentoFinanceiro(models.Model):
    TIPO_CHOICES = [('RECEITA', 'Receita'), ('DESPESA', 'Despesa'), ('TRANSFERENCIA', 'Transferência'), ('INTERNO', 'Registro Interno')]
    STATUS_CHOICES = [('PREVISTO', 'Previsto'), ('PAGO', 'Pago'), ('VENCIDO', 'Vencido'), ('CANCELADO', 'Cancelado')]

    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=16, choices=TIPO_CHOICES)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='PREVISTO')
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    vencimento = models.DateField()
    pagamento = models.DateField(null=True, blank=True)
    competencia = models.CharField(max_length=7, help_text='YYYY-MM')
    descricao = models.CharField(max_length=255)
    categoria = models.ForeignKey(CategoriaFinanceira, on_delete=models.PROTECT, null=True, blank=True)
    conta = models.ForeignKey(ContaFinanceira, on_delete=models.PROTECT, related_name='lancamentos', null=True, blank=True)
    conta_destino = models.ForeignKey(ContaFinanceira, on_delete=models.PROTECT, related_name='transferencias_recebidas', null=True, blank=True)
    centro_custo = models.ForeignKey(CentroCusto, on_delete=models.SET_NULL, null=True, blank=True)
    unidade = models.ForeignKey(Unidade, on_delete=models.SET_NULL, null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    processo_referencia = models.CharField(max_length=120, blank=True)
    anexo = models.FileField(upload_to='financeiro/comprovantes/', null=True, blank=True)
    recorrente = models.BooleanField(default=False)
    origem_recorrencia = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    numero_parcela = models.PositiveIntegerField(default=1)
    total_parcelas = models.PositiveIntegerField(default=1)
    gateway_external_id = models.CharField(max_length=120, blank=True)
    gateway_status = models.CharField(max_length=60, blank=True)
    gateway_url = models.URLField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='lancamentos_criados')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['organizacao', 'status']),
            models.Index(fields=['organizacao', 'vencimento']),
            models.Index(fields=['organizacao', 'competencia']),
        ]


class FinancialAuditLog(models.Model):
    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    lancamento = models.ForeignKey(LancamentoFinanceiro, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    acao = models.CharField(max_length=32)
    detalhes = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
