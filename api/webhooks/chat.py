"""
Webhook de Chat — Endpoint principal para receber mensagens de leads.
"""

import asyncio
import hashlib
import os
import re
import time
from typing import Any
from fastapi import APIRouter, BackgroundTasks, Request
from loguru import logger

_RECENT_WEBHOOKS: dict[str, float] = {}
_DEDUP_TTL_SECONDS = 8.0


def _is_duplicate_webhook(session_id: str, raw_message: Any) -> bool:
    """Idempotência: descarta reenvios do mesmo (session, mensagem) dentro de TTL curto."""
    try:
        payload = raw_message if isinstance(raw_message, str) else repr(raw_message)
        key = hashlib.sha1(f"{session_id}::{payload}".encode("utf-8")).hexdigest()
    except Exception:
        return False
    now = time.monotonic()
    for k, ts in list(_RECENT_WEBHOOKS.items()):
        if now - ts > _DEDUP_TTL_SECONDS:
            _RECENT_WEBHOOKS.pop(k, None)
    last = _RECENT_WEBHOOKS.get(key)
    _RECENT_WEBHOOKS[key] = now
    return last is not None and (now - last) <= _DEDUP_TTL_SECONDS

from api.schemas import ChatResponse
from runtime.orchestrator import process_message
from services.ghl import (
    get_conversation_by_contact,
    get_messages_async,
    has_tag,
    send_message_async,
)
from services.logging import log_agent_message, log_lead_message
from services.transcription import transcrever_audio_ghl
from tools.qualification import _get_lead, registrar_estado, registrar_qualificacao

router = APIRouter(prefix="/webhook", tags=["webhook"])

_AUDIO_EXTENSIONS = (".ogg", ".mp3", ".wav", ".m4a", ".mp4", ".webm")


def _clean_body(raw: Any) -> str:
    """Extrai o texto real da mensagem e limpa sufixos do GHL."""
    if not raw:
        return ""
    
    text = ""
    if isinstance(raw, dict):
        text = raw.get("body") or raw.get("message") or ""
    else:
        text = str(raw)

    marker = "Received on"
    if marker in text:
        text = text.split(marker)[0].strip()
    
    return text.strip()





def _build_outbound_messages(reply_text: str, attachments: list[str] | None = None) -> list[dict]:
    """Converte a resposta do agente em mensagens puras de texto, anexando mídia do sistema."""
    blocks = [b.strip() for b in reply_text.split("|||") if b.strip()]
    messages_to_send: list[dict] = []
    
    if attachments:
        messages_to_send.append({"text": "", "attachments": attachments[:10]})

    for block in blocks:
        clean_text = re.sub(r"\[FOTO \d+\]", "", block).strip()
        if clean_text:
            messages_to_send.append({"text": clean_text, "attachments": None})

    return messages_to_send


async def _run_agent_and_respond(
    session_id: str,
    user_message: str,
    contact_id: str | None = None,
    conversation_id: str | None = None
):
    """Executa o agente e envia a resposta em blocos via API do GHL."""
    try:
        result = await process_message(
            session_id=session_id,
            user_message=user_message,
            contact_id=contact_id,
            conversation_id=conversation_id
        )

        reply_text = result["reply"]
        attachments = result.get("attachments")

        if not contact_id:
            logger.warning("Faltando contact_id. Abortando envio.")
            return

        messages_to_send = _build_outbound_messages(reply_text, attachments)
        if not messages_to_send:
            return

        preview_lines = [msg["text"] for msg in messages_to_send if msg["text"]]
        if attachments:
            preview_lines.insert(0, f"[attachments={len(attachments)}]")
        log_agent_message(session_id, " ||| ".join(preview_lines)[:500] or "[mensagem sem texto]")

        # 3. Enviar sequencialmente com delay humano
        for i, msg in enumerate(messages_to_send):
            if i > 0:
                await asyncio.sleep(1.2)

            logger.info(
                "Enviando bloco {i}/{total} | has_attachments={att}",
                i=i + 1,
                total=len(messages_to_send),
                att=bool(msg["attachments"]),
            )
            try:
                await send_message_async(
                    contact_id=contact_id,
                    conversation_id=conversation_id,
                    text=msg["text"],
                    attachments=msg["attachments"],
                )
                logger.info("Bloco {i}/{total} enviado com sucesso ao GHL", i=i + 1, total=len(messages_to_send))
            except Exception as send_err:
                logger.error("ERRO ao enviar bloco {i}/{total} ao GHL: {err}", i=i + 1, total=len(messages_to_send), err=str(send_err))
                raise

    except Exception:
        logger.exception("Falha no processamento em background")


async def _resolve_conversation_id(
    contact_id: str | None,
    conversation_id: str | None,
) -> str | None:
    if conversation_id or not contact_id or len(contact_id) <= 10:
        return conversation_id

    conv = await get_conversation_by_contact(contact_id)
    if conv:
        return conv.get("id")
    return None


async def _resolve_voice_note_text(
    message_text: str,
    conversation_id: str | None,
) -> str:
    is_voice_note = message_text.lower().strip() in ["> voice note <", "voice note"]
    if not is_voice_note:
        return message_text

    if not conversation_id:
        logger.warning("Voice note sem conversation_id")
        return "[Áudio recebido — contexto indisponível]"

    logger.info("Voice note detectada — buscando URL do áudio via GHL API...")
    audio_url = None
    try:
        messages = await get_messages_async(conversation_id, limit=10)
        for msg in reversed(messages):
            if msg.get("direction") != "inbound":
                continue
            for att in msg.get("attachments", []):
                att_url = att if isinstance(att, str) else att.get("url", "")
                if att_url and any(att_url.lower().endswith(ext) for ext in _AUDIO_EXTENSIONS):
                    audio_url = att_url
                    break
            if audio_url:
                break
    except Exception as exc:
        logger.error("Erro ao buscar attachments do áudio: {err}", err=str(exc))

    if not audio_url:
        logger.warning("Voice note sem URL de áudio no GHL")
        return "[Áudio recebido — URL não encontrada]"

    logger.info("Áudio encontrado — iniciando transcrição: {url}", url=audio_url[:80])
    transcribed = await transcrever_audio_ghl(audio_url)
    if transcribed and not transcribed.startswith("["):
        logger.info("Transcrição OK: {t}", t=transcribed[:100])
        return transcribed
    return "[Áudio recebido — transcrição indisponível]"


async def _handle_chat_webhook_background(
    session_id: str,
    contact_id: str | None,
    conversation_id: str | None,
    raw_message: Any,
    veiculo_payload: str | None,
) -> None:
    try:
        resolved_conversation_id = await _resolve_conversation_id(contact_id, conversation_id)
        message_text = _clean_body(raw_message)
        message_text = await _resolve_voice_note_text(message_text, resolved_conversation_id)

        if not message_text:
            logger.warning("Mensagem vazia após pré-processamento | session={session}", session=session_id)
            return

        log_lead_message(session_id, message_text[:500])

        lead = _get_lead(session_id)
        if veiculo_payload and not lead.veiculo_interesse:
            registrar_qualificacao(session_id=session_id, veiculo_interesse=veiculo_payload)

        required_tag = os.getenv("GHL_REQUIRED_TAG")
        is_ghl_id = bool(contact_id and len(contact_id) > 10)
        if is_ghl_id and required_tag and not await has_tag(contact_id, required_tag):
            logger.info(
                "Webhook ignorado por tag ausente | session={session} | tag={tag}",
                session=session_id,
                tag=required_tag,
            )
            return

        await _run_agent_and_respond(
            session_id=session_id,
            user_message=message_text,
            contact_id=contact_id if is_ghl_id else None,
            conversation_id=resolved_conversation_id,
        )
    except Exception:
        logger.exception("Falha no pré-processamento do webhook em background")


async def _handle_greeting_webhook_background(
    contact_id: str,
    conversation_id: str | None,
    veiculo: str | None,
) -> None:
    try:
        if veiculo:
            registrar_estado(
                session_id=contact_id,
                veiculo_interesse=veiculo,
                greeting_vehicle=veiculo,
                vehicle_focus_current=veiculo,
                qualification_target_vehicle=veiculo,
            )

        resolved_conversation_id = await _resolve_conversation_id(contact_id, conversation_id)
        await _run_agent_and_respond(
            session_id=contact_id,
            user_message=f"[SAUDAÇÃO INICIAL] Veículo: {veiculo}" if veiculo else "[SAUDAÇÃO INICIAL]",
            contact_id=contact_id,
            conversation_id=resolved_conversation_id,
        )
    except Exception:
        logger.exception("Falha no webhook de saudação em background")


@router.post("/message", response_model=ChatResponse)
async def chat_webhook(request: Request, background_tasks: BackgroundTasks) -> ChatResponse:
    """Endpoint principal de conversa."""
    try:
        payload_dict = await request.json()
    except Exception:
        return ChatResponse(session_id="error", reply="JSON inválido", status="rejected")

    contact_id = (
        payload_dict.get("contactId")
        or payload_dict.get("contact_id")
        or (payload_dict.get("contact") or {}).get("id")
        or payload_dict.get("session_id")
    )
    
    conversation_id = (
        payload_dict.get("conversationId")
        or payload_dict.get("conversation_id")
        or (payload_dict.get("conversation") or {}).get("id")
    )

    session_id = contact_id

    raw_message = (
        payload_dict.get("body") 
        or payload_dict.get("message") 
        or payload_dict.get("text")
    )
    
    veiculo_payload = (
        payload_dict.get("Veículo de Interesse") 
        or payload_dict.get("veiculo_interesse")
        or payload_dict.get("customData", {}).get("veiculo_interesse")
    )

    if not session_id or not raw_message:
        return ChatResponse(session_id="error", reply="Payload inválido", status="rejected")

    if _is_duplicate_webhook(session_id, raw_message):
        logger.warning(
            "Webhook duplicado descartado | session={session}",
            session=session_id,
        )
        return ChatResponse(session_id=session_id, reply="Duplicado.", status="duplicate")

    background_tasks.add_task(
        _handle_chat_webhook_background,
        session_id=session_id,
        contact_id=contact_id,
        conversation_id=conversation_id,
        raw_message=raw_message,
        veiculo_payload=veiculo_payload,
    )

    return ChatResponse(session_id=session_id, reply="Processando...", status="accepted")


@router.post("/message/saudacao", response_model=ChatResponse)
async def greeting_webhook(request: Request, background_tasks: BackgroundTasks) -> ChatResponse:
    """Endpoint de Saudação Proativa."""
    try:
        payload_dict = await request.json()
    except Exception:
        return ChatResponse(session_id="error", reply="JSON inválido", status="rejected")

    contact_id = (
        payload_dict.get("contactId")
        or payload_dict.get("contact_id")
        or (payload_dict.get("contact") or {}).get("id")
    )
    conv_id = (
        payload_dict.get("conversationId")
        or payload_dict.get("conversation_id")
    )
    
    if not contact_id:
        return ChatResponse(session_id="error", reply="contactId ausente", status="rejected")

    veiculo = (
        payload_dict.get("Veículo de Interesse") 
        or payload_dict.get("veiculo_interesse")
    )
    background_tasks.add_task(
        _handle_greeting_webhook_background,
        contact_id=contact_id,
        conversation_id=conv_id,
        veiculo=veiculo,
    )

    return ChatResponse(session_id=contact_id, reply="Saudação agendada.", status="accepted")
