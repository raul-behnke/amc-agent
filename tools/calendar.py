"""
Calendar Tool — Integração executora com o calendário do GoHighLevel.
"""

import json
import os
from datetime import datetime, timedelta

from loguru import logger

from services.ghl import GHL_CALENDARS_API_VERSION, _ghl_request_sync

def buscar_horarios_livres(data_str: str) -> str:
    """
    Busca horários disponíveis para visita em uma data específica.
    Data deve estar no formato AAAA-MM-DD.
    """
    calendar_id = os.getenv("GHL_CALENDAR_ID")
    if not calendar_id:
        return json.dumps({"ok": False, "error": "agenda_nao_configurada"}, ensure_ascii=False)

    logger.info("Consultando agenda GHL | data={d}", d=data_str)

    try:
        from zoneinfo import ZoneInfo

        timezone = os.getenv("GHL_CALENDAR_TIMEZONE", "America/Sao_Paulo")

        # Converter YYYY-MM-DD para epoch ms (início e fim do dia)
        dt = datetime.strptime(data_str, "%Y-%m-%d")
        tz = ZoneInfo(timezone)
        start_of_day = dt.replace(hour=0, minute=0, second=0, tzinfo=tz)
        end_of_day = dt.replace(hour=23, minute=59, second=59, tzinfo=tz)
        start_epoch_ms = int(start_of_day.timestamp() * 1000)
        end_epoch_ms = int(end_of_day.timestamp() * 1000)

        path = f"/calendars/{calendar_id}/free-slots?startDate={start_epoch_ms}&endDate={end_epoch_ms}&timezone={timezone}"
        data = _ghl_request_sync("GET", path, version=GHL_CALENDARS_API_VERSION)

        # A resposta pode ter formato:
        # {"slots": [...]} ou {"YYYY-MM-DD": {"slots": [...]}} ou {"YYYY-MM-DD": [...]}
        slots = data.get("slots", [])
        if not slots and isinstance(data, dict):
            day_data = data.get(data_str)
            if isinstance(day_data, dict):
                slots = day_data.get("slots", [])
            elif isinstance(day_data, list):
                slots = day_data
        if not slots:
            return json.dumps(
                {"ok": True, "date": data_str, "available_slots": [], "count": 0},
                ensure_ascii=False,
            )

        horarios = []
        for slot in slots:
            if isinstance(slot, str):
                slot_dt = datetime.fromisoformat(slot.replace("Z", "+00:00"))
                horarios.append(slot_dt.strftime("%H:%M"))
            elif isinstance(slot, dict):
                slot_start = slot.get("start") or slot.get("startTime", "")
                if slot_start:
                    slot_dt = datetime.fromisoformat(str(slot_start).replace("Z", "+00:00"))
                    horarios.append(slot_dt.strftime("%H:%M"))

        return json.dumps(
            {"ok": True, "date": data_str, "available_slots": horarios, "count": len(horarios)},
            ensure_ascii=False,
        )

    except Exception as e:
        logger.error(f"Erro ao buscar agenda: {e}")
        return json.dumps({"ok": False, "error": "agenda_indisponivel"}, ensure_ascii=False)

def agendar_visita(
    data_hora_iso: str,
    nome: str,
    email: str,
    telefone: str,
    contact_id: str,
) -> str:
    """
    Realiza o agendamento oficial no calendário do GHL.
    data_hora_iso: Formato ISO (ex: 2024-05-10T14:00:00Z)
    """
    calendar_id = os.getenv("GHL_CALENDAR_ID")
    location_id = os.getenv("GHL_LOCATION_ID")
    if not calendar_id or not location_id:
        logger.error("GHL_CALENDAR_ID ou GHL_LOCATION_ID não configurados para agendamento")
        return json.dumps({"ok": False, "error": "agenda_nao_configurada"}, ensure_ascii=False)

    if not contact_id:
        logger.error("Tentativa de agendamento sem contact_id | lead={n}", n=nome)
        return json.dumps({"ok": False, "error": "contact_id_obrigatorio"}, ensure_ascii=False)

    logger.info("Realizando agendamento GHL | lead={n}", n=nome)
    end_time_iso = data_hora_iso
    try:
        start_dt = datetime.fromisoformat(data_hora_iso.replace("Z", "+00:00"))
        end_time_iso = (start_dt + timedelta(hours=1)).isoformat()
    except ValueError:
        logger.warning("data_hora_iso inválida para cálculo de endTime | valor={valor}", valor=data_hora_iso)

    payload = {
        "calendarId": calendar_id,
        "locationId": location_id,
        "startTime": data_hora_iso,
        "endTime": end_time_iso,
        "title": f"Visita AMC: {nome}",
        "contactId": contact_id,
        "appointmentStatus": "confirmed",
    }
    if email:
        payload["email"] = email
    if telefone:
        payload["phone"] = telefone

    try:
        _ghl_request_sync(
            "POST",
            "/calendars/events/appointments",
            json=payload,
            version=GHL_CALENDARS_API_VERSION,
        )
        return json.dumps(
            {
                "ok": True,
                "status": "confirmed",
                "calendar_id": calendar_id,
                "contact_id": contact_id,
                "start_time": data_hora_iso,
                "end_time": end_time_iso,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        logger.error(f"Erro ao agendar: {e}")
        return json.dumps({"ok": False, "error": "falha_no_agendamento"}, ensure_ascii=False)
