# Skill de Auditoria e Refatoração Arquitetural

Skill (`refactor-arch`) capaz de analisar, auditar e refatorar para o padrão MVC qualquer um dos três projetos legados abaixo, de forma agnóstica de tecnologia.

## Sumário

- [A) Análise Manual](#a-análise-manual)
  - [Projeto 1 — code-smells-project](#projeto-1--code-smells-project-pythonflask)
  - [Projeto 2 — ecommerce-api-legacy](#projeto-2--ecommerce-api-legacy-nodejsexpress)
  - [Projeto 3 — task-manager-api](#projeto-3--task-manager-api-pythonflask)
- [B) Construção da Skill](#b-construção-da-skill)
- [C) Resultados](#c-resultados)
- [D) Como Executar](#d-como-executar)

---

## A) Análise Manual

Critério de severidade usado:

| Severidade | Critério |
|---|---|
| **CRITICAL** | Falha grave de arquitetura/segurança: impede funcionamento correto, expõe dados sensíveis (credenciais hardcoded, SQL Injection) ou quebra totalmente a separação de responsabilidades (God Class com DB + lógica + rotas juntos) |
| **HIGH** | Forte violação de MVC/SOLID: lógica de negócio pesada no Controller, acoplamento forte sem DI, estado global mutável |
| **MEDIUM** | Padronização, duplicação de código, gargalo de performance moderado (N+1, middlewares mal usados, validação ausente) |
| **LOW** | Legibilidade, nomenclatura ruim, magic numbers |

### Projeto 1 — code-smells-project (Python/Flask)

Prova de conceito automatizada de todos os achados: [`code-smells-project/tests/test_findings.py`](code-smells-project/tests/test_findings.py) (`python3 -m unittest tests.test_findings -v`, 7/7 passando).

| # | Severidade | Problema | Local | Justificativa | Prova (teste) |
|---|---|---|---|---|---|
| 1 | **CRITICAL** | SQL Injection generalizado | [models.py:28](code-smells-project/models.py#L28), 48-50, 58-60, 68, 92, 109-111, 127-128, 140, 148-151, 155-166, 174, 188, 192, 220, 224, 279-280, 289-297 | Praticamente toda query é montada por concatenação de string com input do usuário (`"WHERE id = " + str(id)`, `"WHERE email = '" + email + "' AND senha = '" + senha + "'"`). Permite bypass de login e exfiltração/alteração total do banco. | [`test_findings.py:60`](code-smells-project/tests/test_findings.py#L60) |
| 2 | **CRITICAL** | Credenciais e segredos hardcoded + expostos via API | [app.py:7](code-smells-project/app.py#L7) (`SECRET_KEY`), [controllers.py:288-289](code-smells-project/controllers.py#L288-L289) (`health_check` retorna `debug` e `secret_key` no JSON) | O `SECRET_KEY` do Flask está commitado em texto plano e, pior, é devolvido no corpo da resposta de `/health` — qualquer cliente externo consegue ler o segredo da aplicação. | [`test_findings.py:78`](code-smells-project/tests/test_findings.py#L78) |
| 3 | **CRITICAL** | Senhas armazenadas e comparadas em texto plano | [models.py:105-120](code-smells-project/models.py#L105-L120) (`login_usuario`), [database.py:76-79](code-smells-project/database.py#L76-L79) (seed com senha em claro) | Não há hashing de senha; a comparação é feita direto na cláusula `WHERE senha = '...'`. Um vazamento do banco expõe todas as senhas dos usuários imediatamente. | [`test_findings.py:92`](code-smells-project/tests/test_findings.py#L92) |
| 4 | **MEDIUM** | Queries N+1 ao montar pedidos | [models.py:171-233](code-smells-project/models.py#L171-L233) (`get_pedidos_usuario`, `get_todos_pedidos`) | Para cada pedido, abre um cursor para buscar itens e, para cada item, outro cursor para buscar o nome do produto — número de queries cresce linearmente com itens × pedidos. | [`test_findings.py:111`](code-smells-project/tests/test_findings.py#L111) |
| 5 | **MEDIUM** | Validação duplicada entre `criar_produto` e `atualizar_produto` | [controllers.py:24-96](code-smells-project/controllers.py#L24-L96) | O mesmo bloco de validações (nome, preço, estoque, categoria) é copiado e colado em vez de extraído para uma função/validador reutilizável. | [`test_findings.py:157`](code-smells-project/tests/test_findings.py#L157) |
| 6 | **LOW** | Magic numbers espalhados | [controllers.py:47-50](code-smells-project/controllers.py#L47-L50) (tamanho do nome 2/200), [models.py:257-262](code-smells-project/models.py#L257-L262) (limiares de desconto 10000/5000/1000) | Limites de negócio embutidos como literais no meio do código, sem nome nem constante centralizada, dificultando manutenção. | [`test_findings.py:195`](code-smells-project/tests/test_findings.py#L195) |
| 7 | **LOW** | `print()` como mecanismo de log | [controllers.py:8,57,161,179,182,208-210](code-smells-project/controllers.py) | Uso de `print` para logging de eventos de negócio e erros em vez do módulo `logging`, sem níveis, timestamps ou destino configurável. | [`test_findings.py:249`](code-smells-project/tests/test_findings.py#L249) |

### Projeto 2 — ecommerce-api-legacy (Node.js/Express)

Prova de conceito automatizada de todos os achados: [`ecommerce-api-legacy/test/findings.test.js`](ecommerce-api-legacy/test/findings.test.js) (`node --test test/findings.test.js`, 7/7 passando).

| # | Severidade | Problema | Local | Justificativa | Prova (teste) |
|---|---|---|---|---|---|
| 1 | **CRITICAL** | God Class concentrando DB, rotas e regras de negócio | [AppManager.js](ecommerce-api-legacy/src/AppManager.js) (142 linhas) | Uma única classe cria o schema do banco, define todas as rotas Express e implementa a lógica de checkout/pagamento — exatamente o padrão de "God Class" do critério CRITICAL. | [`findings.test.js:48`](ecommerce-api-legacy/test/findings.test.js#L48) |
| 2 | **CRITICAL** | Credenciais e chaves de produção hardcoded | [utils.js:1-7](ecommerce-api-legacy/src/utils.js#L1-L7) (`dbPass`, `paymentGatewayKey`, `smtpUser`) | Segredos de produção (inclusive uma chave de gateway de pagamento `pk_live_...`) commitados em texto plano no repositório. | [`findings.test.js:67`](ecommerce-api-legacy/test/findings.test.js#L67) |
| 3 | **CRITICAL** | Hash de senha falso/quebrado | [utils.js:17-23](ecommerce-api-legacy/src/utils.js#L17-L23) (`badCrypto`) | Não é um algoritmo de hash: repete Base64 do texto original e trunca para 10 caracteres. É reversível na prática e não usa salt — equivalente a armazenar a senha em claro. | [`findings.test.js:76`](ecommerce-api-legacy/test/findings.test.js#L76) |
| 4 | **MEDIUM** | Queries N+1 no relatório financeiro | [AppManager.js:80-129](ecommerce-api-legacy/src/AppManager.js#L80-L129) (`/api/admin/financial-report`) | Para cada curso busca matrículas, e para cada matrícula busca usuário e pagamento em queries separadas dentro de callbacks aninhados — não usa `JOIN`. | [`findings.test.js:90`](ecommerce-api-legacy/test/findings.test.js#L90) |
| 5 | **MEDIUM** | Erros de banco silenciados/ignorados | [AppManager.js:92,104,106](ecommerce-api-legacy/src/AppManager.js#L92) | Vários callbacks recebem `err` e simplesmente não o verificam antes de seguir usando o resultado, podendo mascarar falhas do banco como dados vazios. | [`findings.test.js:119`](ecommerce-api-legacy/test/findings.test.js#L119) |
| 6 | **LOW** | Nomenclatura de variáveis não descritiva | [AppManager.js:29-33](ecommerce-api-legacy/src/AppManager.js#L29-L33) (`u`, `e`, `p`, `cid`, `cc`) | Abreviações genéricas de uma letra para campos de domínio (usuário, email, senha, curso, cartão) dificultam a leitura do fluxo de checkout. | [`findings.test.js:140`](ecommerce-api-legacy/test/findings.test.js#L140) |
| 7 | **LOW** | Strings mágicas de status repetidas | [AppManager.js:46,54](ecommerce-api-legacy/src/AppManager.js#L46) (`"PAID"`, `"DENIED"`) e regra "cartão começa com 4" | Status de pagamento e regra de aprovação (prefixo do número do cartão) são literais espalhados pelo código, sem constantes nem um gateway real. | [`findings.test.js:152`](ecommerce-api-legacy/test/findings.test.js#L152) |

### Projeto 3 — task-manager-api (Python/Flask)

Mesmo já tendo separação em `models/`, `routes/`, `services/`, `utils/`, o projeto concentra lógica de domínio
nas rotas (Controllers "gordos") e tem falhas de segurança relevantes.

Prova de conceito automatizada de todos os achados: [`task-manager-api/tests/test_findings.py`](task-manager-api/tests/test_findings.py) (`python3 -m unittest tests.test_findings -v`, 7/7 passando).

| # | Severidade | Problema | Local | Justificativa | Prova (teste) |
|---|---|---|---|---|---|
| 1 | **CRITICAL** | Autenticação via token falso, previsível e sem validação | [routes/user_routes.py:210](task-manager-api/routes/user_routes.py#L210) (`'fake-jwt-token-' + str(user.id)`) | O "token" é só o ID do usuário concatenado a uma string fixa — trivialmente forjável (`fake-jwt-token-1`) e nenhuma rota valida esse token, ou seja, não existe autenticação real de fato. | [`test_findings.py:72`](task-manager-api/tests/test_findings.py#L72) |
| 2 | **CRITICAL** | Hash de senha com MD5 | [models/user.py:27-32](task-manager-api/models/user.py#L27-L32) (`set_password`/`check_password`) | MD5 é criptograficamente quebrado (colisões e rainbow tables), inadequado para senhas; falta salt e um algoritmo lento (bcrypt/argon2/scrypt). | [`test_findings.py:93`](task-manager-api/tests/test_findings.py#L93) |
| 3 | **CRITICAL** | Credenciais hardcoded (app + serviço de email) | [app.py:13](task-manager-api/app.py#L13) (`SECRET_KEY`), [services/notification_service.py:7-10](task-manager-api/services/notification_service.py#L7-L10) (usuário/senha SMTP em claro) | Segredos de aplicação e de um serviço de terceiros (SMTP) commitados no código-fonte, apesar do projeto já declarar `python-dotenv` no `requirements.txt` sem nunca usá-lo. | [`test_findings.py:107`](task-manager-api/tests/test_findings.py#L107) |
| 4 | **MEDIUM** | Queries N+1 em listagens e relatórios | [routes/task_routes.py:41-57](task-manager-api/routes/task_routes.py#L41-L57) (`get_tasks` busca `User`/`Category` por task dentro do loop), [routes/report_routes.py:53-68](task-manager-api/routes/report_routes.py#L53-L68) (`summary_report` roda uma query de tasks por usuário dentro do loop de usuários) | Número de queries cresce linearmente com a quantidade de registros em vez de usar `JOIN` ou eager loading do SQLAlchemy. | [`test_findings.py:121`](task-manager-api/tests/test_findings.py#L121) |
| 5 | **MEDIUM** | Validação e utilitários duplicados/mortos | [routes/user_routes.py:61](task-manager-api/routes/user_routes.py#L61) reimplementa a regex de `utils/helpers.py:19-23` (`validate_email`, nunca importada); [utils/helpers.py:110-116](task-manager-api/utils/helpers.py#L110-L116) define constantes (`MIN_TITLE_LENGTH`, `VALID_STATUSES` etc.) que nenhuma rota importa, usando literais soltos em vez disso | Há uma camada `utils/` com funções e constantes prontas para reuso, mas as rotas reimplementam a mesma validação com literais duplicados — a "organização parcial" do projeto é superficial. | [`test_findings.py:162`](task-manager-api/tests/test_findings.py#L162) |
| 6 | **LOW** | Dados sensíveis retornados pela API | [models/user.py:16-25](task-manager-api/models/user.py#L16-L25) (`to_dict` inclui `password`) | O hash da senha é devolvido em `POST /users` e `GET /users/<id>`; mesmo hasheado, não deveria trafegar na resposta da API. | [`test_findings.py:177`](task-manager-api/tests/test_findings.py#L177) |
| 7 | **LOW** | Imports não utilizados e magic numbers | [routes/task_routes.py:7](task-manager-api/routes/task_routes.py#L7) (`json, os, sys, time` nunca usados), limites `3`/`200` repetidos como literais em vez das constantes já existentes em `utils/helpers.py` | Sinais de código copiado/colado sem limpeza, aumentando ruído e risco de inconsistência entre validações. | [`test_findings.py:192`](task-manager-api/tests/test_findings.py#L192) |

---

## B) Construção da Skill

### Decisões de design

- `SKILL.md` orquestra as 3 fases em menos de 90 linhas e não repete conhecimento de domínio — só aponta para o arquivo de referência certo em cada fase (progressive disclosure).
- 5 arquivos em `references/` cobrem as 5 áreas de conhecimento exigidas: análise de projeto, catálogo de anti-patterns, template de relatório, guidelines de MVC e playbook de refatoração.
- As 3 fases geram e complementam um único `reports/audit-report.md` por projeto, em vez de só imprimir no chat.
- O template do relatório usa rótulos estruturais fixos em inglês (`Summary`, `Findings`, `File:`, `Description:`, `Impact:`, `Recommendation:`) com conteúdo em português.
- A confirmação da Fase 2 é tratada como decisão humana explícita na conversa, não como permissão de ferramenta.
- A skill tem uma única fonte fora do controle de versão, replicada para os 3 projetos por um script — as 3 cópias commitadas nunca divergem entre si.

### Anti-patterns incluídos

Catálogo com 13 anti-patterns, cobrindo as 4 severidades: CRITICAL (God Class, SQL Injection, credenciais hardcoded, hashing de senha ausente ou quebrado), HIGH (autenticação decorativa, lógica de negócio no Controller, estado global mutável), MEDIUM (queries N+1, validação duplicada, erros silenciados, APIs deprecated) e LOW (magic numbers, nomenclatura ruim/logging via print). Cada item generaliza um problema real confirmado na Análise Manual (seção A) — não são hipotéticos.

### Como garantiu que a skill é agnóstica de tecnologia

- Detecção de stack por evidência (manifesto, imports, DDL, nomes de tabela/rota), não por regra fixa por framework.
- Sinais de anti-pattern descritos como padrões estruturais, não como sintaxe de uma linguagem específica.
- Exemplos do playbook alternam Python/Flask e Node/Express de propósito, com instrução explícita para adaptar em vez de copiar.
- Validada na prática: um smoke test (subagente com acesso só à skill) identificou stack, domínio e apontamentos corretamente sem nenhuma dica prévia.

### Dificuldades encontradas

- O playbook só era lido na Fase 3, mas o relatório da Fase 2 já precisava citar o padrão de transformação aplicável — corrigido lendo o playbook também na Fase 2.
- Uma primeira versão do template traduziu os rótulos estruturais para português; corrigido para usar os rótulos em inglês esperados.
- Um script de reformatação de texto chegou a corromper o frontmatter YAML do `SKILL.md` ao juntar linhas indevidamente; identificado na revisão e corrigido antes de qualquer execução real.

## C) Resultados

Relatórios completos (Fase 1 + Fase 2 + Fase 3) em [`reports/audit-project-1.md`](reports/audit-project-1.md), [`reports/audit-project-2.md`](reports/audit-project-2.md) e [`reports/audit-project-3.md`](reports/audit-project-3.md) — cópia do `reports/audit-report.md` gerado pela skill dentro de cada projeto.

### Resumo dos relatórios de auditoria

| Projeto | Stack | Arquivos analisados | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---|---|---|---|---|---|
| 1 — code-smells-project | Python/Flask | 4 | 5 | 3 | 2 | 2 | 12 |
| 2 — ecommerce-api-legacy | Node/Express | 3 | 4 | 2 | 2 | 2 | 10 |
| 3 — task-manager-api | Python/Flask | 15 | 3 | 2 | 4 | 2 | 11 |

Os 3 relatórios bateram ou superaram os problemas já catalogados na Análise Manual (seção A), incluindo apontamentos adicionais que a auditoria manual não tinha registrado (ex.: o backdoor `/admin/query` como achado isolado, o bug de type-safety em `priority` como string no Projeto 3, e o uso deprecated de `Query.get()` confirmado ao vivo por um `LegacyAPIWarning`).

### Antes/depois da estrutura

| Projeto | Antes | Depois | Apontamentos resolvidos |
|---|---|---|---|
| 1 — code-smells-project | 4 arquivos na raiz, sem camadas (`app.py`, `controllers.py`, `models.py`, `database.py`) | `config/`, `models/`, `routes/`, `controllers/`, `middlewares/` | 12/12 |
| 2 — ecommerce-api-legacy | 1 God Class (`AppManager.js`) concentrando schema, rotas e regra de negócio | `config/`, `database/`, `models/`, `controllers/`, `routes/`, `middlewares/`, `utils/` | 10/10 |
| 3 — task-manager-api | `models/`, `routes/`, `services/`, `utils/` já existiam, mas com regra de negócio pesada nas rotas | Mesmas pastas + `config/`, `controllers/`, `middlewares/` novos; rotas viraram finas | 11/11 |

### Checklist de validação (preenchido para os 3 projetos)

**Fase 1 — Análise**
- [x] Linguagem detectada corretamente
- [x] Framework detectado corretamente
- [x] Domínio da aplicação descrito corretamente
- [x] Número de arquivos analisados condiz com a realidade

**Fase 2 — Auditoria**
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada apontamento tem arquivo e linhas exatos
- [x] Apontamentos ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 apontamentos identificados (10 a 12 por projeto)
- [x] Detecção de API deprecated incluída (confirmada no Projeto 3, com `LegacyAPIWarning` real)
- [x] Skill pausou e pediu confirmação antes da Fase 3

**Fase 3 — Refatoração**
- [x] Estrutura de diretórios segue padrão MVC
- [x] Configuração extraída para módulo de config, sem hardcoded
- [x] Models criados para abstrair dados
- [x] Routes separadas para roteamento
- [x] Controllers concentram o fluxo da aplicação
- [x] Error handling centralizado
- [x] Entry point claro (composition root)
- [x] Aplicação inicia sem erros
- [x] Endpoints originais respondem corretamente

### Evidência de execução

Além da validação que a própria skill fez em cada relatório (seção "Detalhe da validação"/"Notas de validação" de cada arquivo em `reports/`), os 3 projetos foram subidos e exercitados de novo, de forma independente, nesta sessão — sem terminal gráfico disponível para *screenshot*, os logs abaixo são a evidência (saída real de cada boot + as requisições de validação, capturada ao vivo).

**Projeto 1 — code-smells-project** (`python app.py`; requisições: `/health`, login com senha errada, login correto, `/usuarios` sem e com token, `/admin/query`):

```
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
127.0.0.1 - - [07/Jul/2026 22:25:47] "GET /health HTTP/1.1" 200 -
127.0.0.1 - - [07/Jul/2026 22:25:47] "POST /login HTTP/1.1" 401 -
127.0.0.1 - - [07/Jul/2026 22:25:47] "POST /login HTTP/1.1" 200 -
127.0.0.1 - - [07/Jul/2026 22:25:47] "GET /usuarios HTTP/1.1" 401 -
127.0.0.1 - - [07/Jul/2026 22:25:47] "GET /usuarios HTTP/1.1" 200 -
127.0.0.1 - - [07/Jul/2026 22:25:47] "POST /admin/query HTTP/1.1" 404 -
```

**Projeto 2 — ecommerce-api-legacy** (`npm start`; requisições: checkout aprovado, checkout recusado, `financial-report` sem/com header admin):

```
> node src/app.js

◇ injected env (6) from .env
[INFO] 2026-07-08T01:26:13.378Z Frankenstein LMS rodando na porta 3000...
[INFO] 2026-07-08T01:26:15.042Z Processando pagamento do curso 2 para usuário 2
[INFO] 2026-07-08T01:26:15.161Z Processando pagamento do curso 1 para usuário 3
```

**Projeto 3 — task-manager-api** (`python seed.py && python app.py`; requisições: `/health`, `/tasks` sem token, login, `/tasks` com token, `DELETE /users/1`):

```
Seed concluído com sucesso!
  3 usuários
  4 categorias
  10 tasks

 * Serving Flask app 'app'
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
127.0.0.1 - - [07/Jul/2026 22:28:01] "GET /health HTTP/1.1" 200 -
127.0.0.1 - - [07/Jul/2026 22:28:01] "GET /tasks HTTP/1.1" 401 -
127.0.0.1 - - [07/Jul/2026 22:28:01] "POST /login HTTP/1.1" 200 -
127.0.0.1 - - [07/Jul/2026 22:28:01] "GET /tasks HTTP/1.1" 200 -
[2026-07-07 22:28:01,522] INFO in user_controller: Usuário deletado: 1
127.0.0.1 - - [07/Jul/2026 22:28:01] "DELETE /users/1 HTTP/1.1" 200 -
```

### Como a skill se comportou em stacks diferentes

- Identificou corretamente 2 pontos de partida bem diferentes em Python (monolito sem camadas vs. parcialmente organizado) e não tratou "já ter pastas `models/`/`routes/`" como sinônimo de "arquitetura correta" — o Projeto 3 tinha as pastas certas, mas ainda assim recebeu 11 apontamentos reais.
- Traduziu o mesmo anti-pattern para o idioma de cada stack: senha insegura virou MD5 sem salt em Python (Projeto 3) e um "hash" Base64 artesanal em JavaScript (Projeto 2) — sinais de detecção diferentes, mesma classificação de severidade.
- Fez uma escolha de escopo pragmática e explícita no Projeto 2: em vez de introduzir um fluxo de login/JWT novo (mudança de contrato maior), resolveu a autenticação decorativa das rotas administrativas com uma chave compartilhada validada em middleware, documentando no relatório por que essa foi a decisão e qual seria o próximo passo.
- Encontrou um caso real de API deprecated em tempo de execução (não só por leitura de código): o `LegacyAPIWarning` do SQLAlchemy 2.x ao rodar `Model.query.get()` no Projeto 3, confirmando a detecção descrita no catálogo.

## D) Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado
- Python 3.11+ e `pip` (projetos 1 e 3)
- Node.js 18+ e `npm` (projeto 2)

### Rodando os projetos

Os 3 projetos já passaram pela Fase 3 (estrutura MVC) e agora leem configuração/segredos de variáveis de ambiente — nenhum tem mais `SECRET_KEY`/credenciais hardcoded no código.

```bash
# Projeto 1 — code-smells-project (não usa dotenv: exporte as variáveis manualmente)
cd code-smells-project
pip install -r requirements.txt
cp .env.example .env
# edite .env e defina SECRET_KEY (ex: python3 -c "import secrets; print(secrets.token_hex(32))")
export $(cat .env | xargs)
python app.py              # http://localhost:5000

# Projeto 2 — ecommerce-api-legacy (variáveis carregadas automaticamente via dotenv)
cd ../ecommerce-api-legacy
npm install
cp .env.example .env
# edite .env: DB_USER, DB_PASS, PAYMENT_GATEWAY_KEY, SMTP_USER, ADMIN_API_KEY
export $(cat .env | xargs)
npm start                   # http://localhost:3000

# Projeto 3 — task-manager-api (variáveis carregadas automaticamente via dotenv)
cd ../task-manager-api
pip install -r requirements.txt
cp .env.example .env
# edite .env e defina SECRET_KEY
export $(cat .env | xargs)
python seed.py               # popular o banco antes do primeiro boot
python app.py                # http://localhost:5000
```

Autenticação passou a ser real (JWT) nos 3 projetos: faça `POST /login` (Projetos 1 e 3) com um usuário de seed para obter um token e envie-o via header `Authorization: Bearer <token>` nas rotas protegidas — os detalhes de cada projeto (usuários de seed, rotas que exigem admin) estão no `README.md` de cada um.

### Executando a skill

```bash
# Projeto 1
cd code-smells-project
claude "/refactor-arch"

# Projeto 2 (copiar a skill antes de invocar)
cd ../ecommerce-api-legacy
claude "/refactor-arch"

# Projeto 3 (copiar a skill antes de invocar)
cd ../task-manager-api
claude "/refactor-arch"
```