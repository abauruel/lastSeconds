# 🚀 Guia de Gravação em RAM (tmpfs)

## 📋 Visão Geral

Sistema de gravação de vídeo otimizado que usa **RAM (tmpfs)** como buffer primário e sincroniza automaticamente para pendrive USB. Elimina problemas de I/O lento, timeouts e corrupção de arquivos.

## ✨ Benefícios

| Métrica | Pendrive USB | RAM (tmpfs) | Ganho |
|---------|--------------|-------------|-------|
| Velocidade gravação | ~10-30 MB/s | ~1000+ MB/s | **33-100x** |
| Latência I/O | 100-500ms | <1ms | **500x** |
| Timeouts FFmpeg | Frequentes | Zero | ✅ |
| Corrupção arquivos | Sim (linha verde) | Não | ✅ |
| Janela de perda | N/A | ~2 minutos | ⚠️ |

## 🏗️ Arquitetura

```
┌──────────────────────────────────────────────────────────┐
│                    Raspberry Pi 4B                       │
│                                                          │
│  ┌─────────────┐                                        │
│  │  FFmpeg     │──────▶ Grava em RAM                    │
│  │  Process    │        /dev/shm/bts/                   │
│  └─────────────┘        (~100MB buffer)                 │
│                                                          │
│         ▼                                                │
│  ┌─────────────────────────────────┐                   │
│  │ Arquivos em RAM (últimos 5 min) │                   │
│  │ video0_YYYYMMDD_HHMMSS.ts       │                   │
│  └─────────────────────────────────┘                   │
│         ▼                                                │
│  ┌─────────────────────────────────┐                   │
│  │ Cron (a cada 1 minuto)           │                   │
│  │ sync_ram_to_pendrive.sh          │                   │
│  └─────────────────────────────────┘                   │
│         ▼                                                │
│  ┌─────────────────────────────────┐                   │
│  │ Move arquivos >1min para:        │                   │
│  │ /media/pi/usb64gb/bts/           │                   │
│  └─────────────────────────────────┘                   │
└──────────────────────────────────────────────────────────┘
```

## 🔧 Setup Automático

```bash
cd /home/pi/app
sudo ./setup_ram_recording.sh
```

Ver detalhes completos em: [AUTO_START_INFO.md](AUTO_START_INFO.md)

## 📊 Monitoramento

```bash
# Status rápido do buffer RAM
/home/pi/app/monitor_ram.sh

# Ver sincronização
tail -f /home/pi/app/logs/sync_ram.log
```

## ⚙️ Configuração Atual

- **Buffer RAM:** 100MB (~5 minutos)
- **Retenção RAM:** 1 minuto
- **Sincronização:** A cada 1 minuto (cron)
- **Janela de risco:** ~2 minutos
- **Auto-start:** ✅ Sim

## 🔄 Como Funciona a Sincronização

1. FFmpeg grava segmentos de 60s em `/dev/shm/bts/`
2. Cron executa `sync_ram_to_pendrive.sh` a cada 1 minuto
3. Script move arquivos com >1 minuto para pendrive
4. Buffer em RAM mantém últimos 5 minutos sempre disponíveis

**Janela de perda máxima:** ~2 minutos (em caso de queda de energia)

## ✅ Validação

```bash
# 1. Verificar gravação em RAM
ls -lht /dev/shm/bts/stream1/ | head -3

# 2. Ver uso de RAM
du -sh /dev/shm/bts

# 3. Verificar sincronização
tail -10 /home/pi/app/logs/sync_ram.log

# 4. Ver arquivos sincronizados
ls -lht /media/pi/usb64gb/bts/stream1/ | head -3
```

## 🚨 Recuperação de Falhas

### Perda de Energia
- Arquivos em RAM são perdidos (até 2 min)
- Sistema reinicia automaticamente
- Diretórios RAM recriados por `ExecStartPre`
- Gravação volta ao normal em ~60s

### Pendrive Cheio
```bash
# Remover gravações antigas
find /media/pi/usb64gb/bts/stream1/ -name "*.ts" -mtime +7 -delete
find /media/pi/usb64gb/bts/stream2/ -name "*.ts" -mtime +7 -delete
```

### RAM Cheia
```bash
# Forçar sincronização manual
/home/pi/app/sync_ram_to_pendrive.sh
```

## 📈 Performance Observada

### Antes (Pendrive USB)
- ❌ Timeouts FFmpeg: Frequentes
- ❌ Corrupção H.264: Linha verde
- ❌ Latência: 100-500ms
- ❌ Gunicorn timeout: Workers morriam

### Depois (RAM tmpfs)
- ✅ Timeouts: Zero
- ✅ Corrupção: Zero
- ✅ Latência: <1ms
- ✅ Processamento: 100% sucesso

## 📚 Documentação Relacionada

- [AUTO_START_INFO.md](AUTO_START_INFO.md) - Inicialização automática
- [MONITORING.md](MONITORING.md) - Monitoramento do sistema
- [README.md](../README.md) - Documentação geral

---

**Status:** 🟢 Produção - Funcionando perfeitamente  
**Última atualização:** 2026-02-14
