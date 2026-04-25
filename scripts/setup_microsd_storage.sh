#!/bin/bash
# Script para configurar o armazenamento no microSD
# Este script cria a estrutura de diretórios necessária para as gravações

echo "========================================="
echo "Configuração de Armazenamento no microSD"
echo "========================================="
echo ""

# Define o diretório base no microSD
BASE_DIR="/home/pi/recordings"

echo "🗂️  Criando estrutura de diretórios em: $BASE_DIR"
echo ""

# Cria a estrutura de diretórios
mkdir -p "$BASE_DIR/buffers/video0"
mkdir -p "$BASE_DIR/buffers/video2"
mkdir -p "$BASE_DIR/recordings"
mkdir -p "$BASE_DIR/streams"
mkdir -p "$BASE_DIR/stream1"
mkdir -p "$BASE_DIR/stream2"

# Configura permissões adequadas
chmod -R 755 "$BASE_DIR"

echo "✅ Diretórios criados:"
echo "   - $BASE_DIR/buffers/video0"
echo "   - $BASE_DIR/buffers/video2"
echo "   - $BASE_DIR/recordings"
echo "   - $BASE_DIR/streams"
echo "   - $BASE_DIR/stream1"
echo "   - $BASE_DIR/stream2"
echo ""

# Verifica o espaço disponível
echo "💾 Espaço disponível no microSD:"
df -h /home/pi | grep -E "Filesystem|/dev/root"
echo ""

# Calcula o espaço que será usado com segmentos de 3 minutos
echo "📊 Estimativa de uso com segmentos de 3 minutos:"
echo "   - Bitrate estimado: ~2 Mbps por câmera"
echo "   - Tamanho por segmento (3 min): ~45 MB"
echo "   - 2 câmeras: ~90 MB a cada 3 minutos"
echo "   - 1 hora de gravação: ~1.8 GB"
echo "   - 1 dia completo (24h): ~43.2 GB"
echo ""

# Verifica se há espaço suficiente
AVAILABLE_GB=$(df -BG /home/pi | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "$AVAILABLE_GB" -lt 50 ]; then
    echo "⚠️  ATENÇÃO: Espaço disponível ($AVAILABLE_GB GB) pode ser insuficiente"
    echo "   Recomendado: Pelo menos 50 GB livres"
else
    echo "✅ Espaço disponível adequado: $AVAILABLE_GB GB"
fi
echo ""

echo "========================================="
echo "✅ Configuração concluída!"
echo "========================================="
echo ""
echo "Próximos passos:"
echo "1. Reinicie o serviço de captura: sudo systemctl restart capture3_https"
echo "2. Verifique o status: sudo systemctl status capture3_https"
echo "3. Monitore os logs: journalctl -u capture3_https -f"
echo ""
echo "IMPORTANTE:"
echo "- As gravações agora são armazenadas em: $BASE_DIR"
echo "- Cada segmento tem duração de 3 minutos (antes era 1 minuto)"
echo "- Certifique-se de ter espaço suficiente no microSD"
echo ""
