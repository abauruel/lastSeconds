# 🔄 Configuração de Inicialização Automática - Serviço Systemd

## ✅ Serviço de Produção - BTS (Better Seconds)

O sistema está configurado com um **serviço systemd** para inicialização automática e gerenciamento profissional da aplicação.

### 📋 Informações do Serviço

**Nome:** `bts.service`  
**Descrição:** Better Seconds Recording System  
**Localização:** `/etc/systemd/system/bts.service`  
**Status:** ✅ Habilitado (auto-start)

### 🚀 O que acontece automaticamente ao reiniciar:

#### 1. **Inicialização da Rede**
- ✅ **eth0:** IP estático `192.168.0.1/24` (câmeras)
- ✅ **wlan0:** IP estático `10.42.0.1/24` (hotspot WiFi)
- ✅ **DHCP:** Servidor dnsmasq ativo em ambas interfaces
- ✅ **Câmeras:** IPs reservados (210 e 209)

#### 2. **Serviço MediaMTX**
- ✅ **Status:** `active (running)`
- ✅ **Portas:** RTSP (8554), HLS (8888), RTMP (1935)
- ✅ **Streams:** `/live/stream1` e `/live/stream2`

#### 3. **Serviço BTS** 
- ✅ **Dependências:** Aguarda `network-online.target`, `mediamtx.service`, `dnsmasq.service`
- ✅ **Workers:** 2 processos Gunicorn (preload_app=True)
- ✅ **FFmpeg:** 2 processos (câmera 0 e câmera 1)
- ✅ **Watchdog:** Monitoramento de saúde a cada 15s
- ✅ **API:** Flask na porta 5000
- ✅ **Gravação:** Segmentos de 60s em `/media/pi/usb64gb/bts/`

### 📊 Ordem de Inicialização:

```
1. Sistema inicia
   ↓
2. Rede configurada (eth0 + wlan0)
   ↓
3. DHCP (dnsmasq) inicia
   ↓
4. Câmeras obtêm IPs fixos (210 e 209)
   ↓
5. MediaMTX inicia (streaming server)
   ↓
6. Serviço BTS inicia
   ├─ Gunicorn master process
   ├─ 2 workers Flask
   ├─ FFmpeg process 0 (stream1)
   └─ FFmpeg process 1 (stream2)
   ↓
7. Watchdog monitora processos
   ↓
8. Sistema pronto (API em 5000, HLS em 8888)
```

### 🛠️ Comandos de Gerenciamento:

```bash
# Ver status completo
sudo systemctl status bts.service

# Iniciar serviço
sudo systemctl start bts.service

# Parar serviço
sudo systemctl stop bts.service

# Reiniciar serviço
sudo systemctl restart bts.service

# Ver logs em tempo real
sudo journalctl -u bts.service -f

# Ver últimos 100 logs
sudo journalctl -u bts.service -n 100

# Desabilitar auto-start (se necessário)
sudo systemctl disable bts.service

# Habilitar auto-start
sudo systemctl enable bts.service

# Recarregar configuração após editar .service
sudo systemctl daemon-reload
```

### 📝 Configuração do Serviço

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

# Timeout para operações de vídeo
TimeoutStartSec=60
TimeoutStopSec=30

# Recursos
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

### 🔍 Validação Pós-Reboot:

```bash
# 1. Verificar serviço ativo
sudo systemctl is-active bts.service
# Deve retornar: active

# 2. Verificar processos rodando
ps aux | grep -E "gunicorn|ffmpeg" | grep -v grep
# Deve mostrar: gunicorn (3 processos) + ffmpeg (2 processos)

# 3. Testar API
curl http://localhost:5000/status
# Deve retornar: {"status":"running"}

# 4. Verificar câmeras online
ping -c 2 192.168.0.210  # Câmera IMX415
ping -c 2 192.168.0.209  # Câmera IPCAM

# 5. Verificar gravação
ls -lh /media/pi/usb64gb/bts/stream1/ | tail -3
ls -lh /media/pi/usb64gb/bts/stream2/ | tail -3
# Deve mostrar arquivos .ts recentes

# 6. Testar stream HLS
curl -I http://localhost:8888/live/stream1/index.m3u8
# Deve retornar: 200 OK
```

### 📡 URLs de Acesso:

**API REST:**
- Status: `http://192.168.0.1:5000/status`
- Registrar evento: `http://192.168.0.1:5000/record-event`

**Streams HLS:**
- Stream 1 (IMX415): `http://192.168.0.1:8888/live/stream1/index.m3u8`
- Stream 2 (IPCAM): `http://192.168.0.1:8888/live/stream2/index.m3u8`

**Hotspot WiFi:**
- SSID: `bts`
- Senha: `betterseconds`
- IP: `10.42.0.1`

### ⚙️ Recursos do Serviço:

✅ **Auto-restart:** Reinicia automaticamente em caso de falha  
✅ **Logging:** Logs centralizados via journald  
✅ **Dependências:** Aguarda rede e serviços necessários  
✅ **Timeout:** Configurado para operações de vídeo  
✅ **Recursos:** Limites adequados para processos pesados  
✅ **Preload:** Gunicorn com preload_app para FFmpeg único  

### ⚠️ Importante:

- **Tempo de inicialização:** ~30-60 segundos após boot
- **Primeira gravação:** Aparece após ~65 segundos
- **Watchdog ativo:** Auto-recuperação de processos mortos
- **Logs persistentes:** `/home/pi/app/logs/` + journald
- **Câmeras RTSP:** Devem estar acessíveis nas URLs configuradas no `.env`

### 🔧 Troubleshooting:

**Serviço não inicia:**
```bash
# Ver erros detalhados
sudo journalctl -u bts.service -n 50 --no-pager

# Testar manualmente
cd /home/pi/app
source .venv/bin/activate
gunicorn --config gunicorn_config.py capture3:app
```

**FFmpeg não grava:**
```bash
# Verificar conectividade com câmeras
ping 192.168.0.210
ping 192.168.0.209

# Testar stream RTSP manualmente
ffmpeg -i rtsp://admin:123456@192.168.0.210/stream0 -frames:v 1 -f null -

# Ver logs do FFmpeg
tail -f /media/pi/usb64gb/bts/ffmpeg_device0.log
tail -f /media/pi/usb64gb/bts/ffmpeg_device2.log
```

**API não responde:**
```bash
# Verificar se porta está em uso
sudo netstat -tlnp | grep 5000

# Testar bind do gunicorn
curl -v http://localhost:5000/status
curl -v http://192.168.0.1:5000/status
```

### 📚 Documentos Relacionados:

- [Quick Start](QUICK_START.md) - Instalação completa
- [Monitoramento](MONITORING.md) - Ferramentas de monitoramento
- [API Examples](API_EXAMPLES.md) - Exemplos de uso da API
- [Streaming Guide](STREAMING_GUIDE.md) - Acesso aos streams

---

**Status do Sistema:** ✅ Pronto para Produção  
**Última Atualização:** 28/03/2026
tail -5 /home/pi/app/logs/sync_ram.log
# Deve mostrar sincronizações recentes
```

### 📊 Configuração Atual:

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| Buffer RAM | 100 MB | ~5 minutos de vídeo |
| Retenção RAM | 1 minuto | Arquivos movidos após 1 min |
| Sincronização | 1 minuto | Cron executa a cada 1 min |
| Janela de risco | ~2 minutos | Perda máxima em caso de queda |
| Auto-start | ✅ Sim | Systemd enabled |

---

**Última atualização:** 2026-02-14  
**Status:** 🟢 Produção - Totalmente Automatizado
