"""Точка входа: ``python -m shell_emulator``."""

import sys
import tkinter as tk

from shell_emulator.gui import EmulatorApp
from shell_emulator.shell import Shell

WINDOW_SIZE = "800x500"


def main():
    """Запустить эмулятор и вернуть код завершения."""
    root = tk.Tk()
    root.geometry(WINDOW_SIZE)
    shell = Shell()
    EmulatorApp(root, shell)
    root.mainloop()
    return shell.exit_code


if __name__ == "__main__":
    sys.exit(main())
