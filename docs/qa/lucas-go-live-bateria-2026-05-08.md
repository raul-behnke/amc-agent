# Bateria de Testes - Lucas SDR - Pré GO-LIVE

Data base: 2026-05-08  
Fonte de regressão: [conversas_reais_lucas_2026-05-07.md](/Users/raulbehnke/Documents/amc-agno/conversas_reais_lucas_2026-05-07.md:1)

## Objetivo

Validar se o agente Lucas está apto para atender leads reais sem repetir perguntas, sem perder contexto, sem quebrar o funil comercial e sem confirmar agendamentos inválidos.

## Regras Gerais de Aprovação

- Responde a pergunta do lead antes de continuar a qualificação.
- Faz apenas uma pergunta final por mensagem.
- Segue a ordem do funil: interesse -> troca/compra -> motivação -> financeiro -> localização -> agendamento.
- Não repete perguntas já respondidas.
- Não contradiz estoque na mesma conversa.
- Não confirma visita sem data e horário exatos.
- Só faz handoff quando houver pedido explícito de humano ou quando o fluxo comercial exigir.
- Se o lead pedir avaliação por WhatsApp, responde que sim e continua a qualificação.

## Como Executar

Para cada cenário abaixo:

1. Inicie uma nova sessão limpa.
2. Envie as mensagens do bloco `Roteiro`.
3. Compare as respostas reais com o bloco `Esperado`.
4. Preencha o campo `Resultado`.
5. Registre qualquer divergência em `Observações`.

---

## Cenário 01 - Interesse simples com agendamento válido

Origem: caso Onix/Voyage.

### Objetivo

Validar o funil completo com troca, motivação, financiamento, localização e agendamento real.

### Roteiro

**Lead:** Olá, pode sim!  
**Lead:** Quero trocar meu Voyage 1998  
**Lead:** Quero algo mais econômico  
**Lead:** Vai ser financiado mesmo  
**Lead:** Sou de Joinville  
**Lead:** Posso passar aí às 17?  
**Lead:** Pode ser amanhã às 09:00 então

### Esperado

- Exibir detalhes do veículo antes da qualificação.
- Coletar troca e motivação.
- Perguntar financiamento.
- Perguntar localização.
- Se 17h não estiver disponível, oferecer horários alternativos.
- Confirmar visita apenas depois de receber um horário exato válido.
- Criar agendamento no CRM.

### Resultado

- Status: `Pendente`
- Observações:

---

## Cenário 02 - Troca com carro incompleto

### Objetivo

Garantir que `tenho um Gol` não seja suficiente para avançar no funil.

### Roteiro

**Lead:** Oi, quero saber do HB20  
**Lead:** Tenho um Gol

### Esperado

- Responder sobre o HB20 primeiro.
- Perguntar se é compra ou troca, se necessário.
- Pedir ano/modelo completo do Gol.
- Não pular direto para financiamento.

### Resultado

- Status: `Pendente`
- Observações:

---

## Cenário 03 - Avaliação por WhatsApp

### Objetivo

Validar resposta correta quando o lead quer adiantar avaliação por WhatsApp.

### Roteiro

**Lead:** Tenho um Gol 2012  
**Lead:** Dá pra avaliar por WhatsApp mesmo?

### Esperado

- Responder que sim.
- Solicitar fotos, KM, ano/modelo completo e detalhes/avarias.
- Continuar a qualificação na próxima etapa correta.
- Não fazer handoff nesse momento só por causa da pergunta.

### Resultado

- Status: `Pendente`
- Observações:

---

## Cenário 04 - Compra sem troca

Origem: caso Fiat 500.

### Objetivo

Garantir que o agente respeite quando o lead informa que não tem carro para troca.

### Roteiro

**Lead:** Sim, por gentileza  
**Lead:** Para comprar, eu não tenho carro kkk  
**Lead:** Uso diário

### Esperado

- Não perguntar troca novamente.
- Seguir para motivação de compra.
- Depois seguir para forma de pagamento.

### Resultado

- Status: `Pendente`
- Observações:

---

## Cenário 05 - Pergunta financeira no meio do funil

Origem: caso Fiat 500 com cartão.

### Objetivo

Confirmar que o agente responde FAQ financeira e volta ao funil.

### Roteiro

**Lead:** Quero comprar  
**Lead:** Uso diário  
**Lead:** Financiar  
**Lead:** Cartão, como que funciona?

### Esperado

- Responder objetivamente sobre cartão.
- Não encerrar cedo sem necessidade.
- Voltar para a próxima etapa pendente do funil.
- Só fazer handoff se a política exigir atendimento humano explícito.

### Resultado

- Status: `Pendente`
- Observações:

---

## Cenário 06 - Entrada financeira como primeira mensagem

Origem: caso Gol com entrada de R$ 5 mil.

### Objetivo

Validar que o agente responde a pergunta inicial e conduz o funil sem se perder.

### Roteiro

**Lead:** Vcs financiam com 5 mil de entrada?  
**Lead:** Pra comprar msm

### Esperado

- Responder a dúvida sobre entrada primeiro.
- Perguntar motivação de compra na sequência.
- Não repetir a pergunta de financiamento depois que o lead já confirmar.

### Resultado

- Status: `Pendente`
- Observações:

---

## Cenário 07 - Ambiguidade curta do lead

Origem: caso S10 com resposta `Sim`.

### Objetivo

Ver se o agente desambiguar uma vez e continua normalmente.

### Roteiro

**Lead:** Sim tenho um Siena 2010  
**Lead:** Sim  
**Lead:** Troca o Siena

### Esperado

- Se necessário, pedir esclarecimento uma única vez.
- Assim que o lead confirmar troca, avançar sem repetir a mesma pergunta.

### Resultado

- Status: `Pendente`
- Observações:

---

## Cenário 08 - Mensagens quebradas em sequência

Origem: caso `Jumirim` + `Sp`.

### Objetivo

Garantir que o agente una contexto de múltiplas mensagens curtas.

### Roteiro

**Lead:** Jumirim  
**Lead:** Sp

### Esperado

- Interpretar como `Jumirim/SP`.
- Não perguntar cidade novamente logo após isso.

### Resultado

- Status: `Pendente`
- Observações:

---

## Cenário 09 - Estoque indisponível com sugestão similar

Origem: caso Gol indisponível.

### Objetivo

Validar sugestão de similares sem desviar do interesse principal.

### Roteiro

**Lead:** Queria um Gol  
**Lead:** Vocês não têm nem outro Gol?

### Esperado

- Informar indisponibilidade de forma clara.
- Sugerir similares apenas como alternativa.
- Não inventar disponibilidade.
- Não sair oferecendo horário sem contexto.

### Resultado

- Status: `Pendente`
- Observações:

---

## Cenário 10 - Consistência de estoque

Origem: caso Fiat 500 contraditório.

### Objetivo

Garantir que o agente não se contradiga sobre o estoque na mesma conversa.

### Roteiro

**Lead:** Sim, por gentileza  
**Lead:** Pode me mandar fotos?

### Esperado

- Se o carro estiver disponível, manter essa resposta do começo ao fim.
- Se não estiver, não corrigir depois sem nova consulta consistente.
- Nunca dizer `não temos` e depois `temos sim` no mesmo fluxo.

### Resultado

- Status: `Pendente`
- Observações:

---

## Cenário 11 - Disponibilidade objetiva

Origem: caso Clio.

### Objetivo

Checar se o agente responde disponibilidade antes de entrar no funil.

### Roteiro

**Lead:** Você tem o carro aí ou vendeu?  
**Lead:** Gostaria de ver esse Renault Clio Sedan

### Esperado

- Responder disponibilidade de forma direta.
- Só depois puxar compra/troca.
- Não repetir `compra ou troca` ignorando a pergunta do lead.

### Resultado

- Status: `Pendente`
- Observações:

---

## Cenário 12 - Dia sem horário

### Objetivo

Impedir falso agendamento.

### Roteiro

**Lead:** Sou de Joinville sim  
**Lead:** Posso ir segunda?

### Esperado

- Não confirmar visita.
- Buscar horários livres para a segunda-feira correspondente.
- Oferecer opções e pedir escolha do horário.

### Resultado

- Status: `Pendente`
- Observações:

---

## Cenário 13 - Horário indisponível com alternativas

Origem: caso Onix às 17h.

### Objetivo

Validar reação correta a slot indisponível.

### Roteiro

**Lead:** Posso passar aí às 17?

### Esperado

- Negar o slot de forma natural se não houver disponibilidade.
- Oferecer horários alternativos.
- Confirmar só quando o lead escolher um horário exato.

### Resultado

- Status: `Pendente`
- Observações:

---

## Cenário 14 - Áudio sem transcrição útil

Origem: casos com voice note.

### Objetivo

Garantir que o agente não invente conteúdo de áudio.

### Roteiro

**Lead:** > Voice Note <

### Esperado

- Pedir para o lead mandar por texto, se não houver transcrição disponível.
- Não alucinar resposta.

### Resultado

- Status: `Pendente`
- Observações:

---

## Cenário 15 - Lead responde fora de ordem

### Objetivo

Validar recuperação de contexto quando o lead mistura tema de veículo e financeiro.

### Roteiro

**Lead:** Queria um Gol  
**Lead:** Financiar  
**Lead:** Sou de Concórdia  
**Lead:** Mas vocês têm mesmo?

### Esperado

- Responder disponibilidade antes de insistir em cidade ou forma de pagamento.
- Não repetir cidade se já foi informada.
- Retomar o funil no ponto certo.

### Resultado

- Status: `Pendente`
- Observações:

---

## Cenário 16 - Pedido explícito de humano

### Objetivo

Validar handoff somente quando solicitado de forma clara.

### Roteiro

**Lead:** Quero falar com um consultor  
**Lead:** Prefiro atendimento humano

### Esperado

- Fazer handoff.
- Enviar despedida correta.
- Encerrar sem continuar qualificando.

### Resultado

- Status: `Pendente`
- Observações:

---

## Checklist Final de GO-LIVE

- [ ] Nenhum cenário repetiu pergunta já respondida.
- [ ] Nenhum cenário confirmou visita sem horário exato.
- [ ] Nenhum cenário inventou conteúdo de áudio.
- [ ] Nenhum cenário contradisse o estoque.
- [ ] Todas as perguntas financeiras foram respondidas antes da continuidade do funil.
- [ ] Todos os handoffs ocorreram no momento certo.
- [ ] Todos os agendamentos válidos tentaram criação real no CRM.
- [ ] Os campos mínimos de qualificação foram coletados quando aplicáveis.

## Conclusão

Preencher após a rodada:

- Status geral: `Pendente`
- Bloqueadores:
- Ajustes recomendados:
- Decisão: `GO` / `NO-GO`
