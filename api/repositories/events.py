from typing import Any, Dict, Optional
import json
from ..db import get_conn

TIPO_ENTRADA        = "entrada"
TIPO_MSG_ENVIADA    = "mensagem_enviada"
TIPO_ERRO_ENVIO     = "erro_envio"
TIPO_FOLLOWUP       = "followup"
TIPO_ATUALIZACAO    = "atualizacao"

TIPOS_VALIDOS = {
    TIPO_ENTRADA,
    TIPO_MSG_ENVIADA,
    TIPO_ERRO_ENVIO,
    TIPO_FOLLOWUP,
    TIPO_ATUALIZACAO,
}

def add_event(lead_id: int, tipo: str, payload: Optional[Dict[str, Any]] = None) -> None:
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(f"Tipo de evento inválido: {tipo}")

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO lead_events (lead_id, tipo, payload)
            VALUES (%s, %s, %s)
            """,
            (lead_id, tipo, json.dumps(payload) if payload is not None else None),
        )
