from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from usuarios.models import Cliente, get_or_create_user_organization

from .models import CategoriaFinanceira, ContaFinanceira, FinancialAccess, LancamentoFinanceiro
from .services import calculate_account_balance, create_installments


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
