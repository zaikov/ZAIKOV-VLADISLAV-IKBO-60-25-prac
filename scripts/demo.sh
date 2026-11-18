#!/bin/sh
# Демонстрация построения графа зависимостей реальных пакетов NuGet
# и обработки ошибок обращения к репозиторию. Нужен доступ в интернет.
# Большие графы загружаются долго: каждый пакет — отдельные HTTP-запросы,
# ход загрузки выводится строками «Загрузка ...».
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
