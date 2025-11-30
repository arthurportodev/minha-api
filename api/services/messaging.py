import os
import requests
from typing import Any, Dict

WHATSAPP_API = os.getenv("WHATSAPP_API_URL", "")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")


def send_whatsapp(telefone: str, texto: str) -> Dict[str, Any]:
    """Envia uma mensagem de texto pelo Evolution API (WhatsApp)."""
    if not WHATSAPP_API or not WHATSAPP_TOKEN:
        return {
            "status": "disabled",
            "detail": "configure WHATSAPP_API_URL/WHATSAPP_TOKEN",
        }

    # Evolution costuma usar header 'apikey', não 'Authorization'
    headers = {
        "apikey": WHATSAPP_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "to": telefone,  # se na sua config antiga era 'to', pode manter 'to'
        "text": texto,
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
            "body": response.text,
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "detail": str(e),
        }
