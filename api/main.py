from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, Query

from api.schemas import LeadIn, LeadOut, LeadFilters, SendMessageIn
from services.normalize import clean_name, clean_phone, lower_or_none
from services.scoring import compute_score, stage_from_score
from repositories.leads import upsert_lead, get_by_id, list_leads
from repositories.events import add_event
from repositories.historico_servicos import (
    adicionar_servico,
    listar_historico_por_lead,
)

# opcional – se você tiver o ping configurado no db.py
try:
    from db import ping as db_ping
except ImportError:  # se não existir, a health só responde "ok" sem testar o banco
    db_ping = None


app = FastAPI(
    title="Leads API - Projeto Automação Estética",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Healthcheck
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> Dict[str, str]:
    api_status = "ok"
    db_status = "unknown"

    if db_ping is not None:
        try:
            db_ping()
            db_status = "ok"
        except Exception:
            db_status = "fail"

    return {"api": api_status, "db": db_status}


# ---------------------------------------------------------------------------
# Webhook de entrada de lead
# ---------------------------------------------------------------------------

@app.post("/webhooks/lead", response_model=LeadOut)
def webhook_lead(lead_in: LeadIn) -> LeadOut:
    """
    Recebe um lead de qualquer origem (WhatsApp, ManyChat, formulário etc.),
    normaliza os dados, calcula o score e grava/atualiza no banco.
    """

    # 1) Normalização básica
    data: Dict[str, Any] = lead_in.dict()

    data["nome"] = clean_name(data.get("nome"))
    data["telefone"] = clean_phone(data.get("telefone"))
    data["origem"] = lower_or_none(data.get("origem")) or "outro"
    # tags já vem como lista de strings em LeadIn

    # 2) Scoring simples com base nas respostas / dados
    score = compute_score(
        has_phone=bool(data.get("telefone")),
        has_email=bool(data.get("email")),
        origem=data.get("origem"),
        tags=data.get("tags"),
    )
    etapa = stage_from_score(score)

    data["score"] = score
    data["etapa"] = etapa

    # 3) Upsert do lead (insere ou atualiza)
    lead_id = upsert_lead(data)

    # 4) Registro de evento de entrada
    add_event(
        lead_id=lead_id,
        tipo="entrada",
        payload=data,
    )

    return LeadOut(lead_id=lead_id, score=score, etapa=etapa)


# ---------------------------------------------------------------------------
# Consultas de leads
# ---------------------------------------------------------------------------

@app.get("/leads")
def listar_leads(
    origem: Optional[str] = Query(None),
    etapa: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    """
    Lista leads com filtros básicos de origem e etapa.
    """
    filtros = LeadFilters(origem=origem, etapa=etapa)
    return list_leads(filtros)


@app.get("/leads/{lead_id}")
def obter_lead(lead_id: int) -> Dict[str, Any]:
    """
    Retorna os dados de um lead específico.
    """
    lead = get_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    return lead


# ---------------------------------------------------------------------------
# Histórico de serviços (designer de sobrancelha, limpeza de pele, depilação a laser)
# ---------------------------------------------------------------------------

class HistoricoServicoIn(SendMessageIn.__class__):  # gambizinha só pra reaproveitar BaseModel
    """
    Modelo rápido de entrada para histórico de serviços.

    Se quiser, pode mover isso para schemas.py depois.
    """
    # para evitar mexer no seu schemas.py agora, vamos declarar manualmente abaixo
    ...


# Como não temos o modelo no arquivo, vamos declarar explicitamente aqui:
from pydantic import BaseModel, Field  # noqa: E402 (import depois por clareza)


class HistoricoServicoIn(BaseModel):
    lead_id: int = Field(..., description="ID do lead relacionado")
    servico: str = Field(
        ...,
        description="Tipo de serviço (ex: 'depilacao_laser', 'designer_sobrancelha', 'limpeza_pele')",
    )
    data_servico: str = Field(
        ...,
        description="Data/hora do serviço no formato 'YYYY-MM-DD HH:MM:SS'",
    )
    status: str = Field(
        ...,
        description="Status do serviço (lead, agendado, confirmado, concluido, no_show, cancelado)",
    )
    ticket: Optional[float] = Field(
        None,
        description="Valor do ticket (opcional)",
    )
    observacoes: Optional[str] = Field(
        None,
        description="Observações livres (opcional)",
    )


@app.post("/leads/{lead_id}/historico-servicos")
def criar_historico_servico(
    lead_id: int,
    body: HistoricoServicoIn,
) -> Dict[str, Any]:
    """
    Cria um registro de histórico de serviço para um lead.
    """

    # Garantir que o lead_id da URL e do body batem
    if body.lead_id != lead_id:
        raise HTTPException(
            status_code=400,
            detail="lead_id do corpo e da URL precisam ser iguais",
        )

    # Verifica se o lead existe
    lead = get_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    historico_id = adicionar_servico(
        lead_id=body.lead_id,
        servico=body.servico,
        data_servico=body.data_servico,
        status=body.status,
        ticket=body.ticket,
        observacoes=body.observacoes,
    )

    return {"id": historico_id, "status": "created"}


@app.get("/leads/{lead_id}/historico-servicos")
def listar_historico_servicos(lead_id: int) -> List[Dict[str, Any]]:
    """
    Lista o histórico de serviços realizados / agendados para um lead.
    """
    # opcional: validar se o lead existe
    lead = get_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    return listar_historico_por_lead(lead_id)


# ---------------------------------------------------------------------------
# (Opcional) Endpoint para enviar mensagem manual (se for usar o services.messaging)
# ---------------------------------------------------------------------------

# from .services.messaging import send_whatsapp  # descomenta se quiser usar

# @app.post("/leads/{lead_id}/send-message")
# def send_message(lead_id: int, body: SendMessageIn):
#     lead = get_by_id(lead_id)
#     if not lead:
#         raise HTTPException(status_code=404, detail="Lead não encontrado")
#
#     telefone = lead.get("telefone")
#     if not telefone:
#         raise HTTPException(status_code=400, detail="Lead não possui telefone")
#
#     result = send_whatsapp(telefone=telefone, texto=body.texto)
#     return result
