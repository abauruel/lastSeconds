# Procedimento: Resolver Problema de Câmera 2 Não Detectada

## 🔴 Sintoma

```
GET /health

{
  "cameras": {
    "detected": ["/dev/video0"],
    "count": 1,
    "issues": ["Camera /dev/video2 not detected"]
  },
  "status": "unhealthy"
}
```

## 🔍 Diagnóstico

### Passo 1: Verificar dispositivos atuais

```bash
v4l2-ctl --list-devices
```

**Saída esperada (antes):**
```
HD USB Camera (usb-0000:01:00.0-1.1):
    /dev/video0
    /dev/video1
Logitech USB Camera (usb-0000:01:00.0-1.2):
    /dev/video2
    /dev/video3
```

**Saída observada (problema):**
```
HD USB Camera (usb-0000:01:00.0-1.1):
    /dev/video0
    /dev/video1
Logitech USB Camera (usb-0000:01:00.0-1.2):
    /dev/video3  ← ⚠️ Mudou de video2!
    /dev/video4
```

### Passo 2: Verificar quais câmeras existem

```bash
ls -la /dev/video*
```

### Passo 3: Inspecionar configuração atual

```bash
# Ver qual camera está mapeada para stream1 e stream2
cat /home/pi/app/ffmpeg_manager.py | grep -A 10 "detect_usb_cameras"

# Ver logs de erro
tail -50 /media/pi/usb64gb/bts/ffmpeg_device*.log
```

---

## ✅ Solução Implementada

### O Problema
O código original usava números **fixos** para dispositivos:

```python
fixed_devices = {
    0: '/dev/video0',  # ✓ Sempre video0
    1: '/dev/video2'   # ✗ Assume que será sempre video2!
}
```

Mas no Linux, a enumeração `/dev/videoX` é **dinâmica**:
- Depende da ordem de conexão dos dispositivos USB
- Muda após desconexão/reconexão
- Muda após reinicialização do sistema

### A Solução
Implementar **detecção dinâmica**:

1. **Em [ffmpeg_manager.py](../ffmpeg_manager.py#L48)**: Função `detect_usb_cameras()` agora:
   - Executa `v4l2-ctl --list-devices` para descobrir todos os /dev/video*
   - Filtra números pares (câmeras principais)
   - Mapeia para índices 0 e 1
   - Fallback: tenta dispositivos conhecidos se dinâmico falhar

2. **Em [routes/status_routes.py](../routes/status_routes.py#L145)**: Rota `/health` agora:
   - Enumera dinamicamente todos os /dev/video* disponíveis
   - Filtra por números pares
   - Retorna lista completa em `cameras.detected`
   - Não assume número fixo para video2

---

## 🧪 Teste Prático

### Teste 1: Verificar detecção automática

```bash
./test_camera_detection.sh
```

Você deve ver:
```
✓ camera_0: /dev/video0 (detectada dinamicamente)
✓ camera_1: /dev/video2 (detectada dinamicamente)  # ou video3, video4, etc
```

### Teste 2: Simular desconexão/reconexão

```bash
# 1. Desconecte uma câmera USB fisicamente (aguarde 10s)

# 2. Reconecte-a

# 3. Execute
v4l2-ctl --list-devices

# Você verá que o número pode ter mudado (ex: video3 → video2)

# 4. Teste novamente
./test_camera_detection.sh

# A câmera deve ser detectada no novo número!
```

### Teste 3: Verificar rota /health

```bash
curl http://localhost:5000/health | jq '.cameras'
```

Esperado:
```json
{
  "detected": ["/dev/video0", "/dev/video2"],  # ou video3, video4
  "count": 2,
  "details": {
    "camera_0": "/dev/video0",
    "camera_1": "/dev/video2"  # ou novo número
  }
}
```

---

## 🔧 Implementação Passo-a-Passo

### Se você quiser implementar manualmente:

**1. Atualizar `detect_usb_cameras()` em ffmpeg_manager.py**

```python
def detect_usb_cameras(self):
    """Detecta câmeras dinamicamente via v4l2-ctl"""
    cameras = {}
    
    try:
        # Obter dispositivos com v4l2-ctl
        result = subprocess.run(
            ["v4l2-ctl", "--list-devices"],
            capture_output=True, text=True, timeout=5
        )
        
        # Extrair /dev/video* com números pares
        video_devices = []
        for line in result.stdout.split('\n'):
            if line.strip().startswith('/dev/video'):
                device = line.strip()
                num = int(device.split('video')[1])
                if num % 2 == 0 and os.path.exists(device):
                    video_devices.append(device)
        
        # Mapear para índices 0 e 1
        for idx, device in enumerate(sorted(video_devices)[:2]):
            cameras[idx] = device
            
    except:
        # Fallback: tentar dispositivos fixos
        for device in ['/dev/video0', '/dev/video2']:
            if os.path.exists(device):
                cameras[len(cameras)] = device
    
    return cameras
```

**2. Atualizar rota `/health` em routes/status_routes.py**

```python
# 5. Câmeras USB
try:
    result = subprocess.run(
        ["v4l2-ctl", "--list-devices"],
        capture_output=True, text=True, timeout=5
    )
    
    # Extrair /dev/video* com números pares
    usb_cameras = []
    for line in result.stdout.split('\n'):
        if line.strip().startswith('/dev/video'):
            device = line.strip()
            if os.path.exists(device):
                num = int(device.split('video')[1])
                if num % 2 == 0:
                    usb_cameras.append(device)
    
    health_data["cameras"]["detected"] = sorted(usb_cameras)
    health_data["cameras"]["count"] = len(usb_cameras)
    
    if len(usb_cameras) < 2:
        health_data["issues"].append(f"Only {len(usb_cameras)} cameras detected")
        health_data["status"] = "unhealthy"
        
except Exception as e:
    health_data["cameras"]["error"] = str(e)
    health_data["issues"].append(f"Failed to check cameras: {str(e)}")
```

---

## 📋 Checklist de Validação

- [ ] Executei `./test_camera_detection.sh` e 2 câmeras foram detectadas
- [ ] Consultei `/health` e `cameras.count` = 2
- [ ] Desconectei/reconectei uma câmera USB
- [ ] Executei `v4l2-ctl --list-devices` e observei mudança no número
- [ ] Executei `./test_camera_detection.sh` novamente e câmeras foram encontradas
- [ ] FFmpeg está rodando sem erros (verifique logs)
- [ ] Streams estão sendo gravados (verifique `/media/pi/usb64gb/bts/stream1` e `stream2`)

---

## 🚨 Troubleshooting

### Problema: "v4l2-ctl command not found"

```bash
sudo apt-get update
sudo apt-get install -y v4l-utils
```

### Problema: Nenhuma câmera detectada

```bash
# Verificar se as câmeras estão conectadas
lsusb | grep -i camera
lsusb | grep -i -E "logitech|webcam"

# Ver todos os dispositivos de vídeo (incluindo internos)
v4l2-ctl --list-devices

# Testar acesso direto a um dispositivo
ffmpeg -f v4l2 -input_format mjpeg -i /dev/video0 -t 1 -f null -
```

### Problema: Stream2 não está gravando

```bash
# Verificar se ffmpeg encontrou a câmera corretamente
tail -100 /media/pi/usb64gb/bts/ffmpeg_device1.log | grep -i "video\|error"

# Testar câmera 2 manualmente
ffmpeg -f v4l2 -input_format mjpeg -i /dev/video3 -t 1 test.mp4
```

---

## 📊 Antes vs Depois

| Antes | Depois |
|-------|--------|
| ❌ Assume video2 fixo | ✅ Detecta dinamicamente |
| ❌ Falha se video2→video3 | ✅ Funciona com qualquer número |
| ❌ Requer restart para hotplug | ✅ Detecta mudanças automaticamente |
| ❌ Mensagem confusa de erro | ✅ Mostra dispositivos reais encontrados |

---

## 📚 Referências Técnicas

- **Linux V4L2**: Enumeração dinâmica de dispositivos de vídeo
- **udev**: Sistema de gerenciamento de dispositivos no Linux
- **ffmpeg_manager.py**: Detecção e inicialização de câmeras
- **routes/status_routes.py**: Endpoint de health check com status

---

## 📞 Suporte

Para mais detalhes, ver: [CAMERA_DEVICE_ENUMERATION.md](./CAMERA_DEVICE_ENUMERATION.md)
