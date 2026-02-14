#!/bin/bash
# Script para configurar gravação em RAM (tmpfs) com backup em pendrive
# Resolve problemas de I/O lento eliminando corrupção de arquivos

set -e

echo "======================================================================"
echo "CONFIGURAÇÃO DE GRAVAÇÃO EM RAM (TMPFS)"
echo "======================================================================"
echo

# Configurações
RAM_DIR="/dev/shm/bts"  # tmpfs já montado por padrão
PENDRIVE_DIR="/media/pi/usb64gb/bts"
RAM_SIZE_MB=30      # 300MB para buffer de vídeo (~10 minutos)
KEEP_MINUTES=1       # Manter últimos 10 minutos em RAM

echo "Configurações:"
echo "  Diretório RAM: $RAM_DIR"
echo "  Diretório Pendrive: $PENDRIVE_DIR"
echo "  Tamanho buffer RAM: ${RAM_SIZE_MB}MB (~$KEEP_MINUTES minutos)"
echo

# Verifica espaço disponível em RAM
available_ram=$(free -m | awk '/^Mem:/{print $7}')
echo "RAM disponível: ${available_ram}MB"

if [ $available_ram -lt $RAM_SIZE_MB ]; then
    echo "⚠️  AVISO: RAM disponível (${available_ram}MB) menor que configurado (${RAM_SIZE_MB}MB)"
    echo "    Sistema pode ficar instável. Considere reduzir RAM_SIZE_MB"
    read -p "Continuar mesmo assim? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 1
    fi
fi

echo
echo "1. Criando diretórios em RAM..."
sudo mkdir -p "$RAM_DIR/stream1"
sudo mkdir -p "$RAM_DIR/stream2"
sudo chown -R pi:pi "$RAM_DIR"
echo "   ✓ Diretórios criados"

echo
echo "2. Verificando pendrive..."
if [ ! -d "$PENDRIVE_DIR" ]; then
    echo "   ✗ Pendrive não montado em $PENDRIVE_DIR"
    exit 1
fi
echo "   ✓ Pendrive OK"

echo
echo "3. Criando script de sincronização..."
cat > /home/pi/app/sync_ram_to_pendrive.sh << 'SYNCEOF'
#!/bin/bash
# Sincroniza arquivos de RAM para pendrive
# Move arquivos com mais de N minutos para liberar RAM

RAM_DIR="/dev/shm/bts"
PENDRIVE_DIR="/media/pi/usb64gb/bts"
KEEP_MINUTES=10

# Função para mover arquivos antigos
sync_stream() {
    local stream=$1
    local count=0
    
    # Encontra arquivos com mais de KEEP_MINUTES minutos
    find "$RAM_DIR/$stream" -name "*.ts" -mmin +$KEEP_MINUTES -type f | while read -r file; do
        filename=$(basename "$file")
        dest="$PENDRIVE_DIR/$stream/$filename"
        
        # Move apenas se não existir no destino
        if [ ! -f "$dest" ]; then
            mv "$file" "$dest" 2>/dev/null && {
                echo "$(date '+%Y-%m-%d %H:%M:%S') - Movido: $filename"
                ((count++))
            }
        else
            # Remove duplicata
            rm "$file" 2>/dev/null
        fi
    done
}

# Sincroniza ambos os streams
sync_stream "stream1"
sync_stream "stream2"

# Mostra uso de RAM
ram_usage=$(du -sh "$RAM_DIR" 2>/dev/null | cut -f1)
echo "$(date '+%Y-%m-%d %H:%M:%S') - Uso de RAM: $ram_usage"
SYNCEOF

chmod +x /home/pi/app/sync_ram_to_pendrive.sh
echo "   ✓ Script criado: /home/pi/app/sync_ram_to_pendrive.sh"

echo
echo "4. Configurando cron para sincronização automática..."
# Sincroniza a cada 5 minutos
CRON_LINE="*/5 * * * * /home/pi/app/sync_ram_to_pendrive.sh >> /home/pi/app/logs/sync_ram.log 2>&1"

# Remove entrada antiga se existir
crontab -l 2>/dev/null | grep -v "sync_ram_to_pendrive.sh" | crontab -

# Adiciona nova entrada
(crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
echo "   ✓ Cron configurado (executa a cada 5 minutos)"

echo
echo "5. Criando arquivo de configuração de ambiente..."
cat > /home/pi/app/.env.ram << 'EOF'
# Configuração para gravação em RAM
export BTS_STREAM1_DIR="/dev/shm/bts/stream1"
export BTS_STREAM2_DIR="/dev/shm/bts/stream2"
export BTS_USE_RAM=1
EOF
echo "   ✓ Arquivo criado: /home/pi/app/.env.ram"

echo
echo "======================================================================"
echo "CONFIGURAÇÃO CONCLUÍDA"
echo "======================================================================"
echo
echo "Próximos passos:"
echo
echo "1. Atualizar ffmpeg_manager.py para usar diretórios em RAM"
echo "   (já foi preparado para ler variáveis de ambiente)"
echo
echo "2. Reiniciar o serviço:"
echo "   sudo systemctl restart better_seconds_record.service"
echo
echo "3. Monitorar sincronização:"
echo "   tail -f /home/pi/app/logs/sync_ram.log"
echo
echo "4. Verificar uso de RAM:"
echo "   du -sh /dev/shm/bts"
echo
echo "⚠️  IMPORTANTE:"
echo "   - Dados em RAM são perdidos se o sistema reiniciar"
echo "   - Mantenha sincronização funcionando (cron)"
echo "   - Monitore uso de RAM regularmente"
echo
echo "Para reverter: execute ./revert_ram_config.sh"
echo "======================================================================"
