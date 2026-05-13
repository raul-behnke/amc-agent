# Relatório de Execução - Bateria Lucas SDR

Gerado em: 2026-05-08 16:18:25
Fonte: `docs/qa/lucas-go-live-payloads-2026-05-08.json`

## qa-c01 - Interesse simples com agendamento valido

- Status final: `SCHEDULED`
- Score final: `33%`
- Qualificação final: `{"status": "SCHEDULED", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": true, "veiculo_troca": "Voyage 1998", "motivo_troca": "Quero algo mais econômico", "precisa_financiamento": true, "e_local": null, "data_visita": "2026-05-09T09:00:00", "veiculo_interesse": "Onix LT 1.4", "motivo_handoff": null}`

### Interações

**1. Lead:** Olá, pode sim!

**1. Lucas:** O Onix LT 1.4 é show! Você pensa em comprar direto ou tem um carro pra dar na troca?

**2. Lead:** Quero trocar meu Voyage 1998

**2. Lucas:** Qual ano/modelo completo é o seu Voyage? E o que te fez querer trocar de carro agora?Qual ano/modelo completo é o seu Voyage? E o que fez você querer trocar de carro agora?

**3. Lead:** Quero algo mais econômico

**3. Lucas:** Entendi, quer algo mais econômico mesmo. Você pretende financiar ou pagar à vista?
Aceitamos na troca sem problemas! Qual o ano/modelo completo do seu Voyage?

**4. Lead:** Vai ser financiado mesmo

**4. Lucas:** Trabalhamos com os principais bancos para facilitar seu financiamento. Você é de Joinville ou região?

**5. Lead:** Sou de Joinville

**5. Lucas:** Show! Quando fica bom pra você vir conhecer o Onix LT 1.4 na loja? A gente tá na Rua Iririu, Joinville.

**6. Lead:** Posso passar aí às 17?

**6. Lucas:** Não consegui acessar a agenda agora, mas me diga o melhor horário para você que eu reservo aqui com o pessoal!

**7. Lead:** Pode ser amanhã às 09:00 então

**7. Lucas:** Perfeito! Sua visita está agendada para amanhã às 09:00. Te esperamos na Rua Iririu, Joinville. Qualquer coisa, é só chamar. Até lá!

---

## qa-c02 - Troca com carro incompleto

- Status final: `NEW_LEAD`
- Score final: `16%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": true, "veiculo_troca": "Gol", "motivo_troca": "Motivação ainda não informada", "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": "Hyundai HB20", "motivo_handoff": null}`

### Interações

**1. Lead:** Oi, quero saber do HB20

**1. Lucas:** *1. HYUNDAI HB20 COMF./C.PLUS/C.STYLE 1.0 FLEX 12V*  
📅 2017 | 🕹️ Mecânico | 🛣️ 120.000 km  
💰 *R$ 48.900*  

*2. HYUNDAI HB20 EVOLUTION BLUELINK 1.0 FLEX 12V MEC*  
📅 2022 | 🕹️ Mecânico | 🛣️ 48.000 km  
💰 *R$ 66.900*  

*3. HYUNDAI HB20 COMF./C.PLUS/C.STYLE 1.0 FLEX 12V*  
📅 2017 | 🕹️ Mecânico | 🛣️ 110.000 km  
💰 *R$ 48.900*  

*4. HYUNDAI HB20 COMF./C.PLUS/C.STYLE 1.0 FLEX 12V*  
📅 2015 | 🕹️ Mecânico | 🛣️ 112.000 km  
💰 *R$ 47.900*  
Você pensa em comprar direto ou tem algum carro para dar na troca?

**2. Lead:** Tenho um Gol

**2. Lucas:** Qual ano/modelo completo do seu Gol? E o que te motivou a querer trocar de carro agora?Qual o ano/modelo completo do seu Gol?

---

## qa-c03 - Avaliacao por WhatsApp

- Status final: `NEW_LEAD`
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** Tenho um Gol 2012

**1. Lucas:** Você vai comprar o carro direto ou quer usar seu Gol 2012 na troca?

**2. Lead:** Dá pra avaliar por WhatsApp mesmo?

**2. Lucas:** Claro, a gente faz a avaliação pelo WhatsApp com fotos e dados do seu Gol. Me envia:  
• Fotos (frente, traseira, laterais e interior)  
• KM atual  
• Ano/modelo completo  
• Detalhes ou avarias  

Me confirma, você vai comprar direto ou quer usar o Gol na troca?

---

## qa-c04 - Compra sem troca

- Status final: `NEW_LEAD`
- Score final: `16%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": false, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": "FIAT 500 1.4 EVO FLEX CULT 2014", "motivo_handoff": null}`

### Interações

**1. Lead:** Sim, por gentileza

**1. Lucas:** Você vai comprar o Fiat 500 direto ou tem algum carro para dar na troca?

**2. Lead:** Para comprar, eu não tenho carro kkk

**2. Lucas:** Beleza, sem troca então. Você pensa em financiar ou vai pagar à vista?

**3. Lead:** Uso diário

**3. Lucas:** Uso diário pede uma opção prática, perfeito. Você vai financiar ou pagar à vista?

---

## qa-c05 - Pergunta financeira no meio do funil

- Status final: `NEW_LEAD`
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** Quero comprar

**1. Lucas:** Qual carro você está procurando? Tem alguma marca ou modelo específico em mente?

**2. Lead:** Uso diário

**2. Lucas:** Tá, você vai comprar direto ou tem algum carro pra dar na troca?

**3. Lead:** Financiar

**3. Lucas:** Você vai comprar direto ou tem algum carro pra dar na troca?

**4. Lead:** Cartão, como que funciona?

**4. Lucas:** Sim, aceitamos pagamento com cartão. Você vai comprar direto ou tem algum carro pra dar na troca?

---

## qa-c06 - Entrada financeira como primeira mensagem

- Status final: `NEW_LEAD`
- Score final: `16%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": true, "e_local": null, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** Vcs financiam com 5 mil de entrada?

**1. Lucas:** Você pensa em comprar ou tem algum carro para troca?

**2. Lead:** Pra comprar msm

**2. Lucas:** Você tem algum veículo para dar na troca ou vai comprar direto?

---

## qa-c07 - Ambiguidade curta do lead

- Status final: `NEW_LEAD`
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** Sim tenho um Siena 2010

**1. Lucas:** Não temos Siena agora, mas tenho essas opções aqui: 

*1. JEEP RENEGADE SPORT 1.8 4X2 FLEX 16V AUT.*
📅 2020 | 🕹️ Automático | 🛣️ 97.000 km
💰 *R$ 73.900*

*2. CITROËN C3 EXCL./EXCL.SOLAR./SONORA 1.6 FLEX AUT*
📅 2010 | 🕹️ Automático | 🛣️ 130.000 km
💰 *R$ 26.900*

*3. RENAULT FLUENCE SEDAN PRIVILÈGE 2.0 16V FLEX AUT*
📅 2012 | 🕹️ Automático | 🛣️ 128.000 km
💰 *R$ 43.900*

*4. CHEVROLET ONIX HATCH LT 1.4 8V FLEXPOWER 5P MEC.*
📅 2015 | 🕹️ Mecânico | 🛣️ 127.000 km
💰 *R$ 47.900*

*5. FIAT 500 CULT 1.4 FLEX 8V EVO MEC.*
📅 2014 | 🕹️ Mecânico | 🛣️ 79.000 km
💰 *R$ 46.900*

Você quer trocar seu Siena por algum desses?

**2. Lead:** Sim

**2. Lucas:** Você pretende fazer a troca do seu Siena ou vai comprar o carro direto?

**3. Lead:** Troca o Siena

**3. Lucas:** Pra te dar um valor mais assertivo na avaliação, me manda por favor:
• Fotos do carro (frente, traseira, laterais e interior)
• KM atual
• Ano/modelo completo
• Se tem algum detalhe ou avaria

Enquanto isso, você pensa em financiar ou comprar à vista?

---

## qa-c08 - Mensagens quebradas em sequencia

- Status final: `NEW_LEAD`
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** Jumirim

**1. Lucas:** Não temos o Jumirim disponível no momento, mas posso te mostrar algumas opções que estão no pátio da AMC Veículos: Jeep Renegade 2020, Citroën C3 2010, Renault Fluence 2012, Chevrolet Onix 2015 e Fiat 500 2014. Você pensa em comprar algum desses ou tem um carro para dar na troca?

**2. Lead:** Sp

**2. Lucas:** Você pensa em comprar algum veículo direto ou tem um carro para dar na troca?

---

## qa-c09 - Estoque indisponivel com sugestao similar

- Status final: `NEW_LEAD`
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": "Volkswagen Gol 1.0 Mi Total Flex 8V 4p 2012/2013", "motivo_handoff": null}`

### Interações

**1. Lead:** Queria um Gol

**1. Lucas:** ✨ VOLKSWAGEN GOL (NOVO) 1.0 MI TOTAL FLEX 8V 4P  
━━━━━━━━━━━━━━━━━━  
📅 Ano: 2013  
🕹️ Câmbio: Mecânico  
🛣️ KM: 123.000 km  
💰 VALOR: R$ 34.900  
━━━━━━━━━━━━━━━━━━  
[FOTO 1]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825091-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNyAoNCkuanBlZw.jpeg  
[FOTO 2]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825221-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNS5qcGVn.jpeg  
[FOTO 3]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825275-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNSAoMSkuanBlZw.jpeg  
[FOTO 4]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825429-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNSAoMikuanBlZw.jpeg  
[FOTO 5]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825553-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNSAoNCkuanBlZw.jpeg  
[FOTO 6]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825624-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNSAoMykuanBlZw.jpeg  
[FOTO 7]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825707-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNiAoMykuanBlZw.jpeg  
[FOTO 8]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825756-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNiAoMikuanBlZw.jpeg  
[FOTO 9]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825877-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNyAoMSkuanBlZw.jpeg  
[FOTO 10]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825987-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNiAoMSkuanBlZw.jpeg  

Você tem algum carro pra dar na troca ou vai comprar direto?

**2. Lead:** Vocês não têm nem outro Gol?

**2. Lucas:** No momento só temos esse Gol 2013 1.0 mecânico disponível. Você tem algum carro para dar na troca ou vai comprar direto?

---

## qa-c10 - Consistencia de estoque

- Status final: `NEW_LEAD`
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": "FIAT 500 1.4 EVO FLEX CULT 2014", "motivo_handoff": null}`

### Interações

**1. Lead:** Sim, por gentileza

**1. Lucas:** *1. FIAT 500 CULT 1.4 FLEX 8V EVO MEC.*
📅 2014 | 🕹️ Mecânico | 🛣️ 79.000 km
💰 *R$ 46.900*

Quer comprar direto ou tem algum carro para dar na troca?

**2. Lead:** Pode me mandar fotos?

**2. Lucas:** Pra te passar as fotos do FIAT 500 CULT 1.4 FLEX 8V EVO MEC. 2014, só confirmando: você pensa em comprar direto ou tem um carro para dar na troca?

---

## qa-c11 - Disponibilidade objetiva

- Status final: `NEW_LEAD`
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": "Renault Clio Sedan 1.6 16v Expression Hi-flex 4p", "motivo_handoff": null}`

### Interações

**1. Lead:** Você tem o carro aí ou vendeu?

**1. Lucas:** O Renault Clio Sedan 1.6 16v Expression Hi-flex 4p não está disponível no momento. Posso te mostrar outros modelos semelhantes, como o Renault Fluence Sedan Privilège 2012 automático por R$ 43.900. Você pensa em comprar direto ou tem algum carro para dar na troca?

**2. Lead:** Gostaria de ver esse Renault Clio Sedan

**2. Lucas:** O Renault Clio Sedan que você quer não está disponível agora, mas tem o Renault Fluence Sedan Privilège 2012 automático por R$ 43.900. Você vai comprar direto ou tem algum carro para troca?

---

## qa-c12 - Dia sem horario

- Status final: `NEW_LEAD`
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** Sou de Joinville sim

**1. Lucas:** Você pensa em comprar o carro direto ou tem algum veículo pra dar na troca?

**2. Lead:** Posso ir segunda?

**2. Lucas:** Antes de combinar, me fala se você vai comprar direto ou tem algum carro pra troca?

---

## qa-c13 - Horario indisponivel com alternativas

- Status final: `NEW_LEAD`
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** Posso passar aí às 17?

**1. Lucas:** Você pensa em comprar direto ou tem algum carro para dar na troca?

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
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": "Volkswagen Gol 1.0 Mi Total Flex 8V 4p 2012/2013", "motivo_handoff": null}`

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
[FOTO 5]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825553-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNSAoNCkuanBlZw.jpeg
[FOTO 6]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825624-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNSAoMykuanBlZw.jpeg
[FOTO 7]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825707-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNiAoMykuanBlZw.jpeg
[FOTO 8]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825756-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNiAoMikuanBlZw.jpeg
[FOTO 9]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825877-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNyAoMSkuanBlZw.jpeg
[FOTO 10]: https://www.socarrao.com.br/sc-vehicle-images-prod/1017634/1776777825987-V2hhdHNBcHAgSW1hZ2UgMjAyNi0wNC0yMCBhdCAxNy4xOS4xNiAoMSkuanBlZw.jpeg
Me conta, você tem algum carro para dar na troca ou vai comprar direto?

**2. Lead:** Financiar

**2. Lucas:** Me conta, você tem algum carro para dar na troca ou vai financiar só a compra?

**3. Lead:** Sou de Concórdia

**3. Lucas:** Você tem algum carro para troca ou vai comprar direto o Gol?

**4. Lead:** Mas vocês têm mesmo?

**4. Lucas:** Sim, temos o Gol 2013 mecânico com 123.000 km por R$ 34.900 ||| Você pensa em comprar direto ou tem algum carro para dar na troca?

---

## qa-c16 - Pedido explicito de humano

- Status final: `NEW_LEAD`
- Score final: `0%`
- Qualificação final: `{"status": "NEW_LEAD", "nome": null, "tipo_veiculo": null, "marca_preferida": null, "modelo_preferido": null, "faixa_preco": null, "ano_minimo": null, "cambio": null, "tem_troca": null, "veiculo_troca": null, "motivo_troca": null, "precisa_financiamento": null, "e_local": null, "data_visita": null, "veiculo_interesse": null, "motivo_handoff": null}`

### Interações

**1. Lead:** Quero falar com um consultor

**1. Lucas:** Você pensa em comprar o carro direto ou tem algum veículo para dar na troca?

**2. Lead:** Prefiro atendimento humano

**2. Lucas:** Posso continuar te atendendo aqui rapidinho pra agilizar? Você está pensando em comprar direto ou tem um carro para troca?

---
