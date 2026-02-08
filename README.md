# Better Seconds Record - Sistema de Gravação por Eventos

Sistema de gravação de vídeo por eventos baseado em Raspberry Pi 4B que captura automaticamente os últimos 10 segundos antes de um evento detectado.

## 📋 Visão Geral

O sistema mantém duas câmeras gravando continuamente em segmentos de **5 minutos**, armazenando os **últimos 5 horas** (60 segmentos) de cada câmera. Quando um evento é detectado (botão pressionado ou chamada de API), o sistema registra o timestamp e pode posteriormente extrair um clipe de 10 segundos (5s antes + 5s depois do evento).

### Características Principais

- ✅ **Resposta instantânea**: Registro de eventos em <100ms
- ✅ **Processamento assíncrono**: Extração de vídeos sob demanda
- ✅ **Buffer inteligente**: 5 horas de histórico por câmera
- ✅ **Uso eficiente de recursos**: Otimizado para Raspberry Pi 4B (2GB RAM)
- ✅ **Feedback visual**: LEDs indicam quando evento foi registrado
- ✅ **Integração com banco de dados**: SQLite para gerenciamento de vídeos

## 🏗️ Arquitetura

### Componentes

```
┌─────────────────────────────────────────────────────────┐
│                    Raspberry Pi 4B                      │
│                                                         │
│  ┌─────────────┐      ┌──────────────┐                │
│  │  Camera 1   │──────▶│   FFmpeg     │                │
│  │ /dev/video0 │      │  Process 0   │                │
│  └─────────────┘      └──────┬───────┘                │
│                               │                         │
│  ┌─────────────┐             │  Segmentos 5min        │
│  │  Camera 2   │──────▶      │  (60 arquivos)         │
│  │ /dev/video2 │      │      ▼                         │
│  └─────────────┘      │  ┌────────────────┐           │
│                       │  │  /media/pi/     │           │
│  ┌─────────────┐     │  │  usb64gb/bts/   │           │
│  │   Button    │─────┼──▶│  stream1/       │           │
│  │   GPIO      │     │  │  stream2/       │           │
│  └─────────────┘     │  └────────────────┘           │
│                      │                                 │
│  ┌──────────────────▼──────────────────┐             │
│  │    Flask API (Port 5000)            │             │
│  │  - Registro de timestamps           │             │
│  │  - Processamento manual             │             │
│  │  - Gerenciamento de vídeos          │             │
│  └────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

### Fluxo de Dados

1. **Gravação Contínua**
   - FFmpeg captura vídeo de ambas as câmeras
   - Gera segmentos de 5 minutos com timestamps no nome
   - Mantém buffer circular de 60 arquivos (5 horas)
   - Formato: `video0_YYYYMMDD_HHMMSS.mp4`

2. **Detecção de Evento**
   - Botão GPIO ou chamada de API
   - Timestamp registrado em `timestamps/YYYYMMDD.txt`
   - LED pisca para feedback visual
   - Resposta instantânea ao usuário

3. **Processamento Manual**
   - Chamada à rota `/process_timestamps`
   - Sistema busca arquivo de segmento que contém o timestamp
   - Extrai 10 segundos usando FFmpeg
   - Gera thumbnail e salva no banco de dados

## 🚀 Instalação

### Dependências

```bash
# Instalar dependências do sistema
sudo apt-get update
sudo apt-get install ffmpeg python3-pip

# Instalar dependências Python
pip3 install -r requirements_uploader.txt

# Dependências principais
# - Flask
# - SQLAlchemy
# - RPi.GPIO
# - rpi_ws281x (LEDs)
```

### Configuração

1. **Criar diretórios necessários**

```bash
# Criar estrutura de diretórios
sudo mkdir -p /media/pi/usb64gb/bts/stream1
sudo mkdir -p /media/pi/usb64gb/bts/stream2
sudo mkdir -p /home/pi/app/recordings/streams
sudo mkdir -p /home/pi/app/recordings/buffers/video0
sudo mkdir -p /home/pi/app/recordings/buffers/video2

# Ajustar permissões
sudo chown -R pi:pi /media/pi/usb64gb/bts
sudo chown -R pi:pi /home/pi/app/recordings
```

2. **Configurar serviço systemd**

```bash
sudo cp video_uploader.service /etc/systemd/system/better_seconds_record.service
sudo systemctl daemon-reload
sudo systemctl enable better_seconds_record.service
sudo systemctl start better_seconds_record.service
```

## 📡 API Endpoints

### Gravação de Eventos

#### POST `/record/cam1`
Registra evento da câmera 1 (instantâneo)

```bash
curl -X POST http://localhost:5000/record/cam1
```

**Resposta:**
```json
{
  "status": "success",
  "message": "Evento cam1 registrado"
}
```

#### POST `/record/cam2`
Registra evento da câmera 2 (instantâneo)

```bash
curl -X POST http://localhost:5000/record/cam2
```

### Processamento de Timestamps

#### POST `/process_timestamps`
Processa timestamps pendentes e gera vídeos

**Processar últimos 3 dias (padrão):**
```bash
curl -X POST http://localhost:5000/process_timestamps
```

**Processar dia específico:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"date":"20260208"}' \
  http://localhost:5000/process_timestamps
```

**Processar últimos N dias:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"days_back":7}' \
  http://localhost:5000/process_timestamps
```

**Resposta:**
```json
{
  "status": "success",
  "processed": 5,
  "failed": 2,
  "dates": ["20260208", "20260207"]
}
```

### Gerenciamento do Sistema

#### POST `/start`
Inicia processos FFmpeg

```bash
curl -X POST http://localhost:5000/start
```

#### POST `/stop`
Para processos FFmpeg

```bash
curl -X POST http://localhost:5000/stop
```

#### PUT `/update_status`
Atualiza status de um vídeo no banco de dados

```bash
curl -X PUT -H "Content-Type: application/json" \
  -d '{"name":"rpi4bmobile_stream1_20260208_133935.mp4","status":"uploaded"}' \
  http://localhost:5000/update_status
```

**Status válidos:**
- `pending` - Aguardando upload
- `uploading` - Upload em andamento
- `uploaded` - Upload concluído
- `error` - Erro no processamento

## 📁 Estrutura de Arquivos

```
/home/pi/app/
├── ffmpeg_manager.py          # Gerenciador principal do FFmpeg
├── app.py                      # Aplicação Flask
├── database/
│   ├── models.py              # Modelos SQLAlchemy
│   ├── db_config.py           # Configuração do banco
│   └── init_db.py             # Inicialização do banco
├── routes/
│   ├── ffmpeg_routes.py       # Rotas da API
│   └── status_routes.py       # Rotas de status
├── recordings/
│   └── streams/
│       ├── timestamps/        # Arquivos de timestamp
│       │   └── YYYYMMDD.txt  # Um arquivo por dia
│       └── YYYYMMDD/          # Vídeos processados por dia
│           ├── rpi4bmobile_stream1_*.mp4
│           ├── rpi4bmobile_stream1_*.mp4.jpeg
│           └── ...
└── video_uploader.service     # Serviço systemd

/media/pi/usb64gb/bts/
├── stream1/                   # Segmentos da câmera 1
│   └── video0_YYYYMMDD_HHMMSS.mp4
├── stream2/                   # Segmentos da câmera 2
│   └── video2_YYYYMMDD_HHMMSS.mp4
├── ffmpeg_device0.log        # Logs do FFmpeg câmera 1
└── ffmpeg_device2.log        # Logs do FFmpeg câmera 2
```

## 🔧 Configuração Avançada

### Parâmetros do FFmpeg

**Tempo de segmento:**
```python
segment_time=300  # 5 minutos (300 segundos)
```

**Buffer circular:**
```python
segment_wrap=60   # 60 arquivos = 5 horas
```

**Cálculo de espaço em disco:**
- Bitrate médio: 2-3 Mbps
- 5 horas × 2 streams = 10 horas
- Espaço necessário: ~9-13 GB
- Disco disponível: 64GB ✓

### Ajuste de Duração do Buffer

Para alterar o tempo de histórico:

```python
# 10 horas (120 segmentos)
segment_wrap=120

# 2 horas (24 segmentos)  
segment_wrap=24
```

### Ajuste do Clipe Extraído

```python
# Alterar duração do clipe
"-t", "15",  # 15 segundos ao invés de 10

# Alterar offset antes do evento
offset_seconds = max(0, offset_in_file - 10)  # 10s antes
```

## 🐛 Troubleshooting

### Problema: Vídeos vazios ou corrompidos

**Causa:** Tentativa de extração de arquivo ainda sendo escrito pelo FFmpeg

**Solução:** O sistema já inclui verificações:
- Arquivo deve ter >100KB
- Arquivo deve ter >10s desde última modificação

**Verificar manualmente:**
```bash
# Verificar se arquivo está completo
ffprobe /media/pi/usb64gb/bts/stream1/video0_YYYYMMDD_HHMMSS.mp4

# Se mostrar "moov atom not found", o arquivo ainda está sendo escrito
```

### Problema: Eventos não processados

**Verificar timestamps pendentes:**
```bash
cat /home/pi/app/recordings/streams/timestamps/$(date +%Y%m%d).txt
```

**Processar manualmente:**
```bash
curl -X POST http://localhost:5000/process_timestamps
```

### Problema: FFmpeg não iniciando

**Verificar logs:**
```bash
tail -f /media/pi/usb64gb/bts/ffmpeg_device0.log
tail -f /media/pi/usb64gb/bts/ffmpeg_device2.log
```

**Verificar câmeras:**
```bash
ls -l /dev/video*
v4l2-ctl --list-devices
```

### Problema: Espaço em disco

**Verificar uso:**
```bash
df -h /media/pi/usb64gb/
du -sh /media/pi/usb64gb/bts/stream*
```

**Limpar vídeos antigos:**
```bash
# Deletar segmentos com mais de 6 horas
find /media/pi/usb64gb/bts/stream1/ -name "*.mp4" -mmin +360 -delete
find /media/pi/usb64gb/bts/stream2/ -name "*.mp4" -mmin +360 -delete
```

## 📊 Monitoramento

### Logs do Serviço

```bash
# Logs em tempo real
journalctl -u better_seconds_record.service -f

# Últimas 50 linhas
journalctl -u better_seconds_record.service -n 50

# Filtrar por erros
journalctl -u better_seconds_record.service | grep -i error
```

### Status do Sistema

```bash
# Status do serviço
systemctl status better_seconds_record.service

# Processos FFmpeg rodando
ps aux | grep ffmpeg

# Uso de CPU/RAM
top -p $(pgrep -d',' ffmpeg)
```

### Banco de Dados

```bash
# Conectar ao SQLite
sqlite3 /home/pi/app/database/videos.db

# Listar vídeos pendentes
SELECT * FROM videos WHERE status = 'pending';

# Contar vídeos por status
SELECT status, COUNT(*) FROM videos GROUP BY status;
```

## 🔒 Segurança

- API exposta apenas em localhost (127.0.0.1)
- Para acesso remoto, usar túnel SSH ou VPN
- Logs sensíveis não incluem credenciais
- Permissões de arquivo restritas ao usuário `pi`

## 📝 Formato do Arquivo de Timestamps

Cada linha no arquivo `timestamps/YYYYMMDD.txt`:

```json
{
  "timestamp_epoch": 1770567030,
  "timestamp_iso": "2026-02-08T13:10:30.915529",
  "cam_id": 0,
  "status": "pending",
  "processed_at": "2026-02-08T13:25:27.541898"
}
```

**Campos:**
- `timestamp_epoch`: Unix timestamp
- `timestamp_iso`: ISO 8601 timestamp
- `cam_id`: 0 (câmera 1) ou 1 (câmera 2)
- `status`: pending, processed, ou failed
- `processed_at`: Quando foi processado (opcional)

## 🎯 Casos de Uso

### 1. Gravação manual de evento

```bash
# Pressionar botão físico OU
curl -X POST http://localhost:5000/record/cam1

# Processar depois (pode ser minutos ou horas depois)
curl -X POST http://localhost:5000/process_timestamps
```

### 2. Processamento em lote

```bash
# Cron job para processar todas as noites às 2h
0 2 * * * curl -X POST http://localhost:5000/process_timestamps
```

### 3. Integração com sistema de alarme

```python
import requests

def on_alarm_triggered():
    # Registrar evento
    requests.post('http://localhost:5000/record/cam1')
    requests.post('http://localhost:5000/record/cam2')
    
    # Processar imediatamente se necessário
    requests.post('http://localhost:5000/process_timestamps')
```

## 🔄 Atualizações e Manutenção

```bash
# Reiniciar serviço após mudanças
sudo systemctl restart better_seconds_record.service

# Ver logs de inicialização
journalctl -u better_seconds_record.service -b

# Backup do banco de dados
cp /home/pi/app/database/videos.db ~/backup_$(date +%Y%m%d).db
```

## 📞 Suporte

Para problemas ou dúvidas:
1. Verificar logs: `journalctl -u better_seconds_record.service`
2. Verificar espaço em disco: `df -h`
3. Verificar processos: `ps aux | grep ffmpeg`

## 📜 Licença

Proprietary - Uso interno apenas

---

**Versão:** 2.0  
**Última atualização:** 8 de fevereiro de 2026  
**Hardware:** Raspberry Pi 4B (2GB RAM)  
**Sistema Operacional:** Raspberry Pi OS (Debian 12)
