# code-smells-project

API de E-commerce em Python/Flask, estruturada em MVC.

## Estrutura

```
config/       # configuração lida de variáveis de ambiente
models/       # 1 arquivo por entidade (produto, usuario, pedido) — dados + regra de negócio
routes/       # definição de endpoints (Blueprints), delega tudo ao controller
controllers/  # orquestra o fluxo de cada requisição
middlewares/  # autenticação JWT e tratamento de erro centralizado
database.py   # conexão SQLite por-requisição + criação/seed do schema
app.py        # composition root
```

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env
# edite .env e defina SECRET_KEY (ex: python -c "import secrets; print(secrets.token_hex(32))")
export $(cat .env | xargs)
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo (senhas com hash — ver seed em `database.py`).

## Autenticação

`POST /login` com `{"email": "...", "senha": "..."}` devolve um token JWT em `dados.token`. Envie esse token nas rotas protegidas via header `Authorization: Bearer <token>`.

Usuários de exemplo (seed): `admin@loja.com` / `admin123` (tipo `admin`), `joao@email.com` / `123456` (tipo `cliente`).
