#!/bin/bash
# Script para monitorar a saúde dos streams
# Uso: ./monitor_streaming_health.sh

API_URL="http://localhost:5000"

echo "========================================="
echo "MONITORAMENTO DE SAÚDE DO STREAMING"
echo "========================================="
echo ""

# Verifica saúde geral
echo "🔍 Verificando saúde geral do sistema..."
response=$(curl -s "${API_URL}/health")

if [ $? -eq 0 ]; then
    echo "$response" | python3 -m json.tool
    
    # Extrai status
    status=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null)
    
    if [ "$status" == "healthy" ]; then
        echo ""
        echo "✅ Sistema está saudável!"
    else
        echo ""
        echo "⚠️  Sistema com problemas detectados!"
        echo ""
        echo "Deseja tentar reparar automaticamente? (y/n)"
        read -r resposta
        
        if [ "$resposta" == "y" ]; then
            echo ""
            echo "🔧 Tentando reparar..."
            
            # Verifica se MediaMTX está com problema
            mediamtx_healthy=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['details']['mediamtx']['healthy'])" 2>/dev/null)
            if [ "$mediamtx_healthy" == "False" ]; then
                echo "🔄 Reiniciando MediaMTX..."
                curl -s -X POST "${API_URL}/restart_mediamtx" | python3 -m json.tool
                sleep 5
            fi
            
            # Verifica FFmpeg device0
            device0_healthy=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['details']['ffmpeg']['device0']['healthy'])" 2>/dev/null)
            if [ "$device0_healthy" == "False" ]; then
                echo "🔄 Reiniciando FFmpeg device0..."
                curl -s -X POST "${API_URL}/restart_ffmpeg/0" | python3 -m json.tool
                sleep 2
            fi
            
            # Verifica FFmpeg device1
            device1_healthy=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['details']['ffmpeg']['device1']['healthy'])" 2>/dev/null)
            if [ "$device1_healthy" == "False" ]; then
                echo "🔄 Reiniciando FFmpeg device1..."
                curl -s -X POST "${API_URL}/restart_ffmpeg/1" | python3 -m json.tool
                sleep 2
            fi
            
            echo ""
            echo "✅ Tentativa de reparo concluída. Verificando novamente em 10 segundos..."
            sleep 10
            
            # Verifica novamente
            response2=$(curl -s "${API_URL}/health")
            echo "$response2" | python3 -m json.tool
        fi
    fi
else
    echo "❌ Erro ao conectar com a API!"
    echo "Verifique se o serviço better_seconds_record está rodando:"
    echo "  sudo systemctl status better_seconds_record"
fi

echo ""
echo "========================================="
echo "Verificando arquivos de log..."
echo "========================================="
echo ""

# Últimas linhas do log do FFmpeg
if [ -f "/media/pi/usb64gb/bts/ffmpeg_device0.log" ]; then
    echo "📝 Últimas 5 linhas do FFmpeg device0:"
    tail -n 5 /media/pi/usb64gb/bts/ffmpeg_device0.log
fi

echo ""

if [ -f "/media/pi/usb64gb/bts/ffmpeg_device2.log" ]; then
    echo "📝 Últimas 5 linhas do FFmpeg device2:"
    tail -n 5 /media/pi/usb64gb/bts/ffmpeg_device2.log
fi

echo ""
echo "========================================="
echo "Testes de acesso aos streams"
echo "========================================="
echo ""

# Testa stream1
echo "🌐 Testando stream1 (http://192.168.1.187:8888/live/stream1/)..."
http_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8888/live/stream1/index.m3u8")
if [ "$http_code" == "200" ]; then
    echo "✅ Stream1 disponível (HTTP $http_code)"
else
    echo "❌ Stream1 indisponível (HTTP $http_code)"
fi

# Testa stream2
echo "🌐 Testando stream2 (http://192.168.1.187:8888/live/stream2/)..."
http_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8888/live/stream2/index.m3u8")
if [ "$http_code" == "200" ]; then
    echo "✅ Stream2 disponível (HTTP $http_code)"
else
    echo "❌ Stream2 indisponível (HTTP $http_code)"
fi

echo ""
echo "========================================="
echo "Monitoramento concluído!"
echo "========================================="
