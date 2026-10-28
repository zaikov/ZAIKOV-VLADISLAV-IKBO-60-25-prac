"""Тесты параметров командной строки и конфигурационного файла."""

import contextlib
import io
import os
import tempfile
import unittest

from shell_emulator.config import (
    SOURCE_CLI, SOURCE_FILE, ConfigError, describe, load_settings, read_ini,
)

USAGE_ERROR_CODE = 2


class ConfigTest(unittest.TestCase):
    """Тесты чтения и объединения параметров."""

    def setUp(self):
        """Создать временный каталог для конфигурационных файлов."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def make_ini(self, text):
        """Записать INI-файл во временный каталог и вернуть путь к нему."""
        path = os.path.join(self.tmp.name, "config.ini")
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        return path

    def test_no_params(self):
        """Без параметров все значения не заданы."""
        settings = load_settings([])
        self.assertIsNone(settings.vfs_path)
        self.assertIsNone(settings.script_path)
        self.assertEqual(settings.errors, [])

    def test_cli_only(self):
        """Параметры берутся из командной строки."""
        settings = load_settings(["--vfs", "a.csv", "--script", "s.txt"])
        self.assertEqual(settings.vfs_path, "a.csv")
        self.assertEqual(settings.script_path, "s.txt")
        self.assertEqual(settings.sources["vfs_path"], SOURCE_CLI)

    def test_file_only(self):
        """Параметры берутся из конфигурационного файла."""
        path = self.make_ini(
            "[emulator]\nvfs_path = f.csv\nscript_path = f.txt\n"
        )
        settings = load_settings(["--config", path])
        self.assertEqual(settings.vfs_path, "f.csv")
        self.assertEqual(settings.script_path, "f.txt")
        self.assertEqual(settings.sources["script_path"], SOURCE_FILE)

    def test_cli_overrides_file(self):
        """Командная строка имеет приоритет над файлом."""
        path = self.make_ini(
            "[emulator]\nvfs_path = f.csv\nscript_path = f.txt\n"
        )
        settings = load_settings(["--config", path, "--vfs", "cli.csv"])
        self.assertEqual(settings.vfs_path, "cli.csv")
        self.assertEqual(settings.sources["vfs_path"], SOURCE_CLI)
        self.assertEqual(settings.script_path, "f.txt")
        self.assertEqual(settings.sources["script_path"], SOURCE_FILE)

    def test_missing_file(self):
        """Отсутствующий файл — ошибка в settings.errors."""
        missing = os.path.join(self.tmp.name, "missing.ini")
        settings = load_settings(["--config", missing, "--vfs", "a.csv"])
        self.assertIn("file not found", settings.errors[0])
        self.assertEqual(settings.vfs_path, "a.csv")

    def test_broken_format(self):
        """Файл без заголовка секции — ошибка формата."""
        path = self.make_ini("vfs_path = f.csv\n")
        with self.assertRaisesRegex(ConfigError, "invalid INI format"):
            read_ini(path)

    def test_missing_section(self):
        """Файл без секции [emulator] — ошибка."""
        path = self.make_ini("[other]\nvfs_path = f.csv\n")
        with self.assertRaisesRegex(ConfigError, r"missing \[emulator\]"):
            read_ini(path)

    def test_unknown_argument(self):
        """Неизвестный параметр командной строки завершает программу."""
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                load_settings(["--unknown"])
        self.assertEqual(context.exception.code, USAGE_ERROR_CODE)

    def test_describe(self):
        """Отладочный вывод содержит все параметры и их источники."""
        settings = load_settings(["--vfs", "a.csv"])
        text = "\n".join(describe(settings))
        self.assertIn("config_path = None", text)
        self.assertIn(f"vfs_path = a.csv ({SOURCE_CLI})", text)
        self.assertIn("script_path = None (not set)", text)


if __name__ == "__main__":
    unittest.main()
