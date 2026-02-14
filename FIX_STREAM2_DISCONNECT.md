# 🔧 Solução para Stream2 Caindo Constantemente

## 🔍 Problema Identificado

A câmera USB da stream2 (porta 1-1.4, /dev/video2) está desconectando e reconectando a cada 2-5 minutos devido a problemas de hardware USB.

### Evidências no dmesg:
```
[27266.858390] usb 1-1.4: USB disconnect
[27267.092132] usb 1-1.4: new high-speed USB device
[27425.858811] usb 1-1.4: USB disconnect
[27426.093922] usb 1-1.4: new high-speed USB device
... (múltiplas desconexões)
```

## ✅ Soluções (em ordem de prioridade)

### **SOLUÇÃO 1: Trocar Porta USB (MAIS EFETIVO)** 🔌

**Ação:** Trocar fisicamente a câmera da stream2 para outra porta USB do Raspberry Pi

**Passos:**
1. Parar o serviço:
   ```bash
   sudo systemctl stop better_seconds_record.service
   ```

2. Desconectar a câmera da porta USB atual (1-1.4)

3. Conectar em uma porta USB diferente (preferencialmente USB 2.0 direto na placa)

4. Aguardar 5 segundos e verificar detecção:
   ```bash
   v4l2-ctl --list-devices | grep -A2 "usb-webcam"
   ```

5. Reiniciar serviço:
   ```bash
   sudo systemctl start better_seconds_record.service
   ```

6. Monitorar por 30 minutos:
   ```bash
   /home/pi/app/monitor_ram.sh
   ```

**Vantagem:** Resolve se o problema for da porta USB específica (mais provável)

---

### **SOLUÇÃO 2: Usar Hub USB Powered Externo** ⚡

**Problema:** Raspberry Pi pode não fornecer corrente suficiente para ambas as câmeras

**Ação:** Conectar as câmeras através de um hub USB com alimentação externa

**Passos:**
1. Adquirir hub USB 2.0/3.0 com alimentação própria (5V 2A ou mais)
2. Conectar as 2 webcams ao hub powered
3. Conectar o hub ao Raspberry Pi
4. Reiniciar e testar

**Vantagem:** Garante energia estável para ambas as câmeras

---

### **SOLUÇÃO 3: Desabilitar Autosuspensão USB (JÁ APLICADO)** ✅

**Status:** ✅ Já aplicado automaticamente

O sistema já desabilitou a suspensão USB:
```bash
echo 'on' > /sys/bus/usb/devices/1-1.4/power/control
```

Para tornar permanente, adicione ao `/etc/rc.local` (antes de `exit 0`):
```bash
echo 'on' > /sys/bus/usb/devices/1-1.*/power/control 2>/dev/null || true
```

---

### **SOLUÇÃO 4: Aumentar Corrente USB via config.txt** ⚡

**Ação:** Aumentar a corrente máxima fornecida às portas USB

**Passos:**
1. Editar `/boot/config.txt`:
   ```bash
   sudo nano /boot/config.txt
   ```

2. Adicionar no final:
   ```
   # Aumenta corrente USB para webcams
   max_usb_current=1
   usb_max_current_enable=1
   ```

3. Reiniciar:
   ```bash
   sudo reboot
   ```

**Vantagem:** Permite até 1.2A por porta (padrão é 600mA)

**⚠️ ATENÇÃO:** Requer fonte de alimentação adequada (5V 3A mínimo)

---

### **SOLUÇÃO 5: Reduzir Resolução/FPS da Stream2** 📉

**Ação:** Reduzir carga da câmera problemática

**Passos:**
1. Editar configuração no código [ffmpeg_manager.py](ffmpeg_manager.py#L225):

   Linha atual:
   ```python
   "-f", "v4l2", "-input_format", "h264", "-video_size", "1280x720", "-r", "25",
   ```

   Mudar para:
   ```python
   "-f", "v4l2", "-input_format", "h264", "-video_size", "640x480", "-r", "15",
   ```

2. Reiniciar serviço

**Vantagem:** Reduz consumo de energia e processamento

---

### **SOLUÇÃO 6: Melhorar Resfriamento** 🌡️

**Ação:** Adicionar dissipador/cooler na câmera ou no Raspberry Pi

**Passos:**
- Adicionar ventilador no case do Raspberry Pi
- Verificar se as câmeras estão em local ventilado
- Adicionar dissipador térmico nas câmeras

---

### **SOLUÇÃO 7: Script de Monitoramento de Desconexões** 📊

Criar script para detectar e logar desconexões automaticamente:

```bash
#!/bin/bash
# /home/pi/app/monitor_usb_disconnects.sh

while true; do
    dmesg | grep "USB disconnect" | grep "1-1.4" | tail -1 >> /home/pi/app/logs/usb_disconnect.log
    sleep 30
done
```

Executar em background:
```bash
chmod +x /home/pi/app/monitor_usb_disconnects.sh
nohup /home/pi/app/monitor_usb_disconnects.sh &
```

---

## 🧪 Como Testar Se o Problema Foi Resolvido

```bash
# 1. Monitorar desconexões USB em tempo real
dmesg -w | grep "1-1.4"

# 2. Verificar estabilidade da gravação (deve mostrar arquivos novos a cada minuto)
watch -n 5 'ls -lth /dev/shm/bts/stream2/ | head -5'

# 3. Ver logs do watchdog (não deve aparecer alertas de device1)
sudo journalctl -u better_seconds_record.service -f | grep -E "(device1|stream2|ALERTA)"

# 4. Teste de 1 hora
# Aguardar 1 hora e verificar se houve desconexões:
dmesg | grep "USB disconnect" | grep "1-1.4" | tail -20
```

**Sucesso:** Nenhuma desconexão por pelo menos 1 hora

---

## 📋 Checklist de Diagnóstico

- [x] Problema identificado: Desconexões USB da porta 1-1.4
- [x] Causa provável: Energia insuficiente ou porta USB defeituosa
- [ ] Teste 1: Trocar porta USB
- [ ] Teste 2: Usar hub USB powered
- [ ] Teste 3: Aumentar corrente USB via config.txt
- [ ] Teste 4: Monitorar por 1 hora após mudanças

---

## 🔗 Arquivos Relacionados

- [ffmpeg_manager.py](ffmpeg_manager.py) - Gerenciador de processos FFmpeg
- [MONITORING.md](docs/MONITORING.md) - Guia de monitoramento
- Logs: `/home/pi/app/logs/`
- Kernel: `dmesg | grep usb`

---

## 📞 Próximos Passos

1. **IMEDIATO:** Trocar câmera para outra porta USB
2. **SE NÃO RESOLVER:** Testar com hub USB powered
3. **SE PERSISTIR:** Trocar cabo USB da câmera
4. **ÚLTIMA OPÇÃO:** Trocar a câmera física por outra

A stream1 está estável (porta 1-1.3), então o problema é específico da porta 1-1.4 ou da câmera da stream2.
