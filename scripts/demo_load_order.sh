#!/bin/sh
# Демонстрация режима вывода порядка загрузки зависимостей
# (load_order = true). Для тестовых репозиториев сначала выводится
# файл описания графа, затем порядок загрузки. Примеры nuget_*
# обращаются к реальному репозиторию NuGet и требуют интернета.
cd "$(dirname "$0")/.." || exit 1

for config in examples/load_order/*.toml; do
    echo
    echo "=== $(head -n 1 "$config" | sed 's/^# //')"
    if grep -q '^test_mode = true' "$config"; then
        # Путь к файлу репозитория берём из строки repository = "...".
        repo="$(sed -n 's/^repository = "\(.*\)"$/\1/p' "$config")"
        echo "--- $repo:"
        grep -v '^#' "$repo"
    fi
    echo "--- \$ ./run.sh -c $config"
    ./run.sh -c "$config"
    echo "код возврата: $?"
done
