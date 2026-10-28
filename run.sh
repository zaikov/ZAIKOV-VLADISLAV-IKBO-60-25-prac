#!/bin/sh
# Запуск эмулятора: ./run.sh [--vfs PATH] [--script PATH] [--config PATH]
# Запуск тестов:    ./run.sh test
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT/src"

if [ "$1" = "test" ]; then
    exec python3 -m unittest discover -s "$ROOT/tests" -v
fi
exec python3 -m shell_emulator "$@"
