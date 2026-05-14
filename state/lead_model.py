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


class TrackedVehicle(BaseModel):
    """Resumo serializável de um veículo citado ou apresentado ao lead."""

    vehicle_key: Optional[str] = None
    titulo: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    ano: Optional[int] = None
    preco: Optional[int] = None
    cambio: Optional[str] = None
    source: Optional[str] = None


class VehicleJourney(BaseModel):
    """Memória comercial de múltiplos veículos dentro da mesma conversa."""

    greeting_vehicle: Optional[str] = None
    primary_interest: Optional[str] = None
    secondary_interests: list[str] = Field(default_factory=list)
    current_focus: Optional[str] = None
    current_request: Optional[str] = None
    photo_target: Optional[str] = None
    scheduling_target: Optional[str] = None
    qualification_target: Optional[str] = None
    mentioned_vehicles: list[TrackedVehicle] = Field(default_factory=list)
    presented_vehicles: list[TrackedVehicle] = Field(default_factory=list)
    last_presented_vehicles: list[TrackedVehicle] = Field(default_factory=list)


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
    km_troca: Optional[str] = None
    quitado_troca: Optional[bool] = None
    estado_troca: Optional[str] = None
    fotos_troca_recebidas: Optional[bool] = None
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
    vehicle_journey: VehicleJourney = Field(default_factory=VehicleJourney)

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
            self.vehicle_journey.current_focus = vehicle
            self.vehicle_journey.qualification_target = vehicle
            self._set_interest_priority(vehicle)
        if active_filters:
            self.vehicle_focus.active_filters = active_filters
        if alternatives_shown is not None:
            self.vehicle_focus.alternatives_shown = alternatives_shown
            self.register_presented_vehicles(alternatives_shown, source="alternatives_shown")

    def _make_tracked_vehicle(
        self,
        vehicle: Any,
        source: Optional[str] = None,
    ) -> TrackedVehicle:
        if isinstance(vehicle, TrackedVehicle):
            tracked = vehicle.model_copy()
            if source:
                tracked.source = source
            return tracked

        if isinstance(vehicle, dict):
            titulo = str(vehicle.get("titulo") or vehicle.get("modelo") or vehicle.get("marca") or "").strip()
            return TrackedVehicle(
                vehicle_key=str(vehicle.get("vehicle_key") or "").strip() or None,
                titulo=titulo,
                marca=vehicle.get("marca"),
                modelo=vehicle.get("modelo"),
                ano=vehicle.get("ano"),
                preco=vehicle.get("preco"),
                cambio=vehicle.get("cambio"),
                source=source,
            )

        title = str(vehicle).strip()
        return TrackedVehicle(titulo=title, source=source)

    def _merge_tracked_vehicle_list(
        self,
        current_list: list[TrackedVehicle],
        incoming: list[Any],
        source: Optional[str] = None,
    ) -> list[TrackedVehicle]:
        merged = list(current_list)
        known_titles = {item.titulo.lower().strip(): index for index, item in enumerate(merged)}

        for raw_vehicle in incoming:
            tracked = self._make_tracked_vehicle(raw_vehicle, source=source)
            title_key = tracked.titulo.lower().strip()
            if not title_key:
                continue
            if title_key in known_titles:
                existing = merged[known_titles[title_key]]
                merged[known_titles[title_key]] = existing.model_copy(
                    update={
                        "vehicle_key": tracked.vehicle_key or existing.vehicle_key,
                        "marca": tracked.marca or existing.marca,
                        "modelo": tracked.modelo or existing.modelo,
                        "ano": tracked.ano or existing.ano,
                        "preco": tracked.preco or existing.preco,
                        "cambio": tracked.cambio or existing.cambio,
                        "source": tracked.source or existing.source,
                    }
                )
            else:
                known_titles[title_key] = len(merged)
                merged.append(tracked)

        return merged

    def _set_interest_priority(self, vehicle_title: str) -> None:
        title = str(vehicle_title).strip()
        if not title:
            return
        if not self.vehicle_journey.primary_interest:
            self.vehicle_journey.primary_interest = title
            return
        if title == self.vehicle_journey.primary_interest:
            return
        if title not in self.vehicle_journey.secondary_interests:
            self.vehicle_journey.secondary_interests.append(title)

    def register_vehicle_mentions(
        self,
        vehicles: list[Any],
        source: Optional[str] = None,
    ) -> None:
        if not vehicles:
            return
        self.vehicle_journey.mentioned_vehicles = self._merge_tracked_vehicle_list(
            self.vehicle_journey.mentioned_vehicles,
            vehicles,
            source=source,
        )
        for vehicle in vehicles:
            tracked = self._make_tracked_vehicle(vehicle, source=source)
            if tracked.titulo:
                self._set_interest_priority(tracked.titulo)

    def register_presented_vehicles(
        self,
        vehicles: list[Any],
        source: Optional[str] = None,
    ) -> None:
        if vehicles is None:
            return
        merged = self._merge_tracked_vehicle_list([], vehicles, source=source)
        self.vehicle_journey.last_presented_vehicles = merged
        self.vehicle_journey.presented_vehicles = self._merge_tracked_vehicle_list(
            self.vehicle_journey.presented_vehicles,
            vehicles,
            source=source,
        )
        self.register_vehicle_mentions(vehicles, source=source)

    def set_vehicle_targets(
        self,
        current_request: Optional[str] = None,
        current_focus: Optional[str] = None,
        photo_target: Optional[str] = None,
        scheduling_target: Optional[str] = None,
        qualification_target: Optional[str] = None,
    ) -> None:
        if current_request:
            self.vehicle_journey.current_request = current_request
            self._set_interest_priority(current_request)
        if current_focus:
            self.vehicle_journey.current_focus = current_focus
            self.vehicle_focus.current = current_focus
            self.vehicle_focus.last_valid = current_focus
            self.veiculo_interesse = current_focus
            self._set_interest_priority(current_focus)
        if photo_target:
            self.vehicle_journey.photo_target = photo_target
            self._set_interest_priority(photo_target)
        if scheduling_target:
            self.vehicle_journey.scheduling_target = scheduling_target
            self._set_interest_priority(scheduling_target)
        if qualification_target:
            self.vehicle_journey.qualification_target = qualification_target
            self._set_interest_priority(qualification_target)

        if self.vehicle_journey.primary_interest:
            self.veiculo_interesse = self.vehicle_journey.primary_interest

    def trade_vehicle_has_details(self) -> bool:
        """Verifica se o veículo de troca tem detalhes suficientes."""
        if not self.veiculo_troca:
            return False
        text = str(self.veiculo_troca).lower()
        # Busca por um ano (4 dígitos) no texto
        import re

        has_year = bool(re.search(r"\b(19|20)\d{2}\b", text))
        return has_year

    def get_missing_trade_fields(self) -> list[str]:
        """Retorna os dados ainda pendentes para avaliar a troca."""
        if self.tem_troca is not True:
            return []

        missing = []
        if not self.trade_vehicle_has_details():
            missing.append("ano/modelo")
        if not self.km_troca:
            missing.append("km")
        if self.quitado_troca is None:
            missing.append("quitado")
        if not self.estado_troca:
            missing.append("estado")
        if self.fotos_troca_recebidas is not True:
            missing.append("fotos")
        return missing

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
        if not self._intencao_texto():
            missing.append("🔄 Intenção")
        elif self.get_missing_trade_fields():
            missing.append("🚘 Dados da Troca")
        if not self.motivacao:
            missing.append("💬 Motivação")
        if not (self.negociacao or self.precisa_financiamento is not None):
            missing.append("💰 Negociação")
        if not self.cidade:
            missing.append("📍 Cidade")
        return missing

    def next_qualification_field(self) -> str | None:
        """Retorna o próximo campo prioritário da qualificação."""
        if not self.nome:
            return "nome"
        if not (self.interesse or self.veiculo_interesse):
            return "interesse"
        if not self._intencao_texto():
            return "intencao"

        missing_trade = self.get_missing_trade_fields()
        if missing_trade:
            return "veiculo_troca"
        if not self.motivacao:
            return "motivacao"
        if not (self.negociacao or self.precisa_financiamento is not None):
            return "negociacao"
        if not self.cidade:
            return "cidade"
        if self.data_visita and not self.has_exact_schedule():
            return "data_visita"
        return None

    def next_qualification_question(self) -> str | None:
        """Sugere a próxima pergunta curta de qualificação."""
        next_field = self.next_qualification_field()
        if next_field == "nome":
            return "Como posso te chamar?"
        if next_field == "interesse":
            return "Qual carro você está procurando?"
        if next_field == "intencao":
            return "Você pensa em compra direta ou em colocar um carro na troca?"
        if next_field == "veiculo_troca":
            missing_trade = self.get_missing_trade_fields()
            if "ano/modelo" in missing_trade:
                return "Qual o ano e o modelo do seu carro de troca?"
            if "km" in missing_trade:
                return "Quantos km ele tem hoje?"
            if "quitado" in missing_trade:
                return "Esse carro está quitado?"
            if "estado" in missing_trade:
                return "Como está o estado dele?"
            if "fotos" in missing_trade:
                return "Pode me mandar algumas fotos dele: frente, traseira, laterais e interior?"
        if next_field == "motivacao":
            if self.tem_troca is True:
                return "O que te fez pensar em trocar de carro agora?"
            return "O que te atraiu nesse modelo?"
        if next_field == "negociacao":
            return "Você pretende financiar a diferença ou pagar à vista?"
        if next_field == "cidade":
            return "Em qual cidade você está?"
        if next_field == "data_visita":
            return "Qual horário exato fica melhor pra você?"
        return None

    def proximo_passo(self) -> str:
        """Resumo textual do próximo passo comercial."""
        if self.data_visita and not self.has_exact_schedule():
            return "Definir horário exato da visita."
        question = self.next_qualification_question()
        if question:
            return question
        return "Qualificação principal concluída."

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário serializável para a LLM."""
        data = self.model_dump()
        data["status"] = self.status.value
        data["lead_stage"] = self.lead_stage
        data["veiculo_interesse"] = self.veiculo_interesse
        data["qualificacao_pendente"] = self.get_missing_fields()
        data["vehicle_journey"] = self.vehicle_journey.model_dump()
        data["qualificacao"] = {
            "nome": self.nome,
            "interesse": self.interesse or self.veiculo_interesse,
            "intencao": self._intencao_texto(),
            "troca": self.veiculo_troca if self.tem_troca else "Não informada/Não possui",
            "km_troca": self.km_troca,
            "quitado_troca": self.quitado_troca,
            "estado_troca": self.estado_troca,
            "fotos_troca_recebidas": self.fotos_troca_recebidas,
            "motivacao": self.motivacao or self.motivo_troca,
            "negociacao": self.negociacao,
            "cidade": self.cidade,
        }
        data["dados_troca_pendentes"] = self.get_missing_trade_fields()
        data["next_qualification_field"] = self.next_qualification_field()
        data["next_qualification_question"] = self.next_qualification_question()
        return data

    def has_exact_schedule(self) -> bool:
        """Verifica se existe um horário exato agendado."""
        if not self.data_visita:
            return False
        # Verifica se tem 'T' ou um padrão de hora
        return "T" in self.data_visita or ":" in self.data_visita
