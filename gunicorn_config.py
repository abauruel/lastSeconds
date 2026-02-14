"""
Configuração do Gunicorn para Better Seconds Record

Usa preload_app para garantir que o FFMpegManager seja inicializado
apenas uma vez no master process, não em cada worker.
"""

import os
import multiprocessing

# Bind
bind = "0.0.0.0:5000"

# Workers (reduzido para 2 para evitar overhead desnecessário)
workers = 2

# Preload app - carrega antes de fazer fork dos workers
# Isso garante que FFMpegManager seja inicializado apenas uma vez
preload_app = True

# Timeout (aumentado para 300s = 5min devido a operações de vídeo lentas no pendrive)
timeout = 300

# Logging (movido para disco interno para evitar deadlock de I/O no pendrive)
accesslog = "/home/pi/app/logs/gunicorn_access.log"
errorlog = "/home/pi/app/logs/gunicorn_error.log"
loglevel = "info"

# Worker class
worker_class = "sync"

# Graceful timeout
graceful_timeout = 30

def on_starting(server):
    """Chamado antes do master process começar"""
    print("🚀 Gunicorn master process iniciando...")

def when_ready(server):
    """Chamado quando o servidor está pronto para aceitar conexões"""
    print("✅ Gunicorn pronto para aceitar conexões")

def on_exit(server):
    """Chamado quando o master process está saindo"""
    print("🛑 Gunicorn master process encerrando...")
