"""
Schemas Pydantic para a API.

Todos os contratos de entrada e saída ficam aqui.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload de entrada flexível (compatível com testes e GHL)."""

    # Campos para teste manual / legado ZAF
    session_id: Optional[str] = Field(default=None, description="ID único da sessão.")
    message: Optional[Any] = Field(default=None, description="Mensagem do lead (pode ser string ou objeto).")
    
    # Campos reais do GHL Webhook
    contactId: Optional[str] = Field(default=None)
    conversationId: Optional[str] = Field(default=None)
    body: Optional[Any] = Field(default=None)
    type: Optional[str] = Field(default=None)
    locationId: Optional[str] = Field(default=None)
    
    # Campos extras para capturar o resto do payload
    model_config = {"extra": "allow"}


class ChatResponse(BaseModel):
    """Payload de resposta do webhook de chat."""

    session_id: str
    reply: str
    status: str = "accepted"


class ScenarioTestRunRequest(BaseModel):
    """Parâmetros para iniciar uma execução de cenários reais."""

    limit: Optional[int] = Field(default=5, ge=1)
    simulator: str = Field(default="auto")
    max_turns: int = Field(default=6, ge=1, le=20)
    max_parallel: int = Field(default=5, ge=1, le=5)
