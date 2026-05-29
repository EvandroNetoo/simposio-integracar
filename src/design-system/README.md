# Design System SECOM-ES

Este diretório documenta a base visual usada no frontend Django do Simpósio
IntegraCAR.

## Decisões

- A fonte padrão é Open Sans, aplicada globalmente em `src/static/css/styles.css`.
- A paleta segue as cores oficiais SECOM-ES: Azul, Marsala e Cinzas.
- Os componentes atuais continuam usando classes Tailwind/DaisyUI, mas os
  estilos são normalizados por tokens CSS para manter consistência institucional.
- Formulários usam altura mínima de 35px, foco visível, estado de erro por
  `aria-invalid` e mensagens com `aria-live`.
- O layout autenticado usa navegação lateral, link de pular conteúdo e região
  principal identificada por `main#main-content`.

## Arquivos

- `tokens/secom-es.tokens.json`: fonte estruturada dos tokens.
- `tokens/secom-es.variables.css`: variáveis CSS para consumo direto.
- `tokens/secom-es.scss`: mapas SCSS para projetos com Sass.
- `tokens/tailwind.secom-es.js`: extensão Tailwind reutilizável.

## Manutenção

Novos componentes devem usar os tokens existentes antes de criar valores
visuais novos. Qualquer cor fora da paleta deve ter justificativa de
acessibilidade, estado semântico ou compatibilidade técnica.
