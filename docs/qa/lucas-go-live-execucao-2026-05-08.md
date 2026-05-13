# Execução da Bateria - Lucas SDR - Pré GO-LIVE

Arquivo principal da bateria: [lucas-go-live-bateria-2026-05-08.md](/Users/raulbehnke/Documents/amc-agno/docs/qa/lucas-go-live-bateria-2026-05-08.md:1)

Payloads base: [lucas-go-live-payloads-2026-05-08.json](/Users/raulbehnke/Documents/amc-agno/docs/qa/lucas-go-live-payloads-2026-05-08.json:1)

## Objetivo

Padronizar a execução manual dos cenários de QA usando o webhook local e a consulta de qualificação do lead.

## Pré-requisitos

- API rodando em `http://127.0.0.1:8000`
- Sessões novas para cada cenário
- Leitura do estado via `GET /leads/{session_id}/qualification`

## Rotas úteis

- `POST /webhook/chat`
- `GET /leads/{session_id}/qualification`
- `GET /health`

## Sanidade inicial

```bash
curl -s http://127.0.0.1:8000/health
```

Esperado:

```json
{"status":"ok","framework":"ZOI Agent Framework","version":"0.1.0"}
```

## Formato do payload

Use sempre este formato mínimo:

```json
{
  "session_id": "qa-c01",
  "message": "Texto do lead"
}
```

Observação:
- Para testes locais sem GHL, use `session_id`.
- O webhook aceita `message`, `body` ou `text`.

## Comandos padrão

Enviar uma mensagem:

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"qa-c01","message":"Olá, pode sim!"}'
```

Consultar estado da sessão:

```bash
curl -sS http://127.0.0.1:8000/leads/qa-c01/qualification
```

## Ordem recomendada

1. Cenários 01 a 04
2. Cenários 05 a 08
3. Cenários 09 a 12
4. Cenários 13 a 16

## Roteiro de execução por cenário

### Cenário 01

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c01","message":"Olá, pode sim!"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c01","message":"Quero trocar meu Voyage 1998"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c01","message":"Quero algo mais econômico"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c01","message":"Vai ser financiado mesmo"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c01","message":"Sou de Joinville"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c01","message":"Posso passar aí às 17?"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c01","message":"Pode ser amanhã às 09:00 então"}'
curl -sS http://127.0.0.1:8000/leads/qa-c01/qualification
```

### Cenário 02

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c02","message":"Oi, quero saber do HB20"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c02","message":"Tenho um Gol"}'
curl -sS http://127.0.0.1:8000/leads/qa-c02/qualification
```

### Cenário 03

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c03","message":"Tenho um Gol 2012"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c03","message":"Dá pra avaliar por WhatsApp mesmo?"}'
curl -sS http://127.0.0.1:8000/leads/qa-c03/qualification
```

### Cenário 04

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c04","message":"Sim, por gentileza"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c04","message":"Para comprar, eu não tenho carro kkk"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c04","message":"Uso diário"}'
curl -sS http://127.0.0.1:8000/leads/qa-c04/qualification
```

### Cenário 05

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c05","message":"Quero comprar"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c05","message":"Uso diário"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c05","message":"Financiar"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c05","message":"Cartão, como que funciona?"}'
curl -sS http://127.0.0.1:8000/leads/qa-c05/qualification
```

### Cenário 06

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c06","message":"Vcs financiam com 5 mil de entrada?"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c06","message":"Pra comprar msm"}'
curl -sS http://127.0.0.1:8000/leads/qa-c06/qualification
```

### Cenário 07

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c07","message":"Sim tenho um Siena 2010"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c07","message":"Sim"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c07","message":"Troca o Siena"}'
curl -sS http://127.0.0.1:8000/leads/qa-c07/qualification
```

### Cenário 08

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c08","message":"Jumirim"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c08","message":"Sp"}'
curl -sS http://127.0.0.1:8000/leads/qa-c08/qualification
```

### Cenário 09

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c09","message":"Queria um Gol"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c09","message":"Vocês não têm nem outro Gol?"}'
curl -sS http://127.0.0.1:8000/leads/qa-c09/qualification
```

### Cenário 10

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c10","message":"Sim, por gentileza"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c10","message":"Pode me mandar fotos?"}'
curl -sS http://127.0.0.1:8000/leads/qa-c10/qualification
```

### Cenário 11

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c11","message":"Você tem o carro aí ou vendeu?"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c11","message":"Gostaria de ver esse Renault Clio Sedan"}'
curl -sS http://127.0.0.1:8000/leads/qa-c11/qualification
```

### Cenário 12

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c12","message":"Sou de Joinville sim"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c12","message":"Posso ir segunda?"}'
curl -sS http://127.0.0.1:8000/leads/qa-c12/qualification
```

### Cenário 13

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c13","message":"Posso passar aí às 17?"}'
curl -sS http://127.0.0.1:8000/leads/qa-c13/qualification
```

### Cenário 14

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c14","message":"> Voice Note <"}'
curl -sS http://127.0.0.1:8000/leads/qa-c14/qualification
```

### Cenário 15

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c15","message":"Queria um Gol"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c15","message":"Financiar"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c15","message":"Sou de Concórdia"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c15","message":"Mas vocês têm mesmo?"}'
curl -sS http://127.0.0.1:8000/leads/qa-c15/qualification
```

### Cenário 16

```bash
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c16","message":"Quero falar com um consultor"}'
curl -sS -X POST http://127.0.0.1:8000/webhook/chat -H 'Content-Type: application/json' -d '{"session_id":"qa-c16","message":"Prefiro atendimento humano"}'
curl -sS http://127.0.0.1:8000/leads/qa-c16/qualification
```

## Registro de evidências

Para cada cenário, registrar:

- Texto exato das respostas
- Estado final do lead
- Se houve erro de fluxo
- Se houve necessidade de handoff
- Se houve tentativa real de agendamento

## Saída esperada da rodada

- Atualização do arquivo da bateria com `Passou`, `Falhou` ou `Parcial`
- Lista consolidada de bugs para correção pré GO-LIVE
