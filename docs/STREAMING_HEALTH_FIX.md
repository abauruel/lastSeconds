# Correção do Problema de Streaming Parando

## Problema Identificado

Após um tempo de execução, os streams HLS (HTTP) e RTSP paravam de funcionar, sendo necessário reiniciar o serviço `better_seconds_record` para voltar a funcionar.

### Causa Raiz

O problema ocorria porque:

1. **MediaMTX travando**: O servidor MediaMTX (responsável pelos streams HLS/RTSP) podia travar ou parar de responder
2. **Watchdog incompleto**: O watchdog apenas verificava se os processos FFmpeg estavam vivos, mas não verificava:
   - Se o MediaMTX estava funcionando
   - Se os streams estavam realmente disponíveis via HTTP/RTSP
   - Se os processos estavam realmente produzindo output
3. **Detecção lenta**: Verificação a cada 60 segundos com tolerância de 5 minutos para arquivos antigos resultava em detecção muito lenta de problemas

## Solução Implementada

### 1. Verificação de Saúde do MediaMTX

Adicionado método `check_mediamtx_health()` que verifica:
- Se o processo MediaMTX está rodando
- Se a API do MediaMTX está respondendo (porta 9997)

### 2. Verificação dos Streams HLS

Adicionado método `check_stream_health()` que:
- Verifica se os arquivos `.m3u8` estão disponíveis via HTTP
- Testa cada stream individualmente (stream1 e stream2)

### 3. Reinício Automático do MediaMTX

Adicionado método `restart_mediamtx()` que:
- Para o serviço MediaMTX
- Limpa processos órfãos
- Inicia o serviço novamente
- Valida se iniciou corretamente

### 4. Watchdog Melhorado

O watchdog agora:
- **Verifica a cada 30 segundos** (reduzido de 60s)
- **Tolerância de 3 minutos** nos arquivos (reduzido de 5min)
- **Verifica MediaMTX** a cada 1 minuto
- **Verifica disponibilidade dos streams HLS**
- **Reinicia processos FFmpeg** após reiniciar o MediaMTX
- Detecta e corrige problemas automaticamente

### 5. Novas Rotas de API

#### GET /health
Verifica a saúde completa do sistema:
```bash
curl http://localhost:5000/health
```

Retorna:
```json
{
  "status": "healthy|unhealthy",
  "details": {
    "mediamtx": {
      "status": "healthy|unhealthy",
      "healthy": true|false
    },
    "ffmpeg": {
      "device0": {
        "running": true|false,
        "healthy": true|false
      },
      "device1": {
        "running": true|false,
        "healthy": true|false
      }
    },
    "streams": {
      "stream1": {
        "available": true|false
      },
      "stream2": {
        "available": true|false
      }
    }
  }
}
```

#### POST /restart_mediamtx
Reinicia manualmente o MediaMTX:
```bash
curl -X POST http://localhost:5000/restart_mediamtx
```

#### POST /restart_ffmpeg/<device_number>
Reinicia um processo FFmpeg específico:
```bash
# Reiniciar camera 1 (device0)
curl -X POST http://localhost:5000/restart_ffmpeg/0

# Reiniciar camera 2 (device1)
curl -X POST http://localhost:5000/restart_ffmpeg/1
```

## Como Usar

### 1. Reiniciar o Serviço para Aplicar as Mudanças

```bash
sudo systemctl restart better_seconds_record
```

### 2. Monitorar com o Script

```bash
chmod +x monitor_streaming_health.sh
./monitor_streaming_health.sh
```

O script irá:
- Verificar a saúde de todos os componentes
- Oferecer reparo automático se detectar problemas
- Mostrar logs recentes
- Testar acesso aos streams

### 3. Monitoramento Contínuo

Para monitorar continuamente (a cada 2 minutos):
```bash
watch -n 120 './monitor_streaming_health.sh'
```

### 4. Verificar Logs do Watchdog

```bash
# Ver logs em tempo real
sudo journalctl -u better_seconds_record -f

# Ver apenas alertas do watchdog
sudo journalctl -u better_seconds_record -f | grep -E "(ALERTA|Reiniciando|MediaMTX|Watchdog)"
```

## Comportamento Esperado

Com as melhorias implementadas:

1. **Detecção Rápida**: Problemas são detectados em até 30 segundos
2. **Recuperação Automática**: Sistema tenta se recuperar automaticamente
3. **Monitoramento Completo**: Verifica FFmpeg, MediaMTX e streams HLS/RTSP
4. **Logs Detalhados**: Todos os eventos são registrados com emojis para fácil identificação

## Mensagens do Watchdog

- 🐕 `Watchdog de processos FFmpeg iniciado` - Watchdog iniciou
- ⚠️ `ALERTA: ...` - Problema detectado
- 🚨 `Device X não está saudável` - Processo com problema
- 🔄 `Reiniciando...` - Tentando recuperação
- ✅ `reiniciado com sucesso` - Recuperação bem-sucedida
- ❌ `Falha ao...` - Recuperação falhou

## Troubleshooting

### Streams ainda param de funcionar

1. Verifique se o MediaMTX está configurado corretamente:
```bash
sudo systemctl status mediamtx
```

2. Verifique se há espaço em disco:
```bash
df -h
```

3. Verifique memória:
```bash
free -h
```

4. Aumente a frequência do watchdog editando [ffmpeg_manager.py](ffmpeg_manager.py#L416):
```python
check_interval = 15  # Verifica a cada 15 segundos
```

### MediaMTX não reinicia automaticamente

Verifique se o serviço tem permissão para usar `sudo`:
```bash
# Adicione ao /etc/sudoers.d/streaming:
pi ALL=(ALL) NOPASSWD: /bin/systemctl stop mediamtx
pi ALL=(ALL) NOPASSWD: /bin/systemctl start mediamtx
pi ALL=(ALL) NOPASSWD: /bin/systemctl restart mediamtx
pi ALL=(ALL) NOPASSWD: /usr/bin/pkill
```

## Dependências Adicionadas

- `requests` - Para verificar APIs HTTP

Instalar se necessário:
```bash
cd /home/pi/app
source .venv/bin/activate
pip install requests
```

## Changelog

**2026-02-12**
- Adicionada verificação de saúde do MediaMTX
- Adicionada verificação dos streams HLS
- Implementado reinício automático do MediaMTX
- Reduzido intervalo do watchdog de 60s para 30s
- Reduzida tolerância de arquivos antigos de 5min para 3min
- Adicionadas rotas de API para diagnóstico e controle manual
- Criado script de monitoramento `monitor_streaming_health.sh`
