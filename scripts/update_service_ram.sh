#!/bin/bash
# Script para atualizar o serviço systemd com suporte a gravação em RAM

echo "Atualizando serviço systemd..."

sudo tee /etc/systemd/system/better_seconds_record.service > /dev/null <<'EOF'
[Unit]
Description=Better Seconds Record application
After=network.target sound.target

[Service]
StandardOutput=journal
StandardError=journal
WorkingDirectory=/home/pi/app

# Carrega variáveis de ambiente se existir .env.ram
EnvironmentFile=-/home/pi/app/.env.ram

Environment="XDG_RUNTIME_DIR=/run/user/1000"
Environment="PULSE_SERVER=unix:/run/user/1000/pulse/native"
Environment="SERVER_SOFTWARE=gunicorn"

ExecStart=/bin/bash -c 'cd /home/pi/app && source .venv/bin/activate && gunicorn -c gunicorn_config.py capture3:app'
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
echo "✓ Serviço atualizado"
