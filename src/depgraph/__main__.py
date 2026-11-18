"""Точка входа: ``python -m depgraph [-c CONFIG]``."""

import argparse
import sys

from depgraph.config import ConfigError, load_config
from depgraph.nuget import NugetClient, NugetError, describe_range

DEFAULT_CONFIG = "config.toml"
EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_REPOSITORY_ERROR = 3
INDENT = "  "


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


def format_dependencies(package):
    """Сформировать строки вывода прямых зависимостей пакета.

    :param package: объект :class:`~depgraph.nuget.PackageInfo`.
    :return: список строк.
    """
    lines = [f"Пакет: {package.package_id} {package.version}"]
    unique = package.unique_dependencies()
    if not unique:
        lines.append("Прямых зависимостей нет")
        return lines
    # Сначала — зависимости по каждой целевой платформе .NET,
    # как они записаны в манифесте пакета.
    lines.append("Прямые зависимости по целевым платформам:")
    for group in package.groups:
        lines.append(f"{INDENT}{group.target_framework}")
        if not group.dependencies:
            lines.append(f"{INDENT * 2}(нет зависимостей)")
        for dependency in group.dependencies:
            version = describe_range(dependency.version_range)
            lines.append(f"{INDENT * 2}{dependency.package_id} ({version})")
    # Затем — общий список без повторов: он нужен для построения графа.
    lines.append(f"Всего прямых зависимостей: {len(unique)}")
    lines.extend(f"{INDENT}{name}" for name in unique)
    return lines


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
    if config.test_mode:
        print_error("тестовый режим будет поддержан на этапе 3")
        return EXIT_CONFIG_ERROR
    try:
        client = NugetClient(config.repository)
        package = client.get_package(config.package_name)
    except NugetError as error:
        print_error(str(error))
        return EXIT_REPOSITORY_ERROR
    # Этап 2: выводим прямые зависимости заданного пакета.
    for line in format_dependencies(package):
        print(line)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
