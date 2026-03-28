#!/bin/bash

# Script de monitoramento de saúde USB para detectar desconexões
# Uso: ./monitor_usb_health.sh

LOG_DIR="/home/pi/app/logs"
LOG_FILE="$LOG_DIR/usb_health.log"
ALERT_FILE="$LOG_DIR/usb_alerts.log"

mkdir -p "$LOG_DIR"

echo "====================================="
echo "🔍 Monitor de Saúde USB"
echo "====================================="
echo ""

# Função para logar com timestamp
log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Função para alertar
alert_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🚨 ALERTA: $1" | tee -a "$ALERT_FILE"
}

# Verifica dispositivos USB atuais
echo "📊 Status Atual das Câmeras:"
echo ""

# Lista dispositivos
v4l2-ctl --list-devices 2>/dev/null | grep -A2 "usb-webcam"

echo ""
echo "📍 Portas USB em uso:"
lsusb | grep "2bc5:0529"

echo ""
echo "⚡ Status de energia USB:"
for device in /sys/bus/usb/devices/1-1.*/power/control; do
    if [ -f "$device" ]; then
        port=$(echo $device | grep -oP '1-1\.\d+')
        status=$(cat $device)
        echo "  Porta $port: $status"
    fi
done

echo ""
echo "📈 Histórico de Desconexões (últimas 24h):"
echo ""

# Conta desconexões por porta
disconnect_count_1_3=$(dmesg | grep "USB disconnect" | grep "1-1.3" | wc -l)
disconnect_count_1_4=$(dmesg | grep "USB disconnect" | grep "1-1.4" | wc -l)

echo "  Porta 1-1.3 (Stream1): $disconnect_count_1_3 desconexões"
echo "  Porta 1-1.4 (Stream2): $disconnect_count_1_4 desconexões"

if [ $disconnect_count_1_4 -gt 5 ]; then
    alert_msg "Stream2 (porta 1-1.4) teve $disconnect_count_1_4 desconexões! AÇÃO NECESSÁRIA!"
    echo ""
    echo "⚠️  PROBLEMA DETECTADO: Stream2 está desconectando frequentemente!"
    echo "    → Veja FIX_STREAM2_DISCONNECT.md para soluções"
fi

echo ""
echo "🕒 Últimas 5 desconexões da Stream2:"
dmesg | grep "USB disconnect" | grep "1-1.4" | tail -5

echo ""
echo "====================================="
echo "📊 Estatísticas de Arquivos Gravados"
echo "====================================="
echo ""

# Stream1
stream1_dir="/dev/shm/bts/stream1"
if [ -d "$stream1_dir" ]; then
    stream1_files=$(ls -1 "$stream1_dir" | wc -l)
    stream1_latest=$(ls -1t "$stream1_dir" | head -1)
    if [ -n "$stream1_latest" ]; then
        stream1_age=$(($(date +%s) - $(stat -c %Y "$stream1_dir/$stream1_latest")))
        echo "✅ Stream1: $stream1_files arquivos, último há ${stream1_age}s"
    else
        echo "⚠️  Stream1: Sem arquivos!"
    fi
else
    echo "❌ Stream1: Diretório não existe"
fi

# Stream2
stream2_dir="/dev/shm/bts/stream2"
if [ -d "$stream2_dir" ]; then
    stream2_files=$(ls -1 "$stream2_dir" | wc -l)
    stream2_latest=$(ls -1t "$stream2_dir" | head -1)
    if [ -n "$stream2_latest" ]; then
        stream2_age=$(($(date +%s) - $(stat -c %Y "$stream2_dir/$stream2_latest")))
        if [ $stream2_age -gt 120 ]; then
            echo "❌ Stream2: $stream2_files arquivos, último há ${stream2_age}s (PROBLEMA!)"
            alert_msg "Stream2 não está gravando! Último arquivo há ${stream2_age}s"
        else
            echo "✅ Stream2: $stream2_files arquivos, último há ${stream2_age}s"
        fi
    else
        echo "⚠️  Stream2: Sem arquivos!"
        alert_msg "Stream2 sem arquivos!"
    fi
else
    echo "❌ Stream2: Diretório não existe"
fi

echo ""
echo "====================================="
echo "🌡️  Status do Sistema"
echo "====================================="
echo ""

# Temperatura
temp=$(vcgencmd measure_temp | grep -oP '\d+\.\d+')
echo "Temperatura CPU: ${temp}°C"

if (( $(echo "$temp > 70" | bc -l) )); then
    alert_msg "Temperatura alta: ${temp}°C"
    echo "⚠️  ALERTA: Temperatura acima de 70°C!"
fi

# Throttling
throttled=$(vcgencmd get_throttled | grep -oP '0x\w+')
if [ "$throttled" != "0x0" ]; then
    alert_msg "Sistema throttled: $throttled (problema de energia!)"
    echo "⚠️  ALERTA: Sistema com throttling! Verifique fonte de alimentação"
fi

echo ""
echo "====================================="
echo "💡 Recomendações"
echo "====================================="
echo ""

if [ $disconnect_count_1_4 -gt 5 ]; then
    echo "🔧 AÇÃO RECOMENDADA:"
    echo "   1. Trocar câmera da stream2 para outra porta USB"
    echo "   2. Usar hub USB powered com alimentação externa"
    echo "   3. Verificar cabo USB da câmera"
    echo ""
    echo "   Veja detalhes em: FIX_STREAM2_DISCONNECT.md"
fi

if [ $disconnect_count_1_3 -gt 5 ]; then
    echo "⚠️  Stream1 também está com desconexões - problema geral de USB!"
    echo "   → Verificar fonte de alimentação do Raspberry Pi"
    echo "   → Considerar hub USB powered para ambas as câmeras"
fi

echo ""
log_msg "Verificação de saúde USB concluída"

exit 0
