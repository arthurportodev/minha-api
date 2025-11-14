from typing import Any, Dict, Optional
import json
from ..db import get_conn

def add_event(lead_id: int, tipo: str, payload: Optional[Dict[str, Any]] = None) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO lead_events (lead_id, tipo, payload) VALUES (%s, %s, %s)",
            (lead_id, tipo, (json.dumps(payload) if payload is not None else None)),
        )