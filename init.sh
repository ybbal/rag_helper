#!/bin/bash

VENV_DIR="venv"
PYTHON_PATH="python"  # По умолчанию

# Парсинг аргументов
while getopts ":p:" opt; do
  case $opt in
    p) PYTHON_PATH="$OPTARG" ;;
    \?) echo "Неверный аргумент: -$OPTARG" >&2; exit 1 ;;
    :) echo "Аргумент -$OPTARG требует путь к Python." >&2; exit 1 ;;
  esac
done

# Проверка Python
if ! command -v "$PYTHON_PATH" &> /dev/null; then
  echo "Ошибка: Python не найден по пути '$PYTHON_PATH'"
  exit 1
fi

# Удаление старого venv (если есть)
if [ -d "$VENV_DIR" ]; then
  echo "Удаление старого venv..."
  rm -rf "$VENV_DIR" || { echo "Ошибка удаления venv. Закройте все IDE/терминалы."; exit 1; }
fi

# Создание venv
echo "Создание venv с Python ($PYTHON_PATH)..."
"$PYTHON_PATH" -m venv "$VENV_DIR" || { echo "Ошибка создания venv. Проверьте права доступа."; exit 1; }

# Активация и установка зависимостей
source "$VENV_DIR/bin/activate"      # Linux/Mac

# Обновление pip (с обработкой ошибок)
pip install --upgrade pip || { echo "Ошибка обновления pip. Попробуйте запустить от администратора."; exit 1; }

if [ -f "requirements.txt" ]; then
  echo "Установка зависимостей..."
  pip install -r requirements.txt || { echo "Ошибка установки зависимостей. Проверьте файл requirements.txt."; exit 1; }
else
  echo "Файл requirements.txt не найден. Пропускаем установку."
fi

echo "Готово! Виртуальное окружение настроено."