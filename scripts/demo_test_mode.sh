#!/bin/sh
# Демонстрация тестового режима: граф строится по файлу описания
# репозитория, где пакеты называются большими латинскими буквами.
# Для каждого случая сначала выводится файл репозитория, затем граф.
cd "$(dirname "$0")/.." || exit 1

run() {
    config="$1"
    # Путь к файлу репозитория берём из строки repository = "...".
    repo="$(sed -n 's/^repository = "\(.*\)"$/\1/p' "$config")"
    echo
    echo "=== $(head -n 1 "$config" | sed 's/^# //')"
    echo "--- $repo:"
    grep -v '^#' "$repo"
    echo "--- \$ ./run.sh -c $config"
    ./run.sh -c "$config"
    echo "код возврата: $?"
}

for config in examples/test_mode/*.toml; do
    run "$config"
done
for config in examples/test_mode/errors/*.toml; do
    run "$config"
done
