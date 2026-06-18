# Documento de Requisitos - Sistema de Eventos Acadêmicos

## 1. Objetivo do Sistema

Desenvolver um sistema web para gerenciamento de inscrições e submissões de trabalhos em simpósios acadêmicos, permitindo que pesquisadores realizem cadastro, submetam trabalhos, acompanhem avaliações e recebam pareceres emitidos pela comissão avaliadora.

---

# 2. Perfis de Usuário

## 2.1 Pesquisador / Autor

Responsável por:

* Realizar cadastro no sistema;
* Submeter trabalhos;
* Acompanhar avaliações;
* Enviar correções quando solicitado;
* Consultar pareceres e resultados.

## 2.2 Avaliador

Responsável por:

* Visualizar trabalhos atribuídos;
* Avaliar trabalhos;
* Registrar pareceres;
* Emitir recomendações.

## 2.3 Administrador / Comissão Organizadora

Responsável por:

* Configurar o evento;
* Cadastrar avaliadores;
* Distribuir trabalhos;
* Acompanhar avaliações;
* Registrar decisões finais;
* Visualizar resultados.

---

# 3. Requisitos Funcionais

## RF01 - Cadastro de Pesquisador

O sistema deve permitir o cadastro de pesquisadores contendo:

* Nome completo;
* CPF ou documento de identificação;
* E-mail;
* Telefone;
* Instituição de vínculo;
* Tipo de vínculo:

  * Estudante;
  * Professor;
  * Técnico;
  * Pesquisador externo;
  * Outro.
* Titulação ou nível de formação;
* Cidade;
* Estado;
* Senha de acesso;
* Link para Currículo Lattes.

---

## RF02 - Login e Autenticação

O sistema deve permitir autenticação por e-mail e senha.

Funcionalidades mínimas:

* Tela de login;
* Recuperação de senha;
* Controle de acesso por perfil:

  * Pesquisador;
  * Avaliador;
  * Administrador.

---

## RF03 - Cadastro de Evento

O administrador deve poder cadastrar:

* Nome do evento;
* Edição;
* Ano;
* Instituição organizadora;
* Período de submissão;
* Período de avaliação;
* Data de divulgação dos resultados;
* E-mail de contato;
* Regras gerais de submissão.

---

## RF04 - Submissão de Trabalho

O sistema deve permitir o envio de resumos expandidos contendo:

* Título;
* Área temática;
* Resumo;
* Palavras-chave;
* Nome dos autores;
* Instituição dos autores;
* E-mail do autor principal;
* Autor correspondente;
* Arquivo PDF;
* Declaração de autoria;
* Aceite dos termos de submissão.

---

## RF05 - Cadastro de Coautores

O sistema deve permitir cadastrar coautores contendo:

* Nome completo;
* E-mail;
* Instituição;
* Tipo de vínculo;
* Ordem de autoria.

O sistema deve permitir alterar a ordem dos autores enquanto o prazo estiver aberto.

---

## RF06 - Validação da Submissão

O sistema deve validar:

* Campos obrigatórios preenchidos;
* Arquivo anexado;
* Formato permitido;
* Prazo de submissão aberto;
* Aceite dos termos de submissão.

---

## RF07 - Edição da Submissão

O pesquisador poderá editar trabalhos enquanto o período de submissão estiver aberto.

Após o encerramento:

* Alterações somente mediante liberação manual do administrador.

---

## RF08 - Comprovante de Submissão

Após o envio, o sistema deve gerar comprovante contendo:

* Código da submissão;
* Título do trabalho;
* Autor principal;
* Data e horário do envio;
* Situação inicial.

---

## RF09 - Situação do Trabalho

O sistema deve permitir acompanhar as seguintes situações:

* Rascunho;
* Submetido;
* Em avaliação;
* Aprovado;
* Aprovado com correções;
* Reprovado;
* Correção enviada;
* Avaliação finalizada.

---

## RF10 - Cadastro de Avaliadores

O administrador deve cadastrar avaliadores contendo:

* Nome completo;
* E-mail;
* Instituição;
* Titulação;
* Áreas de atuação;
* Eixos temáticos;
* Perfil de acesso.

---

## RF11 - Distribuição de Trabalhos

O administrador deve poder:

* Distribuir trabalhos manualmente;
* Distribuir por área temática;
* Definir quantidade mínima de avaliadores por trabalho.

Para a primeira versão do sistema recomenda-se distribuição manual.

---

## RF12 - Visualização do Trabalho pelo Avaliador

O avaliador deve visualizar:

* Código da submissão;
* Título;
* Área temática;
* Resumo;
* Palavras-chave;
* Arquivo anexado;
* Dados dos autores (quando não houver avaliação cega).

Caso a avaliação seja cega, os dados dos autores devem ser ocultados.

---

## RF13 - Registro de Parecer

O avaliador deve registrar:

* Nota ou conceito;
* Comentários ao autor;
* Comentários internos;
* Recomendação final.

Recomendações possíveis:

* Aceitar;
* Aceitar com correções;
* Rejeitar.

---

## RF14 - Decisão Final da Comissão

O administrador deve registrar uma decisão final:

* Aprovado;
* Aprovado com correções;
* Reprovado.

A decisão pode considerar os pareceres dos avaliadores.

---

## RF15 - Envio de Correções

Quando solicitado, o autor deve poder enviar:

* Arquivo corrigido;
* Observações.

O sistema deve registrar:

* Data de envio;
* Arquivo enviado;
* Observações;
* Situação da nova versão.

---

## RF16 - Notificações por E-mail

O sistema deve enviar notificações automáticas para:

* Confirmação de cadastro;
* Confirmação de submissão;
* Trabalho enviado para avaliação;
* Parecer disponível;
* Solicitação de correção;
* Resultado final;
* Confirmação de envio da versão corrigida.

---

## RF17 - Painel do Pesquisador

O painel deve disponibilizar:

* Dados cadastrais;
* Lista de trabalhos submetidos;
* Situação dos trabalhos;
* Comprovantes de submissão;
* Pareceres recebidos;
* Envio de correções.

---

## RF20 - Painel do Avaliador

O painel deve disponibilizar:

* Trabalhos atribuídos;
* Prazo de avaliação;
* Situação das avaliações;
* Acesso aos arquivos;
* Formulário de parecer;
* Histórico de pareceres enviados.

---

# 4. Modelo de Dados

## 4.1 Pesquisador

| Campo        | Tipo     |
| ------------ | -------- |
| id           | UUID     |
| nomeCompleto | String   |
| cpfDocumento | String   |
| email        | String   |
| telefone     | String   |
| instituicao  | String   |
| tipoVinculo  | Enum     |
| titulacao    | String   |
| cidade       | String   |
| estado       | String   |
| dataCadastro | DateTime |

---

## 4.2 Trabalho

| Campo            | Tipo        |
| ---------------- | ----------- |
| id               | UUID        |
| codigoSubmissao  | String      |
| titulo           | String      |
| areaTematica     | String      |
| resumo           | Text        |
| palavrasChave    | String      |
| autorPrincipal   | Pesquisador |
| coautores        | Lista       |
| arquivoSubmetido | Arquivo     |
| dataSubmissao    | DateTime    |
| situacao         | Enum        |
| versaoAtual      | Integer     |
| resultadoFinal   | Enum        |

---

## 4.3 Avaliação

| Campo               | Tipo      |
| ------------------- | --------- |
| id                  | UUID      |
| trabalho            | Trabalho  |
| avaliador           | Avaliador |
| criterios           | JSON      |
| notas               | JSON      |
| comentariosAutor    | Text      |
| comentariosInternos | Text      |
| recomendacao        | Enum      |
| dataParecer         | DateTime  |

---

## 4.4 Evento

| Campo            | Tipo      |
| ---------------- | --------- |
| id               | UUID      |
| nome             | String    |
| edicao           | String    |
| ano              | Integer   |
| periodoSubmissao | DateRange |
| periodoAvaliacao | DateRange |
| dataResultado    | Date      |
| regrasSubmissao  | Text      |
| eixosTematicos   | Lista     |

---

# 5. Fluxo Básico do Sistema

1. Administrador cadastra o evento;
2. Administrador cadastra avaliadores e áreas temáticas;
3. Pesquisador cria conta;
4. Pesquisador submete trabalho;
5. Sistema confirma a submissão;
6. Administrador distribui trabalhos para avaliadores;
7. Avaliador registra parecer;
8. Sistema disponibiliza avaliação;
9. Comissão registra decisão final;
10. Autor visualiza resultado;
11. Autor envia correções (quando necessário);
12. Comissão finaliza o processo.

---

# 6. Prioridade de Desenvolvimento (MVP)

### Alta Prioridade

* Cadastro de usuários;
* Login e autenticação;
* Cadastro de evento;
* Submissão de trabalhos em PDF;
* Painel do pesquisador;
* Cadastro de avaliadores;
* Distribuição manual de trabalhos;
* Registro de parecer;
* Painel administrativo.

### Média Prioridade

* Recuperação de senha;
* Notificações por e-mail;
* Controle de versões corrigidas;
* Relatórios administrativos.

### Baixa Prioridade

* Distribuição automática de avaliadores;
* Avaliação cega;
* Métricas e dashboards;
* Integrações externas.
