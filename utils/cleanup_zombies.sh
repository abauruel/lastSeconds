#!/bin/bash
# Script para limpar processos zumbis do FFmpeg

echo "🧹 Limpando processos zumbis do FFmpeg..."

# Encontra processos zumbis do ffmpeg
ZOMBIES=$(ps aux | grep ffmpeg | grep defunct | grep -v grep | awk '{print $2}')

if [ -z "$ZOMBIES" ]; then
    echo "✅ Nenhum processo zumbi encontrado"
    exit 0
fi

COUNT=$(echo "$ZOMBIES" | wc -l)
echo "🧟 Encontrados $COUNT processos zumbis"

# Tenta enviar SIGCHLD para o processo pai (Gunicorn) para reapar os filhos
PARENT_PID=$(pgrep -f "gunicorn.*capture3:app" | head -1)

if [ -n "$PARENT_PID" ]; then
    echo "📡 Enviando SIGCHLD para processo pai (PID: $PARENT_PID)..."
    kill -CHLD "$PARENT_PID" 2>/dev/null
    sleep 2
    
    # Verifica se os zumbis foram limpos
    REMAINING=$(ps aux | grep ffmpeg | grep defunct | grep -v grep | wc -l)
    
    if [ $REMAINING -eq 0 ]; then
        echo "✅ Todos os zumbis foram limpos com sucesso"
    else
        echo "⚠️  Ainda restam $REMAINING zumbis. Eles serão limpos automaticamente pelo sistema."
    fi
else
    echo "⚠️  Processo pai não encontrado. Zumbis serão limpos pelo sistema."
fi

exit 0
