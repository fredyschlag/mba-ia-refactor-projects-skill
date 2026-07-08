from database import get_db

NOME_MIN_LEN = 2
NOME_MAX_LEN = 200
CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]


def _row_to_dict(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco": row["preco"],
        "estoque": row["estoque"],
        "categoria": row["categoria"],
        "ativo": row["ativo"],
        "criado_em": row["criado_em"],
    }


def validar(dados):
    if not dados:
        raise ValueError("Dados inválidos")
    if "nome" not in dados:
        raise ValueError("Nome é obrigatório")
    if "preco" not in dados:
        raise ValueError("Preço é obrigatório")
    if "estoque" not in dados:
        raise ValueError("Estoque é obrigatório")

    nome = dados["nome"]
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", "geral")

    if preco < 0:
        raise ValueError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValueError("Estoque não pode ser negativo")
    if len(nome) < NOME_MIN_LEN:
        raise ValueError("Nome muito curto")
    if len(nome) > NOME_MAX_LEN:
        raise ValueError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValueError("Categoria inválida. Válidas: " + str(CATEGORIAS_VALIDAS))

    return dados


def listar_todos():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM produtos")
    return [_row_to_dict(row) for row in cursor.fetchall()]


def buscar_por_id(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM produtos WHERE id = ?", (id,))
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def buscar(termo="", categoria=None, preco_min=None, preco_max=None):
    db = get_db()
    cursor = db.cursor()

    condicoes = []
    parametros = []

    if termo:
        condicoes.append("(nome LIKE ? OR descricao LIKE ?)")
        parametros.extend([f"%{termo}%", f"%{termo}%"])
    if categoria:
        condicoes.append("categoria = ?")
        parametros.append(categoria)
    if preco_min is not None:
        condicoes.append("preco >= ?")
        parametros.append(preco_min)
    if preco_max is not None:
        condicoes.append("preco <= ?")
        parametros.append(preco_max)

    query = "SELECT * FROM produtos"
    if condicoes:
        query += " WHERE " + " AND ".join(condicoes)

    cursor.execute(query, parametros)
    return [_row_to_dict(row) for row in cursor.fetchall()]


def criar(dados):
    validar(dados)
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
        (
            dados["nome"],
            dados.get("descricao", ""),
            dados["preco"],
            dados["estoque"],
            dados.get("categoria", "geral"),
        ),
    )
    db.commit()
    return cursor.lastrowid


def atualizar(id, dados):
    validar(dados)
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
        (
            dados["nome"],
            dados.get("descricao", ""),
            dados["preco"],
            dados["estoque"],
            dados.get("categoria", "geral"),
            id,
        ),
    )
    db.commit()


def deletar(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM produtos WHERE id = ?", (id,))
    db.commit()


def decrementar_estoque(id, quantidade):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", (quantidade, id))


def incrementar_estoque(id, quantidade):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE produtos SET estoque = estoque + ? WHERE id = ?", (quantidade, id))


def deletar_todos():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM produtos")
    db.commit()
