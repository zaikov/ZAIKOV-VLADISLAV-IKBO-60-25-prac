"""Загрузка и проверка конфигурации из файла формата TOML.

Конфигурационный файл содержит пять обязательных параметров::

    package_name = "Serilog.Sinks.Console"
    repository = "https://api.nuget.org/v3/index.json"
    test_mode = false
    output_file = "graph.svg"
    ascii_tree = true

Все найденные ошибки собираются в один список, чтобы пользователь
увидел их сразу, а не исправлял по одной.
"""

import os
import re
import tomllib
from dataclasses import dataclass
from urllib.parse import urlparse

# Параметры конфигурации и ожидаемые типы значений в TOML.
FIELD_TYPES = {
    "package_name": str,
    "repository": str,
    "test_mode": bool,
    "output_file": str,
    "ascii_tree": bool,
}
TYPE_NAMES = {
    str: "строка",
    bool: "логическое значение true/false",
}
# Ограничение длины идентификатора пакета в NuGet.
MAX_PACKAGE_NAME_LENGTH = 100
# Идентификатор NuGet: латинские буквы, цифры и «_», части
# разделяются точкой или дефисом, например Serilog.Sinks.Console.
NUGET_ID_PATTERN = re.compile(r"[A-Za-z0-9_]+(?:[.-][A-Za-z0-9_]+)*")
# В тестовом репозитории пакеты называются большими латинскими буквами.
TEST_PACKAGE_PATTERN = re.compile(r"[A-Z]+")
URL_SCHEMES = ("http", "https")
OUTPUT_EXTENSION = ".svg"


class ConfigError(Exception):
    """Ошибка конфигурации со списком сообщений ``errors``."""

    def __init__(self, errors):
        """Создать исключение по списку сообщений об ошибках."""
        super().__init__("\n".join(errors))
        self.errors = list(errors)


@dataclass(frozen=True)
class Config:
    """Проверенные параметры, заданные пользователем."""

    package_name: str
    repository: str
    test_mode: bool
    output_file: str
    ascii_tree: bool

    def items(self):
        """Вернуть пары ``(ключ, значение)`` в порядке ``FIELD_TYPES``."""
        return [(name, getattr(self, name)) for name in FIELD_TYPES]


def load_config(path):
    """Прочитать и проверить конфигурационный файл.

    :param path: путь к файлу TOML.
    :return: объект :class:`Config`.
    :raises ConfigError: если файл не читается или параметры неверны.
    """
    data = read_toml(path)
    # Сначала проверяем набор ключей и типы: без этого значения
    # нельзя безопасно проверять по смыслу.
    errors = check_keys(data) + check_types(data)
    if errors:
        raise ConfigError(errors)
    config = Config(**data)
    errors = validate(config)
    if errors:
        raise ConfigError(errors)
    return config


def read_toml(path):
    """Прочитать файл TOML и вернуть словарь параметров.

    :raises ConfigError: если файл не найден или имеет неверный формат.
    """
    try:
        # tomllib требует открывать файл в двоичном режиме.
        with open(path, "rb") as file:
            return tomllib.load(file)
    except FileNotFoundError:
        raise ConfigError(["файл конфигурации не найден"]) from None
    except OSError as error:
        message = f"не удалось прочитать файл: {error.strerror}"
        raise ConfigError([message]) from None
    except UnicodeDecodeError:
        raise ConfigError(["файл должен быть в кодировке UTF-8"]) from None
    except tomllib.TOMLDecodeError as error:
        raise ConfigError([f"неверный формат TOML: {error}"]) from None


def check_keys(data):
    """Найти отсутствующие и неизвестные параметры."""
    errors = [
        f"{key}: обязательный параметр не задан"
        for key in FIELD_TYPES if key not in data
    ]
    errors += [
        f"{key}: неизвестный параметр"
        for key in data if key not in FIELD_TYPES
    ]
    return errors


def check_types(data):
    """Проверить, что значения заданных параметров имеют нужный тип."""
    errors = []
    for key, expected in FIELD_TYPES.items():
        # Сравниваем тип точно: в Python bool — подкласс int,
        # и isinstance принял бы лишние значения.
        if key in data and type(data[key]) is not expected:
            errors.append(
                f"{key}: ожидается {TYPE_NAMES[expected]}, "
                f"получено {data[key]!r}"
            )
    return errors


def validate(config):
    """Проверить значения параметров по смыслу.

    :return: список сообщений об ошибках (пустой, если ошибок нет).
    """
    return (
        validate_package_name(config.package_name, config.test_mode)
        + validate_repository(config.repository, config.test_mode)
        + validate_output_file(config.output_file)
    )


def validate_package_name(name, test_mode):
    """Проверить имя анализируемого пакета."""
    if not name.strip():
        return ["package_name: имя пакета не может быть пустым"]
    if len(name) > MAX_PACKAGE_NAME_LENGTH:
        return [
            f"package_name: имя пакета длиннее "
            f"{MAX_PACKAGE_NAME_LENGTH} символов"
        ]
    if test_mode and not TEST_PACKAGE_PATTERN.fullmatch(name):
        return [
            f"package_name: в тестовом режиме имя пакета состоит "
            f"из больших латинских букв, получено '{name}'"
        ]
    if not NUGET_ID_PATTERN.fullmatch(name):
        return [f"package_name: недопустимое имя пакета NuGet '{name}'"]
    return []


def validate_repository(repository, test_mode):
    """Проверить URL репозитория или путь к файлу тестового репозитория."""
    if not repository.strip():
        return ["repository: не задан URL или путь к файлу репозитория"]
    # В тестовом режиме вместо URL указывается путь к файлу.
    if test_mode:
        return validate_repository_file(repository)
    return validate_repository_url(repository)


def validate_repository_file(path):
    """Проверить, что файл тестового репозитория существует."""
    if not os.path.exists(path):
        return [f"repository: файл тестового репозитория '{path}' не найден"]
    if not os.path.isfile(path):
        return [f"repository: '{path}' не является файлом"]
    return []


def validate_repository_url(url):
    """Проверить, что URL репозитория имеет вид http(s)://адрес."""
    parsed = urlparse(url)
    if parsed.scheme not in URL_SCHEMES or not parsed.netloc:
        return [
            f"repository: неверный URL '{url}', ожидается адрес "
            f"http:// или https:// (для пути к файлу включите test_mode)"
        ]
    return []


def validate_output_file(name):
    """Проверить имя файла, в который будет сохранено изображение графа."""
    if not name.strip():
        return ["output_file: имя файла не может быть пустым"]
    if not name.lower().endswith(OUTPUT_EXTENSION):
        return [
            f"output_file: ожидается файл с расширением "
            f"{OUTPUT_EXTENSION}, получено '{name}'"
        ]
    # Отрезаем расширение и проверяем, что перед ним есть имя.
    if not os.path.basename(name)[:-len(OUTPUT_EXTENSION)]:
        return [f"output_file: не задано имя файла перед '{name}'"]
    if os.path.isdir(name):
        return [f"output_file: '{name}' является каталогом"]
    directory = os.path.dirname(name)
    if directory and not os.path.isdir(directory):
        return [f"output_file: каталог '{directory}' не существует"]
    return []
