"""Параметры эмулятора: командная строка и конфигурационный файл INI.

Значения из командной строки имеют приоритет над значениями из файла.
"""

import argparse
import configparser
from dataclasses import dataclass, field

# Секция INI-файла, из которой читаются параметры.
INI_SECTION = "emulator"
# Параметры, которые можно задать и в командной строке, и в файле.
PARAMS = ("vfs_path", "script_path")
# Подписи источников значений для отладочного вывода.
SOURCE_CLI = "command line"
SOURCE_FILE = "config file"


class ConfigError(Exception):
    """Ошибка чтения конфигурационного файла."""


@dataclass
class Settings:
    """Итоговые параметры запуска эмулятора.

    ``sources`` хранит для каждого параметра, откуда взято значение,
    ``errors`` — сообщения об ошибках чтения конфигурации.
    """

    config_path: str | None = None
    vfs_path: str | None = None
    script_path: str | None = None
    sources: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)


def build_arg_parser():
    """Создать разборщик параметров командной строки."""
    parser = argparse.ArgumentParser(
        prog="shell_emulator",
        description="Эмулятор командной оболочки UNIX с GUI.",
    )
    parser.add_argument(
        "--vfs", dest="vfs_path", metavar="PATH",
        help="путь к физическому расположению VFS",
    )
    parser.add_argument(
        "--script", dest="script_path", metavar="PATH",
        help="путь к стартовому скрипту",
    )
    parser.add_argument(
        "--config", dest="config_path", metavar="PATH",
        help="путь к конфигурационному файлу INI",
    )
    return parser


def read_ini(path):
    """Прочитать параметры из секции ``[emulator]`` INI-файла.

    :param path: путь к конфигурационному файлу.
    :return: словарь с заданными в файле параметрами из ``PARAMS``.
    :raises ConfigError: если файл не найден или имеет неверный формат.
    """
    parser = configparser.ConfigParser()
    try:
        # read_file, в отличие от read, сообщает об отсутствии файла
        # исключением, а не молча пропускает его.
        with open(path, encoding="utf-8") as file:
            parser.read_file(file)
    except FileNotFoundError:
        raise ConfigError(f"config: {path}: file not found") from None
    except OSError as error:
        raise ConfigError(f"config: {path}: {error.strerror}") from None
    except (configparser.Error, UnicodeDecodeError) as error:
        # Сообщение configparser бывает многострочным, берём первую строку.
        reason = str(error).splitlines()[0]
        raise ConfigError(
            f"config: {path}: invalid INI format: {reason}"
        ) from None
    if not parser.has_section(INI_SECTION):
        raise ConfigError(f"config: {path}: missing [{INI_SECTION}] section")
    section = parser[INI_SECTION]
    # Пустые значения (vfs_path =) считаем незаданными.
    return {name: section[name] for name in PARAMS if section.get(name)}


def load_settings(argv=None):
    """Собрать параметры из командной строки и конфигурационного файла.

    :param argv: список аргументов; по умолчанию ``sys.argv[1:]``.
    :return: объект :class:`Settings`.
    """
    args = build_arg_parser().parse_args(argv)
    settings = Settings(config_path=args.config_path)
    # Приоритет реализован порядком применения: сначала значения
    # из файла, затем поверх них — из командной строки.
    if args.config_path:
        try:
            file_values = read_ini(args.config_path)
        except ConfigError as error:
            # Ошибка конфигурации не прерывает запуск: она будет
            # показана в окне, а параметры командной строки сработают.
            settings.errors.append(str(error))
            file_values = {}
        _apply(settings, file_values, SOURCE_FILE)
    # argparse записывает None для параметров, которые не были указаны.
    cli_values = {
        name: getattr(args, name) for name in PARAMS
        if getattr(args, name) is not None
    }
    _apply(settings, cli_values, SOURCE_CLI)
    return settings


def _apply(settings, values, source):
    """Записать значения в ``settings``, запомнив их источник."""
    for name, value in values.items():
        setattr(settings, name, value)
        settings.sources[name] = source


def describe(settings):
    """Вернуть строки отладочного вывода со всеми параметрами запуска."""
    lines = [f"[debug] config_path = {settings.config_path}"]
    for name in PARAMS:
        source = settings.sources.get(name, "not set")
        value = getattr(settings, name)
        lines.append(f"[debug] {name} = {value} ({source})")
    return lines
