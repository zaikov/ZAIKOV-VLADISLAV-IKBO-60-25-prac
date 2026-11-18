"""Тесты запуска приложения целиком."""

import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

from depgraph.__main__ import (
    EXIT_CONFIG_ERROR, EXIT_CYCLE, EXIT_OK, EXIT_RENDER_ERROR,
    EXIT_REPOSITORY_ERROR, main,
)
from depgraph.nuget import NugetError
from depgraph.visualize import RenderError

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

    def make_config(self, package, repository, test_mode, **flags):
        """Создать конфигурационный файл с заданными параметрами.

        ``flags`` — логические параметры ``ascii_tree`` и ``load_order``,
        по умолчанию выключенные.
        """
        values = {"test_mode": test_mode, "ascii_tree": False,
                  "load_order": False, **flags}
        lines = [
            f'package_name = "{package}"',
            f'repository = "{repository}"',
            f'output_file = "{self.output_file()}"',
        ]
        lines += [
            f"{key} = {'true' if value else 'false'}"
            for key, value in values.items()
        ]
        return self.make_file("config.toml", "\n".join(lines) + "\n")

    def output_file(self):
        """Вернуть путь к файлу SVG во временном каталоге."""
        return os.path.join(self.tmp.name, "graph.svg")

    def run_main(self, config, render_error=None):
        """Запустить main и вернуть (код, stdout, stderr).

        Вызов Graphviz подменяется, чтобы тесты не зависели от того,
        установлен ли он; ``render_error`` имитирует его ошибку.
        """
        out, err = io.StringIO(), io.StringIO()
        with (
            mock.patch("depgraph.__main__.render_svg") as render,
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            render.side_effect = render_error
            code = main(["-c", config])
        self.render = render
        return code, out.getvalue(), err.getvalue()

    def test_test_mode_graph(self):
        """В тестовом режиме граф строится по файлу и выводится."""
        repo = self.make_file("repo.txt", "A: B\nB: A C\nC:\n")
        code, out, _ = self.run_main(self.make_config("A", repo, True))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("пакетов 3, связей 3", out)
        self.assertIn("  [1] B -> A, C", out)
        self.assertIn("  A -> B -> A", out)

    def test_visualization(self):
        """Выводятся описание DOT и сообщение о сохранённом SVG."""
        repo = self.make_file("repo.txt", "A: B\nB:\n")
        code, out, _ = self.run_main(self.make_config("A", repo, True))
        self.assertEqual(code, EXIT_OK)
        self.assertIn('    "A" -> "B";', out)
        self.assertIn(f"сохранено в {self.output_file()}", out)
        self.assertNotIn("ASCII-дерево", out)
        dot_text, path = self.render.call_args.args
        self.assertTrue(dot_text.startswith('digraph "A"'))
        self.assertEqual(path, self.output_file())

    def test_ascii_tree(self):
        """При ascii_tree = true выводится ASCII-дерево."""
        repo = self.make_file("repo.txt", "A: B\nB:\n")
        config = self.make_config("A", repo, True, ascii_tree=True)
        _, out, _ = self.run_main(config)
        self.assertIn("ASCII-дерево зависимостей:\nA\n└── B\n", out)

    def test_render_error(self):
        """Ошибка Graphviz — код 5, остальной вывод сохраняется."""
        repo = self.make_file("repo.txt", "A:\n")
        config = self.make_config("A", repo, True, ascii_tree=True)
        code, out, err = self.run_main(config, RenderError("нет dot"))
        self.assertEqual(code, EXIT_RENDER_ERROR)
        self.assertIn("Ошибка: нет dot", err)
        self.assertIn("ASCII-дерево", out)

    def test_test_mode_error(self):
        """Ошибка файла репозитория — код 3."""
        repo = self.make_file("repo.txt", "A: B\n")
        code, out, err = self.run_main(self.make_config("A", repo, True))
        self.assertEqual(code, EXIT_REPOSITORY_ERROR)
        self.assertEqual(out, "")
        self.assertIn("B в файле не описан", err)

    def test_load_order(self):
        """Режим load_order выводит порядок загрузки вместо графа."""
        repo = self.make_file("repo.txt", "A: B C\nB: C\nC:\n")
        code, out, _ = self.run_main(
            self.make_config("A", repo, True, load_order=True)
        )
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(out.splitlines(), [
            "Порядок загрузки зависимостей пакета A:",
            "  1. C",
            "  2. B",
            "  3. A (анализируемый пакет)",
        ])

    def test_load_order_cycle(self):
        """При цикле в режиме load_order — код 4."""
        repo = self.make_file("repo.txt", "A: B\nB: A\n")
        code, out, _ = self.run_main(
            self.make_config("A", repo, True, load_order=True)
        )
        self.assertEqual(code, EXIT_CYCLE)
        self.assertIn("нельзя определить", out)

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
