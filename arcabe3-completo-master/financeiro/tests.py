from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from usuarios.models import Cliente, get_or_create_user_organization

from .models import CategoriaFinanceira, ContaFinanceira, FinancialAccess, LancamentoFinanceiro
from .services import (
    aplicar_indice_monetario,
    calculate_account_balance,
    create_installments,
    gerar_fatura_reembolso,
)


class FinanceiroTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='full', password='123456')
        self.viewer = User.objects.create_user(username='viewer', password='123456')
        self.org = get_or_create_user_organization(self.user)
        self.cliente = Cliente.objects.create(nome='Cliente 1', email='a@a.com', tipo='PF', status=True, user=self.user, organizacao=self.org)
        self.conta = ContaFinanceira.objects.create(organizacao=self.org, nome='Banco 1', tipo='BANCO', saldo_inicial=100)
        self.categoria = CategoriaFinanceira.objects.create(organizacao=self.org, nome='Honorários', tipo='RECEITA', grupo_dre='Operacional')

    def test_parcelamento_gera_parcelas(self):
        base_data = {
            'organizacao': self.org,
            'tipo': 'RECEITA',
            'status': 'PREVISTO',
            'valor': Decimal('100.00'),
            'vencimento': date(2026, 1, 10),
            'competencia': '2026-01',
            'descricao': 'Contrato',
            'categoria': self.categoria,
            'conta': self.conta,
        }
        itens = create_installments(base_data, 3, self.user)
        self.assertEqual(len(itens), 3)
        self.assertEqual(itens[1].numero_parcela, 2)
        self.assertEqual(itens[2].vencimento.month, 3)

    def test_registro_interno_nao_afeta_saldo_e_dre(self):
        LancamentoFinanceiro.objects.create(
            organizacao=self.org, tipo='INTERNO', status='PAGO', valor=200, vencimento=date.today(),
            competencia='2026-02', descricao='Interno', conta=self.conta, categoria=self.categoria, created_by=self.user
        )
        self.assertEqual(calculate_account_balance(self.conta), Decimal('100.00'))

    def test_visualizador_nao_cria(self):
        org_view = get_or_create_user_organization(self.viewer)
        FinancialAccess.objects.create(organizacao=org_view, user=self.viewer, role=FinancialAccess.ROLE_VIEWER)
        self.client.login(username='viewer', password='123456')
        response = self.client.post(reverse('financeiro_lancamentos'), {
            'tipo': 'RECEITA', 'descricao': 'X', 'valor': '10.00', 'vencimento': '2026-02-10'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(LancamentoFinanceiro.objects.filter(organizacao=org_view).count(), 0)

    def test_exportacao_valida(self):
        LancamentoFinanceiro.objects.create(
            organizacao=self.org, tipo='RECEITA', status='PAGO', valor=100, vencimento=date.today(),
            competencia='2026-02', descricao='Export', conta=self.conta, categoria=self.categoria, created_by=self.user
        )
        self.client.login(username='full', password='123456')
        csv_response = self.client.get(reverse('financeiro_exportar', kwargs={'formato': 'csv'}))
        xlsx_response = self.client.get(reverse('financeiro_exportar', kwargs={'formato': 'xlsx'}))
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn('tipo,status,valor', csv_response.content.decode())
        self.assertEqual(xlsx_response.status_code, 200)
        self.assertTrue(xlsx_response.content.startswith(b'PK'))


    def test_aplica_indice_monetario(self):
        atualizado, taxa = aplicar_indice_monetario(Decimal('1000.00'), 'IPCA')
        self.assertEqual(taxa, Decimal('0.0450'))
        self.assertEqual(atualizado, Decimal('1045.00'))

    def test_gera_fatura_reembolso(self):
        from .models import DespesaProcessual

        DespesaProcessual.objects.create(
            organizacao=self.org,
            cliente=self.cliente,
            processo_referencia='0001',
            categoria='TAXA',
            descricao='Custas iniciais',
            valor=Decimal('120.00'),
            created_by=self.user,
        )
        fatura = gerar_fatura_reembolso(
            self.org,
            self.cliente,
            '0001',
            date(2026, 2, 15),
            incluir_honorarios=False,
            user=self.user,
        )
        self.assertEqual(fatura.valor_total, Decimal('120.00'))
        self.assertTrue(fatura.pix_qr_code.startswith('PIX|FATURA'))


    def test_financeiro_juridico_bloqueia_cliente_de_outra_organizacao(self):
        outro_user = User.objects.create_user(username='other', password='123456')
        outra_org = get_or_create_user_organization(outro_user)
        cliente_outro = Cliente.objects.create(
            nome='Cliente 2', email='b@b.com', tipo='PF', status=True, user=outro_user, organizacao=outra_org
        )

        self.client.login(username='full', password='123456')
        response = self.client.post(reverse('financeiro_juridico'), {
            'acao': 'honorario',
            'cliente_id': cliente_outro.id,
            'processo_referencia': 'PROC-99',
            'tipo': 'PRO_LABORE',
            'descricao': 'Tentativa inválida',
            'valor_contratado': '300.00',
        })

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload['ok'])

    def test_financeiro_juridico_calcula_rentabilidade_subtraindo_despesas(self):
        LancamentoFinanceiro.objects.create(
            organizacao=self.org,
            tipo='RECEITA',
            status='PAGO',
            valor=Decimal('500.00'),
            vencimento=date.today(),
            competencia='2026-02',
            descricao='Receita do caso',
            conta=self.conta,
            categoria=self.categoria,
            cliente=self.cliente,
            processo_referencia='PROC-RENT',
            created_by=self.user,
        )
        LancamentoFinanceiro.objects.create(
            organizacao=self.org,
            tipo='DESPESA',
            status='PAGO',
            valor=Decimal('120.00'),
            vencimento=date.today(),
            competencia='2026-02',
            descricao='Despesa do caso',
            conta=self.conta,
            categoria=self.categoria,
            cliente=self.cliente,
            processo_referencia='PROC-RENT',
            created_by=self.user,
        )

        self.client.login(username='full', password='123456')
        response = self.client.get(reverse('financeiro_juridico'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        caso = next(item for item in payload['rentabilidade_por_caso'] if item['processo_referencia'] == 'PROC-RENT')
        self.assertEqual(Decimal(str(caso['rentabilidade'])), Decimal('380.00'))

    def test_endpoint_financeiro_juridico(self):
        self.client.login(username='full', password='123456')
        response = self.client.post(reverse('financeiro_juridico'), {
            'acao': 'honorario',
            'cliente_id': self.cliente.id,
            'processo_referencia': 'PROC-01',
            'tipo': 'PRO_LABORE',
            'descricao': 'Honorário contratual',
            'valor_contratado': '500.00',
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(len(payload['honorarios']) >= 1)
