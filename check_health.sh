#!/bin/bash
# Script de monitoramento da saúde da aplicação de gravação

echo "=================================================="
echo "🏥 STATUS DE SAÚDE DA APLICAÇÃO DE GRAVAÇÃO"
echo "=================================================="
echo ""

# 1. Status do serviço
echo "📋 1. STATUS DO SERVIÇO"
echo "----------------------------------------"
systemctl status better_seconds_record.service --no-pager | head -15
echo ""

# 2. Processos FFmpeg
echo "📹 2. PROCESSOS FFMPEG ATIVOS"
echo "----------------------------------------"
FFMPEG_COUNT=$(ps aux | grep ffmpeg | grep -E "(video0|video2)" | grep -v grep | wc -l)
echo "Processos FFmpeg ativos: $FFMPEG_COUNT"
if [ $FFMPEG_COUNT -eq 2 ]; then
    echo "✅ Ambos os processos FFmpeg estão rodando"
elif [ $FFMPEG_COUNT -eq 1 ]; then
    echo "⚠️  Apenas 1 processo FFmpeg está rodando"
elif [ $FFMPEG_COUNT -eq 0 ]; then
    echo "❌ Nenhum processo FFmpeg está rodando!"
else
    echo "⚠️  Número inesperado de processos: $FFMPEG_COUNT"
fi
echo ""
ps aux | grep ffmpeg | grep -E "(video0|video2)" | grep -v grep | awk '{print $11, $12, $13, $14, $15, $16, $17, $18}' | head -2
echo ""

# 3. Processos Zumbis
echo "🧟 3. PROCESSOS ZUMBIS"
echo "----------------------------------------"
ZOMBIE_COUNT=$(ps aux | grep defunct | grep -v grep | wc -l)
if [ $ZOMBIE_COUNT -eq 0 ]; then
    echo "✅ Nenhum processo zumbi detectado"
else
    echo "⚠️  $ZOMBIE_COUNT processos zumbis encontrados:"
    ps aux | grep defunct | grep -v grep
fi
echo ""

# 4. Últimos arquivos gravados - Stream1
echo "📁 4. ÚLTIMOS ARQUIVOS GRAVADOS - STREAM1"
echo "----------------------------------------"
STREAM1_DIR="/media/pi/usb64gb/bts/stream1"
if [ -d "$STREAM1_DIR" ]; then
    LATEST1=$(ls -t "$STREAM1_DIR"/video0_*.mp4 2>/dev/null | head -1)
    if [ -n "$LATEST1" ]; then
        FILE_AGE=$(( $(date +%s) - $(stat -c %Y "$LATEST1") ))
        FILE_SIZE=$(stat -c %s "$LATEST1")
        echo "Último arquivo: $(basename "$LATEST1")"
        echo "Tamanho: $(numfmt --to=iec-i --suffix=B $FILE_SIZE)"
        echo "Idade: ${FILE_AGE}s"
        
        if [ $FILE_AGE -lt 120 ]; then
            echo "✅ Stream1 está gravando ativamente (arquivo recente)"
        elif [ $FILE_AGE -lt 300 ]; then
            echo "⚠️  Stream1 pode ter problemas (arquivo com ${FILE_AGE}s)"
        else
            echo "❌ Stream1 parou de gravar! (último arquivo há ${FILE_AGE}s)"
        fi
    else
        echo "❌ Nenhum arquivo encontrado"
    fi
else
    echo "❌ Diretório não existe: $STREAM1_DIR"
fi
echo ""

# 5. Últimos arquivos gravados - Stream2
echo "📁 5. ÚLTIMOS ARQUIVOS GRAVADOS - STREAM2"
echo "----------------------------------------"
STREAM2_DIR="/media/pi/usb64gb/bts/stream2"
if [ -d "$STREAM2_DIR" ]; then
    LATEST2=$(ls -t "$STREAM2_DIR"/video2_*.mp4 2>/dev/null | head -1)
    if [ -n "$LATEST2" ]; then
        FILE_AGE=$(( $(date +%s) - $(stat -c %Y "$LATEST2") ))
        FILE_SIZE=$(stat -c %s "$LATEST2")
        echo "Último arquivo: $(basename "$LATEST2")"
        echo "Tamanho: $(numfmt --to=iec-i --suffix=B $FILE_SIZE)"
        echo "Idade: ${FILE_AGE}s"
        
        if [ $FILE_AGE -lt 120 ]; then
            echo "✅ Stream2 está gravando ativamente (arquivo recente)"
        elif [ $FILE_AGE -lt 300 ]; then
            echo "⚠️  Stream2 pode ter problemas (arquivo com ${FILE_AGE}s)"
        else
            echo "❌ Stream2 parou de gravar! (último arquivo há ${FILE_AGE}s)"
        fi
    else
        echo "❌ Nenhum arquivo encontrado"
    fi
else
    echo "❌ Diretório não existe: $STREAM2_DIR"
fi
echo ""

# 6. Câmeras USB detectadas
echo "🎥 6. CÂMERAS USB DETECTADAS"
echo "----------------------------------------"
v4l2-ctl --list-devices 2>/dev/null | grep -A2 "usb-webcam" | head -6
echo ""

# 7. Uso de disco
echo "💾 7. USO DE DISCO"
echo "----------------------------------------"
df -h /media/pi/usb64gb | tail -1 | awk '{print "Usado: " $3 " / " $2 " (" $5 ")"}'
DISK_USAGE=$(df /media/pi/usb64gb | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo "✅ Espaço em disco OK ($DISK_USAGE%)"
elif [ $DISK_USAGE -lt 90 ]; then
    echo "⚠️  Espaço em disco baixo ($DISK_USAGE%)"
else
    echo "❌ Espaço em disco crítico! ($DISK_USAGE%)"
fi
echo ""

# 8. Últimas linhas dos logs de erro
echo "📄 8. ÚLTIMAS MENSAGENS DE ERRO (FFmpeg)"
echo "----------------------------------------"
echo "--- Stream1 (últimas 5 linhas) ---"
tail -5 /media/pi/usb64gb/bts/ffmpeg_device0.log 2>/dev/null || echo "Nenhum erro recente"
echo ""
echo "--- Stream2 (últimas 5 linhas) ---"
tail -5 /media/pi/usb64gb/bts/ffmpeg_device2.log 2>/dev/null || echo "Nenhum erro recente"
echo ""

# 9. Temperatura do sistema (Raspberry Pi)
echo "🌡️  9. TEMPERATURA DO SISTEMA"
echo "----------------------------------------"
if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
    TEMP=$(cat /sys/class/thermal/thermal_zone0/temp)
    TEMP_C=$((TEMP / 1000))
    echo "CPU: ${TEMP_C}°C"
    
    if [ $TEMP_C -lt 60 ]; then
        echo "✅ Temperatura normal"
    elif [ $TEMP_C -lt 70 ]; then
        echo "⚠️  Temperatura elevada"
    else
        echo "❌ Temperatura crítica!"
    fi
else
    echo "ℹ️  Informação de temperatura não disponível"
fi
echo ""

# 10. Resumo final
echo "=================================================="
echo "📊 RESUMO"
echo "=================================================="

ISSUES=0

# Verifica issues
if [ $FFMPEG_COUNT -ne 2 ]; then
    echo "❌ Processos FFmpeg incorretos"
    ISSUES=$((ISSUES + 1))
fi

if [ $ZOMBIE_COUNT -gt 0 ]; then
    echo "⚠️  Processos zumbis detectados"
    ISSUES=$((ISSUES + 1))
fi

if [ -n "$LATEST1" ]; then
    FILE_AGE1=$(( $(date +%s) - $(stat -c %Y "$LATEST1") ))
    if [ $FILE_AGE1 -gt 300 ]; then
        echo "❌ Stream1 não está gravando"
        ISSUES=$((ISSUES + 1))
    fi
fi

if [ -n "$LATEST2" ]; then
    FILE_AGE2=$(( $(date +%s) - $(stat -c %Y "$LATEST2") ))
    if [ $FILE_AGE2 -gt 300 ]; then
        echo "❌ Stream2 não está gravando"
        ISSUES=$((ISSUES + 1))
    fi
fi

if [ $DISK_USAGE -gt 90 ]; then
    echo "❌ Espaço em disco crítico"
    ISSUES=$((ISSUES + 1))
fi

if [ $ISSUES -eq 0 ]; then
    echo ""
    echo "✅ ✅ ✅ SISTEMA SAUDÁVEL ✅ ✅ ✅"
    echo ""
    echo "Todas as verificações passaram!"
else
    echo ""
    echo "⚠️  ⚠️  ⚠️  $ISSUES PROBLEMA(S) DETECTADO(S) ⚠️  ⚠️  ⚠️"
    echo ""
    echo "Considere investigar os problemas acima."
fi

echo "=================================================="
echo "Verificação concluída em: $(date)"
echo "=================================================="
