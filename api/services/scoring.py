from typing import Optional, List


def compute_score(
    has_phone: bool,
    has_email: bool,
    origem: str,
    tags: Optional[List[str]] = None,
    servico_interesse: Optional[str] = None,
    regiao_corpo: Optional[str] = None,
    disponibilidade: Optional[str] = None,
) -> int:
    """
    Calcula um score de 0 a 100 para o lead, pensando no funil da clínica de estética.

    - Bloco 1: contato (telefone/email)
    - Bloco 2: serviço de interesse (designer, limpeza, depilação)
    - Bloco 3: detalhes específicos de depilação (região + histórico em tags)
    - Bloco 4: disponibilidade
    """
    score = 0
    tags = tags or []

    # =========================
    # 1) CONTATO (até 35 pts)
    # =========================
    if has_phone:
        # foco forte em quem tem telefone válido (WhatsApp)
        score += 30
    if has_email:
        score += 5

    # =========================
    # 2) SERVIÇO DE INTERESSE (até 30 pts)
    # =========================
    # servico_interesse pode vir do payload ou ser inferido por tags,
    # então deixamos opcional.
    si = (servico_interesse or "").lower()

    if si == "depilacao_laser":
        score += 30
    elif si == "limpeza_pele":
        score += 20
    elif si == "designer_sobrancelha":
        score += 10
    # se não vier nada, não soma aqui

    # =========================
    # 3) DETALHES DE DEPILAÇÃO A LASER (até 30 pts)
    # =========================
    if si == "depilacao_laser":
        # 3.1 Região do corpo (até 15)
        regiao = (regiao_corpo or "").lower()

        if any(p in regiao for p in ["perna", "coxa", "corpo inteiro", "corpo todo"]):
            score += 15
        elif any(p in regiao for p in ["virilha", "axila", "rosto", "braço", "braco"]):
            score += 10
        elif regiao:
            score += 5

        # 3.2 Histórico (até 15)
        # essas tags você configura no n8n conforme a resposta do lead:
        # - "laser_outra_clinica"
        # - "laser_parou"
        # - "laser_primeira_vez"
        if "laser_outra_clinica" in tags:
            score += 15
        elif "laser_parou" in tags:
            score += 10
        elif "laser_primeira_vez" in tags:
            score += 5

    # =========================
    # 4) DISPONIBILIDADE (até 5 pts)
    # =========================
    disp = (disponibilidade or "").lower()
    opcoes = ["manhã", "manha", "tarde", "noite", "semana", "sábado", "sabado"]
    encontradas = [p for p in opcoes if p in disp]

    # se a pessoa tem mais de um período/dia possível, é mais fácil encaixar
    if len(encontradas) >= 2:
        score += 5

    # Garante que fica entre 0 e 100
    return max(0, min(score, 100))


def stage_from_score(score: int) -> str:
    """
    Traduz o score em etapa do funil.
    Aqui eu deixo 'cliente' para ser setado manualmente (quando a venda fechar),
    e uso o score só pra decidir 'novo' x 'qualificado'.
    """
    if score >= 60:
        return "qualificado"
    return "novo"
