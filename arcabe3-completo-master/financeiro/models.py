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


class Honorario(models.Model):
    TIPO_PRO_LABORE = 'PRO_LABORE'
    TIPO_EXITO = 'EXITO'
    TIPO_SUCUMBENCIA = 'SUCUMBENCIA'
    TIPO_MENSAL = 'MENSAL'
    TIPO_CHOICES = [
        (TIPO_PRO_LABORE, 'Pró-labore'),
        (TIPO_EXITO, 'Êxito (ad exitum)'),
        (TIPO_SUCUMBENCIA, 'Sucumbência'),
        (TIPO_MENSAL, 'Mensal (retainer)'),
    ]
    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('ATIVO', 'Ativo'),
        ('ENCERRADO', 'Encerrado'),
    ]

    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    processo_referencia = models.CharField(max_length=120)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descricao = models.CharField(max_length=255, blank=True)
    valor_contratado = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    percentual_exito = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    valor_causa = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total_parcelas = models.PositiveIntegerField(default=1)
    recorrente_mensal = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='ATIVO')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['organizacao', 'cliente', 'processo_referencia'])]

    @property
    def valor_previsto(self):
        if self.tipo == self.TIPO_EXITO:
            return (self.valor_causa * self.percentual_exito) / Decimal('100')
        return self.valor_contratado


class AdiantamentoCliente(models.Model):
    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    processo_referencia = models.CharField(max_length=120, blank=True)
    valor_total = models.DecimalField(max_digits=14, decimal_places=2)
    saldo_disponivel = models.DecimalField(max_digits=14, decimal_places=2)
    descricao = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class DespesaProcessual(models.Model):
    CATEGORIA_CHOICES = [
        ('TAXA', 'Taxa judicial'),
        ('COPIA', 'Cópias'),
        ('TRANSPORTE', 'Transporte'),
        ('OUTROS', 'Outros'),
    ]
    STATUS_CHOICES = [('PENDENTE', 'Pendente'), ('FATURADA', 'Faturada'), ('REEMBOLSADA', 'Reembolsada')]

    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    processo_referencia = models.CharField(max_length=120)
    categoria = models.CharField(max_length=16, choices=CATEGORIA_CHOICES)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    reembolsavel = models.BooleanField(default=True)
    status_reembolso = models.CharField(max_length=12, choices=STATUS_CHOICES, default='PENDENTE')
    comprovante = models.FileField(upload_to='financeiro/despesas/', null=True, blank=True)
    adiantamento = models.ForeignKey(AdiantamentoCliente, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class MovimentacaoAdiantamento(models.Model):
    TIPO_CHOICES = [('CREDITO', 'Crédito'), ('USO', 'Uso em despesa'), ('ESTORNO', 'Estorno')]

    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    adiantamento = models.ForeignKey(AdiantamentoCliente, on_delete=models.CASCADE, related_name='movimentacoes')
    despesa = models.ForeignKey(DespesaProcessual, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    observacao = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class FaturaFinanceira(models.Model):
    STATUS_CHOICES = [('PENDENTE', 'Pendente'), ('PAGA', 'Paga'), ('ATRASADA', 'Atrasada'), ('CANCELADA', 'Cancelada')]
    MEIO_CHOICES = [('BOLETO', 'Boleto'), ('PIX', 'Pix dinâmico'), ('CARTAO', 'Cartão de crédito')]

    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    processo_referencia = models.CharField(max_length=120, blank=True)
    descricao = models.CharField(max_length=255)
    vencimento = models.DateField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='PENDENTE')
    meio_pagamento = models.CharField(max_length=10, choices=MEIO_CHOICES, default='PIX')
    incluir_honorarios = models.BooleanField(default=False)
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    linha_digitavel = models.CharField(max_length=120, blank=True)
    pix_qr_code = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class FaturaItem(models.Model):
    TIPO_CHOICES = [('HONORARIO', 'Honorário'), ('DESPESA', 'Despesa')]

    fatura = models.ForeignKey(FaturaFinanceira, on_delete=models.CASCADE, related_name='itens')
    tipo = models.CharField(max_length=12, choices=TIPO_CHOICES)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    honorario = models.ForeignKey(Honorario, on_delete=models.SET_NULL, null=True, blank=True)
    despesa = models.ForeignKey(DespesaProcessual, on_delete=models.SET_NULL, null=True, blank=True)


class SplitPagamentoRegra(models.Model):
    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    nome_parceiro = models.CharField(max_length=120)
    percentual = models.DecimalField(max_digits=5, decimal_places=2)
    ativo = models.BooleanField(default=True)


class AtualizacaoMonetaria(models.Model):
    INDICE_CHOICES = [('IPCA', 'IPCA'), ('SELIC', 'SELIC'), ('IGPM', 'IGPM')]

    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    processo_referencia = models.CharField(max_length=120)
    indice = models.CharField(max_length=10, choices=INDICE_CHOICES)
    valor_original = models.DecimalField(max_digits=14, decimal_places=2)
    valor_atualizado = models.DecimalField(max_digits=14, decimal_places=2)
    taxa_aplicada = models.DecimalField(max_digits=8, decimal_places=4)
    observacao = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TimeTrackingFinanceiro(models.Model):
    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    processo_referencia = models.CharField(max_length=120)
    descricao = models.CharField(max_length=255)
    horas = models.DecimalField(max_digits=8, decimal_places=2)
    valor_hora = models.DecimalField(max_digits=10, decimal_places=2)
    faturado = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def valor_total(self):
        return self.horas * self.valor_hora
