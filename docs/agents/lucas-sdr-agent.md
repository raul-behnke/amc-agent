# Arquitetura: Lucas SDR Agent (AMC Veículos)

## Visão Geral
O Lucas SDR Agent atua como o primeiro contato comercial na AMC Veículos, focado em qualificação de leads, engajamento e agendamento de visitas na loja. Ele opera dentro do ZOI Agent Framework, utilizando a memória persistente e conectando-se ao CRM da loja (GoHighLevel/etc).

## Objetivos do Agente
1. Responder rapidamente aos leads recebidos.
2. Qualificar os leads usando parâmetros pré-definidos (interesse, orçamento, intenção de compra).
3. Consultar o estoque de veículos em tempo real (via tool).
4. Agendar a visita presencial do lead na concessionária.
5. Realizar o handoff (transferência) para um vendedor humano quando necessário.

## Componentes Arquiteturais

### 1. Prompts (Contexto & Personalidade)
- **Persona:** Lucas, um consultor automotivo amigável, direto e focado na jornada do cliente.
- **Tom de Voz:** "WhatsApp Native" – natural, sem repetições robóticas, consultivo.
- **Instruções Dinâmicas:** Alimentadas pelo `project-context.md` e regras de negócio específicas da AMC Veículos.

### 2. Tools (Ferramentas)
As ferramentas (tools) que o agente pode utilizar:
- `consultar_estoque(modelo, ano)`: Busca informações atualizadas no inventário.
- `verificar_disponibilidade_agenda(data, hora)`: Checa horários livres para visita.
- `agendar_visita(lead_id, data, hora)`: Confirma o agendamento no sistema.
- `atualizar_crm(lead_id, dados_qualificacao)`: Registra as respostas de qualificação.
- `acionar_handoff_humano(motivo)`: Passa a conversa para um vendedor real.

### 3. Memória (State & History)
- **Short-Term Memory:** Histórico imediato da conversa via Agno e Redis (para respostas em tempo real).
- **Long-Term Memory:** Atualizações gravadas no PostgreSQL / CRM para manter o estado do lead ao longo dos dias (ex: lead já disse que tem veículo para troca).

### 4. Fluxo (State Machine)
O agente operará baseado em estados da qualificação:
1. `NEW_LEAD`: Saudação inicial e identificação de interesse.
2. `QUALIFYING`: Coleta de informações (modelo desejado, troca de carro, financiamento).
3. `SCHEDULING`: Tentativa de agendamento de visita.
4. `HANDOFF`: Acionado em caso de dúvidas complexas, negociação de valores ou sucesso no agendamento.

## Próximos Passos
- Implementar as Tools iniciais de consulta de estoque e CRM.
- Esboçar o workflow de orquestração no runtime do FastAPI.
