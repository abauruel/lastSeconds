#!/bin/bash
# ============================================================
# Diagnóstico de travamentos FFmpeg (2 processos via Python)
# Raspberry Pi 4B - Alex Bauruel
# ============================================================

# --- CONFIGURAÇÕES ---
MONITOR_DURATION=4000   # 300 segundos (ex: 5min)
LOGDIR="/media/pi/usb64gb/bts/tmp/ffmpeg_diag_python_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOGDIR"

# Caminhos das câmeras
DEVICES=("/dev/video0" "/dev/video2")

# Array para manter controle dos processos FFmpeg já monitorados
declare -A MONITORED_PIDS

# Função para instrumentar um processo FFmpeg
instrument_ffmpeg_process() {
  local PID=$1
  local DISCOVERY_TIME=$2
  
  if [[ -n "${MONITORED_PIDS[$PID]}" ]]; then
    return 0  # Já está sendo monitorado
  fi
  
  echo "[INFO] $(date): Instrumentando novo processo FFmpeg PID=$PID (descoberto em: $DISCOVERY_TIME)"
  
  # Marcar como monitorado
  MONITORED_PIDS[$PID]="$DISCOVERY_TIME"
  
  # Coletar informações do processo
  CMD=$(ps -p "$PID" -o cmd= 2>/dev/null | tr -d '\n')
  if [ -z "$CMD" ]; then
    echo "[WARN] Processo PID=$PID já terminou antes da instrumentação"
    return 1
  fi
  
  # Criar logs para o novo processo
  echo "[INFO] Coletando logs de PID=$PID → ffmpeg_${PID}_*.log"
  sudo strace -tt -p "$PID" -e trace=read,write -s 256 -o "$LOGDIR/ffmpeg_${PID}.strace" 2>/dev/null &
  sudo lsof -p "$PID" > "$LOGDIR/ffmpeg_${PID}_lsof.log" 2>&1
  ps -p "$PID" -o pid,ppid,cmd,%cpu,%mem > "$LOGDIR/ffmpeg_${PID}_start.log"
  
  # Log detalhado do novo processo
  {
    echo "=== Novo processo FFmpeg detectado ==="
    echo "PID: $PID"
    echo "Data/Hora: $(date)"
    echo "Comando: $CMD"
    echo "====================================="
  } >> "$LOGDIR/new_ffmpeg_detailed.log"
}

echo "[INFO] Iniciando diagnóstico para subprocessos FFmpeg"
echo "[INFO] Logs em: $LOGDIR"
echo

# --- ETAPA 1: Estado inicial ---
for DEV in "${DEVICES[@]}"; do
  NAME=$(basename "$DEV")
  echo "[INFO] Coletando estado inicial de $DEV..."
  v4l2-ctl -d "$DEV" --all > "$LOGDIR/${NAME}_before.log" 2>&1
done

lsusb -v > "$LOGDIR/lsusb.log" 2>&1
df -h > "$LOGDIR/df.log"
vcgencmd measure_temp > "$LOGDIR/temp_start.log" 2>&1

# --- ETAPA 2: iniciar monitores do sistema ---
sudo dmesg -wT > "$LOGDIR/dmesg_live.log" 2>&1 &
PID_DMESG=$!

sudo iotop -aoP > "$LOGDIR/iotop.log" 2>&1 &
PID_IOTOP=$!

top -b -d 5 -n $((MONITOR_DURATION / 5)) > "$LOGDIR/top.log" 2>&1 &
PID_TOP=$!

# Monitoramento da temperatura
(
  while true; do
    date +"%Y-%m-%d %H:%M:%S" >> "$LOGDIR/temp.log"
    vcgencmd measure_temp >> "$LOGDIR/temp.log"
    sleep 10
  done
) &
PID_TEMP=$!

# --- ETAPA 3: localizar e seguir subprocessos FFmpeg ---
echo "[INFO] Detectando processos relacionados ao sistema de captura..."

# Primeiro, verificar se há processos Python relacionados
PYTHON_PROCS=$(pgrep -f "capture3|video_uploader|ble_action" | tr '\n' ' ')
if [ -n "$PYTHON_PROCS" ]; then
  echo "[INFO] Processos Python detectados: $PYTHON_PROCS"
  for PID in $PYTHON_PROCS; do
    ps -p "$PID" -o pid,cmd > "$LOGDIR/python_${PID}_info.log" 2>&1
  done
fi

# Aguardar por processos FFmpeg com tentativas múltiplas
echo "[INFO] Aguardando subprocessos FFmpeg..."
MAX_ATTEMPTS=6
ATTEMPT=1
PIDS_FFMPEG=""

while [ $ATTEMPT -le $MAX_ATTEMPTS ] && [ -z "$PIDS_FFMPEG" ]; do
  echo "[INFO] Tentativa $ATTEMPT/$MAX_ATTEMPTS - Procurando processos FFmpeg..."
  
  # Buscar por diferentes padrões de FFmpeg
  PIDS_FFMPEG=$(pgrep -f "ffmpeg" | tr '\n' ' ')
  
  # Se não encontrou, tentar padrões mais específicos
  if [ -z "$PIDS_FFMPEG" ]; then
    PIDS_FFMPEG=$(pgrep -f "video[02]" | tr '\n' ' ')
  fi
  
  if [ -z "$PIDS_FFMPEG" ]; then
    echo "[WARN] Nenhum processo FFmpeg encontrado na tentativa $ATTEMPT"
    sleep 10
    ATTEMPT=$((ATTEMPT + 1))
  else
    echo "[INFO] Processos FFmpeg detectados: $PIDS_FFMPEG"
    break
  fi
done

# Se ainda não encontrou FFmpeg, oferecer opções
if [ -z "$PIDS_FFMPEG" ]; then
  echo "[WARN] Nenhum processo FFmpeg encontrado após $MAX_ATTEMPTS tentativas."
  echo "[INFO] Continuando monitoramento do sistema sem instrumentação específica do FFmpeg..."
  echo "[INFO] Os logs de sistema (dmesg, iotop, top) ainda serão coletados."
  echo "[INFO] Você pode iniciar os processos FFmpeg agora e eles aparecerão nos logs."
  FFMPEG_MODE="system_only"
else
  FFMPEG_MODE="ffmpeg_found"
fi

echo "[INFO] Processos FFmpeg detectados: $PIDS_FFMPEG"

# Coleta de logs de cada processo FFmpeg em tempo real (se encontrados)
if [ "$FFMPEG_MODE" = "ffmpeg_found" ]; then
  echo "[INFO] Instrumentando processos FFmpeg encontrados inicialmente..."
  for PID in $PIDS_FFMPEG; do
    instrument_ffmpeg_process "$PID" "inicial"
  done
fi

# Monitor contínuo para novos processos FFmpeg durante a execução
echo "[INFO] Iniciando monitor contínuo para novos processos FFmpeg..."
(
  MONITOR_INTERVAL=5  # Verificar a cada 5 segundos
  while true; do
    # Obter lista atual de processos FFmpeg
    CURRENT_FFMPEG=$(pgrep -f "ffmpeg" 2>/dev/null)
    
    if [ -n "$CURRENT_FFMPEG" ]; then
      # Verificar cada processo encontrado
      for PID in $CURRENT_FFMPEG; do
        # Se não está sendo monitorado ainda, instrumentar
        if [[ -z "${MONITORED_PIDS[$PID]}" ]]; then
          echo "[INFO] $(date): Novo processo FFmpeg detectado - PID=$PID"
          instrument_ffmpeg_process "$PID" "$(date)"
          
          # Atualizar modo se necessário
          if [ "$FFMPEG_MODE" = "system_only" ]; then
            FFMPEG_MODE="ffmpeg_detected_later"
            echo "[INFO] Modo alterado para: $FFMPEG_MODE"
          fi
        fi
      done
      
      # Verificar se algum processo monitorado terminou
      for MONITORED_PID in "${!MONITORED_PIDS[@]}"; do
        if ! kill -0 "$MONITORED_PID" 2>/dev/null; then
          echo "[INFO] $(date): Processo FFmpeg PID=$MONITORED_PID terminou" >> "$LOGDIR/ffmpeg_lifecycle.log"
          # Coletar informações finais se o processo ainda existir
          ps -p "$MONITORED_PID" -o pid,ppid,cmd,%cpu,%mem >> "$LOGDIR/ffmpeg_lifecycle.log" 2>/dev/null
          # Não remover do array para manter histórico
        fi
      done
    fi
    
    # Log de status a cada minuto
    if (( $(date +%S) == 0 )); then
      ACTIVE_COUNT=$(echo "$CURRENT_FFMPEG" | wc -w)
      MONITORED_COUNT=${#MONITORED_PIDS[@]}
      echo "[INFO] $(date): Status - Processos FFmpeg ativos: $ACTIVE_COUNT, Monitorados: $MONITORED_COUNT" >> "$LOGDIR/monitor_status.log"
    fi
    
    sleep $MONITOR_INTERVAL
  done
) &
PID_FFMPEG_MONITOR=$!

# --- ETAPA 4: monitorar ---
echo "[INFO] Monitorando por ${MONITOR_DURATION}s..."
sleep "$MONITOR_DURATION"

# --- ETAPA 5: encerrar monitores ---
echo "[INFO] Encerrando monitores..."
sudo kill $PID_DMESG $PID_IOTOP $PID_TOP $PID_TEMP $PID_FFMPEG_MONITOR 2>/dev/null

# --- ETAPA 6: Estado final ---
echo "[INFO] Coletando estado final..."

# Relatório de processos FFmpeg monitorados
MONITORED_COUNT=${#MONITORED_PIDS[@]}
echo "[INFO] Total de processos FFmpeg monitorados durante a sessão: $MONITORED_COUNT"

if [ $MONITORED_COUNT -gt 0 ]; then
  {
    echo "=== Relatório de Processos FFmpeg Monitorados ==="
    echo "Data: $(date)"
    echo "Duração do monitoramento: ${MONITOR_DURATION}s"
    echo ""
    for PID in "${!MONITORED_PIDS[@]}"; do
      echo "PID: $PID"
      echo "  Descoberto em: ${MONITORED_PIDS[$PID]}"
      if kill -0 "$PID" 2>/dev/null; then
        echo "  Status: ATIVO"
        ps -p "$PID" -o pid,ppid,cmd,%cpu,%mem >> "$LOGDIR/final_active_ffmpeg.log" 2>/dev/null
      else
        echo "  Status: TERMINADO"
      fi
      echo ""
    done
    echo "=================================================="
  } > "$LOGDIR/ffmpeg_monitoring_summary.log"
fi

# Verificar se há processos zumbi do FFmpeg
ZOMBIE_FFMPEG=$(ps aux | grep -E "\[ffmpeg\].*<defunct>" | wc -l)
if [ "$ZOMBIE_FFMPEG" -gt 0 ]; then
  echo "[INFO] Encontrados $ZOMBIE_FFMPEG processos FFmpeg zumbi" 
  ps aux | grep -E "\[ffmpeg\].*<defunct>" > "$LOGDIR/zombie_ffmpeg.log" 2>&1
fi

# Verificar processos FFmpeg finais (todos os ativos, não apenas monitorados)
FINAL_FFMPEG=$(pgrep -f "ffmpeg" | tr '\n' ' ')
if [ -n "$FINAL_FFMPEG" ]; then
  echo "[INFO] Processos FFmpeg ainda ativos no final: $FINAL_FFMPEG"
  for PID in $FINAL_FFMPEG; do
    ps -p "$PID" -o pid,ppid,cmd,%cpu,%mem > "$LOGDIR/ffmpeg_${PID}_final.log" 2>/dev/null
  done
fi

for DEV in "${DEVICES[@]}"; do
  NAME=$(basename "$DEV")
  v4l2-ctl -d "$DEV" --all > "$LOGDIR/${NAME}_after.log" 2>&1
done

vcgencmd measure_temp > "$LOGDIR/temp_end.log" 2>&1

# --- Compactar resultados ---
cd /media/pi/usb64gb/bts/tmp
TARFILE="${LOGDIR}.tar.gz"
tar -czf "$TARFILE" "$(basename $LOGDIR)"

echo
echo "[✅] Diagnóstico concluído!"
echo "Arquivo compactado salvo em: $TARFILE"
echo
echo "📊 Resumo do diagnóstico:"
echo "  - Duração do monitoramento: ${MONITOR_DURATION}s"
echo "  - Modo de execução: $FFMPEG_MODE"
echo "  - Processos FFmpeg monitorados: $MONITORED_COUNT"
if [ -n "$ZOMBIE_FFMPEG" ] && [ "$ZOMBIE_FFMPEG" -gt 0 ]; then
  echo "  - ⚠️  Processos FFmpeg zumbi encontrados: $ZOMBIE_FFMPEG"
fi
echo
echo "🔍 Para analisar os logs:"
echo "  tar -tzf $TARFILE                              # Listar arquivos"
echo "  tar -xzf $TARFILE                              # Extrair arquivos"
echo "  less $(basename $LOGDIR)/dmesg_live.log        # Ver logs do kernel"
echo "  less $(basename $LOGDIR)/top.log               # Ver uso de recursos"
echo "  less $(basename $LOGDIR)/monitor_status.log    # Status do monitoramento"
echo "  less $(basename $LOGDIR)/ffmpeg_monitoring_summary.log  # Resumo dos FFmpeg"
if [ -f "$LOGDIR/new_ffmpeg_detailed.log" ]; then
  echo "  less $(basename $LOGDIR)/new_ffmpeg_detailed.log      # Novos FFmpeg detectados"
fi
if [ -f "$LOGDIR/ffmpeg_lifecycle.log" ]; then
  echo "  less $(basename $LOGDIR)/ffmpeg_lifecycle.log         # Ciclo de vida dos FFmpeg"
fi
echo
