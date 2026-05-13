"""
CRM Tool — Sincronização de dados com o GoHighLevel.

Permite que o agente salve o progresso da qualificação no CRM real,
criando contatos, oportunidades, notas e realize escalonamento.
"""

import os
import json

from loguru import logger

from services.ghl import (
    upsert_contact,
    upsert_opportunity,
    add_contact_note,
    remove_contact_tag_sync,
    trigger_workflow,
    notify_escalation,
)
from tools.qualification import _get_lead


def sincronizar_com_crm(session_id: str, phone: str) -> str:
    """
    Sincroniza os dados atuais de qualificação do lead com o CRM GoHighLevel.

    Chame esta ferramenta quando a qualificação avançar significativamente
    (ex: o cliente informou nome e interesse) ou quando o agendamento/handoff ocorrer.

    Args:
        session_id: ID da sessão atual.
        phone: Telefone do cliente (obrigatório para busca no CRM).

    Returns:
        Status da sincronização.
    """
    lead = _get_lead(session_id)

    # 1. Garantir contato no GHL
    try:
        contact = upsert_contact(phone=phone, name=lead.nome)
        contact_id = contact.get("id")
    except Exception as e:
        logger.error("Erro no upsert_contact: {err}", err=str(e))
        return json.dumps({"ok": False, "error": "crm_contact_sync_failed"}, ensure_ascii=False)

    # 2. Mapear status ZAF -> Pipeline GHL
    pipeline_id = os.getenv("GHL_PIPELINE_ID", "default_pipeline")

    stages = {
        "NEW_LEAD": os.getenv("GHL_STAGE_NEW", "stage_1"),
        "QUALIFYING": os.getenv("GHL_STAGE_QUALIFYING", "stage_2"),
        "QUALIFIED": os.getenv("GHL_STAGE_QUALIFIED", "stage_3"),
        "SCHEDULING": os.getenv("GHL_STAGE_SCHEDULING", "stage_4"),
        "SCHEDULED": os.getenv("GHL_STAGE_SCHEDULED", "stage_5"),
        "HANDOFF": os.getenv("GHL_STAGE_HANDOFF", "stage_6"),
    }

    stage_id = stages.get(lead.status.value, stages["NEW_LEAD"])
    opp_title = f"Interesse: {lead.modelo_preferido or lead.tipo_veiculo or 'Lead ZAF'}"

    # 3. Atualizar Oportunidade
    try:
        upsert_opportunity(
            contact_id=contact_id,
            pipeline_id=pipeline_id,
            stage_id=stage_id,
            title=opp_title
        )
    except Exception as e:
        logger.warning("Erro no upsert_opportunity: {err}", err=str(e))

    # 4. Adicionar nota com resumo da qualificação
    try:
        resumo = (
            f"--- Atualização ZAF Agent ---\n"
            f"Status: {lead.status.value}\n"
            f"Nome: {lead.nome or 'Não informado'}\n"
            f"Interesse: {lead.interesse or lead.veiculo_interesse or lead.modelo_preferido or lead.tipo_veiculo or 'Não informado'}\n"
            f"Intenção: {lead.intencao or ('Troca de ' + lead.veiculo_troca if lead.veiculo_troca else 'Compra')}\n"
            f"Motivação: {lead.motivacao or lead.motivo_troca or 'Não informado'}\n"
            f"Negociação: {lead.negociacao or ('Financiamento' if lead.precisa_financiamento else 'Não informado')}\n"
            f"Cidade: {lead.cidade or ('Joinville/região' if lead.e_local else 'Não informado')}\n"
            f"Observações: {lead.observacoes or lead.motivo_handoff or 'Nenhuma'}\n"
            f"Agendamento: {lead.data_visita or 'Pendente'}\n"
        )
        if lead.conversation_summary:
            resumo += f"\n--- Resumo ---\n{lead.conversation_summary}\n"
        if lead.lead_answers:
            resumo += "\n--- Respostas ---\n" + "\n".join([f"- {k.capitalize()}: {v}" for k, v in lead.lead_answers.items()])
        
        add_contact_note(contact_id=contact_id, body=resumo)
    except Exception as e:
        logger.warning("Erro ao adicionar nota: {err}", err=str(e))

    # 5. Lidar com Handoff (remover tag)
    if lead.status.value == "HANDOFF":
        required_tag = os.getenv("GHL_REQUIRED_TAG", "agente-ia-dev")
        logger.info("Handoff detectado. Removendo tag '{tag}' do contato {cid}", tag=required_tag, cid=contact_id)
        remove_contact_tag_sync(contact_id, required_tag)
        return json.dumps(
            {
                "ok": True,
                "status": "HANDOFF",
                "contact_id": contact_id,
                "removed_tag": required_tag,
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "ok": True,
            "status": lead.status.value,
            "contact_id": contact_id,
            "pipeline_stage": stage_id,
        },
        ensure_ascii=False,
    )


def escalonar_lead(
    session_id: str,
    contact_id: str,
    conversation_id: str,
    motivo: str,
    mensagem_despedida: str,
) -> str:
    """
    Escalona o lead para um consultor humano.

    Executa o fluxo completo de escalonamento:
    1. Envia nota estruturada no CRM
    2. Notifica o webhook de pré-atendimento
    3. Dispara o workflow GHL de escalonamento
    4. Remove a tag do agente IA

    Args:
        session_id: ID da sessão atual.
        contact_id: ID do contato no GHL.
        conversation_id: ID da conversa no GHL.
        motivo: Motivo do escalonamento (ex: 'cliente_prefere_whatsapp', 'agendamento_realizado').
        mensagem_despedida: Mensagem de despedida enviada ao lead.

    Returns:
        Status do escalonamento.
    """
    import asyncio
    lead = _get_lead(session_id)

    # Montar nota estruturada
    nota = _build_structured_note(lead, motivo)

    # Adicionar nota no CRM
    try:
        nota_crm = f"[Motivo: {motivo}]\n\n{nota}".strip()
        add_contact_note(contact_id=contact_id, body=nota_crm)
        logger.info("Nota de escalonamento adicionada | contact={cid}", cid=contact_id[:10])
    except Exception as e:
        logger.error("Erro ao adicionar nota de escalonamento: {err}", err=str(e))

    # Executar funções async do escalonamento
    async def _run_escalation():
        # Notificar webhook de pré-atendimento
        await notify_escalation(
            contact_id=contact_id,
            conversation_id=conversation_id,
            reason=motivo,
            note=nota,
            farewell_message=mensagem_despedida,
        )
        # Disparar workflow GHL
        await trigger_workflow(contact_id)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_run_escalation())
        else:
            loop.run_until_complete(_run_escalation())
    except RuntimeError:
        asyncio.run(_run_escalation())

    # Remover tag do agente IA
    required_tag = os.getenv("GHL_REQUIRED_TAG", "agente-ia-dev")
    remove_contact_tag_sync(contact_id, required_tag)
    logger.info(
        "Escalonamento concluído | contact={} | motivo={}",
        contact_id[:10], motivo,
    )

    return json.dumps(
        {
            "ok": True,
            "status": "handoff_notified",
            "contact_id": contact_id,
            "conversation_id": conversation_id,
            "reason": motivo,
        },
        ensure_ascii=False,
    )


def _build_structured_note(lead, motivo: str) -> str:
    """Monta nota estruturada de handoff para o CRM."""
    lines = [f"Motivo: {motivo}", ""]

    if lead.nome:
        lines.append(f"Nome: {lead.nome}")
    if lead.modelo_preferido or lead.tipo_veiculo:
        lines.append(f"Interesse: {lead.interesse or lead.modelo_preferido or lead.tipo_veiculo}")
    if lead.intencao:
        lines.append(f"Intenção: {lead.intencao}")
    elif lead.veiculo_troca:
        lines.append(f"Intenção: Troca de {lead.veiculo_troca}")
    if lead.motivacao or lead.motivo_troca:
        lines.append(f"Motivação: {lead.motivacao or lead.motivo_troca}")
    if lead.negociacao:
        lines.append(f"Negociação: {lead.negociacao}")
    if lead.cidade:
        lines.append(f"Cidade: {lead.cidade}")
    if lead.observacoes:
        lines.append(f"Observações: {lead.observacoes}")
    if lead.veiculo_interesse:
        lines.append(f"Veículo do estoque: {lead.veiculo_interesse}")
    if lead.faixa_preco:
        lines.append(f"Faixa de preço: {lead.faixa_preco}")

    troca = "Sim"
    if lead.tem_troca:
        troca = f"Sim ({lead.veiculo_troca or 'não informado'})"
    elif lead.tem_troca is False:
        troca = "Não"
    else:
        troca = "Não informado"
    lines.append(f"Troca: {troca}")

    if lead.precisa_financiamento is not None:
        lines.append(f"Financiamento: {'Sim' if lead.precisa_financiamento else 'Não (à vista)'}")
    if lead.e_local is not None:
        lines.append(f"Local: {'Joinville/região' if lead.e_local else 'Outra cidade'}")
    if lead.data_visita:
        lines.append(f"Agendamento: {lead.data_visita}")

    if lead.conversation_summary:
        lines.append("\n--- Resumo da Conversa ---")
        lines.append(lead.conversation_summary)

    if lead.lead_answers:
        lines.append("\n--- Respostas Exatas do Cliente ---")
        for key, answer in lead.lead_answers.items():
            lines.append(f"- {key.capitalize()}: {answer}")

    return "\n".join(lines)
