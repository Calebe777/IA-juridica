from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum

from .models import FinancialAuditLog, LancamentoFinanceiro


def _add_months(dt: date, months: int) -> date:
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, monthrange(year, month)[1])
    return date(year, month, day)


def create_installments(base_data: dict, total_parcelas: int, user):
    lancamentos = []
    payload = dict(base_data)
    start_due = payload.pop('vencimento')
    payload.pop('competencia', None)
    for idx in range(total_parcelas):
        venc = _add_months(start_due, idx)
        lanc = LancamentoFinanceiro.objects.create(
            **payload,
            vencimento=venc,
            competencia=f'{venc.year}-{venc.month:02d}',
            numero_parcela=idx + 1,
            total_parcelas=total_parcelas,
            created_by=user,
        )
        FinancialAuditLog.objects.create(
            organizacao=lanc.organizacao,
            lancamento=lanc,
            user=user,
            acao='CRIACAO',
            detalhes=f'Parcela {idx + 1}/{total_parcelas} criada.'
        )
        lancamentos.append(lanc)
    return lancamentos


def create_transfer(organizacao, conta_origem, conta_destino, valor, vencimento, user):
    return LancamentoFinanceiro.objects.create(
        organizacao=organizacao,
        tipo='TRANSFERENCIA',
        status='PAGO',
        valor=valor,
        vencimento=vencimento,
        pagamento=vencimento,
        competencia=f'{vencimento.year}-{vencimento.month:02d}',
        descricao=f'Transferência de {conta_origem.nome} para {conta_destino.nome}',
        conta=conta_origem,
        conta_destino=conta_destino,
        created_by=user,
    )


def calculate_account_balance(conta):
    pagos = LancamentoFinanceiro.objects.filter(
        Q(tipo='RECEITA') | Q(tipo='DESPESA') | Q(tipo='TRANSFERENCIA'),
        conta=conta,
        status='PAGO',
    ).exclude(tipo='INTERNO')

    receitas = pagos.filter(tipo='RECEITA').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    despesas = pagos.filter(tipo='DESPESA').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    transferencias_saida = pagos.filter(tipo='TRANSFERENCIA').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    transferencias_entrada = LancamentoFinanceiro.objects.filter(
        conta_destino=conta,
        tipo='TRANSFERENCIA',
        status='PAGO',
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

    return conta.saldo_inicial + receitas - despesas - transferencias_saida + transferencias_entrada


def generate_recurring(reference_date=None):
    reference_date = reference_date or date.today()
    seeds = LancamentoFinanceiro.objects.filter(recorrente=True, vencimento__day=reference_date.day)
    created = 0
    for seed in seeds:
        next_due = _add_months(seed.vencimento, 1)
        exists = LancamentoFinanceiro.objects.filter(origem_recorrencia=seed, vencimento=next_due).exists()
        if exists:
            continue
        LancamentoFinanceiro.objects.create(
            organizacao=seed.organizacao,
            tipo=seed.tipo,
            status='PREVISTO',
            valor=seed.valor,
            vencimento=next_due,
            competencia=f'{next_due.year}-{next_due.month:02d}',
            descricao=seed.descricao,
            categoria=seed.categoria,
            conta=seed.conta,
            centro_custo=seed.centro_custo,
            unidade=seed.unidade,
            cliente=seed.cliente,
            processo_referencia=seed.processo_referencia,
            recorrente=seed.recorrente,
            origem_recorrencia=seed,
            total_parcelas=1,
            numero_parcela=1,
            created_by=seed.created_by,
        )
        created += 1
    return created
