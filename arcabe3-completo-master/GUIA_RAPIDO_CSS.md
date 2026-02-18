# Guia rápido: como alterar visual (centralizar, cores, etc.)

Este projeto já carrega automaticamente o arquivo:

- `staticfiles/css/custom_overrides.css`

## Exemplos prontos

No arquivo acima já deixei exemplos de:
- centralizar títulos (login/cadastro)
- mudar cor de botão
- centralizar conteúdo da tabela de clientes
- alterar fundo das páginas do financeiro

## Receita rápida para qualquer alteração

1. Abra o template da tela e identifique o `id` principal da página (ex.: `#clientes-page`).
2. No `custom_overrides.css`, crie uma regra com esse seletor.
3. Ajuste propriedades como `text-align`, `background-color`, `color`, `margin`, `padding`.
4. Salve e recarregue no navegador.

## Snippets úteis

```css
/* Centralizar um bloco */
.meu-bloco {
  display: flex;
  justify-content: center;
  align-items: center;
}

/* Trocar cor de texto */
#clientes-header h1 {
  color: #1d4ed8;
}

/* Trocar cor de fundo */
#clientes-page {
  background: #f8fafc;
}
```
