from database import get_db

STATUSES_VALIDOS = ["pendente", "aprovado", "enviado", "entregue", "cancelado"]

# (faturamento mínimo, percentual de desconto aplicado acima desse limite)
FAIXAS_DESCONTO = [
    (10000, 0.10),
    (5000, 0.05),
    (1000, 0.02),
]

_PEDIDOS_COM_ITENS_QUERY = """
    SELECT
        pedidos.id AS pedido_id,
        pedidos.usuario_id,
        pedidos.status,
        pedidos.total,
        pedidos.criado_em,
        itens_pedido.produto_id,
        itens_pedido.quantidade,
        itens_pedido.preco_unitario,
        produtos.nome AS produto_nome
    FROM pedidos
    LEFT JOIN itens_pedido ON itens_pedido.pedido_id = pedidos.id
    LEFT JOIN produtos ON produtos.id = itens_pedido.produto_id
    {where}
    ORDER BY pedidos.id
"""


def _montar_pedidos(rows):
    pedidos_por_id = {}
    ordem = []

    for row in rows:
        pid = row["pedido_id"]
        if pid not in pedidos_por_id:
            pedidos_por_id[pid] = {
                "id": row["pedido_id"],
                "usuario_id": row["usuario_id"],
                "status": row["status"],
                "total": row["total"],
                "criado_em": row["criado_em"],
                "itens": [],
            }
            ordem.append(pid)

        if row["produto_id"] is not None:
            pedidos_por_id[pid]["itens"].append({
                "produto_id": row["produto_id"],
                "produto_nome": row["produto_nome"] or "Desconhecido",
                "quantidade": row["quantidade"],
                "preco_unitario": row["preco_unitario"],
            })

    return [pedidos_por_id[pid] for pid in ordem]


def listar_todos():
    db = get_db()
    cursor = db.cursor()
    cursor.execute(_PEDIDOS_COM_ITENS_QUERY.format(where=""))
    return _montar_pedidos(cursor.fetchall())


def listar_por_usuario(usuario_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        _PEDIDOS_COM_ITENS_QUERY.format(where="WHERE pedidos.usuario_id = ?"),
        (usuario_id,),
    )
    return _montar_pedidos(cursor.fetchall())


def criar(usuario_id, itens):
    if not itens:
        raise ValueError("Pedido deve ter pelo menos 1 item")

    db = get_db()
    cursor = db.cursor()

    total = 0
    for item in itens:
        cursor.execute("SELECT * FROM produtos WHERE id = ?", (item["produto_id"],))
        produto = cursor.fetchone()
        if produto is None:
            raise ValueError(f"Produto {item['produto_id']} não encontrado")
        if produto["estoque"] < item["quantidade"]:
            raise ValueError(f"Estoque insuficiente para {produto['nome']}")
        total += produto["preco"] * item["quantidade"]

    cursor.execute(
        "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)",
        (usuario_id, total),
    )
    pedido_id = cursor.lastrowid

    for item in itens:
        cursor.execute("SELECT preco FROM produtos WHERE id = ?", (item["produto_id"],))
        produto = cursor.fetchone()
        cursor.execute(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
            (pedido_id, item["produto_id"], item["quantidade"], produto["preco"]),
        )
        decrementar_estoque_produto(cursor, item["produto_id"], item["quantidade"])

    db.commit()
    return {"pedido_id": pedido_id, "total": total}


def decrementar_estoque_produto(cursor, produto_id, quantidade):
    cursor.execute(
        "UPDATE produtos SET estoque = estoque - ? WHERE id = ?",
        (quantidade, produto_id),
    )


def atualizar_status(pedido_id, novo_status):
    if novo_status not in STATUSES_VALIDOS:
        raise ValueError("Status inválido")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT status FROM pedidos WHERE id = ?", (pedido_id,))
    pedido = cursor.fetchone()
    if pedido is None:
        raise ValueError("Pedido não encontrado")

    status_anterior = pedido["status"]
    cursor.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))

    # Devolve o estoque reservado quando um pedido é cancelado (evita creditar
    # duas vezes se o pedido já estava cancelado antes desta chamada).
    if novo_status == "cancelado" and status_anterior != "cancelado":
        cursor.execute(
            "SELECT produto_id, quantidade FROM itens_pedido WHERE pedido_id = ?",
            (pedido_id,),
        )
        for item in cursor.fetchall():
            cursor.execute(
                "UPDATE produtos SET estoque = estoque + ? WHERE id = ?",
                (item["quantidade"], item["produto_id"]),
            )

    db.commit()


def _calcular_desconto(faturamento):
    for limite, percentual in FAIXAS_DESCONTO:
        if faturamento > limite:
            return faturamento * percentual
    return 0


def relatorio_vendas():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM pedidos")
    total_pedidos = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(total) FROM pedidos")
    faturamento = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status = 'pendente'")
    pendentes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status = 'aprovado'")
    aprovados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status = 'cancelado'")
    cancelados = cursor.fetchone()[0]

    desconto = _calcular_desconto(faturamento)

    return {
        "total_pedidos": total_pedidos,
        "faturamento_bruto": round(faturamento, 2),
        "desconto_aplicavel": round(desconto, 2),
        "faturamento_liquido": round(faturamento - desconto, 2),
        "pedidos_pendentes": pendentes,
        "pedidos_aprovados": aprovados,
        "pedidos_cancelados": cancelados,
        "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
    }


def deletar_todos():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM itens_pedido")
    cursor.execute("DELETE FROM pedidos")
    db.commit()
