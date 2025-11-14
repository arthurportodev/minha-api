def compute_score(has_phone: bool, has_email: bool, origem: str, tags: list[str] | None) -> int:
    """Calcula a pontuação do lead com base em critérios simples de qualificação."""
    score = 0
    if has_phone: score += 30
    if has_email: score += 10
    if origem == "manychat": score += 20
    if tags and any(t in {"interesse_alto", "quente"} for t in tags): score +=20
    return max(0, min(score, 100))

def stage_from_score(score: int) -> str:
    return "qualificado" if score >= 60 else "novo"