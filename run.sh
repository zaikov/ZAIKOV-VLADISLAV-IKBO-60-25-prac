#!/bin/sh
# Запуск эмулятора: ./run.sh
# Запуск тестов:    ./run.sh test
cd "$(dirname "$0")" || exit 1
export PYTHONPATH="src"

if [ "$1" = "test" ]; then
    exec python3 -m unittest discover -s tests -v
fi
exec python3 -m shell_emulator "$@"
