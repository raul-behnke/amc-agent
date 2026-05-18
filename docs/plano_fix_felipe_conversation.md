# Plano de Correção — Bugs detectados nas conversas com "Felipe"

**Data:** 2026-05-18
**Branch:** `fix/felipe-conversation-bugs`
**Sessões analisadas (VPS, `/var/log/amc-agno/app.log`):**
- `bOhcRIey3ToF46t8QPb0` (18/mai 19:58 → 20:09)
- `51x9tmHRKGUhGuVAFwkO` (18/mai 20:11 → 20:23)

---

## 1. Bugs identificados

### Bug A — "Não temos o sedã específico que você mencionou"
**Sessão 1, linha 3.** O lead pediu apenas categoria genérica ("Gostaria de um sedã"), mas o agente respondeu negando um modelo que ele nunca citou.

**Causa raiz:** em `runtime/orchestrator.py::_build_stock_injection`, quando não há match exato do modelo, é injetado o texto:
> `"INFORME AO LEAD QUE NÃO TEMOS O MODELO ESPECÍFICO DISPONÍVEL NO MOMENTO..."`

O prompt em `prompts/lucas_sdr.py` já tem regra mandando ignorar isso para categorias genéricas, mas o LLM regride. Solução: **remover a frase contraditória na origem** quando a busca for por categoria genérica.

### Bug B — Resposta duplicada (race no orchestrator)
**Sessão 2, linhas 29-30.** Duas respostas seguidas do agente em <2s ("Entendi, vamos ver isso!" + "Para te ajudar, me conta, qual é o seu nome?").

**Causa raiz:** O lead enviou "Cara" (20:12:38) e "E a menor parcela" (20:13:12) em sequência. Cada webhook disparou `process_message` em paralelo. O detector de mensagens não respondidas (`_detect_unanswered`) só ajuda quando o histórico está atualizado, mas como as duas chamadas rodam ao mesmo tempo, ambas veem o mesmo histórico (sem outbound entre elas) e ambas chamam o agente.

**Fix:** `asyncio.Lock` por `session_id` para serializar o processamento. A segunda chamada espera a primeira terminar; quando entra, o `_detect_unanswered` já enxerga a resposta da primeira e processa só a mensagem nova (ou consolida).

### Bug C — Perda do contexto "menor parcela" (interpretação de valor)
**Sessão 2, linhas 39-40.** Lead pediu "menor parcela" no início e mais tarde disse "não tava 2 e poucos mil". O agente interpretou como **preço total** ("Essa faixa de 2 e poucos mil não corresponde aos nossos modelos") em vez de **parcela mensal**.

**Causa raiz:** Não há regra no prompt para interpretar valores numéricos no contexto de `negociacao='menor parcela'`. O state já tem essa informação, mas o agente não a usa para desambiguar.

**Fix:** instrução no prompt; quando `NEGOCIACAO_LEAD` indica foco em parcela, valores numéricos citados pelo lead devem ser tratados como parcela mensal.

### Bug D — Contradição no agendamento (Sessão 1, linhas 23-25)
Agente disse "não consigo agendar para meio-dia" e logo após confirmou agendamento para 12:15.

**Causa raiz:** Não há regra explícita no prompt sobre horário de almoço; o LLM inventou a restrição. A ferramenta `buscar_horarios_livres` é a fonte de verdade.

**Fix:** instrução clara: nunca afirme indisponibilidade sem antes consultar `buscar_horarios_livres`.

### Bug E — Desculpas defensivas sem motivo (Sessão 2, linhas 35-36)
Lead enviou apenas "?" e o agente respondeu "Desculpe pela confusão" — não houve erro anterior justificando o pedido de desculpas.

**Fix:** regra no prompt proibindo pedidos de desculpa sem erro explícito documentado na conversa.

---

## 2. Fases de implementação

### Fase 1 — Fix A (headline sedã genérico) [arquivos: `runtime/orchestrator.py`]
Detectar quando a `search_query` é uma categoria genérica (`sedan`, `sedã`, `suv`, `hatch`, `picape`, `caminhonete`, etc.) e, nesse caso, substituir a injeção contraditória por uma afirmação neutra ("Separei estas opções de {categoria}").

### Fase 2 — Fix B (lock por sessão) [arquivos: `runtime/orchestrator.py`]
- Adicionar `_session_locks: dict[str, asyncio.Lock]`.
- Envolver o corpo de `process_message` em `async with _get_session_lock(session_id):`.
- Logar quando uma chamada ficou aguardando (útil para validar em produção).

### Fase 3 — Fix C, D, E (regras no prompt) [arquivos: `prompts/lucas_sdr.py`]
Acrescentar três bullets:
- Interpretação de valores quando `NEGOCIACAO_LEAD` foca em parcela.
- Proibição de afirmar indisponibilidade de horário sem consultar a ferramenta.
- Proibição de pedidos de desculpa sem erro anterior.

### Fase 4 — Validação local
```bash
ruff check . && ruff format --check .
pytest tests/ -v
source venv/bin/activate && uvicorn api.main:app --reload --port 8000
```
Replay manual via `curl` ou WhatsApp sandbox dos dois cenários:
1. "Olá" → "Gostaria de um sedã" → resposta NÃO deve conter "específico".
2. Duas mensagens em <2s → 1 única resposta consolidada.
3. "menor parcela" + "Corsa" + "não tava 2 mil" → agente confirma se é parcela.

### Fase 5 — Commit + Deploy
- Commit único na branch `fix/felipe-conversation-bugs`.
- PR para `main` ou merge direto.
- `./deploy_production.sh` na VPS.
- `tail -f /var/log/amc-agno/app.log` para smoke test.

---

## 3. Riscos e mitigações

| Risco | Mitigação |
|-------|-----------|
| Lock por sessão pode introduzir latência se uma resposta demorar muito | Lock é `asyncio.Lock` (não thread); só serializa quem é da mesma sessão. Sem timeout — se o agent travar, o webhook do GHL já tem timeout próprio. |
| Detecção de categoria genérica pode pegar falsos positivos (ex: "sedan Civic") | Match só dispara quando a query é EXATAMENTE a palavra-chave ou pequena variação. Modelos compostos não entram. |
| Regras novas no prompt podem aumentar tokens | Acréscimo de ~3 bullets curtas, impacto desprezível. |

---

## 4. Critérios de aceitação

- [ ] Replay da Sessão 1 não produz frase com "específico" quando lead pediu só categoria.
- [ ] Duas mensagens em <3s produzem 1 resposta única.
- [ ] Lead com `negociacao='menor parcela'` que cita valor numérico recebe confirmação de que é parcela.
- [ ] `ruff check` e `pytest` passam.
- [ ] Deploy executado sem erros; logs limpos por 10min após restart.
