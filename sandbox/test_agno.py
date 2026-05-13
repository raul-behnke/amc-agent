import os
import sys
from dotenv import load_dotenv

from agno.agent import Agent
from agno.models.openai import OpenAIChat

# Carrega do .env na raiz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()


def test_agent():
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("Erro: OPENAI_API_KEY não encontrada.")
        return

    print(f"Testando conexão com o modelo: {model_name}")

    agent = Agent(
        model=OpenAIChat(id=model_name, api_key=api_key),
        description="Você é um assistente de testes do ZOI Agent Framework.",
        markdown=True,
    )

    try:
        response = agent.run(
            "Diga exatamente 'Olá, ZOI Agent Framework funcionando!' e nada mais."
        )
        print("Resposta do agente:")
        print(response.content)
    except Exception as e:
        print(f"Erro ao testar o agente: {e}")


if __name__ == "__main__":
    test_agent()
