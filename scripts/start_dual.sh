#!/bin/bash

# Script para iniciar o servidor Better Seconds Record em modo DUAL (HTTP + HTTPS)
# HTTP: porta 5000
# HTTPS: porta 5443

cd /home/pi/app

echo "🚀 Iniciando Better Seconds Record Server - Modo Dual (HTTP + HTTPS)..."

# Verifica se os certificados SSL existem
if [ ! -f "/home/pi/app/ssl/server.crt" ] || [ ! -f "/home/pi/app/ssl/server.key" ]; then
    echo "⚠️  Certificados SSL não encontrados. Gerando..."
    bash /home/pi/app/scripts/generate_ssl_cert.sh
fi

# Ativa o ambiente virtual
source .venv/bin/activate

# Para processos antigos se existirem
pkill -f "gunicorn.*capture3:app" 2>/dev/null
sleep 2

# Inicia HTTP em background (porta 5000)
echo "🌐 Iniciando servidor HTTP na porta 5000..."
gunicorn --config gunicorn_config.py capture3:app &
HTTP_PID=$!

sleep 3

# Inicia HTTPS em background (porta 5443)
echo "🔐 Iniciando servidor HTTPS na porta 5443..."
gunicorn --config gunicorn_config_https.py capture3:app &
HTTPS_PID=$!

echo ""
echo "✅ Servidores iniciados com sucesso!"
echo "   HTTP:  http://0.0.0.0:5000"
echo "   HTTPS: https://0.0.0.0:5443"
echo ""
echo "   PIDs: HTTP=$HTTP_PID HTTPS=$HTTPS_PID"
echo ""
echo "Para parar: pkill -f 'gunicorn.*capture3:app'"

# Aguarda os processos
wait
