# ZOI Agent Framework (ZAF) - Technical Plan & Roadmap

## 1. Revisão da Estrutura do Repositório
A estrutura foi alinhada com as expectativas arquiteturais, separando responsabilidades:
- `api/`: Controllers do FastAPI e endpoints (webhooks).
- `runtime/`: O motor de orquestração (recebe webhook -> carrega memória -> executa Agno -> salva estado).
- `agents/`: Definição dos agentes (ex: Lucas SDR).
- `tools/`: Ferramentas isoladas e stateless (consultar_estoque, agendar_visita).
- `memory/`: Gerenciamento de curto e longo prazo (Redis, PostgreSQL, Agno memory).
- `services/`: Lógica de negócio desacoplada (adapters para CRM, integrações).
- `state/`: Gerenciamento da state machine da conversa (lead funnel state).
- `prompts/`: Templates de prompts desacoplados do código fonte.
- `tests/` & `sandbox/`: Ambientes de validação.

## 2. Formalização da Arquitetura Inicial
- **Entrada:** Um Webhook na `api/` recebe o evento (ex: mensagem do WhatsApp/GHL).
- **Orquestração:** O `runtime/` intercepta a chamada, busca o ID da sessão e recupera o histórico na `memory/` e o estado atual no `state/`.
- **Agente:** O Agno é instanciado com o contexto recuperado e as `tools/` pertinentes ao estado do lead.
- **Processamento:** O modelo (OpenAI/Anthropic) toma decisões (Reasoning) e executa actions (ex: buscar estoque).
- **Saída:** A resposta é formatada, o novo estado/memória é persistido, e a resposta é devolvida/enviada via `services/`.

## 3. Plano das Sprints

### Sprint 0 — Foundation (Atual)
- Setup de repositório, Docker e docker-compose.
- Configuração do FastAPI (Rotas Base + Healthcheck).
- Setup do Agno e chaves de API.
- Configuração de logging estruturado.
- Gestão de variáveis de ambiente (`.env`).

### Sprint 1 — Conversational Runtime
- Setup do Lucas SDR Agent inicial (apenas prompt e conversa).
- Criação da sessão conversacional e memória simples em memória ou SQLite/Redis.
- Webhook funcional.
- Histórico de mensagens funcional.

### Sprint 2 — Inventory Tool
- Integração de um banco de dados falso (JSON) de estoque de veículos.
- Criação da Tool `consultar_estoque`.
- Roteamento contextual (só buscar estoque se fizer sentido no funil).

### Sprint 3 — Lead Qualification
- Implementação da State Machine na pasta `state/`.
- Regras de transição de estado (NEW_LEAD -> QUALIFYING -> SCHEDULING).
- Persistência das informações do lead qualificadas (extração estruturada).

### Sprint 4 — CRM Integration
- Criação do adapter GHL na pasta `services/`.
- Criação das Tools de CRM (atualizar_tags, adicionar_notas, mudar_pipeline).
- Fluxo formal de Handoff humano.

### Sprint 5 — Testing Sandbox
- Construção de testes unitários na pasta `tests/`.
- Sandbox interativo CLI ou Web (Streamlit/FastAPI Jinja) para debugar a memória e tracing.

## 4. Primeiros Componentes do Runtime (Sprint 0 -> 1)
- `api/main.py`: App FastAPI e injeção de dependências.
- `api/webhooks/chat.py`: Endpoint POST para receber a mensagem.
- `runtime/orchestrator.py`: Função central `process_message(session_id, user_message)`.
- `agents/lucas.py`: Definição base do agente Agno (sem tools complexas ainda).

## 5. Riscos Arquiteturais
- **Acoplamento de Estado:** O Agno pode tentar armazenar estado internamente de forma opaca. É vital que a ZAF controle a gravação explícita no banco/Redis.
- **Latência no Webhook:** A chamada ao LLM pode estourar o timeout de plataformas (como WhatsApp ou GHL). O runtime idealmente deveria processar de forma assíncrona (BackgroundTasks ou filas via Celery/Redis) e disparar o callback.
- **Context Window Overflow:** Sem um resumo (summarization) na memória de longo prazo, conversas longas estourarão os limites ou encarecerão os custos rapidamente.

## 6. Melhorias Estruturais (Next Steps)
- Adotar **Dependency Injection** clara (ex: `Depends()` no FastAPI) para plugar serviços e bancos.
- Para evitar timeout, prever o desenho de um **Event Bus** (Filas de mensagem) em Sprints futuras.
- Estruturar os Schemas via Pydantic numa pasta de domínio global (ex: `domain/` ou `schemas/`).
