# Better Seconds Record - Sistema de Gravação por Eventos

Sistema de gravação de vídeo por eventos baseado em Raspberry Pi 4B que captura automaticamente os últimos 10 segundos antes de um evento detectado.

## 📋 Visão Geral

O sistema mantém duas câmeras gravando continuamente em segmentos de **1 minuto** (60 segundos), com capacidade de armazenar até **23 horas** (1400 segmentos) de cada câmera. Quando um evento é detectado (botão pressionado ou chamada de API), o sistema registra o timestamp e pode posteriormente extrair um clipe dos **últimos N segundos ANTES do evento** (padrão: 10 segundos).

### Características Principais

- ✅ **Resposta instantânea**: Registro de eventos em <100ms
- ✅ **Processamento assíncrono**: Extração de vídeos sob demanda
- ✅ **Buffer inteligente**: Até 300 horas de histórico por câmera
- ✅ **Uso eficiente de recursos**: Otimizado para Raspberry Pi 4B (2GB RAM)
- ✅ **Feedback visual**: LEDs indicam quando evento foi registrado
- ✅ **Integração com banco de dados**: SQLite para gerenciamento de vídeos
- ✅ **Segmentação robusta**: Previne arquivos corrompidos com `segment_atclocktime`
- ✅ **Watchdog inteligente**: Monitora saúde dos processos sem falsos-positivos
- ✅ **Auto-recuperação**: Sistema se recupera automaticamente de falhas
- ✅ **Logging detalhado**: Rastreamento completo de restarts e eventos
- ✅ **Extração inteligente**: Recupera sempre segundos ANTES do evento, busca arquivos anteriores quando necessário
- ✅ **Validação temporal**: Garante continuidade entre segmentos (gap máximo 90s)
- ✅ **Duração customizável**: Suporta clipes de qualquer duração via API
- ✅ **Gravação em RAM**: Buffer em tmpfs elimina corrupção por I/O lento do pendrive
- ✅ **Sincronização automática**: Cron move arquivos para pendrive a cada 1 minuto
- ✅ **Alta performance**: ~1000 MB/s em RAM vs ~10-30 MB/s em pendrive USB

## 📚 Documentação

### 🚀 Instalação e Configuração
- **[Quick Start](docs/QUICK_START.md)** - ⭐ Guia completo de instalação do zero
- **[Guia de Gravação em RAM](docs/RAM_RECORDING_GUIDE.md)** - Sistema de buffer em tmpfs e sincronização automática
- **[Inicialização Automática](docs/AUTO_START_INFO.md)** - Configuração de auto-start após reboot

### 📊 Operação e Monitoramento
- **[Monitoramento](docs/MONITORING.md)** - Ferramentas de monitoramento e health checks
- **[Processamento de Timestamps](docs/PROCESS_TIMESTAMPS_USAGE.md)** - Como processar eventos registrados
- **[Exemplos de API](docs/API_EXAMPLES.md)** - Exemplos de uso da API REST

### 📹 Streaming e Câmeras
- **[Guia de Streaming](docs/STREAMING_GUIDE.md)** - Como visualizar câmeras ao vivo (HLS/RTMP)
- **[Acesso às Câmeras](docs/ACESSO_CAMERAS.md)** - Informações de acesso às câmeras
- **[Diagnóstico de Streams](docs/DIAGNOSTICO_STREAMS.md)** - Troubleshooting de streaming
- **[Enumeração Dinâmica de Câmeras](docs/CAMERA_DEVICE_ENUMERATION.md)** - ⭐ Solução para problema: câmera 2 não detectada

### 🔧 Manutenção e Troubleshooting
- **[Correção de Câmeras Não Detectadas](CAMERA_DETECTION_FIX.md)** - Passo-a-passo para resolver video2→video3

- **[Correção de Arquivos Corrompidos](docs/CORRUPTED_FILES_FIX.md)** - Como lidar com arquivos corrompidos
- **[Skills](docs/SKILLS.md)** - Habilidades e capacidades do sistema

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
│  ┌─────────────┐             │  Segmentos 1min        │
│  │  Camera 2   │──────▶      │  (até 1400 arquivos)  │
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

1. **Gravação Contínua (RAM)**
   - FFmpeg captura vídeo de ambas as câmeras
   - Gera segmentos de 1 minuto direto em **RAM** (`/dev/shm/bts/`)
   - Elimina timeouts e corrupção por I/O lento
   - Usa `segment_atclocktime` para evitar arquivos corrompidos
   - Formato: `video0_YYYYMMDD_HHMMSS.ts` (MPEG-TS para melhor streaming)
   - Watchdog monitora saúde dos processos a cada 60s
   - **Sincronização:** Cron move arquivos >1min para pendrive a cada 1 minuto

2. **Detecção de Evento**
   - Botão GPIO ou chamada de API
   - Timestamp registrado em `timestamps/YYYYMMDD.txt`
   - LED pisca para feedback visual
   - Resposta instantânea ao usuário (<100ms)

3. **Processamento Manual**
   - Chamada à rota `/process_timestamps`
   - Sistema busca arquivo(s) de segmento que contém o timestamp
   - Verifica primeiro em RAM, depois em pendrive
   - Extrai N segundos ANTES do evento (padrão: 10s)
   - Busca arquivo anterior se evento está no início do segmento
   - Valida continuidade temporal (gap máximo 90s entre arquivos)
   - Timeouts estendidos (90s FFmpeg, 300s Gunicorn)
   - Gera thumbnail e salva no banco de dados

4. **Arquitetura Gunicorn**
   - Master process com preload_app=True
   - FFmpeg e watchdog inicializados no master
   - 2 workers para atender requisições HTTP
   - Evita conflito de múltiplos watchdogs

## 🚀 Instalação

### Pré-requisitos

- Raspberry Pi 4B (2GB RAM mínimo)
- Raspberry Pi OS (Debian 12)
- Python 3.11+
- FFmpeg 4.3+
- 2 Câmeras USB (H.264 hardware encoding recomendado)
- Disco USB para armazenamento (64GB mínimo)

### Dependências

```bash
# Instalar dependências do sistema
sudo apt-get update
sudo apt-get install ffmpeg python3-pip python3-venv v4l-utils

# Criar ambiente virtual
cd /home/pi/app
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependências Python
pip3 install -r requirements_uploader.txt

# Dependências principais
# - Flask
# - Gunicorn
# - SQLAlchemy
# - RPi.GPIO
# - rpi_ws281x (LEDs)
```

### Configuração

#### 1. **Criar diretórios necessários**

```bash
# Estrutura em Pendrive (backup permanente)
sudo mkdir -p /media/pi/usb64gb/bts/stream1
sudo mkdir -p /media/pi/usb64gb/bts/stream2

# Estrutura em RAM (gravação rápida) - criada automaticamente pelo serviço
# /dev/shm/bts/stream1
# /dev/shm/bts/stream2

# Diretórios de processamento
sudo mkdir -p /home/pi/app/recordings/streams
sudo mkdir -p /home/pi/app/recordings/buffers/video0
sudo mkdir -p /home/pi/app/recordings/buffers/video2
sudo mkdir -p /home/pi/app/logs

# Ajustar permissões
sudo chown -R pi:pi /media/pi/usb64gb/bts
sudo chown -R pi:pi /home/pi/app/recordings
sudo chown -R pi:pi /home/pi/app/logs
```

#### 2. **Configurar gravação em RAM (Recomendado)**

```bash
# Executar script de setup automático
cd /home/pi/app
sudo ./setup_ram_recording.sh

# O script irá:
# - Criar diretórios em /dev/shm/bts/
# - Configurar sincronização automática (cron a cada 1 minuto)
# - Criar arquivo .env.ram com variáveis de ambiente
# - Configurar logs em /home/pi/app/logs/
```

**Benefícios da gravação em RAM:**
- ✅ Elimina corrupção de arquivos (linha verde)
- ✅ Sem timeouts de gravação
- ✅ Performance ~1000 MB/s vs ~10-30 MB/s
- ✅ Buffer de ~5 minutos sempre disponível
- ✅ Sincronização automática para pendrive a cada 1 minuto

**Ver documentação completa:** [AUTO_START_INFO.md](docs/AUTO_START_INFO.md)

#### 3. **Configurar serviço systemd**

```bash
# Usar o script de atualização (recomendado)
sudo ./update_service.sh

# Ou manualmente:
sudo cp video_uploader.service /etc/systemd/system/better_seconds_record.service
sudo systemctl daemon-reload
sudo systemctl enable better_seconds_record.service
sudo systemctl start better_seconds_record.service
```

### Configuração do Gunicorn

O sistema usa **Gunicorn** com configuração otimizada em `gunicorn_config.py`:

- **2 workers** (suficiente para carga)
- **preload_app=True** - FFmpeg inicializado apenas uma vez no master process
- **timeout=300s** - 5 minutos para operações longas (processamento de vídeo)
- **Logs em disco interno** (`/home/pi/app/logs/`) - evita I/O no pendrive
- Evita conflitos de múltiplos watchdogs competindo pelos mesmos processos

**Importante:** Não aumentar o número de workers! Cada worker adicional tentaria gerenciar os mesmos processos FFmpeg, causando loops de restart.

```python
# gunicorn_config.py
workers = 2
preload_app = True
bind = "0.0.0.0:5000"
```

## 📡 API Endpoints

### Gravação de Eventos

#### POST `/record/cam1`
Registra evento da câmera 1 (instantâneo)

**Padrão (10 segundos):**
```bash
curl -X POST http://localhost:5000/record/cam1
```

**Com duração customizada (15 segundos):**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"duration":15}' \
  http://localhost:5000/record/cam1
```

**Resposta:**
```json
{
  "status": "success",
  "message": "Evento cam1 registrado (duração: 10s)"
}
```

#### POST `/record/cam2`
Registra evento da câmera 2 (instantâneo)

**Padrão (10 segundos):**
```bash
curl -X POST http://localhost:5000/record/cam2
```

**Com duração customizada (20 segundos):**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"duration":20}' \
  http://localhost:5000/record/cam2
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
├── capture3.py                # Aplicação Flask
├── gunicorn_config.py         # Configuração do Gunicorn ⭐ NOVO
├── update_service.sh          # Script de atualização do serviço ⭐ NOVO
├── check_empty_files.sh       # Verifica arquivos corrompidos ⭐ NOVO
├── CORRUPTED_FILES_FIX.md     # Documentação das correções ⭐ NOVO
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
│   └── video0_YYYYMMDD_HHMMSS.ts
├── stream2/                   # Segmentos da câmera 2
│   └── video2_YYYYMMDD_HHMMSS.ts
├── ffmpeg_device0.log        # Logs do FFmpeg câmera 1
├── ffmpeg_device2.log        # Logs do FFmpeg câmera 2
├── ffmpeg_restart_log.txt    # Log de reinícios do FFmpeg ⭐ NOVO
├── gunicorn_access.log       # Log de acesso do Gunicorn ⭐ NOVO
└── gunicorn_error.log        # Log de erros do Gunicorn ⭐ NOVO
```

## 🔧 Configuração Avançada

### Parâmetros do FFmpeg

**Tempo de segmento:**
```python
segment_time=60  # 1 minuto (60 segundos)
```

**Buffer circular:**
```python
segment_wrap=1400   # ~23 horas de segmentos
```

**Segmentação com Alinhamento de Tempo:**
```python
# Previne criação de arquivos vazios
segment_atclocktime=1
segment_clocktime_offset=0
```

Essas opções garantem que segmentos sejam criados apenas quando há dados reais, evitando arquivos .ts corrompidos (0 bytes).

**Cálculo de espaço em disco:**
- Bitrate médio: 2-3 Mbps por stream
- Capacidade máxima: 300 horas × 2 streams = 600 horas
- Espaço necessário (300h por stream): ~270-400 GB
- Disco disponível: 64GB (suficiente para ~24-36 horas por stream)
- **Recomendação**: Configure segment_wrap menor ou implemente limpeza automática

### Ajuste de Duração do Buffer

Para alterar o tempo de histórico:

```python
# 10 horas (120 segmentos)
segment_wrap=120

# 2 horas (24 segmentos)  
segment_wrap=24
```

### Ajuste do Clipe Extraído

**Alterar duração na API:**
```bash
# Registrar evento com 15 segundos ao invés de 10
curl -X POST -H "Content-Type: application/json" \
  -d '{"duration":15}' \
  http://localhost:5000/record/cam1
```

**Comportamento da extração:**
- Recupera SEMPRE os últimos N segundos ANTES do evento
- Se evento está no início (<duration segundos), busca arquivo anterior
- Valida continuidade temporal (gap máximo 90s)
- Ajusta duração automaticamente se conteúdo insuficiente

**Exemplo:** Evento em 10:35:05 com duration=10
- Extrai de 10:34:55 até 10:35:05 (10s antes do evento)
- Se necessário, busca no arquivo anterior para completar 10s

## 🐛 Troubleshooting

### Problema: Arquivos .ts com 0 bytes (corrompidos)

**Causa:** Processo FFmpeg reiniciado antes de escrever dados no segmento

**Soluções implementadas:**
1. ✅ `segment_atclocktime=1` - Cria segmentos apenas com dados reais
2. ✅ Health check melhorado - Detecta arquivos vazios com >10s
3. ✅ Limpeza automática - Remove arquivos 0-byte após 60s
4. ✅ Gunicorn preload - Evita múltiplos watchdogs competindo

**Verificar arquivos vazios:**
```bash
# Script de verificação
cd /home/pi/app
./check_empty_files.sh

# Verificação manual
find /media/pi/usb64gb/bts/stream1 -name "*.ts" -size 0
find /media/pi/usb64gb/bts/stream2 -name "*.ts" -size 0
```

**Logs de restart:**
```bash
# Ver quando processos foram reiniciados
tail -f /media/pi/usb64gb/bts/ffmpeg_restart_log.txt
```

**Correção de filesystem (se erro EXT4):**
```bash
sudo systemctl stop better_seconds_record.service
sudo umount /media/pi/usb64gb
sudo fsck -fy /dev/sda1
sudo mount /media/pi/usb64gb
sudo systemctl start better_seconds_record.service
```

### Problema: Vídeos vazios ou corrompidos (durante extração)

**Causa:** Tentativa de extração de arquivo ainda sendo escrito pelo FFmpeg

**Solução:** O sistema já inclui verificações:
- Arquivo deve ter >100KB
- Arquivo deve ter >10s desde última modificação

**Verificar manualmente:**
```bash
# Verificar se arquivo está completo
ffprobe /media/pi/usb64gb/bts/stream1/video0_YYYYMMDD_HHMMSS.ts

# Se mostrar "moov atom not found" (mp4) ou erro de leitura (ts), o arquivo ainda está sendo escrito
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

### Problema: Vídeo extraído tem duração menor que solicitada

**Causa:** Evento ocorre muito cedo no segmento e arquivo anterior não existe ou está muito distante

**Comportamento esperado:**
- Sistema busca arquivo anterior automaticamente
- Se gap > 90s entre arquivos, usa apenas conteúdo disponível
- Logs mostram: "Vídeo terá Xs ao invés de Ys"

**Exemplo de log normal:**
```
INFO: Evento ocorre em 5.2s do início do arquivo.
      Faltam 4.8s para completar 10s. Buscando arquivo anterior...
      Arquivo anterior encontrado: video0_20260214_100000.ts
      Continuidade temporal validada: 60s entre arquivos
```

**Exemplo com gap:**
```
AVISO: Gap detectado entre arquivos (360s > 90s).
       Usando apenas conteúdo disponível desde início.
       Vídeo terá 5.0s ao invés de 10s
```

**Solução:** Normal - sistema ajusta automaticamente a duração disponível

### Problema: Loop infinito de restarts

**Sintoma:** Logs mostram reinícios contínuos:
```
🚨 Device 0 não está saudável, tentando restart...
🚨 Device 1 não está saudável, tentando restart...
```

**Causa:** Configuração incorreta do Gunicorn (múltiplos workers sem preload)

**Solução:**
```bash
# Atualizar serviço para usar gunicorn_config.py
cd /home/pi/app
sudo ./update_service.sh
sudo systemctl restart better_seconds_record.service

# Verificar se corrigiu (deve mostrar apenas 2 processos FFmpeg)
ps aux | grep ffmpeg | grep -v grep | wc -l
```

**Verificar watchdog:**
```bash
# Não deve mais mostrar loops
journalctl -u better_seconds_record.service -f | grep -E "watchdog|restart|saudável"
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

**Verificar se dispositivo está em uso:**
```bash
# Ver processos usando a câmera
sudo fuser /dev/video0
sudo fuser /dev/video2
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

# Monitorar watchdog e restarts
journalctl -u better_seconds_record.service -f | grep -E "watchdog|restart|empty"
```

### Logs do Gunicorn

```bash
# Logs de acesso
tail -f /media/pi/usb64gb/bts/gunicorn_access.log

# Logs de erro
tail -f /media/pi/usb64gb/bts/gunicorn_error.log

# Log de reinícios FFmpeg
tail -f /media/pi/usb64gb/bts/ffmpeg_restart_log.txt
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
### Atualização do Serviço

```bash
# Reiniciar serviço após mudanças
sudo systemctl restart better_seconds_record.service

# Ver logs de inicialização
journalctl -u better_seconds_record.service -b

# Verificar status
systemctl status better_seconds_record.service
```

### Atualizar para Configuração Gunicorn Otimizada

Se você está usando a versão antiga com 4 workers:

```bash
cd /home/pi/app
sudo ./update_service.sh
sudo systemctl restart better_seconds_record.service

# Verificar se aplicou corretamente
ps aux | grep gunicorn
# Deve mostrar: gunicorn -c gunicorn_config.py capture3:app
```

### Backup do Banco de Dados

```bash
# Backup manual
cp /home/pi/app/database/videos.db ~/backup_$(date +%Y%m%d).db

# Script de backup automático (cron)
0 3 * * * cp /home/pi/app/database/videos.db ~/backups/videos_$(date +\%Y\%m\%d).db
```

### Limpeza de Arquivos Antigos

```bash
# Remover segmentos com mais de 7 dias
find /media/pi/usb64gb/bts/stream1/ -name "*.ts" -mtime +7 -delete
find /media/pi/usb64gb/bts/stream2/ -name "*.ts" -mtime +7 -delete

# Remover vídeos processados com mais de 30 dias
find /home/pi/app/recordings/streams/ -name "*.mp4" -mtime +30 -delete
```

### Verificação de Integridade

```bash
# Verificar arquivos corrompidos
./check_empty_files.sh

# Verificar processos FFmpeg
ps aux | grep ffmpeg | grep -v grep

# Verificar número de workers (deve ser 2)
ps aux | grep gunicorn | grep -v grep | wc -l
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

**Versão:** 2.1  
**Última atualização:** 13 de fevereiro de 2026  
**Hardware:** Raspberry Pi 4B (2GB RAM)  
**Sistema Operacional:** Raspberry Pi OS (Debian 12)

## 🆕 Changelog v2.1 (13/02/2026)

### Correções Críticas
- ✅ **Configuração Gunicorn**: Preload app + 2 workers para evitar conflitos
- ✅ **Arquivos corrompidos**: Adicionado `segment_atclocktime` no FFmpeg
- ✅ **Health check aprimorado**: Detecta arquivos vazios (0 bytes)
- ✅ **Limpeza automática**: Remove segmentos vazios após 60s
- ✅ **Logging de restarts**: Rastreamento de reinícios do FFmpeg

### Novos Arquivos
- `gunicorn_config.py` - Configuração otimizada do Gunicorn
- `update_service.sh` - Script para atualizar o serviço systemd
- `check_empty_files.sh` - Verificação de arquivos corrompidos
- `CORRUPTED_FILES_FIX.md` - Documentação detalhada das correções

### Melhorias
- Formato de segmento alterado de `.mp4` para `.ts` (melhor para streaming)
- Watchdog otimizado para evitar falsos-positivos
- Melhor tratamento de reinícios de processo
- Documentação expandida com troubleshooting
