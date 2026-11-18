"""Тесты чтения файла тестового репозитория."""

import os
import tempfile
import unittest

from depgraph.graph import build_graph
from depgraph.repo_file import RepoFileError, load_repo_file, make_lookup

# Папка с примерами лежит в корне проекта, рядом с tests/.
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES_DIR = os.path.join(PROJECT_DIR, "examples", "test_repos")


class RepoFileTestCase(unittest.TestCase):
    """Базовый класс: временный каталог для файлов репозитория."""

    def setUp(self):
        """Создать временный каталог."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def make_repo(self, text):
        """Записать файл репозитория и вернуть путь к нему."""
        path = os.path.join(self.tmp.name, "repo.txt")
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        return path


class LoadRepoFileTest(RepoFileTestCase):
    """Тесты корректных файлов."""

    def test_parse(self):
        """Пакеты и зависимости, комментарии и пустые строки."""
        path = self.make_repo("# граф\nA: B C\n\nB: C\nC:\n")
        repo = load_repo_file(path)
        self.assertEqual(repo, {"A": ["B", "C"], "B": ["C"], "C": []})

    def test_repeated_dependency(self):
        """Повторы в списке зависимостей убираются."""
        repo = load_repo_file(self.make_repo("A: B B\nB:\n"))
        self.assertEqual(repo["A"], ["B"])

    def test_examples(self):
        """Все примеры из examples/test_repos загружаются."""
        for name in sorted(os.listdir(EXAMPLES_DIR)):
            if not name.endswith(".txt"):
                continue
            with self.subTest(name=name):
                load_repo_file(os.path.join(EXAMPLES_DIR, name))

    def test_error_examples(self):
        """Примеры из examples/test_repos/errors содержат ошибки.

        Пустой файл загружается, а ошибка возникает при поиске пакета.
        """
        errors_dir = os.path.join(EXAMPLES_DIR, "errors")
        for name in sorted(os.listdir(errors_dir)):
            path = os.path.join(errors_dir, name)
            with self.subTest(name=name):
                with self.assertRaises(RepoFileError):
                    repo = load_repo_file(path)
                    make_lookup(repo, path)("A")

    def test_graph_from_file(self):
        """Граф строится по файлу так же, как по репозиторию NuGet."""
        path = self.make_repo("A: B\nB: A C\nC:\n")
        repo = load_repo_file(path)
        graph = build_graph("A", make_lookup(repo, path))
        self.assertEqual(graph.nodes(), ["A", "B", "C"])


class RepoFileErrorsTest(RepoFileTestCase):
    """Тесты ошибок файла репозитория."""

    def test_errors(self):
        """Ошибки содержимого файла с номером строки."""
        cases = {
            "A: B\nB C\n": "repo.txt:2: ожидается строка вида",
            "A: lib\n": "больших латинских букв, получено 'lib'",
            "a: B\nB:\n": "получено 'a'",
            ": B\nB:\n": "получено ''",
            "A:\nA: B\n": "repo.txt:2: пакет A описан повторно",
            "A: B C\nB:\n": "пакет A зависит от C",
        }
        for text, message in cases.items():
            with self.subTest(text=text):
                with self.assertRaisesRegex(RepoFileError, message):
                    load_repo_file(self.make_repo(text))

    def test_missing_file(self):
        """Файл не найден."""
        missing = os.path.join(self.tmp.name, "missing.txt")
        with self.assertRaisesRegex(RepoFileError, "файл не найден"):
            load_repo_file(missing)

    def test_not_utf8(self):
        """Файл не в UTF-8."""
        path = os.path.join(self.tmp.name, "cp1251.txt")
        with open(path, "wb") as file:
            file.write("# пакеты\nA:\n".encode("cp1251"))
        with self.assertRaisesRegex(RepoFileError, "UTF-8"):
            load_repo_file(path)

    def test_root_not_described(self):
        """Анализируемый пакет не описан в файле."""
        path = self.make_repo("A:\n")
        get_dependencies = make_lookup(load_repo_file(path), path)
        with self.assertRaisesRegex(RepoFileError, "пакет Z в файле"):
            get_dependencies("Z")


if __name__ == "__main__":
    unittest.main()
