#!/bin/sh
# Проверка приоритета: командная строка важнее конфигурационного файла.
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

run "Оба значения из файла" --config examples/config.ini
run "--vfs из командной строки, скрипт из файла" \
    --config examples/config.ini --vfs vfs/cli.csv
run "--script из командной строки, VFS из файла" \
    --config examples/config.ini --script examples/start_short.txt
run "В файле только VFS, скрипт из командной строки" \
    --config examples/config_vfs_only.ini --script examples/start.txt
