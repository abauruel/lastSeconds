#!/bin/bash

###############################################################################
# Backup de MicroSD para uso com Balena Etcher
# 
# Este script cria uma imagem .img do microSD que pode ser restaurada
# usando Balena Etcher (https://www.balena.io/etcher/)
#
# Uso:
#   ./backup_microsd.sh [dispositivo] [destino]
#
# Exemplos:
#   ./backup_microsd.sh /dev/sdb ~/backups/
#   ./backup_microsd.sh (interativo)
###############################################################################

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Backup MicroSD para Balena Etcher                  ║"
echo "║                  Better Seconds System                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then 
   echo -e "${RED}❌ Este script precisa ser executado como root (use sudo)${NC}"
   exit 1
fi

# Função para listar dispositivos
list_devices() {
    echo -e "${BLUE}📋 Dispositivos disponíveis:${NC}"
    lsblk -d -o NAME,SIZE,TYPE,MOUNTPOINT | grep -E "disk|part"
    echo ""
}

# Função para verificar se dispositivo existe
check_device() {
    if [ ! -b "$1" ]; then
        echo -e "${RED}❌ Dispositivo $1 não encontrado${NC}"
        exit 1
    fi
}

# Função para confirmar ação
confirm() {
    read -p "$1 (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[SsYy]$ ]]; then
        echo -e "${YELLOW}⚠️  Operação cancelada${NC}"
        exit 0
    fi
}

# Modo interativo ou argumentos
if [ -z "$1" ]; then
    echo -e "${YELLOW}🔍 Modo interativo ativado${NC}\n"
    
    list_devices
    
    read -p "Digite o dispositivo do microSD (ex: /dev/sdb): " DEVICE
    
    # Remover /dev/ se usuário digitou apenas sdb
    if [[ ! $DEVICE == /dev/* ]]; then
        DEVICE="/dev/$DEVICE"
    fi
    
    check_device "$DEVICE"
    
    # Mostrar informações do dispositivo
    echo -e "\n${BLUE}📊 Informações do dispositivo:${NC}"
    sudo fdisk -l "$DEVICE" | head -n 5
    echo ""
    
    # Confirmar dispositivo correto
    echo -e "${RED}⚠️  ATENÇÃO: Você selecionou $DEVICE${NC}"
    confirm "Tem certeza que este é o dispositivo CORRETO?"
    
    # Diretório de destino
    read -p "Digite o diretório de destino (padrão: ~/backups): " DEST_DIR
    DEST_DIR=${DEST_DIR:-~/backups}
    
    # Opção de compactação
    read -p "Deseja compactar o backup? (s/N): " -n 1 -r COMPRESS
    echo ""
    
else
    DEVICE="$1"
    DEST_DIR="${2:-~/backups}"
    check_device "$DEVICE"
fi

# Criar diretório de destino se não existir
mkdir -p "$DEST_DIR"

# Nome do arquivo
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="backup-bts-${DATE}.img"
DEST_FILE="${DEST_DIR}/${FILENAME}"

# Verificar espaço disponível
DEVICE_SIZE=$(blockdev --getsize64 "$DEVICE")
DEVICE_SIZE_GB=$((DEVICE_SIZE / 1024 / 1024 / 1024))
AVAILABLE_SPACE=$(df -B1 "$DEST_DIR" | tail -1 | awk '{print $4}')
AVAILABLE_GB=$((AVAILABLE_SPACE / 1024 / 1024 / 1024))

echo -e "${BLUE}📏 Tamanho do dispositivo: ${DEVICE_SIZE_GB}GB${NC}"
echo -e "${BLUE}💾 Espaço disponível: ${AVAILABLE_GB}GB${NC}\n"

if [ "$AVAILABLE_SPACE" -lt "$DEVICE_SIZE" ]; then
    echo -e "${YELLOW}⚠️  Aviso: Espaço em disco pode ser insuficiente${NC}"
    if [[ ! $COMPRESS =~ ^[SsYy]$ ]]; then
        confirm "Continuar mesmo assim?"
    fi
fi

# Desmontar partições montadas
echo -e "${BLUE}📤 Desmontando partições do dispositivo...${NC}"
umount ${DEVICE}* 2>/dev/null || true
sleep 1

# Criar backup
echo -e "\n${GREEN}🚀 Iniciando backup...${NC}"
echo -e "${BLUE}   Origem: $DEVICE${NC}"
echo -e "${BLUE}   Destino: $DEST_FILE${NC}"

if [[ $COMPRESS =~ ^[SsYy]$ ]]; then
    echo -e "${BLUE}   Compactação: Ativada (.img.gz)${NC}\n"
    DEST_FILE="${DEST_FILE}.gz"
    
    echo -e "${YELLOW}⏳ Criando backup compactado (isso pode levar 15-30 minutos)...${NC}"
    dd if="$DEVICE" bs=4M status=progress | gzip -c > "$DEST_FILE"
else
    echo -e "${BLUE}   Compactação: Desativada${NC}\n"
    
    echo -e "${YELLOW}⏳ Criando backup (isso pode levar 15-30 minutos)...${NC}"
    dd if="$DEVICE" of="$DEST_FILE" bs=4M status=progress
fi

# Verificar se backup foi criado
if [ ! -f "$DEST_FILE" ]; then
    echo -e "${RED}❌ Erro: Backup não foi criado${NC}"
    exit 1
fi

BACKUP_SIZE=$(du -h "$DEST_FILE" | cut -f1)

# Sucesso!
echo -e "\n${GREEN}✅ Backup concluído com sucesso!${NC}\n"
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  📁 Arquivo: $FILENAME"
echo -e "${BLUE}║  📍 Local: $DEST_DIR"
echo -e "${BLUE}║  📊 Tamanho: $BACKUP_SIZE"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}\n"

# Instruções para Balena Etcher
echo -e "${GREEN}🔧 Próximos passos para restaurar em outro microSD:${NC}\n"
echo -e "${YELLOW}1.${NC} Baixe o Balena Etcher: ${BLUE}https://www.balena.io/etcher/${NC}"
echo -e "${YELLOW}2.${NC} Instale e abra o Balena Etcher"
echo -e "${YELLOW}3.${NC} Clique em 'Flash from file' e selecione:"
echo -e "      ${BLUE}$DEST_FILE${NC}"
echo -e "${YELLOW}4.${NC} Insira o novo microSD no leitor de cartão"
echo -e "${YELLOW}5.${NC} Clique em 'Select target' e escolha o novo microSD"
echo -e "${YELLOW}6.${NC} Clique em 'Flash!' e aguarde"
echo -e "${YELLOW}7.${NC} Após concluir, insira o microSD no Raspberry Pi"

if [[ $COMPRESS =~ ^[SsYy]$ ]]; then
    echo -e "\n${BLUE}ℹ️  Nota: O Balena Etcher descompacta arquivos .gz automaticamente${NC}"
fi

echo -e "\n${GREEN}✨ Processo concluído!${NC}\n"

# Opção de transferir arquivo
echo -e "${BLUE}💡 Dica: Para transferir o backup para outro computador:${NC}"
echo -e "   ${YELLOW}scp $DEST_FILE usuario@ip-do-computador:~/Downloads/${NC}\n"

# Salvar informações do backup
INFO_FILE="${DEST_DIR}/backup_info_${DATE}.txt"
cat > "$INFO_FILE" << EOF
Backup MicroSD - Better Seconds System
=======================================
Data: $(date)
Dispositivo: $DEVICE
Tamanho do dispositivo: ${DEVICE_SIZE_GB}GB
Arquivo de backup: $DEST_FILE
Tamanho do backup: $BACKUP_SIZE
Compactado: $([ "$COMPRESS" = "s" ] && echo "Sim" || echo "Não")

Informações do dispositivo:
$(sudo fdisk -l "$DEVICE" 2>/dev/null || echo "N/A")

Sistema Better Seconds:
- Rede Ethernet: 192.168.0.1/24
- Rede WiFi: 10.42.0.1/24 (SSID: bts)
- Serviços: bts.service, mediamtx.service
EOF

echo -e "${GREEN}📝 Informações do backup salvas em: $INFO_FILE${NC}\n"

exit 0
