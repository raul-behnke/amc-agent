# Planejamento de Sprints: Fase 2 (Evolução e Estabilização)

Este documento reflete a segunda fase do projeto do Agente Lucas SDR (AMC Veículos), focada em escalar a robustez, inteligência e as capacidades comerciais do agente após a reestruturação da sua arquitetura base (Migração para o modelo "LLM-Driven / Código Executa").

---

## Sprint 1: Estabilização e Prevenção de Casos Limites (Edge Cases)
**Status: EM ANDAMENTO**

**Objetivo:** Garantir que a fundação não quebre em cenários adversos de conversação, blindando o fluxo comercial e a renderização de dados no WhatsApp.

* **Manejo de Objeções Curtas:** Treinar o agente para lidar com "Não gostei desse", "Muito caro", ou "Não" sem perder o fluxo do checklist.
* **Timeouts e Retomadas (Follow-ups Naturais):** Tratar adequadamente leads que somem por horas/dias e voltam com respostas curtas, garantindo que o contexto seja recuperado de forma natural.
* **Failsafes de Mídia e Formatação:** Garantir no código (`orchestrator.py`) que vazamentos de Markdown (como `![]()`) jamais cheguem ao usuário final, mesmo que a LLM alucine.
* **Monitoramento de Hallucinations:** Mapeamento explícito para o agente se desculpar caso os dados do estoque estejam indisponíveis, em vez de inventar anos/valores/km.

---

## Sprint 2: Evolução do Estoque e "Match" Inteligente
**Status: NA FILA**

**Objetivo:** Tornar o Lucas SDR capaz de atuar não apenas consultando, mas *recomendando* de forma persuasiva.

* **Busca Semântica Avançada:** Melhorar a `inventory_tool` para entender sinônimos e intenções vagas (ex: "carro alto" = SUV; "carro pra Uber" = Sedan econômico).
* **Cross-Selling Automático:** Se o lead pede um modelo ausente no estoque, o agente deve sugerir proativamente veículos similares na mesma categoria e faixa de preço.
* **Tratamento de Múltiplos Filtros Simultâneos:** Melhorar a extração no `vehicle_focus` quando o cliente passa muitos parâmetros de uma vez ("Quero um hatch automático acima de 2020 e abaixo de 80 mil").

---

## Sprint 3: Otimização de Agendamento e Handoff (Transição Humana)
**Status: NA FILA**

**Objetivo:** Suavizar o fechamento de visitas e garantir uma transição perfeita para o vendedor humano no GHL.

* **Validação de Agenda Dinâmica:** Conectar a tool de agendamento de forma que o agente verifique disponibilidades reais da loja (horário comercial).
* **Resumo de Handoff Limpo:** Ao agendar ou pedir transbordo, gerar um `conversation_summary` objetivo para a equipe de vendas, destacando apenas os dados do checklist e a intenção final.
* **Escalada Emergencial (Escalation):** Identificar intenções de frustração, urgência máxima ou pedido de gerente para acionar o transbordo imediato, silenciando o bot.

---

## Sprint 4: Memória de Longo Prazo e Retenção de Contexto
**Status: NA FILA**

**Objetivo:** Permitir que o Lucas construa relacionamento e lembre do cliente em interações futuras.

* **Evolução do `lead_answers`:** Armazenar as preferências e respostas qualificadas permanentemente nos Custom Fields do GHL, não apenas no banco de sessões.
* **Retomada de Conversa Ativa:** Criar suporte a Webhooks reversos para que o Lucas puxe assunto dias depois sobre novas entradas de estoque alinhadas ao interesse anterior.
* **Anti-Looping Avançado:** Criação de bloqueio estrito no prompt para que a IA seja penalizada se tentar refazer perguntas de checklist já marcadas como "concluídas".

---

## Sprint 5: Refinamento de Persuasão e Tom de Voz
**Status: NA FILA**

**Objetivo:** Lapidar o comportamento para que o agente se comunique com o nível de conversão dos melhores vendedores da AMC.

* **Auditoria de Transcrições (Ajuste Fino):** Revisar conversas reais em produção para extrair momentos de excesso de formalidade e ajustar o `prompt` em conformidade.
* **Gatilhos Mentais (Escassez/Urgência):** Injetar diretivas comerciais para criar senso de oportunidade sem parecer agressivo (ex: "Esse modelo costuma sair rápido por esse preço").
* **A/B Testing de Prompts:** Criar e mensurar variações da personalidade do Lucas para identificar qual abordagem converte mais visitas à loja física.
