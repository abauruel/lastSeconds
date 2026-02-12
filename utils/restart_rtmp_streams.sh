#!/bin/bash
# Script para forçar reconexão dos streams RTMP ao MediaMTX

echo "🔄 Reiniciando streams RTMP..."
echo ""

# Para o serviço de gravação (que inclui o RTMP)
echo "1. Parando serviço de gravação..."
sudo systemctl stop better_seconds_record.service
sleep 2

# Limpa conexões RTMP antigas (caso existam)
echo "2. Limpando conexões antigas..."
pkill -f "rtmp://localhost/live/" 2>/dev/null
sleep 1

# Reinicia MediaMTX para limpar estados
echo "3. Reiniciando MediaMTX..."
sudo systemctl restart mediamtx 2>/dev/null || sudo pkill -HUP mediamtx
sleep 2

# Limpa arquivos HLS antigos
echo "4. Limpando cache HLS..."
rm -f /tmp/live_stream*.m3u8 /tmp/live_stream*.ts 2>/dev/null

# Reinicia serviço de gravação (que vai reconectar ao RTMP)
echo "5. Iniciando serviço de gravação..."
sudo systemctl start better_seconds_record.service
sleep 3

echo ""
echo "✅ Reinício completo!"
echo ""
echo "Aguarde 5-10 segundos para os streams se estabilizarem..."
echo ""

# Aguarda um pouco
sleep 5

# Verifica status
echo "Verificando status..."
./check_streaming.sh
