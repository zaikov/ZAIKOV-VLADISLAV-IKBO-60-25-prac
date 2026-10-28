"""Тесты стартового скрипта: чтение файла и выполнение в окне."""

import os
import tempfile
import tkinter as tk
import unittest

from shell_emulator.gui import EmulatorApp
from shell_emulator.script import read_script
from shell_emulator.shell import Shell, ShellError


class ScriptTestCase(unittest.TestCase):
    """Базовый класс: временный каталог для файлов скриптов."""

    def setUp(self):
        """Создать временный каталог."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def make_script(self, text):
        """Записать скрипт во временный каталог и вернуть путь к нему."""
        path = os.path.join(self.tmp.name, "start.txt")
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        return path


class ReadScriptTest(ScriptTestCase):
    """Тесты чтения файла скрипта."""

    def test_skips_comments_and_empty_lines(self):
        """Комментарии и пустые строки пропускаются, номера сохраняются."""
        path = self.make_script("# comment\nls\n\n  cd /tmp  \n")
        self.assertEqual(read_script(path), [(2, "ls"), (4, "cd /tmp")])

    def test_missing_file(self):
        """Отсутствующий файл — ошибка."""
        missing = os.path.join(self.tmp.name, "missing.txt")
        with self.assertRaisesRegex(ShellError, "file not found"):
            read_script(missing)


class RunScriptTest(ScriptTestCase):
    """Тесты выполнения скрипта в окне эмулятора."""

    def setUp(self):
        """Создать окно эмулятора; пропустить тест без дисплея."""
        super().setUp()
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("графический дисплей недоступен")
        self.root.withdraw()
        self.shell = Shell()
        self.app = EmulatorApp(self.root, self.shell)

    def tearDown(self):
        """Закрыть окно, если оно ещё существует."""
        if self.shell.running:
            self.root.destroy()

    def output(self):
        """Вернуть весь текст из поля вывода."""
        return self.app.output.get("1.0", tk.END)

    def test_shows_input_and_output(self):
        """В окне видны и введённые команды, и их вывод."""
        path = self.make_script("cd /tmp\n")
        self.assertTrue(self.app.run_script(path))
        self.assertIn(":~$ cd /tmp", self.output())
        self.assertIn("cd: called with arguments: /tmp", self.output())

    def test_stops_on_first_error(self):
        """Скрипт останавливается на первой ошибке."""
        path = self.make_script("ls\ncd a b\nls -a\n")
        self.assertFalse(self.app.run_script(path))
        self.assertIn("line 2: execution stopped", self.output())
        self.assertNotIn("ls -a", self.output())

    def test_exit_stops_script(self):
        """Команда exit завершает скрипт и эмулятор."""
        path = self.make_script("exit 5\nls\n")
        self.assertTrue(self.app.run_script(path))
        self.assertFalse(self.shell.running)
        self.assertEqual(self.shell.exit_code, 5)


if __name__ == "__main__":
    unittest.main()
