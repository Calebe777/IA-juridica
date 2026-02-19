from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import OperationalError, ProgrammingError
from django.db.models import Case, DecimalField, Sum, When
from django.http import JsonResponse

from usuarios.models import Cliente

from .models import (
    AdiantamentoCliente,
    AtualizacaoMonetaria,
    DespesaProcessual,
    Honorario,
    LancamentoFinanceiro,
    TimeTrackingFinanceiro,
)
from .permissions import finance_view_required, get_financial_role
from .services import aplicar_indice_monetario, extrato_prestacao_contas, gerar_fatura_reembolso


@login_required(login_url='login')
@finance_view_required
def financeiro_juridico(request):
    role, org = get_financial_role(request.user)

    try:
        if request.method == 'POST' and role == 'FULL':
            acao = request.POST.get('acao')
            if acao == 'honorario':
                Honorario.objects.create(
                    organizacao=org,
                    cliente_id=request.POST['cliente_id'],
                    processo_referencia=request.POST['processo_referencia'],
                    tipo=request.POST['tipo'],
                    descricao=request.POST.get('descricao', ''),
                    valor_contratado=request.POST.get('valor_contratado') or 0,
                    percentual_exito=request.POST.get('percentual_exito') or 0,
                    valor_causa=request.POST.get('valor_causa') or 0,
                    total_parcelas=int(request.POST.get('total_parcelas', 1)),
                    recorrente_mensal=request.POST.get('recorrente_mensal') == 'true',
                    created_by=request.user,
                )
            elif acao == 'adiantamento':
                valor = request.POST.get('valor_total')
                AdiantamentoCliente.objects.create(
                    organizacao=org,
                    cliente_id=request.POST['cliente_id'],
                    processo_referencia=request.POST.get('processo_referencia', ''),
                    valor_total=valor,
                    saldo_disponivel=valor,
                    descricao=request.POST.get('descricao', ''),
                    created_by=request.user,
                )
            elif acao == 'despesa':
                DespesaProcessual.objects.create(
                    organizacao=org,
                    cliente_id=request.POST['cliente_id'],
                    processo_referencia=request.POST['processo_referencia'],
                    categoria=request.POST['categoria'],
                    descricao=request.POST['descricao'],
                    valor=request.POST['valor'],
                    reembolsavel=request.POST.get('reembolsavel') == 'true',
                    created_by=request.user,
                )
            elif acao == 'faturar_reembolso':
                gerar_fatura_reembolso(
                    org,
                    Cliente.objects.get(id=request.POST['cliente_id']),
                    request.POST['processo_referencia'],
                    datetime.strptime(request.POST['vencimento'], '%Y-%m-%d').date(),
                    request.POST.get('incluir_honorarios') == 'true',
                    request.user,
                )
            elif acao == 'atualizacao_monetaria':
                valor_original = request.POST.get('valor_original')
                valor_atualizado, taxa = aplicar_indice_monetario(Decimal(valor_original), request.POST['indice'])
                AtualizacaoMonetaria.objects.create(
                    organizacao=org,
                    cliente_id=request.POST['cliente_id'],
                    processo_referencia=request.POST['processo_referencia'],
                    indice=request.POST['indice'],
                    valor_original=valor_original,
                    valor_atualizado=valor_atualizado,
                    taxa_aplicada=taxa,
                    observacao=request.POST.get('observacao', ''),
                    created_by=request.user,
                )
            elif acao == 'time_tracking':
                TimeTrackingFinanceiro.objects.create(
                    organizacao=org,
                    cliente_id=request.POST['cliente_id'],
                    processo_referencia=request.POST['processo_referencia'],
                    descricao=request.POST['descricao'],
                    horas=request.POST['horas'],
                    valor_hora=request.POST['valor_hora'],
                    created_by=request.user,
                )

        cliente_id = request.GET.get('cliente_id')
        processo_referencia = request.GET.get('processo_referencia', '')
        extrato = {}
        if cliente_id and processo_referencia:
            extrato = extrato_prestacao_contas(org, Cliente.objects.get(id=cliente_id), processo_referencia)

        hoje = date.today()
        futuro = hoje + timedelta(days=90)
        projecao = LancamentoFinanceiro.objects.filter(
            organizacao=org,
            status='PREVISTO',
            vencimento__gte=hoje,
            vencimento__lte=futuro,
        ).values('tipo').annotate(total=Sum('valor'))

        rentabilidade = (
            LancamentoFinanceiro.objects.filter(organizacao=org)
            .values('cliente__nome', 'processo_referencia')
            .annotate(
                receitas=Sum(Case(When(tipo='RECEITA', then='valor'), default=0, output_field=DecimalField())),
                despesas=Sum(Case(When(tipo='DESPESA', then='valor'), default=0, output_field=DecimalField())),
            )
        )

        return JsonResponse({
            'role': role,
            'honorarios': list(Honorario.objects.filter(organizacao=org).values('id', 'cliente__nome', 'tipo', 'processo_referencia', 'status')),
            'adiantamentos': list(AdiantamentoCliente.objects.filter(organizacao=org).values('id', 'cliente__nome', 'processo_referencia', 'valor_total', 'saldo_disponivel')),
            'despesas': list(DespesaProcessual.objects.filter(organizacao=org).values('id', 'cliente__nome', 'processo_referencia', 'categoria', 'valor', 'status_reembolso')),
            'projecao_90_dias': list(projecao),
            'atualizacoes_monetarias': list(AtualizacaoMonetaria.objects.filter(organizacao=org).values('processo_referencia', 'indice', 'valor_original', 'valor_atualizado', 'taxa_aplicada', 'created_at')),
            'time_tracking': list(TimeTrackingFinanceiro.objects.filter(organizacao=org).values('cliente__nome', 'processo_referencia', 'descricao', 'horas', 'valor_hora', 'faturado')),
            'extrato_prestacao_contas': extrato,
            'rentabilidade_por_caso': list(rentabilidade),
        })
    except (OperationalError, ProgrammingError) as exc:
        return JsonResponse({
            'ok': False,
            'role': role,
            'error': 'Estrutura do banco desatualizada para o módulo financeiro jurídico.',
            'detail': str(exc),
            'hint': 'Execute: python manage.py migrate financeiro',
            'honorarios': [],
            'adiantamentos': [],
            'despesas': [],
            'projecao_90_dias': [],
            'atualizacoes_monetarias': [],
            'time_tracking': [],
            'extrato_prestacao_contas': {},
            'rentabilidade_por_caso': [],
        })
