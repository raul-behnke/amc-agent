"""
Lucas SDR Agent — AMC Veículos.

Agente de pré-qualificação comercial automotiva.
Utiliza Agno como runtime de agente e SqliteDb para persistência de sessão.
"""

import json
import os

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIChat

from prompts.lucas_sdr import LUCAS_DESCRIPTION, LUCAS_INSTRUCTIONS
from tools.faq import consultar_faq
from tools.qualification import registrar_estado
from tools.crm import escalonar_lead
from tools.calendar import buscar_horarios_livres, agendar_visita

# ---------------------------------------------------------------------------
# Database (persistência de sessão)
# Em produção, trocar por PostgresDb ou equivalente.
# ---------------------------------------------------------------------------
DB_PATH = os.getenv("AGENT_DB_PATH", "data/agent_sessions.db")
db = SqliteDb(db_file=DB_PATH)


def _make_agent_tools(session_id: str, contact_id: str | None = None, conversation_id: str | None = None) -> list:
    """
    Cria wrappers das tools com session_id injetado.
    """



    def _escalonar_lead(motivo: str, mensagem_despedida: str = "") -> str:
        """
        Escalona o lead para um consultor humano.

        Use quando: o lead pedir para falar com humano, preferir continuar por WhatsApp,
        ou quando o agendamento foi concluído e precisa transferir para vendas.

        Args:
            motivo: Motivo do escalonamento (ex: 'cliente_prefere_whatsapp', 'agendamento_realizado').
            mensagem_despedida: Mensagem de despedida que foi enviada ao lead.
        """
        if not contact_id or not conversation_id:
            return "Erro: contact_id ou conversation_id não disponíveis para escalonamento."
        result = escalonar_lead(
            session_id=session_id,
            contact_id=contact_id,
            conversation_id=conversation_id,
            motivo=motivo,
            mensagem_despedida=mensagem_despedida,
        )
        try:
            payload = json.loads(result)
        except json.JSONDecodeError:
            return result

        if payload.get("ok"):
            registrar_estado(session_id=session_id, motivo_handoff=motivo)
        return result

    def _agendar_visita(data_hora_iso: str, nome: str, email: str = "", telefone: str = "") -> str:
        """
        Realiza o agendamento oficial no calendário do GHL.

        Use SOMENTE quando o lead confirmar data e horário exatos para visita.
        Antes de agendar, use buscar_horarios_livres para verificar a disponibilidade.
        Só confirme ao lead se a resposta vier com ok=true e creation_verified=true.

        Args:
            data_hora_iso: Data e horário no formato ISO (ex: 2026-05-09T10:00:00).
            nome: Nome do lead.
            email: Email do lead (opcional).
            telefone: Telefone do lead (opcional, o sistema já possui).
        """
        result = agendar_visita(
            data_hora_iso=data_hora_iso,
            nome=nome,
            email=email,
            telefone=telefone,
            contact_id=contact_id or "",
        )
        try:
            payload = json.loads(result)
        except json.JSONDecodeError:
            return result

        if payload.get("ok") and payload.get("creation_verified") and payload.get("start_time"):
            registrar_estado(
                session_id=session_id,
                data_visita=payload["start_time"],
            )
        return result

    return [
        _escalonar_lead,
        buscar_horarios_livres,
        _agendar_visita,
    ]


def create_lucas_agent(
    session_id: str,
    user_id: str | None = None,
    contact_id: str | None = None,
    conversation_id: str | None = None,
) -> Agent:
    """
    Fábrica do Lucas SDR Agent.
    """
    model_id = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    api_key = os.getenv("OPENAI_API_KEY")

    # Tools com session_id injetado
    tools = _make_agent_tools(session_id, contact_id=contact_id, conversation_id=conversation_id)

    agent = Agent(
        name="Lucas SDR",
        model=OpenAIChat(id=model_id, api_key=api_key),
        description=LUCAS_DESCRIPTION,
        instructions=LUCAS_INSTRUCTIONS,
        # Tools operacionais restritas apenas a agendamento e handoff
        tools=[consultar_faq, *tools],
        # Persistência de sessão
        db=db,
        session_id=session_id,
        user_id=user_id,
        # Memória conversacional
        add_history_to_context=True,
        num_history_runs=8,
        # Experiência
        markdown=False,  # WhatsApp não renderiza markdown
        add_datetime_to_context=True,
    )

    return agent
