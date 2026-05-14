"""
Calendar Tool — Integração executora com o calendário do GoHighLevel.
"""

import json
import os
from datetime import datetime, timedelta

from loguru import logger
from zoneinfo import ZoneInfo

from services.ghl import GHL_CALENDARS_API_VERSION, _ghl_request_sync


def _get_calendar_timezone() -> ZoneInfo:
    return ZoneInfo(os.getenv("GHL_CALENDAR_TIMEZONE", "America/Sao_Paulo"))


def _parse_schedule_input(value: str) -> tuple[str, datetime | None]:
    raw_value = (value or "").strip()
    if not raw_value:
        raise ValueError("data_str vazio")

    tz = _get_calendar_timezone()
    if "T" in raw_value:
        dt = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        else:
            dt = dt.astimezone(tz)
        return dt.strftime("%Y-%m-%d"), dt

    dt = datetime.strptime(raw_value, "%Y-%m-%d").replace(tzinfo=tz)
    return raw_value, None


def _load_free_slots(data_str: str) -> tuple[list[dict[str, str]], str]:
    timezone = os.getenv("GHL_CALENDAR_TIMEZONE", "America/Sao_Paulo")
    tz = _get_calendar_timezone()

    dt = datetime.strptime(data_str, "%Y-%m-%d")
    start_of_day = dt.replace(hour=0, minute=0, second=0, tzinfo=tz)
    end_of_day = dt.replace(hour=23, minute=59, second=59, tzinfo=tz)
    start_epoch_ms = int(start_of_day.timestamp() * 1000)
    end_epoch_ms = int(end_of_day.timestamp() * 1000)

    calendar_id = os.getenv("GHL_CALENDAR_ID")
    path = f"/calendars/{calendar_id}/free-slots?startDate={start_epoch_ms}&endDate={end_epoch_ms}&timezone={timezone}"
    data = _ghl_request_sync("GET", path, version=GHL_CALENDARS_API_VERSION)

    raw_slots = data.get("slots", [])
    if not raw_slots and isinstance(data, dict):
        day_data = data.get(data_str)
        if isinstance(day_data, dict):
            raw_slots = day_data.get("slots", [])
        elif isinstance(day_data, list):
            raw_slots = day_data

    normalized_slots: list[dict[str, str]] = []
    for slot in raw_slots:
        slot_start = slot
        if isinstance(slot, dict):
            slot_start = slot.get("start") or slot.get("startTime", "")
        if not slot_start:
            continue

        slot_dt = datetime.fromisoformat(str(slot_start).replace("Z", "+00:00"))
        if slot_dt.tzinfo is None:
            slot_dt = slot_dt.replace(tzinfo=tz)
        else:
            slot_dt = slot_dt.astimezone(tz)
        normalized_slots.append(
            {
                "start_time": slot_dt.isoformat(),
                "local_time": slot_dt.strftime("%H:%M"),
            }
        )

    normalized_slots.sort(key=lambda item: item["start_time"])
    return normalized_slots, timezone


def _suggest_similar_slots(slots: list[dict[str, str]], requested_dt: datetime | None, limit: int = 3) -> list[str]:
    if not slots:
        return []

    if requested_dt is None:
        return [slot["local_time"] for slot in slots[:limit]]

    requested_minutes = requested_dt.hour * 60 + requested_dt.minute

    ranked = sorted(
        slots,
        key=lambda slot: (
            abs((int(slot["local_time"][:2]) * 60 + int(slot["local_time"][3:])) - requested_minutes),
            slot["local_time"],
        ),
    )
    suggestions: list[str] = []
    seen: set[str] = set()
    for slot in ranked:
        local_time = slot["local_time"]
        if local_time in seen:
            continue
        seen.add(local_time)
        suggestions.append(local_time)
        if len(suggestions) >= limit:
            break
    return suggestions

def buscar_horarios_livres(data_str: str) -> str:
    """
    Busca horários disponíveis para visita em uma data específica.
    Aceita `AAAA-MM-DD` ou um horário ISO (`AAAA-MM-DDTHH:MM:SS`).
    Quando recebe horário exato, também informa se ele está disponível e sugere os mais próximos.
    """
    calendar_id = os.getenv("GHL_CALENDAR_ID")
    if not calendar_id:
        return json.dumps({"ok": False, "error": "agenda_nao_configurada"}, ensure_ascii=False)

    logger.info("Consultando agenda GHL | data={d}", d=data_str)

    try:
        normalized_date, requested_dt = _parse_schedule_input(data_str)
        normalized_slots, timezone = _load_free_slots(normalized_date)
        horarios = [slot["local_time"] for slot in normalized_slots]
        requested_time = requested_dt.strftime("%H:%M") if requested_dt else None
        requested_slot_available = requested_time in horarios if requested_time else None
        suggested_slots = _suggest_similar_slots(normalized_slots, requested_dt)
        return json.dumps(
            {
                "ok": True,
                "date": normalized_date,
                "timezone": timezone,
                "requested_time": requested_time,
                "requested_slot_available": requested_slot_available,
                "available_slots": horarios,
                "suggested_slots": suggested_slots,
                "count": len(horarios),
            },
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

    try:
        requested_date, requested_dt = _parse_schedule_input(data_hora_iso)
        if requested_dt is None:
            raise ValueError("agendar_visita requer data e hora exatas")
    except ValueError:
        logger.warning("data_hora_iso inválida para agendamento | valor={valor}", valor=data_hora_iso)
        return json.dumps({"ok": False, "error": "data_hora_invalida"}, ensure_ascii=False)

    available_slots, timezone = _load_free_slots(requested_date)
    requested_time = requested_dt.strftime("%H:%M")
    free_times = [slot["local_time"] for slot in available_slots]
    if requested_time not in free_times:
        logger.info(
            "Horário indisponível antes do POST | lead={lead} | data={data} | hora={hora}",
            lead=nome,
            data=requested_date,
            hora=requested_time,
        )
        return json.dumps(
            {
                "ok": False,
                "error": "horario_indisponivel",
                "date": requested_date,
                "requested_time": requested_time,
                "timezone": timezone,
                "suggested_slots": _suggest_similar_slots(available_slots, requested_dt),
                "available_slots": free_times,
            },
            ensure_ascii=False,
        )

    logger.info("Realizando agendamento GHL | lead={n}", n=nome)
    end_time_iso = data_hora_iso
    try:
        end_time_iso = (requested_dt + timedelta(hours=1)).isoformat()
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
        response = _ghl_request_sync(
            "POST",
            "/calendars/events/appointments",
            json=payload,
            version=GHL_CALENDARS_API_VERSION,
        )
        appointment_id = (
            response.get("id")
            or response.get("_id")
            or response.get("appointment", {}).get("id")
            or response.get("event", {}).get("id")
        )
        if not appointment_id:
            logger.error("Agendamento sem confirmação verificável | resposta={resp}", resp=response)
            return json.dumps(
                {
                    "ok": False,
                    "error": "agendamento_nao_verificado",
                    "date": requested_date,
                    "requested_time": requested_time,
                    "timezone": timezone,
                    "suggested_slots": _suggest_similar_slots(available_slots, requested_dt),
                },
                ensure_ascii=False,
            )
        return json.dumps(
            {
                "ok": True,
                "status": "confirmed",
                "appointment_id": appointment_id,
                "creation_verified": True,
                "calendar_id": calendar_id,
                "contact_id": contact_id,
                "start_time": data_hora_iso,
                "end_time": end_time_iso,
                "timezone": timezone,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        logger.error(f"Erro ao agendar: {e}")
        return json.dumps({"ok": False, "error": "falha_no_agendamento"}, ensure_ascii=False)
