"""
Configuração do Gunicorn para Better Seconds Record - HTTPS

Configuração para HTTPS usando certificados SSL.
Pode rodar em paralelo com a versão HTTP ou substituí-la.
"""

import os
import multiprocessing

# Bind HTTPS na porta 5443
bind = "0.0.0.0:5443"

# SSL
certfile = "/home/pi/app/ssl/server.crt"
keyfile = "/home/pi/app/ssl/server.key"

# Workers (reduzido para 2 para evitar overhead desnecessário)
workers = 2

# Preload app - carrega antes de fazer fork dos workers
preload_app = True

# Timeout (aumentado para 300s = 5min devido a operações de vídeo lentas no pendrive)
timeout = 300

# Logging
accesslog = "/home/pi/app/logs/gunicorn_https_access.log"
errorlog = "/home/pi/app/logs/gunicorn_https_error.log"
loglevel = "info"

# Worker class
worker_class = "sync"

# Graceful timeout
graceful_timeout = 30

def on_starting(server):
    """Chamado antes do master process começar"""
    print("🔐 Gunicorn HTTPS master process iniciando na porta 5443...")

def when_ready(server):
    """Chamado quando o servidor está pronto para aceitar conexões"""
    print("✅ Gunicorn HTTPS pronto para aceitar conexões em https://0.0.0.0:5443")

def on_exit(server):
    """Chamado quando o master process está saindo"""
    print("🛑 Gunicorn HTTPS master process encerrando...")
