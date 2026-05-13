"""
Lead Model — Gestão de estado e funil de qualificação.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class LeadStatus(str, Enum):
    """Estados possíveis do lead no funil comercial."""

    NEW_LEAD = "NEW_LEAD"
    QUALIFYING = "QUALIFYING"
    QUALIFIED = "QUALIFIED"
    SCHEDULED = "SCHEDULED"
    SCHEDULING = "SCHEDULING"
    HANDOFF = "HANDOFF"
    LOST = "LOST"


class VehicleFocus(BaseModel):
    """Estado do veículo que é o foco atual da conversa."""

    current: Optional[str] = None
    last_valid: Optional[str] = None
    active_filters: Optional[dict[str, Any]] = None
    alternatives_shown: list[Any] = Field(default_factory=list)


class LeadQualification(BaseModel):
    """Ficha de qualificação e estado da conversa."""

    # Identificação
    nome: Optional[str] = None
    whatsapp: Optional[str] = None

    # Interesse
    interesse: Optional[str] = None
    veiculo_interesse: Optional[str] = None
    tipo_veiculo: Optional[str] = None
    marca_preferida: Optional[str] = None
    modelo_preferido: Optional[str] = None
    faixa_preco: Optional[str] = None
    ano_minimo: Optional[int] = None
    cambio: Optional[str] = None

    # Intenção e Troca
    intencao: Optional[str] = None
    tem_troca: Optional[bool] = None
    veiculo_troca: Optional[str] = None
    motivo_troca: Optional[str] = None

    # Negociação e Qualificação
    motivacao: Optional[str] = None
    negociacao: Optional[str] = None
    precisa_financiamento: Optional[bool] = None
    cidade: Optional[str] = None
    e_local: Optional[bool] = None
    observacoes: Optional[str] = None

    # Visita e Handoff
    data_visita: Optional[str] = None
    motivo_handoff: Optional[str] = None

    # Metadados de Sessão
    status: LeadStatus = LeadStatus.NEW_LEAD
    lead_stage: str = "NEW_LEAD"
    conversation_summary: Optional[str] = None
    last_interaction: Optional[str] = None
    vehicle_focus: VehicleFocus = Field(default_factory=VehicleFocus)

    # Memória de respostas curtas (checkpoint)
    lead_answers: dict[str, Any] = Field(default_factory=dict)

    def completeness_score(self) -> int:
        """Calcula o percentual de preenchimento da qualificação (6 campos)."""
        total = 6
        filled = 0
        if self.nome:
            filled += 1
        if self.interesse or self.veiculo_interesse or self.modelo_preferido:
            filled += 1
        if self._intencao_texto():
            filled += 1
        if self.motivacao or self.motivo_troca:
            filled += 1
        if self.negociacao or self.precisa_financiamento is not None:
            filled += 1
        if self.cidade or self.e_local is not None:
            filled += 1
        return int((filled / total) * 100)

    def set_vehicle_focus(
        self,
        vehicle: Optional[str] = None,
        active_filters: Optional[dict[str, Any]] = None,
        alternatives_shown: Optional[list[Any]] = None,
    ) -> None:
        """Atualiza o veículo em foco."""
        if vehicle:
            self.vehicle_focus.current = vehicle
            self.vehicle_focus.last_valid = vehicle
            self.veiculo_interesse = vehicle
        if active_filters:
            self.vehicle_focus.active_filters = active_filters
        if alternatives_shown is not None:
            self.vehicle_focus.alternatives_shown = alternatives_shown

    def trade_vehicle_has_details(self) -> bool:
        """Verifica se o veículo de troca tem detalhes suficientes."""
        if not self.veiculo_troca:
            return False
        text = str(self.veiculo_troca).lower()
        # Busca por um ano (4 dígitos) no texto
        import re

        has_year = bool(re.search(r"\b(19|20)\d{2}\b", text))
        return has_year

    def _intencao_texto(self) -> str | None:
        if self.intencao:
            return self.intencao
        if self.tem_troca is True:
            return "Troca"
        if self.tem_troca is False:
            return "Compra à vista/Financiamento"
        return None

    def get_missing_fields(self) -> list[str]:
        """Retorna campos ainda não preenchidos do funil de qualificação."""
        missing = []
        if not self.nome:
            missing.append("👤 Nome")
        if not (self.interesse or self.veiculo_interesse):
            missing.append("🚗 Interesse")
        if not self._intencao_texto() or (self.tem_troca is True and not self.trade_vehicle_has_details()):
            missing.append("🔄 Intenção")
        if not self.motivacao:
            missing.append("💬 Motivação")
        if not (self.negociacao or self.precisa_financiamento is not None):
            missing.append("💰 Negociação")
        if not self.cidade:
            missing.append("📍 Cidade")
        return missing

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário serializável para a LLM."""
        data = self.model_dump()
        data["status"] = self.status.value
        data["lead_stage"] = self.lead_stage
        data["veiculo_interesse"] = self.veiculo_interesse
        data["qualificacao_pendente"] = self.get_missing_fields()
        data["qualificacao"] = {
            "nome": self.nome,
            "interesse": self.interesse or self.veiculo_interesse,
            "intencao": self._intencao_texto(),
            "troca": self.veiculo_troca if self.tem_troca else "Não informada/Não possui",
            "motivacao": self.motivacao or self.motivo_troca,
            "negociacao": self.negociacao,
            "cidade": self.cidade,
        }
        return data

    def has_exact_schedule(self) -> bool:
        """Verifica se existe um horário exato agendado."""
        if not self.data_visita:
            return False
        # Verifica se tem 'T' ou um padrão de hora
        return "T" in self.data_visita or ":" in self.data_visita
