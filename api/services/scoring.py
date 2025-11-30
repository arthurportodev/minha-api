from typing import List, Optional


def compute_score(
    has_phone: bool,
    has_email: bool,
    origem: Optional[str],
    tags: Optional[List[str]] = None,
) -> int:
    """
    Calcula um score de 0 a 100 com base em informações simples
    do lead (telefone, e-mail, origem, tags etc.).
    """

    score = 0

    # Telefone é muito importante
    if has_phone:
        score += 40

    # E-mail ajuda bastante
    if has_email:
        score += 20

    # Origem do lead
    origem = (origem or "").lower()

    if origem in ("instagram", "manychat", "whatsapp"):
        score += 20
    elif origem in ("site", "formulario"):
        score += 10
    # "outro" ou vazio não ganha bônus

    # Tags podem adicionar mais pontos
    tags = tags or []

    tags_lower = [t.lower() for t in tags]

    # Interesse direto em estética
    if any(t in tags_lower for t in ["estetica", "limpeza_pele", "laser", "sobrancelha"]):
        score += 10

    # Lead quente
    if "urgente" in tags_lower or "quer_agendar" in tags_lower:
        score += 10

    # Garante limite entre 0 e 100
    score = max(0, min(score, 100))
    return score


def stage_from_score(score: int) -> str:
    """
    Converte o score em etapa do funil.
    """

    if score >= 70:
        return "cliente"
    elif score >= 40:
        return "qualificado"
    else:
        return "novo"
