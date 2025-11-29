from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List
import json

# Schemas (validação de entrada/saída)
from .schemas import (
    LeadIn,
    LeadOut,
    SendMessageIn,
    HistoricoServicoIn,
    HistoricoServicoOut,
)

# Serviços de regra de negócio
from .services.normalize import clean_phone, clean_name, lower_or_none
from .services.scoring import compute_score, stage_from_score

# Repositórios (acesso ao banco)
from .repositories.leads import upsert_lead, get_by_id, list_leads
from .repositories.events import add_event
from .repositories.historico_servicos import (
    adicionar_servico,
    list_history_for_lead,
)

# Saúde do banco
from .db import ping

app = FastAPI(
    title="API Projeto Automação",
    version="1.0.0",
    description="API de captação, qualificação e histórico de leads."
)


# =========================
#   HEALTH CHECK
# =========================

@app.get("/health")
def health_check():
    """
    Verifica se a API está de pé e se o banco responde.
    """
    db_ok = ping()
    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
    }


# =========================
#   WEBHOOK DE LEAD
# =========================

@app.post("/webhooks/lead", response_model=LeadOut)
def webhook_lead(payload: LeadIn):
    """
    Recebe um lead vindo de n8n / ManyChat / formulário, normaliza,
    calcula score, salva/atualiza no banco e registra evento.
    """

    # 1) Normalização básica
    nome = clean_name(payload.nome)
    email = lower_or_none(payload.email) if payload.email else None
    telefone = clean_phone(payload.telefone) if payload.telefone else None
    origem = payload.origem
    tags = payload.tags or []
    externo_id = payload.externo_id

    has_phone = bool(telefone)
    has_email = bool(email)

    # 2) Scoring e etapa
    score = compute_score(has_phone, has_email, origem, tags, servico_interesse=payload.servico_interesse, regiao_corpo=payload.regiao_corpo, disponibilidade=payload.disponibilidade,)
    etapa = stage_from_score(score)

    # 3) Monta dict pra camada de repositório
    data = {
        "nome": nome,
        "email": email,
        "telefone": telefone,
        "origem": origem,
        "tags_json": json.dumps(tags) if tags else None,
        "externo_id": externo_id,
        "score": score,
        "etapa": etapa,
    }

    # 4) Salva / atualiza lead
    lead_id = upsert_lead(data)

    # 5) Registra evento de entrada
    add_event(
        lead_id,
        "entrada",
        {
            "origem": origem,
            "externo_id": externo_id,
            "tags": tags,
            "score": score,
            "etapa": etapa,
        },
    )

    return LeadOut(lead_id=lead_id, score=score, etapa=etapa)


# =========================
#   LEADS (CRUD BÁSICO)
# =========================

@app.get("/leads/{lead_id}")
def get_lead(lead_id: int):
    """
    Retorna os dados brutos de um lead pelo ID.
    """
    lead = get_by_id(lead_id)
    if not lead:
        raise HTTPException(404, "Lead não encontrado")
    return lead


@app.get("/leads")
def get_leads(
    origem: Optional[str] = Query(None),
    etapa: Optional[str] = Query(None),
):
    """
    Lista até 200 leads, com filtros opcionais por origem e etapa.
    """
    return list_leads(origem, etapa)


# =========================
#   ENVIO DE MENSAGEM
# =========================

@app.post("/action/send-message")
def action_send_message(data: SendMessageIn):
    """
    Envia uma mensagem para o lead (whatsapp), registra o evento
    'mensagem_enviada' e retorna o resultado da integração externa.
    """
    lead = get_by_id(data.lead_id)
    if not lead:
        raise HTTPException(404, "Lead não encontrado")

    if not lead.get("telefone"):
        raise HTTPException(422, "Lead sem telefone")

    # Import local para evitar dependência circular
    from .services.messaging import send_whatsapp

    resp = send_whatsapp(lead["telefone"], data.texto)

    add_event(
        data.lead_id,
        "mensagem_enviada",
        {"telefone": lead["telefone"], "texto": data.texto, "resp": resp},
    )

    return {"ok": True, "result": resp}


# =========================
#   HISTÓRICO DE SERVIÇOS
# =========================

@app.post(
    "/leads/{lead_id}/historico",
    response_model=HistoricoServicoOut,
)
def create_history_entry(lead_id: int, payload: HistoricoServicoIn):
    """
    Cria um registro de serviço (procedimento agendado / realizado)
    para o lead informado.
    """
    # Garante que o lead existe
    lead = get_by_id(lead_id)
    if not lead:
        raise HTTPException(404, "Lead não encontrado")

    # Grava no histórico
    history_id = adicionar_servico(
        lead_id=lead_id,
        servico=payload.servico,
        data_servico=payload.data_servico,
        status=payload.status,
        ticket=payload.ticket,
        observacoes=payload.observacoes,
    )

    # Loga evento de atualização
    add_event(
        lead_id,
        "atualizacao",
        {
            "tipo": "historico_servico",
            "servico": payload.servico,
            "status": payload.status,
            "ticket": payload.ticket,
        },
    )

    # Busca o registro criado para devolver com created_at etc.
    history_items = list_history_for_lead(lead_id)
    created = next((h for h in history_items if h["id"] == history_id), None)
    if not created:
        raise HTTPException(500, "Erro ao recuperar histórico recém-criado")

    return created


@app.get(
    "/leads/{lead_id}/historico",
    response_model=List[HistoricoServicoOut],
)
def get_history_for_lead(lead_id: int):
    """
    Lista o histórico de serviços do lead (consultas, procedimentos, etc.).
    """
    lead = get_by_id(lead_id)
    if not lead:
        raise HTTPException(404, "Lead não encontrado")

    return list_history_for_lead(lead_id)

