#!/bin/sh
# Демонстрация обработки ошибок для всех параметров конфигурации.
# Каждый файл в examples/errors/ содержит ошибку определённого вида,
# её описание записано в первой строке файла.
cd "$(dirname "$0")/.." || exit 1

run() {
    echo
    echo "=== $1"
    shift
    echo "\$ ./run.sh $*"
    ./run.sh "$@"
    echo "код возврата: $?"
}

run "Файл конфигурации не найден" -c examples/no_such_config.toml
run "Вместо файла указан каталог" -c examples
run "Неизвестный аргумент командной строки" --unknown

for file in examples/errors/*.toml; do
    # Описание ошибки — первая строка файла без «# Ошибка: ».
    run "$(head -n 1 "$file" | sed 's/^# Ошибка: //')" -c "$file"
done
