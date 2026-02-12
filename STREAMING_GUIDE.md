# 📹 Guia Completo - Visualização de Câmeras em Tempo Real

## 🎥 Como Acessar as Câmeras

Você tem **3 formas** de visualizar as câmeras ao vivo em diferentes dispositivos:

---

## 📺 1. HLS (Recomendado para navegadores)

### URLs de acesso:
```
Stream 1: http://192.168.1.187:8888/live/stream1/index.m3u8
Stream 2: http://192.168.1.187:8888/live/stream2/index.m3u8
```

### Como usar:

#### No navegador (Safari, Edge):
Abra diretamente a URL acima no navegador (Safari e Edge têm suporte nativo)

#### No navegador (Chrome, Firefox) - use um player:

**Opção 1: HLS.js Player (HTML simples)**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Câmeras ao Vivo</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
</head>
<body>
    <h1>Stream 1</h1>
    <video id="video1" controls width="640"></video>
    
    <h1>Stream 2</h1>  
    <video id="video2" controls width="640"></video>
    
    <script>
        // Stream 1
        var video1 = document.getElementById('video1');
        if (Hls.isSupported()) {
            var hls1 = new Hls();
            hls1.loadSource('http://192.168.1.187:8888/live/stream1/index.m3u8');
            hls1.attachMedia(video1);
        }
        
        // Stream 2
        var video2 = document.getElementById('video2');
        if (Hls.isSupported()) {
            var hls2 = new Hls();
            hls2.loadSource('http://192.168.1.187:8888/live/stream2/index.m3u8');
            hls2.attachMedia(video2);
        }
    </script>
</body>
</html>
```

**Opção 2: VLC Media Player**
1. Abrir VLC
2. Media → Open Network Stream
3. Colar URL: `http://192.168.1.187:8888/live/stream1/index.m3u8`

---

## 🎬 2. RTSP (Melhor qualidade/latência)

### URLs de acesso:
```
Stream 1: rtsp://192.168.1.187:8554/live/stream1
Stream 2: rtsp://192.168.1.187:8554/live/stream2
```

### Como usar:

#### VLC:
1. Media → Open Network Stream
2. URL: `rtsp://192.168.1.187:8554/live/stream1`

#### ffplay (linha de comando):
```bash
ffplay rtsp://192.168.1.187:8554/live/stream1
```

#### Aplicativos móveis:
- **Android**: VLC for Android, RTSP Player
- **iOS**: VLC, RTSP Player

---

## 📡 3. RTMP (Para streaming software)

### URLs de acesso:
```
Stream 1: rtmp://192.168.1.187:1935/live/stream1
Stream 2: rtmp://192.168.1.187:1935/live/stream2
```

### Como usar:

#### VLC:
URL: `rtmp://192.168.1.187:1935/live/stream1`

#### OBS Studio (para restream):
- Source → Media Source
- Uncheck "Local File"
- Input: `rtmp://192.168.1.187:1935/live/stream1`

---

## ⚠️ Solução de Problemas

### Problema: 404 Not Found no HLS

**Causa:** O FFmpeg está configurado para ignorar falhas de RTMP e não está conectado ao MediaMTX.

**Solução:** Execute o script de reinício:
```bash
cd /home/pi/app
./restart_rtmp_streams.sh
```

### Verificar se streams estão ativos:

```bash
# Verificar conexões RTMP
netstat -tn | grep :1935

# Ver logs do MediaMTX
sudo journalctl -u mediamtx -f

# Verificar se HLS está sendo gerado
ls -lh /tmp/live_stream1_*
```

### Códigos de status:

**✅ Stream ativo:**
```
[RTMP] [conn ::1:12345] is publishing to path 'live/stream1'
```

**❌ Stream inativo:**
```
[HLS] destroyed: no one is publishing to path 'live/stream1'
```

---

## 🔧 Manutenção

### Reiniciar streaming RTMP:
```bash
sudo systemctl restart better_seconds_record.service
```

### Verificar status:
```bash
./check_streaming.sh
```

### Testar acesso local:
```bash
# HLS
curl -I http://localhost:8888/live/stream1/index.m3u8

# Listar streams disponíveis
curl http://localhost:9997/v3/paths/list | python3 -m json.tool
```

---

## 📱 Exemplos de Código

### Python (OpenCV):
```python
import cv2

# RTSP
cap = cv2.VideoCapture('rtsp://192.168.1.187:8554/live/stream1')

while True:
    ret, frame = cap.read()
    if ret:
        cv2.imshow('Stream 1', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

### JavaScript (Web):
```javascript
// Usando HLS.js
const video = document.getElementById('video');
if (Hls.isSupported()) {
    const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 90
    });
    hls.loadSource('http://192.168.1.187:8888/live/stream1/index.m3u8');
    hls.attachMedia(video);
    hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play();
    });
}
```

### Android (Kotlin):
```kotlin
// Usando ExoPlayer
val player = ExoPlayer.Builder(context).build()
val mediaItem = MediaItem.fromUri("rtsp://192.168.1.187:8554/live/stream1")
player.setMediaItem(mediaItem)
player.prepare()
player.play()
```

---

## 🌐 Acessar de Fora da Rede Local

Para acessar de fora da sua rede, você precisa:

1. **Port Forwarding no roteador:**
   - Porta 8888 → 192.168.1.187:8888 (HLS)
   - Porta 8554 → 192.168.1.187:8554 (RTSP)
   - Porta 1935 → 192.168.1.187:1935 (RTMP)

2. **Usar IP público ou DDNS:**
   - Descubra seu IP: `curl ifconfig.me`
   - Configure DDNS (DuckDNS, No-IP, etc.)

3. **URLs externas:**
   ```
   http://SEU_IP_PUBLICO:8888/live/stream1/index.m3u8
   rtsp://SEU_IP_PUBLICO:8554/live/stream1
   ```

4. **Segurança (Recomendado):**
   - Use VPN (WireGuard, OpenVPN)
   - Configure autenticação no MediaMTX
   - Use HTTPS/TLS

---

## 📊 Comparação de Protocolos

| Protocolo | Latência | Qualidade | Compatibilidade | Firewall |
|-----------|----------|-----------|-----------------|----------|
| **HLS**   | Alta (~6-30s) | Média | Navegadores ✅ | Fácil |
| **RTSP**  | Baixa (~1-3s) | Alta | Apps específicos | Difícil |
| **RTMP**  | Média (~3-6s) | Alta | Software streaming | Média |

**Recomendação:**
- **Navegador web:** HLS
- **App móvel/Desktop:** RTSP
- **OBS/Streaming:** RTMP

---

## 💡 Dicas

1. **Baixa latência:** Use RTSP
2. **Máxima compatibilidade:** Use HLS
3. **Múltiplos viewers:** HLS escala melhor
4. **Rede local:** Qualquer protocolo funciona
5. **Internet:** HLS é mais confiável atravessando firewalls

---

## 🆘 Suporte

Se as câmeras não aparecerem:

1. Verifique se o MediaMTX está rodando: `ps aux | grep mediamtx`
2. Verifique se FFmpeg está enviando: `./check_streaming.sh`
3. Reinicie os serviços: `./restart_rtmp_streams.sh`
4. Veja logs: `sudo journalctl -u mediamtx -f`
