#!/bin/bash

VENV_DIR="venv"
PYTHON_PATH="python"  # По умолчанию (используется из venv)

# Активация venv
echo "Активация venv..."
source "$VENV_DIR/bin/activate"      # Linux/Mac

export PYTHONPATH="$PYTHONPATH:src"

# Запуск бота
echo "Запуск бота..."
"$PYTHON_PATH" main.py