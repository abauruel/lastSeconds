#!/bin/bash
# Sincroniza arquivos de RAM para pendrive
# Move arquivos com mais de N minutos para liberar RAM

RAM_DIR="/dev/shm/bts"
PENDRIVE_DIR="/media/pi/usb64gb/bts"
KEEP_MINUTES=1

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
