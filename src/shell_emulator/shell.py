"""Ядро эмулятора: разбор ввода и выполнение команд.

Модуль не зависит от графического интерфейса, поэтому его удобно
тестировать отдельно.
"""

from shell_emulator.vfs import VfsError, default_vfs, read_vfs, write_vfs

EXIT_SUCCESS = 0
# Код возврата в UNIX занимает один байт, поэтому bash берёт его
# по модулю 256: exit 257 даёт код 1.
EXIT_CODE_MODULO = 256
MAX_CD_ARGS = 1
MAX_EXIT_ARGS = 1
# Ключи, которые понимает заглушка ls (можно комбинировать: -la).
LS_OPTIONS = "la"


class ShellError(Exception):
    """Ошибка выполнения: неизвестная команда или неверные аргументы."""


def parse(line):
    """Разбить строку ввода на команду и список аргументов по пробелам.

    :param line: строка, введённая пользователем.
    :return: кортеж ``(команда, аргументы)``; для пустой строки
        ``(None, [])``.
    """
    # split() без аргументов делит по любым пробельным символам
    # и не создаёт пустых элементов при нескольких пробелах подряд.
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
        # Длинные ключи (--help, --all) заглушка не поддерживает.
        if arg.startswith("--"):
            raise ShellError(f"ls: unrecognized option '{arg}'")
        # Аргументы без «-» и одиночный «-» — это пути, а не ключи.
        if not arg.startswith("-") or arg == "-":
            continue
        # Короткие ключи можно объединять: -la = -l -a.
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
    а ``exit_code`` хранит код завершения. ``vfs`` — текущая
    виртуальная файловая система, ``vfs_path`` — путь к её CSV-файлу.
    """

    def __init__(self):
        """Создать оболочку с набором поддерживаемых команд."""
        self.running = True
        self.exit_code = EXIT_SUCCESS
        # Пока VFS не загружена, работаем с VFS по умолчанию.
        self.vfs = default_vfs()
        self.vfs_path = None
        # Таблица команд: имя команды -> метод, который её выполняет.
        # Чтобы добавить команду, достаточно дописать её сюда.
        self._commands = {
            "ls": self._ls,
            "cd": self._cd,
            "exit": self._exit,
            "vfs-init": self._vfs_init,
        }

    def execute(self, line):
        """Выполнить строку ввода и вернуть текст вывода.

        :param line: строка, введённая пользователем.
        :return: вывод команды (может быть пустой строкой).
        :raises ShellError: если команда неизвестна или аргументы неверны.
        """
        name, args = parse(line)
        # Пустой ввод (только Enter) ничего не делает, как в bash.
        if name is None:
            return ""
        handler = self._commands.get(name)
        if handler is None:
            raise ShellError(f"{name}: command not found")
        return handler(args)

    def load_vfs(self, path):
        """Загрузить VFS из CSV-файла.

        Путь запоминается в любом случае, чтобы vfs-init мог очистить
        файл. Если загрузка не удалась, остаётся VFS по умолчанию.

        :param path: путь к CSV-файлу.
        :raises VfsError: если файл не найден или имеет неверный формат.
        """
        self.vfs_path = path
        self.vfs = read_vfs(path)

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
        # Само окно закрывает GUI, увидев running == False.
        self.running = False
        return "exit"

    def _vfs_init(self, args):
        """Заменить текущую VFS на VFS по умолчанию.

        Физический CSV-файл VFS (если он задан) тоже очищается:
        в нём остаётся только строка заголовка.
        """
        if args:
            raise ShellError("vfs-init: too many arguments")
        self.vfs = default_vfs()
        if self.vfs_path is None:
            return "vfs-init: VFS reset to default"
        try:
            write_vfs(self.vfs, self.vfs_path)
        except VfsError as error:
            raise ShellError(f"vfs-init: {error}") from None
        return f"vfs-init: VFS reset to default, {self.vfs_path} cleared"
