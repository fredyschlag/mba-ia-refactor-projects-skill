# Audit Report — task-manager-api

## Phase 1 — Project Analysis

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python
Framework:     Flask 3.0.0 (Flask-SQLAlchemy 3.1.1, Flask-CORS 4.0.0, Marshmallow 3.20.1, python-dotenv 1.0.0, requests 2.31.0)
Dependencies:  flask-sqlalchemy (ORM), flask-cors, marshmallow (declared but unused for validation), hashlib (stdlib, used for password "hashing")
Domain:        Task management system — users assign/track tasks organized by category, with priority, status, due dates and productivity reports.
Architecture:  Partially organized — models/, routes/, services/, utils/ folders already exist, but routes/*.py contain heavy business logic (validation, overdue calculation, dict-serialization duplicated from models) instead of delegating to Models/Controllers.
Source files:  15 files analyzed (app.py, database.py, seed.py, models/{__init__,task,user,category}.py, routes/{__init__,task_routes,user_routes,report_routes}.py, services/{__init__,notification_service}.py, utils/{__init__,helpers}.py)
DB tables:     tasks, users, categories (SQLite file tasks.db, created via db.create_all(), no migrations)
================================
```

## Phase 2 — Architecture Audit Report

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python / Flask 3.0.0 + Flask-SQLAlchemy 3.1.1 (SQLAlchemy 2.0.51) + SQLite
Files:   15 analyzed | ~1158 lines of code

Summary
CRITICAL: 3 | HIGH: 2 | MEDIUM: 4 | LOW: 2

Findings

[CRITICAL] Credenciais e configuração sensível hardcoded no app principal
File: app.py:11-13,34
Description: `SECRET_KEY = 'super-secret-key-123'` (linha 13) e a URI do banco (linha 11) estão embutidas como literais no código-fonte, e `app.run(debug=True, ...)` (linha 34) sobe o Werkzeug debugger sem nenhum controle por ambiente. `python-dotenv` está declarado em requirements.txt mas nenhum `load_dotenv()`/`os.environ` é chamado em nenhum arquivo do projeto (confirmado por grep) — a dependência existe mas nunca foi de fato usada para externalizar config.
Impact: qualquer pessoa com acesso ao repositório (ou a um dump de código) tem a SECRET_KEY usada para assinar sessões/cookies Flask. Debug mode ligado por padrão expõe o console interativo do Werkzeug em caso de exceção não tratada — se isso chegar a um ambiente exposto, é execução de código arbitrário remota, não apenas vazamento de stack trace.
Recommendation: ver padrão 4 do playbook (externalizar configuração e segredos) — mover SECRET_KEY, URI do banco e a flag de debug para variáveis de ambiente lidas via `os.environ`, com `.env.example` documentando as chaves esperadas e `.env` no `.gitignore`.

[CRITICAL] Credenciais SMTP hardcoded em NotificationService
File: services/notification_service.py:7-10
Description: `email_user = 'taskmanager@gmail.com'` e `email_password = 'senha123'` estão fixos no construtor da classe, em texto plano.
Impact: credencial real de uma conta de e-mail exposta a qualquer um com leitura do repositório — permite enviar e-mail em nome da aplicação (phishing/spam) ou, se a senha for reaproveitada em outro serviço, comprometer outras contas.
Recommendation: ver padrão 4 do playbook (externalizar configuração e segredos) — ler `EMAIL_HOST`, `EMAIL_USER` e `EMAIL_PASSWORD` de variáveis de ambiente.

[CRITICAL] Senha armazenada com hash inseguro (MD5 sem salt) e hash exposto na API
File: models/user.py:29,31-32,16-25
Description: `set_password` faz `hashlib.md5(pwd.encode()).hexdigest()` (linha 29) e `check_password` repete o mesmo cálculo para comparar (linhas 31-32). MD5 é criptograficamente quebrado e, sem salt, duas senhas idênticas geram exatamente o mesmo hash — confirmado rodando o hashing dos dados de `seed.py`: o usuário `joao@email.com` (senha `1234`) e qualquer outro usuário que usasse a mesma senha `1234` produziriam o hash idêntico `81dc9bdb52d04dc20036dbd8313ed055`, que é uma entrada conhecida em qualquer rainbow table pública (uma busca por esse hash específico já revela a senha em texto claro). Além disso, `to_dict()` (linhas 16-25) devolve o campo `password` (o hash) em toda resposta de `/users`, `/users/<id>`, `POST /users`, `PUT /users/<id>` e `/login`.
Impact: mesmo sem SQL Injection, um vazamento de banco (ou a própria API, já que o hash vai na resposta) permite quebrar senhas de usuários em segundos via rainbow table — não é preciso nem força bruta.
Recommendation: ver padrão 5 do playbook (hashing de senha seguro) — trocar para `werkzeug.security.generate_password_hash`/`check_password_hash` (já é dependência transitiva do Flask, não exige lib nova) e remover o campo de senha/hash do `to_dict()`.

[HIGH] Autenticação e autorização decorativas
File: routes/user_routes.py:185-211; models/user.py:34-38
Description: `/login` devolve `'token': 'fake-jwt-token-' + str(user.id)` (linha 210) — um valor previsível, sem assinatura. Nenhuma rota do projeto lê o header `Authorization` ou valida esse token (confirmado por grep em todo o código-fonte). O Model `User` já expõe `is_admin()` (linhas 34-38), mas nenhuma rota o chama antes de operações sensíveis como `DELETE /users/<id>`, `DELETE /tasks/<id>`, `DELETE /categories/<id>` ou a troca de `role` em `PUT /users/<id>` — qualquer cliente não autenticado pode deletar qualquer usuário/task/categoria ou promover um usuário a admin.
Impact: não existe controle de acesso real na API — o "login" é apenas cosmético; qualquer requisição, autenticada ou não, tem os mesmos privilégios totais sobre todos os dados.
Recommendation: ver padrão 6 do playbook (autenticação real em vez de token decorativo) — gerar um JWT assinado com a SECRET_KEY e validar via middleware/decorator em todas as rotas que hoje não checam nada; usar `is_admin()`/`role` para proteger as rotas destrutivas e administrativas. Se adicionar `pyjwt` estiver fora do escopo desta rodada, isso deve ficar explícito como próximo passo (não finja que o token atual é seguro).

[HIGH] Lógica de negócio duplicada nas rotas em vez de reutilizar o Model
File: routes/task_routes.py:30-39,71-80,110-114,177-183; routes/user_routes.py:171-180; routes/report_routes.py:34-37,132-135
Description: o cálculo "task está atrasada?" (`due_date < utcnow() and status not in (done, cancelled)`) é reimplementado manualmente com `if/else` aninhado em pelo menos 5 handlers diferentes, mesmo o Model `Task` já expondo `is_overdue()` (models/task.py:50-60) — que nunca é chamado em lugar nenhum (confirmado por grep). O mesmo vale para `validate_status`/`validate_priority` (models/task.py:38-48): também nunca chamados; `task_routes.py` reimplementa as mesmas checagens inline em `create_task` (linhas 110-114) e `update_task` (linhas 177-183).
Impact: a regra de negócio "o que é uma task atrasada" e "o que é uma prioridade/status válido" está espalhada em 7+ lugares — corrigir a regra (ex: mudar o critério de atraso) exige lembrar de editar todos os pontos, e é fácil esquecer um (risco real de divergência silenciosa).
Recommendation: ver padrão 2 do playbook (mover regra de negócio do Controller para o Model) — todo handler deve chamar `task.is_overdue()`, `task.validate_status(...)` e `task.validate_priority(...)` em vez de reimplementar a lógica.

[MEDIUM] Queries N+1
File: routes/task_routes.py:41-56; routes/report_routes.py:55-68,161-164
Description: `get_tasks()` (task_routes.py) faz `User.query.get(t.user_id)` e `Category.query.get(t.category_id)` dentro do loop `for t in tasks` — uma query extra por task, para cada uma das duas tabelas relacionadas. `summary_report()` (report_routes.py) faz `Task.query.filter_by(user_id=u.id).all()` dentro do loop `for u in users` (linha 56), e `get_categories()` faz `Task.query.filter_by(category_id=c.id).count()` dentro do loop `for c in categories` (linha 163).
Impact: o número de queries cresce linearmente com o número de registros (ex: 100 tasks = até 201 queries em `get_tasks`) — em produção, com volume real de dados, isso vira o principal gargalo de latência do endpoint mais usado da API.
Recommendation: ver padrão 7 do playbook (resolver N+1 com JOIN/eager loading) — usar `joinedload(Task.user, Task.category)` nas queries de listagem, e uma única query agregada (`GROUP BY`) para as contagens de `report_routes.py`.

[MEDIUM] Validação/utilitários duplicados e nunca reutilizados (com divergência real de comportamento)
File: utils/helpers.py:57-108,110-116; routes/report_routes.py:7,67,151; routes/task_routes.py:113
Description: `process_task_data()` (utils/helpers.py:57-108) reimplementa — em outro arquivo — a mesma validação de título/status/prioridade/tags que já existe em `task_routes.py`, mas nunca é importada nem chamada por nenhuma rota (confirmado por grep). As constantes `VALID_STATUSES`, `VALID_ROLES`, `MAX_TITLE_LENGTH`, `MIN_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH`, `DEFAULT_PRIORITY`, `DEFAULT_COLOR` (linhas 110-116) também nunca são referenciadas em lugar nenhum. `format_date`/`calculate_percentage` são importados em `report_routes.py:7` mas nunca chamados — o arquivo recalcula a mesma fórmula manualmente (`round((done/total)*100, 2) if total > 0 ...`, linha 151) em vez de usar `calculate_percentage`. Divergência concreta: `process_task_data` faz `int(data['priority'])` com `try/except` antes de comparar (helpers.py:83), enquanto `create_task` em `task_routes.py:113` compara `priority < 1 or priority > 5` sem cast — se o cliente enviar `"priority": "3"` (string), a comparação `str < int` levanta `TypeError` não capturado (o bloco `try/except` de `create_task` só envolve o `db.session.commit`, linhas 146-154), retornando um erro 500 HTML do Flask em vez do JSON padronizado da API.
Impact: manter a mesma regra em dois lugares (um deles morto) é dívida técnica que engana quem lê o código — parece que já existe validação centralizada reutilizável, mas na prática cada rota tem sua própria cópia, incluindo um bug real de type-safety exposto a qualquer client que envie prioridade como string.
Recommendation: ver padrão 9 do playbook (consolidar validação duplicada) — eliminar `process_task_data`/constantes mortas ou passar a usá-los como única fonte de validação, chamados tanto por `create_task` quanto por `update_task`.

[MEDIUM] Tratamento de erro que engole falhas (`except:` genérico)
File: routes/task_routes.py:62,137,204,236; routes/user_routes.py:130,149; routes/report_routes.py:186,207,221; utils/helpers.py:46,49,88
Description: 9 ocorrências de `except:` (ou `except Exception as e` sem log estruturado) que capturam qualquer erro e devolvem uma mensagem genérica (`'Erro interno'`, `'Erro ao atualizar'`, `'Erro ao deletar'`) sem registrar o traceback real em nenhum logger.
Impact: um erro de programação (ex: violação de constraint do banco, bug de tipo) fica indistinguível de uma falha esperada — em produção, não há como diagnosticar a causa raiz de um 500 a partir dos logs, porque a exceção original nunca é registrada.
Recommendation: ver padrão 8 do playbook (centralizar tratamento de erro em middleware único) — usar `@app.errorhandler(Exception)` com `app.logger.exception(...)` para capturar e logar o erro real uma única vez, liberando os handlers desse `try/except` repetitivo.

[MEDIUM] Uso de API deprecated (`Query.get()` e `datetime.utcnow()`)
File: routes/task_routes.py (7 ocorrências); routes/user_routes.py (4); routes/report_routes.py (3); models/task.py, models/user.py, utils/helpers.py, seed.py (22 ocorrências de utcnow no total)
Description: `Model.query.get(id)` é usado 15 vezes no projeto; ao executar o código com o SQLAlchemy 2.0.51 instalado (versão puxada por `flask-sqlalchemy==3.1.1`), essa chamada emite de fato `LegacyAPIWarning: The Query.get() method is considered legacy as of the 1.x series... becomes a legacy construct in 2.0` (confirmado rodando o app localmente). `datetime.utcnow()` é usado 22 vezes; está deprecated desde Python 3.12 em favor de `datetime.now(datetime.UTC)` (o ambiente atual roda Python 3.10, então o warning ainda não aparece aqui, mas o projeto ficará quebrado/ruidoso ao migrar para 3.12+).
Impact: dívida técnica silenciosa — o projeto já emite warnings reais contra a versão instalada do SQLAlchemy, e vai gerar mais assim que o runtime Python for atualizado; adiar a troca só aumenta o número de ocorrências a corrigir depois.
Recommendation: ver padrão 10 do playbook (substituir API deprecated pelo equivalente moderno) — trocar `Model.query.get(id)` por `db.session.get(Model, id)`, e `datetime.utcnow()` por `datetime.now(datetime.UTC)`.

[LOW] Magic numbers e strings mágicas em vez das constantes já existentes
File: routes/task_routes.py:110,113,177,182; models/task.py:39,46; models/category.py:10; routes/report_routes.py:180
Description: o intervalo de prioridade (`1`/`5`) e a lista de status válidos (`['pending', 'in_progress', 'done', 'cancelled']`) aparecem repetidos como literais em pelo menos 4 lugares, apesar de `utils/helpers.py:110-116` já definir `VALID_STATUSES`/`DEFAULT_PRIORITY` (não usados — ver apontamento MEDIUM acima). A cor padrão `'#000000'` também é repetida como literal em `models/category.py:10` e `routes/report_routes.py:180`.
Impact: mudar uma regra de negócio simples (ex: permitir prioridade até 10) exige caçar e editar cada ocorrência manualmente, com risco de esquecer uma.
Recommendation: referenciar as constantes já definidas em `utils/helpers.py` (ou centralizá-las no Model correspondente) em vez de repetir os literais.

[LOW] Nomenclatura pouco descritiva e logging via `print()`
File: routes/task_routes.py:149,153,219,234; routes/user_routes.py:83,89,147; services/notification_service.py:21,24; routes/report_routes.py:33,55,59,119,161 (variáveis `t`, `u`, `c`, `n`)
Description: eventos de negócio e erros são reportados apenas via `print()` (sem nível, timestamp ou destino configurável), e variáveis de laço usam nomes de uma letra para conceitos de domínio (`for t in tasks`, `for u in users`, `for c in categories`, `for n in self.notifications`).
Impact: em produção, `print()` não tem nível de severidade nem timestamp e some se a saída padrão não for capturada — não dá para filtrar só erros ou correlacionar com um request específico; nomes de uma letra aumentam o tempo de leitura do código para qualquer pessoa nova no projeto.
Recommendation: usar `app.logger`/`logging` configurado (nível, formato, destino) em vez de `print()`, e renomear variáveis de laço para o nome do domínio (`task`, `user`, `category`, `notification`).

================================
Total: 11 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

## Phase 3 — Refactoring Complete

```
================================
PHASE 3: REFACTORING COMPLETE
================================
New Project Structure:
.
 ├─ app.py                              # composition root (sem lógica de negócio)
 ├─ config/
 │   ├─ __init__.py
 │   └─ settings.py                     # única fonte de env vars (SECRET_KEY, DB, SMTP, debug)
 ├─ controllers/
 │   ├─ __init__.py
 │   ├─ task_controller.py
 │   ├─ user_controller.py
 │   ├─ report_controller.py
 │   └─ category_controller.py
 ├─ database.py
 ├─ .env                                 # segredos locais (gitignored)
 ├─ .env.example                         # variáveis documentadas, sem valores reais
 ├─ middlewares/
 │   ├─ __init__.py
 │   ├─ auth.py                          # JWT real: login_required / admin_required
 │   └─ error_handler.py                 # tratamento de erro centralizado
 ├─ models/
 │   ├─ __init__.py
 │   ├─ task.py                          # validate_status/priority/title, is_overdue, to_dict
 │   ├─ user.py                          # hashing seguro, validate_email/password/role
 │   └─ category.py
 ├─ routes/
 │   ├─ __init__.py
 │   ├─ task_routes.py                   # fina: só endpoint -> controller
 │   ├─ user_routes.py
 │   └─ report_routes.py
 ├─ seed.py
 ├─ services/
 │   ├─ __init__.py
 │   └─ notification_service.py          # credenciais via config/settings.py
 └─ utils/
     ├─ __init__.py
     └─ helpers.py                       # utc_now, parse_date, calculate_percentage etc.

Validation
  ✓ Application boots without errors (python app.py — sem stack trace, sem warnings)
  ✓ All endpoints respond correctly (testados via curl: /, /health, /tasks*, /users*, /login,
    /reports/*, /categories* — GET/POST/PUT/DELETE)
  ✓ 11/11 anti-patterns from the audit report resolved
================================
```

### Notas de validação

- Todos os 21 endpoints originais foram exercitados via `curl` após `python seed.py` + `python app.py`. Os fluxos legítimos (com login/token válido quando aplicável) preservam o mesmo status code e forma de resposta de antes.
- **Mudança de comportamento intencional (fixa o finding HIGH de auth decorativa)**: rotas que antes aceitavam qualquer requisição sem autenticação agora exigem `Authorization: Bearer <token>` (obtido via `POST /login`, que continua público) e retornam `401`/`403` quando ausente/inválido/sem permissão — isso é o resultado esperado de corrigir o apontamento, não uma regressão. Permanecem públicas apenas `GET /`, `GET /health`, `POST /users` (cadastro) e `POST /login`. Rotas destrutivas/administrativas (`DELETE /tasks/<id>`, `DELETE /users/<id>`, `DELETE /categories/<id>`, `PUT/DELETE /users/<id>`) exigem `role=admin`. Confirmado com `curl`: usuário comum recebe `403` nessas rotas, admin recebe `200`.
- `GET /users*`, `POST /users`, `PUT /users/<id>`, `POST /login`: confirmado por `curl` que o campo `password` (hash) não aparece mais em nenhuma resposta.
- MD5 sem salt substituído por `werkzeug.security.generate_password_hash`/`check_password_hash` — `seed.py` e `login` testados de ponta a ponta com as senhas de seed (`1234`, `abcd`, `pass`) com sucesso.
- Bug de type-safety do finding MEDIUM (`priority` como string quebrando com 500 não tratado) testado e confirmado corrigido: `POST /tasks` com `"priority": "3"` agora retorna `201` normalmente.
- N+1 eliminado: `GET /tasks` usa `joinedload`; `GET /reports/summary` e `GET /categories` usam uma query agregada por usuário/categoria em vez de uma query por item dentro do loop.
- `Model.query.get(id)` substituído por `db.session.get(Model, id)` em 100% das ocorrências — reexecutado o boot com o mesmo teste da Fase 2 e confirmado que o `LegacyAPIWarning` não aparece mais nos logs.
- `datetime.utcnow()` substituído por `utils.helpers.utc_now()` (implementado com `datetime.now(timezone.utc)`, não deprecated) em todas as 22 ocorrências, mantendo datetimes *naive* de propósito para não quebrar comparações com o que já está persistido no SQLite (que não guarda timezone) — evita trocar uma deprecation por um bug de comparação aware/naive.
- `except:` genérico removido de todos os controllers; tratamento de erro agora centralizado em `middlewares/error_handler.py` (`HTTPException` preserva status code original, `Exception` genérica vira `500` padronizado com `app.logger.exception`).
- `process_task_data()` e as 7 constantes nunca usadas em `utils/helpers.py` foram removidas; a validação de Task passou a viver em `models/task.py` (`validate_title/status/priority`), reutilizada por `create_task` e `update_task`. Mesmo padrão aplicado a `User` (`validate_email/password/role`).
- Magic numbers eliminados: `Task.MIN_PRIORITY/MAX_PRIORITY/VALID_STATUSES`, `User.VALID_ROLES/MIN_PASSWORD_LENGTH`, `Category.DEFAULT_COLOR` centralizados como constantes de classe, referenciadas por controllers e mensagens de erro.
- `print()` substituído por `current_app.logger`/`logging` em controllers e em `NotificationService`.
- Dependência nova adicionada: `pyjwt==2.8.0` (necessária para o finding de autenticação real — dentro do escopo, conforme previsto no playbook).
- Não havia suíte de testes própria no projeto (`tests/`/`test/`) — nada a migrar.
- Nenhum apontamento do relatório da Fase 2 ficou sem correção.
