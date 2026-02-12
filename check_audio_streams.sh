#!/bin/bash

# Script para verificar integridade de arquivos de vídeo usando ffprobe
# Pasta alvo: /media/pi/usb64gb/bts/stream1/

TARGET_DIR="/media/pi/usb64gb/bts/stream2/"
LOG_FILE="video_integrity_$(date +%Y%m%d_%H%M%S).log"

echo "========================================" | tee "$LOG_FILE"
echo "Verificação de Integridade - $(date)" | tee -a "$LOG_FILE"
echo "Diretório: $TARGET_DIR" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Verifica se o diretório existe
if [ ! -d "$TARGET_DIR" ]; then
    echo "ERRO: Diretório $TARGET_DIR não encontrado!" | tee -a "$LOG_FILE"
    exit 1
fi

# Verifica se ffprobe está instalado
if ! command -v ffprobe &> /dev/null; then
    echo "ERRO: ffprobe não está instalado!" | tee -a "$LOG_FILE"
    exit 1
fi

# Contadores
total_files=0
valid_files=0
corrupted_files=0

# Processa cada arquivo no diretório
echo "Analisando arquivos..." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

for file in "$TARGET_DIR"*; do
    # Pula se não for arquivo
    if [ ! -f "$file" ]; then
        continue
    fi
    
    # Pula arquivos que não são vídeo (baseado em extensões comuns)
    case "${file##*.}" in
        mp4|MP4|mkv|MKV|avi|AVI|mov|MOV|ts|TS|m4v|M4V)
            ;;
        *)
            continue
            ;;
    esac
    
    total_files=$((total_files + 1))
    filename=$(basename "$file")
    
    # Verifica integridade do arquivo com ffprobe (verifica código de saída)
    if ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$file" > /dev/null 2>&1; then
        echo "✓ $filename - ÍNTEGRO" | tee -a "$LOG_FILE"
        valid_files=$((valid_files + 1))
    else
        echo "❌ $filename - CORROMPIDO" | tee -a "$LOG_FILE"
        corrupted_files=$((corrupted_files + 1))
    fi
done

# Relatório final
echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "RESUMO DA VERIFICAÇÃO" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "Total de arquivos: $total_files" | tee -a "$LOG_FILE"
echo "Arquivos íntegros: $valid_files" | tee -a "$LOG_FILE"
echo "Arquivos corrompidos: $corrupted_files" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

if [ $corrupted_files -gt 0 ]; then
    echo "❌ ATENÇÃO: $corrupted_files arquivo(s) corrompido(s)!" | tee -a "$LOG_FILE"
    echo "Status: FALHOU" | tee -a "$LOG_FILE"
else
    echo "✓ Todos os arquivos estão íntegros" | tee -a "$LOG_FILE"
    echo "Status: SUCESSO" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "Log salvo em: $LOG_FILE" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
