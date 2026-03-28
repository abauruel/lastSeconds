#!/bin/bash

# Script para testar detecção dinâmica de câmeras
# Simula mudança de dispositivos /dev/video* e verifica se a detecção ainda funciona

set -e

echo "=========================================="
echo "   TESTE DE DETECÇÃO DINÂMICA DE CÂMERAS"
echo "=========================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Teste 1: Listar dispositivos atuais
echo -e "${BLUE}[TESTE 1] Listando dispositivos atuais...${NC}"
echo ""

if command -v v4l2-ctl &> /dev/null; then
    echo "v4l2-ctl disponível. Saída:"
    v4l2-ctl --list-devices
else
    echo -e "${RED}✗ v4l2-ctl não instalado${NC}"
    echo "  Instalando: sudo apt-get install v4l-utils"
fi

echo ""
echo -e "${BLUE}[TESTE 2] Verificando dispositivos /dev/video*${NC}"
echo ""

if [ -d /dev ]; then
    video_devices=$(ls -la /dev/video* 2>/dev/null | awk '{print $NF}' | sort)
    if [ -z "$video_devices" ]; then
        echo -e "${RED}✗ Nenhum dispositivo /dev/video* encontrado${NC}"
    else
        echo "Dispositivos encontrados:"
        for device in $video_devices; do
            echo "  ✓ $device"
        done
    fi
else
    echo -e "${RED}✗ /dev não acessível${NC}"
fi

echo ""
echo -e "${BLUE}[TESTE 3] Analisando padrão de enumeração${NC}"
echo ""

# Extrai números dos dispositivos
echo "Análise dos números de dispositivo:"
for device in /dev/video*; do
    if [ -e "$device" ] 2>/dev/null; then
        num=$(echo "$device" | sed 's/[^0-9]//g')
        if [ -n "$num" ]; then
            remainder=$((num % 2))
            if [ "$remainder" -eq 0 ]; then
                echo "  $device -> $num (PAR - câmera principal) ✓"
            else
                echo "  $device -> $num (ÍMPAR - plano de fundo/secundário)"
            fi
        fi
    fi
done

echo ""
echo -e "${BLUE}[TESTE 4] Testando rota /health${NC}"
echo ""

if command -v curl &> /dev/null; then
    echo "Consultando http://localhost:5000/health"
    if curl -s http://localhost:5000/health > /tmp/health_response.json 2>/dev/null; then
        echo ""
        echo "Resposta recebida:"
        cat /tmp/health_response.json | python3 -m json.tool 2>/dev/null | grep -A 10 '"cameras"' || cat /tmp/health_response.json
        
        # Extrai status das câmeras
        echo ""
        cameras_detected=$(cat /tmp/health_response.json | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data['cameras'].get('detected', [])))" 2>/dev/null || echo "0")
        echo "Câmeras detectadas: $cameras_detected"
        
        if [ "$cameras_detected" -ge 2 ]; then
            echo -e "${GREEN}✓ Detecção OK (2+ câmeras encontradas)${NC}"
        else
            echo -e "${YELLOW}⚠ Aviso: Menos de 2 câmeras detectadas${NC}"
        fi
    else
        echo -e "${RED}✗ Não conseguiu conectar ao servidor (porta 5000)${NC}"
        echo "  Certifique-se de que o app está rodando: python app.py"
    fi
else
    echo -e "${YELLOW}⚠ curl não instalado, pulando teste${NC}"
fi

echo ""
echo -e "${BLUE}[TESTE 5] Verificando logs do FFmpeg${NC}"
echo ""

ffmpeg_logs=$(find /media/pi/usb64gb -name "ffmpeg_device*.log" 2>/dev/null | head -3)
if [ ! -z "$ffmpeg_logs" ]; then
    echo "Logs encontrados:"
    for log in $ffmpeg_logs; do
        echo "  - $log"
        # Mostra últimas linhas (erro ou sucesso)
        echo "    Últimas linhas:"
        tail -3 "$log" | sed 's/^/      /'
    done
else
    echo -e "${YELLOW}⚠ Nenhum log do FFmpeg encontrado em /media/pi/usb64gb${NC}"
fi

echo ""
echo "=========================================="
echo "   TESTES CONCLUÍDOS"
echo "=========================================="
echo ""
echo -e "${GREEN}✓ Se câmeras foram detectadas corretamente, a solução está funcionando!${NC}"
echo ""
echo "Próximos passos para validação completa:"
echo "1. Desconecte uma câmera USB"
echo "2. Reconecte-a"
echo "3. Execute: v4l2-ctl --list-devices"
echo "4. Execute este script novamente"
echo "5. Verifique se a câmera foi detectada no novo dispositivo"
