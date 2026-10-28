"""Графический интерфейс эмулятора на tkinter."""

import getpass
import socket
import tkinter as tk
from tkinter import scrolledtext

from shell_emulator.shell import ShellError

FONT = ("Menlo", 13)
BACKGROUND = "#1e1e1e"
FOREGROUND = "#d4d4d4"
ERROR_COLOR = "#f14c4c"
PROMPT_COLOR = "#6a9955"


def get_user_host():
    """Вернуть строку ``username@hostname`` по реальным данным ОС."""
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
        self.output.tag_config("error", foreground=ERROR_COLOR)
        self.output.tag_config("prompt", foreground=PROMPT_COLOR)
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
        self.entry.bind("<Return>", self._on_enter)
        self.entry.focus_set()

    def prompt(self):
        """Вернуть текст приглашения командной строки."""
        return f"{self.user_host}:~$ "

    def write(self, text, tag=None):
        """Добавить текст в поле вывода.

        :param text: выводимый текст.
        :param tag: имя тега оформления (``"error"``, ``"prompt"``).
        """
        tags = (tag,) if tag else ()
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text, tags)
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def run_command(self, line):
        """Выполнить команду, показав ввод и вывод, как в терминале.

        :param line: строка с командой.
        :return: ``True``, если команда выполнилась без ошибки.
        """
        self.write(self.prompt(), "prompt")
        self.write(line + "\n")
        try:
            result = self.shell.execute(line)
        except ShellError as error:
            self.write(f"{error}\n", "error")
            return False
        if result:
            self.write(result + "\n")
        if not self.shell.running:
            self.root.destroy()
        return True

    def _on_enter(self, _event):
        """Обработать нажатие Enter в строке ввода."""
        line = self.entry.get()
        self.entry.delete(0, tk.END)
        self.run_command(line)
        return "break"
