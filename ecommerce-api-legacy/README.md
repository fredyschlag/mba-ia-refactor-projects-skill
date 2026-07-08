# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express, estruturada em MVC (`models/`, `controllers/`, `routes/`).

## Como rodar

```bash
npm install
npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória e já carrega seeds automaticamente no boot. Configuração e segredos vêm de variáveis de ambiente (ver `.env.example`); um `.env` com valores de desenvolvimento já está incluso para rodar localmente sem configuração extra.

As rotas `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem o header `x-admin-key` (valor em `.env`/`ADMIN_API_KEY`). O checkout (`POST /api/checkout`) valida a senha do usuário quando o e-mail já existe.

Exemplos de requisições estão em `api.http`.
