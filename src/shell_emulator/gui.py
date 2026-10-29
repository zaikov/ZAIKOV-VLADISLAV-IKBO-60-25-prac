"""Графический интерфейс эмулятора на tkinter."""

import getpass
import socket
import tkinter as tk
from tkinter import scrolledtext

from shell_emulator.config import describe
from shell_emulator.script import read_script
from shell_emulator.shell import ShellError
from shell_emulator.vfs import VfsError

# Оформление окна в стиле тёмного терминала.
FONT = ("Menlo", 13)
BACKGROUND = "#1e1e1e"
FOREGROUND = "#d4d4d4"
ERROR_COLOR = "#f14c4c"
PROMPT_COLOR = "#6a9955"
DEBUG_COLOR = "#808080"


def get_user_host():
    """Вернуть строку ``username@hostname`` по реальным данным ОС."""
    # getuser() берёт имя из переменных окружения или системной базы
    # пользователей, gethostname() — сетевое имя компьютера.
    return f"{getpass.getuser()}@{socket.gethostname()}"


class EmulatorApp:
    """Окно терминала: поле вывода и строка ввода с приглашением."""

    def __init__(self, root, shell):
        """Построить окно эмулятора.

        :param root: корневое окно tkinter.
        :param shell: объект :class:`~shell_emulator.shell.Shell`.
        """
        self.root = root
        self.shell = shell
        self.user_host = get_user_host()
        root.title(f"Эмулятор - [{self.user_host}]")
        root.configure(bg=BACKGROUND)
        self._build_output()
        self._build_input()

    def _build_output(self):
        """Создать поле вывода, доступное только для чтения."""
        self.output = scrolledtext.ScrolledText(
            self.root, state=tk.DISABLED, wrap=tk.WORD, font=FONT,
            bg=BACKGROUND, fg=FOREGROUND, relief=tk.FLAT,
        )
        # Теги задают цвет отдельных фрагментов текста.
        self.output.tag_config("error", foreground=ERROR_COLOR)
        self.output.tag_config("prompt", foreground=PROMPT_COLOR)
        self.output.tag_config("debug", foreground=DEBUG_COLOR)
        self.output.pack(fill=tk.BOTH, expand=True)

    def _build_input(self):
        """Создать строку ввода с приглашением."""
        bar = tk.Frame(self.root, bg=BACKGROUND)
        bar.pack(fill=tk.X)
        tk.Label(
            bar, text=self.prompt(), font=FONT,
            bg=BACKGROUND, fg=PROMPT_COLOR,
        ).pack(side=tk.LEFT)
        self.entry = tk.Entry(
            bar, font=FONT, bg=BACKGROUND, fg=FOREGROUND,
            insertbackground=FOREGROUND, relief=tk.FLAT,
            highlightthickness=0,
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        # По нажатию Enter выполняем введённую команду.
        self.entry.bind("<Return>", self._on_enter)
        self.entry.focus_set()

    def prompt(self):
        """Вернуть текст приглашения командной строки."""
        return f"{self.user_host}:~$ "

    def write(self, text, tag=None):
        """Добавить текст в поле вывода.

        :param text: выводимый текст.
        :param tag: имя тега оформления (``"error"``, ``"prompt"``,
            ``"debug"``).
        """
        tags = (tag,) if tag else ()
        # Поле вывода закрыто для редактирования пользователем, поэтому
        # на время записи его нужно временно открыть.
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text, tags)
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def run_command(self, line):
        """Выполнить команду, показав ввод и вывод, как в терминале.

        :param line: строка с командой.
        :return: ``True``, если команда выполнилась без ошибки.
        """
        # Сначала повторяем ввод с приглашением, как это делает терминал.
        self.write(self.prompt(), "prompt")
        self.write(line + "\n")
        try:
            result = self.shell.execute(line)
        except ShellError as error:
            self.write(f"{error}\n", "error")
            return False
        if result:
            self.write(result + "\n")
        # После команды exit закрываем окно.
        if not self.shell.running:
            self.root.destroy()
        return True

    def show_settings(self, settings):
        """Вывести параметры запуска и ошибки чтения конфигурации.

        :param settings: объект :class:`~shell_emulator.config.Settings`.
        """
        for line in describe(settings):
            self.write(line + "\n", "debug")
        for error in settings.errors:
            self.write(error + "\n", "error")

    def load_vfs(self, path):
        """Загрузить VFS и сообщить о результате в окне.

        :param path: путь к CSV-файлу VFS или ``None``.
        """
        if not path:
            self.write("[debug] VFS: default (empty)\n", "debug")
            return
        try:
            self.shell.load_vfs(path)
        except VfsError as error:
            # При ошибке эмулятор продолжает работу с VFS по умолчанию.
            self.write(f"{error}\n", "error")
            self.write("[debug] VFS: default (empty)\n", "debug")
            return
        dirs, files, depth = self.shell.vfs.stats()
        self.write(
            f"[debug] VFS loaded from {path}: {dirs} directories, "
            f"{files} files, depth {depth}\n",
            "debug",
        )

    def run_script(self, path):
        """Выполнить стартовый скрипт, показывая ввод и вывод команд.

        Выполнение останавливается на первой ошибке.

        :param path: путь к файлу скрипта.
        :return: ``True``, если скрипт выполнен без ошибок.
        """
        try:
            commands = read_script(path)
        except ShellError as error:
            self.write(f"{error}\n", "error")
            return False
        for number, line in commands:
            if not self.run_command(line):
                self.write(
                    f"script: {path}: line {number}: execution stopped\n",
                    "error",
                )
                return False
            # Если в скрипте встретился exit, окно уже закрыто —
            # остальные команды выполнять не нужно.
            if not self.shell.running:
                break
        return True

    def _on_enter(self, _event):
        """Обработать нажатие Enter в строке ввода."""
        line = self.entry.get()
        self.entry.delete(0, tk.END)
        self.run_command(line)
        # "break" не даёт tkinter обработать Enter ещё раз по умолчанию.
        return "break"
