import os, requests
from typing import Dict, Any

WHATSAPP_API = os.getenv("WHATSAPP_API_URL", "")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")

def send_whatsapp(telefone: str, texto: str) -> dict[str, Any]:
    """Envia uma mensagem de texto pelo Whatsapp API"""
    if not WHATSAPP_API or not WHATSAPP_TOKEN:
        return {"status":"disabled", "detail":"configure WHATSAPP_API_URL/WHATSAPP_TOKEN"}
    
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    payload = {"to": telefone, "text": texto}

    try:
       response = requests.post(WHATSAPP_API, headers=headers, json=payload, timeout=15)
       return {
           "status": response.status_code,
           "body": response.text
       }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "detail": str(e)
        }
    