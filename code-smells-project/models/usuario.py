from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db


def _row_to_dict(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "tipo": row["tipo"],
        "criado_em": row["criado_em"],
    }


def validar(dados):
    if not dados:
        raise ValueError("Dados inválidos")

    nome = dados.get("nome", "")
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    if not nome or not email or not senha:
        raise ValueError("Nome, email e senha são obrigatórios")

    return dados


def listar_todos():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM usuarios")
    return [_row_to_dict(row) for row in cursor.fetchall()]


def buscar_por_id(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id = ?", (id,))
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def criar(dados):
    validar(dados)
    db = get_db()
    cursor = db.cursor()
    senha_hash = generate_password_hash(dados["senha"])
    cursor.execute(
        "INSERT INTO usuarios (nome, email, senha_hash, tipo) VALUES (?, ?, ?, ?)",
        (dados["nome"], dados["email"], senha_hash, dados.get("tipo", "cliente")),
    )
    db.commit()
    return cursor.lastrowid


def autenticar(email, senha):
    if not email or not senha:
        raise ValueError("Email e senha são obrigatórios")

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
    row = cursor.fetchone()

    if row and check_password_hash(row["senha_hash"], senha):
        return _row_to_dict(row)
    return None


def deletar_todos():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM usuarios")
    db.commit()
