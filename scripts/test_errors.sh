#!/bin/sh
# Проверка обработки ошибок параметров, конфигурации и стартового скрипта.
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

run "Справка по параметрам (окно не открывается)" --help
run "Неизвестный параметр (окно не открывается, код 2)" --unknown
run "Параметр без значения (окно не открывается, код 2)" --vfs
run "Конфигурационный файл не найден" --config examples/missing.ini
run "Неверный формат INI" --config examples/config_broken.ini
run "Нет секции [emulator]" --config examples/config_no_section.ini
run "Стартовый скрипт не найден" --script examples/missing.txt
run "Ошибка в стартовом скрипте: остановка на строке 4" \
    --script examples/start_error.txt
