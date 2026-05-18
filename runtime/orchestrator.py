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
from tools.inventory import consultar_estoque, detect_vehicle_mentions, get_vehicle_photo_urls, resolve_vehicle_target
from runtime.intent_extractor import extract_intent_from_message

INITIAL_GREETING_MARKER = "[SAUDAÇÃO INICIAL]"
PHOTO_PROMISE_PATTERNS = (
    "te mando as fotos",
    "te mando umas fotos",
    "te mando foto",
    "mando as fotos",
    "mando umas fotos",
    "mando foto",
    "vou mandar as fotos",
    "vou mandar foto",
    "vou te mandar",
    "ja te envio",
    "já te envio",
    "ja envio",
    "já envio",
    "envio depois",
    "envio quando",
    "mando depois",
    "mando quando",
    "mando assim que",
    "te envio as fotos",
    "te envio foto",
    "encaminho as fotos",
    "encaminho foto",
    "to enviando",
    "tô enviando",
    "estou enviando",
    "ja mandei",
    "já mandei",
)


def _detect_photo_promise(text: str) -> bool:
    normalized = _normalize_vehicle_text(text)
    if not normalized:
        return False
    return any(p in normalized for p in PHOTO_PROMISE_PATTERNS)


WHATSAPP_CONTINUATION_PATTERNS = (
    "continuar pelo whatsapp",
    "seguir pelo whatsapp",
    "falar pelo whatsapp",
    "resolvemos por whatsapp",
    "ver por whatsapp",
    "prefiro pelo whatsapp",
    "quero pelo whatsapp",
    "sem agendar",
    "sem visita",
)


def _normalize_vehicle_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _extract_query_tokens(search_query: str) -> set[str]:
    normalized = _normalize_vehicle_text(search_query)
    tokens = {w.lower() for w in re.findall(r"\w+", search_query) if len(w) >= 3}
    if normalized and len(normalized) >= 3:
        tokens.add(normalized)
    return tokens


def _is_exact_model_match(search_query: str, vehicle: dict) -> bool:
    query_tokens = _extract_query_tokens(search_query)
    if not query_tokens:
        return False

    modelo = str(vehicle.get("modelo", "")).lower()
    marca = str(vehicle.get("marca", "")).lower()
    modelo_norm = _normalize_vehicle_text(modelo)
    marca_norm = _normalize_vehicle_text(marca)
    modelo_words = {w for w in re.findall(r"\w+", modelo) if len(w) >= 3}
    marca_words = {w for w in re.findall(r"\w+", marca) if len(w) >= 3}
    if modelo_norm and len(modelo_norm) >= 3:
        modelo_words.add(modelo_norm)
    if marca_norm and len(marca_norm) >= 3:
        marca_words.add(marca_norm)

    query_model_words = query_tokens - marca_words
    if query_model_words and (query_model_words & modelo_words):
        return True
    if modelo_norm and any(token == modelo_norm or token.endswith(modelo_norm) or modelo_norm.endswith(token) for token in query_model_words):
        return True
    if not query_model_words and (query_tokens & marca_words):
        return True
    return False


def _wants_whatsapp_continuation(text: str) -> bool:
    normalized = _normalize_vehicle_text(text)
    if not normalized:
        return False
    return any(_normalize_vehicle_text(pattern) in normalized for pattern in WHATSAPP_CONTINUATION_PATTERNS)


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

    # Identificar matches do modelo exato
    exact_model_matches = []
    for m in matches:
        if _is_exact_model_match(search_query, m):
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
            f"O SISTEMA BUSCOU POR '{search_query}', MAS NÃO ENCONTROU O MODELO EXATO. "
            f"INFORME AO LEAD QUE NÃO TEMOS O MODELO ESPECÍFICO DISPONÍVEL NO MOMENTO, "
            f"MAS APRESENTE ESTAS 3 MELHORES ALTERNATIVAS ABAIXO PARA MANTER O INTERESSE.\n{filtered_json}"
        )


def _filter_stock_payload(estoque_raw: str, search_query: str) -> dict | None:
    try:
        data = json.loads(estoque_raw)
    except (json.JSONDecodeError, TypeError):
        return None

    matches = data.get("matches", [])
    if not matches:
        return data

    exact_model_matches = []
    for match in matches:
        if _is_exact_model_match(search_query, match):
            exact_model_matches.append(match)

    filtered = dict(data)
    if exact_model_matches:
        filtered["matches"] = exact_model_matches
        filtered["count"] = len(exact_model_matches)
        return filtered

    filtered["matches"] = matches[:3]
    filtered["count"] = len(matches[:3])
    return filtered


def _normalize_title(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def _build_stock_injection(
    filtered_payload: dict | None,
    search_query: str,
    fallback_raw: str,
    already_presented_titles: set[str] | None = None,
) -> str:
    if not filtered_payload:
        return f"O SISTEMA BUSCOU ESTOQUE PARA '{search_query}'. RESULTADO:\n{fallback_raw}"

    matches = filtered_payload.get("matches", [])
    if not matches:
        return f"O SISTEMA BUSCOU ESTOQUE PARA '{search_query}'. NENHUM VEÍCULO ENCONTRADO."

    # Suppress re-presentation: if every match was already shown to the lead, don't
    # re-inject the card. The lead is just answering questions, not asking to see it again.
    already_presented_titles = already_presented_titles or set()
    if already_presented_titles:
        match_titles = {
            _normalize_title(item.get("titulo") or item.get("modelo"))
            for item in matches
        }
        match_titles.discard("")
        if match_titles and match_titles.issubset(already_presented_titles):
            return (
                f"O SISTEMA REVERIFICOU '{search_query}': segue disponível e os dados não mudaram. "
                f"ESTE(S) VEÍCULO(S) JÁ FORAM APRESENTADOS AO LEAD. NÃO reapresente o card nem repita "
                f"ano/km/câmbio/valor. O lead está apenas respondendo perguntas — apenas continue a "
                f"qualificação de onde parou."
            )

    filtered_json = json.dumps(filtered_payload, ensure_ascii=False)
    if len(matches) == 1:
        return (
            f"O SISTEMA ENCONTROU EXATAMENTE 1 UNIDADE DE '{search_query}' NO ESTOQUE. "
            f"APRESENTE APENAS ESTE VEÍCULO. NÃO SUGIRA ALTERNATIVAS.\n{filtered_json}"
        )

    exact_titles = {
        str(item.get("modelo", "")).lower().strip()
        for item in matches
        if str(item.get("modelo", "")).strip()
    }
    query_lower = search_query.lower().strip()
    if any(model and model in query_lower for model in exact_titles):
        return (
            f"O SISTEMA ENCONTROU {len(matches)} UNIDADES DE '{search_query}' NO ESTOQUE. "
            f"APRESENTE TODAS AS OPÇÕES DESTE MODELO.\n{filtered_json}"
        )

    return (
        f"O SISTEMA BUSCOU POR '{search_query}', MAS NÃO ENCONTROU O MODELO EXATO. "
        f"INFORME AO LEAD QUE NÃO TEMOS O MODELO ESPECÍFICO DISPONÍVEL NO MOMENTO, "
        f"MAS APRESENTE ESTAS 3 MELHORES ALTERNATIVAS ABAIXO PARA MANTER O INTERESSE.\n{filtered_json}"
    )

def _build_session_context(session_id: str) -> str:
    lead = _get_lead(session_id)

    context_lines = [
        "[CONTEXTO SESSAO]",
        f"LEAD_STATUS_ATUAL={lead.status.value}",
        f"VEICULO_INTERESSE_ATUAL={lead.veiculo_interesse}",
        f"VEICULO_TROCA_ATUAL={lead.veiculo_troca}",
        f"KM_TROCA_ATUAL={lead.km_troca}",
        f"QUITADO_TROCA_ATUAL={lead.quitado_troca}",
        f"ESTADO_TROCA_ATUAL={lead.estado_troca}",
        f"FOTOS_TROCA_RECEBIDAS_ATUAL={lead.fotos_troca_recebidas}",
        f"PRECISA_FINANCIAMENTO_ATUAL={lead.precisa_financiamento}",
        f"VEICULO_SAUDACAO={lead.vehicle_journey.greeting_vehicle}",
        f"VEICULO_FOCO_ATUAL={lead.vehicle_journey.current_focus}",
        f"VEICULO_SOLICITADO_NESTE_TURNO={lead.vehicle_journey.current_request}",
        f"VEICULO_ALVO_FOTOS={lead.vehicle_journey.photo_target}",
        f"NOME_LEAD={lead.nome}",
        f"CIDADE_LEAD={lead.cidade}",
        f"INTENCAO_LEAD={lead._intencao_texto()}",
        f"MOTIVACAO_LEAD={lead.motivacao}",
        f"NEGOCIACAO_LEAD={lead.negociacao}",
        f"TEM_TROCA={lead.tem_troca}",
    ]
    
    # Lacunas factuais — apenas informa o que ainda não sabemos, sem sugerir ação
    missing = lead.get_missing_fields()
    if missing:
        context_lines.append(f"QUALIFICACAO_PENDENTE={', '.join(missing)}")
    missing_trade = lead.get_missing_trade_fields()
    if missing_trade:
        context_lines.append(f"DADOS_TROCA_PENDENTES={', '.join(missing_trade)}")
    if lead.lead_answers:
        context_lines.append(f"LEAD_ANSWERS={json.dumps(lead.lead_answers, ensure_ascii=False)}")
    if lead.conversation_summary:
        context_lines.append(f"CONVERSATION_SUMMARY={lead.conversation_summary}")

    presented_titles = [v.titulo for v in lead.vehicle_journey.presented_vehicles if v.titulo]
    if presented_titles:
        context_lines.append(f"VEICULOS_JA_CONFIRMADOS_DISPONIVEIS={json.dumps(presented_titles, ensure_ascii=False)}")
        context_lines.append(f"VEICULOS_JA_SUGERIDOS={json.dumps(presented_titles, ensure_ascii=False)}")

    score = lead.completeness_score()
    temperature = "hot" if score >= 70 else "warm" if score >= 40 else "cold"
    context_lines.append(f"LEAD_TEMPERATURE={temperature}")
    context_lines.append(f"MATURIDADE_SCORE={score}%")

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
    logger.info("Processando mensagem | session={session}", session=session_id)

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
        
        # Failsafe: Nunca permitir que o nome do lead seja extraído como 'Lucas' (nome do agente)
        if facts.get("nome") and str(facts.get("nome")).lower().strip() == "lucas":
            logger.warning("Fato 'nome: Lucas' ignorado por ser o nome do agente.")
            facts.pop("nome")

        # Failsafe determinístico: se o lead prometeu mandar fotos, força a flag
        # mesmo que o extractor LLM não capture (evita ciclo de re-pedido de fotos).
        lead_existing = _get_lead(session_id)
        if (
            lead_existing.tem_troca is True
            and lead_existing.fotos_troca_recebidas is not True
            and _detect_photo_promise(input_text)
        ):
            facts["fotos_troca_recebidas"] = True
            logger.info("Promessa de fotos de troca detectada deterministicamente.")

        if facts:
            logger.info(f"Fatos extraídos: {facts}")
            registrar_qualificacao(session_id=session_id, **facts)
            system_injections.append(f"O SISTEMA IDENTIFICOU E SALVOU FATOS NOVOS: {json.dumps(facts, ensure_ascii=False)}")

        # Barreira anti-repetição: se fotos já foram tratadas, bloqueia novo pedido.
        lead_after_facts = _get_lead(session_id)
        if lead_after_facts.fotos_troca_recebidas is True:
            system_injections.append(
                "FOTOS_TROCA_JA_TRATADAS=True — O lead JÁ enviou ou JÁ prometeu enviar as fotos do carro de troca. "
                "PROIBIDO pedir fotos do veículo de troca neste turno e nos próximos. "
                "Apenas valide brevemente ('Perfeito, fico no aguardo') e avance para a próxima etapa. "
                "NUNCA repita pedido de fotos do carro do cliente."
            )

        visit_intent = bool(getattr(intent, "visit_intent", False))

        if visit_intent:
            lead_for_visit = _get_lead(session_id)
            visit_score = lead_for_visit.completeness_score()
            if visit_score >= 50:
                system_injections.append("SINAL_DE_VISITA_DETECTADO=True — O lead demonstrou intenção de visitar a loja e maturidade é suficiente. Proponha agendamento IMEDIATAMENTE com endereço e horário sugerido.")
            else:
                system_injections.append(f"SINAL_DE_VISITA_DETECTADO=True — O lead demonstrou intenção de visitar, mas maturidade ainda é baixa ({visit_score}%). Responda positivamente ('Claro, vamos agendar'), mas antes colete o dado faltante mais importante. Só agende no próximo turno.")

        if _wants_whatsapp_continuation(input_text):
            system_injections.append(
                "PREFERENCIA_WHATSAPP_DETECTADA=True — O lead não quer agendar visita agora e prefere seguir pelo WhatsApp. "
                "Não insista em visita. Conduza a continuidade remota e escalone com escalonar_lead."
            )

        lead_ctx = _get_lead(session_id)
        should_detect_vehicle_mentions = bool(
            intent.vehicle_query or intent.is_asking_for_vehicle or intent.is_asking_for_photos
        )
        mentioned_queries = detect_vehicle_mentions(input_text, limit=3) if should_detect_vehicle_mentions else []
        if intent.vehicle_query:
            normalized_explicit_query = intent.vehicle_query.strip().lower()
            existing_queries = {query.lower() for query in mentioned_queries}
            has_same_family = any(
                normalized_explicit_query in query or query in normalized_explicit_query
                for query in existing_queries
            )
            if normalized_explicit_query not in existing_queries and not has_same_family:
                mentioned_queries.insert(0, intent.vehicle_query.strip())

        if mentioned_queries:
            registrar_estado(
                session_id=session_id,
                vehicle_mentions=mentioned_queries,
                current_vehicle_request=mentioned_queries[0],
                qualification_target_vehicle=mentioned_queries[0],
            )

        # B. Busca de Estoque Contextual (pode rodar mais de uma vez no mesmo turno)
        should_search_stock = intent.is_asking_for_vehicle or intent.is_accepting_info
        if should_search_stock:
            search_queries: list[str] = []
            if mentioned_queries:
                search_queries.extend(mentioned_queries)
            elif intent.vehicle_query:
                search_queries.append(intent.vehicle_query)
            elif lead_ctx.vehicle_journey.current_focus:
                search_queries.append(lead_ctx.vehicle_journey.current_focus)
            elif lead_ctx.veiculo_interesse:
                search_queries.append(lead_ctx.veiculo_interesse)

            seen_queries: set[str] = set()
            primary_turn_query = search_queries[0] if search_queries else None

            already_presented_titles = {
                _normalize_title(v.titulo)
                for v in lead_ctx.vehicle_journey.presented_vehicles
                if v.titulo
            }
            already_presented_titles.discard("")

            perfil_parts = []
            if lead_ctx.faixa_preco:
                perfil_parts.append(f"orçamento: {lead_ctx.faixa_preco}")
            if lead_ctx.cambio:
                perfil_parts.append(f"câmbio: {lead_ctx.cambio}")
            if lead_ctx.tipo_veiculo:
                perfil_parts.append(f"tipo: {lead_ctx.tipo_veiculo}")
            perfil_cliente = " | ".join(perfil_parts) if perfil_parts else None

            for search_query in search_queries:
                normalized_query = search_query.lower().strip()
                if not normalized_query or normalized_query in seen_queries:
                    continue
                seen_queries.add(normalized_query)

                logger.info(
                    "Buscando estoque | trigger={trigger} | query={query}",
                    trigger=("vehicle_ask" if intent.is_asking_for_vehicle else "acceptance"),
                    query=search_query,
                )
                estoque_raw = consultar_estoque(
                    prompt_busca=search_query,
                    modo="discovery",
                    limite=3,
                    perfil_cliente=perfil_cliente,
                )
                filtered_payload = _filter_stock_payload(estoque_raw, search_query)
                system_injections.append(
                    _build_stock_injection(
                        filtered_payload, search_query, estoque_raw, already_presented_titles
                    )
                )

                if filtered_payload:
                    presented_vehicles = filtered_payload.get("matches") or []
                    registrar_estado(
                        session_id=session_id,
                        vehicle_focus_current=search_query if search_query == primary_turn_query else None,
                        current_vehicle_request=search_query if search_query == primary_turn_query else None,
                        qualification_target_vehicle=search_query if search_query == primary_turn_query else None,
                        vehicle_mentions=[search_query],
                        presented_vehicles=presented_vehicles,
                    )

        # C. Busca Fotos se o lead pedir (Desacoplamento Visual)
        photos_to_send = []
        if intent.is_asking_for_photos:
            lead = _get_lead(session_id)
            candidate_vehicles = [
                item.model_dump() for item in lead.vehicle_journey.last_presented_vehicles
            ] or [
                item.model_dump() for item in lead.vehicle_journey.presented_vehicles
            ]

            explicit_query = intent.vehicle_query
            if explicit_query and lead.veiculo_troca and explicit_query.lower().strip() in lead.veiculo_troca.lower().strip():
                explicit_query = None

            resolved_vehicle = resolve_vehicle_target(
                request_text=input_text,
                explicit_query=explicit_query,
                candidate_vehicles=candidate_vehicles,
            )

            if resolved_vehicle:
                photo_target = str(resolved_vehicle.get("titulo") or resolved_vehicle.get("modelo") or explicit_query or "").strip()
                registrar_estado(
                    session_id=session_id,
                    vehicle_focus_current=photo_target,
                    current_vehicle_request=photo_target,
                    photo_target_vehicle=photo_target,
                    qualification_target_vehicle=photo_target,
                    vehicle_mentions=[resolved_vehicle],
                )
                logger.info("Buscando fotos no fundo para: {query}", query=photo_target)
                photos_to_send = get_vehicle_photo_urls(photo_target, limit=10)
                if photos_to_send:
                    system_injections.append(
                        f"O SISTEMA ENVIOU {len(photos_to_send)} FOTOS DO VEÍCULO DA LOJA PARA O CLIENTE. "
                        f"VEICULO_ALVO_DAS_FOTOS={photo_target}"
                    )
                elif candidate_vehicles and len(candidate_vehicles) > 1:
                    system_injections.append(
                        "O LEAD PEDIU FOTOS DE UM VEÍCULO ESPECÍFICO, MAS O SISTEMA NÃO CONSEGUIU ENVIAR AS FOTOS. "
                        "SEJA EXPLÍCITO SOBRE A AMBIGUIDADE E CONFIRME QUAL VEÍCULO ELE QUER ANTES DE AFIRMAR QUE ENVIOU."
                    )
            elif candidate_vehicles and len(candidate_vehicles) > 1:
                system_injections.append(
                    "O LEAD PEDIU FOTOS, MAS HÁ MAIS DE UM VEÍCULO NO CONTEXTO E O ALVO NÃO FICOU CLARO. "
                    "NÃO AFIRME QUE ENVIOU FOTOS. PEÇA CONFIRMAÇÃO OBJETIVA DO MODELO CERTO."
                )
            else:
                fallback_query = explicit_query or lead.vehicle_journey.current_focus or lead.veiculo_interesse
                if fallback_query:
                    registrar_estado(
                        session_id=session_id,
                        photo_target_vehicle=fallback_query,
                        qualification_target_vehicle=fallback_query,
                    )
                    logger.info("Buscando fotos no fundo para fallback: {query}", query=fallback_query)
                    photos_to_send = get_vehicle_photo_urls(fallback_query, limit=10)
                    if photos_to_send:
                        system_injections.append(
                            f"O SISTEMA ENVIOU {len(photos_to_send)} FOTOS DO VEÍCULO DA LOJA PARA O CLIENTE. "
                            f"VEICULO_ALVO_DAS_FOTOS={fallback_query}"
                        )

        # D. Densidade e Maturidade (Prevenir fechamento prematuro)
        lead = _get_lead(session_id)
        score = lead.completeness_score()
        if score < 50 and not intent.wants_human and not visit_intent:
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

    logger.info("Resposta gerada | session={session}", session=session_id)

    return {
        "session_id": session_id,
        "reply": agent_reply,
        "attachments": photos_to_send if 'photos_to_send' in locals() and photos_to_send else None,
    }
