# Catálogo de Anti-patterns (Fase 2)

Cada entrada tem: **sinais de detecção** (o que procurar, de forma acionável — não "código ruim", e sim o padrão textual/estrutural exato) e a **severidade** a aplicar. Use a escala abaixo, que é a mesma para todo o processo de auditoria:

| Severidade | Critério |
|---|---|
| **CRITICAL** | Falha grave de arquitetura/segurança: impede funcionamento correto, expõe dados sensíveis, ou quebra totalmente a separação de responsabilidades |
| **HIGH** | Forte violação de MVC/SOLID: lógica de negócio pesada no Controller, acoplamento forte sem DI, estado global mutável |
| **MEDIUM** | Padronização, duplicação de código, gargalo de performance moderado |
| **LOW** | Legibilidade, nomenclatura ruim, magic numbers |

A mesma classe de problema pode variar de severidade dependendo do contexto (ex: um `except` genérico que engole um erro de validação é MEDIUM; um que engole uma falha de pagamento sem avisar ninguém é HIGH) — use o critério acima com julgamento, não como tabela de lookup cega.

Esta lista cobre os anti-patterns mais comuns encontrados na prática, mas **não é exaustiva**. Se encontrar algo que viola claramente MVC/SOLID mas não se encaixa em nenhuma entrada abaixo, classifique-o mesmo assim usando a tabela de severidade acima e documente com a mesma qualidade de detalhe (arquivo, linha, descrição, impacto, recomendação).

---

### 1. [CRITICAL] God Class / God File

**Sinais de detecção**: um único arquivo ou classe concentra simultaneamente (a) definição de schema/conexão de banco, (b) definição de rotas HTTP, e (c) regras de negócio não-triviais (cálculos, orquestração multi-tabela). Também conta um único arquivo de "models" que mistura SQL cru + validação + formatação de múltiplos domínios distintos (ex: produtos, usuários e pedidos no mesmo `models.py`). Pergunta-teste: "se eu quisesse testar só a regra de negócio X isoladamente, eu conseguiria sem subir banco/servidor?" — se a resposta é não, é God Class.

### 2. [CRITICAL] SQL Injection / Injeção de comando

**Sinais de detecção**: strings SQL montadas por concatenação ou f-string/template literal com uma variável vinda de `request`/input do usuário — `"SELECT ... WHERE id = " + id`, `` `SELECT * FROM x WHERE y = '${input}'` ``, `.format()`/`%` com valor de request. O mesmo padrão com `os.system()`, `subprocess` com `shell=True`, ou `eval()`/`exec()` recebendo input do usuário é command injection — mesma severidade. Um endpoint que aceita uma query SQL inteira do corpo da requisição e executa direto (`cursor.execute(request.json["sql"])`) é o caso extremo: um backdoor de fato, não apenas uma injeção pontual.

### 3. [CRITICAL] Credenciais e segredos hardcoded

**Sinais de detecção**: literais de string para `SECRET_KEY`, senha de banco, chave de API, usuário/senha de SMTP, etc. diretamente no código-fonte (não lidos de variável de ambiente). Severidade sobe ainda mais se esse segredo também vazar através de algum endpoint (`/health`, `/debug`, `/config`) que devolve o valor no corpo da resposta — isso combina "hardcoded" com "exposto publicamente" no mesmo apontamento.

### 4. [CRITICAL] Senhas sem hashing seguro

**Sinais de detecção**: senha comparada ou armazenada em texto plano (`WHERE senha = '<valor>'`, coluna guardando o valor exatamente como veio do request); ou uso de `MD5`/`SHA1` puro sem salt (`hashlib.md5(pwd).hexdigest()`); ou uma função de "hash" artesanal que não é um algoritmo criptográfico reconhecido (ex: repetir/truncar Base64). Teste rápido: duas entradas parecidas (mesmo prefixo, por exemplo) produzem saídas correlacionadas ou idênticas? Se sim, não é hashing seguro de verdade.

### 5. [HIGH] Autenticação/Autorização decorativa

**Sinais de detecção**: um "token" de sessão que é apenas um ID ou string previsível concatenada (`"token-" + user.id`, `"fake-jwt-" + id`) sem assinatura nem verificação em nenhuma rota; ou um conceito de papel/role (`is_admin()`, campo `role`) que existe no Model mas nenhuma rota realmente o checa antes de operações sensíveis (deletar, editar dados de terceiros, relatórios financeiros). O teste decisivo: existe ALGUMA rota que rejeita uma requisição por falta/invalidez de autenticação? Se a resposta é não para o sistema inteiro, é autenticação decorativa.

### 6. [HIGH] Lógica de negócio pesada em Controllers/Rotas (ou espalhada por várias camadas)

**Sinais de detecção**: cálculos de domínio (descontos, totais, regras de aprovação), orquestração de múltiplas tabelas, ou uma mesma regra (ex: "pedido está atrasado?") reimplementada em vários handlers em vez de centralizada em um Model/Service e reutilizada. Se o Model já expõe um método para a regra (ex: `Task.is_overdue()`) mas as rotas reescrevem o mesmo `if/else` na mão, isso conta tanto como este item quanto como duplicação de lógica (item 9) — cite os dois.

### 7. [HIGH] Estado global mutável compartilhado

**Sinais de detecção**: variável de módulo (não dentro de uma classe/request) que é escrita por múltiplos handlers concorrentes (`let cache = {}`, `global counter`) sem nenhum mecanismo de sincronização ou escopo por requisição. Isso vira condição de corrida sob carga e acopla partes do sistema que não deveriam se conhecer.

### 8. [MEDIUM] Queries N+1

**Sinais de detecção**: um loop (`for`/`forEach`) que dispara uma nova query de banco a cada iteração para buscar dados relacionados (ex: para cada pedido, uma query pra buscar seus itens; para cada item, outra query pra buscar o nome do produto) em vez de usar `JOIN`, `include`/eager loading do ORM, ou uma única query com `WHERE id IN (...)`. Sinal inequívoco em SQLAlchemy/Django ORM: `Model.query.get(id)` ou `Model.objects.get(id=x)` dentro de um loop sobre outra coleção.

### 9. [MEDIUM] Validação duplicada e divergente

**Sinais de detecção**: o mesmo conjunto de regras de validação (tamanho de campo, formato, valores permitidos) copiado e colado entre o handler de criação e o de atualização — e, na prática, divergiu: uma das cópias esqueceu uma regra que a outra tem. Prova concreta: um dado rejeitado na criação é aceito silenciosamente na atualização (ou vice-versa).

### 10. [MEDIUM] Tratamento de erro que engole falhas

**Sinais de detecção**: `except:` genérico (Python) ou callback que recebe `err` e não o verifica antes de seguir (Node) — a falha real desaparece e vira uma mensagem genérica ("Erro interno") ou, pior, a operação é reportada como sucesso mesmo tendo falhado.

### 11. [MEDIUM] Uso de APIs, métodos ou dependências deprecated

**Sinais de detecção** (exemplos concretos — generalize o princípio para o que encontrar):

| Stack | API deprecated | Substituir por |
|---|---|---|
| SQLAlchemy 2.x | `Model.query.get(id)` (gera `LegacyAPIWarning`) | `db.session.get(Model, id)` |
| Python 3.12+ | `datetime.datetime.utcnow()` | `datetime.datetime.now(datetime.UTC)` |
| Node.js | pacote `request` (descontinuado desde 2020) | `fetch` nativo (Node ≥ 18) ou `axios`/`undici` |
| Node.js | `new Buffer(...)` | `Buffer.from(...)` |
| Express 4.16+ | dependência separada `body-parser` | `express.json()` / `express.urlencoded()` embutidos |
| Qualquer stack | runtime/major version end-of-life (Python 2, Node < 18, framework major desatualizado) | atualizar para a versão LTS/estável atual |

Rode a aplicação (ou pelo menos importe os módulos) durante a Fase 1/2 e preste atenção a `DeprecationWarning`/`LegacyAPIWarning` no output — eles apontam exatamente essas ocorrências.

### 12. [LOW] Magic numbers / strings mágicas

**Sinais de detecção**: literais numéricos ou de string que codificam uma regra de negócio (limiares de desconto, tamanhos mínimos/máximos, status permitidos) espalhados no meio do código sem uma constante nomeada — especialmente quando o mesmo valor se repete em mais de um lugar.

### 13. [LOW] Nomenclatura pouco descritiva e logging via `print`/`console.log`

**Sinais de detecção**: variáveis de uma letra para conceitos de domínio (`u`, `e`, `p`, `cc`); eventos de negócio ou erros reportados só via `print()`/`console.log()` em vez de um logger configurável (sem nível, timestamp ou destino estruturado).
