# Correções Implementadas - Arquivos .ts Corrompidos

## Data: 13 de Fevereiro de 2026

---

## 🔍 Problema Identificado

Arquivos .ts com **0 bytes** eram criados quando o processo FFmpeg era reiniciado. Análise do log `video_integrity_20260213_144037.log` mostrou:

- **4 arquivos corrompidos** de 299 totais (1.3%)
- Todos tinham 0 bytes
- Criados segundos antes de reinícios do FFmpeg

### Causas Raiz:
1. **Erro no filesystem EXT4** no disco USB (detectado em dmesg)
2. FFmpeg criava arquivo vazio ao iniciar novo segmento
3. Processo reiniciado antes de escrever dados
4. Watchdog reiniciando processos em falsos-positivos
5. **🔴 CRÍTICO: Múltiplos workers do Gunicorn** - 4 workers criando 4 watchdogs competindo pelos mesmos processos

---

## ✅ Correções Implementadas

### 1. **Melhorias na Configuração FFmpeg**
- ✅ Adicionado `segment_atclocktime=1` e `segment_clocktime_offset=0`
- Garante que segmentos sejam criados apenas quando há dados reais
- Alinha criação de segmentos com o relógio do sistema

**Localização:** [ffmpeg_manager.py](ffmpeg_manager.py#L199) (linha 199 e 217)

### 2. **Melhoria no Health Check**
- ✅ Verifica tamanho do arquivo além de timestamp
- Detecta arquivos vazios com mais de 10 segundos
- Evita falsos-positivos que causavam reinícios desnecessários

**Localização:** [ffmpeg_manager.py](ffmpeg_manager.py#L403) (linha 403)

```python
# Verifica se arquivo tem 0 bytes e mais de 10 segundos
if file_size == 0 and file_age > 10:
    print(f"⚠️ ALERTA: Arquivo mais recente está vazio há {file_age:.0f}s")
    return False
```

### 3. **Logging de Restarts**
- ✅ Log de todos os restart salvos em `/media/pi/usb64gb/bts/ffmpeg_restart_log.txt`
- Permite identificar padrões de reinícios
- Útil para debug futuro

**Localização:** [ffmpeg_manager.py](ffmpeg_manager.py#L433) (linha 433)

### 4. **Limpeza Automática de Arquivos Vazios**
- ✅ Nova função `_cleanup_empty_segments()`
- Remove arquivos .ts e .mp4 com 0 bytes após 60 segundos
- Executada automaticamente pelo watchdog a cada minuto

**Localização:** [ffmpeg_manager.py](ffmpeg_manager.py#L573) (linha 573)

### 5. **Script de Verificação**
- ✅ Criado script `check_empty_files.sh`
- Verifica manualmente arquivos vazios
- Útil para diagnóstico

**Uso:**
```bash
cd /home/pi/app
./check_empty_files.sh
```

### 6. **🔴 CORREÇÃO CRÍTICA: Gunicorn Multi-Worker**
- ✅ Criado `gunicorn_config.py` com configuração correta
- Reduzido de 4 para 2 workers (suficiente para a carga)
- Ativado `preload_app=True` - FFmpeg inicializado apenas uma vez
- Modificado `capture3.py` para detectar ambiente gunicorn
- Script `update_service.sh` para atualizar o serviço

**Problema antes:** 4 workers = 4 instâncias FFMpegManager = 4 watchdogs = CAOS
**Solução:** 1 instância FFMpegManager no master process = 1 watchdog = ORDEM

**Aplicar correção:**
```bash
cd /home/pi/app
sudo ./update_service.sh
sudo systemctl restart better_seconds_record.service
```

---

## ⚠️ AÇÕES NECESSÁRIAS (ORDEM DE PRIORIDADE)

### 1. 🔴 URGENTE: Corrigir Worker Loop (CRÍTICO)

O sistema está em **loop infinito de restarts** porque múltiplos workers estão competindo:

```bash
cd /home/pi/app
sudo ./update_service.sh
sudo systemctl restart better_seconds_record.service
```

**Verificar se corrigiu:**
```bash
# Deve mostrar apenas 2 processos FFmpeg (não dezenas)
ps aux | grep ffmpeg | grep -v grep | wc -l

# Não deve mais mostrar loops de restart
journalctl -u better_seconds_record.service -f
```

### 2. ⚠️ IMPORTANTE: Corrigir Filesystem do Disco USB

O disco USB tem **erro no filesystem EXT4** detectado no kernel:
```
EXT4-fs error (device sda1): ext4_validate_block_bitmap:421: 
bg 215: bad block bitmap checksum
```

**EXECUTAR IMEDIATAMENTE:**

```bash
# 1. Parar o serviço
sudo systemctl stop video_uploader.service

# 2. Desmontar o disco
sudo umount /media/pi/usb64gb

# 3. Verificar e corrigir filesystem
sudo fsck -fy /dev/sda1

# 4. Remontar
sudo mount /media/pi/usb64gb

# 5. Reiniciar serviço
sudo systemctl start video_uploader.service
```

**⚠️ Importante:** 
- O `fsck` pode levar alguns minutos
- Backup dos dados importantes antes se possível
- Considerar substituir o disco se erros persistirem

---

## 📊 Monitoramento

### Verificar Log de Restarts:
```bash
tail -f /media/pi/usb64gb/bts/ffmpeg_restart_log.txt
```

### Verificar Arquivos Vazios:
```bash
find /media/pi/usb64gb/bts/stream1 -name "*.ts" -size 0
find /media/pi/usb64gb/bts/stream2 -name "*.ts" -size 0
```

### Status do Watchdog:
```bash
journalctl -u video_uploader.service -f | grep -E "watchdog|restart|empty"
```

---

## 🎯 Resultados Esperados

Com essas correções:
- ✅ Redução drástica de arquivos 0-byte criados
- ✅ Limpeza automática de arquivos corrompidos
- ✅ Menos reinícios desnecessários do FFmpeg
- ✅ Melhor diagnóstico com logging
- ✅ Sistema mais resiliente a falhas

---

## 📝 Próximos Passos (Se Problemas Persistirem)

1. Analisar `/media/pi/usb64gb/bts/ffmpeg_restart_log.txt` para padrões
2. Verificar temperatura do Raspberry Pi (pode causar instabilidade USB)
3. Testar com outro disco USB para descartar hardware defeituoso
4. Considerar adicionar cache em RAM para escritas do FFmpeg

---

## 🔧 Reversão (Se Necessário)

As mudanças são minimamente invasivas. Para reverter:
1. Remover `segment_atclocktime=1:segment_clocktime_offset=0` das linhas 199 e 217
2. Comentar chamada `_cleanup_empty_segments()` na linha 557

---

**Status:** ✅ Implementado e pronto para teste
**Requer Restart:** Sim - `sudo systemctl restart video_uploader.service`
