# 🏥 Monitoramento de Saúde da Aplicação

Este documento descreve todas as formas de monitorar a saúde da aplicação de gravação de vídeo.

## 📊 Formas de Monitoramento

### 1. Script de Health Check Completo

**Uso mais recomendado** - Mostra todos os detalhes em formato legível:

```bash
/home/pi/app/check_health.sh
```

**O que verifica:**
- ✅ Status do serviço systemd
- ✅ Processos FFmpeg ativos (esperado: 2)
- ✅ Processos zumbis
- ✅ Últimos arquivos gravados (Stream1 e Stream2)
- ✅ Câmeras USB detectadas
- ✅ Uso de disco
- ✅ Logs de erro do FFmpeg
- ✅ Temperatura da CPU
- ✅ Resumo com status geral

**Exemplo de saída:**
```
✅ ✅ ✅ SISTEMA SAUDÁVEL ✅ ✅ ✅
```

---

### 2. Endpoint HTTP `/health`

**Uso em sistemas de monitoramento** - Retorna JSON com status detalhado:

```bash
curl http://localhost:5000/health | python3 -m json.tool
```

**Resposta:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-12T10:17:15.069369",
  "issues": [],
  "ffmpeg_processes": {
    "count": 2,
    "expected": 2,
    "running": true,
    "zombies": 0
  },
  "streams": {
    "stream1": {
      "latest_file": "video0_20260212_101621.mp4",
      "file_age_seconds": 3,
      "file_size_bytes": 1572912,
      "recording": true
    },
    "stream2": {
      "latest_file": "video2_20260212_101621.mp4",
      "file_age_seconds": 11,
      "file_size_bytes": 786480,
      "recording": true
    }
  },
  "cameras": {
    "detected": ["/dev/video0", "/dev/video2"],
    "count": 2
  },
  "disk": {
    "total_bytes": 61603581952,
    "used_bytes": 9395933184,
    "available_bytes": 49045151744,
    "usage_percent": 17
  },
  "system": {
    "cpu_temperature_celsius": 53.07
  }
}
```

**Códigos HTTP:**
- `200` - Sistema saudável ou degradado (com avisos)
- `503` - Sistema não saudável (gravação parada)
- `500` - Erro interno ao verificar saúde

---

### 3. Comandos Manuais Rápidos

#### Verificar processos FFmpeg:
```bash
ps aux | grep ffmpeg | grep -E "(video0|video2)" | grep -v grep
```
**Esperado:** 2 processos ativos

#### Verificar últimos arquivos gravados:
```bash
# Stream1
ls -lth /media/pi/usb64gb/bts/stream1/ | head -5

# Stream2
ls -lth /media/pi/usb64gb/bts/stream2/ | head -5
```

#### Verificar processos zumbis:
```bash
ps aux | grep defunct | grep ffmpeg
```
**Esperado:** Nenhum processo (ou poucos temporários)

#### Verificar câmeras USB:
```bash
v4l2-ctl --list-devices | grep -A2 "usb-webcam"
```
**Esperado:** 2 câmeras (/dev/video0 e /dev/video2)

#### Verificar logs de erro:
```bash
# Stream1
tail -20 /media/pi/usb64gb/bts/ffmpeg_device0.log

# Stream2
tail -20 /media/pi/usb64gb/bts/ffmpeg_device2.log
```

#### Verificar status do serviço:
```bash
systemctl status better_seconds_record.service
```

---

### 4. Limpeza de Processos Zumbis

Se houver muitos processos zumbis (defunct):

```bash
/home/pi/app/cleanup_zombies.sh
```

**Nota:** O Watchdog automático já limpa zumbis periodicamente.

---

## 🐕 Watchdog Automático

A aplicação possui um **watchdog automático** que:

- ✅ Verifica saúde dos processos FFmpeg **a cada 60 segundos**
- ✅ Detecta se processos morreram
- ✅ Detecta se arquivos não são criados por >5 minutos
- ✅ **Reinicia automaticamente** processos problemáticos
- ✅ Limpa processos zumbis periodicamente
- ✅ Re-detecta câmeras se dispositivo sumir

### Ver logs do Watchdog:

```bash
sudo journalctl -u better_seconds_record.service -f | grep -E "(Watchdog|ALERTA|Reiniciando)"
```

---

## 🚨 Alertas e Problemas

### Status possíveis:

| Status | Descrição | Ação |
|--------|-----------|------|
| **healthy** ✅ | Tudo funcionando | Nenhuma |
| **degraded** ⚠️ | Problemas menores (zumbis, disco alto) | Monitorar |
| **unhealthy** ❌ | Gravação parada, câmera desconectada | Investigar |

### Problemas comuns:

#### 1. Stream parou de gravar
**Sintoma:** Último arquivo tem >5 minutos

**Solução automática:** Watchdog reinicia em até 60s

**Solução manual:**
```bash
sudo systemctl restart better_seconds_record.service
```

#### 2. Câmera desconectada
**Sintoma:** `/dev/video0` ou `/dev/video2` não existe

**Solução:**
1. Reconectar câmera USB
2. Aguardar Watchdog detectar (60s)
3. Ou reiniciar manualmente o serviço

#### 3. Espaço em disco baixo
**Sintoma:** Uso > 80%

**Solução:**
```bash
# Limpar arquivos antigos
find /media/pi/usb64gb/bts/stream1 -type f -mtime +30 -delete
find /media/pi/usb64gb/bts/stream2 -type f -mtime +30 -delete
```

#### 4. Muitos processos zumbis
**Sintoma:** >10 processos defunct

**Solução:**
```bash
/home/pi/app/cleanup_zombies.sh
```

#### 5. Temperatura alta
**Sintoma:** CPU > 70°C

**Solução:**
- Verificar ventilação
- Limpar poeira
- Reduzir taxa de frames

---

## 📱 Monitoramento Remoto

### Integração com sistemas de monitoramento:

#### Prometheus:
```yaml
- job_name: 'recording-system'
  metrics_path: '/health'
  static_configs:
    - targets: ['192.168.1.X:5000']
```

#### Uptime Kuma:
- Tipo: HTTP(s)
- URL: `http://192.168.1.X:5000/health`
- Interval: 60s
- Esperado: Status 200

#### Script de alerta simples:
```bash
#!/bin/bash
STATUS=$(curl -s http://localhost:5000/health | jq -r '.status')
if [ "$STATUS" != "healthy" ]; then
    echo "ALERTA: Sistema não saudável - $STATUS" | mail -s "Alerta Recording" admin@example.com
fi
```

---

## 🔧 Manutenção

### Verificação diária recomendada:
```bash
/home/pi/app/check_health.sh
```

### Logs importantes:
```bash
# Logs do serviço
sudo journalctl -u better_seconds_record.service -n 100

# Logs do FFmpeg
tail -100 /media/pi/usb64gb/bts/ffmpeg_device0.log
tail -100 /media/pi/usb64gb/bts/ffmpeg_device2.log

# Logs do sistema
dmesg | grep -i "video\|usb" | tail -50
```

---

## 💡 Dicas

1. **Configure alertas** no endpoint `/health` para ser notificado de problemas
2. **Monitore o disco** regularmente - a gravação para quando cheio
3. **Watchdog cuida da maioria dos problemas** automaticamente
4. **Em caso de dúvida**, reinicie o serviço:
   ```bash
   sudo systemctl restart better_seconds_record.service
   ```

---

## 📞 Suporte

Se o problema persistir após estas verificações:

1. Capture logs completos:
   ```bash
   sudo journalctl -u better_seconds_record.service -n 500 > /tmp/service.log
   tail -500 /media/pi/usb64gb/bts/ffmpeg_device*.log > /tmp/ffmpeg.log
   dmesg > /tmp/dmesg.log
   ```

2. Execute health check completo:
   ```bash
   /home/pi/app/check_health.sh > /tmp/health.txt
   ```

3. Compartilhe os arquivos `/tmp/*.log` e `/tmp/health.txt`
