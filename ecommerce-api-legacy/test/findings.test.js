// Provas de conceito automatizadas para os 7 achados documentados na Análise Manual
// (README.md do repositório, seção "Projeto 2 — ecommerce-api-legacy").
//
// Usa apenas o test runner nativo do Node (node:test) e fetch nativo (Node >= 18),
// sem dependências extras. Cada teste sobe um AppManager + Express isolado
// (banco SQLite ':memory:' próprio) em uma porta efêmera.
//
// Como rodar:
//   cd ecommerce-api-legacy
//   node --test test/findings.test.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const express = require('express');

const AppManager = require('../src/AppManager');
const { config, badCrypto } = require('../src/utils');

function startServer() {
  const manager = new AppManager();
  manager.initDb();
  const app = express();
  app.use(express.json());
  manager.setupRoutes(app);
  const server = app.listen(0);
  const port = server.address().port;
  return { manager, server, baseUrl: `http://127.0.0.1:${port}` };
}

function stopServer(server) {
  return new Promise((resolve) => server.close(resolve));
}

function runAsync(db, sql, params = []) {
  return new Promise((resolve, reject) => {
    db.run(sql, params, function (err) {
      if (err) reject(err);
      else resolve(this);
    });
  });
}

// ----------------------------------------------------------------------
// 1) CRITICAL — God Class concentrando DB, rotas e regras de negócio
// ----------------------------------------------------------------------
test('CRITICAL - AppManager concentra schema de banco, rotas HTTP e regra de negócio de pagamento no mesmo arquivo/classe', () => {
  const source = fs.readFileSync(path.join(__dirname, '..', 'src', 'AppManager.js'), 'utf8');
  const manager = new AppManager();

  // camada de dados (schema) e camada de rotas expostas pelo MESMO objeto
  assert.equal(typeof manager.initDb, 'function');
  assert.equal(typeof manager.setupRoutes, 'function');

  // o mesmo arquivo contém DDL de banco, definição de rota HTTP e a regra de
  // negócio de aprovação de pagamento — três responsabilidades que deveriam
  // estar em Model / Router / Controller separados
  assert.match(source, /CREATE TABLE/);
  assert.match(source, /app\.post\('\/api\/checkout'/);
  assert.match(source, /processPaymentAndEnroll/);
});

// ----------------------------------------------------------------------
// 2) CRITICAL — Credenciais e chaves de produção hardcoded
// ----------------------------------------------------------------------
test('CRITICAL - credenciais e chave de gateway de pagamento estão hardcoded em utils.js (não vêm de env)', () => {
  assert.equal(config.dbPass, 'senha_super_secreta_prod_123');
  assert.equal(config.paymentGatewayKey, 'pk_live_1234567890abcdef');
  assert.equal(process.env.DB_PASS, undefined, 'não deveria existir env var: o segredo está cravado no código-fonte');
});

// ----------------------------------------------------------------------
// 3) CRITICAL — Hash de senha falso/quebrado (badCrypto)
// ----------------------------------------------------------------------
test('CRITICAL - badCrypto gera colisão para senhas diferentes que só compartilham os 2 primeiros bytes', () => {
  // badCrypto só olha para os 2 primeiros caracteres do Base64 da senha inteira
  // e repete esse mesmo par 5x — ou seja, tudo que vier depois do começo da
  // senha é irrelevante para o hash final.
  const hashSenhaA = badCrypto('ab123456');
  const hashSenhaB = badCrypto('ab999999XYZ-totalmente-diferente');

  assert.equal(hashSenhaA, hashSenhaB, 'duas senhas bem diferentes geraram o mesmo "hash"');
  assert.equal(hashSenhaA.length, 10);
});

// ----------------------------------------------------------------------
// 4) MEDIUM — Queries N+1 no relatório financeiro
// ----------------------------------------------------------------------
test('MEDIUM - /api/admin/financial-report dispara uma query por matrícula em vez de usar JOIN', async () => {
  const { manager, server, baseUrl } = startServer();
  try {
    // seed inicial já tem 1 curso com 1 matrícula; adiciona mais 3 matrículas
    // do mesmo usuário no mesmo curso para tornar o crescimento linear visível
    for (let i = 0; i < 3; i++) {
      await runAsync(manager.db, 'INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)');
    }

    let calls = 0;
    const originalAll = manager.db.all.bind(manager.db);
    const originalGet = manager.db.get.bind(manager.db);
    manager.db.all = (...args) => { calls += 1; return originalAll(...args); };
    manager.db.get = (...args) => { calls += 1; return originalGet(...args); };

    const resp = await fetch(`${baseUrl}/api/admin/financial-report`);
    assert.equal(resp.status, 200);

    // 1 (SELECT courses) + 2 cursos * 1 (SELECT enrollments) + 4 matrículas * 2 (user + payment)
    const esperado = 1 + 2 + 4 * 2;
    assert.equal(calls, esperado, `esperado ${esperado} chamadas ao banco (N+1); obtidas: ${calls}`);
  } finally {
    await stopServer(server);
  }
});

// ----------------------------------------------------------------------
// 5) MEDIUM — Erros de banco silenciados/ignorados
// ----------------------------------------------------------------------
test('MEDIUM - DELETE /api/users/:id ignora erro do banco e ainda assim responde como sucesso', async () => {
  const { manager, server, baseUrl } = startServer();
  try {
    // força um erro real: fecha a conexão antes da rota tentar usá-la
    await new Promise((resolve) => manager.db.close(resolve));

    const resp = await fetch(`${baseUrl}/api/users/1`, { method: 'DELETE' });
    const text = await resp.text();

    // a rota nunca checa "err" no callback do db.run, então mesmo com o banco
    // fechado (erro garantido) ela responde 200 como se tivesse funcionado
    assert.equal(resp.status, 200);
    assert.match(text, /Usuário deletado/);
  } finally {
    await stopServer(server);
  }
});

// ----------------------------------------------------------------------
// 6) LOW — Nomenclatura de variáveis não descritiva
// ----------------------------------------------------------------------
test('LOW - handler de checkout usa nomes de variável de uma letra para campos de domínio', () => {
  const source = fs.readFileSync(path.join(__dirname, '..', 'src', 'AppManager.js'), 'utf8');
  const checkoutHandler = source.slice(source.indexOf("app.post('/api/checkout'"), source.indexOf("app.get('/api/admin/financial-report'"));

  for (const nomeCurto of ['let u =', 'let e =', 'let p =', 'let cid =', 'let cc =']) {
    assert.ok(checkoutHandler.includes(nomeCurto), `esperava encontrar "${nomeCurto}" no handler de checkout`);
  }
});

// ----------------------------------------------------------------------
// 7) LOW — Strings mágicas / regra de aprovação baseada em prefixo do cartão
// ----------------------------------------------------------------------
test('LOW - aprovação de pagamento depende só do prefixo "4" do número do cartão, sem validação real', async () => {
  const { server, baseUrl } = startServer();
  try {
    const aprovado = await fetch(`${baseUrl}/api/checkout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        usr: 'Fulano PoC',
        eml: 'fulano.poc@teste.com',
        pwd: 'senha123',
        c_id: 1,
        card: '4000-nao-e-um-cartao-valido', // não passa em nenhuma validação de cartão real, mas começa com "4"
      }),
    });
    assert.equal(aprovado.status, 200);
    const aprovadoBody = await aprovado.json();
    assert.equal(aprovadoBody.msg, 'Sucesso');

    const recusado = await fetch(`${baseUrl}/api/checkout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        usr: 'Ciclano PoC',
        eml: 'ciclano.poc@teste.com',
        pwd: 'senha123',
        c_id: 1,
        card: '9999999999999999', // 16 dígitos "válidos" no formato, mas não começa com "4"
      }),
    });
    assert.equal(recusado.status, 400);
  } finally {
    await stopServer(server);
  }
});
