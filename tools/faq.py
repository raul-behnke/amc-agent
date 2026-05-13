"""
FAQ Tool — Base de Conhecimento Comercial da AMC Veículos.

Usa LLM para busca semântica na base FAQ, garantindo que variações
como "dá pra parcelar?" encontrem "financiamento".
"""

import json
import os

import yaml
from loguru import logger
from openai import OpenAI

FAQ_FILE = "data/faq.yaml"

_faq_cache: list | None = None


def _load_faq() -> list:
    """Carrega as perguntas e respostas do arquivo YAML (com cache)."""
    global _faq_cache
    if _faq_cache is not None:
        return _faq_cache

    if not os.path.exists(FAQ_FILE):
        logger.warning(f"Arquivo de FAQ não encontrado: {FAQ_FILE}")
        return []

    try:
        with open(FAQ_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            all_items = []
            for bloco in data.get("faq", {}).get("blocos", []):
                all_items.extend(bloco.get("itens", []))
            _faq_cache = all_items
            return all_items
    except Exception as e:
        logger.error(f"Erro ao ler arquivo YAML: {e}")
        return []


def _match_faq_with_llm(tema: str, faq_items: list) -> str | None:
    """Usa LLM para encontrar a FAQ mais relevante semanticamente."""
    api_key = os.getenv("OPENAI_API_KEY")
    model_id = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        logger.error("OPENAI_API_KEY não configurada para FAQ LLM.")
        return None

    # Montar o catálogo de FAQs numerado
    faq_catalog = "\n".join(
        f'{i}. P: {item.get("pergunta", "")} | R: {item.get("resposta", "")}'
        for i, item in enumerate(faq_items, 1)
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um matcher semântico de FAQ. Recebe uma pergunta do cliente e uma lista de FAQs numeradas. "
                        "Retorne APENAS o JSON: {\"match\": <número>} com o número da FAQ mais relevante. "
                        "Se nenhuma FAQ for relevante, retorne {\"match\": 0}. "
                        "Sem explicação, apenas JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": f"PERGUNTA DO CLIENTE: {tema}\n\nFAQs DISPONÍVEIS:\n{faq_catalog}",
                },
            ],
        )
        raw = response.choices[0].message.content or ""
        # Extrair JSON
        data = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        match_idx = data.get("match", 0)
        if match_idx and 1 <= match_idx <= len(faq_items):
            matched = faq_items[match_idx - 1]
            logger.info(
                "FAQ match LLM | pergunta={p} | match_idx={idx}",
                p=matched.get("pergunta", "")[:50],
                idx=match_idx,
            )
            return matched.get("resposta", "")
        return None
    except Exception as exc:
        logger.warning("Fallback FAQ sem LLM | err={err}", err=str(exc))
        return None


def consultar_faq(tema: str) -> str:
    """
    Consulta informações oficiais sobre processos da AMC Veículos.
    Utilize sempre que o cliente tiver dúvidas sobre financiamento, troca, garantia, etc.

    Args:
        tema: O assunto ou pergunta da dúvida (ex: 'financiamento', 'troca', 'garantia').
    """
    logger.info("Consultando FAQ | tema={t}", t=tema)

    faq_items = _load_faq()
    if not faq_items:
        return "Base de conhecimentos indisponível."

    # Busca semântica via LLM
    result = _match_faq_with_llm(tema, faq_items)
    if result:
        return result

    return "Informação não encontrada na base de conhecimentos."
