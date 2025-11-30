import os
import requests
from typing import Any, Dict

WHATSAPP_API = os.getenv("WHATSAPP_API_URL", "")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")


def send_whatsapp(telefone: str, texto: str) -> Dict[str, Any]:
    """
    Envia mensagem de texto via Evolution API.
    """

    if not WHATSAPP_API or not WHATSAPP_TOKEN:
        return {
            "status": "disabled",
            "detail": "configure WHATSAPP_API_URL/WHATSAPP_TOKEN",
        }

    headers = {
        "apikey": WHATSAPP_TOKEN,           # Evolution usa 'apikey'
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        # campo mais comum na Evolution:
        "number": telefone,                # se a doc/fluxo antigo usava outro nome, troca aqui
        "text": texto,
        # opcional:
        "delay": 0,
        "presence": "composing",
    }

    try:
        response = requests.post(
            WHATSAPP_API,
            headers=headers,
            json=payload,
            timeout=15,
        )
        return {
            "status": response.status_code,
            "detail": response.text,       # 👈 agora o detalhe vem no n8n
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "detail": str(e),
        }
