from typing import Any, Dict, List, Optional
from ..db import get_conn


def adicionar_servico(
    lead_id: int,
    servico: str,
    data_servico: str,   # 'YYYY-MM-DD HH:MM:SS'
    status: str,
    ticket: Optional[float] = None,
    observacoes: Optional[str] = None,
) -> int:
    sql = """
    INSERT INTO historico_servicos
        (lead_id, servico, data_servico, status, ticket, observacoes)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    params = (lead_id, servico, data_servico, status, ticket, observacoes)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return int(cur.lastrowid)


def listar_historico_por_lead(lead_id: int) -> List[Dict[str, Any]]:
    sql = """
    SELECT *
    FROM historico_servicos
    WHERE lead_id = %s
    ORDER BY data_servico DESC
    """
    with get_conn() as conn, conn.cursor(dictionary=True) as cur:
        cur.execute(sql, (lead_id,))
        return cur.fetchall()
