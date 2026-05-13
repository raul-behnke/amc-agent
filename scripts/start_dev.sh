#!/bin/bash

# ZAF — Dev Sandbox Script
# Inicia o servidor local e expõe via Ngrok para testes com o GHL.

echo "🚀 Iniciando ZOI Agent Framework em modo Sandbox..."

# 1. Ativar ambiente virtual
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Venv não encontrada. Por favor, crie o ambiente virtual primeiro."
    exit 1
fi

# 2. Iniciar o servidor FastAPI em background
echo "📡 Iniciando servidor FastAPI na porta 8000..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
SERVER_PID=$!

# 3. Iniciar o Ngrok
echo "🔗 Iniciando túnel Ngrok..."
ngrok http 8000 --log=stdout > /dev/null &
NGROK_PID=$!

# Esperar o ngrok subir
sleep 3

# 4. Obter a URL do Ngrok
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^"]*\.ngrok-free.app')

if [ -z "$NGROK_URL" ]; then
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^"]*\.ngrok.io')
fi

echo ""
echo "✅ Ambiente Sandbox Pronto!"
echo "----------------------------------------------------------------"
echo "🌐 URL Pública do Webhook:"
echo "👉 $NGROK_URL/webhook/chat"
echo "----------------------------------------------------------------"
echo "📝 Logs do servidor disponíveis em: server.log"
echo "⚠️  Lembre-se de configurar a tag '$(grep GHL_REQUIRED_TAG .env | cut -d '=' -f2)' no seu contato de teste no GHL."
echo "----------------------------------------------------------------"
echo "Pressione [CTRL+C] para encerrar o ambiente."

# Manter o script rodando e limpar ao sair
trap "kill $SERVER_PID $NGROK_PID; echo '🛑 Ambiente encerrado.'; exit" INT
wait
