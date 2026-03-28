#!/bin/bash
# Script para desabilitar autosuspensão USB nas webcams
# Evita desconexões causadas por economia de energia

echo "🔧 Desabilitando autosuspensão USB..."

# Desabilita para todas as portas USB
for device in /sys/bus/usb/devices/*/power/control; do
    if [ -f "$device" ]; then
        echo 'on' > "$device" 2>/dev/null
        port=$(echo $device | grep -oP '(\d+-\d+\.\d+)')
        if [ -n "$port" ]; then
            echo "  ✓ Porta $port: autosuspensão desabilitada"
        fi
    fi
done

echo "✅ Configuração aplicada"

exit 0
