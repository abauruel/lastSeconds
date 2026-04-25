#!/bin/bash
# Script bash wrapper para processar timestamps
# Facilita a execução sem precisar lembrar da sintaxe Python

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/process_timestamps_standalone.py"

# Verifica se o ambiente virtual existe
if [ -d "$SCRIPT_DIR/.venv" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# Executa o script Python com todos os argumentos passados
python3 "$PYTHON_SCRIPT" "$@"
