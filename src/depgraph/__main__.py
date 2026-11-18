"""Точка входа: ``python -m depgraph [-c CONFIG]``."""

import argparse
import sys

from depgraph.config import ConfigError, load_config
from depgraph.graph import build_graph, format_graph
from depgraph.nuget import NugetClient, NugetError
from depgraph.repo_file import RepoFileError, load_repo_file, make_lookup

DEFAULT_CONFIG = "config.toml"
EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_REPOSITORY_ERROR = 3


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


def make_source(config):
    """Вернуть функцию получения прямых зависимостей пакета.

    В тестовом режиме зависимости берутся из файла, иначе —
    из репозитория NuGet (последняя стабильная версия пакета,
    зависимости всех целевых платформ). Обе функции принимают имя
    пакета и возвращают список имён его прямых зависимостей.
    """
    if config.test_mode:
        repo = load_repo_file(config.repository)
        return make_lookup(repo, config.repository)
    client = NugetClient(config.repository)

    def fetch_dependencies(name):
        """Загрузить прямые зависимости пакета из NuGet."""
        # Каждый пакет требует нескольких HTTP-запросов, поэтому
        # показываем ход загрузки, чтобы было видно, что программа
        # работает. Пишем в поток ошибок, чтобы не смешивать с графом.
        print(f"Загрузка {name}...", file=sys.stderr)
        return client.get_package(name).unique_dependencies()
    return fetch_dependencies


def print_error(message):
    """Вывести сообщение об ошибке в поток ошибок."""
    print(f"Ошибка: {message}", file=sys.stderr)


def main(argv=None):
    """Запустить приложение и вернуть код завершения.

    :param argv: аргументы командной строки; по умолчанию ``sys.argv[1:]``.
    """
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        for message in error.errors:
            print_error(f"{args.config}: {message}")
        return EXIT_CONFIG_ERROR
    try:
        source = make_source(config)
        graph = build_graph(config.package_name, source)
    except (NugetError, RepoFileError) as error:
        print_error(str(error))
        return EXIT_REPOSITORY_ERROR
    for line in format_graph(graph):
        print(line)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
