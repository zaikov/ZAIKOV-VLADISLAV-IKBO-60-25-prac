"""Виртуальная файловая система (VFS), которая целиком хранится в памяти.

Источник VFS — CSV-файл со строкой заголовка ``path,type,content``:

- ``path`` — абсолютный путь элемента, например ``/home/user/a.txt``;
- ``type`` — ``dir`` для каталога или ``file`` для файла;
- ``content`` — содержимое файла в base64 (у каталогов пустое).

Вложенность задаётся самим путём: элемент ``/home/user`` лежит
в каталоге ``/home``. Корневой каталог ``/`` есть всегда и в файле
не указывается. Порядок строк в файле не важен.
"""

import base64
import csv

CSV_HEADER = ["path", "type", "content"]
TYPE_DIR = "dir"
TYPE_FILE = "file"
SEPARATOR = "/"
# Имена, которые нельзя использовать в пути элемента VFS.
FORBIDDEN_NAMES = ("", ".", "..")


class VfsError(Exception):
    """Ошибка загрузки или сохранения VFS."""


class VfsDir:
    """Каталог VFS: хранит вложенные элементы в словаре по именам."""

    def __init__(self, name):
        """Создать пустой каталог с именем ``name``."""
        self.name = name
        self.children = {}


class VfsFile:
    """Файл VFS: хранит содержимое в виде байтов."""

    def __init__(self, name, data):
        """Создать файл с именем ``name`` и содержимым ``data``."""
        self.name = name
        self.data = data


class Vfs:
    """Виртуальная файловая система с корневым каталогом ``root``."""

    def __init__(self):
        """Создать VFS, состоящую только из пустого корня."""
        self.root = VfsDir("")

    def stats(self):
        """Посчитать элементы VFS (корень не учитывается).

        :return: кортеж ``(каталогов, файлов, глубина вложенности)``.
        """
        return _count(self.root, 0)


def default_vfs():
    """Вернуть VFS по умолчанию — пустой корневой каталог."""
    return Vfs()


def read_vfs(path):
    """Загрузить VFS из CSV-файла в память.

    :param path: путь к CSV-файлу.
    :return: объект :class:`Vfs`.
    :raises VfsError: если файл не найден или имеет неверный формат.
    """
    try:
        rows = _read_rows(path)
        return _build(rows)
    except VfsError as error:
        # Добавляем к сообщению путь к файлу, чтобы было понятно,
        # какой именно файл не удалось загрузить.
        raise VfsError(f"vfs: {path}: {error}") from None


def write_vfs(vfs, path):
    """Сохранить VFS в CSV-файл (используется командой vfs-init).

    :param vfs: объект :class:`Vfs`.
    :param path: путь к CSV-файлу; файл перезаписывается.
    :raises VfsError: если файл не удаётся записать.
    """
    try:
        with open(path, "w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file, lineterminator="\n")
            writer.writerow(CSV_HEADER)
            writer.writerows(_to_rows(vfs.root, ""))
    except OSError as error:
        raise VfsError(f"vfs: {path}: {error.strerror}") from None


def _count(directory, depth):
    """Рекурсивно посчитать каталоги, файлы и глубину внутри каталога."""
    dirs = files = 0
    max_depth = depth
    for child in directory.children.values():
        if isinstance(child, VfsDir):
            sub_dirs, sub_files, sub_depth = _count(child, depth + 1)
            dirs += 1 + sub_dirs
            files += sub_files
            max_depth = max(max_depth, sub_depth)
        else:
            files += 1
            max_depth = max(max_depth, depth + 1)
    return dirs, files, max_depth


def _read_rows(path):
    """Прочитать и проверить строки CSV-файла.

    :raises VfsError: при ошибке чтения или формата.
    """
    try:
        # newline="" требуется модулю csv для правильной обработки
        # переводов строк внутри значений.
        with open(path, encoding="utf-8", newline="") as file:
            return _parse_rows(csv.reader(file))
    except FileNotFoundError:
        raise VfsError("file not found") from None
    except UnicodeDecodeError:
        raise VfsError("invalid encoding, UTF-8 expected") from None
    except OSError as error:
        raise VfsError(error.strerror) from None
    except csv.Error as error:
        raise VfsError(f"invalid CSV: {error}") from None


def _parse_rows(reader):
    """Проверить заголовок и разобрать все строки данных.

    :return: список кортежей ``(номер строки, части пути, тип, данные)``.
    """
    header = next(reader, None)
    if header != CSV_HEADER:
        expected = ",".join(CSV_HEADER)
        raise VfsError(f"invalid header, expected: {expected}")
    rows = []
    for row in reader:
        # Полностью пустые строки (например, в конце файла) пропускаем.
        if row:
            rows.append(_parse_row(reader.line_num, row))
    return rows


def _parse_row(line, row):
    """Разобрать одну строку CSV: путь, тип и содержимое."""
    if len(row) != len(CSV_HEADER):
        raise VfsError(
            f"line {line}: expected {len(CSV_HEADER)} columns, "
            f"got {len(row)}"
        )
    path, kind, content = row
    parts = _split_path(line, path)
    if kind == TYPE_DIR:
        if content:
            raise VfsError(f"line {line}: directory {path} has content")
        return line, parts, kind, None
    if kind == TYPE_FILE:
        return line, parts, kind, _decode(line, content)
    raise VfsError(f"line {line}: unknown type '{kind}', expected dir/file")


def _split_path(line, path):
    """Разбить абсолютный путь на имена: ``/a/b`` -> ``['a', 'b']``."""
    if not path.startswith(SEPARATOR) or path == SEPARATOR:
        raise VfsError(f"line {line}: invalid path '{path}'")
    parts = path[1:].split(SEPARATOR)
    # Пустое имя появляется при «//» или «/» в конце пути.
    if any(part in FORBIDDEN_NAMES for part in parts):
        raise VfsError(f"line {line}: invalid path '{path}'")
    return parts


def _decode(line, content):
    """Декодировать содержимое файла из base64 в байты."""
    try:
        # validate=True запрещает посторонние символы, иначе b64decode
        # молча пропустил бы их и вернул искажённые данные.
        return base64.b64decode(content, validate=True)
    except ValueError:
        # binascii.Error — неверный base64, ValueError — символы вне
        # ASCII (например, кириллица) в строке base64.
        raise VfsError(f"line {line}: invalid base64 content") from None


def _build(rows):
    """Построить дерево VFS из разобранных строк CSV."""
    vfs = Vfs()
    # Сначала добавляем элементы с меньшей глубиной: так родительский
    # каталог всегда создаётся раньше вложенных в него элементов.
    for line, parts, kind, data in sorted(rows, key=lambda r: len(r[1])):
        parent = _find_parent(vfs, line, parts)
        name = parts[-1]
        if name in parent.children:
            path = SEPARATOR + SEPARATOR.join(parts)
            raise VfsError(f"line {line}: duplicate path {path}")
        if kind == TYPE_DIR:
            parent.children[name] = VfsDir(name)
        else:
            parent.children[name] = VfsFile(name, data)
    return vfs


def _find_parent(vfs, line, parts):
    """Найти каталог, в который нужно добавить элемент с путём ``parts``."""
    node = vfs.root
    for name in parts[:-1]:
        node = node.children.get(name)
        # Родитель должен существовать и быть именно каталогом.
        if not isinstance(node, VfsDir):
            parent = SEPARATOR + SEPARATOR.join(parts[:-1])
            raise VfsError(f"line {line}: parent directory {parent} not found")
    return node


def _to_rows(directory, prefix):
    """Обойти каталог и выдать строки CSV для всех вложенных элементов."""
    for child in directory.children.values():
        path = f"{prefix}{SEPARATOR}{child.name}"
        if isinstance(child, VfsDir):
            yield [path, TYPE_DIR, ""]
            yield from _to_rows(child, path)
        else:
            content = base64.b64encode(child.data).decode("ascii")
            yield [path, TYPE_FILE, content]
