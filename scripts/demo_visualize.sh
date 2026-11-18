#!/bin/sh
# Демонстрация визуализации: описание графа на языке Graphviz, SVG-файл
# и ASCII-дерево для трёх реальных пакетов NuGet и тестового графа
# с циклами. Изображения сохраняются в docs/images/.
# Нужны Graphviz (команда dot) и доступ в интернет.
cd "$(dirname "$0")/.." || exit 1

for config in examples/visualize/*.toml; do
    echo
    echo "=== $(head -n 1 "$config" | sed 's/^# //')"
    echo "--- \$ ./run.sh -c $config"
    ./run.sh -c "$config"
    echo "код возврата: $?"
done
