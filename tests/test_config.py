"""Тесты загрузки и проверки конфигурации."""

import os
import tempfile
import unittest

from depgraph.config import ConfigError, load_config

VALID_CONFIG = {
    "package_name": '"Serilog.Sinks.Console"',
    "repository": '"https://api.nuget.org/v3/index.json"',
    "test_mode": "false",
    "output_file": '"graph.svg"',
    "ascii_tree": "true",
}


class ConfigTestCase(unittest.TestCase):
    """Базовый класс: временный каталог для конфигурационных файлов."""

    def setUp(self):
        """Создать временный каталог."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def make_file(self, name, text):
        """Записать файл во временный каталог и вернуть путь к нему."""
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        return path

    def make_config(self, **overrides):
        """Создать TOML-файл из VALID_CONFIG с заменой значений.

        Значение ``None`` удаляет параметр из файла.
        """
        values = dict(VALID_CONFIG, **overrides)
        lines = [
            f"{key} = {value}"
            for key, value in values.items() if value is not None
        ]
        return self.make_file("config.toml", "\n".join(lines) + "\n")

    def assert_error(self, message, **overrides):
        """Проверить, что конфигурация вызывает ошибку с текстом."""
        path = self.make_config(**overrides)
        with self.assertRaises(ConfigError) as context:
            load_config(path)
        self.assertIn(message, "\n".join(context.exception.errors))


class LoadConfigTest(ConfigTestCase):
    """Тесты корректных конфигураций."""

    def test_valid(self):
        """Корректный файл загружается со всеми параметрами."""
        config = load_config(self.make_config())
        self.assertEqual(config.package_name, "Serilog.Sinks.Console")
        self.assertFalse(config.test_mode)
        self.assertTrue(config.ascii_tree)

    def test_items_order(self):
        """Параметры выводятся в порядке описания."""
        config = load_config(self.make_config())
        keys = [key for key, _ in config.items()]
        self.assertEqual(keys, list(VALID_CONFIG))

    def test_test_mode(self):
        """В тестовом режиме repository — путь к существующему файлу."""
        repo = self.make_file("repo.txt", "A: B\n")
        config = load_config(self.make_config(
            package_name='"A"', repository=f'"{repo}"', test_mode="true",
        ))
        self.assertEqual(config.repository, repo)


class FileErrorsTest(ConfigTestCase):
    """Тесты ошибок чтения файла."""

    def test_missing_file(self):
        """Отсутствующий файл конфигурации."""
        missing = os.path.join(self.tmp.name, "missing.toml")
        with self.assertRaisesRegex(ConfigError, "не найден"):
            load_config(missing)

    def test_directory(self):
        """Вместо файла указан каталог."""
        with self.assertRaisesRegex(ConfigError, "не удалось прочитать"):
            load_config(self.tmp.name)

    def test_invalid_toml(self):
        """Синтаксическая ошибка TOML."""
        path = self.make_file("bad.toml", 'package_name = "Serilog\n')
        with self.assertRaisesRegex(ConfigError, "неверный формат TOML"):
            load_config(path)

    def test_not_utf8(self):
        """Файл не в кодировке UTF-8."""
        path = os.path.join(self.tmp.name, "cp1251.toml")
        with open(path, "wb") as file:
            file.write('a = "привет"'.encode("cp1251"))
        with self.assertRaisesRegex(ConfigError, "UTF-8"):
            load_config(path)


class KeyErrorsTest(ConfigTestCase):
    """Тесты набора ключей и типов значений."""

    def test_missing_key(self):
        """Отсутствующий параметр."""
        self.assert_error("ascii_tree: обязательный", ascii_tree=None)

    def test_unknown_key(self):
        """Неизвестный параметр."""
        self.assert_error("extra: неизвестный параметр", extra="1")

    def test_wrong_types(self):
        """Неверный тип значения у каждого параметра."""
        cases = {
            "package_name": "42",
            "repository": "[]",
            "test_mode": '"false"',
            "output_file": "1.5",
            "ascii_tree": "1",
        }
        for key, value in cases.items():
            with self.subTest(key=key):
                self.assert_error(f"{key}: ожидается", **{key: value})

    def test_all_errors_reported(self):
        """Все ошибки типов выводятся вместе, а не только первая."""
        path = self.make_config(package_name="1", ascii_tree='"yes"')
        with self.assertRaises(ConfigError) as context:
            load_config(path)
        self.assertEqual(len(context.exception.errors), 2)


class ValueErrorsTest(ConfigTestCase):
    """Тесты проверки значений по смыслу."""

    def test_package_name(self):
        """Ошибки имени пакета."""
        cases = {
            '""': "не может быть пустым",
            f'"{"A" * 101}"': "длиннее 100 символов",
            '"Serilog Sinks"': "недопустимое имя пакета",
            '"Serilog..Sinks"': "недопустимое имя пакета",
        }
        for value, message in cases.items():
            with self.subTest(value=value):
                self.assert_error(message, package_name=value)

    def test_package_name_test_mode(self):
        """В тестовом режиме имя пакета — большие латинские буквы."""
        repo = self.make_file("repo.txt", "A:\n")
        self.assert_error(
            "больших латинских букв", package_name='"Serilog"',
            repository=f'"{repo}"', test_mode="true",
        )

    def test_repository_url(self):
        """Ошибки URL репозитория."""
        cases = {
            '"  "': "не задан URL",
            '"ftp://host/index.json"': "неверный URL",
            '"https://"': "неверный URL",
            '"examples/test_repo.txt"': "включите test_mode",
        }
        for value, message in cases.items():
            with self.subTest(value=value):
                self.assert_error(message, repository=value)

    def test_repository_file(self):
        """Ошибки пути к файлу тестового репозитория."""
        missing = os.path.join(self.tmp.name, "missing.txt")
        cases = {
            f'"{missing}"': "не найден",
            f'"{self.tmp.name}"': "не является файлом",
        }
        for value, message in cases.items():
            with self.subTest(value=value):
                self.assert_error(
                    message, package_name='"A"', repository=value,
                    test_mode="true",
                )

    def test_output_file(self):
        """Ошибки имени файла с изображением графа."""
        cases = {
            '""': "не может быть пустым",
            '"graph.png"': "расширением .svg",
            '".svg"': "не задано имя файла",
            '"no_such_dir/graph.svg"': "не существует",
        }
        for value, message in cases.items():
            with self.subTest(value=value):
                self.assert_error(message, output_file=value)

    def test_output_file_is_directory(self):
        """Имя файла указывает на существующий каталог."""
        directory = os.path.join(self.tmp.name, "dir.svg")
        os.mkdir(directory)
        self.assert_error("является каталогом", output_file=f'"{directory}"')


if __name__ == "__main__":
    unittest.main()
