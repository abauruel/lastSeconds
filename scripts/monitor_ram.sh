#!/bin/bash
# Monitor de gravação em RAM

echo "======================================"
echo "MONITOR DE GRAVAÇÃO EM RAM"
echo "======================================"
echo

# Verificar se processos FFmpeg estão rodando
FFMPEG_COUNT=$(ps aux | grep "[f]fmpeg" | grep -v grep | wc -l)

if [ "$FFMPEG_COUNT" -eq 0 ]; then
    echo "⚠️  AVISO: Nenhum processo FFmpeg detectado!"
    echo ""
    echo "As gravações não foram iniciadas ainda."
    echo ""
    echo "Para iniciar as gravações (v1.1+):"
    echo "  curl -X POST http://localhost:5000/start"
    echo ""
    echo "Ou verifique o status da API:"
    echo "  curl http://localhost:5000/status"
    echo ""
    exit 0
fi

echo "✅ Processos FFmpeg ativos: $FFMPEG_COUNT"
echo

# Verificar se diretórios existem
if [ ! -d "/dev/shm/bts" ]; then
    echo "⚠️  AVISO: Diretório /dev/shm/bts não existe!"
    echo ""
    echo "Os processos FFmpeg estão rodando mas os diretórios não foram criados."
    echo "Aguarde alguns segundos ou verifique os logs:"
    echo "  sudo journalctl -u bts.service -n 50"
    echo ""
    exit 1
fi

echo "Uso de RAM:"
du -sh /dev/shm/bts /dev/shm/bts/stream1 /dev/shm/bts/stream2 2>/dev/null || echo "Alguns diretórios não encontrados"
echo

echo "Arquivos em RAM (últimos 5):"
if [ -d "/dev/shm/bts/stream1" ]; then
    echo "Stream 1:"
    ls -lht /dev/shm/bts/stream1/ | head -6
else
    echo "Stream 1: Diretório não encontrado"
fi
echo

if [ -d "/dev/shm/bts/stream2" ]; then
    echo "Stream 2:"
    ls -lht /dev/shm/bts/stream2/ | head -6
else
    echo "Stream 2: Diretório não encontrado"
fi
echo

echo "Processos FFmpeg:"
ps aux | grep "[f]fmpeg" | grep -v grep
echo

echo "Últimas sincronizações:"
tail -5 /home/pi/app/logs/sync_ram.log 2>/dev/null || echo "Nenhuma sincronização ainda"
echo

# Status geral
if [ -d "/dev/shm/bts/stream1" ] && [ -d "/dev/shm/bts/stream2" ] && [ "$FFMPEG_COUNT" -ge 2 ]; then
    echo "✅ ✅ ✅ SISTEMA GRAVANDO NORMALMENTE ✅ ✅ ✅"
else
    echo "⚠️  Atenção: Verifique se todas as câmeras estão gravando"
fi
