#!/bin/bash
# Script para verificar arquivos .ts com 0 bytes

echo "========================================="
echo "Verificando arquivos vazios (.ts)"
echo "========================================="

STREAM1="/media/pi/usb64gb/bts/stream1"
STREAM2="/media/pi/usb64gb/bts/stream2"

count=0

for dir in "$STREAM1" "$STREAM2"; do
    if [ -d "$dir" ]; then
        echo ""
        echo "Verificando: $dir"
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                size=$(stat -c%s "$file")
                if [ "$size" -eq 0 ]; then
                    echo "❌ VAZIO: $(basename "$file")"
                    ((count++))
                fi
            fi
        done < <(find "$dir" -name "*.ts" -o -name "*.mp4")
    fi
done

echo ""
echo "========================================="
echo "Total de arquivos vazios: $count"
echo "========================================="

if [ "$count" -gt 0 ]; then
    echo ""
    echo "Para remover automaticamente, o watchdog do FFmpeg Manager"
    echo "irá limpar esses arquivos após 60 segundos."
fi
