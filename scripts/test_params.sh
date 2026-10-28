#!/bin/sh
# Проверка каждого параметра командной строки по отдельности и вместе.
# Чтобы перейти к следующему запуску, введите exit или закройте окно.
cd "$(dirname "$0")/.." || exit 1

run() {
    echo
    echo "=== $1"
    shift
    echo "\$ ./run.sh $*"
    ./run.sh "$@"
    echo "код возврата: $?"
}

run "Без параметров"
run "Только --vfs" --vfs vfs/default.csv
run "Только --script" --script examples/start.txt
run "Только --config" --config examples/config.ini
run "Все три параметра" --vfs vfs/cli.csv \
    --script examples/start_short.txt --config examples/config.ini
run "exit из стартового скрипта (ожидается код 5)" \
    --script examples/start_exit.txt
