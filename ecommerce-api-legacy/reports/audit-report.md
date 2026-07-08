# Audit Report — ecommerce-api-legacy

## Phase 1 — Project Analysis

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js)
Framework:     Express ^4.18.2
Dependencies:  sqlite3 ^5.1.6 (driver direto, sem ORM)
Domain:        LMS (plataforma de cursos) com fluxo de checkout — matrícula e pagamento de cursos
Architecture:  Monolítica — 3 arquivos em src/ (app.js, AppManager.js, utils.js), sem pastas models/controllers/routes; rotas, regra de negócio e acesso a dados concentrados em uma única classe (AppManager)
Source files:  3 files analyzed (src/app.js, src/AppManager.js, src/utils.js)
DB tables:     users, courses, enrollments, payments, audit_logs
================================
```

## Phase 2 — Architecture Audit Report

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js) + Express 4.18.2
Files:   3 analyzed | ~180 lines of code

Summary
CRITICAL: 4 | HIGH: 2 | MEDIUM: 2 | LOW: 2

Findings

[CRITICAL] God Class / God File
File: src/AppManager.js:1-141
Description: A classe `AppManager` concentra, sozinha, três responsabilidades que deveriam estar em camadas separadas: (a) definição de schema e conexão com o banco (`initDb`, linhas 10-23), (b) definição de todas as rotas HTTP (`setupRoutes`, linhas 25-138), e (c) toda a regra de negócio não-trivial do sistema — orquestração de checkout (pagamento, matrícula, auditoria) e cálculo de relatório financeiro — escrita inline dentro dos próprios handlers de rota.
Impact: É impossível testar a regra "um cartão que não começa com 4 é recusado" ou "o relatório financeiro soma corretamente os pagamentos PAID" sem subir um servidor Express e um banco SQLite completos. Qualquer mudança de uma regra de negócio exige tocar no mesmo arquivo que define rotas e schema, aumentando o risco de regressão.
Recommendation: Ver padrão 1 do playbook (separar o God File em Models por domínio: `User`, `Course`, `Enrollment`, `Payment`) combinado com o padrão 2 (mover a regra de negócio dos handlers para métodos desses Models), mantendo as rotas em Controllers finos.

[CRITICAL] Credenciais e segredos hardcoded (com vazamento adicional via log)
File: src/utils.js:2-6, src/AppManager.js:45
Description: O objeto `config` em `utils.js` traz `dbUser`, `dbPass` ("senha_super_secreta_prod_123"), `paymentGatewayKey` ("pk_live_1234567890abcdef") e `smtpUser` como literais de string no código-fonte, versionados no git. Piorando o quadro, `AppManager.js:45` executa `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` — ou seja, a cada checkout, o número completo do cartão de crédito informado pelo cliente e a chave live do gateway de pagamento são escritos em texto claro na saída padrão/logs do processo.
Impact: Qualquer pessoa com acesso ao repositório (ou a um log agregado, ex: em produção) obtém a senha do banco, a chave de produção do gateway de pagamento e, adicionalmente, números de cartão de clientes reais — uma violação direta de PCI-DSS, que proíbe armazenar/logar o PAN em texto claro.
Recommendation: Ver padrão 4 do playbook (externalizar config/segredos para variáveis de ambiente, com `.env` fora do git) e remover completamente o log do número do cartão e da chave do gateway — nunca logar dados de pagamento ou segredos, nem parcialmente.

[CRITICAL] Senha armazenada com "hash" artesanal reversível e colidente
File: src/utils.js:17-23, src/AppManager.js:68
Description: `badCrypto(pwd)` faz `Buffer.from(pwd).toString('base64')`, pega os 2 primeiros caracteres e repete o mesmo trecho 10000 vezes, cortando em 10 caracteres — o valor de `pwd` nunca é reconsiderado a cada iteração, então o resultado depende só do primeiro byte (e metade do segundo) da senha. Confirmado executando a função: `badCrypto("senhaforte")` e `badCrypto("senha123")` produzem exatamente `"c2c2c2c2c2"` — a mesma saída para senhas diferentes — e `badCrypto("123456")`/`badCrypto("123")` colidem em `"MTMTMTMTMT"`. Não é um algoritmo de hash, é uma codificação reversível (Base64) truncada.
Impact: Colisões triviais permitem autenticação com uma senha diferente da original sempre que o primeiro byte coincidir (ex.: qualquer senha começando com "s" e segundo caractere próximo colide com "senhaforte"); além disso, por ser Base64 (reversível), quem lê a coluna `pass` recupera quase a senha original diretamente, sem precisar quebrar hash nenhum.
Recommendation: Ver padrão 5 do playbook — substituir `badCrypto` por `bcrypt`/`argon2` (hash com salt e custo configurável), nunca reimplementar hashing na mão.

[CRITICAL] Autenticação/Autorização decorativa em operações sensíveis
File: src/AppManager.js:66-75, 80, 131
Description: Em `/api/checkout`, quando o e-mail já pertence a um usuário existente, o código chama `processPaymentAndEnroll(user.id)` (linha 74) sem nunca comparar a senha `p` enviada com o `pass` já salvo — ou seja, basta conhecer o e-mail de qualquer cliente para "logar" como ele e fazer compras em seu nome. Além disso, `GET /api/admin/financial-report` (linha 80) devolve receita e lista de alunos de todos os cursos, e `DELETE /api/users/:id` (linha 131) apaga qualquer usuário — ambos sem nenhuma verificação de token, sessão ou papel de administrador em qualquer ponto da rota.
Impact: Qualquer chamador não autenticado consegue extrair o relatório financeiro completo da plataforma e apagar contas de usuários arbitrariamente, e qualquer pessoa pode fazer checkout usando a identidade de outro cliente só sabendo seu e-mail — isso expõe dados sensíveis de negócio e permite dano direto a contas de terceiros, sem exigir nenhuma credencial válida.
Recommendation: Ver padrão 6 do playbook (autenticação real com token assinado + middleware `requer_autenticacao`) aplicado a `/api/admin/financial-report` e `DELETE /api/users/:id`, e adicionar a verificação de senha (hash) para usuário já existente antes de prosseguir com o checkout.

[HIGH] Lógica de negócio pesada nas rotas (ausência de camada de Service/Model)
File: src/AppManager.js:28-78, 80-129
Description: A decisão de aprovação de pagamento (`cc.startsWith("4") ? "PAID" : "DENIED"`, linha 46) e o cálculo de receita/composição do relatório financeiro (acumulação de `courseData.revenue` e `courseData.students`, linhas 89-127) são regras de domínio escritas diretamente dentro dos handlers `app.post`/`app.get`, misturadas com parsing de request e resposta HTTP.
Impact: Se amanhã outra rota (ex: um endpoint de reprocessamento de pagamento) precisar da mesma regra de aprovação ou do mesmo cálculo de receita, o único jeito é copiar o trecho — e as duas cópias divergem com o tempo, exatamente o risco que separação em camadas existe para evitar.
Recommendation: Ver padrão 2 do playbook — extrair `Payment.approve(cardNumber)` e `Course.calculateRevenueReport()` (ou equivalente) para os Models, deixando os handlers como Controllers finos que apenas coordenam request → Model → response.

[HIGH] Estado global mutável compartilhado
File: src/utils.js:9-15, src/AppManager.js:59
Description: `globalCache` e `totalRevenue` são declarados como variáveis de módulo (linhas 9-10 de `utils.js`), fora de qualquer classe ou escopo de requisição. `logAndCache`, chamada a cada checkout bem-sucedido (`AppManager.js:59`), escreve em `globalCache` diretamente, sem nenhuma sincronização ou isolamento por requisição.
Impact: Múltiplas requisições concorrentes de checkouts diferentes compartilham e sobrescrevem o mesmo objeto `globalCache` (as chaves usam `userId`, então na prática colidem entre requisições do mesmo usuário), e `totalRevenue` fica declarado e exportado mas nunca é de fato incrementado em lugar nenhum — código morto que sinaliza uma intenção de estado global que nunca foi terminada.
Recommendation: Eliminar `globalCache`/`totalRevenue` como estado de módulo; se um cache for necessário, usar um mecanismo com escopo e TTL explícitos (ex: uma camada de cache injetada, não uma variável solta no módulo).

[MEDIUM] Queries N+1 no relatório financeiro
File: src/AppManager.js:89-127
Description: Para montar `/api/admin/financial-report`, o código itera os cursos com `forEach` (linha 89) e, para cada curso, dispara uma query de matrículas (linha 92); para cada matrícula, dispara mais duas queries em série — uma de usuário (linha 104) e uma de pagamento (linha 106). Com N cursos e M matrículas por curso, isso é `1 + N + N*M*2` queries para uma única requisição.
Impact: Com poucos cursos/matrículas o efeito é imperceptível, mas o padrão não escala — cada novo curso/matrícula adiciona queries síncronas em série ao tempo de resposta do endpoint administrativo, que tende a ser justamente o mais consultado (dashboards).
Recommendation: Ver padrão 7 do playbook — substituir os três níveis de loop por um `JOIN` único (`courses` ⋈ `enrollments` ⋈ `users` ⋈ `payments`) ou por três queries com `WHERE id IN (...)`, agregando em memória.

[MEDIUM] Tratamento de erro que engole falhas
File: src/AppManager.js:92, 104, 106, 133-136
Description: Nas queries de matrículas/usuário/pagamento dentro do relatório financeiro (linhas 92, 104, 106), o parâmetro `err` do callback nunca é verificado antes de seguir usando o resultado. Em `DELETE /api/users/:id` (linhas 133-136), o `err` do `db.run` também é ignorado e a rota sempre responde com sucesso, inclusive dizendo explicitamente no próprio texto da resposta que o banco fica inconsistente: `"Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."`.
Impact: Uma falha real (ex: banco travado, constraint violada) nessas queries não é reportada para o cliente nem logada — o usuário recebe uma resposta de sucesso mesmo quando a operação falhou ou deixou dados órfãos (matrículas/pagamentos apontando para um `user_id` que não existe mais), corrompendo silenciosamente a integridade referencial dos dados.
Recommendation: Ver padrão 8 do playbook — checar `err` em todo callback antes de prosseguir e centralizar o tratamento de erro; para o `DELETE`, também remover em cascata (ou bloquear a exclusão) as `enrollments`/`payments` associadas em vez de deixá-las órfãs.

[LOW] Magic numbers / strings mágicas
File: src/AppManager.js:15, 21, 46, 48, 68, 108
Description: A regra de aprovação de pagamento está codificada como o literal `"4"` (`cc.startsWith("4")`, linha 46) sem nenhuma constante nomeada explicando a regra de negócio; os status `"PAID"`/`"DENIED"` são strings soltas repetidas em várias linhas (15, 21, 46, 48, 108) em vez de um enum/constantes; e a senha default `"123456"` (linha 68) é um literal de fallback embutido no meio da lógica de checkout.
Impact: Sem uma constante nomeada, um leitor não sabe se `"4"` é um valor arbitrário de teste ou uma regra de negócio real (bandeira de cartão); divergências de grafia entre `"PAID"` e um eventual `"Paid"` em outro lugar não seriam pegas em tempo de desenvolvimento.
Recommendation: Extrair `PAYMENT_STATUS = { PAID: "PAID", DENIED: "DENIED" }` e uma constante/função nomeada para a regra de aprovação, eliminando os literais espalhados.

[LOW] Nomenclatura pouco descritiva e logging via console.log
File: src/AppManager.js:29-33, 45; src/app.js:13; src/utils.js:13
Description: Os dados do corpo da requisição de checkout são atribuídos a variáveis de uma ou duas letras (`u`, `e`, `p`, `cid`, `cc`, linhas 29-33) para conceitos de domínio importantes (nome, e-mail, senha, id do curso, cartão). Eventos de negócio e erros são reportados só via `console.log` (`app.js:13`, `AppManager.js:45`, `utils.js:13`), sem nível, timestamp ou destino configurável.
Impact: Nomes de uma letra tornam o fluxo de checkout mais difícil de revisar e mais propenso a troca acidental de variável (ex: usar `e` no lugar de `p`); `console.log` sem estrutura não pode ser filtrado por nível em produção nem redirecionado para um agregador de logs sem parsing manual.
Recommendation: Renomear para nomes de domínio (`username`, `email`, `password`, `courseId`, `cardNumber`) e substituir `console.log` por um logger configurável (ex: `pino`/`winston`) com níveis.

================================
Total: 10 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

## Phase 3 — Refactoring Complete

```
================================
PHASE 3: REFACTORING COMPLETE
================================
New Project Structure:
src/
├── app.js                          # composition root: express, rotas, middlewares, listen
├── config/
│   └── settings.js                 # lê segredos/config de variáveis de ambiente (falha se faltar)
├── database/
│   └── connection.js               # conexão sqlite3 + schema + seed (senha do seed já com bcrypt)
├── models/
│   ├── User.js                     # hash/verificação de senha (bcrypt), CRUD de usuário
│   ├── Course.js                   # busca de curso + relatório financeiro (JOIN único, sem N+1)
│   ├── Enrollment.js                # matrícula: criar/buscar/deletar por usuário
│   ├── Payment.js                  # regra de aprovação de pagamento + persistência
│   └── AuditLog.js                 # registro de auditoria
├── controllers/
│   ├── checkoutController.js       # orquestra checkout: valida, autentica, aprova, matricula
│   ├── adminController.js          # relatório financeiro
│   └── userController.js           # exclusão de usuário com limpeza em cascata
├── routes/
│   ├── checkoutRoutes.js           # POST /api/checkout
│   ├── adminRoutes.js               # GET /api/admin/financial-report (protegida)
│   └── userRoutes.js               # DELETE /api/users/:id (protegida)
├── middlewares/
│   ├── errorHandler.js             # tratamento de erro centralizado
│   └── requireAdminKey.js          # autenticação real de rotas administrativas
└── utils/
    ├── constants.js                # PAYMENT_STATUS, DEFAULT_PASSWORD (fim dos magic strings)
    └── logger.js                   # logger com nível + timestamp (sem console.log cru)

.env / .env.example                 # segredos fora do código-fonte (config/settings.js os exige)

Validation
  ✓ Application boots without errors
  ✓ All endpoints respond correctly (mesmo status/forma de resposta nos fluxos originais)
  ✓ 10/10 anti-patterns from the audit report resolved
================================
```

### Detalhe da validação

Endpoints originais mapeados e exercitados via `curl` com a aplicação subida em background (`node src/app.js`), banco SQLite em memória com os mesmos seeds:

| # | Requisição | Esperado (original) | Obtido (refatorado) |
|---|---|---|---|
| 1 | `POST /api/checkout` (novo usuário, cartão `4...`) | 200, `{msg, enrollment_id}` | 200, `{"msg":"Sucesso","enrollment_id":2}` |
| 2 | `POST /api/checkout` (novo usuário, cartão `5...`) | 400 "Pagamento recusado" | 400 "Pagamento recusado" |
| 3 | `GET /api/admin/financial-report` sem header | *(antes: 200 sem restrição)* | 401 `{"erro":"Não autorizado"}` — comportamento corrigido de propósito (Finding CRITICAL #4) |
| 4 | `GET /api/admin/financial-report` com `x-admin-key` correto | 200, array de cursos | 200, mesmo formato: `[{"course","revenue","students"}]` |
| 5 | `POST /api/checkout` (e-mail existente, senha errada) | *(antes: 200, sem checar senha)* | 401 "Credenciais inválidas" — comportamento corrigido de propósito (Finding CRITICAL #4) |
| 6 | `POST /api/checkout` (e-mail existente, senha correta) | 200 | 200, `{"msg":"Sucesso","enrollment_id":3}` |
| 7 | `DELETE /api/users/:id` sem header | *(antes: 200 sempre, mesmo com erro)* | 401 `{"erro":"Não autorizado"}` — comportamento corrigido de propósito (Finding CRITICAL #4) |
| 8 | `DELETE /api/users/:id` com `x-admin-key` correto | *(antes: 200 texto fixo, deixava órfãos)* | 200 JSON, e `enrollments`/`payments` do usuário são removidos em cascata (Finding MEDIUM #9) |
| 9 | `GET /api/admin/financial-report` após o delete | — | Curso do usuário deletado aparece com `revenue: 0, students: []` — confirma que não sobrou nenhum registro órfão |
| 10 | `POST /api/checkout` (campos faltando) | 400 "Bad Request" | 400 "Bad Request" |

Os itens 3, 5 e 7 mudam de comportamento **intencionalmente**: eram exatamente os apontamentos CRITICAL de autenticação/autorização decorativa do relatório da Fase 2. Preservar o comportamento antigo ali significaria preservar o bug. Todos os outros fluxos (sucesso de checkout, pagamento recusado, formato do relatório financeiro, validação de campos obrigatórios) mantêm status code e forma de resposta idênticos aos originais.

### Apontamentos do relatório × correção aplicada

| Finding (Fase 2) | Severidade | Resolvido em | Como |
|---|---|---|---|
| God Class / God File | CRITICAL | `models/*.js`, `controllers/*.js`, `routes/*.js` | `AppManager.js` foi eliminado; schema, regra de negócio e rotas viraram camadas separadas (padrão 1 + 2 do playbook) |
| Credenciais/segredos hardcoded + vazamento em log | CRITICAL | `config/settings.js`, `.env`/`.env.example`, `checkoutController.js` | Segredos saíram do código-fonte para env vars (falha se ausente); log do cartão/chave de pagamento foi removido (padrão 4) |
| Senha com "hash" artesanal colidente | CRITICAL | `models/User.js`, `database/connection.js` | `badCrypto` substituído por `bcrypt` (hash + salt); seed também passou a gerar hash real (padrão 5) |
| Autenticação/Autorização decorativa | CRITICAL | `middlewares/requireAdminKey.js`, `checkoutController.js` | Checkout agora verifica a senha (bcrypt.compare) para usuário existente; admin/delete exigem `x-admin-key` válido (padrão 6, adaptado — ver nota abaixo) |
| Lógica de negócio pesada nas rotas | HIGH | `models/Payment.js`, `models/Course.js` | Aprovação de pagamento e cálculo de receita viraram métodos de Model, reutilizáveis e testáveis sem servidor (padrão 2) |
| Estado global mutável compartilhado | HIGH | — (removido) | `globalCache`/`totalRevenue`/`logAndCache` eliminados: não tinham consumidor real e só existiam como estado de módulo não sincronizado |
| Queries N+1 no relatório financeiro | MEDIUM | `models/Course.js` (`findFinancialReport`) | Os 3 níveis de loop viraram um único `LEFT JOIN`, agregado em memória (padrão 7) |
| Tratamento de erro que engole falhas | MEDIUM | `controllers/userController.js`, `models/*.js`, `middlewares/errorHandler.js` | Todo `err` de callback agora é propagado (`reject`/`next(err)`); `DELETE` deixou de responder sucesso incondicional e passou a limpar `enrollments`/`payments` associados |
| Magic numbers / strings mágicas | LOW | `utils/constants.js` | `PAYMENT_STATUS` e `DEFAULT_PASSWORD` nomeados e centralizados |
| Nomenclatura pouco descritiva + console.log | LOW | `controllers/*.js`, `utils/logger.js` | Variáveis renomeadas para nomes de domínio; `console.log` cru substituído por `logger.info/error` com nível e timestamp |

**Nota sobre o padrão 6 do playbook**: em vez de introduzir um sistema completo de login/JWT (que exigiria um endpoint de login novo e mudar o contrato de `/api/checkout` para exigir token), a autenticação das rotas administrativas foi resolvida com um segredo compartilhado (`ADMIN_API_KEY`) validado em middleware — uma autenticação real (rejeita toda requisição sem o segredo correto), porém mais simples que JWT completo. Se o produto precisar de múltiplos administradores com sessões/tokens individuais, migrar `requireAdminKey` para JWT com um endpoint de login é o próximo passo natural, fora do escopo desta refatoração.

Todos os 10 apontamentos do relatório da Fase 2 foram corrigidos — nenhum ficou pendente.
```
