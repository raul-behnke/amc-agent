"""
Inventory Search Intent Classifier

Classifica a intenção de busca de veículos do lead.
Determina se o lead quer:
- Detalhes do veículo atual
- Voltar a um veículo apresentado
- Outras opções do mesmo modelo
- Outras opções da categoria
- Opções por faixa de preço
- Mudar preferência (mais novo, menos km)
- Busca aberta
"""

import os
from typing import Optional
from pydantic import BaseModel, Field

# pyrefly: ignore [missing-import]
from agno.agent import Agent
# pyrefly: ignore [missing-import]
from agno.models.openai import OpenAIChat


class InventorySearchIntent(BaseModel):
    """Contrato de intenção de busca de veículos."""

    search_intent: str = Field(
        ...,
        description="Tipo de intenção de busca. Valores: 'same_vehicle_info', 'return_to_presented_vehicle', 'same_model_options', 'category_expansion', 'budget_expansion', 'preference_shift', 'general_recommendation'.",
    )
    scope: str = Field(
        ...,
        description="Escopo da busca. Valores: 'current_vehicle', 'presented_vehicle', 'same_model', 'category', 'price_range', 'preference', 'open_recommendation'.",
    )
    modo: str = Field(
        ...,
        description="Modo de busca. Valores: 'vehicle_info' ou 'alternatives'.",
    )
    use_vehicle_focus_as_filter: bool = Field(
        ...,
        description="Se deve usar o veículo em foco como filtro restritivo.",
    )
    exclude_presented: bool = Field(
        ...,
        description="Se deve excluir veículos já apresentados da busca (apenas contexto para o LLM).",
    )
    context_vehicle: Optional[str] = Field(
        None,
        description="Veículo específico de contexto (para return_to_presented_vehicle).",
    )
    preference: Optional[str] = Field(
        None,
        description="Preferência específica (para preference_shift). Valores: 'newer', 'lower_km', 'cheaper', etc.",
    )
    confidence: float = Field(
        ...,
        description="Confiança na classificação (0-1).",
    )


INTENT_CLASSIFIER_INSTRUCTIONS = """
Você é um classificador de intenção de busca de veículos em uma concessionária.

Seu papel: analisar a mensagem do lead e o contexto para classificar a intenção comercial da busca.

CONTEXTO DISPONÍVEL:
- lead_message: Mensagem atual do lead
- presented_vehicles: Lista de veículos já apresentados ao lead
- context_vehicle: Veículo em foco na conversa (se houver)
- vehicle_focus_reason: Razão do veículo estar em foco (lead_liked_vehicle, etc.)

TIPOS DE INTENÇÃO DE BUSCA:

1. SAME_VEHICLE_INFO
- Lead quer detalhes do veículo atual/context_vehicle
- Exemplos: "tem fotos?", "qual a quilometragem?", "está disponível?", "qual o valor?"
- Comportamento: scope=current_vehicle, modo=vehicle_info, use_vehicle_focus_as_filter=True, exclude_presented=False

2. RETURN_TO_PRESENTED_VEHICLE
- Lead faz referência EXPLÍCITA a um veículo apresentado no histórico
- Exemplos: "esse automático de 50 mil", "aquele sedan", "o carro que você me mostrou", "volta pra mim aquele Sentra"
- Comportamento: scope=presented_vehicle, modo=vehicle_info, use_vehicle_focus_as_filter=True, exclude_presented=False, context_vehicle=veículo_referenciado

3. SAME_MODEL_OPTIONS
- Lead quer outras opções do MESMO modelo
- Exemplos: "tem outro Sentra?", "tem esse modelo mais novo?", "tem outro desse automático?"
- Comportamento: scope=same_model, modo=alternatives, use_vehicle_focus_as_filter=True, exclude_presented=True (diferentes versões/anos)

4. CATEGORY_EXPANSION
- Lead quer opções mais amplas de uma CATEGORIA
- Exemplos: "tem mais alguma opção de sedan?", "tem outro sedã?", "quais SUVs vocês têm?", "tem mais hatch automático?"
- Comportamento: scope=category, modo=alternatives, use_vehicle_focus_as_filter=False, exclude_presented=True (evitar repetições, priorizar diversidade)

5. BUDGET_EXPANSION
- Lead quer opções com base em PREÇO
- Exemplos: "tem algo mais barato?", "tem até 50 mil?", "tem alguma opção nessa faixa?", "tem algo um pouco acima?"
- Comportamento: scope=price_range, modo=alternatives, use_vehicle_focus_as_filter=False, exclude_presented=True

6. PREFERENCE_SHIFT
- Lead muda ou adiciona uma preferência específica
- Exemplos: "tem algum mais novo?", "tem com menos km?", "tem automático?", "tem manual?", "tem flex?"
- Comportamento: scope=preference, modo=alternatives, use_vehicle_focus_as_filter=False, exclude_presented=True, preference=específico

7. GENERAL_RECOMMENDATION
- Lead faz busca aberta sem veículo específico
- Exemplos: "queria um carro bom pra família", "quero algo econômico", "quero um carro pra Uber", "o que vocês têm até 60 mil?"
- Comportamento: scope=open_recommendation, modo=alternatives, use_vehicle_focus_as_filter=False, exclude_presented=False (primeira busca)

REGRAS CRÍTICAS:

REABERTURA DE VEÍCULO APRESENTADO:
- Se mensagem contém pronomes demonstrativos + característica específica: "esse [X]", "aquele [X]", "o [X] que você me mostrou"
- Verifique se existe veículo em presented_vehicles com essa característica
- Se SIM → search_intent=return_to_presented_vehicle, context_vehicle=veículo_encontrado
- Exemplo: "esse automático de 50 mil" + presented_vehicles=[Sentra 2014 (aut, 55k)] → return_to_presented_vehicle

DISTINÇÃO ENTRE MODELO E CATEGORIA:
- "Outro Sentra" → same_model_options (mesmo modelo)
- "Outro sedã" → category_expansion (categoria ampla)
- "Mais opções" sozinho → depender do contexto, mas geralmente category_expansion

TERMOS DE EXPANSÃO:
- "mais alguma opção", "outra opção", "tem mais", "outro modelo", "alguma outra"
- Indica pedido de NOVAS alternativas
- Se categoria mencionada (sedã, SUV, hatch) → category_expansion
- Se preço mencionado → budget_expansion
- Se preferência mencionada → preference_shift

EXCLUSÃO DE APRESENTADOS:
- exclude_presented=True quando lead pede NOVAS alternativas (mesmo modelo, categoria, preço, preferência)
- exclude_presented=False quando lead quer detalhes do veículo atual ou voltar a apresentado

CONFIDÊNCIA:
- Alta (0.8-1.0) quando intenção é explícita e clara
- Média (0.5-0.8) quando há ambiguidade mas contexto ajuda
- Baixa (<0.5) quando muito ambíguo (nesse caso, assumir general_recommendation)

EXEMPLOS DE CLASSIFICAÇÃO:

Exemplo 1:
Lead: "Gostei desse 2014, tem mais alguma opção de sedan?"
Contexto: Sentra 2014 apresentado, Sentra 2016 apresentado
→ search_intent=category_expansion, scope=category, modo=alternatives, use_vehicle_focus_as_filter=False, exclude_presented=True, confidence=0.9

Exemplo 2:
Lead: "Tem outro Sentra?"
Contexto: Sentra 2014 apresentado
→ search_intent=same_model_options, scope=same_model, modo=alternatives, use_vehicle_focus_as_filter=True, exclude_presented=True, confidence=0.95

Exemplo 3:
Lead: "Esse automático de 50 mil tá bom"
Contexto: Sentra 2014 (automático, R$ 55.000) apresentado
→ search_intent=return_to_presented_vehicle, scope=presented_vehicle, modo=vehicle_info, use_vehicle_focus_as_filter=True, exclude_presented=False, context_vehicle=Sentra 2014, confidence=0.85

Exemplo 4:
Lead: "Tem fotos desse carro?"
Contexto: Sentra 2014 em foco
→ search_intent=same_vehicle_info, scope=current_vehicle, modo=vehicle_info, use_vehicle_focus_as_filter=True, exclude_presented=False, confidence=0.95

Exemplo 5:
Lead: "Tem algum sedan mais novo que esse?"
Contexto: Sentra 2014 em foco
→ search_intent=preference_shift, scope=preference, modo=alternatives, use_vehicle_focus_as_filter=False, exclude_presented=True, preference=newer, confidence=0.9

Exemplo 6:
Lead: "Gostei do Sentra, mas tem algum sedan mais barato?"
Contexto: Sentra 2014 apresentado
→ search_intent=preference_shift, scope=preference, modo=alternatives, use_vehicle_focus_as_filter=False, exclude_presented=True, preference=cheaper, confidence=0.9

Exemplo 7:
Lead: "Queria um carro bom pra família"
Contexto: Nenhum veículo em foco
→ search_intent=general_recommendation, scope=open_recommendation, modo=alternatives, use_vehicle_focus_as_filter=False, exclude_presented=False, confidence=0.85
"""


def _get_intent_classifier_agent() -> Agent:
    model_id = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY")

    return Agent(
        name="Inventory Search Intent Classifier",
        model=OpenAIChat(id=model_id, api_key=api_key),
        instructions=[INTENT_CLASSIFIER_INSTRUCTIONS],
        output_schema=InventorySearchIntent,
        markdown=False,
    )


def classify_inventory_search_intent(
    lead_message: str,
    presented_vehicles: list[dict] | None = None,
    context_vehicle: str | None = None,
    vehicle_focus_reason: str | None = None,
) -> InventorySearchIntent:
    """
    Classifica a intenção de busca de veículos do lead.

    Args:
        lead_message: Mensagem atual do lead
        presented_vehicles: Lista de veículos já apresentados (com chave e características)
        context_vehicle: Veículo em foco na conversa
        vehicle_focus_reason: Razão do veículo estar em foco

    Returns:
        InventorySearchIntent com a classificação completa
    """
    agent = _get_intent_classifier_agent()

    context_parts = []
    if presented_vehicles:
        context_parts.append(f"PRESENTED_VEHICLES:\n{presented_vehicles}")
    if context_vehicle:
        context_parts.append(f"CONTEXT_VEHICLE: {context_vehicle}")
    if vehicle_focus_reason:
        context_parts.append(f"VEHICLE_FOCUS_REASON: {vehicle_focus_reason}")

    prompt = f"LEAD_MESSAGE:\n{lead_message}"
    if context_parts:
        prompt = f"\n".join(context_parts) + f"\n\n{prompt}"

    response = agent.run(prompt)

    if hasattr(response, "content") and isinstance(response.content, InventorySearchIntent):
        return response.content

    if isinstance(response, InventorySearchIntent):
        return response

    raise ValueError("Falha na classificação de intenção. Resposta não é um InventorySearchIntent.")