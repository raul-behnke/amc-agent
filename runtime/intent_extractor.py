import json
import os
from typing import Optional
from pydantic import BaseModel, Field
# pyrefly: ignore [missing-import]
from agno.agent import Agent
# pyrefly: ignore [missing-import]
from agno.models.openai import OpenAIChat

class QualificationFacts(BaseModel):
    nome: Optional[str] = Field(None, description="Nome do lead")
    interesse: Optional[str] = Field(None, description="Categoria ou perfil geral do carro buscado")
    intencao: Optional[str] = Field(None, description="Intenção: 'compra' ou 'troca de [modelo ano]'. Ex: 'troca de Gol 2011'.")
    tem_troca: Optional[bool] = Field(None, description="True se o lead mencionou ter carro para troca, perguntou se aceitam troca, ou informou modelo de troca.")
    veiculo_troca: Optional[str] = Field(None, description="Carro que o lead quer dar na troca (ano/modelo)")
    motivacao: Optional[str] = Field(None, description="Motivação da compra/troca (ex: 'preciso de mais espaço', 'carro antigo dando problema')")
    negociacao: Optional[str] = Field(None, description="Forma de pagamento desejada (ex: financiamento, à vista)")
    cidade: Optional[str] = Field(None, description="Cidade ou região do lead")

class IntentExtraction(BaseModel):
    is_asking_for_vehicle: bool = Field(..., description="True apenas se o lead está pedindo para ver opções de veículos, preços ou características do estoque.")
    vehicle_query: Optional[str] = Field(None, description="O modelo específico mencionado pelo lead. Se o lead pedir fotos de um carro específico (ex: 'fotos do Gol'), extraia 'Gol' aqui obrigatoriamente.")
    is_asking_for_photos: bool = Field(..., description="True APENAS se o lead pediu para RECEBER fotos do nosso estoque. False se o lead está enviando ou oferecendo fotos do carro dele.")
    is_accepting_info: bool = Field(..., description="True se o lead está aceitando/confirmando receber informações (ex: 'pode sim', 'claro', 'manda', 'quero saber', 'show'). False se está fazendo uma pergunta nova ou dando informação.")
    wants_human: bool = Field(..., description="True se o lead exigir um humano, gerente, ou estiver muito irritado.")
    qualification_facts: QualificationFacts = Field(default_factory=QualificationFacts)

EXTRACTOR_INSTRUCTIONS = """
Você é um extrator semântico frio, rápido e factual.
Seu único papel é extrair dados de intenção e qualificação da mensagem de um cliente em uma concessionária.
NÃO responda ao cliente. NÃO invente dados.
Se uma informação não estiver CLARA e EXPLÍCITA na mensagem, deixe como nulo.

REGRAS DE NOME:
- NUNCA extraia 'Lucas' como nome do lead. 'Lucas' é o nome do agente/vendedor.
- Só extraia o nome se o lead se identificar explicitamente (ex: 'Sou o Raul', 'Meu nome é João').

REGRAS DE INFERÊNCIA PERMITIDAS:
- Se o lead pergunta 'aceitam troca?' ou diz 'tenho um Gol 2011' ou 'quero trocar': tem_troca=True.
- Se o lead informa veículo de troca: intencao='troca de [modelo ano]'.
- Se o lead diz 'quero comprar' sem mencionar troca: intencao='compra'.

REGRAS PARA BUSCA DE VEÍCULOS E MOTIVAÇÃO:
Se o contexto mostrar que a última pergunta foi sobre a MOTIVAÇÃO da compra/troca (ex: "Qual o motivo da troca?"), e o lead responder coisas como "quero algo mais estiloso", "quero um carro maior", "busco conforto", "para trabalho":
1. Salve essa resposta no campo `motivacao`.
2. NÃO defina `is_asking_for_vehicle` como True. Isso NÃO é um pedido para listar estoque agora, é apenas a motivação.
Só defina `is_asking_for_vehicle` como True se o lead pedir ativamente para ver carros (ex: "me mostra opções", "tem modelos assim?", "quais carros estilosos vocês têm?").

SELEÇÃO DE OPÇÕES:
Se o agente apresentou várias opções (ex: HB20 2017 e HB20 2015) e o lead escolheu uma ou pediu fotos ("desse 2015", "do automático", "do mais barato"):
1. Preencha o `vehicle_query` com a referência completa do modelo escolhido (ex: "HB20 2015", "HB20 Automático").
2. Se o lead pedir fotos, marque `is_asking_for_photos=True`.

REGRAS PARA FOTOS:
- Se o lead diz 'tem fotos?', 'manda fotos', 'quero ver as fotos desse': is_asking_for_photos=True.
- Se o lead diz 'vou mandar as fotos', 'já te envio as fotos', 'já encaminho as imagens': is_asking_for_photos=False (ele está enviando, não pedindo).

Sua extração será usada pelo Runtime do sistema apenas para carregar o contexto antes da resposta do Vendedor.
"""

def _get_extractor_agent() -> Agent:
    model_id = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY")
    
    return Agent(
        name="Intent Extractor",
        model=OpenAIChat(id=model_id, api_key=api_key),
        instructions=[EXTRACTOR_INSTRUCTIONS],
        output_schema=IntentExtraction,
        markdown=False,
    )

def extract_intent_from_message(user_message: str, context: str = "") -> IntentExtraction:
    """
    Lê a mensagem do usuário (e um breve contexto se necessário) e extrai o JSON factual de intenção.
    """
    agent = _get_extractor_agent()
    
    prompt = f"MENSAGEM DO LEAD:\n{user_message}"
    if context:
        prompt = f"CONTEXTO RECENTE:\n{context}\n\n{prompt}"
        
    response = agent.run(prompt)
    
    # O Agno com response_model retorna diretamente a instância Pydantic no atributo content, 
    # ou podemos extrair do agent run result.
    if hasattr(response, 'content') and isinstance(response.content, IntentExtraction):
        return response.content
        
    # Fallback se o retorno for envelopado
    if isinstance(response, IntentExtraction):
        return response
        
    raise ValueError("Falha na extração semântica. Resposta não é um objeto IntentExtraction.")
