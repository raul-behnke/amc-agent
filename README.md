# ZOI Agent Framework

Framework operacional para agentes comerciais orientados por IA.

## Objetivos
- Orquestração de agentes
- Memória persistente
- Ferramentas desacopladas
- Integração CRM
- Multi-agent systems
- Runtime observável

## Arquitetura
- Agents
- Tools
- Memory
- State Machine
- Event Bus
- Runtime

# amc-agent

## Stack
- Agno
- FastAPI
- PostgreSQL
- Redis
- Docker

## Primeiro Projeto
Lucas SDR Agent - AMC Veículos

## Como Testar (Ambiente Sandbox)

Para testar o agente localmente usando o **ngrok** e o seu próprio WhatsApp via CRM GoHighLevel:

1.  **Tag de Segurança**: No seu contato de teste dentro do GHL, adicione a tag `agente-ia-dev`. O agente só responderá a contatos com esta tag.
2.  **Inicie o Sandbox**:
    ```bash
    ./scripts/start_dev.sh
    ```
3.  **Configuração GHL**: Copie a URL gerada pelo ngrok e cole na configuração de Webhook do seu Workflow no GoHighLevel.
4.  **Chat**: Mande uma mensagem para o número da sua loja e veja o Lucas responder em tempo real!
