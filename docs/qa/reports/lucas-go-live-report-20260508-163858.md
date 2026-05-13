# Relatório de Execução - Bateria Lucas SDR

Gerado em: 2026-05-08 16:38:58
Fonte: `docs/qa/lucas-go-live-payloads-2026-05-08.json`

## qa-c01 - Interesse simples com agendamento valido

- Status final: `SCHEDULED`
- Score final: `50%`
- Qualificação final: `{"status": "SCHEDULED", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": true, "veiculo_troca": "Voyage 1998", "motivo_troca": "Quero algo mais econômico", "precisa_financiamento": true, "e_local": true, "data_visita": "2026-05-09T09:00:00", "veiculo_interesse": "Onix LT 1.4", "motivo_handoff": null}`

### Interações

**1. Lead:** Olá, pode sim!

**1. Lucas:** Você pensa em comprar direto ou tem um carro para dar na troca?

**2. Lead:** Quero trocar meu Voyage 1998

**2. Lucas:** O que te motivou a querer trocar o Voyage 1998 agora?

**3. Lead:** Quero algo mais econômico

**3. Lucas:** Você pensa em financiar o Onix ou vai pagar à vista?

**4. Lead:** Vai ser financiado mesmo

**4. Lucas:** Você é de Joinville ou região?

**5. Lead:** Sou de Joinville

**5. Lucas:** Show! Quando fica bom pra você vir conhecer o carro na loja?

**6. Lead:** Posso passar aí às 17?

**6. Lucas:** Não consegui acessar a agenda agora, mas me diz o melhor horário pra você que eu reservo aqui com o pessoal!

**7. Lead:** Pode ser amanhã às 09:00 então

**7. Lucas:** Não consegui acessar a agenda agora, mas já registrei seu interesse para amanhã às 09:00. Confirma se esse horário tá bom para você vir conhecer o carro na loja?

---

## qa-c02 - Troca com carro incompleto

- Status final: `NEW_LEAD`
- Score final: `16%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": true, "veiculo_troca": "Gol", "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": "Hyundai HB20", "motivo_handoff": null}`

### Interações

**1. Lead:** Oi, quero saber do HB20

**1. Lucas:** Olá! 👋 Vi que você quer saber do HB20. Posso te passar mais informações sobre ele?

**2. Lead:** Tenho um Gol

**2. Lucas:** Qual ano/modelo completo do seu Gol?

---

## qa-c03 - Avaliacao por WhatsApp

- Status final: `NEW_LEAD`
- Score final: `16%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": true, "veiculo_troca": "Gol 2012", "motivo_troca": "querer trocar Gol 2012", "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** Tenho um Gol 2012

**1. Lucas:** O que te fez querer trocar o Gol 2012 agora?

**2. Lead:** Dá pra avaliar por WhatsApp mesmo?

**2. Lucas:** Sim, pode mandar as fotos e os dados do Gol 2012 que a gente adianta a avaliação pelo WhatsApp. ||| E você pretende financiar ou pagar à vista?

---

## qa-c04 - Compra sem troca

- Status final: `NEW_LEAD`
- Score final: `16%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": false, "veiculo_troca": null, "motivo_troca": "Uso diário", "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": "FIAT 500 1.4 EVO FLEX CULT 2014", "motivo_handoff": null}`

### Interações

**1. Lead:** Sim, por gentileza

**1. Lucas:** Você vai comprar o Fiat 500 direto ou tem algum carro para dar na troca?

**2. Lead:** Para comprar, eu não tenho carro kkk

**2. Lucas:** Beleza, sem troca então. Você pensa em financiar ou vai pagar à vista?

**3. Lead:** Uso diário

**3. Lucas:** Financiamento ou à vista?

---

## qa-c05 - Pergunta financeira no meio do funil

- Status final: `NEW_LEAD`
- Score final: `16%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": "Uso diário", "precisa_financiamento": true, "e_local": null, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** Quero comprar

**1. Lucas:** Qual marca e modelo você está procurando para comprar?

**2. Lead:** Uso diário

**2. Lucas:** Você tem algum carro para dar na troca ou vai comprar direto?

**3. Lead:** Financiar

**3. Lucas:** Você tem veículo para dar na troca ou vai comprar direto?

**4. Lead:** Cartão, como que funciona?

**4. Lucas:** Aceitamos cartão, não tem problema. Você tem carro para dar na troca ou vai comprar direto?

---

## qa-c06 - Entrada financeira como primeira mensagem

- Status final: `QUALIFYING`
- Score final: `33%`
- Qualificação final: `{"status": "QUALIFYING", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": false, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": true, "e_local": null, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** Vcs financiam com 5 mil de entrada?

**1. Lucas:** Você vai comprar direto ou tem algum carro para dar na troca?

**2. Lead:** Pra comprar msm

**2. Lucas:** Certo, sem troca então. Você é de Joinville ou região?

---

## qa-c07 - Ambiguidade curta do lead

- Status final: `NEW_LEAD`
- Score final: `16%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": true, "veiculo_troca": "Siena", "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** Sim tenho um Siena 2010

**1. Lucas:** O que te fez querer trocar de carro agora?

**2. Lead:** Sim

**2. Lucas:** Qual a principal razão para trocar seu Siena 2010 agora?

**3. Lead:** Troca o Siena

**3. Lucas:** Qual ano/modelo completo do seu Siena para fazermos a avaliação certinha?

---

## qa-c08 - Mensagens quebradas em sequencia

- Status final: `NEW_LEAD`
- Score final: `16%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": false, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** Jumirim

**1. Lucas:** Não temos o Jumirim disponível no momento, mas essas opções estão disponíveis no nosso pátio: Jeep Renegade 2020 por R$73.900, Citroën C3 2010 por R$26.900, Renault Fluence 2012 por R$43.900, Chevrolet Onix 2015 por R$47.900 e Fiat 500 2014 por R$46.900. Você tem um carro para dar na troca ou vai comprar direto?

**2. Lead:** Sp

**2. Lucas:** Você pensa em comprar direto ou tem um carro para dar na troca?

---

## qa-c09 - Estoque indisponivel com sugestao similar

- Status final: `NEW_LEAD`
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": "Volkswagen Gol 1.0 Mi Total Flex 8V 4p 2012/2013", "motivo_handoff": null}`

### Interações

**1. Lead:** Queria um Gol

**1. Lucas:** Tem algum carro pra dar na troca ou vai comprar direto?

**2. Lead:** Vocês não têm nem outro Gol?

**2. Lucas:** Só temos esse Gol 2013 1.0 mecânico disponível. Você tem algum carro pra dar na troca ou vai comprar direto?

---

## qa-c10 - Consistencia de estoque

- Status final: `NEW_LEAD`
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": "FIAT 500 1.4 EVO FLEX CULT 2014", "motivo_handoff": null}`

### Interações

**1. Lead:** Sim, por gentileza

**1. Lucas:** Pra mandar as fotos certinho, você vai comprar direto ou tem algum carro para dar na troca?

**2. Lead:** Pode me mandar fotos?

**2. Lucas:** Pra eu te enviar as fotos do FIAT 500 CULT 1.4 FLEX 8V EVO MEC. 2014, você vai comprar direto ou tem veículo para dar na troca?

---

## qa-c11 - Disponibilidade objetiva

- Status final: `NEW_LEAD`
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": "Renault Clio Sedan 1.6 16v Expression Hi-flex 4p", "motivo_handoff": null}`

### Interações

**1. Lead:** Você tem o carro aí ou vendeu?

**1. Lucas:** O Renault Clio Sedan 1.6 16v Expression Hi-flex 4p não está mais disponível. Posso te mostrar opções similares que temos aqui na loja. Você vai comprar direto ou tem veículo para troca?

**2. Lead:** Gostaria de ver esse Renault Clio Sedan

**2. Lucas:** O Renault Clio Sedan 1.6 16v Expression Hi-flex 4p não está disponível no momento, mas tem o Renault Fluence Sedan Privilège 2012 automático por R$ 43.900. Você pensa em comprar direto ou tem algum carro para troca?

---

## qa-c12 - Dia sem horario

- Status final: `NEW_LEAD`
- Score final: `16%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": true, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** Sou de Joinville sim

**1. Lucas:** Você vai comprar direto ou tem algum veículo para dar na troca?

**2. Lead:** Posso ir segunda?

**2. Lucas:** Você vai comprar direto ou tem algum carro pra troca?

---

## qa-c13 - Horario indisponivel com alternativas

- Status final: `NEW_LEAD`
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** Posso passar aí às 17?

**1. Lucas:** Você pensa em comprar direto ou quer fazer uma troca?

---

## qa-c14 - Audio sem transcricao util

- Status final: `NEW_LEAD`
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** > Voice Note <

**1. Lucas:** Desculpa, não consegui escutar seu áudio agora 😅 Pode mandar por texto pra mim?

---

## qa-c15 - Lead responde fora de ordem

- Status final: `NEW_LEAD`
- Score final: `16%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": true, "e_local": null, "data_visita": null, "veiculo_interesse": "Volkswagen Gol 1.0 Mi Total Flex 8V 4p 2012/2013", "motivo_handoff": null}`

### Interações

**1. Lead:** Queria um Gol

**1. Lucas:** ✨ *VOLKSWAGEN GOL (NOVO) 1.0 MI TOTAL FLEX 8V 4P*
━━━━━━━━━━━━━━━━━━
📅 *Ano:* 2013
🕹️ *Câmbio:* Mecânico
🛣️ *KM:* 123.000 km
💰 *VALOR:* R$ 34.900
━━━━━━━━━━━━━━━━━━
[FOTO 1]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825091-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNyAoNCkuanBlZw.jpeg
[FOTO 2]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825221-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xNS5qcGVn.jpeg
[FOTO 3]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825275-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNSAoMSkuanBlZw.jpeg
[FOTO 4]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825429-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNSAoMikuanBlZw.jpeg
[FOTO 5]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825553-V2hhdHNBcHAgSW1hZ2UgMjAyNi0yMCBhdCAxNy4xOS4xNSAoNCkuanBlZw.jpeg
[FOTO 6]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825624-V2hhdHNBcHAgSW1hZ2UgMjAyNi0yMCBhdCAxNy4xOS4xNSAoMykuanBlZw.jpeg
[FOTO 7]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825707-V2hhdHNBcHAgSW1hZ2UgMjAyNi0yMCBhdCAxNy4xOS4xNiAoMykuanBlZw.jpeg
[FOTO 8]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825756-V2hhdHNBcHAgSW1hZ2UgMjAyNi0yMCBhdCAxNy4xOS4xNiAoMikuanBlZw.jpeg
[FOTO 9]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825877-V2hhdHNBcHAgSW1hZ2UgMjAyNi0yMCBhdCAxNy4xOS4xNyAoMSkuanBlZw.jpeg
[FOTO 10]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825987-V2hhdHNBcHAgSW1hZ2UgMjAyNi0yMCBhdCAxNy4xOS4xNiAoMSkuanBlZw.jpeg
Me conta, você tem algum carro para dar na troca ou vai comprar direto?

**2. Lead:** Financiar

**2. Lucas:** Você tem algum carro para dar na troca ou vai financiar o Gol direto?

**3. Lead:** Sou de Concórdia

**3. Lucas:** Você pensa em comprar direto o Gol ou tem algum carro para dar na troca?

**4. Lead:** Mas vocês têm mesmo?

**4. Lucas:** Temos sim, o Gol 2013 com 123 mil km por R$ 34.900 ||| Você vai comprar direto ou tem algum carro para dar na troca?

---

## qa-c16 - Pedido explicito de humano

- Status final: `NEW_LEAD`
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** Quero falar com um consultor

**1. Lucas:** Ok, vou transferir seu atendimento para um consultor humano pelo WhatsApp. Qualquer coisa, estamos aqui!

**2. Lead:** Prefiro atendimento humano

**2. Lucas:** Ok, vou transferir seu atendimento para um consultor humano pelo WhatsApp. Qualquer coisa, estamos aqui!

---
