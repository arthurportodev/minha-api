from typing import Optional, List, Dict, Any
from ..db import get_conn
from typing import Optional, List, Dict, Any
from ..db import get_conn


def upsert_lead(data: Dict[str, Any]) -> int:
    sql = """
    INSERT INTO leads (nome, email, telefone, origem, tags, externo_id, score, etapa)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
      nome = VALUES(nome),
      origem = VALUES(origem),
      tags = VALUES(tags),
      externo_id = VALUES(externo_id),
      score = VALUES(score),
      etapa = VALUES(etapa),
      updated_at = CURRENT_TIMESTAMP
    """

    params = (
        data["nome"],
        data["email"],
        data["telefone"],
        data["origem"],
        data["tags_json"],
        data.get("externo_id"),
        data["score"],
        data["etapa"],
    )

    with get_conn() as conn, conn.cursor(dictionary=True) as cur:
        cur.execute(sql, params)

        # Se for um novo insert
        if cur.lastrowid:
            return int(cur.lastrowid)

        # Caso tenha sido update, buscamos o ID existente
        cur.execute(
            """
            SELECT id
            FROM leads
            WHERE (email = %s AND %s IS NOT NULL)
               OR (telefone = %s AND %s IS NOT NULL)
            ORDER BY id DESC
            LIMIT 1
            """,
            (data["email"], data["email"], data["telefone"], data["telefone"]),
        )
        row = cur.fetchone()
        return int(row["id"]) if row else 0


def get_by_id(lead_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn, conn.cursor(dictionary=True) as cur:
        cur.execute("SELECT * FROM leads WHERE id = %s", (lead_id,))
        return cur.fetchone()


def list_leads(origem: Optional[str], etapa: Optional[str]) -> List[Dict[str, Any]]:
    clauses: List[str] = []
    params: List[Any] = []

    if origem:
        clauses.append("origem = %s")
        params.append(origem)
    if etapa:
        clauses.append("etapa = %s")
        params.append(etapa)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM leads {where} ORDER BY updated_at DESC LIMIT 200"

    with get_conn() as conn, conn.cursor(dictionary=True) as cur:
        cur.execute(sql, params)
        return cur.fetchall()
    
def update_lead(lead_id: int, data: Dict[str, Any]) -> None:
    """
    Atualiza um lead existente.
    Apenas as chaves presentes em `data` e permitidas em `allowed_fields`
    são incluídas no UPDATE.

    Exemplo de `data`:
        {"servico_interesse": "Botox", "regiao_corpo": "rosto"}
    """
    if not data:
        return

    # Campos que realmente existem na tabela `leads`
    allowed_fields = {
        "nome",
        "email",
        "telefone",
        "origem",
        "tags",
        "externo_id",
        "score",
        "etapa",
        "servico_interesse",
        "regiao_corpo",
        "disponibilidade",
    }

    set_clauses: List[str] = []
    params: List[Any] = []

    for key, value in data.items():
        if key not in allowed_fields:
            # ignora qualquer chave estranha que vier do agente/n8n
            continue
        set_clauses.append(f"{key} = %s")
        params.append(value)

    if not set_clauses:
        # nada permitido pra atualizar
        return

    # opcional: atualiza o updated_at também
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")

    params.append(lead_id)
    sql = f"UPDATE leads SET {', '.join(set_clauses)} WHERE id = %s"

    with get_conn() as conn, conn.cursor(dictionary=True) as cur:
        cur.execute(sql, params)
        conn.commit()
