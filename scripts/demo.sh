#!/bin/sh
# Демонстрация запуска с корректными конфигурационными файлами.
cd "$(dirname "$0")/.." || exit 1

run() {
    echo
    echo "=== $1"
    shift
    echo "\$ ./run.sh $*"
    ./run.sh "$@"
    echo "код возврата: $?"
}

run "Конфигурация по умолчанию (config.toml)"
run "Тестовый режим" -c examples/test_mode.toml
run "Справка по параметрам командной строки" --help
