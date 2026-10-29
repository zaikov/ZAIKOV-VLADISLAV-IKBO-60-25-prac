#!/bin/sh
# Запуск эмулятора: ./run.sh [--vfs PATH] [--script PATH] [--config PATH]
# Запуск тестов:    ./run.sh test
# Абсолютный путь к папке проекта (там, где лежит этот скрипт).
ROOT="$(cd "$(dirname "$0")" && pwd)"
# Пакет shell_emulator лежит в src, сообщаем об этом Python.
# Текущий каталог не меняем, чтобы относительные пути в параметрах
# считались от того места, откуда запущен скрипт.
export PYTHONPATH="$ROOT/src"

if [ "$1" = "test" ]; then
    exec python3 -m unittest discover -s "$ROOT/tests" -v
fi
exec python3 -m shell_emulator "$@"
