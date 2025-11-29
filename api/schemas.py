from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Literal, Dict, Any

from pydantic import BaseModel, EmailStr, Field


# =========================
#   Tipos auxiliares (enums)
# =========================

LeadOrigem = Literal["instagram", "manychat", "site", "outro"]
LeadEtapa = Literal["novo", "qualificado", "cliente"]

ServicoTipo = Literal["depilacao_laser", "designer_sobrancelha", "limpeza_pele"]
ServicoStatus = Literal["lead", "agendado", "confirmado", "concluido", "no_show", "cancelado"]

LeadEventTipo = Literal["entrada", "mensagem_enviada", "erro_envio", "followup", "atualizacao"]


# =========================
#   LEADS
# =========================

class LeadIn(BaseModel):
    """
    Modelo de entrada de lead recebido via webhook.
    Esses campos vêm do n8n / Evolution / ManyChat, etc.
    """
    nome: str = Field(..., min_length=1, description="Nome completo do lead")
    email: Optional[EmailStr] = Field(
        None, description="E-mail válido do lead"
    )
    telefone: Optional[str] = Field(
        None, description="Telefone com DDI e DDD"
    )
    origem: LeadOrigem = Field(
        "outro",
        description="Origem do lead (instagram, manychat, site, etc.)",
    )
    tags: Optional[List[str]] = Field(
        None, description="Lista de tags do lead"
    )
    externo_id: Optional[str] = Field(
        None, description="ID externo (ManyChat, formulário, etc.)"
    )


class LeadOut(BaseModel):
    """
    Resposta padrão do webhook de lead após salvar e calcular score.
    """
    lead_id: int
    score: int
    etapa: LeadEtapa


class LeadDetail(BaseModel):
    """
    (Opcional) Modelo completo de um lead para listagem/detalhe.
    Pode ser usado em /leads, /leads/{id}, etc.
    """
    id: int
    nome: str
    email: Optional[EmailStr]
    telefone: Optional[str]
    origem: LeadOrigem
    etapa: LeadEtapa
    score: int
    tags: Optional[List[str]]
    externo_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    servico_interesse: Optional[str] = None
    regiao_corpo: Optional[str] = None
    disponibilidade: Optional[str] = None


    class Config:
        orm_mode = True  # Pydantic v1: permite ler objetos vindos do cursor/ORM


class LeadFilters(BaseModel):
    """
    Filtros para listagem de leads (por origem, etapa, etc.).
    """
    origem: Optional[LeadOrigem] = None
    etapa: Optional[LeadEtapa] = None


# =========================
#   ENVIO DE MENSAGEM
# =========================

class SendMessageIn(BaseModel):
    """
    Corpo do request para enviar mensagem ao lead.
    """
    lead_id: int
    texto: str


# =========================
#   EVENTOS DO LEAD (lead_events)
# =========================

class LeadEventCreate(BaseModel):
    """
    Registro de evento associado a um lead (log de automação).
    """
    lead_id: int
    tipo: LeadEventTipo
    payload: Dict[str, Any]


# =========================
#   HISTÓRICO DE SERVIÇOS (historico_servicos)
# =========================

class HistoricoServicoIn(BaseModel):
    """
    Entrada para registrar um serviço executado / agendado para o lead.
    """
    lead_id: int
    servico: ServicoTipo
    data_servico: datetime
    status: ServicoStatus = "lead"
    ticket: Optional[Decimal] = None
    observacoes: Optional[str] = None


class HistoricoServicoOut(HistoricoServicoIn):
    """
    Resposta com histórico de serviço já salvo no banco.
    """
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
