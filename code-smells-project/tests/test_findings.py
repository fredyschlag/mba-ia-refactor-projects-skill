"""
Provas de conceito automatizadas para os 7 achados documentados na Análise Manual
(README.md do repositório, seção "Projeto 1 — code-smells-project").

Cada teste isola e demonstra em tempo de execução o problema descrito no README,
usando um banco SQLite temporário e o `test_client` do Flask (não sobe servidor real).

Como rodar:
    cd code-smells-project
    python3 -m unittest tests.test_findings -v
"""
import contextlib
import io
import logging
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database  # noqa: E402


def _fresh_app():
    """Reseta o singleton de conexão do database.py e aponta para um SQLite temporário,
    para que cada execução dos testes não dependa nem suje o loja.db de desenvolvimento."""
    database.db_connection = None
    fd, path = tempfile.mkstemp(prefix="loja_test_", suffix=".db")
    os.close(fd)
    os.remove(path)
    database.db_path = path

    # app.py só registra rotas na importação (get_db() é chamado sob demanda dentro
    # dos handlers), então importar aqui já com o db_path trocado é seguro.
    import app as app_module

    return app_module.app, path


class FindingsProofOfConcept(unittest.TestCase):
    """1 teste por achado do Projeto 1, na mesma ordem da tabela do README."""

    @classmethod
    def setUpClass(cls):
        cls.app, cls.db_path = _fresh_app()
        cls.app.testing = True
        cls.client = cls.app.test_client()
        # Primeira request qualquer força o get_db() a criar/seedar o banco temporário.
        cls.client.get("/health")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    # ------------------------------------------------------------------
    # 1) CRITICAL — SQL Injection generalizado
    # ------------------------------------------------------------------
    def test_1_sql_injection_bypassa_login_sem_senha_correta(self):
        """models.login_usuario monta a query por concatenação de string.
        Um comentário SQL ('--') na 'email' anula a checagem de senha inteira,
        permitindo logar como admin sem saber a senha."""
        payload = {
            "email": "admin@loja.com' -- ",
            "senha": "qualquer-coisa-errada",
        }
        resp = self.client.post("/login", json=payload)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200, data)
        self.assertTrue(data["sucesso"])
        self.assertEqual(data["dados"]["email"], "admin@loja.com")

    # ------------------------------------------------------------------
    # 2) CRITICAL — Credenciais e segredos hardcoded expostos via API
    # ------------------------------------------------------------------
    def test_2_secret_key_hardcoded_e_devolvido_pelo_endpoint_health(self):
        """app.py:7 define SECRET_KEY hardcoded e controllers.health_check
        devolve esse mesmo segredo no corpo da resposta pública de /health."""
        resp = self.client.get("/health")
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data["secret_key"], "minha-chave-super-secreta-123")
        self.assertEqual(data["secret_key"], self.app.config["SECRET_KEY"])
        self.assertTrue(data["debug"])

    # ------------------------------------------------------------------
    # 3) CRITICAL — Senhas armazenadas e comparadas em texto plano
    # ------------------------------------------------------------------
    def test_3_senha_e_persistida_em_texto_plano_no_banco(self):
        """models.criar_usuario grava a senha exatamente como recebida, sem hashing."""
        senha_original = "MinhaSenh@SuperSecreta123"
        resp = self.client.post(
            "/usuarios",
            json={"nome": "PoC Teste", "email": "poc.senha@teste.com", "senha": senha_original},
        )
        self.assertEqual(resp.status_code, 201, resp.get_json())

        conn = database.get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT senha FROM usuarios WHERE email = ?", ("poc.senha@teste.com",))
        row = cursor.fetchone()

        self.assertEqual(row["senha"], senha_original)

    # ------------------------------------------------------------------
    # 4) MEDIUM — Queries N+1 ao montar pedidos
    # ------------------------------------------------------------------
    def test_4_listar_pedidos_do_usuario_dispara_uma_query_por_item(self):
        """models.get_pedidos_usuario abre um cursor por pedido e mais um cursor
        por item dentro do pedido, em vez de usar JOIN. O número de statements
        SQL cresce linearmente com pedidos x itens."""
        # usuário + produto exclusivos para não interferir com outros testes
        usuario_id = self.client.post(
            "/usuarios",
            json={"nome": "PoC N1", "email": "poc.n1@teste.com", "senha": "123456"},
        ).get_json()["dados"]["id"]

        produto_id = self.client.post(
            "/produtos",
            json={"nome": "Produto PoC N1", "preco": 10.0, "estoque": 100, "categoria": "geral"},
        ).get_json()["dados"]["id"]

        # pedido A com 1 item, pedido B com 5 itens (mesmo produto, quantidades unitárias)
        self.client.post(
            "/pedidos",
            json={"usuario_id": usuario_id, "itens": [{"produto_id": produto_id, "quantidade": 1}]},
        )
        self.client.post(
            "/pedidos",
            json={
                "usuario_id": usuario_id,
                "itens": [{"produto_id": produto_id, "quantidade": 1} for _ in range(5)],
            },
        )

        conn = database.get_db()
        statements = []
        conn.set_trace_callback(statements.append)
        resp = self.client.get(f"/pedidos/usuario/{usuario_id}")
        conn.set_trace_callback(None)

        self.assertEqual(resp.status_code, 200)
        # 1 (SELECT pedidos) + 2 pedidos (SELECT itens_pedido cada) + 6 itens (SELECT produto cada)
        esperado = 1 + 2 + 6
        self.assertEqual(
            len(statements),
            esperado,
            f"Esperado {esperado} statements SQL (N+1); executados: {len(statements)}\n{statements}",
        )

    # ------------------------------------------------------------------
    # 5) MEDIUM — Validação duplicada e divergente entre criar/atualizar produto
    # ------------------------------------------------------------------
    def test_5_validacao_duplicada_diverge_entre_criar_e_atualizar_produto(self):
        """criar_produto valida tamanho do nome e categoria contra uma lista fixa;
        atualizar_produto copiou só parte dessas regras, então o mesmo dado que
        é rejeitado na criação é aceito silenciosamente na atualização."""
        # nome de 1 caractere: create rejeita (regra de min. 2 caracteres)
        resp_create_nome_curto = self.client.post(
            "/produtos", json={"nome": "A", "preco": 10.0, "estoque": 1, "categoria": "geral"}
        )
        self.assertEqual(resp_create_nome_curto.status_code, 400)

        # categoria inexistente: create rejeita
        resp_create_categoria_invalida = self.client.post(
            "/produtos",
            json={"nome": "Produto Válido", "preco": 10.0, "estoque": 1, "categoria": "categoria-que-nao-existe"},
        )
        self.assertEqual(resp_create_categoria_invalida.status_code, 400)

        # cria um produto válido para em seguida tentar "quebrá-lo" via update
        produto_id = self.client.post(
            "/produtos",
            json={"nome": "Produto PoC Divergencia", "preco": 10.0, "estoque": 1, "categoria": "geral"},
        ).get_json()["dados"]["id"]

        # o MESMO nome de 1 caractere e a MESMA categoria inválida são aceitos no update
        resp_update = self.client.put(
            f"/produtos/{produto_id}",
            json={"nome": "A", "preco": 10.0, "estoque": 1, "categoria": "categoria-que-nao-existe"},
        )

        self.assertEqual(
            resp_update.status_code,
            200,
            "atualizar_produto deveria (mas não deveria) aceitar dado que criar_produto rejeita",
        )

    # ------------------------------------------------------------------
    # 6) LOW — Magic numbers (limiares de desconto não nomeados)
    # ------------------------------------------------------------------
    def test_6_limiar_de_desconto_e_um_magic_number_nao_documentado(self):
        """models.relatorio_vendas aplica desconto conforme limiares (1000, 5000, 10000)
        embutidos como literais. Cruzar o limiar de 1000 muda o percentual de desconto
        sem que exista nenhuma constante nomeada documentando essa regra de negócio.

        Usa um banco isolado (não o compartilhado pelas outras provas) para que o
        faturamento acumulado de outros testes não interfira no limiar observado."""
        conexao_original = database.db_connection
        caminho_original = database.db_path
        app, db_path = _fresh_app()
        client = app.test_client()
        try:
            usuario_id = client.post(
                "/usuarios",
                json={"nome": "PoC Magic", "email": "poc.magic@teste.com", "senha": "123456"},
            ).get_json()["dados"]["id"]

            produto_id = client.post(
                "/produtos",
                json={"nome": "Produto PoC Magic", "preco": 999.0, "estoque": 100, "categoria": "geral"},
            ).get_json()["dados"]["id"]

            # pedido logo abaixo do limiar mágico de 1000
            client.post(
                "/pedidos",
                json={"usuario_id": usuario_id, "itens": [{"produto_id": produto_id, "quantidade": 1}]},
            )
            relatorio_abaixo = client.get("/relatorios/vendas").get_json()["dados"]
            desconto_abaixo = relatorio_abaixo["desconto_aplicavel"]

            # segundo pedido empurra o faturamento total para além de 1000
            client.post(
                "/pedidos",
                json={"usuario_id": usuario_id, "itens": [{"produto_id": produto_id, "quantidade": 1}]},
            )
            relatorio_acima = client.get("/relatorios/vendas").get_json()["dados"]
            desconto_acima = relatorio_acima["desconto_aplicavel"]

            self.assertEqual(desconto_abaixo, 0)
            self.assertGreater(
                desconto_acima,
                0,
                "cruzar o limiar mágico de 1000 deveria disparar o desconto de 2% embutido no código",
            )
        finally:
            database.db_connection.close()
            database.db_connection = conexao_original
            database.db_path = caminho_original
            if os.path.exists(db_path):
                os.remove(db_path)

    # ------------------------------------------------------------------
    # 7) LOW — print() como mecanismo de log
    # ------------------------------------------------------------------
    def test_7_eventos_de_negocio_sao_logados_via_print_em_stdout(self):
        """controllers.criar_produto usa print() em vez do módulo logging — o evento
        aparece em stdout, mas nunca passa pelo logger da aplicação (sem nível,
        timestamp ou handler estruturado)."""

        class _ListHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.records = []

            def emit(self, record):
                self.records.append(record)

        handler = _ListHandler()
        self.app.logger.addHandler(handler)
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                resp = self.client.post(
                    "/produtos",
                    json={"nome": "Produto PoC Log", "preco": 5.0, "estoque": 1, "categoria": "geral"},
                )
        finally:
            self.app.logger.removeHandler(handler)

        self.assertEqual(resp.status_code, 201)
        saida = buffer.getvalue()

        self.assertIn("Produto criado com ID", saida)
        # o mesmo evento nunca chega ao logging.Logger da aplicação
        self.assertFalse(
            any("Produto criado" in r.getMessage() for r in handler.records),
            "o evento de negócio não deveria vazar para o logger estruturado, só existe via print()",
        )


if __name__ == "__main__":
    unittest.main()
