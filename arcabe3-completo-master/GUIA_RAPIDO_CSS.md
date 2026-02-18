# Guia rápido: como alterar visual (centralizar, cores, etc.)

Você pode usar um arquivo próprio de CSS (ex.: `staticfiles/css/custom_overrides.css`) para fazer ajustes visuais sem mexer na lógica do Django.

## 1) Como ativar seu CSS no projeto

No `templates/base.html`, adicione:

```django
{% load static %}
<link rel="stylesheet" href="{% static 'css/custom_overrides.css' %}" />
```

> Dica: coloque o `<link>` antes de `</head>`.

## 2) Exemplos simples

```css
/* Centralizar texto de um título */
h1 {
  text-align: center;
}

/* Mudar cor de botões de submit */
button[type="submit"] {
  background: #7c3aed;
  color: #fff;
}

/* Centralizar conteúdo de tabelas */
table th,
table td {
  text-align: center;
}
```

## 3) Receita rápida para qualquer alteração

1. Abra a página no navegador.
2. Clique com botão direito no elemento > **Inspecionar**.
3. Copie uma classe/estrutura do elemento.
4. Crie a regra no `custom_overrides.css`.
5. Salve e atualize a página (`Ctrl + F5`).

## 4) Exemplo de seletor mais específico

```css
/* Exemplo: só o título principal da tela de clientes */
header h1 {
  color: #1d4ed8;
}
```
