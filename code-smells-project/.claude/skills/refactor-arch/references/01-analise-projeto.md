# Heurísticas de Análise de Projeto (Fase 1)

Este documento ensina a levantar rapidamente o "raio-x" de qualquer projeto de backend — linguagem, framework, banco de dados, domínio e nível de organização arquitetural — sem depender de já conhecer a stack de antemão. A ideia é sempre partir de **evidências no próprio repositório** (arquivos de manifesto, imports, nomes de tabela/rota) em vez de assumir uma stack específica.

Use os comandos abaixo como ponto de partida (ajuste os padrões conforme o que for encontrado) e trate esta lista como exemplos ilustrativos, não uma lista fechada — o princípio (manifesto → imports → schema → nomes de domínio) generaliza para qualquer linguagem, mesmo uma não listada aqui.

## 1. Detectar linguagem

Procure arquivos de manifesto de dependências na raiz do projeto — eles são o sinal mais confiável:

| Arquivo encontrado | Linguagem provável |
|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py` | Python |
| `package.json` | JavaScript/TypeScript (Node.js) |
| `pom.xml`, `build.gradle` | Java/Kotlin |
| `Gemfile` | Ruby |
| `go.mod` | Go |
| `composer.json` | PHP |
| `*.csproj`, `*.sln` | C#/.NET |

Se nenhum manifesto existir, conte a extensão predominante entre os arquivos-fonte (`find . -name "*.py" -o -name "*.js" ... | sed 's/.*\.//' | sort | uniq -c | sort -rn`).

## 2. Detectar framework

Abra o manifesto encontrado e procure por dependências conhecidas. Também vale grepar o código por imports/requires características, já que às vezes o manifesto está desatualizado:

| Sinal no manifesto ou código | Framework |
|---|---|
| `flask` no requirements/import `from flask import Flask` | Flask |
| `django` no requirements/`django.db.models` | Django |
| `fastapi` no requirements/`from fastapi import FastAPI` | FastAPI |
| `"express"` no package.json/`require('express')` ou `import express` | Express |
| `"next"` no package.json | Next.js |
| `"@nestjs/core"` no package.json | NestJS |
| `spring-boot-starter` no pom.xml/`@RestController` | Spring Boot |
| `rails` no Gemfile | Ruby on Rails |
| `laravel/framework` no composer.json | Laravel |

Pegue também a **versão declarada** da dependência principal (ex: `flask==3.1.1`) para citar na Fase 1 — isso ajuda a cruzar com o catálogo de APIs deprecated (`02-catalogo-anti-patterns.md`).

## 3. Detectar banco de dados

Procure por três tipos de evidência, na seguinte ordem de confiabilidade:

1. **Driver/ORM importado**: `sqlite3`, `psycopg2`/`asyncpg` (Postgres), `pymysql`/`mysql2` (MySQL), `sqlalchemy`/`flask_sqlalchemy`, `mongoose`/`pymongo` (MongoDB), `sequelize`, `prisma`.
2. **Arquivos de dados/schema**: presença de `*.db`/`*.sqlite`, pasta `migrations/`, arquivo `schema.prisma`, `docker-compose.yml` com serviço `postgres`/`mysql`/`mongo`.
3. **Comandos DDL embutidos no código**: `grep -rn "CREATE TABLE" .` — muito comum em projetos legados que não usam migration tool nenhuma (o banco é criado "na unha" dentro do próprio app).

Liste as tabelas/coleções encontradas (via `CREATE TABLE`, classes de Model ORM, ou schemas) — isso alimenta diretamente a detecção de domínio no próximo passo.

## 4. Detectar o domínio da aplicação

O domínio raramente está escrito em algum lugar explícito — infira a partir de:

- **Nomes de tabelas/entidades/models** (ex: `produtos`, `pedidos`, `usuarios` → e-commerce; `tasks`, `categories` → gerenciador de tarefas; `courses`, `enrollments`, `payments` → LMS/cursos).
- **Nomes de rotas/endpoints** (ex: `/checkout`, `/produtos/busca`, `/relatorios/vendas`).
- **README existente** — se houver, geralmente descreve o propósito em uma frase; use como confirmação, não como única fonte (READMEs de projetos legados podem estar desatualizados).

## 5. Mapear a arquitetura atual

Rode `find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" \) | grep -v node_modules` para listar os arquivos-fonte e classifique o nível de organização em um destes três baldes:

- **Monolítico / sem camadas**: toda a lógica (rotas + regras de negócio + acesso a dados) cabe em poucos arquivos na raiz (tipicamente ≤ 5), sem nenhuma pasta `models/`, `controllers/`, `routes/`.
- **Parcialmente organizado**: já existem pastas como `models/`, `routes/`, `services/`, `utils/`, mas isso **não garante** que as responsabilidades estejam corretas por dentro — é comum encontrar regra de negócio pesada dentro de uma rota mesmo com essa separação de pastas existindo. Não assuma que "tem pasta = está bem arquitetado"; a Fase 2 é quem vai confirmar ou refutar isso.
- **Já em MVC (ou próximo disso)**: camadas separadas e responsabilidades majoritariamente corretas. Ainda assim, rode a Fase 2 normalmente — pode haver violações pontuais (ex: uma rota específica fazendo query direta) mesmo em projetos com boa estrutura geral.

Conte o número de arquivos-fonte analisados (excluindo dependências como `node_modules/`, `venv/`, `__pycache__/`) — esse número entra no resumo da Fase 1 e deve bater com a realidade do projeto.

## 6. Formato do resumo da Fase 1

Ao final, imprima um resumo estruturado assim (adapte os campos ao que for aplicável):

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem detectada>
Framework:     <framework + versão, se encontrada>
Dependencies:  <dependências relevantes para a auditoria, ex: libs de auth/crypto/orm>
Domain:        <domínio inferido, em 1 frase>
Architecture:  <Monolítica / Parcialmente organizada / Já em MVC> — <1 frase justificando>
Source files:  <N> files analyzed
DB tables:     <tabelas/coleções encontradas>
================================
```
