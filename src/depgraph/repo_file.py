"""Тестовый репозиторий: граф пакетов, описанный в текстовом файле.

Используется в тестовом режиме (``test_mode = true``) вместо реального
репозитория NuGet. Пакеты называются большими латинскими буквами,
каждая строка описывает пакет и его прямые зависимости::

    # комментарий
    A: B C
    B: C
    C:

Каждый пакет описывается один раз; зависимость должна быть описана
в том же файле. Пустые строки и строки с ``#`` пропускаются.
"""

from depgraph.config import TEST_PACKAGE_PATTERN

COMMENT_PREFIX = "#"
SEPARATOR = ":"


class RepoFileError(Exception):
    """Ошибка чтения или содержимого файла тестового репозитория."""


def load_repo_file(path):
    """Прочитать файл тестового репозитория.

    :param path: путь к файлу.
    :return: словарь ``{пакет: [зависимости]}`` в порядке описания.
    :raises RepoFileError: если файл не читается или неверен.
    """
    try:
        with open(path, encoding="utf-8") as file:
            lines = file.read().splitlines()
    except FileNotFoundError:
        raise RepoFileError(f"{path}: файл не найден") from None
    except OSError as error:
        raise RepoFileError(f"{path}: {error.strerror}") from None
    except UnicodeDecodeError:
        raise RepoFileError(f"{path}: файл не в кодировке UTF-8") from None
    repo = parse_repo_file(lines, path)
    check_references(repo, path)
    return repo


def parse_repo_file(lines, path):
    """Разобрать строки файла в словарь ``{пакет: [зависимости]}``."""
    repo = {}
    for number, line in enumerate(lines, start=1):
        text = line.strip()
        if not text or text.startswith(COMMENT_PREFIX):
            continue
        name, dependencies = parse_line(text, f"{path}:{number}")
        if name in repo:
            raise RepoFileError(
                f"{path}:{number}: пакет {name} описан повторно"
            )
        repo[name] = dependencies
    return repo


def parse_line(text, where):
    """Разобрать строку вида ``A: B C``.

    Повторы в списке зависимостей одного пакета убираются.

    :param where: место в файле для сообщений об ошибках.
    :return: кортеж ``(пакет, [зависимости])``.
    """
    if SEPARATOR not in text:
        raise RepoFileError(
            f"{where}: ожидается строка вида 'A: B C', получено '{text}'"
        )
    name, _, rest = text.partition(SEPARATOR)
    name = name.strip()
    dependencies = rest.split()
    for item in [name, *dependencies]:
        if not TEST_PACKAGE_PATTERN.fullmatch(item):
            raise RepoFileError(
                f"{where}: имя пакета должно состоять из больших "
                f"латинских букв, получено '{item}'"
            )
    return name, list(dict.fromkeys(dependencies))


def check_references(repo, path):
    """Проверить, что все зависимости описаны в файле."""
    for name, dependencies in repo.items():
        for dependency in dependencies:
            if dependency not in repo:
                raise RepoFileError(
                    f"{path}: пакет {name} зависит от {dependency}, "
                    f"но {dependency} в файле не описан"
                )


def make_lookup(repo, path):
    """Вернуть функцию получения зависимостей пакета из ``repo``.

    Функция имеет тот же вид, что и для реального репозитория,
    поэтому граф строится одинаково в обоих режимах.
    """
    def get_dependencies(name):
        """Вернуть прямые зависимости пакета ``name``."""
        if name not in repo:
            raise RepoFileError(f"{path}: пакет {name} в файле не описан")
        return repo[name]
    return get_dependencies
