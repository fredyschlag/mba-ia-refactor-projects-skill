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

## C) Resultados

## D) Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado
- Python 3.11+ e `pip` (projetos 1 e 3)
- Node.js 18+ e `npm` (projeto 2)

### Rodando os projetos

```bash
# Projeto 1 — code-smells-project
cd code-smells-project
pip install -r requirements.txt
python app.py            # http://localhost:5000

# Projeto 2 — ecommerce-api-legacy
cd ecommerce-api-legacy
npm install
npm start                 # http://localhost:3000

# Projeto 3 — task-manager-api
cd task-manager-api
pip install -r requirements.txt
python seed.py             # popular o banco antes do primeiro boot
python app.py              # http://localhost:5000
```

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

### Rodando as provas de conceito da Análise Manual

Cada projeto tem uma suíte de testes que prova, em tempo de execução, os achados listados na seção A). Não usam dependências além das já declaradas nos próprios projetos.

```bash
# Projeto 1 — 7 testes (unittest + Flask test client)
cd code-smells-project
python3 -m unittest tests.test_findings -v

# Projeto 2 — 7 testes (node:test, nativo do Node >= 18)
cd ../ecommerce-api-legacy
node --test test/findings.test.js

# Projeto 3 — 7 testes (unittest + Flask/SQLAlchemy isolado em memória)
cd ../task-manager-api
python3 -m unittest tests.test_findings -v
```
