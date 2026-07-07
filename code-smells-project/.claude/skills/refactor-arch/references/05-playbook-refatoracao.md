# Playbook de Refatoração (Fase 3)

Um padrão de transformação por anti-pattern do catálogo. Os exemplos usam Python/Flask e Node/Express (as stacks dos projetos-alvo), mas o **princípio** de cada transformação é o que importa — aplique a mesma ideia em qualquer linguagem. Não copie os exemplos literalmente sem adaptar aos nomes/tipos reais do projeto em mãos.

---

### 1. Separar God File em Models por domínio

**Quando aplicar**: um `models.py`/`models.js` único mistura SQL + regra de negócio de várias entidades sem relação direta entre si.

Antes (`models.py`, um arquivo para tudo):
```python
def get_produto_por_id(id): ...
def criar_pedido(usuario_id, itens): ...
def login_usuario(email, senha): ...
```

Depois (um arquivo por entidade):
```python
# models/produto.py
class Produto:
    @staticmethod
    def buscar_por_id(id): ...

# models/pedido.py
class Pedido:
    @staticmethod
    def criar(usuario_id, itens): ...

# models/usuario.py
class Usuario:
    @staticmethod
    def autenticar(email, senha): ...
```

---

### 2. Mover regra de negócio do Controller/Rota para o Model

**Quando aplicar**: um handler HTTP calcula/decide algo que depende só dos dados de uma entidade (desconto, "está atrasado?", total do pedido) — isso deveria ser um método do Model, reutilizável por qualquer controller que precise da mesma regra.

Antes (regra reimplementada dentro da rota, como em `task_routes.py`):
```python
@task_bp.route("/tasks/<int:task_id>")
def get_task(task_id):
    task = Task.query.get(task_id)
    if task.due_date and task.due_date < datetime.utcnow() and task.status not in ("done", "cancelled"):
        overdue = True
    else:
        overdue = False
    ...
```

Depois (regra centralizada no Model, chamada de qualquer lugar):
```python
# models/task.py
class Task(db.Model):
    def is_overdue(self):
        return bool(self.due_date and self.due_date < datetime.utcnow()
                    and self.status not in ("done", "cancelled"))

# controllers/task_controller.py
def get_task(task_id):
    task = Task.query.get_or_404(task_id)
    return {**task.to_dict(), "overdue": task.is_overdue()}
```

---

### 3. Parametrizar queries SQL (eliminar SQL Injection)

**Quando aplicar**: qualquer query montada por concatenação/f-string com valor vindo de request.

Antes:
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
```

Depois (bind parameters — o driver escapa o valor, não é possível injetar SQL):
```python
cursor.execute("SELECT * FROM usuarios WHERE email = ? AND senha_hash = ?", (email, senha_hash))
```

Em Node com `sqlite3`, o equivalente já é usar `?` na query com array de parâmetros (muitos projetos legados já fazem isso parcialmente — confirme que **todas** as queries usam bind parameters, não só algumas).

---

### 4. Externalizar configuração e segredos

**Quando aplicar**: `SECRET_KEY`, senha de banco, chave de API ou qualquer credencial aparece como literal de string no código.

Antes:
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
```

Depois:
```python
# config/settings.py
import os
SECRET_KEY = os.environ["SECRET_KEY"]  # falha alto e cedo se não configurado, em vez de usar um default inseguro

# app.py
from config.settings import SECRET_KEY
app.config["SECRET_KEY"] = SECRET_KEY
```
Crie um `.env.example` documentando as variáveis esperadas (sem valores reais) e garanta que `.env`/arquivos com segredo real estejam no `.gitignore`.

---

### 5. Hashing de senha seguro

**Quando aplicar**: senha em texto plano, MD5/SHA1 puro, ou hash artesanal.

Antes:
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()
```

Depois (Werkzeug já é dependência transitiva do Flask — sem lib nova):
```python
from werkzeug.security import generate_password_hash, check_password_hash

def set_password(self, pwd):
    self.password_hash = generate_password_hash(pwd)  # salgado, com custo configurável

def check_password(self, pwd):
    return check_password_hash(self.password_hash, pwd)
```
Em Node, o equivalente é trocar qualquer hash artesanal por `bcrypt`/`argon2`. **Nunca devolva o hash da senha em nenhuma resposta de API** — remova o campo do `to_dict()`/serializer.

---

### 6. Autenticação real em vez de token decorativo

**Quando aplicar**: token previsível (`"fake-jwt-" + id`) que nenhuma rota valida.

Antes:
```python
return {"token": "fake-jwt-token-" + str(user.id)}
```

Depois (assinatura real + middleware que verifica em rotas protegidas):
```python
import jwt

def gerar_token(user):
    return jwt.encode({"user_id": user.id, "role": user.role}, SECRET_KEY, algorithm="HS256")

# middlewares/auth.py
def requer_autenticacao(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return {"erro": "Não autenticado"}, 401
        return func(*args, **kwargs)
    return wrapper
```
Se adicionar uma dependência nova (`pyjwt`) não for viável no escopo da refatoração, documente claramente no relatório de auditoria que a autenticação real ficou como próximo passo — não finja que o token decorativo virou seguro só por trocar de nome.

---

### 7. Resolver queries N+1 com JOIN/eager loading

**Quando aplicar**: loop disparando uma query por item para buscar dado relacionado.

Antes (SQLAlchemy, uma query por task dentro do loop):
```python
for t in Task.query.all():
    user = User.query.get(t.user_id)  # N queries extras
```

Depois (eager loading — 1 query só):
```python
from sqlalchemy.orm import joinedload
tasks = Task.query.options(joinedload(Task.user), joinedload(Task.category)).all()
```
Em SQL cru, o equivalente é substituir o loop de subqueries por um `JOIN` único que já traz os dados relacionados na mesma consulta.

---

### 8. Centralizar tratamento de erro em middleware único

**Quando aplicar**: `try/except`/`try/catch` genérico e repetido em cada handler, ou callback que ignora `err`.

Antes:
```python
def criar_produto():
    try:
        ...
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
```

Depois (um error handler central, handlers ficam livres de try/except repetitivo):
```python
# middlewares/error_handler.py
@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.exception("Erro não tratado")
    return jsonify({"erro": "Erro interno"}), 500

# controllers/produto_controller.py
def criar_produto():
    dados = validar_produto(request.get_json())  # levanta ValueError se inválido
    return jsonify(Produto.criar(**dados)), 201
```

---

### 9. Consolidar validação duplicada

**Quando aplicar**: a mesma regra de validação copiada entre criação e atualização, já divergida.

Antes: bloco de validação colado em `criar_produto()` e `atualizar_produto()`, cada um com um subconjunto diferente das regras.

Depois (uma função/schema único, chamado dos dois lugares):
```python
def validar_produto(dados, parcial=False):
    erros = []
    if not parcial or "nome" in dados:
        if not (2 <= len(dados.get("nome", "")) <= 200):
            erros.append("Nome deve ter entre 2 e 200 caracteres")
    if not parcial or "categoria" in dados:
        if dados.get("categoria") not in CATEGORIAS_VALIDAS:
            erros.append("Categoria inválida")
    if erros:
        raise ValueError(erros)
    return dados
```

---

### 10. Substituir API deprecated pelo equivalente moderno

**Quando aplicar**: uso de método/dependência sinalizado como deprecated (ver item 11 do catálogo).

Antes (SQLAlchemy 2.x, gera `LegacyAPIWarning`):
```python
user = User.query.get(user_id)
```

Depois:
```python
user = db.session.get(User, user_id)
```
