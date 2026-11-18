"""Тесты запуска приложения целиком."""

import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

from depgraph.__main__ import (
    EXIT_CONFIG_ERROR, EXIT_OK, EXIT_REPOSITORY_ERROR, main,
)
from depgraph.nuget import NugetError

NUGET_URL = "https://api.nuget.org/v3/index.json"


class MainTest(unittest.TestCase):
    """Тесты функции main."""

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

    def make_config(self, package, repository, test_mode):
        """Создать конфигурационный файл с заданными параметрами."""
        mode = "true" if test_mode else "false"
        return self.make_file("config.toml", (
            f'package_name = "{package}"\n'
            f'repository = "{repository}"\n'
            f"test_mode = {mode}\n"
            f'output_file = "graph.svg"\n'
            f"ascii_tree = false\n"
        ))

    def run_main(self, config):
        """Запустить main с конфигурацией и вернуть (код, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["-c", config])
        return code, out.getvalue(), err.getvalue()

    def test_test_mode_graph(self):
        """В тестовом режиме граф строится по файлу и выводится."""
        repo = self.make_file("repo.txt", "A: B\nB: A C\nC:\n")
        code, out, _ = self.run_main(self.make_config("A", repo, True))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("пакетов 3, связей 3", out)
        self.assertIn("  [1] B -> A, C", out)
        self.assertIn("  A -> B -> A", out)

    def test_test_mode_error(self):
        """Ошибка файла репозитория — код 3."""
        repo = self.make_file("repo.txt", "A: B\n")
        code, out, err = self.run_main(self.make_config("A", repo, True))
        self.assertEqual(code, EXIT_REPOSITORY_ERROR)
        self.assertEqual(out, "")
        self.assertIn("B в файле не описан", err)

    def test_nuget_graph(self):
        """Граф реального репозитория строится через NugetClient."""
        dependencies = {"Root": ["Lib"], "Lib": []}
        with mock.patch("depgraph.__main__.NugetClient") as client:
            client.return_value.get_package.side_effect = (
                lambda name: mock.Mock(**{
                    "unique_dependencies.return_value": dependencies[name],
                })
            )
            code, out, err = self.run_main(
                self.make_config("Root", NUGET_URL, False)
            )
        self.assertEqual(code, EXIT_OK)
        client.assert_called_once_with(NUGET_URL)
        self.assertIn("  [0] Root -> Lib", out)
        self.assertIn("Загрузка Lib...", err)

    def test_nuget_error(self):
        """Ошибка репозитория NuGet — код 3 и сообщение в stderr."""
        with mock.patch("depgraph.__main__.NugetClient") as client:
            client.return_value.get_package.side_effect = NugetError("нет")
            code, _, err = self.run_main(
                self.make_config("Root", NUGET_URL, False)
            )
        self.assertEqual(code, EXIT_REPOSITORY_ERROR)
        self.assertIn("Ошибка: нет", err)

    def test_config_error(self):
        """Ошибка конфигурации — код 1, вывода в stdout нет."""
        path = self.make_file("bad.toml", "package_name = 1\n")
        code, out, err = self.run_main(path)
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertEqual(out, "")
        self.assertIn("Ошибка:", err)


if __name__ == "__main__":
    unittest.main()
