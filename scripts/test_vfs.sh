#!/bin/sh
# Проверка загрузки VFS разных видов, ошибок загрузки и команды vfs-init.
# Чтобы перейти к следующему запуску, введите exit или закройте окно.
cd "$(dirname "$0")/.." || exit 1

# vfs-init очищает CSV-файл VFS, поэтому для этих проверок работаем
# с копиями во временном каталоге — файлы в репозитории не меняются.
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cp vfs/deep.csv "$TMP/deep.csv"
cp vfs/several.csv "$TMP/several.csv"

run() {
    echo
    echo "=== $1"
    shift
    echo "\$ ./run.sh $*"
    ./run.sh "$@"
    echo "код возврата: $?"
}

# --- Корректные VFS (в окне видно число каталогов, файлов и глубину)
run "Минимальная VFS: один файл" --vfs vfs/minimal.csv
run "Несколько файлов, двоичный файл в base64" --vfs vfs/several.csv
run "Вложенность не менее 3 уровней" --vfs vfs/deep.csv
run "VFS из конфигурационного файла" --config examples/config.ini

# --- Ошибки загрузки (эмулятор работает с VFS по умолчанию)
run "Файл VFS не найден" --vfs vfs/missing.csv
for file in vfs/invalid/*.csv; do
    run "Неверный формат: $file" --vfs "$file"
done

# --- vfs-init очищает физический файл VFS
run "vfs-init (введите vfs-init, затем exit)" --vfs "$TMP/several.csv"
echo "Содержимое $TMP/several.csv после запуска:"
cat "$TMP/several.csv"

# --- Стартовый скрипт со всеми командами этапов 1–3
run "Все команды этапов 1–3, остановка на ошибке" \
    --vfs "$TMP/deep.csv" --script examples/start_all.txt
echo "Содержимое $TMP/deep.csv после запуска:"
cat "$TMP/deep.csv"
