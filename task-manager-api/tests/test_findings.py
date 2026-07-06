"""
Provas de conceito automatizadas para os 7 achados documentados na Análise Manual
(README.md do repositório, seção "Projeto 3 — task-manager-api").

Cada teste sobe uma instância Flask isolada com SQLite em memória (reaproveitando
os blueprints e models reais do projeto), sem tocar no tasks.db de desenvolvimento.

Como rodar:
    cd task-manager-api
    python3 -m unittest tests.test_findings -v
"""
import hashlib
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask  # noqa: E402
from sqlalchemy import event  # noqa: E402

from database import db  # noqa: E402
from models.task import Task  # noqa: E402
from models.user import User  # noqa: E402
from models.category import Category  # noqa: E402
from routes.task_routes import task_bp  # noqa: E402
from routes.user_routes import user_bp  # noqa: E402
from routes.report_routes import report_bp  # noqa: E402

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _build_test_app():
    """App Flask isolado com SQLite em memória — não usa app.py nem tasks.db,
    só os blueprints/models reais, para não sujar o banco de desenvolvimento."""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = True
    db.init_app(app)
    app.register_blueprint(task_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(report_bp)
    with app.app_context():
        db.create_all()
    return app


def _source(relative_path):
    with open(os.path.join(PROJECT_ROOT, relative_path), encoding="utf-8") as fh:
        return fh.read()


class FindingsProofOfConcept(unittest.TestCase):
    """1 teste por achado do Projeto 3, na mesma ordem da tabela do README."""

    def setUp(self):
        self.app = _build_test_app()
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    # ------------------------------------------------------------------
    # 1) CRITICAL — Autenticação via token falso, previsível e sem validação
    # ------------------------------------------------------------------
    def test_1_token_e_previsivel_e_nenhuma_rota_o_valida(self):
        """routes/user_routes.py:210 devolve 'fake-jwt-token-' + id. Nenhuma rota
        do projeto exige Authorization, então o token não protege nada."""
        resp = self.client.post(
            "/users", json={"name": "PoC Token", "email": "poc.token@teste.com", "password": "1234"}
        )
        user_id = resp.get_json()["id"]

        login = self.client.post("/login", json={"email": "poc.token@teste.com", "password": "1234"})
        token = login.get_json()["token"]

        # o token é 100% previsível a partir do ID, sem nenhum segredo/assinatura
        self.assertEqual(token, f"fake-jwt-token-{user_id}")

        # e nenhuma rota "protegida" sequer pede Authorization: DELETE funciona sem token algum
        delete_sem_auth = self.client.delete(f"/users/{user_id}")
        self.assertEqual(delete_sem_auth.status_code, 200)

    # ------------------------------------------------------------------
    # 2) CRITICAL — Hash de senha com MD5, sem salt
    # ------------------------------------------------------------------
    def test_2_md5_sem_salt_gera_hash_identico_para_usuarios_diferentes(self):
        """models/user.py:27-32 usa hashlib.md5 puro. Dois usuários com a mesma
        senha ficam com o mesmo hash gravado — não há salt por usuário."""
        u1 = User(name="Usuário A", email="a.poc@teste.com")
        u1.set_password("mesma-senha-123")
        u2 = User(name="Usuário B", email="b.poc@teste.com")
        u2.set_password("mesma-senha-123")

        self.assertEqual(u1.password, u2.password)
        self.assertEqual(u1.password, hashlib.md5("mesma-senha-123".encode()).hexdigest())

    # ------------------------------------------------------------------
    # 3) CRITICAL — Credenciais hardcoded (app + serviço de e-mail)
    # ------------------------------------------------------------------
    def test_3_secret_key_e_senha_smtp_estao_hardcoded_no_codigo_fonte(self):
        """app.py:13 e services/notification_service.py:7-10 têm segredos como
        literais de string, mesmo o projeto declarando python-dotenv no requirements."""
        app_source = _source("app.py")
        notification_source = _source("services/notification_service.py")

        self.assertIn("super-secret-key-123", app_source)
        self.assertIn("senha123", notification_source)
        self.assertIn("python-dotenv", _source("requirements.txt"))
        self.assertNotIn("os.environ", notification_source)

    # ------------------------------------------------------------------
    # 4) MEDIUM — Queries N+1 em listagens e relatórios
    # ------------------------------------------------------------------
    def test_4_get_tasks_dispara_uma_query_extra_por_task(self):
        """routes/task_routes.py:41-57 busca User e Category dentro do loop de
        tasks em vez de usar JOIN/eager loading — número de queries cresce com N.

        Cada task referencia um usuário/categoria DIFERENTE de propósito: se
        reusassem o mesmo ID, o identity map do SQLAlchemy mascararia o N+1
        (cache de sessão), escondendo o problema."""
        num_tasks = 5
        for i in range(num_tasks):
            user = User(name=f"Usuário {i}", email=f"tasks.poc{i}@teste.com")
            user.set_password("1234")
            categoria = Category(name=f"Categoria PoC {i}")
            db.session.add_all([user, categoria])
            db.session.flush()
            db.session.add(Task(title=f"Task PoC {i}", user_id=user.id, category_id=categoria.id))
        db.session.commit()
        db.session.expunge_all()  # simula uma requisição nova, sem cache de sessão

        statements = []

        def contador(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(db.engine, "before_cursor_execute", contador)
        try:
            resp = self.client.get("/tasks")
        finally:
            event.remove(db.engine, "before_cursor_execute", contador)

        self.assertEqual(resp.status_code, 200)
        # 1 SELECT de tasks + 1 SELECT de User e 1 de Category para CADA task
        esperado = 1 + num_tasks * 2
        self.assertEqual(
            len(statements),
            esperado,
            f"esperava exatamente {esperado} statements (N+1); executados: {len(statements)}",
        )

    # ------------------------------------------------------------------
    # 5) MEDIUM — Validação e utilitários duplicados/mortos
    # ------------------------------------------------------------------
    def test_5_validate_email_existe_em_utils_mas_rota_reimplementa_a_regex_manualmente(self):
        """utils/helpers.py define validate_email, mas routes/user_routes.py nunca
        a importa: reimplementa a mesma regex inline (código morto + duplicado)."""
        from utils.helpers import validate_email

        self.assertTrue(validate_email("ok@teste.com"))
        self.assertFalse(validate_email("invalido"))

        user_routes_source = _source("routes/user_routes.py")
        self.assertNotIn("from utils.helpers import", user_routes_source)
        self.assertIn(r"[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+", user_routes_source)

    # ------------------------------------------------------------------
    # 6) LOW — Dados sensíveis retornados pela API (password no to_dict)
    # ------------------------------------------------------------------
    def test_6_resposta_da_api_devolve_o_hash_da_senha(self):
        """models/user.py:16-25 inclui 'password' no to_dict(), que é usado
        diretamente pela resposta de POST /users."""
        resp = self.client.post(
            "/users", json={"name": "PoC Vaza Senha", "email": "vaza.senha@teste.com", "password": "abcd"}
        )
        data = resp.get_json()

        self.assertEqual(resp.status_code, 201)
        self.assertIn("password", data)
        self.assertEqual(data["password"], hashlib.md5("abcd".encode()).hexdigest())

    # ------------------------------------------------------------------
    # 7) LOW — Imports não utilizados e magic numbers
    # ------------------------------------------------------------------
    def test_7_task_routes_tem_imports_mortos_e_ignora_as_constantes_de_helpers(self):
        """routes/task_routes.py importa json/os/sys/time sem usá-los e repete os
        literais 3/200 em vez de MIN_TITLE_LENGTH/MAX_TITLE_LENGTH de utils/helpers.py."""
        source = _source("routes/task_routes.py")
        linha_import = next(linha for linha in source.splitlines() if linha.startswith("import json"))
        corpo_sem_import = source.replace(linha_import, "", 1)

        for nome_nao_usado in ("os", "sys", "time"):
            ocorrencias = len(re.findall(rf"\b{nome_nao_usado}\b", corpo_sem_import))
            self.assertEqual(
                ocorrencias, 0, f"'{nome_nao_usado}' foi importado mas não aparece em nenhum outro lugar do arquivo"
            )

        self.assertIn("len(title) < 3", source)
        self.assertIn("len(title) > 200", source)
        self.assertNotIn("MIN_TITLE_LENGTH", source)
        self.assertNotIn("MAX_TITLE_LENGTH", source)


if __name__ == "__main__":
    unittest.main()
