# TODO - ZOI Agent Framework

---

## Sprint 0 — Foundation ✅ CONCLUÍDA

### 1. Configuração do Projeto
- [x] Inicializar ambiente virtual (`python -m venv venv`)
- [x] Criar arquivo `requirements.txt` com as dependências base.
- [x] Criar arquivo `.env.example` com variáveis essenciais.

### 2. Docker & Infra
- [x] Escrever `Dockerfile` para FastAPI.
- [x] Escrever `docker-compose.yml` (API + PostgreSQL + Redis).

### 3. Base do Código (FastAPI)
- [x] Criar `api/main.py` com setup da aplicação FastAPI.
- [x] Criar rota de `/health` para healthcheck.
- [x] Configurar formatação de logs (loguru).

### 4. Base do Agno
- [x] Criar script de validação `sandbox/test_agno.py`.

### 5. Padrões de Qualidade
- [x] Criar `.gitignore`.
- [x] Adicionar linter/formatter (Ruff).

---

## Sprint 1 — Conversational Runtime ✅ CONCLUÍDA

### 1. Lucas SDR Agent
- [x] Criar `prompts/lucas_sdr.py` com description e instructions modulares.
- [x] Criar `agents/lucas.py` com fábrica do agente (create_lucas_agent).

### 2. Webhook & API
- [x] Criar `api/schemas.py` com ChatRequest e ChatResponse (Pydantic).
- [x] Criar `api/webhooks/chat.py` com endpoint POST /webhook/chat.
- [x] Registrar router no `api/main.py`.

### 3. Runtime & Orquestração
- [x] Criar `runtime/orchestrator.py` com process_message().
- [x] Execução assíncrona (arun).
- [x] Logging estruturado.

### 4. Memória & Sessão
- [x] Sessão persistente via Agno SqliteDb.
- [x] Histórico de conversa multi-turno funcionando.
- [x] Validação de memória contextual (o agente lembra do que o lead disse).

---

## Sprint 2 — Inventory Tool ✅ CONCLUÍDA

### 1. Integração com CRM (GHL)
- [x] Criar `services/ghl.py` — adapter desacoplado para GoHighLevel.
- [x] Buscar estoque real via Custom Value da API GHL.
- [x] Versão sync e async do fetch (sync para tools, async para outros usos).

### 2. Inventory Tool
- [x] Criar `tools/inventory.py` com função `consultar_estoque`.
- [x] Filtros por: marca, modelo, faixa de preço, ano, câmbio.
- [x] Formatação amigável com título, ano, km, preço e foto.
- [x] Limite de 5 resultados por busca.

### 3. Integração com Agente
- [x] Registrar tool no Lucas SDR Agent.
- [x] Testar busca contextual na conversa (4 turnos com estoque real).
- [x] Agente apresenta opções reais do estoque da AMC Veículos (32 veículos).

---

## Sprint 3 — Lead Qualification ✅ CONCLUÍDA

### 1. Modelo de Dados
- [x] Criar `state/lead_model.py` com `LeadQualification` (Pydantic) e `LeadStatus`.
- [x] Implementar score de completude (0-100%).

### 2. Ferramentas de Qualificação
- [x] Criar `tools/qualification.py` com `registrar_qualificacao` e `consultar_qualificacao`.
- [x] Implementar transição automática de estados do funil.
- [x] Injeção dinâmica de `session_id` no agente.

### 3. Integração e API
- [x] Atualizar prompt do Lucas para extração estruturada.
- [x] Criar endpoint `GET /leads/{session_id}/qualification` para consulta externa do estado.
- [x] Validar persistência e atualização de estado multi-turno.

---

## Sprint 4 — CRM Integration ✅ CONCLUÍDA

### 1. Sincronização de Contato
- [x] Expandir `services/ghl.py` com busca/criação de contato.
- [x] Implementar `upsert_contact` via telefone.
- [x] Sucesso na criação de contato real no GHL durante testes.

### 2. Gestão de Oportunidades
- [x] Criar `tools/crm.py` com `sincronizar_com_crm`.
- [x] Implementar lógica de atualização de pipeline e estágios baseada no status ZAF.
- [x] Adição automática de Notas com o resumo da qualificação no contato.

### 3. Integração do Agente
- [x] Registrar tool de CRM no Lucas Agent com injeção de `session_id`.
- [x] Atualizar prompts para gatilhos de sincronização (avanço de qualificação e handoff).
- [x] Validar extração automática de telefone para sincronização.

---

## Sprint 4.5 — Sandbox & Local Testing (ATUAL) 🛠️

### 1. Ambiente Local (ngrok)
- [ ] Criar script `scripts/start_dev.sh` para subir API + Ngrok.
- [ ] Configurar `.env.dev` com tags de teste.

### 2. Filtros de Segurança (Tags de Dev)
- [ ] Implementar verificação de tags no webhook (ex: responder apenas se tiver `agente-ia-dev`).
- [ ] Adicionar bypass de segurança para IPs específicos ou tokens de teste.

### 3. Validação Real-Time
- [ ] Testar fluxo completo via WhatsApp (GHL -> ngrok -> ZAF -> GHL).
- [ ] Monitorar logs de Background Tasks e GHL API Responses.

---

## Sprint 5 — Refinement & Humanization ✅ CONCLUÍDA

### 1. Tom de Voz & Estilo
- [x] Refinar prompts para evitar padrões robóticos ("Perfeito", "Entendido").
- [x] Implementar estilo "WhatsApp Native" (proativo, direto e informal).
- [x] Melhorar apresentação visual do estoque com emojis e negrito.

### 2. Tratamento de Erros & Edge Cases
- [x] Feedback humanizado para buscas sem resultados.
- [x] Tratamento de erros de API com fallback amigável.

### 3. Documentação Final & Handover
- [x] Atualizar `README.md` com instruções de Sandbox.
- [x] Criar script `scripts/start_dev.sh`.

---

**STATUS FINAL**: Projeto pronto para Validação Real-Time em Sandbox.

---

## Sprint 5 — Testing Sandbox

- [ ] Testes unitários em `tests/`.
- [ ] Sandbox interativo para debug.
- [ ] Tracing e replay de conversas.
