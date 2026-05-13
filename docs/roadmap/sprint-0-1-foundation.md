Sprint 0 e 1

Status

- Sprint 0: especificacao base concluida neste documento
- Sprint 1: runtime fino iniciado com corte de decisoes conversacionais do backend

Objetivo

- mover a decisao de conversa para o agente
- manter o backend como executor de webhook, contexto, persistencia, anexos, agenda, handoff e integracoes GHL

Arquitetura-alvo

- `api/webhooks/chat.py`
  - recebe payloads GHL
  - normaliza mensagem
  - preserva `veiculo_interesse` vindo de origem externa quando existir
  - envia a execucao para background
- `runtime/orchestrator.py`
  - busca historico recente no GHL
  - resume mensagens pendentes em ordem
  - injeta apenas contexto factual da sessao
  - executa o agente
  - nao decide fluxo, proxima pergunta, veiculo em foco ou resposta de fotos/cards
- `agents/lucas.py`
  - concentra o agente conversacional
  - recebe tools executoras e memoria de sessao
- `tools/*`
  - executam consulta/acao
  - nao conduzem conversa

Principio central

- IA decide
- codigo executa

O que sai do runtime na Sprint 1

- resposta deterministica de card
- resposta deterministica de fotos
- inferencia de proxima pergunta do funil
- preprocessamento que marca troca, financiamento, localizacao ou motivo por regex antes do agente
- inferencia automatica de veiculo a partir da mensagem inbound

Session state oficial

Estado atual mantido em `state/lead_model.py` e `tools/qualification.py`:

- `status`
- `nome`
- `tipo_veiculo`
- `marca_preferida`
- `modelo_preferido`
- `faixa_preco`
- `ano_minimo`
- `cambio`
- `tem_troca`
- `veiculo_troca`
- `motivo_troca`
- `precisa_financiamento`
- `e_local`
- `data_visita`
- `veiculo_interesse`
- `motivo_handoff`

Evolucao aprovada para Sprint 2:

- `vehicle_focus.current`
- `vehicle_focus.last_valid`
- `vehicle_focus.alternatives_shown`
- `vehicle_focus.active_filters`
- `lead_stage`
- `lead_answers`
- `conversation_summary`

Intencoes conversacionais oficiais

- pergunta sobre carro atual
- pedido de alternativas
- pedido de fotos
- pedido de preco/condicao
- resposta curta de qualificacao
- objecao
- pergunta operacional
- continuidade so por WhatsApp
- pedido de falar com humano
- agendamento de visita

Conceito de veiculo em foco

- fonte primaria: estado salvo pelo agente (`veiculo_interesse` hoje, `vehicle_focus.current` na Sprint 2)
- fonte secundaria: payload externo de origem quando o lead chega por anuncio/listagem
- o runtime nao escolhe nem troca o veiculo em foco
- quando o agente quiser fotos ou card, ele deve consultar tool apropriada com base no contexto atual

Contrato oficial das tools

- `consultar_estoque`
  - entrada: filtros declarativos
  - saida: dados de estoque formatados para uso do agente
  - proibido: decidir proxima pergunta comercial
- `consultar_faq`
  - entrada: pergunta objetiva
  - saida: resposta operacional/factual
- `registrar_qualificacao`
  - entrada: campos explicitamente coletados
  - saida: confirmacao de persistencia e snapshot resumido
  - observacao: ainda retorna guia de proximo passo legado; isso deve ser reduzido na Sprint 2/3
- `consultar_qualificacao`
  - entrada: nenhuma alem da sessao
  - saida: estado atual resumido
- `buscar_horarios_livres`
  - entrada: data
  - saida: slots disponiveis
- `agendar_visita`
  - entrada: data/hora e dados do lead
  - saida: status do agendamento
- `sincronizar_com_crm`
  - entrada: sessao e telefone
  - saida: status de sincronizacao
- `escalonar_lead`
  - entrada: motivo, ids do CRM e mensagem de despedida
  - saida: status de handoff

Criterios de aceite por fluxo

- pergunta objetiva sobre veiculo
  - runtime nao monta a resposta
  - agente responde usando tool adequada
- fotos
  - runtime apenas converte placeholders/URLs em anexos
  - agente decide se envia fotos
- qualificacao
  - runtime nao injeta pergunta obrigatoria
  - agente decide quando retomar o funil
- handoff
  - agente usa tool de escalonamento
  - runtime apenas entrega a resposta final
- agenda
  - runtime nao confirma agendamento por conta propria
  - agente chama agenda e CRM quando necessario

Backlog tecnico por arquivo/componente

- `runtime/orchestrator.py`
  - remover respostas deterministicas de foto/card
  - remover preprocessamento comercial por regex
  - manter somente contexto factual + historico pendente + execucao do agente
- `api/webhooks/chat.py`
  - parar de inferir veiculo automaticamente da mensagem inbound
  - manter apenas veiculo vindo do payload externo quando aplicavel
- `state/lead_model.py`
  - preparar migracao para estrutura `vehicle_focus` e `conversation_summary`
- `tools/qualification.py`
  - desacoplar retorno de persistencia do conceito de "proximo passo obrigatorio"
- `tools/inventory.py`
  - separar melhor busca de estoque, card e fotos em contratos executores claros
- `prompts/lucas_sdr.py`
  - adaptar prompt para depender menos de guias hardcoded do backend
- `tests/test_orchestrator.py`
  - trocar asserts de resposta deterministica por asserts de contexto fino
- `tests/test_chat_webhook.py`
  - validar que webhook nao infere veiculo inbound

Critério de aceite da Sprint 1

- runtime nao decide proxima pergunta
- runtime nao escolhe veiculo
- runtime nao define fluxo comercial
- runtime ainda preserva webhook, anexos, persistencia, agenda, handoff e integracoes GHL
