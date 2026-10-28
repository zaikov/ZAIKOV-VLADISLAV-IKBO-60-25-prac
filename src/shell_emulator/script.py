"""Чтение стартового скрипта с командами эмулятора."""

from shell_emulator.shell import ShellError

COMMENT_PREFIX = "#"


def read_script(path):
    """Прочитать стартовый скрипт.

    Пустые строки и комментарии (строки, начинающиеся с ``#``)
    пропускаются.

    :param path: путь к файлу скрипта.
    :return: список пар ``(номер строки, команда)``.
    :raises ShellError: если файл не найден или не читается.
    """
    try:
        with open(path, encoding="utf-8") as file:
            lines = file.read().splitlines()
    except FileNotFoundError:
        raise ShellError(f"script: {path}: file not found") from None
    except OSError as error:
        raise ShellError(f"script: {path}: {error.strerror}") from None
    except UnicodeDecodeError:
        raise ShellError(f"script: {path}: invalid encoding") from None
    commands = []
    for number, line in enumerate(lines, start=1):
        text = line.strip()
        if text and not text.startswith(COMMENT_PREFIX):
            commands.append((number, text))
    return commands
