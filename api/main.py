from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, Query
import json

from api.schemas import LeadIn, LeadOut, LeadFilters, SendMessageIn, LeadUpdateIn
from api.services.normalize import clean_name, clean_phone, lower_or_none
from api.services.scoring import compute_score, stage_from_score
from api.repositories.leads import upsert_lead, get_by_id, list_leads, update_lead
from api.repositories.events import add_event
from api.repositories.historico_servicos import (
    adicionar_servico,
    listar_historico_por_lead,
)
from api.services.messaging import send_whatsapp  # <--- IMPORT DO ENVIO WHATSAPP

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
    db_status = "ok"

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
    data: Dict[str, Any] = lead_in.dict()

    # Normalização
    data["nome"] = clean_name(data.get("nome"))
    data["telefone"] = clean_phone(data.get("telefone"))
    data["origem"] = lower_or_none(data.get("origem")) or "outro"

    # Garante que tags é uma lista
    tags = data.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    data["tags"] = tags

    # 👇 campo que o upsert_lead espera
    data["tags_json"] = json.dumps(tags, ensure_ascii=False)

    # Scoring
    score = compute_score(
        has_phone=bool(data.get("telefone")),
        has_email=bool(data.get("email")),
        origem=data.get("origem"),
        tags=tags,
    )
    etapa = stage_from_score(score)
    data["score"] = score
    data["etapa"] = etapa

    # Upsert no banco
    lead_id = upsert_lead(data)

    # Evento
    add_event(
        lead_id=lead_id,
        tipo="entrada",
        payload=data,
    )

    return LeadOut(lead_id=lead_id, score=score, etapa=etapa)


# ---------------------------------------------------------------------------
# Ações (envio de mensagem para lead)
# ---------------------------------------------------------------------------

@app.post("/action/send-message")
def action_send_message(body: SendMessageIn) -> Dict[str, Any]:
    """
    Envia uma mensagem de WhatsApp para o lead informado e registra o evento.

    Esse endpoint é pensado para o n8n:
    - recebe lead_id e texto
    - busca o telefone do lead no banco
    - chama o serviço de envio de WhatsApp
    - registra evento de mensagem enviada (ou erro de envio)
    """

    # 1) Buscar o lead
    lead = get_by_id(body.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    telefone = lead.get("telefone")
    if not telefone:
        raise HTTPException(
            status_code=400,
            detail="Lead não possui telefone cadastrado",
        )

    # 2) Enviar mensagem pelo WhatsApp
    result = send_whatsapp(telefone=telefone, texto=body.texto)

    # 3) Definir tipo de evento conforme resultado
    tipo_evento = "mensagem_enviada"
    if isinstance(result, dict) and result.get("status") == "error":
        tipo_evento = "erro_envio"

    # 4) Registrar evento no lead_events
    add_event(
        lead_id=body.lead_id,
        tipo=tipo_evento,
        payload={
            "texto": body.texto,
            "telefone": telefone,
            "whatsapp_result": result,
        },
    )

    # 5) Retornar algo simples para o n8n
    if isinstance(result, dict):
        return {
            "status": result.get("status", "unknown"),
            "detail": result.get("detail"),
        }

    # fallback se o serviço de envio retornar outro tipo
    return {
        "status": "unknown",
        "detail": str(result),
    }


# ---------------------------------------------------------------------------
# Ação para ATUALIZAR dados do lead (/action/update-lead)
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field  # noqa: E402 (já é usado abaixo também)


class LeadUpdateIn(BaseModel):
    """
    Body para o endpoint /action/update-lead.

    A ideia é o n8n/Agente de IA mandar algo nesse formato:

    {
      "lead_id": 2,
      "lead_update": {
        "servico_interesse": "limpeza_pele",
        "regiao_corpo": "rosto",
        "disponibilidade": "manhã",
        "concluiu_qualificacao": true
      }
    }
    """
    lead_id: int = Field(..., description="ID do lead a ser atualizado")
    lead_update: Dict[str, Any] = Field(
        ...,
        description="Campos a atualizar no cadastro do lead",
    )


@app.post("/action/update-lead")
def action_update_lead(body: LeadUpdateIn) -> Dict[str, Any]:
    """
    Atualiza campos do lead no banco, usando o mesmo upsert_lead.

    Pensado para ser chamado pelo n8n depois que o agente de IA
    extraiu as respostas de qualificação (serviço de interesse, região
    do corpo, disponibilidade, etc.).
    """

    # 1) Buscar lead atual
    lead_atual = get_by_id(body.lead_id)
    if not lead_atual:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    # 2) Montar dicionário de atualização
    updates = dict(body.lead_update or {})

    # --- Normalizações básicas nos campos mais importantes ---------
    if "nome" in updates:
        updates["nome"] = clean_name(updates["nome"])

    if "telefone" in updates:
        updates["telefone"] = clean_phone(updates["telefone"])

    if "origem" in updates:
        updates["origem"] = lower_or_none(updates["origem"]) or "outro"

    # tags: aceita string única ou lista e atualiza tags_json
    if "tags" in updates:
        tags = updates["tags"] or []
        if isinstance(tags, str):
            tags = [tags]
        updates["tags"] = tags
        updates["tags_json"] = json.dumps(tags, ensure_ascii=False)

    # 3) Recalcular score/etapa se algum campo relevante mudou
    if any(k in updates for k in ("telefone", "email", "origem", "tags")):
        telefone = updates.get("telefone", lead_atual.get("telefone"))
        email = updates.get("email", lead_atual.get("email"))
        origem = updates.get("origem", lead_atual.get("origem"))
        tags_calc = updates.get("tags", lead_atual.get("tags") or [])

        score = compute_score(
            has_phone=bool(telefone),
            has_email=bool(email),
            origem=origem,
            tags=tags_calc,
        )
        updates["score"] = score
        updates["etapa"] = stage_from_score(score)

    # 4) Garante que os campos de identificação continuem os mesmos
    data_to_save: Dict[str, Any] = dict(lead_atual)
    data_to_save.update(updates)

    # MUITO importante: manter o externo_id/telefone/email originais
    # para o upsert bater no mesmo registro.
    # (se o seu upsert usar outro campo único, ele já está em lead_atual)
    if "id" in data_to_save:
        # alguns ORMs usam "id", outros "lead_id"; aqui só garantimos que exista
        data_to_save["id"] = lead_atual.get("id", body.lead_id)

    # 5) Salvar via upsert_lead (vai fazer UPDATE no registro existente)
    lead_id_result = upsert_lead(data_to_save)

    # 6) Registrar evento de atualização
    add_event(
        lead_id=body.lead_id,
        tipo="atualizacao",
        payload={
            "updates": updates,
        },
    )

    return {
        "lead_id": lead_id_result,
        "updated_fields": list(updates.keys()),
    }


# ---------------------------------------------------------------------------
# Consultas de leads
# ---------------------------------------------------------------------------

@app.post("/action/update-lead", response_model=LeadOut, tags=["Leads"])
def action_update_lead(payload: LeadUpdateIn):
    """
    Endpoint que o n8n / agente de IA vai chamar para atualizar os dados
    de um lead já existente.

    Exemplo de JSON que o n8n deve enviar:

    {
      "lead_id": 2,
      "servico_interesse": "Botox",
      "regiao_corpo": "rosto",
      "disponibilidade": "período da manhã",
      "etapa": "qualificado",
      "score": 80
    }
    """

    # Garante que o lead existe
    lead = get_by_id(payload.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    # Monta só os campos que realmente serão atualizados
    update_data = payload.dict(exclude_unset=True, exclude={"lead_id"})

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Nenhum campo para atualizar foi enviado.",
        )

    # Atualiza no banco
    update_lead(payload.lead_id, update_data)

    # Busca de novo pra devolver o lead atualizado
    updated = get_by_id(payload.lead_id)
    return updated


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
