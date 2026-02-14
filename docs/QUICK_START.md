# 🚀 Quick Start - Instalação do Zero

Guia completo para instalação e configuração do sistema Better Seconds Record em um Raspberry Pi 4B novo.

## 📋 Pré-requisitos

### Hardware Necessário

- **Raspberry Pi 4B** (2GB RAM mínimo, 4GB recomendado)
- **MicroSD Card** 32GB+ (para SO)
- **Pendrive/HD USB** 64GB+ (para gravações)
- **2 Câmeras USB** com H.264 hardware encoding
- **Fonte 5V/3A** oficial Raspberry Pi
- **Cabo de rede** (recomendado para estabilidade)

### Software Base

- **Raspberry Pi OS** (64-bit, Debian 12 Bookworm)
- **Python 3.11+**
- **FFmpeg 4.3+**
- **Git** (para clone do repositório)

---

## 🔧 Passo 1: Preparar o Sistema Operacional

### 1.1 Instalar Raspberry Pi OS

```bash
# Usar Raspberry Pi Imager
# - Escolher: Raspberry Pi OS (64-bit)
# - Configurar WiFi/SSH nas opções avançadas
# - Hostname: bettersecond
# - Usuário: pi
# - Senha: [sua senha]
# - Habilitar SSH
```

### 1.2 Primeiro Boot

```bash
# Conectar via SSH
ssh pi@bettersecond.local

# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Configurar timezone
sudo timedatectl set-timezone America/Sao_Paulo

# Verificar data/hora
date
```

### 1.3 Expandir Filesystem (se necessário)

```bash
sudo raspi-config
# Opção 6 (Advanced Options) > A1 (Expand Filesystem)
# Reboot
sudo reboot
```

---

## 📦 Passo 2: Instalar Dependências do Sistema

### 2.1 Pacotes Essenciais

```bash
# Atualizar lista de pacotes
sudo apt update

# Instalar ferramentas básicas
sudo apt install -y git vim curl wget htop tree

# Instalar FFmpeg
sudo apt install -y ffmpeg

# Instalar V4L Utils (para câmeras)
sudo apt install -y v4l-utils

# Instalar Python e ferramentas
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Instalar dependências para GPIO/LEDs
sudo apt install -y python3-rpi.gpio

# Instalar build essentials (para compilar pacotes Python)
sudo apt install -y build-essential libssl-dev libffi-dev
```

### 2.2 Verificar Versões

```bash
# Verificar FFmpeg
ffmpeg -version
# Esperado: ffmpeg version 4.3.x ou superior

# Verificar Python
python3 --version
# Esperado: Python 3.11.x

# Verificar Git
git --version
```

---

## 🎥 Passo 3: Configurar Câmeras USB

### 3.1 Conectar Câmeras

```bash
# Conectar ambas as câmeras USB
# Aguardar 10-15 segundos para reconhecimento

# Listar dispositivos de vídeo
ls -l /dev/video*
# Esperado: /dev/video0, /dev/video2 (ou video1)

# Verificar detalhes das câmeras
v4l2-ctl --list-devices

# Ver formatos suportados
v4l2-ctl -d /dev/video0 --list-formats-ext
v4l2-ctl -d /dev/video2 --list-formats-ext
# Verificar se suporta H264 (1280x720 ou 1920x1080)
```

### 3.2 Ajustar Permissões (se necessário)

```bash
# Adicionar usuário pi ao grupo video
sudo usermod -a -G video pi

# Relogar ou reboot para aplicar
sudo reboot
```

---

## 💾 Passo 4: Configurar Pendrive USB

### 4.1 Preparar Pendrive

```bash
# Conectar pendrive USB
# Aguardar 5 segundos

# Identificar dispositivo
lsblk
# Procurar por sda, sdb, etc. (geralmente sda)

# Formatar como EXT4 (recomendado para Linux)
sudo mkfs.ext4 -L bts /dev/sda1
# ⚠️ CUIDADO: Isso apaga todos os dados no pendrive!
```

### 4.2 Montar Automaticamente

```bash
# Criar ponto de montagem
sudo mkdir -p /media/pi/usb64gb

# Obter UUID do pendrive
sudo blkid /dev/sda1
# Copiar o UUID (exemplo: 1234-5678)

# Editar fstab para montagem automática
sudo nano /etc/fstab

# Adicionar linha (substituir UUID):
UUID=1234-5678 /media/pi/usb64gb ext4 defaults,nofail 0 2

# Salvar (Ctrl+O, Enter, Ctrl+X)

# Montar
sudo mount -a

# Verificar
df -h | grep usb64gb

# Ajustar permissões
sudo chown -R pi:pi /media/pi/usb64gb
sudo chmod -R 755 /media/pi/usb64gb
```

---

## 📂 Passo 5: Clonar e Configurar Aplicação

### 5.1 Clonar Repositório

```bash
# Ir para home
cd /home/pi

# Clonar repositório (ajustar URL)
git clone https://github.com/seu-usuario/better-seconds-record.git app
# OU copiar arquivos via SCP/SFTP para /home/pi/app

cd /home/pi/app
```

### 5.2 Criar Ambiente Virtual Python

```bash
# Criar venv
python3 -m venv .venv

# Ativar venv
source .venv/bin/activate

# Atualizar pip
pip install --upgrade pip

# Instalar dependências
pip install -r requirements_uploader.txt
```

### 5.3 Criar Estrutura de Diretórios

```bash
# Diretórios no pendrive
sudo mkdir -p /media/pi/usb64gb/bts/stream1
sudo mkdir -p /media/pi/usb64gb/bts/stream2

# Diretórios locais
mkdir -p /home/pi/app/recordings/streams
mkdir -p /home/pi/app/recordings/buffers/video0
mkdir -p /home/pi/app/recordings/buffers/video2
mkdir -p /home/pi/app/recordings/streams/timestamps
mkdir -p /home/pi/app/logs
mkdir -p /home/pi/app/database

# Ajustar permissões
sudo chown -R pi:pi /media/pi/usb64gb/bts
sudo chown -R pi:pi /home/pi/app/recordings
sudo chown -R pi:pi /home/pi/app/logs
sudo chown -R pi:pi /home/pi/app/database
```

### 5.4 Inicializar Banco de Dados

```bash
# Ativar venv (se não estiver)
cd /home/pi/app
source .venv/bin/activate

# Inicializar banco SQLite
python3 database/init_db.py

# Verificar criação
ls -lh database/videos.db
```

---

## 🎯 Passo 6: Configurar Gravação em RAM

### 6.1 Setup Automático

```bash
cd /home/pi/app

# Tornar script executável
chmod +x setup_ram_recording.sh

# Executar configuração
sudo ./setup_ram_recording.sh

# Script irá:
# - Criar /dev/shm/bts/stream1 e stream2
# - Configurar cron (sincronização a cada 1 minuto)
# - Criar .env.ram
# - Criar sync_ram_to_pendrive.sh
```

### 6.2 Verificar Configuração

```bash
# Ver configuração de ambiente
cat /home/pi/app/.env.ram

# Ver cron configurado
crontab -l
# Esperado: * * * * * /home/pi/app/sync_ram_to_pendrive.sh ...

# Verificar diretórios RAM
ls -la /dev/shm/bts/
```

---

## ⚙️ Passo 7: Configurar Serviço Systemd

### 7.1 Criar/Atualizar Serviço

```bash
cd /home/pi/app

# Tornar script executável
chmod +x update_service.sh

# Atualizar serviço
sudo ./update_service.sh

# Ou manualmente:
sudo cp video_uploader.service /etc/systemd/system/better_seconds_record.service
```

### 7.2 Habilitar e Iniciar

```bash
# Recarregar systemd
sudo systemctl daemon-reload

# Habilitar auto-start
sudo systemctl enable better_seconds_record.service

# Iniciar serviço
sudo systemctl start better_seconds_record.service

# Verificar status
sudo systemctl status better_seconds_record.service
```

### 7.3 Verificar Processos

```bash
# Aguardar 10 segundos após start

# Ver processos FFmpeg (esperado: 2)
ps aux | grep ffmpeg | grep -v grep

# Ver processos Gunicorn
ps aux | grep gunicorn | grep -v grep

# Ver logs em tempo real
sudo journalctl -u better_seconds_record.service -f
```

---

## 🔍 Passo 8: Validar Instalação

### 8.1 Verificar Gravação em RAM

```bash
# Aguardar 65 segundos para primeiro segmento

# Ver arquivos em RAM
ls -lh /dev/shm/bts/stream1/
ls -lh /dev/shm/bts/stream2/

# Ver uso de RAM
du -sh /dev/shm/bts
# Esperado: ~20-50MB
```

### 8.2 Verificar Sincronização

```bash
# Aguardar 2-3 minutos

# Ver log de sincronização
tail -20 /home/pi/app/logs/sync_ram.log
# Esperado: Linhas com "Movido: video..."

# Ver arquivos no pendrive
ls -lh /media/pi/usb64gb/bts/stream1/ | head -5
ls -lh /media/pi/usb64gb/bts/stream2/ | head -5
```

### 8.3 Testar API

```bash
# Verificar se API está respondendo
curl http://localhost:5000/health
# Esperado: JSON com status "healthy"

# Registrar evento teste
curl -X POST http://localhost:5000/record/cam1
# Esperado: {"status": "success", ...}

# Ver timestamp registrado
cat /home/pi/app/recordings/streams/timestamps/$(date +%Y%m%d).txt
```

### 8.4 Testar Processamento

```bash
# Processar timestamp registrado
curl -X POST http://localhost:5000/process_timestamps

# Verificar vídeo gerado (após ~30s)
ls -lh /home/pi/app/recordings/streams/$(date +%Y%m%d)/
# Esperado: Arquivo .mp4 e .jpeg
```

---

## 🎛️ Passo 9: Configurações GPIO/LEDs (Opcional)

### 9.1 Habilitar GPIO

```bash
# Já vem habilitado por padrão no Raspberry Pi OS
# Verificar módulos carregados
lsmod | grep gpio
```

### 9.2 Configurar LEDs WS281x (se usar)

```bash
# Instalar biblioteca (já deve estar no requirements)
source /home/pi/app/.venv/bin/activate
pip install rpi-ws281x

# Configurar pinos no código (led_ws281x_new.py)
# GPIO 18 (PWM0) ou GPIO 12 (PWM0 Alt)
```

### 9.3 Testar Botão GPIO

```bash
cd /home/pi/app
source .venv/bin/activate

# Testar GPIO
python3 teste_gpio.py
# Pressionar botão físico conectado ao GPIO configurado
```

---

## 🌐 Passo 10: Configurar Streaming (Opcional)

### 10.1 Instalar MediaMTX

```bash
# Baixar MediaMTX
cd /tmp
wget https://github.com/bluenviron/mediamtx/releases/download/v1.3.0/mediamtx_v1.3.0_linux_arm64v8.tar.gz

# Extrair
tar -xzf mediamtx_v1.3.0_linux_arm64v8.tar.gz

# Mover para local apropriado
sudo mkdir -p /opt/mediamtx
sudo mv mediamtx /opt/mediamtx/
sudo mv mediamtx.yml /opt/mediamtx/

# Copiar configuração customizada (se existir)
sudo cp /home/pi/app/mediamtx.yml /opt/mediamtx/mediamtx.yml

# Criar serviço systemd
sudo nano /etc/systemd/system/mediamtx.service
```

**Conteúdo do mediamtx.service:**
```ini
[Unit]
Description=MediaMTX
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/mediamtx
ExecStart=/opt/mediamtx/mediamtx /opt/mediamtx/mediamtx.yml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar e iniciar
sudo systemctl daemon-reload
sudo systemctl enable mediamtx.service
sudo systemctl start mediamtx.service

# Verificar status
sudo systemctl status mediamtx.service
```

### 10.2 Testar Streaming

```bash
# Verificar se porta 8554 (RTSP) está aberta
sudo netstat -tuln | grep 8554

# Testar RTSP
ffplay rtsp://localhost:8554/live/stream1

# Testar HLS (navegador)
# http://[IP-DO-PI]:8888/live/stream1/
```

---

## 📊 Passo 11: Configurar Monitoramento

### 11.1 Script de Monitoramento

```bash
cd /home/pi/app

# Tornar executável
chmod +x monitor_ram.sh

# Testar
./monitor_ram.sh
```

### 11.2 Cron para Backup (Opcional)

```bash
# Editar crontab
crontab -e

# Adicionar backup diário às 3h
0 3 * * * cp /home/pi/app/database/videos.db ~/backups/videos_$(date +\%Y\%m\%d).db

# Adicionar limpeza semanal (domingos às 4h)
0 4 * * 0 find /media/pi/usb64gb/bts/stream1/ -name "*.ts" -mtime +7 -delete
0 4 * * 0 find /media/pi/usb64gb/bts/stream2/ -name "*.ts" -mtime +7 -delete
```

---

## 🔐 Passo 12: Segurança e Rede

### 12.1 Configurar Firewall (UFW)

```bash
# Instalar UFW
sudo apt install -y ufw

# Permitir SSH
sudo ufw allow 22/tcp

# Permitir API local (opcional - somente se acesso externo)
# sudo ufw allow 5000/tcp

# Permitir RTSP/HLS (opcional)
# sudo ufw allow 8554/tcp
# sudo ufw allow 8888/tcp

# Habilitar firewall
sudo ufw enable

# Ver status
sudo ufw status
```

### 12.2 Configurar IP Estático (Opcional)

```bash
# Editar dhcpcd.conf
sudo nano /etc/dhcpcd.conf

# Adicionar ao final:
interface eth0
static ip_address=192.168.1.187/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8

# Salvar e reiniciar rede
sudo systemctl restart dhcpcd
```

---

## ✅ Passo 13: Checklist Final

### 13.1 Verificações de Sistema

```bash
# [ ] Sistema atualizado
sudo apt update && sudo apt list --upgradable

# [ ] Câmeras detectadas
ls -l /dev/video* && v4l2-ctl --list-devices

# [ ] Pendrive montado
df -h | grep usb64gb

# [ ] Python venv funcionando
source /home/pi/app/.venv/bin/activate && python --version

# [ ] Banco de dados criado
ls -lh /home/pi/app/database/videos.db

# [ ] Serviço habilitado
sudo systemctl is-enabled better_seconds_record.service

# [ ] Serviço rodando
sudo systemctl is-active better_seconds_record.service

# [ ] FFmpeg gravando (2 processos)
ps aux | grep ffmpeg | grep -v grep | wc -l

# [ ] Arquivos em RAM
ls /dev/shm/bts/stream1/ /dev/shm/bts/stream2/

# [ ] Sincronização funcionando
tail -5 /home/pi/app/logs/sync_ram.log

# [ ] API respondendo
curl -s http://localhost:5000/health | python3 -m json.tool
```

### 13.2 Teste de Ponta a Ponta

```bash
# 1. Registrar evento
curl -X POST http://localhost:5000/record/cam1

# 2. Aguardar 30 segundos

# 3. Processar
curl -X POST http://localhost:5000/process_timestamps

# 4. Verificar vídeo gerado
ls -lh /home/pi/app/recordings/streams/$(date +%Y%m%d)/

# 5. Testar playback
ffplay /home/pi/app/recordings/streams/$(date +%Y%m%d)/*.mp4
```

---

## 🚨 Troubleshooting Comum

### Problema: Câmera não detectada

```bash
# Reconectar USB
# Verificar dmesg
dmesg | tail -30

# Verificar módulos carregados
lsmod | grep uvcvideo
```

### Problema: Pendrive não monta

```bash
# Verificar fstab
cat /etc/fstab

# Montar manualmente
sudo mount /dev/sda1 /media/pi/usb64gb

# Verificar erros
sudo dmesg | grep sda
```

### Problema: Serviço não inicia

```bash
# Ver logs detalhados
sudo journalctl -u better_seconds_record.service -xe

# Verificar configuração
sudo systemctl cat better_seconds_record.service

# Testar manualmente
cd /home/pi/app
source .venv/bin/activate
gunicorn -c gunicorn_config.py capture3:app
```

### Problema: Sem espaço em RAM

```bash
# Verificar uso
free -h

# Verificar buffer
du -sh /dev/shm/bts

# Forçar sincronização
/home/pi/app/sync_ram_to_pendrive.sh
```

---

## 📚 Próximos Passos

Após instalação concluída:

1. 📖 Ler [README principal](../README.md)
2. 🔧 Configurar [monitoramento](MONITORING.md)
3. 📡 Configurar [streaming](STREAMING_GUIDE.md)
4. 🚀 Entender [gravação em RAM](RAM_RECORDING_GUIDE.md)
5. 🔄 Configurar [auto-start](AUTO_START_INFO.md)

---

## 📞 Suporte

Problemas na instalação?

1. Verificar logs: `sudo journalctl -u better_seconds_record.service`
2. Testar componentes individualmente
3. Revisar checklist de validação

**Tempo estimado de instalação:** 45-60 minutos

---

**Última atualização:** 2026-02-14  
**Versão do guia:** 1.0  
**Sistema testado:** Raspberry Pi OS (64-bit) Debian 12 Bookworm
