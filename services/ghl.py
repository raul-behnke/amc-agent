"""
Serviço GHL (GoHighLevel) — Adapter para o CRM.

Responsável por buscar dados do CRM de forma desacoplada.
O restante do sistema NUNCA acessa a API GHL diretamente.
"""

import json
import os
from typing import Any

import httpx
from loguru import logger


GHL_BASE_URL = "https://services.leadconnectorhq.com"
GHL_API_VERSION = "2021-07-28"
GHL_CALENDARS_API_VERSION = "2023-02-21"


def _ghl_headers(version: str | None = None) -> dict[str, str]:
    """Retorna os headers de autenticação do GHL."""
    token = os.getenv("GHL_PIT_TOKEN")
    if not token:
        raise ValueError("GHL_PIT_TOKEN não configurado no .env")
    return {
        "Authorization": f"Bearer {token}",
        "Version": version or GHL_API_VERSION,
        "Accept": "application/json",
    }


async def _ghl_request_async(method: str, path: str, **kwargs: Any) -> dict:
    """Faz uma requisição assíncrona autenticada ao GHL."""
    version = kwargs.pop("version", None)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.request(
            method=method,
            url=f"{GHL_BASE_URL}{path}",
            headers=_ghl_headers(version=version),
            **kwargs,
        )
        response.raise_for_status()
        return response.json()


def _ghl_request_sync(method: str, path: str, **kwargs: Any) -> dict:
    """Faz uma requisição síncrona autenticada ao GHL (para uso em tools)."""
    version = kwargs.pop("version", None)
    with httpx.Client(timeout=30) as client:
        response = client.request(
            method=method,
            url=f"{GHL_BASE_URL}{path}",
            headers=_ghl_headers(version=version),
            **kwargs,
        )
        response.raise_for_status()
        return response.json()


def _parse_inventory_response(data: dict) -> list[dict]:
    """Extrai a lista de veículos do response da API."""
    raw_value = data.get("customValue", {}).get("value", "{}")
    inventory = json.loads(raw_value)
    vehicles = inventory.get("vehicles", [])
    logger.info("Estoque carregado | total={total}", total=len(vehicles))
    return vehicles


def _inventory_path() -> str:
    """Retorna o path da API para buscar o estoque."""
    location_id = os.getenv("GHL_LOCATION_ID")
    custom_value_id = os.getenv("GHL_INVENTORY_CUSTOM_VALUE_ID")
    if not location_id or not custom_value_id:
        raise ValueError("GHL_LOCATION_ID ou GHL_INVENTORY_CUSTOM_VALUE_ID não configurados.")
    return f"/locations/{location_id}/customValues/{custom_value_id}"


async def fetch_inventory_async() -> list[dict]:
    """Busca o estoque de forma assíncrona."""
    logger.info("Buscando estoque no GHL (async)...")
    data = await _ghl_request_async("GET", _inventory_path())
    return _parse_inventory_response(data)


def fetch_inventory_sync() -> list[dict]:
    """Busca o estoque de forma síncrona (para uso em Agno tools)."""
    logger.info("Buscando estoque no GHL (sync)...")
    data = _ghl_request_sync("GET", _inventory_path())
    return _parse_inventory_response(data)


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

def upsert_contact(phone: str, name: str | None = None) -> dict:
    """
    Busca um contato pelo telefone ou cria um novo se não existir.
    """
    location_id = os.getenv("GHL_LOCATION_ID")
    
    # 1. Buscar por telefone
    try:
        search_data = _ghl_request_sync(
            "GET", 
            f"/contacts/?locationId={location_id}&query={phone}"
        )
        contacts = search_data.get("contacts", [])
        if contacts:
            logger.info("Contato encontrado: {id}", id=contacts[0]["id"])
            return contacts[0]
    except Exception as e:
        logger.warning("Erro ao buscar contato: {err}", err=str(e))

    # 2. Criar se não existir
    logger.info("Criando novo contato para {phone}", phone=phone)
    payload = {
        "locationId": location_id,
        "phone": phone,
    }
    if name:
        payload["firstName"] = name

    return _ghl_request_sync("POST", "/contacts/", json=payload).get("contact", {})


async def has_tag(contact_id: str, tag: str) -> bool:
    """Verifica se um contato possui uma tag específica (Async)."""
    location_id = os.getenv("GHL_LOCATION_ID")
    try:
        data = await _ghl_request_async("GET", f"/contacts/{contact_id}")
        contact = data.get("contact", {})
        tags = contact.get("tags", [])
        # Tags no GHL podem vir como lista de strings ou lista de objetos
        tag_list = [t.lower() if isinstance(t, str) else t.get("name", "").lower() for t in tags]
        return tag.lower() in tag_list
    except Exception as e:
        logger.error("Erro ao verificar tag: {err}", err=str(e))
        return False


def remove_contact_tag_sync(contact_id: str, tag: str) -> bool:
    """Remove uma tag específica de um contato (Sync)."""
    try:
        # A API do GHL usa DELETE para remover tags individuais
        _ghl_request_sync("DELETE", f"/contacts/{contact_id}/tags/{tag}")
        logger.info("Tag '{tag}' removida do contato {cid}", tag=tag, cid=contact_id)
        return True
    except Exception as e:
        logger.error("Erro ao remover tag '{tag}': {err}", tag=tag, err=str(e))
        return False


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------

def upsert_opportunity(
    contact_id: str, 
    pipeline_id: str, 
    stage_id: str, 
    title: str,
    status: str = "open"
) -> dict:
    """
    Cria ou atualiza uma oportunidade no pipeline.
    """
    location_id = os.getenv("GHL_LOCATION_ID")
    
    # 1. Buscar oportunidades existentes do contato neste pipeline
    try:
        opps_data = _ghl_request_sync(
            "GET", 
            f"/opportunities/search?locationId={location_id}&contactId={contact_id}"
        )
        for opp in opps_data.get("opportunities", []):
            if opp.get("pipelineId") == pipeline_id:
                # Atualizar existente
                logger.info("Atualizando oportunidade: {id}", id=opp["id"])
                update_payload = {"pipelineStageId": stage_id, "name": title, "status": status}
                return _ghl_request_sync("PUT", f"/opportunities/{opp['id']}", json=update_payload)
    except Exception as e:
        logger.warning("Erro ao buscar oportunidades: {err}", err=str(e))

    # 2. Criar nova se não existir
    logger.info("Criando nova oportunidade para contato {id}", id=contact_id)
    payload = {
        "pipelineId": pipeline_id,
        "pipelineStageId": stage_id,
        "locationId": location_id,
        "contactId": contact_id,
        "name": title,
        "status": status
    }
    return _ghl_request_sync("POST", "/opportunities/", json=payload)


# ---------------------------------------------------------------------------
# Notes & Custom Fields
# ---------------------------------------------------------------------------

def add_contact_note(contact_id: str, body: str) -> dict:
    """Adiciona uma nota ao contato."""
    payload = {"body": body}
    return _ghl_request_sync("POST", f"/contacts/{contact_id}/notes", json=payload)


def update_contact_custom_fields(contact_id: str, custom_fields: list[dict]) -> dict:
    """
    Atualiza campos personalizados do contato.
    custom_fields: [{'id': 'field_id', 'value': 'value'}, ...]
    """
    payload = {"customFields": custom_fields}
    return _ghl_request_sync("PUT", f"/contacts/{contact_id}", json=payload)


# ---------------------------------------------------------------------------
# Conversations & Messages
# ---------------------------------------------------------------------------

async def send_message_async(
    contact_id: str, 
    conversation_id: str | None, 
    text: str, 
    message_type: str = "SMS",
    attachments: list[str] | None = None
) -> dict:
    """Envia uma mensagem para o lead via API do GHL (Async)."""
    payload = {
        "type": message_type,
        "contactId": contact_id,
        "message": text,
    }
    if conversation_id:
        payload["conversationId"] = conversation_id
    if attachments:
        payload["attachments"] = attachments

    logger.info("Enviando mensagem GHL | contact={cid} | photos={n}", cid=contact_id[:10], n=len(attachments or []))
    return await _ghl_request_async("POST", "/conversations/messages", json=payload)


def send_message_sync(
    contact_id: str, 
    conversation_id: str | None, 
    text: str, 
    message_type: str = "SMS",
    attachments: list[str] | None = None
) -> dict:
    """Envia uma mensagem para o lead via API do GHL (Sync — para tools)."""
    payload = {
        "type": message_type,
        "contactId": contact_id,
        "message": text,
    }
    if conversation_id:
        payload["conversationId"] = conversation_id
    if attachments:
        payload["attachments"] = attachments
        
    return _ghl_request_sync("POST", "/conversations/messages", json=payload)


async def get_conversation_by_contact(contact_id: str) -> dict | None:
    """Busca a conversa ativa de um contato."""
    location_id = os.getenv("GHL_LOCATION_ID")
    path = f"/conversations/search?locationId={location_id}&contactId={contact_id}&limit=1"
    
    try:
        data = await _ghl_request_async("GET", path)
        conversations = data.get("conversations", [])
        return conversations[0] if conversations else None
    except Exception as e:
        logger.error("Erro ao buscar conversa: {err}", err=str(e))
        return None


async def get_messages_async(conversation_id: str, limit: int = 20) -> list[dict]:
    """Busca as mensagens mais recentes de uma conversa no GHL."""
    path = f"/conversations/{conversation_id}/messages?limit={limit}"
    try:
        data = await _ghl_request_async("GET", path)
        messages = data.get("messages", {}).get("messages", [])
        return sorted(messages, key=lambda m: m.get("dateAdded", ""))
    except Exception as e:
        logger.error("Erro ao buscar mensagens da conversa {cvid}: {err}", cvid=conversation_id, err=str(e))
        return []


# ---------------------------------------------------------------------------
# Escalation & Workflows
# ---------------------------------------------------------------------------

async def trigger_workflow(contact_id: str) -> bool:
    """Dispara um workflow do GHL para o contato."""
    workflow_id = os.getenv("GHL_ESCALATION_WORKFLOW_ID")
    if not workflow_id:
        logger.warning("GHL_ESCALATION_WORKFLOW_ID não configurado")
        return False
    try:
        await _ghl_request_async("POST", f"/contacts/{contact_id}/workflow/{workflow_id}", json={})
        logger.info("Workflow disparado | contact={cid} | workflow={wid}", cid=contact_id[:10], wid=workflow_id[:10])
        return True
    except Exception as e:
        logger.error("Erro ao disparar workflow: {err}", err=str(e))
        return False


async def notify_escalation(
    contact_id: str,
    conversation_id: str,
    reason: str,
    note: str,
    farewell_message: str,
) -> bool:
    """Notifica o webhook de pré-atendimento sobre o escalonamento."""
    url = os.getenv("ESCALATION_NOTIFY_URL")
    if not url:
        logger.warning("ESCALATION_NOTIFY_URL não configurada")
        return False

    formatted_message = _build_escalation_message(reason, note, farewell_message)
    payload = {
        "event": "ai_escalation",
        "notificationType": "ai_escalation",
        "template": "escalonamento_ia",
        "contactId": contact_id,
        "conversationId": conversation_id,
        "reason": reason,
        "note": note,
        "summary": note,
        "farewellMessage": farewell_message,
        "message": formatted_message,
        "customMessage": formatted_message,
        "messageBody": formatted_message,
        "escalation": {
            "reason": reason,
            "summary": note,
            "farewellMessage": farewell_message,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code not in (200, 201, 202, 204):
                logger.error(
                    "notify_escalation falhou | status={} | body={}",
                    resp.status_code,
                    resp.text[:200],
                )
                return False
        logger.info("notify_escalation OK | contact={} reason={}", contact_id[:10], reason)
        return True
    except Exception as e:
        logger.error("notify_escalation erro | contact={}: {}", contact_id[:10], e)
        return False


def _build_escalation_message(reason: str, note: str, farewell_message: str) -> str:
    """Constroi a mensagem formatada de notificação de escalonamento."""
    reason_label = reason.replace("_", " ").strip() if reason else "não informado"
    parts = [
        "🚨 *ESCALONAMENTO DA IA* 🚨",
        "",
        f"Motivo: {reason_label}",
    ]
    if note:
        parts.extend(["", "Resumo do atendimento:", note.strip()])
    if farewell_message:
        parts.extend(["", f"Mensagem enviada ao lead: {farewell_message.strip()}"])
    return "\n".join(parts).strip()
