# API Integration Documentation
## Better Seconds Recording System - API Reference

**Base URL:** `http://localhost:5000` ou `http://<raspberry-pi-ip>:5000`

**Data:** 03 de Abril de 2026  
**Versão:** 1.2  

---

## ⚠️ MUDANÇAS IMPORTANTES (v1.1)

### Inicialização Manual de Gravações
**A partir da versão 1.1, a aplicação não inicia gravações automaticamente ao iniciar.**

Anteriormente, os processos FFmpeg iniciavam automaticamente quando a aplicação era iniciada. Agora, você deve:

1. **Iniciar a aplicação** - A aplicação iniciará, mas não começará a gravar
2. **Chamar a rota `/start`** - Somente após receber esta chamada as gravações serão iniciadas

**Exemplo de workflow atualizado:**
```bash
# 1. Iniciar o serviço (systemd ou manualmente)
sudo systemctl start video_uploader.service

# 2. Aguardar a aplicação estar pronta
curl http://localhost:5000/status

# 3. Iniciar as gravações quando desejado
curl -X POST http://localhost:5000/start
```

Esta mudança oferece maior controle sobre quando iniciar as gravações, permitindo configurações e verificações antes de começar a capturar vídeo.

---

## 📋 Índice

- [Rotas de Status](#rotas-de-status)
- [Rotas de Gravação](#rotas-de-gravação)
- [Rotas de Processamento](#rotas-de-processamento)
- [Rotas de Vídeos](#rotas-de-vídeos)
- [Rotas de Sistema](#rotas-de-sistema)
- [Códigos de Status HTTP](#códigos-de-status-http)
- [Exemplos de Integração](#exemplos-de-integração)

---

## 🟢 Rotas de Status

### GET `/status`
Verifica se o serviço está em execução.

**Resposta de Sucesso (200):**
```json
{
  "status": "running"
}
```

**Exemplo:**
```bash
curl http://localhost:5000/status
```

---

### GET `/health`
Health check detalhado do sistema com informações sobre processos FFmpeg, streams, disco e CPU.

**Resposta de Sucesso (200):**
```json
{
  "timestamp": "2026-03-28T17:30:00.123456",
  "status": "healthy",
  "issues": [],
  "ffmpeg_processes": {
    "count": 2,
    "expected": 2,
    "running": true,
    "zombies": 0
  },
  "streams": {
    "stream1": {
      "latest_file": "video0_20260328_173000.ts",
      "file_age_seconds": 45,
      "file_size_bytes": 12345678,
      "recording": true,
      "source": "USB"
    },
    "stream2": {
      "latest_file": "video2_20260328_173000.ts",
      "file_age_seconds": 42,
      "file_size_bytes": 12234567,
      "recording": true,
      "source": "USB"
    }
  },
  "disk": {
    "total_gb": 64.0,
    "used_gb": 32.5,
    "free_gb": 31.5,
    "percent_used": 50.8
  },
  "system": {
    "temperature_c": 58.3
  }
}
```

**Status Possíveis:**
- `healthy` - Sistema funcionando perfeitamente
- `degraded` - Sistema funcional com alertas
- `unhealthy` - Problemas críticos detectados
- `error` - Erro durante verificação

**Exemplo:**
```bash
curl http://localhost:5000/health
```

---

## 🎥 Rotas de Gravação

### POST `/record/cam1`
Registra um evento na câmera 1 e reproduz áudio de confirmação via Bluetooth.

**Parâmetros (JSON):**
| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|---------|-----------|
| `duration` | integer | Não | 12 | Duração do vídeo em segundos (antes do evento) |

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "message": "Evento cam1 registrado (duração: 12s)"
}
```

**Resposta de Erro (500):**
```json
{
  "status": "error",
  "message": "Erro ao registrar evento"
}
```

**Exemplo:**
```bash
curl -X POST http://localhost:5000/record/cam1 \
  -H "Content-Type: application/json" \
  -d '{"duration": 15}'
```

---

### POST `/record/cam2`
Registra um evento na câmera 2 e reproduz áudio de confirmação via Bluetooth.

**Parâmetros (JSON):**
| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|---------|-----------|
| `duration` | integer | Não | 12 | Duração do vídeo em segundos (antes do evento) |

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "message": "Evento cam2 registrado (duração: 12s)"
}
```

**Exemplo:**
```bash
curl -X POST http://localhost:5000/record/cam2 \
  -H "Content-Type: application/json" \
  -d '{"duration": 20}'
```

---

### POST `/record`
Registra um evento em **ambas as câmeras simultaneamente** (cam1 e cam2) e reproduz áudio de confirmação via Bluetooth.

**Parâmetros (JSON):**
| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|---------|-----------|
| `duration` | integer | Não | 12 | Duração do vídeo em segundos (antes do evento) |

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "message": "Evento registrado para ambas as câmeras (duração: 12s)"
}
```

**Resposta de Sucesso Parcial (200):**
```json
{
  "status": "partial",
  "message": "Evento registrado apenas para cam1 (duração: 12s)"
}
```

**Resposta de Erro (500):**
```json
{
  "status": "error",
  "message": "Erro ao registrar evento em ambas as câmeras"
}
```

**Exemplo - Duração padrão (12s):**
```bash
curl -X POST http://localhost:5000/record \
  -H "Content-Type: application/json"
```

**Exemplo - Duração personalizada (15s):**
```bash
curl -X POST http://localhost:5000/record \
  -H "Content-Type: application/json" \
  -d '{"duration": 15}'
```

---

## ⚙️ Rotas de Processamento

### POST `/process_timestamps`
Processa timestamps pendentes e gera vídeos dos eventos registrados.

**Parâmetros (JSON):**
| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|---------|-----------|
| `date` | string | Não | null | Data específica no formato YYYYMMDD (ex: "20260328") |
| `days_back` | integer | Não | 3 | Número de dias anteriores para processar |

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "message": "Processamento iniciado",
  "events_processed": 5,
  "events_pending": 0,
  "events_failed": 0
}
```

**Resposta de Erro (500):**
```json
{
  "status": "error",
  "message": "Erro interno ao processar timestamps: [detalhes]"
}
```

**Exemplo - Processar todos eventos dos últimos 3 dias:**
```bash
curl -X POST http://localhost:5000/process_timestamps \
  -H "Content-Type: application/json"
```

**Exemplo - Processar data específica:**
```bash
curl -X POST http://localhost:5000/process_timestamps \
  -H "Content-Type: application/json" \
  -d '{"date": "20260328"}'
```

**Exemplo - Processar últimos 7 dias:**
```bash
curl -X POST http://localhost:5000/process_timestamps \
  -H "Content-Type: application/json" \
  -d '{"days_back": 7}'
```

---

### GET `/process_timestamps/status`
Verifica se há processamento de timestamps em andamento.

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "is_processing": false,
  "message": "Nenhum processamento em andamento"
}
```

**Exemplo:**
```bash
curl http://localhost:5000/process_timestamps/status
```

---

## � Rotas de Vídeos

### GET `/videos`
Lista todas as datas disponíveis com vídeos processados.

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "total_dates": 2,
  "dates": [
    {
      "date": "20260403",
      "date_formatted": "03/04/2026",
      "video_count": 5,
      "path": "/videos/20260403"
    },
    {
      "date": "20260402",
      "date_formatted": "02/04/2026",
      "video_count": 3,
      "path": "/videos/20260402"
    }
  ]
}
```

**Exemplo:**
```bash
curl http://localhost:5000/videos
```

---

### GET `/videos/<date>`
Lista todos os vídeos de uma data específica.

**Parâmetros de URL:**
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `date` | string | Data no formato YYYYMMDD (ex: 20260403) |

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "date": "20260403",
  "date_formatted": "03/04/2026",
  "total_videos": 2,
  "videos": [
    {
      "filename": "rpi4bmobile_stream2_20260403_113647.mp4",
      "size_bytes": 2714696,
      "size_mb": 2.59,
      "modified": "2026-04-03T11:38:43.039474",
      "download_url": "/videos/20260403/rpi4bmobile_stream2_20260403_113647.mp4"
    },
    {
      "filename": "rpi4bmobile_stream1_20260403_113644.mp4",
      "size_bytes": 1093357,
      "size_mb": 1.04,
      "modified": "2026-04-03T11:38:41.747476",
      "download_url": "/videos/20260403/rpi4bmobile_stream1_20260403_113644.mp4"
    }
  ]
}
```

**Resposta de Erro (400 - Data Inválida):**
```json
{
  "status": "error",
  "message": "Formato de data inválido. Use YYYYMMDD (ex: 20260403)"
}
```

**Resposta de Erro (404 - Data Não Encontrada):**
```json
{
  "status": "error",
  "message": "Nenhum vídeo encontrado para a data 20260403"
}
```

**Exemplo:**
```bash
curl http://localhost:5000/videos/20260403
```

---

### GET `/videos/<date>/<filename>`
Faz download de um vídeo específico.

**Parâmetros de URL:**
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `date` | string | Data no formato YYYYMMDD (ex: 20260403) |
| `filename` | string | Nome do arquivo MP4 |

**Resposta de Sucesso (200):**
- Retorna o arquivo de vídeo MP4 para download
- Header `Content-Type: video/mp4`
- Header `Content-Disposition: attachment; filename=<nome_arquivo>`

**Resposta de Erro (400 - Arquivo Inválido):**
```json
{
  "status": "error",
  "message": "Apenas arquivos .mp4 são permitidos"
}
```

**Resposta de Erro (404 - Arquivo Não Encontrado):**
```json
{
  "status": "error",
  "message": "Vídeo não encontrado"
}
```

**Exemplo - Download via curl:**
```bash
curl -O http://localhost:5000/videos/20260403/rpi4bmobile_stream1_20260403_113644.mp4
```

**Exemplo - Download via wget:**
```bash
wget http://localhost:5000/videos/20260403/rpi4bmobile_stream1_20260403_113644.mp4
```

**Exemplo - Visualizar no navegador:**
```
http://192.168.1.100:5000/videos/20260403/rpi4bmobile_stream1_20260403_113644.mp4
```

---

## �🔧 Rotas de Sistema

### POST `/start`
Inicia os processos FFmpeg para ambas as câmeras.

**⚠️ MUDANÇA IMPORTANTE:** A partir de agora, a aplicação não inicia as gravações automaticamente. É necessário chamar esta rota explicitamente para iniciar as gravações.

**Parâmetros (Body JSON - Opcionais):**
```json
{
  "input_source": "rtsp",           // Tipo de fonte: "rtsp" ou "usb" (default: "rtsp")
  "camera_0_url": "rtsp://...",     // URL RTSP da câmera 0 (override da variável de ambiente)
  "camera_1_url": "rtsp://..."      // URL RTSP da câmera 1 (override da variável de ambiente)
}
```

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "message": "Processos do ffmpeg iniciados para ambas as câmeras.",
  "camera_0": "rtsp://admin:123456@192.168.1.100/stream0",
  "camera_1": "rtsp://admin:123456@192.168.1.100/stream1",
  "input_source": "rtsp"
}
```

**Exemplo Básico:**
```bash
curl -X POST http://localhost:5000/start
```

**Exemplo com Parâmetros:**
```bash
curl -X POST http://localhost:5000/start \
  -H "Content-Type: application/json" \
  -d '{
    "input_source": "rtsp",
    "camera_0_url": "rtsp://admin:password@192.168.1.100/stream0",
    "camera_1_url": "rtsp://admin:password@192.168.1.100/stream1"
  }'
```

**Exemplo para câmeras USB:**
```bash
curl -X POST http://localhost:5000/start \
  -H "Content-Type: application/json" \
  -d '{"input_source": "usb"}'
```

---

### POST `/stop`
Para todos os processos FFmpeg.

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "message": "Processos do ffmpeg finalizados."
}
```

**Exemplo:**
```bash
curl -X POST http://localhost:5000/stop
```

---

### POST `/clear_buffers`
Limpa os buffers de gravação.

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "message": "Buffers limpos com sucesso."
}
```

**Exemplo:**
```bash
curl -X POST http://localhost:5000/clear_buffers
```

---

### POST `/update_time`
Atualiza a hora do sistema Raspberry Pi.

**Parâmetros (JSON):**
| Parâmetro | Tipo | Obrigatório | Formato | Descrição |
|-----------|------|-------------|---------|-----------|
| `datetime` | string | Sim | "YYYY-MM-DD HH:MM:SS" ou ISO 8601 | Data e hora para configurar |

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "message": "Hora do sistema atualizada com sucesso",
  "previous_datetime": "2026-03-28 14:30:00",
  "current_datetime": "2026-03-28 14:30:05",
  "timestamp": "2026-03-28T14:30:05.123456"
}
```

**Resposta de Erro (400):**
```json
{
  "status": "error",
  "message": "Campo 'datetime' é obrigatório"
}
```

**Exemplo:**
```bash
curl -X POST http://localhost:5000/update_time \
  -H "Content-Type: application/json" \
  -d '{"datetime": "2026-03-28 14:30:00"}'
```

**Exemplo com ISO 8601:**
```bash
curl -X POST http://localhost:5000/update_time \
  -H "Content-Type: application/json" \
  -d '{"datetime": "2026-03-28T14:30:00"}'
```

---

### POST `/shutdown`
Desliga o Raspberry Pi com segurança, encerrando corretamente os processos FFmpeg.

**Parâmetros (JSON):**
| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|---------|-----------|
| `delay` | integer | Não | 10 | Delay em segundos antes do shutdown (0-300) |

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "message": "Shutdown iniciado com sucesso",
  "timestamp": "2026-03-28T17:30:00.123456",
  "delay_seconds": 10,
  "steps": [
    "FFmpeg processes stopped",
    "Disk data synchronized",
    "System shutdown scheduled in 10s"
  ]
}
```

**Resposta de Erro (400):**
```json
{
  "status": "error",
  "message": "delay deve ser um inteiro entre 0 e 300 segundos"
}
```

**Exemplo - Shutdown com delay padrão (10s):**
```bash
curl -X POST http://localhost:5000/shutdown \
  -H "Content-Type: application/json"
```

**Exemplo - Shutdown imediato:**
```bash
curl -X POST http://localhost:5000/shutdown \
  -H "Content-Type: application/json" \
  -d '{"delay": 0}'
```

**Cancelar shutdown agendado:**
```bash
sudo shutdown -c
```

---

### POST `/reboot`
Reinicia o Raspberry Pi com segurança, encerrando corretamente os processos FFmpeg.

**Parâmetros (JSON):**
| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|---------|-----------|
| `delay` | integer | Não | 10 | Delay em segundos antes do reboot (0-300) |

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "message": "Reboot iniciado com sucesso",
  "timestamp": "2026-03-28T17:30:00.123456",
  "delay_seconds": 10,
  "steps": [
    "FFmpeg processes stopped",
    "Disk data synchronized",
    "System reboot scheduled in 10s"
  ]
}
```

**Resposta de Erro (400):**
```json
{
  "status": "error",
  "message": "delay deve ser um inteiro entre 0 e 300 segundos"
}
```

**Exemplo - Reboot com delay padrão (10s):**
```bash
curl -X POST http://localhost:5000/reboot \
  -H "Content-Type: application/json"
```

**Exemplo - Reboot imediato:**
```bash
curl -X POST http://localhost:5000/reboot \
  -H "Content-Type: application/json" \
  -d '{"delay": 0}'
```

**Exemplo - Reboot com delay personalizado (30s):**
```bash
curl -X POST http://localhost:5000/reboot \
  -H "Content-Type: application/json" \
  -d '{"delay": 30}'
```

**Cancelar reboot agendado:**
```bash
sudo shutdown -c
```

---

### PUT `/update_status`
Atualiza o status de processamento de um vídeo no banco de dados.

**Parâmetros (JSON):**
| Parâmetro | Tipo | Obrigatório | Valores Possíveis | Descrição |
|-----------|------|-------------|-------------------|-----------|
| `name` | string | Sim | - | Nome do arquivo de vídeo |
| `status` | string | Sim | pending, processing, completed, failed, uploaded | Novo status do vídeo |

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "message": "Status do vídeo video_20260328_143000.mp4 atualizado para completed"
}
```

**Resposta de Erro (404):**
```json
{
  "status": "error",
  "message": "Vídeo não encontrado"
}
```

**Exemplo:**
```bash
curl -X PUT http://localhost:5000/update_status \
  -H "Content-Type: application/json" \
  -d '{
    "name": "video_20260328_143000.mp4",
    "status": "completed"
  }'
```

---

### POST `/restart_service`
Reinicia o serviço systemd do Better Seconds.

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "message": "Serviço better_seconds_record.service reiniciado."
}
```

**Exemplo:**
```bash
curl -X POST http://localhost:5000/restart_service
```

---

## 📊 Códigos de Status HTTP

| Código | Descrição |
|--------|-----------|
| 200 | Sucesso - Requisição processada com sucesso |
| 400 | Bad Request - Parâmetros inválidos ou ausentes |
| 404 | Not Found - Recurso não encontrado |
| 500 | Internal Server Error - Erro no servidor |
| 503 | Service Unavailable - Sistema unhealthy (rota /health) |

---

## 🚀 Exemplos de Integração

### Python

```python
import requests
import json

# Base URL
base_url = "http://192.168.1.100:5000"

# Registrar evento na câmera 1
def registrar_evento_cam1(duracao=12):
    url = f"{base_url}/record/cam1"
    payload = {"duration": duracao}
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Verificar status do sistema
def verificar_saude():
    url = f"{base_url}/health"
    response = requests.get(url)
    return response.json()

# Processar timestamps pendentes
def processar_eventos():
    url = f"{base_url}/process_timestamps"
    response = requests.post(url)
    return response.json()

# Exemplo de uso
if __name__ == "__main__":
    # Registrar evento
    resultado = registrar_evento_cam1(duracao=15)
    print(f"Evento registrado: {resultado}")
    
    # Verificar saúde do sistema
    saude = verificar_saude()
    print(f"Status do sistema: {saude['status']}")
    
    # Processar eventos
    processamento = processar_eventos()
    print(f"Processamento: {processamento}")
```

---

### JavaScript / Node.js

```javascript
const axios = require('axios');

const baseURL = 'http://192.168.1.100:5000';

// Registrar evento na câmera 2
async function registrarEventoCam2(duracao = 12) {
  try {
    const response = await axios.post(`${baseURL}/record/cam2`, {
      duration: duracao
    });
    return response.data;
  } catch (error) {
    console.error('Erro ao registrar evento:', error.message);
    throw error;
  }
}

// Verificar status
async function verificarStatus() {
  try {
    const response = await axios.get(`${baseURL}/status`);
    return response.data;
  } catch (error) {
    console.error('Erro ao verificar status:', error.message);
    throw error;
  }
}

// Atualizar hora do sistema
async function atualizarHora(datetime) {
  try {
    const response = await axios.post(`${baseURL}/update_time`, {
      datetime: datetime
    });
    return response.data;
  } catch (error) {
    console.error('Erro ao atualizar hora:', error.message);
    throw error;
  }
}

// Exemplo de uso
(async () => {
  // Registrar evento
  const evento = await registrarEventoCam2(20);
  console.log('Evento registrado:', evento);
  
  // Verificar status
  const status = await verificarStatus();
  console.log('Status:', status);
  
  // Atualizar hora
  const horaAtualizada = await atualizarHora('2026-03-28 15:00:00');
  console.log('Hora atualizada:', horaAtualizada);
})();
```

---

### cURL Examples (Shell Script)

```bash
#!/bin/bash

BASE_URL="http://localhost:5000"

# Função para registrar evento
registrar_evento() {
    local camera=$1
    local duracao=$2
    
    curl -X POST "${BASE_URL}/record/${camera}" \
      -H "Content-Type: application/json" \
      -d "{\"duration\": ${duracao}}"
}

# Função para verificar saúde
verificar_saude() {
    curl -s "${BASE_URL}/health" | jq '.'
}

# Função para processar timestamps
processar_timestamps() {
    local dias=$1
    
    curl -X POST "${BASE_URL}/process_timestamps" \
      -H "Content-Type: application/json" \
      -d "{\"days_back\": ${dias}}"
}

# Uso
echo "Registrando evento na câmera 1..."
registrar_evento "cam1" 12

echo -e "\n\nVerificando saúde do sistema..."
verificar_saude

echo -e "\n\nProcessando últimos 3 dias..."
processar_timestamps 3
```

---

### Webhook Integration Example

```python
# Exemplo de integração via webhook para notificações externas
from flask import Flask, request
import requests

app = Flask(__name__)

BETTER_SECONDS_URL = "http://192.168.1.100:5000"
EXTERNAL_WEBHOOK_URL = "https://seu-servidor.com/webhook"

@app.route('/webhook/evento', methods=['POST'])
def receber_evento():
    """Recebe webhook externo e registra evento no Better Seconds"""
    data = request.json
    
    # Determina qual câmera usar
    camera = data.get('camera', 'cam1')
    duracao = data.get('duracao', 12)
    
    # Registra evento no Better Seconds
    response = requests.post(
        f"{BETTER_SECONDS_URL}/record/{camera}",
        json={"duration": duracao}
    )
    
    # Notifica sistema externo
    if response.status_code == 200:
        requests.post(
            EXTERNAL_WEBHOOK_URL,
            json={
                "status": "success",
                "camera": camera,
                "timestamp": data.get('timestamp')
            }
        )
    
    return response.json()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

---

## 📝 Notas Importantes

### Autenticação
Atualmente, a API **não possui autenticação**. Recomenda-se:
- Executar em rede local protegida
- Implementar firewall para limitar acesso
- Considerar VPN para acesso remoto

### Rate Limiting
- Não há limite de requisições implementado
- Recomenda-se não fazer mais de 10 requisições/segundo

### Áudio
- Reprodução de áudio funciona via dispositivo Bluetooth **G200**
- Volume configurado para **98%**
- Rotas `/record`, `/record/cam1` e `/record/cam2` reproduzem áudio de confirmação

### Armazenamento
- Timestamps: `/media/pi/usb64gb/bts/streams/timestamps/`
- Vídeos gerados: `/media/pi/usb64gb/bts/recordings/`
- Database: `/media/pi/usb64gb/bts/recordings.db`

### Permissões
- Usuário do serviço: `pi`
- Permissões sudo configuradas para:
  - `/usr/bin/date` (atualização de hora)
  - `/usr/sbin/hwclock` (sincronização hardware clock)
  - `/sbin/shutdown` (desligamento do sistema)

---

## 🔍 Troubleshooting

### Erro "Connection refused"
- Verificar se o serviço está rodando: `sudo systemctl status bts.service`
- Verificar portas abertas: `netstat -tlnp | grep 5000`

### Áudio não reproduz
- Verificar dispositivo Bluetooth conectado: `bluetoothctl devices`
- Verificar PulseAudio: `pactl list sinks short`
- Ver logs do serviço: `journalctl -u bts.service -f`

### Eventos não são processados
- Verificar permissões de disco: `df -h /media/pi/usb64gb`
- Verificar logs: `journalctl -u bts.service --since "10 minutes ago"`
- Status do processamento: `GET /process_timestamps/status`

---

## 📧 Suporte

Para questões ou problemas:
1. Verificar logs: `journalctl -u bts.service -n 100`
2. Verificar saúde: `GET /health`
3. Verificar documentação em: `/home/pi/app/docs/`

---

**Última atualização:** 03 de Abril de 2026  
**Versão da API:** 1.2  
**Sistema:** Better Seconds Recording System

## 📝 Changelog

### v1.2 (03/04/2026)
- ✨ Adicionadas rotas de listagem e download de vídeos (`/videos`, `/videos/<date>`, `/videos/<date>/<filename>`)
- ✨ Adicionada rota `/reboot` para reiniciar o Raspberry Pi
- 🔧 Rota `/record` agora registra evento em ambas as câmeras simultaneamente
- 🔧 Duração padrão de eventos alterada de 10s para 12s
- 🔧 Correção de bug na rota `/record` que causava erro 500

### v1.1 (29/03/2026)
- ⚠️ Inicialização manual de gravações obrigatória via `/start`
- ✨ Adicionadas rotas de gerenciamento de sistema (`/shutdown`, `/update_time`)

### v1.0 (28/03/2026)
- 🎉 Lançamento inicial da API
