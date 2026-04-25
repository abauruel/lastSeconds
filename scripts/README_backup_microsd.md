# 💾 Script de Backup MicroSD com Balena Etcher

Script automatizado para criar backup de microSD que pode ser restaurado usando Balena Etcher.

## 🚀 Uso Rápido

### Modo Interativo (Recomendado)

```bash
cd /home/pi/app/scripts
sudo ./backup_microsd.sh
```

O script irá te guiar:
1. Listar todos os dispositivos disponíveis
2. Pedir para selecionar o dispositivo correto
3. Confirmar antes de iniciar
4. Perguntar sobre compactação
5. Criar o backup

### Modo Direto

```bash
# Sintaxe
sudo ./backup_microsd.sh [dispositivo] [diretório-destino]

# Exemplos
sudo ./backup_microsd.sh /dev/sdb ~/backups/
sudo ./backup_microsd.sh /dev/mmcblk0 /media/usb/backups/
```

## 📋 Pré-requisitos

- **Sistema Operacional**: Linux ou macOS
- **Permissões**: Executar como root (sudo)
- **Leitor de cartão**: Para conectar o microSD ao computador
- **Espaço em disco**: ~10-30GB dependendo do tamanho do microSD

## 🔧 Recursos do Script

- ✅ **Detecção automática** de dispositivos
- ✅ **Confirmação de segurança** antes de iniciar
- ✅ **Verificação de espaço** em disco
- ✅ **Barra de progresso** em tempo real
- ✅ **Compactação opcional** (economiza ~50% de espaço)
- ✅ **Timestamp automático** nos arquivos
- ✅ **Desmonta partições** automaticamente
- ✅ **Salva informações** sobre o backup
- ✅ **Instruções para Balena Etcher** ao final

## 📖 Passo a Passo Completo

### 1. Criar o Backup

**No computador com leitor de cartão:**

```bash
# 1. Inserir microSD no leitor
# 2. Executar script
cd /home/pi/app/scripts
sudo ./backup_microsd.sh

# 3. Seguir instruções interativas:
#    - Selecionar dispositivo (ex: /dev/sdb)
#    - Confirmar dispositivo
#    - Escolher diretório de destino
#    - Escolher compactação (recomendado: Sim)

# 4. Aguardar conclusão (~15-30 minutos)
```

**Resultado:**
- Arquivo criado: `~/backups/backup-bts-YYYYMMDD_HHMMSS.img.gz`
- Info criada: `~/backups/backup_info_YYYYMMDD_HHMMSS.txt`

### 2. Restaurar com Balena Etcher

**No mesmo computador ou em outro:**

1. **Baixar Balena Etcher**
   - Linux: https://www.balena.io/etcher/
   - Windows: https://www.balena.io/etcher/
   - macOS: https://www.balena.io/etcher/

2. **Abrir Balena Etcher**

3. **Selecionar arquivo**
   - Clicar em "Flash from file"
   - Navegar até `~/backups/backup-bts-YYYYMMDD_HHMMSS.img.gz`
   - Selecionar

4. **Inserir novo microSD**
   - Inserir no leitor de cartão
   - ⚠️ Todos os dados serão apagados!

5. **Selecionar destino**
   - Clicar em "Select target"
   - Escolher o novo microSD
   - Confirmar

6. **Flash!**
   - Clicar em "Flash!"
   - Aguardar (~15-30 minutos)
   - Validação automática ao final

7. **Finalizar**
   - Remover microSD com segurança
   - Inserir no Raspberry Pi
   - Ligar!

## ⚠️ Avisos Importantes

### Dispositivo Correto

```bash
# SEMPRE verifique o dispositivo antes de confirmar
lsblk

# Características do microSD:
# - Tamanho: ~32GB ou ~64GB
# - Tipo: disk (não part)
# - Pode ter nome: mmcblk0, sdb, disk2, etc.
```

### Espaço em Disco

```bash
# Verificar espaço disponível
df -h ~/backups/

# Espaço necessário:
# - MicroSD 32GB: ~10-15GB compactado, ~32GB não compactado
# - MicroSD 64GB: ~15-25GB compactado, ~64GB não compactado
```

### Tempo Estimado

```
Backup não compactado:     15-30 minutos
Backup compactado:         20-40 minutos (recomendado)
Restore com Etcher:        15-30 minutos
```

## 🔍 Troubleshooting

### "Dispositivo não encontrado"

```bash
# Verificar se microSD está conectado
lsblk

# Verificar se está montado
mount | grep sdb

# Se montado, desmontar manualmente
sudo umount /dev/sdb*
```

### "Permissão negada"

```bash
# Sempre usar sudo
sudo ./backup_microsd.sh
```

### "Espaço insuficiente"

```bash
# Usar compactação
# Quando perguntado: Deseja compactar? Digite: s

# Ou escolher outro destino com mais espaço
sudo ./backup_microsd.sh /dev/sdb /media/hd-externo/backups/
```

### "Backup muito lento"

```bash
# Normal: 15-30 minutos
# Fatores que afetam velocidade:
# - Tamanho do microSD
# - Velocidade do leitor de cartão
# - Compactação (se ativada)
# - Uso de disco do sistema
```

## 📊 Exemplo de Output

```
╔══════════════════════════════════════════════════════════════╗
║           Backup MicroSD para Balena Etcher                  ║
║                  Better Seconds System                        ║
╚══════════════════════════════════════════════════════════════╝

🔍 Modo interativo ativado

📋 Dispositivos disponíveis:
NAME        SIZE TYPE MOUNTPOINT
sda       931.5G disk 
├─sda1      512M part /boot/efi
└─sda2      931G part /
sdb        29.7G disk 
├─sdb1      256M part 
└─sdb2     29.5G part 

Digite o dispositivo do microSD (ex: /dev/sdb): /dev/sdb

📊 Informações do dispositivo:
Disk /dev/sdb: 29.72 GiB, 31914983424 bytes, 62333952 sectors
...

⚠️  ATENÇÃO: Você selecionou /dev/sdb
Tem certeza que este é o dispositivo CORRETO? (s/N): s

Digite o diretório de destino (padrão: ~/backups): 
Deseja compactar o backup? (s/N): s

📏 Tamanho do dispositivo: 29GB
💾 Espaço disponível: 150GB

📤 Desmontando partições do dispositivo...

🚀 Iniciando backup...
   Origem: /dev/sdb
   Destino: /home/user/backups/backup-bts-20260418_143022.img.gz
   Compactação: Ativada (.img.gz)

⏳ Criando backup compactado (isso pode levar 15-30 minutos)...
31914983424 bytes (32 GB, 30 GiB) copied, 1245 s, 25.6 MB/s

✅ Backup concluído com sucesso!

╔══════════════════════════════════════════════════════════════╗
║  📁 Arquivo: backup-bts-20260418_143022.img.gz
║  📍 Local: /home/user/backups
║  📊 Tamanho: 12G
╚══════════════════════════════════════════════════════════════╝

🔧 Próximos passos para restaurar em outro microSD:

1. Baixe o Balena Etcher: https://www.balena.io/etcher/
2. Instale e abra o Balena Etcher
3. Clique em 'Flash from file' e selecione:
      /home/user/backups/backup-bts-20260418_143022.img.gz
4. Insira o novo microSD no leitor de cartão
5. Clique em 'Select target' e escolha o novo microSD
6. Clique em 'Flash!' e aguarde
7. Após concluir, insira o microSD no Raspberry Pi

ℹ️  Nota: O Balena Etcher descompacta arquivos .gz automaticamente

✨ Processo concluído!

📝 Informações do backup salvas em: /home/user/backups/backup_info_20260418_143022.txt
```

## 🎯 Casos de Uso

### Backup Regular (Mensal)

```bash
# Agendar backup mensal
# Adicionar no crontab do sistema de backup:
0 2 1 * * /home/pi/app/scripts/backup_microsd.sh /dev/mmcblk0 /media/backups/
```

### Duplicação para Múltiplos Raspberry Pi

```bash
# 1. Criar backup uma vez
sudo ./backup_microsd.sh /dev/sdb ~/master-backup/

# 2. Usar Balena Etcher para gravar em vários microSDs
# Repetir processo de Flash para cada novo microSD
```

### Migração para MicroSD Maior

```bash
# 1. Backup do microSD atual (32GB)
sudo ./backup_microsd.sh /dev/sdb ~/backups/

# 2. Restaurar em microSD maior (64GB) com Etcher

# 3. Após bootar o Raspberry Pi, expandir filesystem:
sudo raspi-config
# Advanced Options > Expand Filesystem
sudo reboot
```

## 📚 Links Úteis

- [Balena Etcher](https://www.balena.io/etcher/)
- [Documentação Deployment](../docs/PRODUCTION_DEPLOYMENT.md)
- [Raspberry Pi Imager](https://www.raspberrypi.com/software/)

---

**Script criado para:** Better Seconds System  
**Versão:** 1.0  
**Data:** Abril 2026
