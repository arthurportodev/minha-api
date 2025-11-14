from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any, Dict, List

class LeadIn(BaseModel):
    """Modelo de entrada de lead recebido via webhook."""
    nome: str = Field(..., min_length=1, description= "Nome completo do lead")
    email: Optional[EmailStr] = Field(None, description= "E-mail válido do lead")
    telefone: Optional[str] = Field(None, description= "Telefone com DDI e DDD")
    origem: Optional[str] = Field("outro", description= "Origem do lead (ManyChat, form, lp, etc.)")
    tags: Optional[List[str]] = Field(None, description= "Lista de tags do lead")
    externo_id: Optional[str] = Field(None, description= "ID externo (ManyChat, formulário, etc.)")

class LeadOut(BaseModel):
    lead_id: int
    score: int
    etapa: str

class SendMessageIn(BaseModel):
    lead_id: int
    texto: str

class LeadFilters(BaseModel):
    origem: Optional[str] = None
    etapa: Optional[str] = None 