# Better Seconds Record - Guia de Configuração SSL/HTTPS

## 📋 Visão Geral

O servidor Better Seconds Record agora suporta HTTP e HTTPS. Esta documentação explica como configurar e usar ambos os protocolos.

## 🔐 Configuração SSL/HTTPS

### Arquivos Criados

1. **Scripts de Configuração:**
   - `scripts/generate_ssl_cert.sh` - Gera certificados SSL auto-assinados
   - `scripts/start_https.sh` - Inicia servidor HTTPS (porta 5443)
   - `scripts/start_dual.sh` - Inicia HTTP e HTTPS simultâneos

2. **Configurações Gunicorn:**
   - `gunicorn_config.py` - HTTP na porta 5000
   - `gunicorn_config_https.py` - HTTPS na porta 5443

3. **Serviços Systemd:**
   - `capture3_http.service` - Serviço HTTP
   - `capture3_https.service` - Serviço HTTPS

## 🚀 Uso Rápido

### Opção 1: Apenas HTTP (porta 5000)
```bash
cd /home/pi/app
bash scripts/start_app.sh
```

### Opção 2: Apenas HTTPS (porta 5443)
```bash
cd /home/pi/app
bash scripts/start_https.sh
```

### Opção 3: HTTP + HTTPS Simultâneos
```bash
cd /home/pi/app
bash scripts/start_dual.sh
```

## 🔧 Instalação como Serviço

### Habilitar HTTP Service (porta 5000)
```bash
sudo cp /home/pi/app/capture3_http.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable capture3_http.service
sudo systemctl start capture3_http.service
```

### Habilitar HTTPS Service (porta 5443)
```bash
sudo cp /home/pi/app/capture3_https.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable capture3_https.service
sudo systemctl start capture3_https.service
```

### Verificar Status
```bash
# HTTP
sudo systemctl status capture3_http

# HTTPS
sudo systemctl status capture3_https
```

## 📝 Gerando Certificados SSL

Os certificados SSL são gerados automaticamente na primeira execução. Para regerar manualmente:

```bash
bash /home/pi/app/scripts/generate_ssl_cert.sh
```

**Certificados criados:**
- `/home/pi/app/ssl/server.crt` - Certificado público
- `/home/pi/app/ssl/server.key` - Chave privada

**Características:**
- Válido por 365 dias
- Suporta múltiplos domínios/IPs (SANs):
  - raspberrypi.local
  - localhost
  - 192.168.1.187
  - 10.42.0.1
  - 192.168.0.1
  - 127.0.0.1

## 🌐 Acessando o Servidor

### HTTP (porta 5000)
```
http://192.168.1.187:5000/health
http://10.42.0.1:5000/health
http://localhost:5000/health
```

### HTTPS (porta 5443)
```
https://192.168.1.187:5443/health
https://10.42.0.1:5443/health
https://localhost:5443/health
```

## ⚠️ Avisos de Segurança

### Certificados Auto-Assinados

Os certificados SSL gerados são **auto-assinados** e não são confiáveis por autoridades certificadoras. Isso significa:

1. **Navegadores mostrarão aviso de segurança**
   - Chrome/Edge: "Your connection is not private"
   - Firefox: "Warning: Potential Security Risk Ahead"
   - Safari: "This Connection Is Not Private"

2. **Como prosseguir:**
   - Chrome/Edge: Clique em "Advanced" → "Proceed to ... (unsafe)"
   - Firefox: Clique em "Advanced" → "Accept the Risk and Continue"
   - Safari: Clique em "Show Details" → "visit this website"

3. **Requisições via curl/API:**
```bash
# Ignora validação de certificado (desenvolvimento)
curl -k https://192.168.1.187:5443/health

# Python requests
import requests
requests.get('https://192.168.1.187:5443/health', verify=False)
```

### Para Produção Real

Para ambiente de produção público, use certificados válidos:

1. **Let's Encrypt (gratuito):**
```bash
sudo apt install certbot
sudo certbot certonly --standalone -d seudominio.com
```

2. **Atualize o gunicorn_config_https.py:**
```python
certfile = "/etc/letsencrypt/live/seudominio.com/fullchain.pem"
keyfile = "/etc/letsencrypt/live/seudominio.com/privkey.pem"
```

## 🔍 Troubleshooting

### Porta já em uso
```bash
# Verificar processos nas portas
sudo netstat -tlnp | grep -E '5000|5443'

# Parar processos
pkill -f 'gunicorn.*capture3:app'
```

### Certificados não gerados
```bash
# Verificar se openssl está instalado
which openssl

# Gerar manualmente
bash /home/pi/app/scripts/generate_ssl_cert.sh
```

### Erro de permissão SSL
```bash
# Ajustar permissões
chmod 644 /home/pi/app/ssl/server.crt
chmod 600 /home/pi/app/ssl/server.key
chown pi:pi /home/pi/app/ssl/*
```

## 📊 Logs

### HTTP Logs
```bash
tail -f /home/pi/app/logs/gunicorn_access.log
tail -f /home/pi/app/logs/gunicorn_error.log
```

### HTTPS Logs
```bash
tail -f /home/pi/app/logs/gunicorn_https_access.log
tail -f /home/pi/app/logs/gunicorn_https_error.log
```

## 🔄 Migração

Se você já tem o serviço HTTP rodando e quer adicionar HTTPS:

1. **Manter HTTP e adicionar HTTPS:**
```bash
# HTTP continua rodando
sudo systemctl status capture3_http

# Adicionar HTTPS
sudo cp /home/pi/app/capture3_https.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable capture3_https.service
sudo systemctl start capture3_https.service
```

2. **Substituir HTTP por HTTPS:**
```bash
# Parar HTTP
sudo systemctl stop capture3_http
sudo systemctl disable capture3_http

# Iniciar HTTPS
sudo systemctl enable capture3_https.service
sudo systemctl start capture3_https.service
```

## 📱 Testando

```bash
# HTTP
curl http://localhost:5000/health

# HTTPS (ignora certificado auto-assinado)
curl -k https://localhost:5443/health

# Verificar certificado
openssl s_client -connect localhost:5443 -showcerts
```

## 🎯 Recomendações

1. **Desenvolvimento/Uso Local:** Use modo dual (HTTP + HTTPS) para compatibilidade
2. **Rede Interna:** HTTPS com certificados auto-assinados é suficiente
3. **Internet Pública:** Use Let's Encrypt ou certificados válidos
4. **Performance:** HTTP tem ~10% menos overhead que HTTPS
5. **Segurança:** HTTPS protege dados em trânsito (recomendado)
