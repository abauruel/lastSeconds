#!/bin/bash
# Script para verificar status do streaming

echo "=================================================="
echo "📡 STATUS DO STREAMING AO VIVO"
echo "=================================================="
echo ""

# 1. Verifica se MediaMTX está rodando
echo "1. MediaMTX:"
if pgrep -x "mediamtx" > /dev/null; then
    echo "   ✅ Rodando"
    MEDIAMTX_PID=$(pgrep -x "mediamtx")
    echo "   PID: $MEDIAMTX_PID"
else
    echo "   ❌ NÃO está rodando!"
fi
echo ""

# 2. Verifica portas
echo "2. Portas abertas:"
for port in 8888 8554 1935; do
    if netstat -tln 2>/dev/null | grep -q ":$port " || ss -tln 2>/dev/null | grep -q ":$port "; then
        echo "   ✅ Porta $port aberta"
    else
        echo "   ❌ Porta $port fechada"
    fi
done
echo ""

# 3. Verifica conexões RTMP ativas
echo "3. Conexões RTMP ativas:"
RTMP_CONNS=$(netstat -tn 2>/dev/null | grep :1935 | grep ESTABLISHED | wc -l)
if [ "$RTMP_CONNS" -eq 0 ]; then
    RTMP_CONNS=$(ss -tn 2>/dev/null | grep :1935 | grep ESTAB | wc -l)
fi

if [ "$RTMP_CONNS" -ge 2 ]; then
    echo "   ✅ $RTMP_CONNS conexões ativas (esperado: 2)"
elif [ "$RTMP_CONNS" -ge 1 ]; then
    echo "   ⚠️  $RTMP_CONNS conexão ativa (esperado: 2)"
else
    echo "   ❌ Nenhuma conexão RTMP ativa!"
    echo "      FFmpeg não está conectado ao MediaMTX"
fi
echo ""

# 4. Verifica se HLS está sendo gerado
echo "4. Playlists HLS:"
if ls /tmp/live_stream1_*.m3u8 2>/dev/null | head -1 > /dev/null; then
    echo "   ✅ Stream 1 ativo"
    LATEST1=$(ls -t /tmp/live_stream1_*.m3u8 2>/dev/null | head -1)
    AGE1=$(( $(date +%s) - $(stat -c %Y "$LATEST1") ))
    echo "      Última atualização: ${AGE1}s atrás"
else
    echo "   ❌ Stream 1 NÃO está gerando HLS"
fi

if ls /tmp/live_stream2_*.m3u8 2>/dev/null | head -1 > /dev/null; then
    echo "   ✅ Stream 2 ativo"
    LATEST2=$(ls -t /tmp/live_stream2_*.m3u8 2>/dev/null | head -1)
    AGE2=$(( $(date +%s) - $(stat -c %Y "$LATEST2") ))
    echo "      Última atualização: ${AGE2}s atrás"
else
    echo "   ❌ Stream 2 NÃO está gerando HLS"
fi
echo ""

# 5. Testa acesso às URLs
echo "5. Teste de acesso:"
echo "   HLS Stream 1:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/live/stream1/index.m3u8 --max-time 5)
if [ "$HTTP_CODE" = "200" ]; then
    echo "      ✅ Acessível (HTTP $HTTP_CODE)"
elif [ "$HTTP_CODE" = "404" ]; then
    echo "      ❌ Não encontrado (HTTP $HTTP_CODE) - Stream não está ativo"
else
    echo "      ⚠️  HTTP $HTTP_CODE"
fi

echo "   HLS Stream 2:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/live/stream2/index.m3u8 --max-time 5)
if [ "$HTTP_CODE" = "200" ]; then
    echo "      ✅ Acessível (HTTP $HTTP_CODE)"
elif [ "$HTTP_CODE" = "404" ]; then
    echo "      ❌ Não encontrado (HTTP $HTTP_CODE) - Stream não está ativo"
else
    echo "      ⚠️  HTTP $HTTP_CODE"
fi
echo ""

# 6. Últimos logs do MediaMTX
echo "6. Últimos eventos (MediaMTX):"
sudo journalctl -u mediamtx -n 5 --no-pager 2>/dev/null | grep -E "(publishing|destroyed|created)" | tail -5 || echo "   Sem logs disponíveis"
echo ""

# 7. URLs de acesso
echo "=================================================="
echo "📺 URLS DE ACESSO"
echo "=================================================="
IP=$(hostname -I | awk '{print $1}')
echo ""
echo "HLS (navegador web):"
echo "   http://$IP:8888/live/stream1/index.m3u8"
echo "   http://$IP:8888/live/stream2/index.m3u8"
echo ""
echo "RTSP (VLC, apps):"
echo "   rtsp://$IP:8554/live/stream1"
echo "   rtsp://$IP:8554/live/stream2"
echo ""
echo "RTMP (software streaming):"
echo "   rtmp://$IP:1935/live/stream1"
echo "   rtmp://$IP:1935/live/stream2"
echo ""
echo "=================================================="
