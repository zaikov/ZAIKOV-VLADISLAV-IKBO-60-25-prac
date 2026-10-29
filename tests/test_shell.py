"""Тесты ядра эмулятора: парсер и команды этапа 1."""

import unittest

from shell_emulator.gui import get_user_host
from shell_emulator.shell import Shell, ShellError, parse


class ParseTest(unittest.TestCase):
    """Тесты разбора строки ввода."""

    def test_command_with_args(self):
        """Команда и аргументы разделяются пробелами."""
        self.assertEqual(parse("ls -l /home"), ("ls", ["-l", "/home"]))

    def test_extra_spaces(self):
        """Повторяющиеся пробелы не создают пустых аргументов."""
        self.assertEqual(parse("  cd   /tmp  "), ("cd", ["/tmp"]))

    def test_empty_line(self):
        """Пустая строка не содержит команды."""
        self.assertEqual(parse("   "), (None, []))


class ShellTest(unittest.TestCase):
    """Тесты команд-заглушек и обработки ошибок."""

    def setUp(self):
        """Создать новую оболочку для каждого теста."""
        self.shell = Shell()

    def test_empty_input(self):
        """Пустой ввод ничего не выводит."""
        self.assertEqual(self.shell.execute(""), "")

    def test_ls_stub(self):
        """ls выводит своё имя и аргументы."""
        self.assertEqual(
            self.shell.execute("ls -la /home"),
            "ls: called with arguments: -la /home",
        )

    def test_ls_no_args(self):
        """ls без аргументов сообщает об этом."""
        self.assertEqual(
            self.shell.execute("ls"), "ls: called with no arguments"
        )

    def test_ls_invalid_option(self):
        """Неизвестный ключ ls — ошибка."""
        with self.assertRaisesRegex(ShellError, "invalid option -- 'z'"):
            self.shell.execute("ls -z")

    def test_ls_long_option(self):
        """Длинные ключи ls не поддерживаются."""
        with self.assertRaisesRegex(ShellError, "unrecognized option"):
            self.shell.execute("ls --help")

    def test_cd_stub(self):
        """cd выводит своё имя и аргумент."""
        self.assertEqual(
            self.shell.execute("cd /tmp"),
            "cd: called with arguments: /tmp",
        )

    def test_cd_too_many_args(self):
        """cd с несколькими аргументами — ошибка."""
        with self.assertRaisesRegex(ShellError, "too many arguments"):
            self.shell.execute("cd a b")

    def test_unknown_command(self):
        """Неизвестная команда — ошибка."""
        with self.assertRaisesRegex(ShellError, "foo: command not found"):
            self.shell.execute("foo bar")

    def test_exit(self):
        """exit останавливает оболочку с кодом 0."""
        self.shell.execute("exit")
        self.assertFalse(self.shell.running)
        self.assertEqual(self.shell.exit_code, 0)

    def test_exit_with_code(self):
        """exit N задаёт код возврата по модулю 256, как в bash."""
        self.shell.execute("exit 257")
        self.assertEqual(self.shell.exit_code, 1)

    def test_exit_not_numeric(self):
        """Нечисловой аргумент exit — ошибка, оболочка продолжает работу."""
        with self.assertRaisesRegex(ShellError, "numeric argument"):
            self.shell.execute("exit abc")
        self.assertTrue(self.shell.running)

    def test_exit_too_many_args(self):
        """exit с несколькими аргументами — ошибка."""
        with self.assertRaisesRegex(ShellError, "too many arguments"):
            self.shell.execute("exit 1 2")


class UserHostTest(unittest.TestCase):
    """Тест формирования заголовка окна."""

    def test_format(self):
        """Строка имеет вид username@hostname."""
        user, _, host = get_user_host().partition("@")
        self.assertTrue(user)
        self.assertTrue(host)


if __name__ == "__main__":
    unittest.main()
