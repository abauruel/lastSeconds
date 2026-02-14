#!/bin/bash

# Script de monitoramento contínuo de desconexões USB
# Monitora em tempo real e loga desconexões

LOG_FILE="/home/pi/app/logs/usb_disconnect_monitor.log"
mkdir -p /home/pi/app/logs

echo "========================================="
echo "🔍 Monitoramento Contínuo de USB"
echo "========================================="
echo "Pressione Ctrl+C para sair"
echo ""
echo "Monitorando desconexões das câmeras..."
echo "Logs salvos em: $LOG_FILE"
echo ""

# Marca inicial no dmesg
last_line=$(dmesg | wc -l)

while true; do
    # Pega novas linhas do dmesg
    current_line=$(dmesg | wc -l)
    
    if [ $current_line -gt $last_line ]; then
        # Verifica novas linhas por desconexões
        new_logs=$(dmesg | tail -n $((current_line - last_line)))
        
        # Procura por desconexões USB das webcams
        disconnect_1_3=$(echo "$new_logs" | grep "usb 1-1.3: USB disconnect")
        disconnect_1_4=$(echo "$new_logs" | grep "usb 1-1.4: USB disconnect")
        
        if [ -n "$disconnect_1_3" ]; then
            timestamp=$(date '+%Y-%m-%d %H:%M:%S')
            echo "[$timestamp] 🚨 STREAM1 DESCONECTOU (porta 1-1.3)" | tee -a "$LOG_FILE"
            
            # Alerta visual
            echo ""
            echo "╔════════════════════════════════════════╗"
            echo "║  ⚠️  ALERTA: STREAM1 DESCONECTOU!      ║"
            echo "║  Câmera na porta 1-1.3                 ║"
            echo "╚════════════════════════════════════════╝"
            echo ""
        fi
        
        if [ -n "$disconnect_1_4" ]; then
            timestamp=$(date '+%Y-%m-%d %H:%M:%S')
            echo "[$timestamp] 🚨 STREAM2 DESCONECTOU (porta 1-1.4)" | tee -a "$LOG_FILE"
            
            # Alerta visual
            echo ""
            echo "╔════════════════════════════════════════╗"
            echo "║  🔴 ALERTA: STREAM2 DESCONECTOU!       ║"
            echo "║  Câmera na porta 1-1.4                 ║"
            echo "║  AÇÃO: Ver FIX_STREAM2_DISCONNECT.md   ║"
            echo "╚════════════════════════════════════════╝"
            echo ""
        fi
        
        last_line=$current_line
    fi
    
    sleep 2
done
