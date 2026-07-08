# Audit Report — code-smells-project

## Phase 1 — Project Analysis

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python
Framework:     Flask 3.1.1 (+ flask-cors 5.0.1)
Dependencies:  flask, flask-cors — no ORM (raw sqlite3 driver), no auth/crypto library (no bcrypt/passlib/hashlib usage found)
Domain:        API de e-commerce (loja): catálogo de produtos, usuários/login, pedidos com itens, relatório de vendas
Architecture:  Parcialmente organizada — arquivos já separados por nome (app.py/controllers.py/models.py/database.py), mas responsabilidades vazam entre camadas (regra de negócio e validação dentro de controllers.py, SQL concatenado dentro de models.py, e rotas administrativas com acesso direto ao banco declaradas em app.py fora de qualquer controller)
Source files:  4 files analyzed (app.py, controllers.py, database.py, models.py)
DB tables:     produtos, usuarios, pedidos, itens_pedido (SQLite, arquivo loja.db, schema criado via CREATE TABLE embutido em database.py, sem migration tool)
================================
```

## Phase 2 — Architecture Audit Report

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1

Files:   4 analyzed | ~780 lines of code
```

Summary
CRITICAL: 5 | HIGH: 3 | MEDIUM: 2 | LOW: 2

Findings

[CRITICAL] SQL Injection generalizada (concatenação de strings em queries)
File: models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140-166, 174-192, 206-224, 279-281, 289-297
Description: Praticamente toda função de acesso a dados em `models.py` monta a query SQL concatenando strings com valores vindos direto da requisição, em vez de usar bind parameters — ex.: `cursor.execute("SELECT * FROM produtos WHERE id = " + str(id))` (linha 28) ou `"INSERT INTO produtos (...) VALUES ('" + nome + "', ...)"` (linhas 47-50). O caso mais grave é `login_usuario` (linhas 109-111): `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"`. Um payload de `email` igual a `admin@loja.com' -- ` faz a query virar `SELECT * FROM usuarios WHERE email = 'admin@loja.com' -- ' AND senha = ''` — o `--` comenta o resto da cláusula SQL e a senha deixa de ser verificada, autenticando como admin sem conhecer a senha. O mesmo padrão se repete em `criar_produto`, `atualizar_produto`, `deletar_produto`, `get_usuario_por_id`, `criar_usuario`, `criar_pedido`, `get_pedidos_usuario`, `get_todos_pedidos`, `atualizar_status_pedido` e `buscar_produtos` (este último é explorável via query string GET, ex.: `/produtos/busca?q=x' OR '1'='1`, sem nem precisar de um body).
Impact: Qualquer cliente HTTP não autenticado pode ler, alterar ou apagar dados arbitrários no banco, e — via `login_usuario` — se autenticar como qualquer usuário (inclusive `admin@loja.com`) sem saber a senha. É a vulnerabilidade mais severa do projeto porque atinge login, catálogo e pedidos ao mesmo tempo.
Recommendation: ver padrão 3 do playbook (`05-playbook-refatoracao.md`) — reescrever todas as queries com bind parameters (`?` + tupla de valores), sem exceção. Ao mover cada função para o Model correspondente na Fase 3, cada uma já nasce parametrizada.

[CRITICAL] Backdoor de execução de SQL arbitrário em /admin/query
File: app.py:59-78
Description: A rota `POST /admin/query` lê `dados.get("sql", "")` do corpo da requisição e executa diretamente via `cursor.execute(query)` (linha 69), devolvendo o resultado se for `SELECT` ou fazendo commit caso contrário. Não há nenhuma verificação de autenticação/autorização na rota nem qualquer allowlist de comandos.
Impact: Isso é um backdoor completo do banco de dados exposto publicamente — um atacante pode enviar `{"sql": "SELECT * FROM usuarios"}` para exfiltrar credenciais, `{"sql": "UPDATE usuarios SET tipo='admin' WHERE email='atacante@x.com'"}` para se auto-promover a admin, ou `{"sql": "DELETE FROM pedidos"}` para destruir dados — sem precisar de nenhuma das outras vulnerabilidades acima.
Recommendation: ver padrão 3 do playbook (nunca aceitar SQL cru do cliente). O padrão correto é remover este endpoint da API pública; se algum caso de uso administrativo legítimo existir, ele deveria expor operações específicas e parametrizadas (não uma query livre) atrás de autenticação real (padrão 6).

[CRITICAL] Credenciais hardcoded (SECRET_KEY) expostas publicamente
File: app.py:7-8; controllers.py:264-292 (especialmente 285, 288-289)
Description: `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"` está craveado no código-fonte (app.py:7), junto com `DEBUG = True` (app.py:8). Para piorar, o endpoint `GET /health` (controllers.py:264-292) devolve esse mesmo valor no corpo da resposta JSON: `"secret_key": "minha-chave-super-secreta-123"` (linha 289), junto com `"debug": True` (linha 288) — sem nenhuma autenticação para acessar `/health`.
Impact: `SECRET_KEY` é usada pelo Flask para assinar sessões/cookies; hardcoded já é ruim (não pode variar por ambiente, vaza se o repositório vazar), mas devolvê-la em um endpoint público de "health check" significa que qualquer visitante anônimo consegue a chave com um único `curl http://.../health` — o suficiente para forjar cookies de sessão assinados pela aplicação.
Recommendation: ver padrão 4 do playbook — mover `SECRET_KEY` para variável de ambiente (`os.environ["SECRET_KEY"]`), remover `secret_key` e `debug` do payload de `/health` (um health check deve responder só com status operacional, nunca configuração sensível), e desligar `DEBUG` fora de ambiente de desenvolvimento.

[CRITICAL] Senhas armazenadas, comparadas e expostas em texto plano
File: database.py:75-79 (seed); models.py:72-87, 105-131
Description: A tabela `usuarios` guarda a senha como está (`database.py:75-79` insere `"admin123"`, `"123456"`, `"senha123"` literalmente). `criar_usuario` (models.py:122-131) insere o valor de `senha` sem qualquer hashing, e `login_usuario` (models.py:105-120) compara `WHERE ... AND senha = '<valor>'` diretamente. Além disso, `get_todos_usuarios` (models.py:72-87, linha 83) devolve o campo `"senha": row["senha"]` no dicionário retornado, e o controller `listar_usuarios` (controllers.py:128-134) repassa isso sem filtrar — ou seja, `GET /usuarios` devolve a senha em texto plano de todos os usuários para qualquer chamador, sem autenticação.
Impact: Um vazamento de banco (ou simplesmente um `GET /usuarios`, que não exige login) expõe a senha real de todos os usuários — como pessoas costumam reutilizar senha entre serviços, isso compromete contas dos usuários fora da própria aplicação também.
Recommendation: ver padrão 5 do playbook — usar `werkzeug.security.generate_password_hash`/`check_password_hash` (já vem com o Flask, sem dependência nova) para armazenar e verificar senha, e remover o campo `senha`/hash de qualquer resposta serializada (`get_todos_usuarios`, `get_usuario_por_id`).

[CRITICAL] God File: camadas de dados/negócio/rotas misturadas em um único arquivo
File: models.py:1-314; app.py:1-88 (rotas administrativas em 47-78 fora de qualquer controller)
Description: `models.py` concentra SQL cru + regra de negócio de 4 entidades sem relação direta (`produtos`, `usuarios`, `pedidos`, `itens_pedido`) no mesmo arquivo, sem nenhuma camada de acesso a dados abstraída entre a query e a regra de negócio (ex.: `criar_pedido`, linhas 133-169, calcula total, valida estoque e faz 3 tipos de INSERT/UPDATE diferentes na mesma função). Seria impossível testar a regra "pedido sem estoque suficiente é rejeitado" sem subir um banco SQLite de verdade. Em paralelo, `app.py` registra rotas (linhas 11-30) mas também define duas rotas administrativas (`reset-db` e `admin/query`, linhas 47-78) que acessam `get_db()` diretamente, pulando por completo a camada de controller/model que o resto da aplicação usa.
Impact: Qualquer mudança de schema ou regra de negócio arrisca efeito colateral em entidades não relacionadas por estarem no mesmo arquivo; a ausência de separação entre camadas nas rotas administrativas de `app.py` significa que o padrão arquitetural do projeto é inconsistente — parte do código segue Controller→Model, parte pula direto para o banco.
Recommendation: ver padrão 1 do playbook — dividir `models.py` em um Model por entidade (`models/produto.py`, `models/usuario.py`, `models/pedido.py`); mover a lógica das rotas `/admin/*` para controllers dedicados que chamam os Models correspondentes, eliminando o acesso direto a `get_db()` a partir de `app.py`.

[HIGH] Autenticação e autorização inexistentes em toda a API
File: app.py:11-30, 47-57; controllers.py:167-186; database.py:32 (campo `tipo` nunca verificado)
Description: `login` (controllers.py:167-186) apenas confere email/senha e devolve os dados do usuário — nenhum token, cookie de sessão ou JWT é emitido. Nenhuma das ~19 rotas registradas em `app.py` (incluindo `DELETE /produtos/<id>`, `PUT /pedidos/<id>/status`, `GET /relatorios/vendas`, e principalmente `POST /admin/reset-db`, linhas 47-57) exige qualquer credencial para ser chamada. A tabela `usuarios` tem uma coluna `tipo` (database.py:32, valores `'cliente'`/`'admin'`) que sugere controle de papel, mas nenhuma rota em `app.py` ou `controllers.py` jamais lê ou compara esse campo.
Impact: Qualquer pessoa na rede, sem se autenticar, pode listar/criar/editar/apagar produtos, ver todos os pedidos e usuários de todos os clientes, e resetar o banco de dados inteiro (`/admin/reset-db` apaga todas as tabelas sem confirmação). O conceito de "admin" existe só no schema, nunca é aplicado.
Recommendation: ver padrão 6 do playbook — emitir um token assinado (JWT) no login e criar um middleware/decorator `requer_autenticacao` (e uma variante `requer_admin` checando `tipo == 'admin'`) aplicado a todas as rotas que modificam dados ou expõem dados de terceiros, especialmente as `/admin/*`.

[HIGH] Lógica de negócio e efeitos colaterais dentro do Controller
File: controllers.py:208-210, 237-252
Description: `criar_pedido` (controllers.py:208-210) dispara "notificações" via `print("ENVIANDO EMAIL...")`/`print("ENVIANDO SMS...")`/`print("ENVIANDO PUSH...")` diretamente no controller, misturando a formatação da resposta HTTP com orquestração de notificação. Em `atualizar_status_pedido` (linhas 237-252), quando o novo status é `"cancelado"`, a linha 250 imprime `"...cancelado. Devolver estoque."` — mas nenhum código, em nenhum lugar do projeto, de fato devolve o estoque reservado ao produto quando um pedido é cancelado; o log afirma uma ação que nunca acontece.
Impact: Além de violar a separação de camadas (o Controller deveria só traduzir HTTP↔domínio, não decidir "quando disparar notificação"), existe aqui um bug funcional real: cancelar um pedido reduz o estoque para sempre (o estoque foi debitado na criação do pedido em `models.py:163-166` e nunca é restaurado), então o log é enganoso e o inventário do sistema fica incorreto após qualquer cancelamento.
Recommendation: ver padrão 2 do playbook — mover a decisão de "o que fazer quando o status muda" para um método do Model (`Pedido.atualizar_status`), implementando de fato a devolução de estoque no caminho de cancelamento; e mover o disparo de notificação para um serviço dedicado (mesmo que ainda simulado via logger, não via `print` espalhado no controller).

[HIGH] Estado global mutável compartilhado (conexão de banco)
File: database.py:4, 7-10
Description: `db_connection` (linha 4) é uma variável de módulo, inicializada como `None` e populada por `get_db()` (linhas 7-10) na primeira chamada — todas as requisições subsequentes, de qualquer thread, reutilizam esse mesmo objeto de conexão global. O próprio código sinaliza ciência do uso multi-thread (`check_same_thread=False`, linha 10), mas não há nenhum lock/semáforo protegendo o acesso concorrente ao cursor/conexão compartilhados.
Impact: Sob carga concorrente (múltiplas requisições simultâneas), operações de leitura/escrita na mesma conexão SQLite podem colidir, causar `sqlite3.OperationalError: database is locked` ou resultados inconsistentes entre requisições que não deveriam se conhecer — um sintoma clássico de estado global mutável em um servidor multi-thread.
Recommendation: não há um padrão numerado específico no playbook para pooling de conexão, mas o princípio do padrão 1 (Model por entidade, dono da própria persistência) se aplica: abrir uma conexão por requisição (ex. `flask.g` + `teardown_appcontext` fechando a conexão ao fim de cada request) em vez de reusar uma conexão de módulo compartilhada indefinidamente.

[MEDIUM] Validação duplicada e divergente entre criação e atualização de produto
File: controllers.py:24-62 (criar_produto) vs. 64-96 (atualizar_produto)
Description: Os blocos de validação de `criar_produto` e `atualizar_produto` são quase idênticos (copiados e colados), mas divergiram: `criar_produto` valida `len(nome) < 2`/`> 200` (linhas 47-50) e checa `categoria` contra a lista `categorias_validas` (linhas 52-54); `atualizar_produto` não repete nenhuma das duas checagens.
Impact: Um produto que seria rejeitado na criação (nome de 1 caractere, ou categoria `"xyz"` fora da lista permitida) é aceito silenciosamente em uma atualização (`PUT /produtos/<id>`) — prova concreta de que a regra de negócio "categoria deve ser uma das válidas" não é realmente garantida pelo sistema, só pela metade dos caminhos que deveriam aplicá-la.
Recommendation: ver padrão 9 do playbook — extrair uma função/schema único de validação (`validar_produto(dados, parcial=False)`) chamado tanto por `criar_produto` quanto por `atualizar_produto`, eliminando a divergência.

[MEDIUM] Queries N+1 ao montar pedidos com itens
File: models.py:171-201 (get_pedidos_usuario), 203-233 (get_todos_pedidos)
Description: Ambas as funções, para cada pedido retornado pela query principal, abrem um segundo cursor para buscar seus itens (`cursor2`, linha 188/220) e, para cada item, um terceiro cursor para buscar o nome do produto (`cursor3`, linha 191-192/223-224) — uma query adicional por pedido e mais uma por item, em vez de um `JOIN` único. As duas funções são também praticamente idênticas (código duplicado, ~30 linhas repetidas quase na íntegra).
Impact: Para uma listagem com 50 pedidos de 3 itens cada, isso emite ~1 + 50 + 150 = 201 queries em vez de 1, degradando a performance proporcionalmente ao volume de dados — e qualquer correção de bug nessa lógica precisa ser feita em dois lugares por causa da duplicação.
Recommendation: ver padrão 7 do playbook — substituir os cursores aninhados por uma única query com `JOIN` entre `pedidos`, `itens_pedido` e `produtos` (ou `WHERE pedido_id IN (...)` para buscar todos os itens de uma vez), e consolidar as duas funções quase-idênticas em uma só parametrizada por filtro opcional de `usuario_id`.

[LOW] Magic numbers em regras de negócio
File: controllers.py:47-50; models.py:257-262
Description: Limites de validação de nome de produto (`2`, `200` caracteres, controllers.py:47-50) e as faixas de desconto do relatório de vendas (`10000`, `5000`, `1000` de faturamento e `0.1`/`0.05`/`0.02` de desconto, models.py:257-262) aparecem como literais soltos no meio do código, sem constante nomeada.
Impact: Alterar uma regra de desconto exige caçar o literal no meio da função em vez de mudar um único ponto nomeado; também dificulta entender, só lendo o código, o que cada número representa sem reconstruir o contexto da regra de negócio.
Recommendation: extrair constantes nomeadas no topo do Model correspondente (ex. `NOME_MIN_LEN = 2`, `NOME_MAX_LEN = 200`, `FAIXAS_DESCONTO = [(10000, 0.10), (5000, 0.05), (1000, 0.02)]`) — o playbook não tem um padrão numerado específico para isso, mas o princípio é o mesmo do padrão 9 (regra de negócio centralizada em um único lugar nomeado).

[LOW] Logging via print() em vez de logger configurável
File: app.py:56, 83-86; controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250
Description: Todo evento de negócio ou erro (criação/deleção de produto, login bem-sucedido/falho, erros capturados, boot do servidor, reset do banco) é reportado via `print()` cru, sem nível (`info`/`warning`/`error`), timestamp ou destino configurável — mais de uma dúzia de ocorrências espalhadas por `app.py` e `controllers.py`.
Impact: Em produção, não há como filtrar por severidade, redirecionar para um agregador de logs, ou desligar logs verbosos sem editar código — e `print()` em `stdout` se mistura com qualquer outra saída do processo, dificultando observabilidade real do sistema.
Recommendation: o playbook não tem um padrão dedicado a logging, mas o princípio do padrão 8 (centralizar preocupação transversal) se aplica — substituir os `print()` por `logging.getLogger(__name__)` configurado uma vez em `app.py`, com nível apropriado por ambiente.

================================
Total: 12 findings
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
├── app.py                        # composition root: cria a app, registra config/blueprints/middlewares
├── config/
│   ├── __init__.py
│   └── settings.py                # SECRET_KEY/DEBUG/DB_PATH lidos de variáveis de ambiente
├── database.py                    # schema + seed (hash de senha) + conexão SQLite por-requisição (flask.g)
├── models/
│   ├── __init__.py
│   ├── produto.py                 # dados + validação + regras do catálogo
│   ├── usuario.py                 # dados + hashing/verificação de senha
│   └── pedido.py                  # dados + estoque + relatório de vendas
├── routes/
│   ├── __init__.py
│   ├── main_routes.py              # GET /, GET /health
│   ├── produto_routes.py           # /produtos*
│   ├── usuario_routes.py           # /usuarios*, /login
│   ├── pedido_routes.py            # /pedidos*, /relatorios/vendas
│   └── admin_routes.py             # /admin/reset-db
├── controllers/
│   ├── __init__.py
│   ├── main_controller.py
│   ├── produto_controller.py
│   ├── usuario_controller.py
│   ├── pedido_controller.py
│   └── admin_controller.py
├── middlewares/
│   ├── __init__.py
│   ├── auth.py                     # JWT: gerar_token, login_required, admin_required
│   └── error_handler.py            # ValueError→400, 404→JSON, Exception→500 (centralizado)
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md

Validation
  ✓ Application boots without errors (nenhum traceback de import/boot no log do servidor)
  ✓ All endpoints respond correctly (18/18 rotas restantes exercitadas via curl, ver detalhe abaixo)
  ✓ 12/12 anti-patterns from the audit report resolved
================================
```

### Detalhe da validação

Servidor subido em background (`SECRET_KEY=... python3 app.py &`), banco recriado do zero (`rm loja.db`). Todas as 18 rotas remanescentes (das 19 originais — `/admin/query` foi removida por design, ver apontamento CRITICAL #2) foram exercitadas via `curl`, confirmando o mesmo formato/contrato de resposta de antes nos casos de sucesso, além das correções de segurança:

- `GET /`, `GET /health`, `GET /produtos`, `GET /produtos/busca`, `GET /produtos/<id>` — 200, mesma forma de resposta; `/health` não vaza mais `secret_key`/`debug`.
- `POST /login` com a tentativa de bypass de SQL Injection (`email = "admin@loja.com' -- "`) agora retorna `401` em vez de autenticar como admin — confirma a correção do apontamento CRITICAL #1.
- `GET /usuarios` sem token → `401` (antes: `200` com senhas em texto plano); com token de admin → `200` sem o campo `senha`; com token de cliente → `403`.
- `GET /usuarios/<id>` e `GET /pedidos/usuario/<id>` aplicam a regra "dono do recurso ou admin" (200 para o próprio usuário, 403 para outro usuário sem ser admin).
- `POST /produtos` sem token → `401`; com token de admin → `201`; `PUT /produtos/<id>` com categoria inválida agora retorna `400` também na atualização (antes esse caso vazava sem validação — confirma a correção do apontamento MEDIUM #9).
- `POST /pedidos` cria pedido e decrementa estoque corretamente (`estoque` de 50→47 para quantidade 3); tentar criar pedido para outro `usuario_id` sem ser admin → `403`.
- `PUT /pedidos/<id>/status` para `"cancelado"` agora devolve o estoque de fato (`estoque` voltou de 47→50), e uma segunda chamada de cancelamento não credita o estoque de novo (idempotência) — confirma a correção do apontamento HIGH #7.
- `POST /admin/query` → `404` (rota removida, backdoor eliminado — apontamento CRITICAL #2).
- `POST /admin/reset-db` sem token → `401`; com token de cliente → `403`; com token de admin → `200`, e o comportamento pós-reset (sem re-seed automático) é idêntico ao original.
- `POST /usuarios` (registro) → `201`; `GET /produtos/9999` (inexistente) → `404`.

Nenhum traceback apareceu no log do servidor durante toda a sessão de testes. O projeto não tinha suíte de testes própria neste momento (removida antes desta auditoria, conforme histórico do git), então não havia testes automatizados para rodar.

### Apontamentos resolvidos (12/12)

| # | Apontamento | Status |
|---|---|---|
| 1 | [CRITICAL] SQL Injection generalizada | ✅ Resolvido — todas as queries em `models/*.py` usam bind parameters (`?`) |
| 2 | [CRITICAL] Backdoor `/admin/query` | ✅ Resolvido — endpoint removido |
| 3 | [CRITICAL] Credenciais hardcoded (SECRET_KEY) | ✅ Resolvido — `config/settings.py` lê de env var; removido do `/health` |
| 4 | [CRITICAL] Senhas em texto plano | ✅ Resolvido — `werkzeug.security` (hash+salt); campo `senha` nunca mais serializado |
| 5 | [CRITICAL] God File | ✅ Resolvido — `models/produto.py`, `usuario.py`, `pedido.py`; rotas admin movidas para controller próprio |
| 6 | [HIGH] Autenticação/autorização inexistente | ✅ Resolvido — JWT real + `login_required`/`admin_required` + regra dono-ou-admin |
| 7 | [HIGH] Lógica de negócio/efeitos colaterais no Controller | ✅ Resolvido — devolução de estoque implementada de fato no Model; notificação via `logger`, não `print` |
| 8 | [HIGH] Estado global mutável (conexão de banco) | ✅ Resolvido — conexão por-requisição via `flask.g` + `teardown_appcontext` |
| 9 | [MEDIUM] Validação duplicada e divergente | ✅ Resolvido — `produto.validar()` único, chamado por `criar` e `atualizar` |
| 10 | [MEDIUM] Queries N+1 | ✅ Resolvido — `pedido.py` usa `JOIN` único em vez de cursores aninhados |
| 11 | [LOW] Magic numbers | ✅ Resolvido — `NOME_MIN_LEN`/`NOME_MAX_LEN`/`CATEGORIAS_VALIDAS`/`FAIXAS_DESCONTO`/`STATUSES_VALIDOS` nomeados |
| 12 | [LOW] Logging via `print()` | ✅ Resolvido — `app.logger`/`current_app.logger` em todo o projeto |
