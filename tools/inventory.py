"""
Inventory Tool — Consulta executora de estoque da AMC Veículos.
"""

import json
import os
import re
from typing import Any

from loguru import logger
from openai import OpenAI

from services.ghl import fetch_inventory_sync


CATEGORY_KEYWORDS = {
    "hatch": {"hb20", "gol", "palio", "ka", "sandero", "onix", "c3", "fiat 500", "500"},
    "sedan": {"fluence", "sentra", "cruze", "versa", "logan", "civic", "corolla", "clio sedan"},
    "suv": {"renegade", "ecosport", "tracker", "cactus", "creta", "edge", "duster", "captur"},
    "picape": {"s10", "strada", "saveiro", "ranger", "hilux", "amarok", "montana"},
    "pickup": {"s10", "strada", "saveiro", "ranger", "hilux", "amarok", "montana"},
    "compacto": {"hb20", "gol", "palio", "ka", "fiat 500", "500", "c3"},
}

GENERIC_INVENTORY_REQUEST_TOKENS = {
    "tem",
    "algum",
    "alguma",
    "mais",
    "novo",
    "nova",
    "novo?",
    "nova?",
    "acima",
    "abaixo",
    "ate",
    "até",
    "de",
    "ano",
}

PREFERENCE_MODES = {"newer", "cheaper", "automatic", "manual"}
LLM_MODE_VALUES = {"single", "alternatives", "confirm", "vehicle_info"}


def _format_price(price: int) -> str:
    return f"R$ {price:,.0f}".replace(",", ".")


def _format_km(km: int) -> str:
    if km >= 999999:
        return "Consultar"
    return f"{km:,.0f} km".replace(",", ".")





def _match_vehicle_flexible(vehicle: dict[str, Any], search_term: str) -> bool:
    if not search_term:
        return True

    def normalize(t: str) -> str:
        return re.sub(r"[^a-z0-9]", "", t.lower())

    term = normalize(search_term)
    v_marca = normalize(str(vehicle.get("marca", "")))
    v_modelo = normalize(str(vehicle.get("modelo", "")))
    v_titulo = normalize(str(vehicle.get("titulo", "")))

    if term in v_titulo or term in v_modelo or term in v_marca:
        return True

    words = set(re.findall(r"\w+", term))
    ignore = {"flex", "12v", "16v", "plus", "comf", "comfort", "style", "1", "0", "6", "8", "2"}
    important_words = words - ignore
    if not important_words:
        return False

    for word in important_words:
        if len(word) < 2:
            continue
        v_ano = str(vehicle.get("ano", ""))
        if (re.search(rf"\b{re.escape(word)}\b", v_titulo) or 
            re.search(rf"\b{re.escape(word)}\b", v_modelo) or
            word == v_ano):
            return True
    return False


def _normalize_price_text(text: str) -> str:
    return (
        text.lower()
        .replace("r$", "")
        .replace(".", "")
        .replace(",", "")
        .replace(" mil", "000")
        .replace("mil", "000")
        .strip()
    )


def _parse_price_filters(faixa_preco: str | None) -> tuple[int | None, int | None]:
    if not faixa_preco:
        return None, None

    raw = _normalize_price_text(faixa_preco)
    numbers = [int(n) for n in re.findall(r"\d{2,6}", raw)]
    if not numbers:
        return None, None

    if any(token in raw for token in ("até", "ate", "abaixo", "menos de", "no máximo", "maximo")):
        return None, numbers[0]
    if any(token in raw for token in ("acima", "a partir", "mais de")):
        return numbers[0], None
    if len(numbers) >= 2:
        low, high = sorted(numbers[:2])
        return low, high
    return None, numbers[0]


def _parse_year_filter(ano_minimo: int | None) -> int | None:
    return ano_minimo if ano_minimo and ano_minimo > 1900 else None


def _vehicle_matches_category(vehicle: dict[str, Any], tipo_veiculo: str) -> bool:
    tipo = tipo_veiculo.lower().strip()
    title = f"{vehicle.get('marca', '')} {vehicle.get('modelo', '')} {vehicle.get('titulo', '')}".lower()
    keywords = CATEGORY_KEYWORDS.get(tipo, {tipo})
    return any(keyword in title for keyword in keywords)


def _normalize_vehicle_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def _same_vehicle_family(vehicle: dict[str, Any], reference_vehicle: dict[str, Any]) -> bool:
    reference_model = _normalize_vehicle_text(str(reference_vehicle.get("modelo", "")))
    reference_brand = _normalize_vehicle_text(str(reference_vehicle.get("marca", "")))
    vehicle_model = _normalize_vehicle_text(str(vehicle.get("modelo", "")))
    vehicle_brand = _normalize_vehicle_text(str(vehicle.get("marca", "")))
    vehicle_title = _normalize_vehicle_text(str(vehicle.get("titulo", "")))

    if reference_model and vehicle_model and reference_model == vehicle_model:
        if reference_brand and vehicle_brand:
            return reference_brand == vehicle_brand
        return True

    if reference_model and reference_model in vehicle_title:
        if reference_brand and vehicle_brand:
            return reference_brand == vehicle_brand
        return True

    return False


def _filter_inventory(
    inventory: list[dict[str, Any]],
    search_term: str,
    faixa_preco: str | None,
    tipo_veiculo: str | None,
    ano_minimo: int | None = None,
    cambio: str | None = None,
    reference_vehicle: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    min_price, max_price = _parse_price_filters(faixa_preco)
    min_year = _parse_year_filter(ano_minimo)
    filtered = inventory

    if tipo_veiculo:
        filtered = [v for v in filtered if _vehicle_matches_category(v, tipo_veiculo)]
    if reference_vehicle:
        family_filtered = [v for v in filtered if _same_vehicle_family(v, reference_vehicle)]
        if family_filtered:
            filtered = family_filtered
    if min_year is not None:
        filtered = [v for v in filtered if int(v.get("ano", 0) or 0) >= min_year]
    if min_price is not None:
        filtered = [v for v in filtered if int(v.get("preco", 0) or 0) >= min_price]
    if max_price is not None:
        filtered = [v for v in filtered if int(v.get("preco", 0) or 0) <= max_price]
    if cambio:
        filtered = [v for v in filtered if str(v.get("cambio", "")).lower() == cambio.lower()]
    if search_term:
        filtered = [v for v in filtered if _match_vehicle_flexible(v, search_term)]

    return filtered


def _score_vehicle_match(vehicle: dict[str, Any], search_term: str) -> tuple[int, int]:
    # Inclui o ano no texto de busca para garantir que "HB20 2015" pontue mais no 2015 que no 2022
    text_to_match = f"{vehicle.get('titulo', '')} {vehicle.get('ano', '')}".lower()
    words = set(re.findall(r"\w+", search_term.lower()))
    overlap = len(words & set(re.findall(r"\w+", text_to_match)))
    price = int(vehicle.get("preco", 0) or 0)
    return overlap, price


def _serialize_vehicle(vehicle: dict[str, Any]) -> dict[str, Any]:
    price = int(vehicle.get("preco", 0) or 0)
    km = int(vehicle.get("quilometragem", 0) or 0)
    
    return {
        "vehicle_key": "|".join(
            str(vehicle.get(field, "")).strip().lower()
            for field in ("marca", "modelo", "titulo", "ano", "quilometragem", "preco", "cambio")
        ),
        "titulo": vehicle.get("titulo", "Veículo"),
        "marca": vehicle.get("marca"),
        "modelo": vehicle.get("modelo"),
        "ano": vehicle.get("ano"),
        "preco": price,
        "preco_formatado": _format_price(price) if price > 0 else "Sob consulta",
        "quilometragem": km,
        "quilometragem_formatada": _format_km(km) if km > 0 else "Consultar",
        "cambio": vehicle.get("cambio"),
        "tem_fotos": len(vehicle.get("imagens") or []) > 0,
        "imagens_count": len(vehicle.get("imagens") or []),
        "destaque": bool(vehicle.get("destaque")),
    }


def _vehicle_identity_key(vehicle: dict[str, Any]) -> str:
    return "|".join(
        str(vehicle.get(field, "")).strip().lower()
        for field in ("marca", "modelo", "titulo", "ano", "quilometragem", "preco", "cambio")
    )


def _dedupe_vehicles(vehicles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for vehicle in vehicles:
        key = _vehicle_identity_key(vehicle)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(vehicle)
    return deduped


def _normalize_ignored_vehicle_keys(
    veiculos_ignorados: list[Any] | None = None,
    reference_vehicle: dict[str, Any] | None = None,
    mode: str | None = None,
    prefer: str | None = None,
) -> set[str]:
    ignored_keys: set[str] = set()
    has_explicit_ignored = bool(veiculos_ignorados)

    for item in veiculos_ignorados or []:
        if item is None:
            continue
        if isinstance(item, dict):
            key = str(item.get("vehicle_key") or _vehicle_identity_key(item)).strip().lower()
        else:
            key = str(item).strip().lower()
        if key:
            ignored_keys.add(key)

    if mode == "alternatives" and reference_vehicle and (prefer or has_explicit_ignored):
        reference_key = _vehicle_identity_key(reference_vehicle)
        if reference_key:
            ignored_keys.add(reference_key)

    return ignored_keys


def _exclude_ignored_vehicles(
    vehicles: list[dict[str, Any]],
    ignored_keys: set[str],
) -> list[dict[str, Any]]:
    if not ignored_keys:
        return vehicles
    return [
        vehicle
        for vehicle in vehicles
        if _vehicle_identity_key(vehicle) not in ignored_keys
    ]


def _resolve_reference_vehicle(
    inventory: list[dict[str, Any]],
    reference_vehicle: str | None,
) -> dict[str, Any] | None:
    if not reference_vehicle or not reference_vehicle.strip():
        return None

    matches = [item for item in inventory if _match_vehicle_flexible(item, reference_vehicle)]
    if not matches:
        return None

    matches.sort(key=lambda vehicle: _score_vehicle_match(vehicle, reference_vehicle), reverse=True)
    return matches[0]


def _sort_inventory_results(
    vehicles: list[dict[str, Any]],
    search_term: str,
    prefer: str | None = None,
    reference_vehicle: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    normalized_prefer = (prefer or "").lower().strip()
    if normalized_prefer == "newer":
        return sorted(
            vehicles,
            key=lambda x: (
                int(x.get("ano", 0) or 0),
                -(int(x.get("preco", 0) or 0)),
                -int(x.get("quilometragem", 0) or 0),
            ),
            reverse=True,
        )
    if normalized_prefer == "cheaper":
        return sorted(
            vehicles,
            key=lambda x: (
                int(x.get("preco", 0) or 0),
                -(int(x.get("ano", 0) or 0)),
            ),
            reverse=False,
        )

    if normalized_prefer in {"automatic", "manual"}:
        preferred_keyword = "autom" if normalized_prefer == "automatic" else "mec"
        return sorted(
            vehicles,
            key=lambda x: (
                preferred_keyword in str(x.get("cambio", "")).lower(),
                int(x.get("ano", 0) or 0),
                -(int(x.get("preco", 0) or 0)),
            ),
            reverse=True,
        )

    if reference_vehicle:
        return sorted(
            vehicles,
            key=lambda x: (
                _same_vehicle_family(x, reference_vehicle),
                len(set(re.findall(r"\w+", search_term.lower())) & set(re.findall(r"\w+", x.get("titulo", "").lower())))
                if search_term else 0,
                -(int(x.get("preco", 0) or 0)),
            ),
            reverse=True,
        )

    return sorted(
        vehicles,
        key=lambda x: (
            len(set(re.findall(r"\w+", search_term.lower())) & set(re.findall(r"\w+", x.get("titulo", "").lower())))
            if search_term else 0,
            -(int(x.get("preco", 0) or 0)),
        ),
        reverse=True,
    )


def _find_best_vehicle_match(vehicle_query: str) -> dict[str, Any] | None:
    if not vehicle_query.strip():
        return None

    try:
        inventory = fetch_inventory_sync()
    except Exception as exc:
        logger.error("Erro ao buscar estoque para resolver veículo: {err}", err=str(exc))
        return None

    matches = [v for v in inventory if _match_vehicle_flexible(v, vehicle_query)]
    if not matches:
        return None

    matches.sort(key=lambda vehicle: _score_vehicle_match(vehicle, vehicle_query), reverse=True)
    return matches[0]


def _build_card_payload(
    vehicles: list[dict[str, Any]],
    photo_limit: int,
) -> list[dict[str, Any]]:
    return [_serialize_vehicle({**vehicle, "imagens": (vehicle.get("imagens") or [])[:photo_limit]}) for vehicle in vehicles]


def _normalize_mode(mode: str | None) -> str | None:
    if not mode:
        return None
    value = mode.lower().strip()
    return value if value in LLM_MODE_VALUES else None


def _build_search_brief(
    prompt_busca: str | None = None,
    prompt_contexto: str | None = None,
    perfil_cliente: str | None = None,
    vehicle_focus: str | None = None,
    reference_vehicle: str | None = None,
    modelo: str | None = None,
    marca: str | None = None,
    faixa_preco: str | None = None,
    tipo_veiculo: str | None = None,
    ano_minimo: int | None = None,
    cambio: str | None = None,
    prefer: str | None = None,
    modo: str | None = None,
) -> str:
    parts = [
        f"MODO={modo or 'auto'}",
        f"PROMPT_BUSCA={prompt_busca or ''}",
        f"PROMPT_CONTEXTO={prompt_contexto or ''}",
        f"PERFIL_CLIENTE={perfil_cliente or ''}",
        f"VEHICLE_FOCUS={vehicle_focus or ''}",
        f"REFERENCE_VEHICLE={reference_vehicle or ''}",
        f"MODELO={modelo or ''}",
        f"MARCA={marca or ''}",
        f"FAIXA_PRECO={faixa_preco or ''}",
        f"TIPO_VEICULO={tipo_veiculo or ''}",
        f"ANO_MINIMO={ano_minimo or ''}",
        f"CAMBIO={cambio or ''}",
        f"PREFER={prefer or ''}",
    ]
    return "\n".join(part for part in parts if part is not None)


def _inventory_retrieval_pool(
    inventory: list[dict[str, Any]],
    search_brief: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    tokens = set(re.findall(r"\w+", search_brief.lower()))
    stopwords = {
        "mdo",
        "modo",
        "prompt",
        "busca",
        "contexto",
        "perfil",
        "cliente",
        "vehicle",
        "focus",
        "reference",
        "veiculo",
        "veículo",
        "alternativas",
        "foto",
        "fotos",
        "estoque",
        "modelo",
        "marca",
        "ano",
        "preco",
        "preço",
        "cambio",
    }
    meaningful = {token for token in tokens if token not in stopwords and len(token) > 1}
    
    # Sprint 2: Expansão Semântica Básica (Cross-selling e intenções abstratas)
    search_lower = search_brief.lower()
    if any(k in search_lower for k in ("uber", "app", "aplicativo", "economico", "econômico")):
        meaningful.update({"sedan", "hatch", "onix", "prisma", "logan", "hb20", "ka", "argo", "kwid", "mobi", "voyage"})
    if any(k in search_lower for k in ("alto", "espaçoso", "familia", "família", "suv")):
        meaningful.update({"suv", "jeep", "compass", "renegade", "creta", "kicks", "tracker", "hrv", "corolla cross", "nivus", "t-cross"})
    if any(k in search_lower for k in ("barato", "primeiro carro", "custo beneficio")):
        meaningful.update({"hatch", "celta", "palio", "uno", "gol", "fox", "kwid", "mobi"})
    if any(k in search_lower for k in ("picape", "caminhonete", "carga")):
        meaningful.update({"picape", "hilux", "s10", "ranger", "amarok", "toro", "strada", "saveiro"})

    scored: list[tuple[tuple[int, int, int], dict[str, Any]]] = []

    for vehicle in inventory:
        serialized = _serialize_vehicle(vehicle)
        title = str(serialized.get("titulo", "")).lower()
        body = " ".join(
            filter(
                None,
                [
                    str(serialized.get("titulo", "")),
                    str(serialized.get("marca", "")),
                    str(serialized.get("modelo", "")),
                    str(serialized.get("ano", "")),
                    str(serialized.get("cambio", "")),
                    str(serialized.get("preco_formatado", "")),
                    str(serialized.get("quilometragem_formatada", "")),
                ],
            )
        ).lower()
        overlap = len(meaningful & set(re.findall(r"\w+", body)))
        exact = 1 if any(token and token in title for token in meaningful) else 0
        score = (overlap, exact, -int(serialized.get("preco", 0) or 0))
        scored.append((score, vehicle))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [vehicle for _, vehicle in scored[:limit]]


def _extract_json_payload(raw: str) -> dict[str, Any] | None:
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        raw = re.sub(r"```$", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def _rank_inventory_with_llm(
    search_brief: str,
    candidates: list[dict[str, Any]],
    limite: int,
    forced_mode: str | None = None,
) -> dict[str, Any] | None:
    if os.getenv("INVENTORY_USE_LLM", "1").lower() not in {"1", "true", "yes", "on"}:
        return None

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    if not candidates:
        return None

    model_id = os.getenv("INVENTORY_RANKER_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
    client = OpenAI(api_key=api_key)

    payload_candidates = []
    for index, vehicle in enumerate(candidates, start=1):
        serialized = _serialize_vehicle(vehicle)
        payload_candidates.append(
            {
                "index": index,
                "vehicle_key": serialized["vehicle_key"],
                "titulo": serialized["titulo"],
                "marca": serialized["marca"],
                "modelo": serialized["modelo"],
                "ano": serialized["ano"],
                "preco": serialized["preco"],
                "quilometragem": serialized["quilometragem"],
                "cambio": serialized["cambio"],
                "imagens_count": serialized["imagens_count"],
            }
        )

    system_prompt = (
        "Você é um curador de estoque automotivo. "
        "Escolha as melhores opções com base no briefing e no perfil do cliente. "
        "Retorne apenas JSON válido, sem markdown."
    )
    user_prompt = {
        "briefing": search_brief,
        "forced_mode": forced_mode,
        "limit": limite,
        "candidates": payload_candidates,
        "schema": {
            "response_mode": "single|alternatives|confirm|vehicle_info",
            "selected_vehicle_keys": ["vehicle_key"],
            "alternative_reasoning": {"vehicle_key": "string curta"},
            "headline": "string curta em PT-BR",
            "summary": "string curta em PT-BR",
        },
    }

    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
            ],
        )
        raw = response.choices[0].message.content or ""
        data = _extract_json_payload(raw)
        if isinstance(data, dict):
            return data
    except Exception as exc:
        logger.warning("Fallback determinístico no ranking do estoque | err={err}", err=str(exc))

    return None


def infer_vehicle_interest_from_text(text: str) -> str | None:
    lowered = text.lower()
    if any(token in lowered for token in ("tenho um", "tenho uma", "meu ", "minha ", "troca", "dar na troca")):
        return None

    words = set(re.findall(r"\w+", lowered))
    generic_words = {word for word in words if word in GENERIC_INVENTORY_REQUEST_TOKENS or word.isdigit()}
    if words and len(generic_words) == len(words):
        return None

    match = _find_best_vehicle_match(text)
    if not match:
        return None
    return str(match.get("titulo", "")).strip() or None


def resolve_vehicle_for_photo_request(vehicle_query: str, request_text: str = "") -> dict[str, Any] | None:
    if not vehicle_query.strip():
        return None

    try:
        inventory = fetch_inventory_sync()
    except Exception as exc:
        logger.error("Erro ao buscar estoque para fotos: {err}", err=str(exc))
        return None

    matches = [v for v in inventory if _match_vehicle_flexible(v, vehicle_query)]
    if not matches:
        return None

    # Tenta extrair ano da query ou do texto do request
    year_match = re.search(r"\b(19|20)\d{2}\b", f"{vehicle_query} {request_text}")
    if year_match:
        requested_year = year_match.group(0)
        year_filtered = [v for v in matches if str(v.get("ano", "")) == requested_year]
        if year_filtered:
            matches = year_filtered

    matches.sort(key=lambda vehicle: _score_vehicle_match(vehicle, vehicle_query), reverse=True)
    return matches[0]


def get_vehicle_photo_urls(vehicle_query: str, limit: int = 10) -> list[str]:
    if not vehicle_query.strip():
        return []

    match = resolve_vehicle_for_photo_request(vehicle_query)
    if not match:
        return []

    imagens = match.get("imagens", []) or []
    return [url for url in imagens[:limit] if isinstance(url, str) and url.startswith("http")]





def consultar_estoque(
    modelo: str | None = None,
    marca: str | None = None,
    faixa_preco: str | None = None,
    tipo_veiculo: str | None = None,
    ano_minimo: int | None = None,
    cambio: str | None = None,
    reference_vehicle: str | None = None,
    prefer: str | None = None,
    prompt_busca: str | None = None,
    prompt_contexto: str | None = None,
    prompt_apresentacao: str | None = None,
    perfil_cliente: str | None = None,
    vehicle_focus: str | None = None,
    modo: str | None = None,
    limite: int = 5,
    veiculos_ignorados: list[Any] | None = None,
) -> str:
    """
    Consulta o estoque real da AMC Veículos e devolve resultado estruturado.
    """
    normalized_prefer = (prefer or "").lower().strip() or None
    normalized_mode = _normalize_mode(modo)
    if normalized_prefer and normalized_prefer not in PREFERENCE_MODES:
        return json.dumps({"ok": False, "error": "prefer_invalido"}, ensure_ascii=False)

    if normalized_prefer == "automatic" and not cambio:
        cambio = "Automático"
    elif normalized_prefer == "manual" and not cambio:
        cambio = "Mecânico"

    search_brief = _build_search_brief(
        prompt_busca=prompt_busca,
        prompt_contexto=prompt_contexto,
        perfil_cliente=perfil_cliente,
        vehicle_focus=vehicle_focus,
        reference_vehicle=reference_vehicle,
        modelo=modelo,
        marca=marca,
        faixa_preco=faixa_preco,
        tipo_veiculo=tipo_veiculo,
        ano_minimo=ano_minimo,
        cambio=cambio,
        prefer=normalized_prefer,
        modo=normalized_mode,
    )
    search_term = " ".join(
        part
        for part in (
            prompt_busca,
            prompt_contexto,
            perfil_cliente,
            vehicle_focus,
            modelo,
            marca,
            reference_vehicle,
        )
        if part
    ).strip()

    logger.info(
        "Consultando estoque | brief={brief} | faixa={f} | tipo={tipo} | ano_minimo={ano} | reference={ref} | prefer={prefer} | modo={modo}",
        brief=(search_brief[:180] if search_brief else ""),
        f=faixa_preco,
        tipo=tipo_veiculo,
        ano=ano_minimo,
        ref=reference_vehicle,
        prefer=normalized_prefer,
        modo=normalized_mode,
    )

    has_query_context = any(
        [
            prompt_busca,
            prompt_contexto,
            prompt_apresentacao,
            perfil_cliente,
            vehicle_focus,
            modelo,
            marca,
            faixa_preco,
            tipo_veiculo,
            ano_minimo is not None,
            cambio,
            reference_vehicle,
            normalized_prefer,
        ]
    )
    if not has_query_context:
        return json.dumps({"ok": False, "error": "ERRO_TOOL_ESTOQUE: informe um prompt ou filtros de busca."}, ensure_ascii=False)

    try:
        inventory = fetch_inventory_sync()
    except Exception as exc:
        logger.error("Erro GHL: {err}", err=str(exc))
        return json.dumps({"ok": False, "error": "estoque_indisponivel"}, ensure_ascii=False)

    resolved_reference = _resolve_reference_vehicle(inventory, reference_vehicle)
    if not resolved_reference and vehicle_focus:
        resolved_reference = _resolve_reference_vehicle(inventory, vehicle_focus)
    ignored_vehicle_keys = _normalize_ignored_vehicle_keys(
        veiculos_ignorados=veiculos_ignorados,
        reference_vehicle=resolved_reference,
        mode=normalized_mode,
        prefer=normalized_prefer,
    )
    if resolved_reference and not search_term:
        reference_model = str(resolved_reference.get("modelo", "")).strip()
        reference_brand = str(resolved_reference.get("marca", "")).strip()
        search_term = " ".join(part for part in (reference_brand, reference_model) if part).strip()

    hard_matches = _filter_inventory(
        inventory=inventory,
        search_term=search_term if not prompt_busca else "",
        faixa_preco=faixa_preco,
        tipo_veiculo=tipo_veiculo,
        ano_minimo=ano_minimo,
        cambio=cambio,
        reference_vehicle=resolved_reference,
    )
    hard_matches = _sort_inventory_results(
        hard_matches,
        search_term=search_term,
        prefer=normalized_prefer,
        reference_vehicle=resolved_reference,
    )
    hard_matches = _dedupe_vehicles(hard_matches)
    hard_matches = _exclude_ignored_vehicles(hard_matches, ignored_vehicle_keys)

    retrieval_query = search_brief or search_term or modelo or marca or reference_vehicle or ""
    retrieval_pool = _inventory_retrieval_pool(
        inventory=inventory,
        search_brief=retrieval_query,
        limit=max(limite * 4, 20),
    )
    retrieval_pool = _exclude_ignored_vehicles(_dedupe_vehicles(retrieval_pool), ignored_vehicle_keys)

    candidate_source = retrieval_pool if retrieval_query else hard_matches
    if hard_matches and not prompt_busca and not prompt_contexto and not perfil_cliente and not vehicle_focus and not prompt_apresentacao:
        candidate_source = hard_matches

    llm_selection = _rank_inventory_with_llm(
        search_brief=search_brief or retrieval_query,
        candidates=candidate_source or hard_matches,
        limite=limite,
        forced_mode=normalized_mode,
    )

    selected_keys: list[str] = []
    response_mode = normalized_mode
    headline = None
    summary = None
    reasons: dict[str, str] = {}

    if isinstance(llm_selection, dict):
        response_mode = _normalize_mode(str(llm_selection.get("response_mode") or normalized_mode)) or response_mode
        headline = llm_selection.get("headline")
        summary = llm_selection.get("summary")
        selected_keys = [
            str(key).strip().lower()
            for key in (llm_selection.get("selected_vehicle_keys") or [])
            if str(key).strip()
        ]
        reasons = {
            str(key).strip().lower(): str(value)
            for key, value in (llm_selection.get("alternative_reasoning") or {}).items()
            if str(key).strip()
        }

    if normalized_mode:
        response_mode = normalized_mode

    if response_mode in {"single", "confirm", "vehicle_info"}:
        selected_keys = selected_keys[:1]

    if not selected_keys:
        selected_keys = [str(_serialize_vehicle(v)["vehicle_key"]).strip().lower() for v in (candidate_source or hard_matches)[:limite]]

    if response_mode in {"single", "confirm", "vehicle_info"}:
        selected_keys = selected_keys[:1]

    selected_map: dict[str, dict[str, Any]] = {}
    for vehicle in candidate_source or hard_matches:
        serialized = _serialize_vehicle(vehicle)
        selected_map[serialized["vehicle_key"]] = serialized

    ordered_selected: list[dict[str, Any]] = []
    for key in selected_keys:
        serialized = selected_map.get(key)
        if serialized and key not in {item["vehicle_key"] for item in ordered_selected}:
            ordered_selected.append(serialized)

    if not ordered_selected:
        ordered_selected = [_serialize_vehicle(v) for v in (candidate_source or hard_matches)[:limite]]

    response_mode = response_mode or ("single" if len(ordered_selected) == 1 else "alternatives")
    response_mode = response_mode if response_mode in LLM_MODE_VALUES else ("single" if len(ordered_selected) == 1 else "alternatives")

    if response_mode == "alternatives":
        target_count = len(candidate_source or hard_matches or [])
        if target_count and len(ordered_selected) < target_count:
            selected_keys_set = {item["vehicle_key"] for item in ordered_selected}
            for vehicle in candidate_source or hard_matches:
                serialized = _serialize_vehicle(vehicle)
                if serialized["vehicle_key"] in selected_keys_set:
                    continue
                ordered_selected.append(serialized)
                selected_keys_set.add(serialized["vehicle_key"])
                if len(ordered_selected) >= target_count:
                    break

    photo_limit = 10 if response_mode in {"single", "confirm", "vehicle_info"} else 2
    candidate_pool = _build_card_payload(
        [
            {
                **vehicle,
                "imagens": (vehicle.get("imagens") or [])[:photo_limit],
            }
            for vehicle in ordered_selected
        ],
        photo_limit=photo_limit,
    )
    serialized_matches = candidate_pool or _build_card_payload(
        [
            {
                **vehicle,
                "imagens": (vehicle.get("imagens") or [])[:photo_limit],
            }
            for vehicle in (candidate_source or hard_matches)[:limite]
        ],
        photo_limit=photo_limit,
    )

    fallback_matches: list[dict[str, Any]] = []
    if not serialized_matches:
        fallback_source = _dedupe_vehicles(hard_matches or inventory)
        fallback_matches = _build_card_payload(fallback_source[:limite], photo_limit=2)

    selected_pool = serialized_matches if serialized_matches else fallback_matches
    result_mode = response_mode if selected_pool else "empty"
    primary_vehicle = selected_pool[0] if selected_pool else None

    if not fallback_matches:
        fallback_source = _dedupe_vehicles(hard_matches or inventory)
        fallback_matches = _build_card_payload(fallback_source[:limite], photo_limit=2)

    return json.dumps(
        {
            "ok": True,
            "query": {
                "modelo": modelo,
                "marca": marca,
                "faixa_preco": faixa_preco,
                "tipo_veiculo": tipo_veiculo,
                "ano_minimo": ano_minimo,
                "cambio": cambio,
                "reference_vehicle": reference_vehicle,
                "prefer": normalized_prefer,
                "prompt_busca": prompt_busca,
                "prompt_contexto": prompt_contexto,
                "prompt_apresentacao": prompt_apresentacao,
                "perfil_cliente": perfil_cliente,
                "vehicle_focus": vehicle_focus,
                "modo": normalized_mode,
                "limite": limite,
                "veiculos_ignorados": veiculos_ignorados,
            },
            "count": len(serialized_matches),
            "matches": serialized_matches,
            "candidate_pool": selected_pool,
            "selected_vehicle": primary_vehicle,
            "fallback_used": not bool(serialized_matches),
            "fallback_matches": fallback_matches,
            "resolved_reference_vehicle": _serialize_vehicle(resolved_reference) if resolved_reference else None,
            "response_mode": result_mode,
            "search_brief": search_brief,
            "llm_selection": {
                "headline": headline,
                "summary": summary,
                "reasoning": reasons,
            },
            "presentation": {
                "mode": result_mode,
                "cards": selected_pool,
                "fallback_cards": fallback_matches,
                "selection_hints": {
                    "prefer": normalized_prefer,
                    "search_term": search_term,
                    "reference_vehicle": reference_vehicle,
                    "search_brief": search_brief,
                    "filter_summary": {
                        "faixa_preco": faixa_preco,
                        "tipo_veiculo": tipo_veiculo,
                        "ano_minimo": ano_minimo,
                        "cambio": cambio,
                    },
                },
            },
        },
        ensure_ascii=False,
    )
