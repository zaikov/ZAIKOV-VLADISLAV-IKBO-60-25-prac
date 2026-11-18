#!/bin/sh
# Демонстрация получения прямых зависимостей из репозитория NuGet
# и обработки ошибок обращения к репозиторию. Нужен доступ в интернет.
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
run "Справка по параметрам командной строки" --help

# Описание каждого примера — первая строка файла без «# ».
for file in examples/packages/*.toml; do
    run "$(head -n 1 "$file" | sed 's/^# //')" -c "$file"
done
for file in examples/repo_errors/*.toml; do
    run "$(head -n 1 "$file" | sed 's/^# //')" -c "$file"
done

run "Тестовый режим (поддерживается с этапа 3)" -c examples/test_mode.toml
