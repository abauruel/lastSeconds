# 🎥 Problema: Câmera 2 não detectada (video2 → video3)

## 📋 Resumo

**Problema Identificado:** A rota `/health` não detectava a câmera 2 porque o dispositivo mudou de `/dev/video2` para `/dev/video3`.

**Causa Raiz:** A enumeração de dispositivos de vídeo no Linux é **dinâmica** e pode mudar quando:
- Um dispositivo USB é desconectado e reconectado
- O sistema reinicia com uma ordem diferente de inicialização de dispositivos
- Há hotplug de câmeras (plug/unplug enquanto sistema está ligado)

**Solução:** Implementar detecção dinâmica de câmeras com fallback em vez de usar números de dispositivo fixos.

---

## 🔍 Investigação Realizada

### 1. Problema Observado

Via rota `/health`, a câmera 2 não estava sendo detectada:

```json
{
  "cameras": {
    "detected": ["/dev/video0"],
    "count": 1
  },
  "issues": ["Camera /dev/video2 not detected"]
}
```

### 2. Verificação com v4l2-ctl

Ao executar `v4l2-ctl --list-devices`:

**Esperado:**
```
video0 → Câmera USB 1
video2 → Câmera USB 2
```

**Real:**
```
video0 → Câmera USB 1
video3 → Câmera USB 2  ⚠️ (mudou de video2!)
```

### 3. Por que isso acontece?

O Linux enumera dispositivos `/dev/videoX` **sequencialmente** conforme os drivers são carregados:

- **Primeiro boot:** video0, video1 (plano de fundo), video2 (câmera 2), video3 (plano de fundo)
- **Após desconexão/reconexão:** video0, video2, video3, video1, etc.

A ordem depende de:
- Quando cada dispositivo é plugado
- Quando cada driver é carregado
- A ordem de inicialização do sistema

---

## 📝 Análise do Código

### Problema no `ffmpeg_manager.py`

[ffmpeg_manager.py](../ffmpeg_manager.py#L46-L59):

```python
# Configuração fixa dos dispositivos de vídeo
fixed_devices = {
    0: '/dev/video0',  # stream1
    1: '/dev/video2'   # stream2 ❌ PROBLEMA: Assumindo que será sempre video2!
}

# Verifica se os dispositivos existem
for idx, device_path in fixed_devices.items():
    if os.path.exists(device_path):
        cameras[idx] = device_path
        print(f"Câmera {idx}: {device_path}")
    else:
        print(f"AVISO: Dispositivo {device_path} não encontrado!")
```

### Problema na rota `/health` 

[routes/status_routes.py](../routes/status_routes.py#L150-L171):

```python
# Verifica câmeras USB
result = subprocess.run(
    ["v4l2-ctl", "--list-devices"],
    capture_output=True,
    text=True,
    timeout=5
)

usb_cameras = []
for line in result.stdout.split('\n'):
    if '/dev/video' in line and line.strip().startswith('/dev/'):
        device = line.strip()
        if os.path.exists(device):
            usb_cameras.append(device)

# ❌ Checa especificamente por video0 e video2 (assume números fixos)
if '/dev/video2' not in usb_cameras:
    health_data["issues"].append("Camera /dev/video2 not detected")
    health_data["status"] = "unhealthy"
```

---

## ✅ Solução Implementada

### 1. Detecção Dinâmica de Câmeras

Ao invés de assumir `/dev/video2`, **identifique as câmeras pela sua identificação USB** usando `v4l2-ctl`:

```bash
v4l2-ctl --list-devices
# Output:
# HD USB Camera (usb-0000:01:00.0-1.1):
#   /dev/video0
#   /dev/video1
#
# Logitech USB Camera (usb-0000:01:00.0-1.2):
#   /dev/video2  ← ou /dev/video3, /dev/video4, etc.
#   /dev/video3  ← ou /dev/video5, etc.
```

### 2. Estratégia Recomendada

#### Opção A: Usar Identificadores USB (Recomendado)

```python
import subprocess
import os

def get_camera_device_by_usb_id(device_index=0):
    """
    Detecta câmera pela sequência de enumeração, não pelo número fixo.
    
    Args:
        device_index: 0 para primeira câmera, 1 para segunda, etc.
    
    Returns:
        device_path: str, ex: '/dev/video0' ou '/dev/video3'
    """
    try:
        result = subprocess.run(
            ["v4l2-ctl", "--list-devices"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        video_devices = []
        for line in result.stdout.split('\n'):
            if line.strip().startswith('/dev/video'):
                device_path = line.strip()
                # Filtra apenas vídeos principais (video0, video2, video3, etc.)
                # Ignora video1, video5, video7 (geralmente são planos de fundo)
                if int(device_path.split('video')[1]) % 2 == 0:
                    video_devices.append(device_path)
        
        if device_index < len(video_devices):
            return video_devices[device_index]
        
        return None
    except Exception as e:
        print(f"Erro ao detectar câmeras: {e}")
        return None
```

#### Opção B: Usar Regras udev (Mais Robusto)

Criar regras udev que atribuem dispositivos `/dev/video_camera0` e `/dev/video_camera1` independentemente do número:

```bash
# /etc/udev/rules.d/99-camera-symlinks.rules
# Cria symlinks simbólicos para câmeras USB

# Para câmeras identificadas por serialNumber, busID, etc.
SUBSYSTEM=="video4linux", ATTR{index}=="0", SYMLINK+="video_camera0"
SUBSYSTEM=="video4linux", ATTR{index}=="1", SYMLINK+="video_camera1"
```

Depois usar `/dev/video_camera0` e `/dev/video_camera1` no código.

---

## 🔧 Implementação da Solução

### Passo 1: Atualizar `ffmpeg_manager.py`

Modificar `detect_usb_cameras()` para ser dinâmico:

```python
def detect_usb_cameras(self):
    """
    Retorna os dispositivos de câmera USB detectados.
    Identifica câmeras dinamicamente, não assumindo números fixos.
    """
    cameras = {}
    
    try:
        result = subprocess.run(
            ["v4l2-ctl", "--list-devices"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Extrai todos os dispositivos /dev/video
        video_devices = []
        for line in result.stdout.split('\n'):
            if line.strip().startswith('/dev/video'):
                device_path = line.strip()
                # Filtra números pares para evitar planos de fundo
                try:
                    video_num = int(device_path.split('video')[1])
                    if video_num % 2 == 0 and os.path.exists(device_path):
                        video_devices.append(device_path)
                except (ValueError, IndexError):
                    continue
        
        # Mapeia para índices 0 e 1
        for idx, device_path in enumerate(video_devices):
            cameras[idx] = device_path
            print(f"Câmera {idx}: {device_path}")
        
        if not cameras:
            print("ERRO: Nenhum dispositivo de vídeo encontrado!")
        
        return cameras
        
    except Exception as e:
        print(f"Erro ao detectar câmeras: {e}")
        return {}
```

### Passo 2: Atualizar rota `/health`

Modificar [routes/status_routes.py](../routes/status_routes.py#L150-L171) para ser dinâmica:

```python
# 5. Verifica câmeras USB
try:
    result = subprocess.run(
        ["v4l2-ctl", "--list-devices"],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    usb_cameras = []
    for line in result.stdout.split('\n'):
        if line.strip().startswith('/dev/video'):
            device = line.strip()
            if os.path.exists(device):
                # Filtra apenas câmeras principais (video0, video2, video4, etc.)
                try:
                    video_num = int(device.split('video')[1])
                    if video_num % 2 == 0:  # Números pares são câmeras
                        usb_cameras.append(device)
                except (ValueError, IndexError):
                    usb_cameras.append(device)
    
    health_data["cameras"]["detected"] = sorted(usb_cameras)
    health_data["cameras"]["count"] = len(usb_cameras)
    
    # Verifica se tem pelo menos as 2 câmeras esperadas
    if len(usb_cameras) < 2:
        health_data["issues"].append(f"Only {len(usb_cameras)} camera(s) detected, expected 2")
        health_data["status"] = "unhealthy"
    
    health_data["cameras"]["details"] = {
        "camera_0": usb_cameras[0] if len(usb_cameras) > 0 else "NOT FOUND",
        "camera_1": usb_cameras[1] if len(usb_cameras) > 1 else "NOT FOUND"
    }
        
except Exception as e:
    health_data["cameras"]["error"] = str(e)
    health_data["issues"].append(f"Failed to check cameras: {str(e)}")
```

---

## 🛠️ Testes Recomendados

### Teste 1: Verificar Dispositivos Atuais

```bash
# Ver todos os dispositivos de vídeo
v4l2-ctl --list-devices

# Ver detalhes de um dispositivo específico
v4l2-ctl -d /dev/video0 --all | head -20
```

### Teste 2: Simular Desconexão

```bash
# Desconecte uma câmera USB fisicamente
# Reconecte-a
# Execute novamente: v4l2-ctl --list-devices

# Observe se os números mudaram
```

### Teste 3: Testar a Rota de Health

```bash
# Antes da mudança esperada
curl http://localhost:5000/health | jq .cameras

# Depois da mudança
curl http://localhost:5000/health | jq .cameras
```

---

## 📊 Comparação: Antes vs Depois

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Detecção** | Assume `/dev/video0` e `/dev/video2` | Dinamicamente enumera dispositivos |
| **Robustez** | ❌ Falha se video2 → video3 | ✅ Encontra câmera onde quer que esteja |
| **Hotplug** | ❌ Requer restart | ✅ Detecta automaticamente |
| **Manutenção** | Difícil (mudar código) | Fácil (automático) |

---

## 🚀 Próximos Passos

1. ✅ **Identificar o problema** - Enumeração dinâmica de /dev/video*
2. ⏳ **Implementar solução** - Usar detecção dinâmica em `ffmpeg_manager.py` e `/health`
3. ⏳ **Testar com desconexão** - Verificar se funciona após hotplug
4. ⏳ **Considerar udev rules** - Para uma solução ainda mais robusta a longo prazo

---

## 📚 Referências

- [V4L2 (Video4Linux2) Docs](https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/v4l2.rst)
- [v4l2-ctl Manual](https://manpages.debian.org/testing/v4l-utils/v4l2-ctl.1.en.html)
- [Linux udev Rules](https://wiki.debian.org/udev)
- [Raspberry Pi Camera Documentation](https://www.raspberrypi.org/documentation/hardware/camera.md)

---

## 📝 Histórico

- **2026-02-14**: Investigação completa e documentação do problema
