# 📹 Como Visualizar as Câmeras

## 1️⃣ VLC (Melhor opção - Baixa latência)

### No Windows/Mac/Linux:
1. Abra o VLC
2. Menu: **Media** → **Open Network Stream** (Ctrl+N)
3. Cole uma das URLs:
   ```
   rtsp://192.168.1.187:8554/live/stream1
   rtsp://192.168.1.187:8554/live/stream2
   ```
4. Clique em **Play**

### No Android:
1. Baixe o app **VLC for Android**
2. Menu → **New Stream**
3. Cole: `rtsp://192.168.1.187:8554/live/stream1`

### No iPhone/iPad:
1. Baixe o app **VLC for Mobile**
2. Mesmos passos do Android

---

## 2️⃣ Navegador Web (HLS - Maior compatibilidade)

Abra no navegador:
```
http://192.168.1.187:8888/live/stream1/index.m3u8
http://192.168.1.187:8888/live/stream2/index.m3u8
```

Ou use o player HTML:
```
http://192.168.1.187:5000/viewer.html
```

---

## 3️⃣ WebRTC (Menor latência no navegador)

Acesse direto no Chrome/Firefox:
```
http://192.168.1.187:8889/live/stream1/
http://192.168.1.187:8889/live/stream2/
```

---

## 🔧 Troubleshooting

### VLC não conecta:
```bash
# Verifique se o MediaMTX está rodando
sudo systemctl status mediamtx

# Verifique se os streams estão publicando
sudo journalctl -u mediamtx -n 20 | grep publishing
```

### HLS retorna 404:
```bash
# Verifique se há conexões RTMP ativas
ss -tn | grep :1935 | grep ESTAB

# Reinicie os serviços se necessário
sudo systemctl restart mediamtx
sudo systemctl restart better_seconds_record.service
```

### Verificar saúde do sistema:
```bash
curl http://localhost:5000/health | python3 -m json.tool
```

---

## 📊 Latências Típicas

| Protocolo | Latência | Melhor Para |
|-----------|----------|-------------|
| **RTSP** | ~2-3s | VLC, apps mobile |
| **WebRTC** | <1s | Browsers modernos |
| **HLS** | ~10-15s | Compatibilidade ampla |

---

## 🌐 Acesso Externo (Internet)

Para acessar de fora da rede local, configure port forwarding no roteador:

- **RTSP**: Porta 8554 → 192.168.1.187:8554
- **HLS**: Porta 8888 → 192.168.1.187:8888  
- **WebRTC**: Porta 8889 → 192.168.1.187:8889

**Atenção:** Use senha/autenticação para acesso externo!
