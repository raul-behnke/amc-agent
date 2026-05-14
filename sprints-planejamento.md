# Planejamento LLM — Motor de Decisão e Tools

> Todas as melhorias focadas em aprimorar o comportamento da LLM.
> Código mínimo. Prompts e contexto como principal alavanca.

---

## Round 1 — Corrigido (esta sessão)

| # | Melhoria | Onde | Status |
|---|----------|------|--------|
| 1 | `is_accepting_info` → LLM decide se apresenta ou ignora estoque | `lucas_sdr.py` | ✅ |
| 2 | Qualificação como GUIA, não fila rígida | `lucas_sdr.py` | ✅ |
| 3 | `SINAL_DE_VISITA` respeita maturidade (orchestrator injeta contexto diferente) | `orchestrator.py` | ✅ |
| 4 | Disponibilidade + card na mesma mensagem | `lucas_sdr.py` | ✅ |
| 5 | Card com emojis = exceção à regra de listas | `lucas_sdr.py` | ✅ |
| 6 | Removido `SESSION_STATE_JSON` redundante, adicionados campos diretos | `orchestrator.py` | ✅ |
| 7 | Eficiência 3-4 frases exceto card de veículo | `lucas_sdr.py` | ✅ |
| 8 | Intent extractor: queries compostas + `search_filters` | `intent_extractor.py` | ✅ |
| 9 | Agendamento flexível: ativo em HOT, adaptativo em baixa maturidade | `lucas_sdr.py` | ✅ |

---

## Round 2 — Próximas melhorias LLM

### 2.1 Contexto de estoque como decisão, não injeção cega

**Problema atual:** O orchestrator injeta dados de estoque via `system_injections` sempre que `is_accepting_info=True`. A LLM precisa ignorar ativamente, o que nem sempre funciona.

**Melhoria LLM:** Adicionar ao contexto do Lucas se já existe veículo em foco e se o lead está engajado:

```
VEICULO_EM_FOCO_ENGAJADO=True — lead já está negociando o Sentra
```

Isso dá mais sinal para a LLM decidir corretamente sem depender de "ignorar ativamente".

**Código:** `_build_session_context` em `orchestrator.py` — adicionar flag de engajamento baseada em `presented_vehicles` + interações.

---

### 2.2 `search_filters` do Intent Extractor → passado para `consultar_estoque`

**Problema atual:** O novo campo `search_filters` foi adicionado ao IntentExtraction mas o orchestrator não o utiliza.

**Melhoria LLM+:** No orchestrator, quando `search_filters` estiver preenchido, extrair os filtros e passar para `consultar_estoque` como `faixa_preco`, `tipo_veiculo`, `ano_minimo`, `cambio`.

**Código:** `orchestrator.py` — parsear `search_filters` e repassar na chamada de estoque.

---

### 2.3 Prompt do Lucas: instrução de ferramentas mais explícita

**Problema atual:** As ferramentas (`buscar_horarios_livres`, `agendar_visita`, `escalonar_lead`) são registradas no Agno mas o prompt não explica QUANDO usar cada uma de forma sequencial.

**Melhoria LLM:** Adicionar instrução de workflow de agendamento:

```
"WORKFLOW DE AGENDAMENTO: 1. Use buscar_horarios_livres para consultar disponibilidade.
2. Apresente 2-3 opções ao lead. 3. Quando o lead escolher, use agendar_visita com data_hora_iso.
4. Após confirmar agendamento, use escalonar_lead com motivo 'agendamento_realizado'.
5. Após escalonar, PARE — não faça mais perguntas."
```

**Arquivo:** `prompts/lucas_sdr.py`

---

### 2.4 Prompt do Lucas: confirmar agendamento se lead propõe horário

**Problema atual:** Quando o lead diz "posso ir sábado às 14h", o agente pode apenas responder "pode ir" sem de fato agendar.

**Melhoria LLM:**
```
"CONFIRMAÇÃO DE AGENDAMENTO: Se o lead propor data e horário, NÃO apenas confirme verbalmente. USE a ferramenta agendar_visita para criar o compromisso real. Só diga 'está confirmado' DEPOIS de usar a ferramenta."
```

**Arquivo:** `prompts/lucas_sdr.py`

---

### 2.5 Intent Extractor: distinguir "busca por perfil" de "resposta qualificatória"

**Problema atual:** "É meu primeiro carro" pode ser interpretado como `is_accepting_info=True` e triggerar busca.

**Melhoria LLM:** Refinar a definição de `is_accepting_info` no prompt do extractor:

```
"is_accepting_info=True APENAS quando o lead está confirmando que quer receber informações que você ofereceu (ex: você perguntou 'Posso te passar mais informações?' e ele respondeu 'pode sim'). Se o lead está apenas respondendo uma pergunta de qualificação ('é meu primeiro carro', 'tenho 10 mil', 'quero financiar'), is_accepting_info=False — ele está dando informação, não aceitando receber info."
```

**Arquivo:** `intent_extractor.py` — atualizar `EXTRACTOR_INSTRUCTIONS`

---

### 2.6 Prompt do Ranker: considerar veículo em foco para evitar sugestões incoerentes

**Problema atual:** O ranker LLM do estoque não sabe qual veículo está em foco na conversa.

**Melhoria LLM+:** Passar `vehicle_focus` no `search_brief` do ranker para que ele evite sugerir veículos que competem com o foco atual.

**Código:** `tools/inventory.py` — incluir campo no `_build_search_brief` e no user_prompt do ranker.

---

### 2.7 Contexto de conversa resumido para sessões longas

**Problema atual:** `num_history_runs=8` pode não ser suficiente em conversas muito longas (30+ turnos).

**Melhoria LLM+:** Implementar resumo progressivo — a cada 10 mensagens, gerar um resumo via LLM e armazenar em `lead.conversation_summary`. O resumo substitui histórico antigo.

**Código:** `runtime/context_compactor.py` (novo) — LLM que resume histórico e salva no lead state.

---

## Priorização Round 2

| Ordem | Item | Impacto | Esforço |
|-------|------|---------|---------|
| 1 | 2.5 Refinar `is_accepting_info` no extractor | ALTO — evita buscas erradas | Baixo |
| 2 | 2.3 Workflow de agendamento explícito | ALTO — agente agenda de fato | Baixo |
| 3 | 2.4 Confirmar agendamento com ferramenta | ALTO — não só verbalmente | Baixo |
| 4 | 2.2 `search_filters` → estoque | MÉDIO — buscas mais precisas | Médio |
| 5 | 2.1 Flag de engajamento no contexto | MÉDIO — LLM decide melhor | Baixo |
| 6 | 2.6 Ranker considera foco atual | MÉDIO — sugestões coerentes | Médio |
| 7 | 2.7 Resumo progressivo de sessão | BAIXO — sessões longas | Alto |

---

## Fluxo ideal do motor de decisão LLM

```
Mensagem do Lead
    │
    ├─→ Intent Extractor (LLM 1)
    │    ├─ Extrai fatos qualificatórios
    │    ├─ Detecta intenção de busca (is_asking_for_vehicle + search_filters)
    │    ├─ Detecta intenção de visita (visit_intent)
    │    ├─ Detecta aceitação de info (is_accepting_info — APENAS confirmação de oferta)
    │    └─ Detecta pedido de fotos
    │
    ├─→ Orchestrator (código mínimo)
    │    ├─ Registra fatos no lead state
    │    ├─ Se busca de veículo → consulta estoque (com search_filters)
    │    ├─ Se pedido de fotos → busca URLs
    │    ├─ Se intenção de visita → injeta sinal (com maturidade)
    │    └─ Monta contexto: estado + injeções + mensagem
    │
    └─→ Lucas Agent (LLM 2 — motor de decisão)
         ├─ Lê contexto completo
         ├─ Decide: apresentar veículo ou ignorar estoque injetado?
         ├─ Decide: qual pergunta fazer (guia, não fila)?
         ├─ Decide: propor agendamento agora ou coletar mais dados?
         ├─ Decide: usar ferramenta de agenda ou continuar qualificação?
         └─ Gera resposta + ação (agendar, escalar, perguntar)
```

**Princípio:** O código ORQUESTRA (busca dados, monta contexto). A LLM DECIDE (apresenta, pergunta, agenda, ignora).
