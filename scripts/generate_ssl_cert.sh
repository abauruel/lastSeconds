#!/bin/bash

# Script para gerar certificados SSL auto-assinados
# Para uso em ambiente de produção local/embedded

SSL_DIR="/home/pi/app/ssl"
CERT_FILE="$SSL_DIR/server.crt"
KEY_FILE="$SSL_DIR/server.key"

echo "🔐 Gerando certificados SSL auto-assinados..."

# Cria diretório SSL se não existir
mkdir -p "$SSL_DIR"

# Gera certificado auto-assinado válido por 365 dias
openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -days 365 \
    -subj "/C=BR/ST=State/L=City/O=Organization/OU=IT/CN=raspberrypi.local" \
    -addext "subjectAltName=DNS:raspberrypi.local,DNS:localhost,IP:192.168.1.187,IP:10.42.0.1,IP:192.168.0.1,IP:127.0.0.1"

# Ajusta permissões
chmod 644 "$CERT_FILE"
chmod 600 "$KEY_FILE"

echo "✅ Certificados SSL gerados com sucesso!"
echo "   Certificado: $CERT_FILE"
echo "   Chave privada: $KEY_FILE"
echo ""
echo "⚠️  Nota: Certificados auto-assinados não são confiáveis por padrão"
echo "   Navegadores mostrarão aviso de segurança (normal para desenvolvimento)"
