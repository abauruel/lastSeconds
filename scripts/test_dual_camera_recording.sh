#!/bin/bash
# Script de teste de gravação simultânea de 2 câmeras
# Valida race conditions e performance de I/O

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

DURATION=${1:-300}  # Duração do teste em segundos (padrão: 5 minutos)
BASE_DIR="/home/pi/recordings"

echo "========================================="
echo "Teste de Gravação Simultânea - 2 Câmeras"
echo "========================================="
echo ""
echo "Duração do teste: ${DURATION}s ($(($DURATION / 60)) minutos)"
echo "Diretório base: $BASE_DIR"
echo ""

# Função para imprimir status
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "OK" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "WARNING" ]; then
        echo -e "${YELLOW}⚠️  $message${NC}"
    else
        echo -e "${RED}❌ $message${NC}"
    fi
}

# 1. Verificar processos FFmpeg
echo "1. Verificando processos FFmpeg..."
FFMPEG_COUNT=$(ps aux | grep ffmpeg | grep -v grep | wc -l)
if [ $FFMPEG_COUNT -ge 2 ]; then
    print_status "OK" "Encontrados $FFMPEG_COUNT processos FFmpeg"
else
    print_status "ERROR" "Esperados 2+ processos FFmpeg, encontrados: $FFMPEG_COUNT"
    echo "   Execute: sudo systemctl start capture3_https"
    exit 1
fi
echo ""

# 2. Verificar diretórios
echo "2. Verificando estrutura de diretórios..."
for dir in "$BASE_DIR/stream1" "$BASE_DIR/stream2"; do
    if [ -d "$dir" ]; then
        print_status "OK" "Diretório existe: $dir"
    else
        print_status "ERROR" "Diretório não encontrado: $dir"
        exit 1
    fi
done
echo ""

# 3. Baseline - Contar arquivos iniciais
echo "3. Coletando dados baseline..."
STREAM1_INITIAL=$(ls -1 $BASE_DIR/stream1/*.ts 2>/dev/null | wc -l)
STREAM2_INITIAL=$(ls -1 $BASE_DIR/stream2/*.ts 2>/dev/null | wc -l)
echo "   Stream1: $STREAM1_INITIAL arquivos"
echo "   Stream2: $STREAM2_INITIAL arquivos"
echo ""

# 4. Teste de escrita simultânea
echo "4. Iniciando teste de I/O simultâneo..."
echo "   Aguardando ${DURATION}s de gravação..."

SAMPLES=$((DURATION / 30))  # Amostra a cada 30 segundos
for i in $(seq 1 $SAMPLES); do
    echo -n "   Progresso: $(($i * 30))s / ${DURATION}s"
    
    # Verificar processos ainda estão rodando
    FFMPEG_ALIVE=$(ps aux | grep ffmpeg | grep -v grep | wc -l)
    if [ $FFMPEG_ALIVE -lt 2 ]; then
        echo ""
        print_status "ERROR" "Processo FFmpeg morreu durante o teste!"
        exit 1
    fi
    
    # Verificar se arquivos estão sendo criados
    STREAM1_NOW=$(ls -1 $BASE_DIR/stream1/*.ts 2>/dev/null | wc -l)
    STREAM2_NOW=$(ls -1 $BASE_DIR/stream2/*.ts 2>/dev/null | wc -l)
    
    if [ $STREAM1_NOW -gt $STREAM1_INITIAL ] || [ $STREAM2_NOW -gt $STREAM2_INITIAL ]; then
        echo -n " [✓]"
    else
        echo -n " [?]"
    fi
    
    echo ""
    sleep 30
done
echo ""

# 5. Verificar novos arquivos criados
echo "5. Analisando arquivos criados durante o teste..."
STREAM1_FINAL=$(ls -1 $BASE_DIR/stream1/*.ts 2>/dev/null | wc -l)
STREAM2_FINAL=$(ls -1 $BASE_DIR/stream2/*.ts 2>/dev/null | wc -l)
STREAM1_NEW=$((STREAM1_FINAL - STREAM1_INITIAL))
STREAM2_NEW=$((STREAM2_FINAL - STREAM2_INITIAL))

echo "   Stream1: $STREAM1_NEW novos arquivos"
echo "   Stream2: $STREAM2_NEW novos arquivos"

if [ $STREAM1_NEW -gt 0 ] && [ $STREAM2_NEW -gt 0 ]; then
    print_status "OK" "Ambas as câmeras geraram arquivos"
else
    print_status "ERROR" "Uma ou ambas as câmeras não geraram arquivos"
    exit 1
fi
echo ""

# 6. Verificar arquivos corrompidos (0 bytes)
echo "6. Verificando arquivos corrompidos..."
CORRUPT_COUNT=0
for dir in "$BASE_DIR/stream1" "$BASE_DIR/stream2"; do
    CORRUPT=$(find "$dir" -name "*.ts" -size 0 2>/dev/null | wc -l)
    CORRUPT_COUNT=$((CORRUPT_COUNT + CORRUPT))
    if [ $CORRUPT -gt 0 ]; then
        print_status "WARNING" "Encontrados $CORRUPT arquivos vazios em $dir"
        find "$dir" -name "*.ts" -size 0 -exec ls -lh {} \;
    fi
done

if [ $CORRUPT_COUNT -eq 0 ]; then
    print_status "OK" "Nenhum arquivo corrompido detectado"
fi
echo ""

# 7. Verificar integridade com ffprobe
echo "7. Verificando integridade de arquivos (últimos 3 de cada stream)..."
INTEGRITY_ERRORS=0

for stream in stream1 stream2; do
    FILES=$(ls -t $BASE_DIR/$stream/*.ts 2>/dev/null | head -3)
    for file in $FILES; do
        echo -n "   Testando: $(basename $file)... "
        if ffprobe -v error "$file" >/dev/null 2>&1; then
            echo -e "${GREEN}OK${NC}"
        else
            echo -e "${RED}ERRO${NC}"
            INTEGRITY_ERRORS=$((INTEGRITY_ERRORS + 1))
        fi
    done
done

if [ $INTEGRITY_ERRORS -eq 0 ]; then
    print_status "OK" "Todos os arquivos testados estão íntegros"
else
    print_status "ERROR" "$INTEGRITY_ERRORS arquivos com problemas de integridade"
fi
echo ""

# 8. Verificar duração dos segmentos
echo "8. Verificando duração dos segmentos (deve ser ~180s)..."
for stream in stream1 stream2; do
    LAST_FILE=$(ls -t $BASE_DIR/$stream/*.ts 2>/dev/null | head -1)
    if [ -n "$LAST_FILE" ]; then
        DURATION_SEC=$(ffprobe -v error -show_entries format=duration \
                       -of default=noprint_wrappers=1:nokey=1 "$LAST_FILE" 2>/dev/null)
        if [ -n "$DURATION_SEC" ]; then
            DURATION_INT=${DURATION_SEC%.*}
            echo -n "   $stream: ${DURATION_INT}s "
            if [ $DURATION_INT -ge 150 ] && [ $DURATION_INT -le 210 ]; then
                echo -e "${GREEN}[✓ OK]${NC}"
            else
                echo -e "${YELLOW}[⚠ Fora do esperado: 150-210s]${NC}"
            fi
        fi
    fi
done
echo ""

# 9. Verificar uso de I/O
echo "9. Verificando uso de I/O do disco..."
iostat -x 1 3 | grep -A 1 "Device" | tail -5
echo ""

# 10. Verificar espaço em disco
echo "10. Verificando espaço em disco..."
DISK_USAGE=$(df -h $BASE_DIR | tail -1 | awk '{print $5}' | sed 's/%//')
DISK_AVAIL=$(df -h $BASE_DIR | tail -1 | awk '{print $4}')
echo "   Uso atual: ${DISK_USAGE}%"
echo "   Disponível: $DISK_AVAIL"

if [ $DISK_USAGE -lt 80 ]; then
    print_status "OK" "Espaço em disco adequado"
elif [ $DISK_USAGE -lt 90 ]; then
    print_status "WARNING" "Espaço em disco baixo"
else
    print_status "ERROR" "Espaço em disco crítico!"
fi
echo ""

# 11. Verificar logs de erro
echo "11. Verificando últimos erros nos logs FFmpeg..."
for log in "$BASE_DIR/ffmpeg_device0.log" "$BASE_DIR/ffmpeg_device2.log"; do
    if [ -f "$log" ]; then
        echo "   --- $(basename $log) ---"
        tail -5 "$log" | grep -iE "error|warning|fail" || echo "   Nenhum erro recente"
    fi
done
echo ""

# 12. Teste de Race Condition em timestamps
echo "12. Teste de race condition em arquivo de timestamps..."
TIMESTAMP_FILE="$BASE_DIR/streams/timestamps/$(date +%Y%m%d).txt"
if [ -f "$TIMESTAMP_FILE" ]; then
    # Simular 10 escritas simultâneas
    for i in {1..10}; do
        (echo "test_$i_$$_$(date +%s%N)" >> "$TIMESTAMP_FILE") &
    done
    wait
    
    # Verificar se todas as linhas foram escritas
    TEST_LINES=$(grep -c "test_" "$TIMESTAMP_FILE" 2>/dev/null || echo 0)
    if [ $TEST_LINES -eq 10 ]; then
        print_status "OK" "Arquivo de timestamps suporta escrita concorrente"
    else
        print_status "WARNING" "Possível race condition (esperado: 10, encontrado: $TEST_LINES)"
    fi
    
    # Limpar linhas de teste
    sed -i '/test_/d' "$TIMESTAMP_FILE"
else
    print_status "WARNING" "Arquivo de timestamps não encontrado (normal se não há eventos)"
fi
echo ""

# Resumo final
echo "========================================="
echo "           RESUMO DO TESTE"
echo "========================================="
echo ""

TOTAL_TESTS=12
PASSED_TESTS=$((12 - INTEGRITY_ERRORS))

if [ $INTEGRITY_ERRORS -eq 0 ] && [ $CORRUPT_COUNT -eq 0 ]; then
    echo -e "${GREEN}✅ TESTE APROVADO${NC}"
    echo ""
    echo "Sistema operando normalmente com 2 câmeras simultâneas."
    echo "Nenhum problema de race condition ou corrupção detectado."
else
    echo -e "${YELLOW}⚠️  TESTE PARCIALMENTE APROVADO${NC}"
    echo ""
    echo "Problemas detectados:"
    [ $CORRUPT_COUNT -gt 0 ] && echo "  - $CORRUPT_COUNT arquivo(s) corrompido(s)"
    [ $INTEGRITY_ERRORS -gt 0 ] && echo "  - $INTEGRITY_ERRORS erro(s) de integridade"
    echo ""
    echo "Recomendações:"
    echo "  1. Verificar qualidade do microSD"
    echo "  2. Verificar logs: tail -f $BASE_DIR/ffmpeg_device*.log"
    echo "  3. Considerar usar microSD de melhor qualidade"
fi

echo ""
echo "Estatísticas:"
echo "  - Duração do teste: ${DURATION}s"
echo "  - Arquivos gerados (stream1): $STREAM1_NEW"
echo "  - Arquivos gerados (stream2): $STREAM2_NEW"
echo "  - Uso de disco: ${DISK_USAGE}%"
echo "  - Espaço disponível: $DISK_AVAIL"
echo ""
echo "========================================="
