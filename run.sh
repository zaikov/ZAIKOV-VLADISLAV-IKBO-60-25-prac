#!/bin/sh
# Запуск приложения: ./run.sh [-c CONFIG]
# Запуск тестов:     ./run.sh test
# Абсолютный путь к папке проекта (там, где лежит этот скрипт).
ROOT="$(cd "$(dirname "$0")" && pwd)"
# Пакет depgraph лежит в src, сообщаем об этом Python.
export PYTHONPATH="$ROOT/src"

if [ "$1" = "test" ]; then
    exec python3 -m unittest discover -s "$ROOT/tests" -v
fi
exec python3 -m depgraph "$@"
