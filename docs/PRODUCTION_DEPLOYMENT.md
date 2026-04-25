# 🚀 Deployment para Produção - Better Seconds

Este documento descreve o deployment completo do sistema Better Seconds para produção, incluindo todas as configurações de rede, serviços e monitoramento.

## ⚠️ IMPORTANTE - Mudança na v1.1 (29/03/2026)

**Inicialização Manual de Gravações**: A partir da versão 1.1, a aplicação não inicia gravações automaticamente. Após o serviço iniciar, é necessário chamar `POST /start` para começar as gravações.

```bash
# Após iniciar o serviço:
curl -X POST http://192.168.0.1:5000/start
```

Veja mais detalhes na [documentação da API](API_INTEGRATION.md).

---

## 📋 Visão Geral do Sistema

O sistema está configurado com:
- ✅ **Rede Ethernet (eth0):** IP estático para câmeras RTSP
- ✅ **Rede WiFi (wlan0):** Hotspot para acesso remoto
- ✅ **Servidor DHCP:** Distribuição automática de IPs
- ✅ **Serviço Systemd:** Auto-start e gerenciamento profissional
- ✅ **Streaming Server:** MediaMTX para HLS/RTSP/RTMP
- ✅ **API REST:** Flask para controle e eventos
- ✅ **Gravação Contínua:** Segmentos de 60 segundos

---

## 🌐 Configuração de Rede

### Ethernet (eth0) - Câmeras
```
IP: 192.168.0.1/24
DHCP Range: 192.168.0.100-200
Gateway: 192.168.0.1
DNS: 8.8.8.8, 8.8.4.4

Reservas DHCP:
- Câmera IMX415: 192.168.0.210 (MAC: f0:00:06:0b:27:47)
- Câmera IPCAM: 192.168.0.209 (MAC: 5a:5a:00:c6:7e:e9)
```

**Arquivo:** `/etc/dhcpcd.conf`
```ini
# Configuração IP estático para eth0 (câmeras)
interface eth0
static ip_address=192.168.0.1/24
nohook wpa_supplicant
```

### WiFi (wlan0) - Hotspot
```
SSID: bts
Senha: betterseconds
IP: 10.42.0.1/24
DHCP Range: 10.42.0.2-20
Canal: 7
Segurança: WPA2
```

**Arquivo:** `/etc/dhcpcd.conf`
```ini
# Configuração do Hotspot WiFi
interface wlan0
    static ip_address=10.42.0.1/24
    nohook wpa_supplicant
```

### Servidor DHCP (dnsmasq)

**Arquivo:** `/etc/dnsmasq.conf`
```ini
# Interface wlan0 (hotspot)
interface=wlan0
dhcp-range=10.42.0.2,10.42.0.20,255.255.255.0,24h
domain=wlan
address=/gw.wlan/10.42.0.1

# Interface eth0 (câmeras)
interface=eth0
dhcp-range=192.168.0.100,192.168.0.200,255.255.255.0,24h

# Reservas DHCP para câmeras
dhcp-host=f0:00:06:0b:27:47,192.168.0.210,IPCAM-IMX415
dhcp-host=5a:5a:00:c6:7e:e9,192.168.0.209,IPCAM
```

**Gerenciar serviço:**
```bash
sudo systemctl status dnsmasq
sudo systemctl restart dnsmasq
sudo journalctl -u dnsmasq -f
```

---

## 🎬 Serviço BTS (Better Seconds)

### Configuração do Serviço

**Arquivo:** `/etc/systemd/system/bts.service`

```ini
[Unit]
Description=Better Seconds Recording System
After=network-online.target mediamtx.service dnsmasq.service
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=notify
User=pi
Group=pi
WorkingDirectory=/home/pi/app
Environment="PATH=/home/pi/app/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=/home/pi/app/.env
ExecStart=/home/pi/app/.venv/bin/gunicorn --config gunicorn_config.py capture3:app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=bts
TimeoutStartSec=60
TimeoutStopSec=30
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

### Gerenciamento do Serviço

```bash
# Ver status
sudo systemctl status bts.service

# Iniciar/Parar/Reiniciar
sudo systemctl start bts.service
sudo systemctl stop bts.service
sudo systemctl restart bts.service

# Habilitar/Desabilitar auto-start
sudo systemctl enable bts.service
sudo systemctl disable bts.service

# Ver logs em tempo real
sudo journalctl -u bts.service -f

# Ver últimos 100 logs
sudo journalctl -u bts.service -n 100

# Recarregar após editar .service
sudo systemctl daemon-reload
```

### Variáveis de Ambiente

**Arquivo:** `/home/pi/app/.env`

```bash
# Câmeras RTSP
CAMERA_0_RTSP_URL=rtsp://admin:123456@192.168.0.210/stream0
CAMERA_1_RTSP_URL=rtsp://192.168.0.209/live/0/MAIN

# Diretórios de gravação
BTS_STREAM1_DIR=/media/pi/usb64gb/bts/stream1
BTS_STREAM2_DIR=/media/pi/usb64gb/bts/stream2

# API de upload
UPLOAD_API_URL=https://api.example.com/upload
UPLOAD_API_KEY=your-api-key
```

---

## 📡 Servidor de Streaming (MediaMTX)

### Configuração

**Arquivo:** `/home/pi/app/mediamtx_app.yml`

```yaml
paths:
  live/stream1:
    source: publisher
  live/stream2:
    source: publisher

hls: yes
hlsAddress: ":8888"
hlsSegmentCount: 7
hlsSegmentDuration: 2s
hlsAllowOrigin: '*'
```

### URLs de Acesso

**HLS (Navegador):**
- Stream 1: `http://192.168.0.1:8888/live/stream1/index.m3u8`
- Stream 2: `http://192.168.0.1:8888/live/stream2/index.m3u8`

**RTSP (VLC):**
- Stream 1: `rtsp://192.168.0.1:8554/live/stream1`
- Stream 2: `rtsp://192.168.0.1:8554/live/stream2`

**RTMP:**
- Stream 1: `rtmp://192.168.0.1/live/stream1`
- Stream 2: `rtmp://192.168.0.1/live/stream2`

### Gerenciar MediaMTX

```bash
sudo systemctl status mediamtx
sudo systemctl restart mediamtx
sudo journalctl -u mediamtx -f
```

---

## 🔧 API REST

### Endpoints Principais

**Status:**
```bash
GET http://192.168.0.1:5000/status
Response: {"status":"running"}
```

**Registrar Evento:**
```bash
POST http://192.168.0.1:5000/record-event
Body: {
  "cam_id": 0,
  "duration": 10
}
Response: {
  "message": "Event recorded",
  "timestamp": "2026-03-28T11:45:30"
}
```

**Processar Eventos Pendentes:**
```bash
POST http://192.168.0.1:5000/process-pending
Response: {
  "processed": 5,
  "failed": 0
}
```

### Testar API

```bash
# Status
curl http://192.168.0.1:5000/status

# ⚠️ IMPORTANTE (v1.1+): Iniciar gravações primeiro
curl -X POST http://192.168.0.1:5000/start
# Aguardar alguns segundos para FFmpeg iniciar
sleep 5

# Registrar evento cam 1
curl -X POST http://192.168.0.1:5000/record/cam1

# Registrar evento cam 2
curl -X POST http://192.168.0.1:5000/record/cam2

# Registrar evento cam 1 com duração customizada
curl -X POST http://192.168.0.1:5000/record/cam1 \
  -H "Content-Type: application/json" \
  -d '{"duration": 15}'
```

---

## 📊 Monitoramento

### Verificar Saúde do Sistema

```bash
# Status de todos os serviços
sudo systemctl status bts mediamtx dnsmasq dhcpcd

# Processos ativos
ps aux | grep -E "gunicorn|ffmpeg|mediamtx"

# Uso de recursos
htop

# Espaço em disco
df -h /media/pi/usb64gb

# Temperatura
vcgencmd measure_temp
```

### Logs Importantes

```bash
# Serviço BTS
sudo journalctl -u bts.service -f

# MediaMTX
sudo journalctl -u mediamtx.service -f

# DHCP (dnsmasq)
sudo journalctl -u dnsmasq.service -f

# FFmpeg device0
tail -f /media/pi/usb64gb/bts/ffmpeg_device0.log

# FFmpeg device1
tail -f /media/pi/usb64gb/bts/ffmpeg_device2.log

# Gunicorn
tail -f /home/pi/app/logs/gunicorn_error.log
tail -f /home/pi/app/logs/gunicorn_access.log
```

### Verificar Gravações

```bash
# Últimos arquivos stream1
ls -lht /media/pi/usb64gb/bts/stream1/ | head -5

# Últimos arquivos stream2
ls -lht /media/pi/usb64gb/bts/stream2/ | head -5

# Espaço usado
du -sh /media/pi/usb64gb/bts/stream1
du -sh /media/pi/usb64gb/bts/stream2

# Contar segmentos
ls /media/pi/usb64gb/bts/stream1/*.ts | wc -l
ls /media/pi/usb64gb/bts/stream2/*.ts | wc -l
```

---

## 🔍 Troubleshooting

### Câmeras Não Gravam

```bash
# 1. Verificar conectividade
ping -c 3 192.168.0.210
ping -c 3 192.168.0.209

# 2. Testar RTSP manualmente
ffmpeg -i rtsp://admin:123456@192.168.0.210/stream0 -frames:v 1 -f null -
ffmpeg -i rtsp://192.168.0.209/live/0/MAIN -frames:v 1 -f null -

# 3. Ver logs FFmpeg
tail -100 /media/pi/usb64gb/bts/ffmpeg_device0.log
tail -100 /media/pi/usb64gb/bts/ffmpeg_device2.log

# 4. Reiniciar serviço
sudo systemctl restart bts.service
```

### API Não Responde

```bash
# 1. Verificar porta
sudo netstat -tlnp | grep 5000

# 2. Testar local
curl http://localhost:5000/status

# 3. Testar remoto
curl http://192.168.0.1:5000/status

# 4. Ver logs
sudo journalctl -u bts.service -n 50
```

### DHCP Não Funciona

```bash
# 1. Verificar serviço
sudo systemctl status dnsmasq

# 2. Ver leases
cat /var/lib/misc/dnsmasq.leases

# 3. Testar manualmente IP
sudo ip addr add 192.168.0.1/24 dev eth0
sudo ip addr add 10.42.0.1/24 dev wlan0

# 4. Reiniciar
sudo systemctl restart dhcpcd dnsmasq
```

---

## 🔐 Segurança

### Considerações de Segurança

1. **Rede isolada:** Câmeras em rede dedicada (192.168.0.x)
2. **Hotspot com senha:** WPA2 protegido
3. **API sem autenticação:** Considerar adicionar auth em produção
4. **Credenciais RTSP:** Armazenadas em `.env` (não commitar)
5. **Acesso SSH:** Configurar firewall se exposto à internet

### Recomendações

```bash
# Alterar senha do hotspot
sudo nano /etc/hostapd/hostapd.conf
# Editar: wpa_passphrase=betterseconds
sudo systemctl restart hostapd

# Adicionar autenticação na API
# Implementar middleware de autenticação no Flask

# Firewall básico (opcional)
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 5000/tcp  # API
sudo ufw allow 8888/tcp  # HLS
sudo ufw allow 8554/tcp  # RTSP
```

---

## 📈 Performance

### Recursos Utilizados

```
CPU: ~15-25% (idle)
RAM: ~800MB / 2GB
Disco: ~10-30 MB/s (escrita)
Rede: ~5-10 Mbps por câmera
```

### Otimizações

1. **Segmentos de 60s:** Reduz fragmentação
2. **Codec H.264:** Hardware accelerated
3. **Copy mode:** Sem reencoding (`-c:v copy`)
4. **Gunicorn preload:** FFmpeg único em master process
5. **Watchdog inteligente:** Verifica apenas a cada 15s

---

## 🚀 Checklist de Deployment

- [ ] Sistema operacional atualizado
- [ ] Rede configurada (eth0 + wlan0)
- [ ] DHCP configurado com reservas
- [ ] Câmeras acessíveis e testadas
- [ ] Serviço bts.service criado e habilitado
- [ ] MediaMTX configurado e rodando
- [ ] API testada e respondendo
- [ ] Gravações verificadas
- [ ] Logs configurados
- [ ] Documentação atualizada
- [ ] Backup de configurações

---

## � Backup e Restore do MicroSD
### 🚀 Método Recomendado: Script Automatizado

**Use o script incluído para facilitar o processo:**

```bash
# No diretório do projeto
cd /home/pi/app/scripts

# Modo interativo (recomendado)
sudo ./backup_microsd.sh

# Ou especificando dispositivo e destino
sudo ./backup_microsd.sh /dev/sdb ~/backups/
```

**O script faz:**
- ✅ Detecta e lista dispositivos automaticamente
- ✅ Confirma dispositivo correto antes de iniciar
- ✅ Cria backup com nome timestamped
- ✅ Opção de compactação automática
- ✅ Verifica espaço em disco disponível
- ✅ Fornece instruções para Balena Etcher
- ✅ Salva informações do backup

**Após o backup, use o Balena Etcher para restaurar:**
1. Baixe: https://www.balena.io/etcher/
2. Abra e selecione o arquivo `.img` ou `.img.gz` criado
3. Selecione o novo microSD de destino
4. Clique em "Flash!"

**📖 Documentação completa:** [README_backup_microsd.md](../scripts/README_backup_microsd.md)

---
### Backup Completo do MicroSD (Linux/macOS)

**1. Identificar o dispositivo do microSD:**
```bash
# No computador com leitor de cartão
lsblk
# ou
sudo fdisk -l

# Exemplo: /dev/sdb (Linux) ou /dev/disk2 (macOS)
```

**2. Criar backup completo (imagem .img):**
```bash
# Linux
sudo dd if=/dev/sdb of=~/backup-bts-$(date +%Y%m%d).img bs=4M status=progress

# macOS
sudo dd if=/dev/rdisk2 of=~/backup-bts-$(date +%Y%m%d).img bs=4m

# ⚠️ CUIDADO: Verifique o dispositivo correto! dd pode apagar dados.
```

**3. Backup compactado (economiza espaço):**
```bash
# Compactar durante backup
sudo dd if=/dev/sdb bs=4M status=progress | gzip > ~/backup-bts-$(date +%Y%m%d).img.gz

# Estimar tempo: ~15-30 min para 32GB
```

### Restore do Backup

**1. Restaurar imagem completa:**
```bash
# Linux - descompactar e gravar
gunzip -c ~/backup-bts-20260418.img.gz | sudo dd of=/dev/sdb bs=4M status=progress

# Ou se não estiver compactado
sudo dd if=~/backup-bts-20260418.img of=/dev/sdb bs=4M status=progress
```

**2. Expandir partição após restore (se microSD maior):**
```bash
# Após bootar o Raspberry Pi
sudo raspi-config
# Selecionar: Advanced Options > Expand Filesystem
sudo reboot
```

### Backup Usando Raspberry Pi Imager (Windows/Linux/macOS)

**Mais fácil e recomendado:**

1. Baixar [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Inserir microSD no leitor
3. Escolher: `CHOOSE OS > Use custom`
4. Selecionar arquivo `.img` do backup
5. Escolher o microSD de destino
6. Clicar em `Write`

### Backup Apenas das Configurações (Mais Rápido)

```bash
# Executar no Raspberry Pi
# Criar diretório de backup
mkdir -p ~/config-backup-$(date +%Y%m%d)
cd ~/config-backup-$(date +%Y%m%d)

# Copiar configurações de rede
sudo cp /etc/dhcpcd.conf .
sudo cp /etc/dnsmasq.conf .
sudo cp /etc/hostapd/hostapd.conf .

# Copiar serviços
sudo cp /etc/systemd/system/bts.service .
sudo cp /etc/systemd/system/mediamtx.service .

# Copiar aplicação
cp -r ~/app .

# Compactar tudo
cd ~
tar -czf config-backup-$(date +%Y%m%d).tar.gz config-backup-$(date +%Y%m%d)/

# Transferir para outro computador
# Via SCP: scp pi@192.168.0.1:~/config-backup-*.tar.gz .
```

### Restore das Configurações

```bash
# No novo Raspberry Pi (após instalar Raspberry Pi OS)
tar -xzf config-backup-20260418.tar.gz
cd config-backup-20260418/

# Restaurar rede
sudo cp dhcpcd.conf /etc/
sudo cp dnsmasq.conf /etc/
sudo cp hostapd.conf /etc/

# Restaurar serviços
sudo cp bts.service /etc/systemd/system/
sudo cp mediamtx.service /etc/systemd/system/

# Restaurar aplicação
cp -r app ~/

# Recarregar serviços
sudo systemctl daemon-reload
sudo systemctl enable bts mediamtx dnsmasq
sudo reboot
```

### Clonagem Direta (microSD para microSD)

```bash
# Com 2 leitores de cartão conectados
# Identificar origem e destino
lsblk

# Clonar direto (mais rápido)
sudo dd if=/dev/sdb of=/dev/sdc bs=4M status=progress

# ⚠️ Confirme qual é origem e qual é destino!
```

### Ferramentas Alternativas

**Win32 Disk Imager (Windows):**
- Download: https://sourceforge.net/projects/win32diskimager/
- Interface gráfica simples
- Suporta backup e restore

**Etcher (Multiplataforma):**
- Download: https://www.balena.io/etcher/
- Interface moderna
- Validação automática

**PiShrink (Linux - reduz tamanho do backup):**
```bash
# Reduzir imagem antes de backup
wget https://raw.githubusercontent.com/Drewsif/PiShrink/master/pishrink.sh
chmod +x pishrink.sh
sudo ./pishrink.sh backup-bts.img backup-bts-shrunk.img
```

### Checklist de Backup

- [ ] Identificar dispositivo correto (`lsblk` / `fdisk -l`)
- [ ] Verificar espaço em disco disponível
- [ ] Criar backup compactado (.img.gz)
- [ ] Testar restore em microSD de teste
- [ ] Armazenar backup em local seguro
- [ ] Documentar data e versão do sistema
- [ ] Backup recorrente (mensal recomendado)

### Tamanhos Aproximados

```
MicroSD 32GB: ~10-15GB compactado
MicroSD 64GB: ~15-25GB compactado
Tempo backup: ~15-30 minutos
Tempo restore: ~15-30 minutos
```

---

## �📚 Documentos Relacionados

- [Auto Start Info](AUTO_START_INFO.md) - Detalhes do serviço systemd
- [Quick Start](QUICK_START.md) - Instalação do zero
- [API Examples](API_EXAMPLES.md) - Exemplos de uso da API
- [Monitoring](MONITORING.md) - Ferramentas de monitoramento
- [Streaming Guide](STREAMING_GUIDE.md) - Acesso aos streams

---

**Status:** ✅ Sistema em Produção  
**Versão:** 2.0  
**Data:** 28/03/2026
