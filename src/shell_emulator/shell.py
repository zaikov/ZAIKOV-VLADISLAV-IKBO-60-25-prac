"""Ядро эмулятора: разбор ввода и выполнение команд.

Модуль не зависит от графического интерфейса, поэтому его удобно
тестировать отдельно.
"""

EXIT_SUCCESS = 0
EXIT_CODE_MODULO = 256
MAX_CD_ARGS = 1
MAX_EXIT_ARGS = 1
LS_OPTIONS = "la"


class ShellError(Exception):
    """Ошибка выполнения: неизвестная команда или неверные аргументы."""


def parse(line):
    """Разбить строку ввода на команду и список аргументов по пробелам.

    :param line: строка, введённая пользователем.
    :return: кортеж ``(команда, аргументы)``; для пустой строки
        ``(None, [])``.
    """
    parts = line.split()
    if not parts:
        return None, []
    return parts[0], parts[1:]


def _stub_output(name, args):
    """Сформировать вывод команды-заглушки: её имя и аргументы."""
    if not args:
        return f"{name}: called with no arguments"
    return f"{name}: called with arguments: {' '.join(args)}"


def _check_ls_options(args):
    """Проверить ключи команды ls.

    :raises ShellError: если встречен неподдерживаемый ключ.
    """
    for arg in args:
        if not arg.startswith("-") or arg == "-":
            continue
        for option in arg[1:]:
            if option not in LS_OPTIONS:
                raise ShellError(f"ls: invalid option -- '{option}'")


def _parse_exit_code(text):
    """Преобразовать аргумент exit в код возврата, как это делает bash.

    :raises ShellError: если аргумент не является целым числом.
    """
    try:
        return int(text) % EXIT_CODE_MODULO
    except ValueError:
        raise ShellError(
            f"exit: {text}: numeric argument required"
        ) from None


class Shell:
    """Интерпретатор команд эмулятора.

    Атрибут ``running`` становится ``False`` после команды exit,
    а ``exit_code`` хранит код завершения.
    """

    def __init__(self):
        """Создать оболочку с набором поддерживаемых команд."""
        self.running = True
        self.exit_code = EXIT_SUCCESS
        self._commands = {
            "ls": self._ls,
            "cd": self._cd,
            "exit": self._exit,
        }

    def execute(self, line):
        """Выполнить строку ввода и вернуть текст вывода.

        :param line: строка, введённая пользователем.
        :return: вывод команды (может быть пустой строкой).
        :raises ShellError: если команда неизвестна или аргументы неверны.
        """
        name, args = parse(line)
        if name is None:
            return ""
        handler = self._commands.get(name)
        if handler is None:
            raise ShellError(f"{name}: command not found")
        return handler(args)

    def _ls(self, args):
        """Заглушка ls: проверить ключи и вывести имя и аргументы."""
        _check_ls_options(args)
        return _stub_output("ls", args)

    def _cd(self, args):
        """Заглушка cd: принимает не более одного аргумента."""
        if len(args) > MAX_CD_ARGS:
            raise ShellError("cd: too many arguments")
        return _stub_output("cd", args)

    def _exit(self, args):
        """Завершить работу эмулятора с необязательным кодом возврата."""
        if len(args) > MAX_EXIT_ARGS:
            raise ShellError("exit: too many arguments")
        code = _parse_exit_code(args[0]) if args else EXIT_SUCCESS
        self.exit_code = code
        self.running = False
        return "exit"
