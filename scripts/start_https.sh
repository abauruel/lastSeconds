#!/bin/bash

# Script para iniciar o servidor Better Seconds Record em modo HTTPS
# Porta: 5443

cd /home/pi/app

echo "🔐 Iniciando Better Seconds Record HTTPS Server..."

# Verifica se os certificados SSL existem
if [ ! -f "/home/pi/app/ssl/server.crt" ] || [ ! -f "/home/pi/app/ssl/server.key" ]; then
    echo "⚠️  Certificados SSL não encontrados. Gerando..."
    bash /home/pi/app/scripts/generate_ssl_cert.sh
fi

# Ativa o ambiente virtual
source .venv/bin/activate

# Inicia o Gunicorn com HTTPS
exec gunicorn --config gunicorn_config_https.py capture3:app
