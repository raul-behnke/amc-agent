# Regras Arquiteturais

## Princípios

- Toda lógica deve ser desacoplada.
- O CRM não contém inteligência.
- O agente toma decisões.
- Tools são reutilizáveis.
- Estado é centralizado.
- Prompts não contêm regras de negócio rígidas.

## Regras

- Nunca acessar APIs diretamente fora de services/
- Toda integração deve possuir adapter
- Toda tool deve ser stateless
- Toda memória deve ser persistível
- Todo agente deve possuir:
  - prompt
  - tools
  - memory
  - state
