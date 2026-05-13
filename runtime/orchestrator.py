"""
Orchestrator — Runtime fino do ZAF.

Responsável por:
1. Receber a mensagem já normalizada do webhook.
2. Recuperar contexto factual da sessão.
3. Instanciar o agente correto.
4. Executar o agente e devolver a resposta.
"""


import json
import re

# Import logging
# pyrefly: ignore [missing-import]
from loguru import logger


from agents.lucas import create_lucas_agent
from services.ghl import get_messages_async
from tools.qualification import _get_lead, registrar_qualificacao, registrar_estado
from tools.inventory import consultar_estoque, get_vehicle_photo_urls
from runtime.intent_extractor import extract_intent_from_message

INITIAL_GREETING_MARKER = "[SAUDAÇÃO INICIAL]"


def _detect_unanswered(ghl_messages: list[dict]) -> list[str]:
    """Detecta mensagens do usuário que ainda não foram respondidas (Buffer)."""
    if not ghl_messages:
        return []
    
    unanswered = []
    # Percorrer do final para o início
    for msg in reversed(ghl_messages):
        # Se achamos uma mensagem do assistente (outbound), paramos a busca de pendências
        if msg.get("direction") == "outbound":
            break
        # Se for inbound (do lead), adicionamos à lista de mensagens a responder
        if msg.get("direction") == "inbound":
            body = msg.get("body", "").strip()
            if body:
                unanswered.insert(0, body)
    
    if len(unanswered) > 1:
        logger.info("Buffer detectado | mensagens_pendentes={count}", count=len(unanswered))

    return unanswered


def _get_last_outbound(ghl_messages: list[dict]) -> str | None:
    """Busca a última mensagem enviada pelo agente para contexto."""
    if not ghl_messages:
        return None
    for msg in reversed(ghl_messages):
        if msg.get("direction") == "outbound":
            return msg.get("body", "").strip()
    return None


def _format_pending_messages(unanswered: list[str]) -> str | None:
    """
    Formata mensagens pendentes para o modelo responder múltiplos inputs sem misturar assuntos.
    """
    if len(unanswered) <= 1:
        return None

    numbered_messages = "\n".join(
        f"{index}. {message}" for index, message in enumerate(unanswered, start=1)
    )
    return (
        "[MENSAGENS PENDENTES DO LEAD]\n"
        f"{numbered_messages}\n"
        "[INSTRUÇÃO]\n"
        "Responda na ordem das mensagens, mantendo o contexto entre elas e sem ignorar "
        "pedidos objetivos que tenham ficado pendentes."
    )


def _build_initial_greeting(user_message: str) -> str:
    """Saudação inicial determinística — mantida por decisão de produto."""
    vehicle_match = re.search(r"\[SAUDAÇÃO INICIAL\]\s*Veículo:\s*(.+)", user_message, re.IGNORECASE)
    if vehicle_match:
        vehicle_name = vehicle_match.group(1).strip()
        return (
            f"Olá! 👋 Bem-vindo à AMC Veículos. Vi que você demonstrou interesse no "
            f"{vehicle_name} 🚗. Posso te passar mais informações sobre ele?"
        )
    return "Olá! 👋 Bem-vindo à AMC Veículos. Como posso te ajudar hoje? Está procurando algum carro específico?"


def _filter_stock_by_model(estoque_raw: str, search_query: str) -> str:
    """
    Pós-filtra resultados de estoque para focar no modelo exato quando aplicável.
    
    Regras:
    1. Modelo específico + 1 unidade → só essa unidade
    2. Modelo específico + N unidades → todas do modelo
    3. Busca ampla → até 3 melhores
    """
    try:
        data = json.loads(estoque_raw)
    except (json.JSONDecodeError, TypeError):
        return f"O SISTEMA BUSCOU ESTOQUE PARA '{search_query}'. RESULTADO:\n{estoque_raw}"

    matches = data.get("matches", [])
    if not matches:
        return f"O SISTEMA BUSCOU ESTOQUE PARA '{search_query}'. NENHUM VEÍCULO ENCONTRADO."

    # Extrair palavras significativas da busca (ignorar palavras curtas)
    query_words = {w.lower() for w in re.findall(r"\w+", search_query) if len(w) >= 3}

    # Identificar matches do modelo exato
    exact_model_matches = []
    for m in matches:
        modelo = str(m.get("modelo", "")).lower()
        marca = str(m.get("marca", "")).lower()
        
        # O match exato deve ser prioritariamente no MODELO. 
        # Se a query contém apenas a marca (ex: 'Chevrolet'), vai dar match em todos. 
        # Mas se for 'Chevrolet Ipanema', Cruze não deve dar match só pela marca.
        modelo_words = {w for w in re.findall(r"\w+", modelo) if len(w) >= 3}
        marca_words = {w for w in re.findall(r"\w+", marca) if len(w) >= 3}
        
        # Removemos a marca das palavras da query para ver se sobra algo do modelo
        query_model_words = query_words - marca_words
        
        is_exact_match = False
        if query_model_words and (query_model_words & modelo_words):
            # Se tem palavras específicas do modelo na query e elas dão match no modelo
            is_exact_match = True
        elif not query_model_words and (query_words & marca_words):
            # Se a query for APENAS a marca (ex: "Chevrolet")
            is_exact_match = True
            
        if is_exact_match:
            exact_model_matches.append(m)

    if exact_model_matches:
        # Regra 1 e 2: foco no modelo exato
        data["matches"] = exact_model_matches
        data["count"] = len(exact_model_matches)
        filtered_json = json.dumps(data, ensure_ascii=False)

        if len(exact_model_matches) == 1:
            logger.info(f"Estoque filtrado | tipo=modelo_unico | modelo={exact_model_matches[0].get('modelo')}")
            return (
                f"O SISTEMA ENCONTROU EXATAMENTE 1 UNIDADE DE '{search_query}' NO ESTOQUE. "
                f"APRESENTE APENAS ESTE VEÍCULO. NÃO SUGIRA ALTERNATIVAS.\n{filtered_json}"
            )
        else:
            logger.info(f"Estoque filtrado | tipo=multiplas_unidades | count={len(exact_model_matches)}")
            return (
                f"O SISTEMA ENCONTROU {len(exact_model_matches)} UNIDADES DE '{search_query}' NO ESTOQUE. "
                f"APRESENTE TODAS AS OPÇÕES DESTE MODELO.\n{filtered_json}"
            )
    else:
        # Regra 3: busca ampla — limitar a 3
        data["matches"] = matches[:3]
        data["count"] = len(matches[:3])
        filtered_json = json.dumps(data, ensure_ascii=False)
        logger.info(f"Estoque filtrado | tipo=busca_ampla | count={len(matches[:3])}")
        return (
            f"O SISTEMA BUSCOU OPÇÕES PARA '{search_query}'. "
            f"APRESENTE AS MELHORES OPÇÕES ENCONTRADAS.\n{filtered_json}"
        )

def _build_session_context(session_id: str) -> str:
    lead = _get_lead(session_id)
    state_payload = lead.to_dict()

    context_lines = [
        "[CONTEXTO SESSAO]",
        f"LEAD_STATUS_ATUAL={lead.status.value}",
        f"SESSION_STATE_JSON={json.dumps(state_payload, ensure_ascii=False)}",
    ]
    
    # Lacunas factuais — apenas informa o que ainda não sabemos, sem sugerir ação
    missing = lead.get_missing_fields()
    if missing:
        context_lines.append(f"QUALIFICACAO_PENDENTE={', '.join(missing)}")
    if lead.lead_answers:
        context_lines.append(f"LEAD_ANSWERS={json.dumps(lead.lead_answers, ensure_ascii=False)}")
    if lead.conversation_summary:
        context_lines.append(f"CONVERSATION_SUMMARY={lead.conversation_summary}")

    return "\n".join(context_lines)


def _sanitize_agent_reply(reply: str) -> str:
    """Normaliza separação em blocos sem reescrever a resposta do agente."""
    blocks = [block.strip() for block in reply.split("|||")]
    sanitized_blocks: list[str] = []

    for block in blocks:
        if not block:
            continue

        normalized = re.sub(r"\?([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ])", r"? \1", block)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        normalized = "\n".join(line.rstrip() for line in normalized.splitlines())
        normalized = re.sub(r"[ \t]{2,}", " ", normalized).strip()
        if normalized:
            sanitized_blocks.append(normalized)

    return " ||| ".join(sanitized_blocks).strip()


async def process_message(
    session_id: str,
    user_message: str,
    user_id: str | None = None,
    contact_id: str | None = None,
    conversation_id: str | None = None
) -> dict:
    """
    Processa uma mensagem de entrada e retorna a resposta do agente.

    Args:
        session_id: Identificador único da conversa (ex: telefone do lead).
        user_message: Texto enviado pelo lead.
        user_id: Identificador opcional do usuário/lead.

    Returns:
        Dicionário com session_id, resposta do agente e metadata.
    """
    logger.info(
        "Processando mensagem | session={session} | msg={msg}",
        session=session_id,
        msg=user_message[:80],
    )

    if user_message.startswith(INITIAL_GREETING_MARKER):
        agent_reply = _build_initial_greeting(user_message)
        logger.info("Saudação inicial determinística | session={session}", session=session_id)
        return {
            "session_id": session_id,
            "reply": agent_reply,
        }

    # 1. Sincronização de Contexto (GHL as Source of Truth)
    input_text = user_message
    last_outbound = None
    
    if conversation_id:
        ghl_history = await get_messages_async(conversation_id)
        unanswered = _detect_unanswered(ghl_history)
        last_outbound = _get_last_outbound(ghl_history)
        
        # Se a mensagem original (user_message) for uma transcrição, 
        # não queremos que ela seja sobrescrita pelo placeholder "> Voice Note <" do histórico.
        is_placeholder = user_message.lower().strip() in ["> voice note <", "voice note"]
        
        # Se NÃO for um placeholder (ou seja, é uma transcrição real ou texto), 
        # e houver outras mensagens pendentes, concatenamos.
        # Mas se a última do histórico for o placeholder do áudio que acabamos de transcrever, 
        # mantemos a transcrição.
        
        pending_text = _format_pending_messages(unanswered)
        if pending_text:
            # Se a última mensagem do histórico for o placeholder do áudio, 
            # e nosso user_message for a transcrição, substituímos no texto final.
            if "> Voice Note <" in pending_text and not is_placeholder:
                input_text = pending_text.replace("> Voice Note <", user_message)
            else:
                input_text = pending_text

    # 2. Extração Fria de Intenção e Execução de Tools Silenciosa (AI-Native V3)
    system_injections = []
    try:
        logger.info("Executando Intent Extractor no fundo...")
        
        extractor_context = ""
        if last_outbound:
            extractor_context = f"Sua última pergunta/fala para o lead foi: '{last_outbound}'"
            
        intent = extract_intent_from_message(input_text, context=extractor_context)
        
        # A. Atualiza o Estado/CRM se o lead forneceu fatos novos
        facts = intent.qualification_facts.model_dump(exclude_none=True)
        if facts:
            logger.info(f"Fatos extraídos: {facts}")
            registrar_qualificacao(session_id=session_id, **facts)
            system_injections.append(f"O SISTEMA IDENTIFICOU E SALVOU FATOS NOVOS: {json.dumps(facts, ensure_ascii=False)}")
            
        # B. Busca de Estoque Contextual (unificado)
        # Aciona quando: (1) lead perguntou sobre carro, OU (2) lead aceitou receber info e tem veículo em foco
        should_search_stock = intent.is_asking_for_vehicle or intent.is_accepting_info
        if should_search_stock:
            lead_ctx = _get_lead(session_id)
            # Prioridade: query explícita > veículo de interesse > vehicle_focus
            search_query = (
                intent.vehicle_query
                or lead_ctx.veiculo_interesse
                or lead_ctx.vehicle_focus.current
            )
            if search_query:
                logger.info(f"Buscando estoque | trigger={'vehicle_ask' if intent.is_asking_for_vehicle else 'acceptance'} | query={search_query}")
                estoque_raw = consultar_estoque(
                    prompt_busca=search_query,
                    modo="discovery",
                    limite=3,
                )
                # Pós-filtro: separar match exato do modelo vs alternativas
                filtered_result = _filter_stock_by_model(estoque_raw, search_query)
                system_injections.append(filtered_result)

        # C. Busca Fotos se o lead pedir (Desacoplamento Visual)
        photos_to_send = []
        if intent.is_asking_for_photos:
            lead = _get_lead(session_id)
            # Prioridade para FOTOS: 1. vehicle_query (se o lead especificou 'desse 2015') 2. vehicle_focus 3. veiculo_interesse
            # Proteção: Ignorar se o vehicle_query bater com o carro de troca.
            query = intent.vehicle_query
            if query and lead.veiculo_troca and query.lower().strip() in lead.veiculo_troca.lower().strip():
                query = None # Ignora, é o carro de troca
                
            query = query or lead.vehicle_focus.current or lead.veiculo_interesse
            if query:
                # Se o lead escolheu um veículo diferente do foco atual, atualiza o foco
                if query != lead.vehicle_focus.current:
                    registrar_estado(session_id=session_id, vehicle_focus_current=query)
                logger.info(f"Buscando fotos no fundo para: {query}")
                photos_to_send = get_vehicle_photo_urls(query, limit=10)
                if photos_to_send:
                    system_injections.append(f"O SISTEMA ENVIOU {len(photos_to_send)} FOTOS DO VEÍCULO DA LOJA PARA O CLIENTE.")
                
        # D. Densidade e Maturidade (Prevenir fechamento prematuro)
        lead = _get_lead(session_id)
        score = lead.completeness_score()
        if score < 50 and not intent.wants_human:
            missing = lead.get_missing_fields() if lead.get_missing_fields() else ['vários campos']
            missing_summary = ', '.join(missing)
            system_injections.append(
                f"MATURIDADE BAIXA ({score}%). NÃO agende agora. "
                f"Lacunas: {missing_summary}. "
                f"Continue a qualificação antes de propor visita ou agendamento."
            )

    except Exception as e:
        logger.error(f"Erro no Intent Extractor: {str(e)}")

    # 3. Injetar apenas contexto factual e injeções do sistema.
    injection_text = "\n".join(system_injections) if system_injections else ""
    input_text = _build_session_context(session_id) + f"\n[NOTAS INVISÍVEIS DO SISTEMA]\n{injection_text}\n\n[MSG DO LEAD]\n{input_text}"

    # 4. Criar o agente com o contexto da sessão
    agent = create_lucas_agent(
        session_id=session_id,
        user_id=user_id,
        contact_id=contact_id,
        conversation_id=conversation_id,
    )

    # 4. Executar o agente (async)
    try:
        response = await agent.arun(input=input_text)
        raw_reply = response.content or ""
        
        # Failsafe: Remover qualquer link markdown ou URL de imagem que a LLM tente inventar
        import re
        clean_reply = re.sub(r"!\[.*\]\(.*\)", "", raw_reply) # Remove ![txt](url)
        clean_reply = re.sub(r"\[.*\]\(.*\)", "", clean_reply) # Remove [txt](url)
        clean_reply = re.sub(r"http[s]?://\S+", "", clean_reply) # Remove URLs brutas
        
        # Converter **negrito** para *negrito* (padrão WhatsApp)
        clean_reply = clean_reply.replace("**", "*")
        
        agent_reply = _sanitize_agent_reply(clean_reply)
    except Exception as e:
        logger.error("Erro no agente | session={session} | error={err}", session=session_id, err=str(e))
        agent_reply = "Desculpe, tive um problema ao processar sua mensagem. Tente novamente em instantes."

    logger.info(
        "Resposta gerada | session={session} | reply={reply}",
        session=session_id,
        reply=agent_reply[:80],
    )

    return {
        "session_id": session_id,
        "reply": agent_reply,
        "attachments": photos_to_send if 'photos_to_send' in locals() and photos_to_send else None,
    }
