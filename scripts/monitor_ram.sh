#!/bin/bash
# Monitor de gravação em RAM

echo "======================================"
echo "MONITOR DE GRAVAÇÃO EM RAM"
echo "======================================"
echo
echo "Uso de RAM:"
du -sh /dev/shm/bts /dev/shm/bts/stream1 /dev/shm/bts/stream2
echo
echo "Arquivos em RAM (últimos 5):"
ls -lht /dev/shm/bts/stream1/ | head -6
echo
ls -lht /dev/shm/bts/stream2/ | head -6
echo
echo "Processos FFmpeg:"
ps aux | grep "[f]fmpeg" | grep -v grep
echo
echo "Últimas sincronizações:"
tail -5 /home/pi/app/logs/sync_ram.log 2>/dev/null || echo "Nenhuma sincronização ainda"
