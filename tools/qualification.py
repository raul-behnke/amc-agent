"""
Qualification Tool — Persistência factual do estado do lead.

As tools deste módulo apenas registram e consultam estado. A decisão de
conversa continua sendo responsabilidade do agente.
"""

import json
from typing import Any

from loguru import logger

from state.lead_model import LeadQualification, LeadStatus


_lead_states: dict[str, LeadQualification] = {}


def _get_lead(session_id: str) -> LeadQualification:
    """Recupera ou cria o estado de qualificação de um lead."""
    if session_id not in _lead_states:
        _lead_states[session_id] = LeadQualification()
    return _lead_states[session_id]


def _normalize_vehicle_filters(
    faixa_preco: str | None = None,
    ano_minimo: int | None = None,
    cambio: str | None = None,
    tipo_veiculo: str | None = None,
    marca_preferida: str | None = None,
    modelo_preferido: str | None = None,
    cidade: str | None = None,
) -> dict[str, Any]:
    filters = {
        "faixa_preco": faixa_preco,
        "ano_minimo": ano_minimo,
        "cambio": cambio,
        "tipo_veiculo": tipo_veiculo,
        "marca_preferida": marca_preferida,
        "modelo_preferido": modelo_preferido,
        "cidade": cidade,
    }
    return {key: value for key, value in filters.items() if value is not None}


def _register_answer(lead: LeadQualification, key: str, value: Any) -> None:
    if value is not None:
        lead.lead_answers[key] = value


def _refresh_status(lead: LeadQualification) -> None:
    if lead.motivo_handoff:
        lead.status = LeadStatus.HANDOFF
    elif lead.data_visita and lead.has_exact_schedule():
        lead.status = LeadStatus.SCHEDULED
    elif lead.data_visita:
        lead.status = LeadStatus.SCHEDULING
    else:
        score = lead.completeness_score()
        if score >= 80:
            lead.status = LeadStatus.QUALIFIED
        elif score >= 20:
            lead.status = LeadStatus.QUALIFYING
        else:
            lead.status = LeadStatus.NEW_LEAD

    lead.lead_stage = lead.status.value


def _state_snapshot(lead: LeadQualification) -> dict[str, Any]:
    data = lead.to_dict()
    return {
        "status": data["status"],
        "lead_stage": data["lead_stage"],
        "veiculo_interesse": data.get("veiculo_interesse"),
        "qualificacao": data.get("qualificacao"),
        "vehicle_focus": data["vehicle_focus"],
        "vehicle_journey": data["vehicle_journey"],
        "lead_answers": data["lead_answers"],
        "conversation_summary": data.get("conversation_summary"),
        "completeness_score": lead.completeness_score(),
        "qualificacao_pendente": lead.get_missing_fields(),
        "dados_troca_pendentes": lead.get_missing_trade_fields(),
        "next_qualification_field": lead.next_qualification_field(),
        "next_qualification_question": lead.next_qualification_question(),
    }


def registrar_estado(
    session_id: str,
    nome: str | None = None,
    interesse: str | None = None,
    intencao: str | None = None,
    motivacao: str | None = None,
    negociacao: str | None = None,
    cidade: str | None = None,
    observacoes: str | None = None,
    tipo_veiculo: str | None = None,
    marca_preferida: str | None = None,
    modelo_preferido: str | None = None,
    faixa_preco: str | None = None,
    ano_minimo: int | None = None,
    cambio: str | None = None,
    tem_troca: bool | None = None,
    veiculo_troca: str | None = None,
    km_troca: str | None = None,
    quitado_troca: bool | None = None,
    estado_troca: str | None = None,
    fotos_troca_recebidas: bool | None = None,
    motivo_troca: str | None = None,
    precisa_financiamento: bool | None = None,
    e_local: bool | None = None,
    veiculo_interesse: str | None = None,
    data_visita: str | None = None,
    motivo_handoff: str | None = None,
    conversation_summary: str | None = None,
    vehicle_focus_current: str | None = None,
    vehicle_focus_last_valid: str | None = None,
    alternatives_shown: list[Any] | None = None,
    active_filters: dict[str, Any] | None = None,
    greeting_vehicle: str | None = None,
    vehicle_mentions: list[Any] | None = None,
    presented_vehicles: list[Any] | None = None,
    current_vehicle_request: str | None = None,
    photo_target_vehicle: str | None = None,
    scheduling_target_vehicle: str | None = None,
    qualification_target_vehicle: str | None = None,
) -> str:
    """
    Registra ou atualiza o estado factual da sessão atual.

    Retorna um snapshot serializado do estado após a persistência.
    """
    lead = _get_lead(session_id)
    updates: dict[str, Any] = {}

    if nome is not None:
        invalid_names = ["não informado", "desconhecido", "cliente", "lead", "n/a", "não"]
        if str(nome).lower().strip() not in invalid_names:
            # Proteção: Não sobrescreve um nome completo por um primeiro nome parcial
            current_name = str(lead.nome or "").lower().strip()
            new_name = str(nome).lower().strip()
            if not (current_name and new_name in current_name and len(new_name) < len(current_name)):
                lead.nome = nome
                updates["nome"] = nome
                _register_answer(lead, "nome", nome)
        else:
            logger.warning("Tentativa de registrar nome inválido: {name}", name=nome)
    if interesse is not None:
        lead.interesse = interesse
        updates["interesse"] = interesse
        _register_answer(lead, "interesse", interesse)
    if intencao is not None:
        # Proteção similar: não regredir de "troca de Gol 1998" para "troca de Gol"
        current_i = str(lead.intencao or "").lower().strip()
        new_i = str(intencao).lower().strip()
        if not (current_i and new_i in current_i and len(new_i) < len(current_i)):
            lead.intencao = intencao
            updates["intencao"] = intencao
            _register_answer(lead, "intencao", intencao)
    if motivacao is not None:
        lead.motivacao = motivacao
        updates["motivacao"] = motivacao
        _register_answer(lead, "motivacao", motivacao)
    if negociacao is not None:
        lead.negociacao = negociacao
        updates["negociacao"] = negociacao
        _register_answer(lead, "negociacao", negociacao)
    if cidade is not None:
        lead.cidade = cidade
        updates["cidade"] = cidade
        _register_answer(lead, "cidade", cidade)
    if observacoes is not None:
        lead.observacoes = observacoes
        updates["observacoes"] = observacoes
        _register_answer(lead, "observacoes", observacoes)
    if tipo_veiculo is not None:
        lead.tipo_veiculo = tipo_veiculo
        updates["tipo_veiculo"] = tipo_veiculo
        _register_answer(lead, "tipo_veiculo", tipo_veiculo)
    if marca_preferida is not None:
        lead.marca_preferida = marca_preferida
        updates["marca_preferida"] = marca_preferida
        _register_answer(lead, "marca_preferida", marca_preferida)
    if modelo_preferido is not None:
        lead.modelo_preferido = modelo_preferido
        updates["modelo_preferido"] = modelo_preferido
        _register_answer(lead, "modelo_preferido", modelo_preferido)
    if faixa_preco is not None:
        lead.faixa_preco = faixa_preco
        updates["faixa_preco"] = faixa_preco
        _register_answer(lead, "faixa_preco", faixa_preco)
    if ano_minimo is not None:
        lead.ano_minimo = ano_minimo
        updates["ano_minimo"] = ano_minimo
        _register_answer(lead, "ano_minimo", ano_minimo)
    if cambio is not None:
        lead.cambio = cambio
        updates["cambio"] = cambio
        _register_answer(lead, "cambio", cambio)
    if tem_troca is not None:
        lead.tem_troca = tem_troca
        updates["tem_troca"] = tem_troca
        _register_answer(lead, "tem_troca", tem_troca)
    if veiculo_troca is not None:
        # Proteção: Não sobrescreve "Gol 1998" por apenas "Gol"
        current_v = str(lead.veiculo_troca or "").lower().strip()
        new_v = str(veiculo_troca).lower().strip()
        # Só atualiza se o novo valor não for apenas uma parte menos detalhada do atual
        if not (current_v and new_v in current_v and len(new_v) < len(current_v)):
            lead.veiculo_troca = veiculo_troca
            updates["veiculo_troca"] = veiculo_troca
            _register_answer(lead, "veiculo_troca", veiculo_troca)
    if km_troca is not None:
        lead.km_troca = km_troca
        updates["km_troca"] = km_troca
        _register_answer(lead, "km_troca", km_troca)
    if quitado_troca is not None:
        lead.quitado_troca = quitado_troca
        updates["quitado_troca"] = quitado_troca
        _register_answer(lead, "quitado_troca", quitado_troca)
    if estado_troca is not None:
        lead.estado_troca = estado_troca
        updates["estado_troca"] = estado_troca
        _register_answer(lead, "estado_troca", estado_troca)
    if fotos_troca_recebidas is not None:
        lead.fotos_troca_recebidas = fotos_troca_recebidas
        updates["fotos_troca_recebidas"] = fotos_troca_recebidas
        _register_answer(lead, "fotos_troca_recebidas", fotos_troca_recebidas)
    if motivo_troca is not None:
        lead.motivo_troca = motivo_troca
        updates["motivo_troca"] = motivo_troca
        _register_answer(lead, "motivo_troca", motivo_troca)
    if precisa_financiamento is not None:
        lead.precisa_financiamento = precisa_financiamento
        updates["precisa_financiamento"] = precisa_financiamento
        _register_answer(lead, "precisa_financiamento", precisa_financiamento)
    if e_local is not None:
        lead.e_local = e_local
        updates["e_local"] = e_local
        _register_answer(lead, "e_local", e_local)
    if data_visita is not None:
        lead.data_visita = data_visita
        updates["data_visita"] = data_visita
        _register_answer(lead, "data_visita", data_visita)
    if motivo_handoff is not None:
        lead.motivo_handoff = motivo_handoff
        updates["motivo_handoff"] = motivo_handoff
        _register_answer(lead, "motivo_handoff", motivo_handoff)
    if conversation_summary is not None:
        lead.conversation_summary = conversation_summary
        updates["conversation_summary"] = conversation_summary
    if greeting_vehicle is not None:
        lead.vehicle_journey.greeting_vehicle = greeting_vehicle
        if not lead.vehicle_journey.primary_interest:
            lead.vehicle_journey.primary_interest = greeting_vehicle
            lead.veiculo_interesse = greeting_vehicle
        updates["vehicle_journey.greeting_vehicle"] = greeting_vehicle

    incoming_filters = active_filters or _normalize_vehicle_filters(
        faixa_preco=faixa_preco,
        ano_minimo=ano_minimo,
        cambio=cambio,
        tipo_veiculo=tipo_veiculo,
        marca_preferida=marca_preferida,
        modelo_preferido=modelo_preferido,
        cidade=cidade,
    )
    normalized_filters = dict(lead.vehicle_focus.active_filters or {})
    normalized_filters.update(incoming_filters)

    focus_vehicle = vehicle_focus_current or veiculo_interesse or interesse
    if focus_vehicle is not None or incoming_filters or alternatives_shown is not None:
        lead.set_vehicle_focus(
            vehicle=focus_vehicle,
            active_filters=normalized_filters if normalized_filters else None,
            alternatives_shown=alternatives_shown,
        )
        updates["vehicle_focus.current"] = lead.vehicle_focus.current
        if normalized_filters:
            updates["vehicle_focus.active_filters"] = lead.vehicle_focus.active_filters
        if alternatives_shown is not None:
            updates["vehicle_focus.alternatives_shown"] = lead.vehicle_focus.alternatives_shown

    if vehicle_focus_last_valid is not None:
        lead.vehicle_focus.last_valid = vehicle_focus_last_valid
        updates["vehicle_focus.last_valid"] = vehicle_focus_last_valid

    if veiculo_interesse:
        lead.register_vehicle_mentions([veiculo_interesse], source="veiculo_interesse")
        updates["vehicle_journey.primary_interest"] = lead.vehicle_journey.primary_interest

    if vehicle_mentions:
        lead.register_vehicle_mentions(vehicle_mentions, source="mention")
        updates["vehicle_journey.mentioned_count"] = len(lead.vehicle_journey.mentioned_vehicles)

    presented_payload = presented_vehicles if presented_vehicles is not None else alternatives_shown
    if presented_payload is not None:
        lead.register_presented_vehicles(presented_payload, source="stock_search")
        updates["vehicle_journey.presented_count"] = len(lead.vehicle_journey.presented_vehicles)
        updates["vehicle_journey.last_presented_count"] = len(lead.vehicle_journey.last_presented_vehicles)

    if any(
        [
            current_vehicle_request,
            vehicle_focus_current,
            photo_target_vehicle,
            scheduling_target_vehicle,
            qualification_target_vehicle,
        ]
    ):
        lead.set_vehicle_targets(
            current_request=current_vehicle_request,
            current_focus=vehicle_focus_current,
            photo_target=photo_target_vehicle,
            scheduling_target=scheduling_target_vehicle,
            qualification_target=qualification_target_vehicle,
        )
        updates["vehicle_journey.current_focus"] = lead.vehicle_journey.current_focus
        updates["vehicle_journey.current_request"] = lead.vehicle_journey.current_request
        updates["vehicle_journey.photo_target"] = lead.vehicle_journey.photo_target
        updates["vehicle_journey.qualification_target"] = lead.vehicle_journey.qualification_target

    _refresh_status(lead)

    snapshot = _state_snapshot(lead)
    logger.info(
        "Estado atualizado | session={sid} | status={status} | updates={updates}",
        sid=session_id,
        status=lead.status.value,
        updates=updates,
    )

    return json.dumps(snapshot, ensure_ascii=False)


def registrar_qualificacao(
    session_id: str,
    nome: str | None = None,
    interesse: str | None = None,
    intencao: str | None = None,
    motivacao: str | None = None,
    negociacao: str | None = None,
    cidade: str | None = None,
    observacoes: str | None = None,
    tipo_veiculo: str | None = None,
    marca_preferida: str | None = None,
    modelo_preferido: str | None = None,
    faixa_preco: str | None = None,
    ano_minimo: int | None = None,
    cambio: str | None = None,
    tem_troca: bool | None = None,
    veiculo_troca: str | None = None,
    km_troca: str | None = None,
    quitado_troca: bool | None = None,
    estado_troca: str | None = None,
    fotos_troca_recebidas: bool | None = None,
    motivo_troca: str | None = None,
    precisa_financiamento: bool | None = None,
    e_local: bool | None = None,
    veiculo_interesse: str | None = None,
    data_visita: str | None = None,
    motivo_handoff: str | None = None,
) -> str:
    """
    Alias legada para manter compatibilidade com chamadas antigas.
    """
    return registrar_estado(
        session_id=session_id,
        nome=nome,
        interesse=interesse,
        intencao=intencao,
        motivacao=motivacao,
        negociacao=negociacao,
        cidade=cidade,
        observacoes=observacoes,
        tipo_veiculo=tipo_veiculo,
        marca_preferida=marca_preferida,
        modelo_preferido=modelo_preferido,
        faixa_preco=faixa_preco,
        ano_minimo=ano_minimo,
        cambio=cambio,
        tem_troca=tem_troca,
        veiculo_troca=veiculo_troca,
        km_troca=km_troca,
        quitado_troca=quitado_troca,
        estado_troca=estado_troca,
        fotos_troca_recebidas=fotos_troca_recebidas,
        motivo_troca=motivo_troca,
        precisa_financiamento=precisa_financiamento,
        e_local=e_local,
        veiculo_interesse=veiculo_interesse,
        data_visita=data_visita,
        motivo_handoff=motivo_handoff,
    )


def consultar_qualificacao(session_id: str) -> str:
    """
    Consulta o estado atual de qualificação de um lead.
    """
    lead = _get_lead(session_id)
    data = lead.to_dict()

    filled = {
        key: value
        for key, value in data.items()
        if value is not None and value is not False and key not in {"status", "lead_stage"}
    }

    snapshot = {
        "status": lead.status.value,
        "lead_stage": lead.lead_stage,
        "completeness_score": lead.completeness_score(),
        "qualificacao": data.get("qualificacao"),
        "filled": filled,
        "lead_answers": lead.lead_answers,
        "vehicle_focus": lead.vehicle_focus.model_dump(),
        "vehicle_journey": lead.vehicle_journey.model_dump(),
        "conversation_summary": lead.conversation_summary,
        "dados_troca_pendentes": lead.get_missing_trade_fields(),
        "next_qualification_field": lead.next_qualification_field(),
        "next_qualification_question": lead.next_qualification_question(),
    }
    return json.dumps(snapshot, ensure_ascii=False)
