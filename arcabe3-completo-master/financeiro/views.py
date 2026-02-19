import csv
from datetime import date, datetime
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from openpyxl import Workbook

from usuarios.models import Cliente, get_or_create_user_organization

from .models import CategoriaFinanceira, ContaFinanceira, LancamentoFinanceiro
from .permissions import finance_full_required, finance_view_required, get_financial_role
from .services import calculate_account_balance, create_installments


@login_required(login_url='login')
@finance_view_required
def dashboard(request):
    role, org = get_financial_role(request.user)
    contas = ContaFinanceira.objects.filter(organizacao=org)
    saldos = [(conta, calculate_account_balance(conta)) for conta in contas]
    today = date.today()
    base = LancamentoFinanceiro.objects.filter(organizacao=org).exclude(tipo='INTERNO')
    mensal = base.filter(vencimento__year=today.year, vencimento__month=today.month)
    receitas = mensal.filter(tipo='RECEITA').aggregate(total=Sum('valor'))['total'] or 0
    despesas = mensal.filter(tipo='DESPESA').aggregate(total=Sum('valor'))['total'] or 0

    monthly_raw = (
        base.filter(vencimento__year=today.year)
        .annotate(mes=TruncMonth('vencimento'))
        .values('mes', 'tipo')
        .annotate(total=Sum('valor'))
        .order_by('mes')
    )
    monthly_index = {m: {'RECEITA': 0, 'DESPESA': 0} for m in range(1, 13)}
    for row in monthly_raw:
        if row['mes']:
            monthly_index[row['mes'].month][row['tipo']] = float(row['total'] or 0)

    monthly_labels = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    monthly_series = [
        {'label': monthly_labels[i - 1], 'receita': monthly_index[i]['RECEITA'], 'despesa': monthly_index[i]['DESPESA']}
        for i in range(1, 13)
    ]
    max_ano = max([item['receita'] for item in monthly_series] + [item['despesa'] for item in monthly_series] + [1])

    top_categorias = list(
        base.filter(tipo='DESPESA')
        .values('categoria__nome')
        .annotate(total=Sum('valor'))
        .order_by('-total')[:5]
    )
    max_categoria = max([float(item['total'] or 0) for item in top_categorias] + [1])

    return render(request, 'financeiro/dashboard.html', {
        'role': role,
        'saldos': saldos,
        'receitas_mes': receitas,
        'despesas_mes': despesas,
        'a_pagar': base.filter(tipo='DESPESA', status='VENCIDO').count(),
        'a_receber': base.filter(tipo='RECEITA', status='VENCIDO').count(),
        'projecao': base.filter(status='PREVISTO').aggregate(total=Sum('valor'))['total'] or 0,
        'monthly_series': monthly_series,
        'max_ano': max_ano,
        'top_categorias': top_categorias,
        'max_categoria': max_categoria,
    })


@login_required(login_url='login')
@finance_view_required
def lancamentos(request):
    role, org = get_financial_role(request.user)
    if request.method == 'POST':
        if role != 'FULL':
            messages.error(request, 'Perfil visualizador não pode criar lançamentos.')
            return redirect('financeiro_lancamentos')
        tipo = request.POST['tipo']
        parcelas = int(request.POST.get('parcelas', 1))
        vencimento = datetime.strptime(request.POST['vencimento'], '%Y-%m-%d').date()
        base_data = {
            'organizacao': org,
            'tipo': tipo,
            'status': request.POST.get('status', 'PREVISTO'),
            'valor': request.POST['valor'],
            'vencimento': vencimento,
            'competencia': f'{vencimento.year}-{vencimento.month:02d}',
            'descricao': request.POST['descricao'],
            'categoria_id': request.POST.get('categoria') or None,
            'conta_id': request.POST.get('conta') or None,
            'centro_custo_id': request.POST.get('centro_custo') or None,
            'unidade_id': request.POST.get('unidade') or None,
            'cliente_id': request.POST.get('cliente') or None,
            'processo_referencia': request.POST.get('processo_referencia', ''),
            'recorrente': request.POST.get('recorrente') == 'on',
        }
        create_installments(base_data, parcelas, request.user)
        messages.success(request, 'Lançamento criado com sucesso.')
        return redirect('financeiro_lancamentos')

    qs = LancamentoFinanceiro.objects.filter(organizacao=org).select_related('conta', 'categoria', 'cliente').order_by('-vencimento')
    return render(request, 'financeiro/lancamentos.html', {
        'role': role,
        'lancamentos': qs[:200],
        'contas': ContaFinanceira.objects.filter(organizacao=org),
        'categorias': CategoriaFinanceira.objects.filter(organizacao=org),
        'clientes': Cliente.objects.filter(organizacao=org),
    })


@login_required(login_url='login')
@finance_view_required
def contas(request):
    role, org = get_financial_role(request.user)
    if request.method == 'POST' and role == 'FULL':
        ContaFinanceira.objects.create(
            organizacao=org,
            nome=request.POST['nome'],
            tipo=request.POST['tipo'],
            saldo_inicial=request.POST.get('saldo_inicial', 0),
        )
    return render(request, 'financeiro/contas.html', {'role': role, 'contas': ContaFinanceira.objects.filter(organizacao=org)})


@login_required(login_url='login')
@finance_view_required
def categorias(request):
    role, org = get_financial_role(request.user)
    if request.method == 'POST' and role == 'FULL':
        CategoriaFinanceira.objects.create(
            organizacao=org,
            nome=request.POST['nome'],
            tipo=request.POST['tipo'],
            grupo_dre=request.POST.get('grupo_dre', ''),
            nao_entrar_dre=request.POST.get('nao_entrar_dre') == 'on',
        )
    return render(request, 'financeiro/categorias.html', {'role': role, 'categorias': CategoriaFinanceira.objects.filter(organizacao=org)})


@login_required(login_url='login')
@finance_view_required
def relatorios(request):
    _, org = get_financial_role(request.user)
    qs = LancamentoFinanceiro.objects.filter(organizacao=org).select_related('categoria', 'conta', 'cliente')
    if request.GET.get('status'):
        qs = qs.filter(status=request.GET['status'])
    dre = qs.exclude(tipo='INTERNO').exclude(categoria__nao_entrar_dre=True).values('categoria__grupo_dre').annotate(total=Sum('valor'))
    return render(request, 'financeiro/relatorios.html', {'lancamentos': qs[:300], 'dre': dre})


@login_required(login_url='login')
@finance_view_required
def exportar(request, formato):
    _, org = get_financial_role(request.user)
    rows = list(LancamentoFinanceiro.objects.filter(organizacao=org).values_list('tipo', 'status', 'valor', 'vencimento', 'descricao'))
    if formato == 'csv':
        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = 'attachment; filename="financeiro.csv"'
        writer = csv.writer(resp)
        writer.writerow(['tipo', 'status', 'valor', 'vencimento', 'descricao'])
        writer.writerows(rows)
        return resp
    wb = Workbook()
    ws = wb.active
    ws.append(['tipo', 'status', 'valor', 'vencimento', 'descricao'])
    for row in rows:
        ws.append(list(row))
    output = BytesIO()
    wb.save(output)
    resp = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = 'attachment; filename="financeiro.xlsx"'
    return resp


@login_required(login_url='login')
@finance_full_required
def gerar_recibo(request, lancamento_id):
    lanc = get_object_or_404(LancamentoFinanceiro, id=lancamento_id)
    content = f"Recibo\nRecebemos de {lanc.cliente.nome if lanc.cliente else 'Pagador'} o valor de R$ {lanc.valor}."
    return HttpResponse(content, content_type='text/plain')


@csrf_exempt
def webhook_gateway(request):
    if request.method == 'POST':
        payload = request.POST
        external_id = payload.get('id')
        status = payload.get('status', '')
        LancamentoFinanceiro.objects.filter(gateway_external_id=external_id).update(gateway_status=status)
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False}, status=400)


@login_required(login_url='login')
@finance_view_required
def financeiro_juridico(request):
    from .juridico_views import financeiro_juridico as juridico_handler

    return juridico_handler(request)
