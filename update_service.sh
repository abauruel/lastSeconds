#!/bin/bash
# Script para atualizar o serviço better_seconds_record

echo "======================================"
echo "Atualizando serviço Better Seconds Record"
echo "======================================"

# Backup do serviço atual
echo "📋 Criando backup do serviço atual..."
sudo cp /etc/systemd/system/better_seconds_record.service /etc/systemd/system/better_seconds_record.service.backup

# Criar novo arquivo de serviço
echo "✏️  Criando novo arquivo de serviço..."
sudo tee /etc/systemd/system/better_seconds_record.service > /dev/null <<EOF
[Unit]
Description=Better Seconds Record application
After=network.target song.target

[Service]
StandardOutput=journal
StandardError=journal
WorkingDirectory=/home/pi/app
ExecStart=/bin/bash -c 'cd /home/pi/app && source .venv/bin/activate && gunicorn -c gunicorn_config.py capture3:app'
Restart=always
User=root
Environment="XDG_RUNTIME_DIR=/run/user/1000"
Environment="PULSE_SERVER=unix:/run/user/1000/pulse/native"
Environment="SERVER_SOFTWARE=gunicorn"

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo "🔄 Recarregando systemd..."
sudo systemctl daemon-reload

echo ""
echo "✅ Serviço atualizado com sucesso!"
echo ""
echo "Para aplicar as mudanças, execute:"
echo "  sudo systemctl restart better_seconds_record.service"
echo ""
echo "Para monitorar:"
echo "  journalctl -u better_seconds_record.service -f"
echo ""
echo "Diferenças principais:"
echo "  - Agora usa gunicorn_config.py"
echo "  - Reduzido de 4 para 2 workers"
echo "  - FFmpeg inicializado apenas uma vez (preload)"
echo "======================================"
