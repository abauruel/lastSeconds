# Rotas da API para Integracao

Documento rapido com as rotas atualmente expostas pela aplicacao para facilitar integracao com frontend, app mobile ou outros servicos.

- Base URL local: `http://localhost:5000`
- Base URL rede: `http://<ip-do-raspberry>:5000`
- Content-Type para POST/PUT com JSON: `application/json`

## 1. Status e Health

### GET /status
Verifica se a API esta no ar.

Resposta 200:
```json
{
  "status": "running"
}
```

Exemplo:
```bash
curl http://localhost:5000/status
```

### GET /health
Retorna diagnostico detalhado (FFmpeg, streams, cameras, disco e sistema).

Codigos:
- 200: healthy/degraded
- 503: unhealthy
- 500: erro interno no health check

Exemplo:
```bash
curl http://localhost:5000/health
```

## 2. Gravacao e Buffer

### POST /start
Inicia os processos de gravacao para as duas cameras.

Body (opcional):
```json
{
  "input_source": "rtsp",
  "camera_0_url": "rtsp://usuario:senha@host0:554/stream",
  "camera_1_url": "rtsp://usuario:senha@host1:554/stream"
}
```

Exemplo:
```bash
curl -X POST http://localhost:5000/start \
  -H "Content-Type: application/json" \
  -d '{"input_source":"rtsp"}'
```

### POST /stop
Para os processos FFmpeg.

Exemplo:
```bash
curl -X POST http://localhost:5000/stop
```

### POST /clear_buffers
Limpa buffers de gravacao.

Exemplo:
```bash
curl -X POST http://localhost:5000/clear_buffers
```

### POST /record
Registra evento para as duas cameras.

Body (opcional):
```json
{
  "duration": 12
}
```

Codigos:
- 200: success ou partial
- 500: erro

Exemplo:
```bash
curl -X POST http://localhost:5000/record \
  -H "Content-Type: application/json" \
  -d '{"duration":12}'
```

### POST /record/cam1
Registra evento apenas da camera 1 (cam_id=0).

Body (opcional):
```json
{
  "duration": 12
}
```

Exemplo:
```bash
curl -X POST http://localhost:5000/record/cam1 \
  -H "Content-Type: application/json" \
  -d '{"duration":12}'
```

### POST /record/cam2
Registra evento apenas da camera 2 (cam_id=1).

Body (opcional):
```json
{
  "duration": 12
}
```

Exemplo:
```bash
curl -X POST http://localhost:5000/record/cam2 \
  -H "Content-Type: application/json" \
  -d '{"duration":12}'
```

## 3. Processamento de Eventos

### POST /process_timestamps
Inicia processamento de timestamps em background.

Body (opcional):
```json
{
  "date": "20260616",
  "days_back": 3
}
```

Exemplo:
```bash
curl -X POST http://localhost:5000/process_timestamps \
  -H "Content-Type: application/json" \
  -d '{"days_back":3}'
```

### GET /process_timestamps/status
Informa se existe processamento em andamento.

Exemplo:
```bash
curl http://localhost:5000/process_timestamps/status
```

## 4. Videos Processados

### GET /videos
Lista datas disponiveis com videos processados.

Exemplo:
```bash
curl http://localhost:5000/videos
```

### GET /videos/{date}
Lista videos da data no formato YYYYMMDD.

Exemplo:
```bash
curl http://localhost:5000/videos/20260616
```

### GET /videos/{date}/{filename}
Download de video MP4 especifico.

Observacoes:
- `date` precisa ser YYYYMMDD
- `filename` precisa terminar em `.mp4`

Exemplo:
```bash
curl -L "http://localhost:5000/videos/20260616/video_001.mp4" -o video_001.mp4
```

## 5. Atualizacao de Status no Banco

### PUT /update_status
Atualiza status de um video no banco.

Body obrigatorio:
```json
{
  "name": "nome_do_video.mp4",
  "status": "pending"
}
```

Status aceitos: ver enum `VideoStatus` no backend (ex.: `pending`, `processing`, `processed`, `failed`).

Exemplo:
```bash
curl -X PUT http://localhost:5000/update_status \
  -H "Content-Type: application/json" \
  -d '{"name":"video_001.mp4","status":"processed"}'
```

## 6. Controle de Lente (API Proprietaria P6S CGI)

Rotas HTTP que acionam diretamente a API nativa do firmware da camera.
As credenciais sao extraidas automaticamente da variavel `CAMERA_X_RTSP_URL`.

### POST /proprietary/ptz/zoom
Controla zoom optico (in/out).

Body:
```json
{
  "camera": "camera_0",
  "action": "in",
  "speed": 5,
  "seconds": 2.0
}
```

Valores:
- `camera`: `camera_0` ou `camera_1`
- `action`: `in` ou `out`
- `speed`: inteiro `1`-`10` (padrao `5`)
- `seconds`: duracao em segundos (padrao `2.0`)

Codigos:
- 200: sucesso
- 400: validacao
- 502: falha na autenticacao ou comunicacao com a camera
- 503: cliente proprietario nao disponivel

Exemplos:
```bash
curl -X POST http://localhost:5000/proprietary/ptz/zoom \
  -H "Content-Type: application/json" \
  -d '{"camera":"camera_0","action":"in","speed":5,"seconds":2}'
```

```bash
curl -X POST http://localhost:5000/proprietary/ptz/zoom \
  -H "Content-Type: application/json" \
  -d '{"camera":"camera_1","action":"out","speed":3,"seconds":1.5}'
```

### POST /proprietary/ptz/focus
Controla foco motorizado (near/far).

Body:
```json
{
  "camera": "camera_0",
  "action": "far",
  "speed": 5,
  "seconds": 2.0
}
```

Valores:
- `camera`: `camera_0` ou `camera_1`
- `action`: `near` ou `far`
- `speed`: inteiro `1`-`10` (padrao `5`)
- `seconds`: duracao em segundos (padrao `2.0`)

Codigos:
- 200: sucesso
- 400: validacao
- 502: falha na autenticacao ou comunicacao com a camera
- 503: cliente proprietario nao disponivel

Exemplos:
```bash
curl -X POST http://localhost:5000/proprietary/ptz/focus \
  -H "Content-Type: application/json" \
  -d '{"camera":"camera_0","action":"far","speed":5,"seconds":1.5}'
```

```bash
curl -X POST http://localhost:5000/proprietary/ptz/focus \
  -H "Content-Type: application/json" \
  -d '{"camera":"camera_1","action":"near","speed":3,"seconds":1}'
```

## 7. Administracao do Sistema

### POST /update_time
Atualiza data/hora do sistema operacional.

Body:
```json
{
  "datetime": "2026-06-16 14:30:00"
}
```

Tambem aceita ISO 8601 (ex.: `2026-06-16T14:30:00`).

Exemplo:
```bash
curl -X POST http://localhost:5000/update_time \
  -H "Content-Type: application/json" \
  -d '{"datetime":"2026-06-16 14:30:00"}'
```

### POST /shutdown
Agenda desligamento seguro da maquina.

Body (opcional):
```json
{
  "delay": 10
}
```

`delay` deve ser inteiro entre 0 e 300.

Exemplo:
```bash
curl -X POST http://localhost:5000/shutdown \
  -H "Content-Type: application/json" \
  -d '{"delay":10}'
```

### POST /reboot
Agenda reinicio seguro da maquina.

Body (opcional):
```json
{
  "delay": 10
}
```

Exemplo:
```bash
curl -X POST http://localhost:5000/reboot \
  -H "Content-Type: application/json" \
  -d '{"delay":10}'
```

### POST /restart_service
Reinicia servico `bts.service` no host.

Exemplo:
```bash
curl -X POST http://localhost:5000/restart_service
```

## 8. Resumo Rapido de Endpoints

| Metodo | Rota |
|---|---|
| GET | /status |
| GET | /health |
| POST | /start |
| POST | /stop |
| POST | /clear_buffers |
| POST | /record |
| POST | /record/cam1 |
| POST | /record/cam2 |
| POST | /process_timestamps |
| GET | /process_timestamps/status |
| GET | /videos |
| GET | /videos/{date} |
| GET | /videos/{date}/{filename} |
| PUT | /update_status |
| POST | /restart_service |
| POST | /proprietary/ptz/zoom |
| POST | /proprietary/ptz/focus |
| POST | /update_time |
| POST | /shutdown |
| POST | /reboot |

## 9. Observacoes de Integracao

- Configure `CAMERA_0_RTSP_URL` e `CAMERA_1_RTSP_URL` com credenciais validas. O host e as credenciais sao extraidos automaticamente dessas variaveis pelas rotas `/proprietary/ptz/*`.
- Algumas rotas administrativas (`/shutdown`, `/reboot`, `/update_time`, `/restart_service`) exigem permissao sudo no ambiente.
- Em erros de validacao, a API retorna JSON com `status: error` e `message` explicando o problema.

## 10. Cliente API Proprietaria da Camera (linha de comando)

Para uso direto via terminal (sem passar pela API HTTP), o script `scripts/camera_proprietary_client.py` oferece acesso completo a API P6S CGI:

Comandos disponiveis:

- `auth-test`: valida autenticacao
- `zoom-in`: zoom in optico
- `zoom-out`: zoom out optico
- `focus-far`: foco para longe
- `focus-near`: foco para perto
- `reset`: zoom out completo (1x)
- `zoom-to`: zoom absoluto 1x-10x
- `device-info`: consulta `/System/DeviceInfo`
- `device-cap`: consulta `/System/DeviceCap`
- `click`: envia ponto para `/System/Device3DPositioningCfg` (operator=0)
- `box`: envia retangulo para `/System/Device3DPositioningCfg` (operator=1)

Exemplos:

```bash
python3 scripts/camera_proprietary_client.py \
  --host 192.168.0.210 --user admin --password 'SENHA_WEB' auth-test
```

```bash
python3 scripts/camera_proprietary_client.py \
  --host 192.168.0.210 --user admin --password 'SENHA_WEB' zoom-in --speed 5 --seconds 2
```

```bash
python3 scripts/camera_proprietary_client.py \
  --host 192.168.0.210 --user admin --password 'SENHA_WEB' focus-far --speed 5 --seconds 1
```

```bash
python3 scripts/camera_proprietary_client.py \
  --host 192.168.0.210 --user admin --password 'SENHA_WEB' focus-near --speed 3 --seconds 1
```

```bash
python3 scripts/camera_proprietary_client.py \
  --host 192.168.0.210 --user admin --password 'SENHA_WEB' click --x 320 --y 240
```

```bash
python3 scripts/camera_proprietary_client.py \
  --host 192.168.0.210 --user admin --password 'SENHA_WEB' \
  box --x0 200 --y0 140 --x1 440 --y1 340
```

Observacao:

- Use credenciais WEB da camera (podem ser diferentes das credenciais RTSP).