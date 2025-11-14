import re

def clean_phone(raw: str | None) -> str | None:
    """Remove todos os caracteres não numéricos do telefone e retorna apenas dígitos."""
    if not raw: return None
    digits = re.sub(r"\D", "", raw)
    return digits or None

def clean_name(raw: str) -> str:
    """Remove espaços extras e normaliza nome."""
    return " ".join(raw.strip().split())

def lower_or_none(s: str | None) -> str | None:
    """Converte para minúsculo se existir valor, caso contrário retorna None."""
    return s.lower() if s else None

