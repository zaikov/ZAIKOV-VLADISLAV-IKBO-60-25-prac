"""Точка входа: ``python -m depgraph [-c CONFIG]``."""

import argparse
import sys

from depgraph.config import ConfigError, format_value, load_config

DEFAULT_CONFIG = "config.toml"
EXIT_OK = 0
EXIT_CONFIG_ERROR = 1


def build_parser():
    """Создать разборщик аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="depgraph",
        description="Визуализация графа зависимостей пакетов NuGet.",
    )
    parser.add_argument(
        "-c", "--config", default=DEFAULT_CONFIG, metavar="PATH",
        help=f"путь к конфигурационному файлу TOML "
             f"(по умолчанию {DEFAULT_CONFIG})",
    )
    return parser


def main(argv=None):
    """Запустить приложение и вернуть код завершения.

    :param argv: аргументы командной строки; по умолчанию ``sys.argv[1:]``.
    """
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        # Сообщения об ошибках выводим в поток ошибок, по одной
        # на строку, с указанием файла конфигурации.
        for message in error.errors:
            print(f"Ошибка: {args.config}: {message}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    # Этап 1: выводим все параметры в формате «ключ = значение».
    for key, value in config.items():
        print(f"{key} = {format_value(value)}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
