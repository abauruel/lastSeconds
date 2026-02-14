# DIAGN\u00d3STICO: Streams Param Ap\u00f3s um Tempo

## Causa Raiz Identificada \ud83c\udfaf

O problema **N\u00c3O era o MediaMTX**, mas sim **processos FFmpeg travados** ocupando os dispositivos de v\u00eddeo!

### O que estava acontecendo:

1. \u26a0\ufe0f **Dispositivos ocupados**: `/dev/video0` e `/dev/video2` ficavam marcados como "Device or resource busy"
2. \ud83e\udddf **Processos zumbis**: Quando o watchdog tentava reiniciar o FFmpeg, os processos antigos N\u00c3O eram finalizados corretamente
3. \ud83d\udeab **Falha no restart**: Novos processos n\u00e3o conseguiam acessar as c\u00e2meras porque as antigas ainda estavam vivas
4. \ud83d\udca5 **Resultado**: Zero streams funcionando, mas segmentos continuavam sendo gravados pelos processos travados

### Por que reiniciar o servi\u00e7o completo resolvia?

Ao reiniciar `better_seconds_record.service`, o systemd mata TODOS os processos filhos, liberando definitivamente os dispositivos USB.

## Solu\u00e7\u00e3o Implementada \ud83d\udd27

### 1. Limpeza Agressiva de Processos

**Novo m\u00e9todo `_kill_ffmpeg_processes_using_device()`:**
- Usa `lsof` para encontrar TODOS os processos usando o dispositivo
- Mata com `kill -9` (SIGKILL) para garantir finaliza\u00e7\u00e3o
- Fallback com `pkill -9` e `fuser -k` se necess\u00e1rio

### 2. Verifica\u00e7\u00e3o de Disponibilidade

**Novo m\u00e9todo `_is_device_available()`:**
- Testa se o dispositivo est\u00e1 realmente livre antes de iniciar novo processo
- M\u00faltiplas tentativas com retry
- Evita tentar reiniciar em dispositivo ocupado

### 3. Restart Inteligente

**M\u00e9todo `restart_dead_process()` melhorado:**
1. \ud83e\uddf9 Limpa processos zumbis
2. \ud83d\udd2a Mata processo gerenciado
3. \ud83d\udca3 Mata TODOS os processos usando o dispositivo (inclusive \u00f3rf\u00e3os)
4. \u23f3 Aguarda dispositivo ficar livre
5. \u2705 Verifica disponibilidade com m\u00faltiplas tentativas
6. \ud83d\ude80 Inicia novo processo apenas se dispositivo estiver livre
7. \u2714\ufe0f Valida que o processo iniciou corretamente

### 4. Watchdog Melhorado

**Mudan\u00e7as no loop do watchdog:**
- \ud83e\uddf9 Limpa zumbis ANTES de cada verifica\u00e7\u00e3o
- \ud83d\udcca Contador de falhas por dispositivo
- \u23f8\ufe0f Pausa de 2 minutos ap\u00f3s 3 falhas consecutivas
- \u26d4 **N\u00c3O reinicia MediaMTX automaticamente** (para evitar perda de segmentos)

### 5. Porta HLS Corrigida

- Era: `http://localhost:8889` \u274c
- Agora: `http://localhost:8888` \u2705

## Novos Endpoints de API

### POST /force_cleanup
For\u00e7a limpeza completa e reinicializa\u00e7\u00e3o:

```bash
# Limpar e reiniciar ambas as c\u00e2meras
curl -X POST http://localhost:5000/force_cleanup

# Limpar apenas c\u00e2mera 1
curl -X POST http://localhost:5000/force_cleanup -H "Content-Type: application/json" -d '{"devices": [0]}'

# Limpar apenas c\u00e2mera 2
curl -X POST http://localhost:5000/force_cleanup -H "Content-Type: application/json" -d '{"devices": [1]}'
```

Resposta:
```json
{
  "status": "completed",
  "results": [
    {
      "device": 0,
      "status": "success",
      "message": "Device0 limpo e reiniciado"
    },
    {
      "device": 1,
      "status": "success",
      "message": "Device1 limpo e reiniciado"
    }
  ]
}
```

## Como Aplicar as Corre\u00e7\u00f5es

### 1. Instalar Depend\u00eancias

```bash
# Ferramentas para ger\u00eancia de processos
sudo apt-get update
sudo apt-get install -y lsof psmisc
```

### 2. For\u00e7ar Limpeza de Processos Travados AGORA

```bash
# Identificar processos travados
ps aux | grep ffmpeg | grep -v grep

# Matar TODOS os processos FFmpeg
sudo pkill -9 ffmpeg

# Verificar se dispositivos est\u00e3o livres
lsof /dev/video0
lsof /dev/video2

# Se ainda estiverem ocupados, force release
sudo fuser -k /dev/video0
sudo fuser -k /dev/video2
```

### 3. Reiniciar Servi\u00e7o com Novo C\u00f3digo

```bash
sudo systemctl restart better_seconds_record
```

### 4. Monitorar

```bash
# Ver logs do watchdog em tempo real
sudo journalctl -u better_seconds_record -f | grep -E "(\ud83d\udd2a|\u2705|\u274c|Device|Watchdog)"

# Ou usar o script de monitoramento
./monitor_streaming_health.sh
```

## Diagn\u00f3stico de Problemas

### Verificar se dispositivos est\u00e3o livres:

```bash
lsof /dev/video0
lsof /dev/video2
```

Se mostrar processos, mate-os:
```bash
sudo pkill -9 -f "ffmpeg.*video0"
sudo pkill -9 -f "ffmpeg.*video2"
```

### For\u00e7ar limpeza via API:

```bash
curl -X POST http://localhost:5000/force_cleanup
```

### Verificar processos zumbis:

```bash
ps aux | grep defunct
```

### Ver \u00faltimos erros do FFmpeg:

```bash
tail -50 /media/pi/usb64gb/bts/ffmpeg_device0.log
tail -50 /media/pi/usb64gb/bts/ffmpeg_device2.log
```

## Comportamento Esperado Agora

\u2705 **Detec\u00e7\u00e3o**: Problemas detectados em at\u00e9 30 segundos  
\u2705 **Limpeza**: Processos travados s\u00e3o mortos agressivamente  
\u2705 **Verifica\u00e7\u00e3o**: Dispositivo \u00e9 testado antes de reiniciar  
\u2705 **Restart**: Apenas se dispositivo estiver realmente livre  
\u2705 **Retry**: M\u00faltiplas tentativas com pausa ap\u00f3s falhas  
\u2705 **Seguran\u00e7a**: MediaMTX N\u00c3O \u00e9 reiniciado automaticamente  

### Logs do Watchdog

Mensagens que voc\u00ea ver\u00e1:

```
\ud83d\udd2a Matando processo 1234 que est\u00e1 usando /dev/video0
\u2705 Dispositivo /dev/video0 est\u00e1 livre e pronto
\u2705 Processo FFmpeg device0 reiniciado com sucesso (PID 5678)
```

Em caso de falha:
```
\u274c ERRO: Dispositivo /dev/video0 ainda est\u00e1 ocupado ap\u00f3s limpeza!
   Tentando limpeza for\u00e7ada...
\u26a0\ufe0f Falha no restart de device 0 (1 tentativas)
```

Ap\u00f3s 3 falhas:
```
\u23f8\ufe0f Device 0: Muitas falhas, aguardando 2 minutos antes de tentar novamente
```

## Diferen\u00e7as da Solu\u00e7\u00e3o Anterior

| Aspecto | Antes | Agora |
|---------|-------|-------|
| **Foco** | MediaMTX | Processos FFmpeg |
| **Limpeza** | Apenas processo gerenciado | TODOS os processos no dispositivo |
| **Verifica\u00e7\u00e3o** | Nenhuma | Testa se dispositivo est\u00e1 livre |
| **Restart MediaMTX** | Autom\u00e1tico | Manual apenas |
| **Retry** | Infinito | Pausa ap\u00f3s 3 falhas |
| **Porta HLS** | 8889 (errada) | 8888 (correta) |

## Pr\u00f3ximos Passos

1. \u2705 Aplicar corre\u00e7\u00f5es (ver se\u00e7\u00e3o acima)
2. \ud83d\udc41\ufe0f Monitorar por 24-48 horas
3. \ud83d\udcca Analisar logs do watchdog
4. \u2699\ufe0f Ajustar timeouts se necess\u00e1rio

## Se o Problema Persistir

Se mesmo com essas corre\u00e7\u00f5es os streams continuarem parando:

1. **Verifique hardware**:
   - Cabos USB das c\u00e2meras
   - Alimenta\u00e7\u00e3o USB (pode estar insuficiente)
   - Temperatura do Raspberry Pi

2. **Logs detalhados**:
   ```bash
   # Ativar logs verbose do FFmpeg temporariamente
   # Editar ffmpeg_manager.py linha ~185
   # Trocar: -loglevel error
   # Por: -loglevel info
   ```

3. **Aumentar recursos**:
   - Aumentar `rtbufsize` no FFmpeg
   - Reduzir bitrate ou resolu\u00e7\u00e3o
   - Adicionar swap se mem\u00f3ria estiver baixa

4. **Use force_cleanup preventivo**:
   - Crie um cron job para limpar a cada hora:
   ```bash
   0 * * * * curl -X POST http://localhost:5000/force_cleanup >/dev/null 2>&1
   ```

## Considera\u00e7\u00f5es Importantes

\u26a0\ufe0f **Sobre perda de segmentos**: As corre\u00e7\u00f5es minimizam, mas n\u00e3o eliminam 100% a chance de perder alguns segundos de grava\u00e7\u00e3o durante restart. Isso \u00e9 inevit\u00e1vel quando processos travam.

\u2705 **Quando usar force_cleanup**: Se os streams pararem de funcionar mas voc\u00ea ver que arquivos continuam sendo gerados, use `force_cleanup` ao inv\u00e9s de reiniciar o servi\u00e7o completo. Isso preserva melhor a continuidade da grava\u00e7\u00e3o.
