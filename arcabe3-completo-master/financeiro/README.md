# Módulo Financeiro

## Setup
1. `python manage.py migrate`
2. Acesse `/financeiro/` após login.
3. Permissões por usuário são definidas em `FinancialAccess` (`NONE`, `VIEWER`, `FULL`).

## Telas
- `Financeiro > Dashboard`: saldos, receitas x despesas, pagar/receber e projeção.
- `Financeiro > Lançamentos`: receitas/despesas/registro interno, parcelamento e recorrência.
- `Financeiro > Contas`: banco/caixa/cartão/gateway.
- `Financeiro > Categorias`: receita/despesa com grupo DRE e flag “não entra no DRE”.
- `Financeiro > Relatórios`: listagem, DRE e exportação CSV/XLSX.

## Rotas
- `GET /financeiro/`
- `GET|POST /financeiro/lancamentos/`
- `GET|POST /financeiro/contas/`
- `GET|POST /financeiro/categorias/`
- `GET /financeiro/relatorios/`
- `GET /financeiro/exportar/csv/`
- `GET /financeiro/exportar/xlsx/`
- `POST /financeiro/webhook/gateway/`
- `GET /financeiro/recibo/<id>/`

## Regras
- Cliente é ilimitado e não consome ticket.
- Registro interno (`tipo=INTERNO`) não afeta saldo, fluxo e DRE.
- Parcelamento gera `N` lançamentos com competência mensal.
- Recorrência mensal via comando `gerar_recorrencias_financeiras`.

## Integração gateway
- Estrutura para salvar `gateway_external_id`, `gateway_status`, `gateway_url` no lançamento.
- Webhook atualiza status via id externo.
