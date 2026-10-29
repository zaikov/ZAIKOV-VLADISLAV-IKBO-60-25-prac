"""Точка входа: ``python -m shell_emulator [--vfs] [--script] [--config]``."""

import sys
import tkinter as tk

from shell_emulator.config import describe, load_settings
from shell_emulator.gui import EmulatorApp
from shell_emulator.shell import Shell

WINDOW_SIZE = "800x500"


def main(argv=None):
    """Запустить эмулятор и вернуть код завершения.

    :param argv: аргументы командной строки; по умолчанию ``sys.argv[1:]``.
    """
    # При неверных параметрах argparse сам печатает ошибку и завершает
    # программу с кодом 2 — окно в этом случае не открывается.
    settings = load_settings(argv)
    # Отладочный вывод параметров дублируем в терминал.
    for line in describe(settings) + settings.errors:
        print(line)
    root = tk.Tk()
    root.geometry(WINDOW_SIZE)
    shell = Shell()
    app = EmulatorApp(root, shell)
    app.show_settings(settings)
    app.load_vfs(settings.vfs_path)
    if settings.script_path:
        # Скрипт запускаем, когда окно уже отрисовано: так команда exit
        # из скрипта корректно закроет окно внутри mainloop.
        root.after_idle(app.run_script, settings.script_path)
    root.mainloop()
    return shell.exit_code


if __name__ == "__main__":
    sys.exit(main())
