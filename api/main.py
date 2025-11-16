from fastapi import FastAPI, HTTPException, Query
from typing import Optional
import json

# Schemas (validação de entrada/saída)
from .schemas import LeadIn, LeadOut, SendMessageIn

# Serviços de regra do negócio
from .services.normalize import clean_phone, clean_name, lower_or_none
from .services.scoring import compute_score, stage_from_score

# Repositórios (acesso ao banco)
from .repositories.leads import upsert_lead, get_by_id, list_leads
from .repositories.events import add_event

# Saúde do banco
from .db import ping


app = FastAPI(title="Leads API", version="0.1.0")

# 1) Healthcheck - Confere a API e Banco


@app.get("/health")
def health():
    """
    Retorna status básico da API e do banco.
    GET /health -> {"api": "ok", "db":"ok"}
    """
    return {"api": "ok", "db": "ok" if ping() else "fail"}

# 2) Webhook de lead - entrada principal de dados


@app.post("/webhooks/lead", response_model=LeadOut)
def webhook_lead(payload: LeadIn):
    email = lower_or_none(payload.email)
    telefone = clean_phone(payload.telefone)
    if not email and not telefone:
        raise HTTPException(422, "Informe ao menos email ou telefone")

    nome = clean_name(payload.nome)
    origem = payload.origem or "outro"
    tags = payload.tags or []

    # Regra do negócio (score + etapa)
    score = compute_score(bool(telefone), bool(email), origem, tags)
    etapa = stage_from_score(score)

    # Monta o pacote para pesistir
    lead_data = {
        "nome": nome,
        "email": email,
        "telefone": telefone,
        "origem": origem,
        "tags_json": json.dumps(tags) if tags else None,
        "externo_id": payload.externo_id,
        "score": score,
        "etapa": etapa,
    }

    # Upsert no banco (insere se novo; atualiza se já existe por email/telefone)
    lead_id = upsert_lead(lead_data)
    add_event(lead_id, "entrada", {
              "origem": origem, "score": score, "tags": tags})
    return {"lead_id": lead_id, "score": score, "etapa": etapa}

# 3) Listagem de leads - com filtros (query params)


@app.get("/leads")
def get_leads(origem: Optional[str] = Query(None), etapa: Optional[str] = Query(None)):
    """
    Lista até 200 leads, podendo filtrar por ?origem= e ?etapa=
    Ex.: GET /leads?origem=manychat&etapa=qualificado
    """
    return list_leads(origem, etapa)

# 4) Detalhe de um lead - path param


@app.get("/leads/{lead_id}")
def lead_detail(lead_id: int):
    lead = get_by_id(lead_id)
    if not lead:
        raise HTTPException(404, "Lead não encontrado")
    return lead

# 5) Ação: enviar mensagem - integra com whatsapp API


@app.post("/action/send-message")
def send_message(data: SendMessageIn):
    """
    Envia uma mensagem para o lead (whatsapp), registra o evento 'mensagem_enviada'
    e retorna o status da integração externa 
    """
    lead = get_by_id(data.lead_id)
    if not lead:
        raise HTTPException(404, "Lead não encontrado")
    if not lead.get("telefone"):
        raise HTTPException(422, "Lead sem telefone")

    from .services.messaging import send_whatsapp

    resp = send_whatsapp(lead["telefone"], data.texto)
    add_event(data.lead_id, "mensagem_enviada", resp)

    return {"ok": True, "result": resp}
