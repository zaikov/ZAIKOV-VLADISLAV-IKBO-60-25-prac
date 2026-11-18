"""Тесты визуализации: описание DOT, SVG и ASCII-дерево."""

import subprocess
import unittest
from unittest import mock

from depgraph.graph import build_graph
from depgraph.visualize import (
    CYCLE_COLOR, RenderError, ascii_tree, quote, render_svg, to_dot,
)


def make_graph(edges, root="A"):
    """Построить граф по словарю ``{пакет: [зависимости]}``."""
    return build_graph(root, lambda name: edges[name])


class DotTest(unittest.TestCase):
    """Тесты формирования описания на языке DOT."""

    def test_structure(self):
        """Все вершины и связи попадают в описание."""
        dot = to_dot(make_graph({"A": ["B", "C"], "B": [], "C": []}))
        self.assertTrue(dot.startswith('digraph "A" {'))
        self.assertTrue(dot.rstrip().endswith("}"))
        self.assertIn('    "A" -> "B";', dot)
        self.assertIn('    "A" -> "C";', dot)
        self.assertIn('    "C";', dot)

    def test_root_highlighted(self):
        """Анализируемый пакет выделен цветом и рамкой."""
        dot = to_dot(make_graph({"A": []}))
        self.assertIn('"A" [fillcolor=', dot)
        self.assertIn("penwidth=2", dot)

    def test_cycle_edges_red(self):
        """Связи цикла выделены красным, остальные — нет."""
        dot = to_dot(make_graph({"A": ["B", "C"], "B": ["A"], "C": []}))
        cycle_style = f'[color="{CYCLE_COLOR}", penwidth=2]'
        self.assertIn(f'"A" -> "B" {cycle_style};', dot)
        self.assertIn(f'"B" -> "A" {cycle_style};', dot)
        self.assertIn('"A" -> "C";', dot)

    def test_quote(self):
        """Кавычки и обратная косая черта экранируются."""
        self.assertEqual(quote("Serilog.Sinks"), '"Serilog.Sinks"')
        self.assertEqual(quote('a"b\\c'), '"a\\"b\\\\c"')


class RenderTest(unittest.TestCase):
    """Тесты вызова Graphviz (сам Graphviz подменяется)."""

    def test_command(self):
        """Программа dot вызывается с форматом SVG и именем файла."""
        with mock.patch("subprocess.run") as run:
            render_svg("digraph {}", "out.svg")
        args, kwargs = run.call_args
        self.assertEqual(args[0], ["dot", "-Tsvg", "-o", "out.svg"])
        self.assertEqual(kwargs["input"], "digraph {}")

    def test_not_installed(self):
        """Graphviz не установлен."""
        with mock.patch("subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(RenderError, "brew install"):
                render_svg("digraph {}", "out.svg")

    def test_dot_error(self):
        """Graphviz сообщил об ошибке."""
        error = subprocess.CalledProcessError(1, "dot", stderr="syntax\n")
        with mock.patch("subprocess.run", side_effect=error):
            with self.assertRaisesRegex(RenderError, "ошибкой: syntax"):
                render_svg("digraph {", "out.svg")

    def test_timeout(self):
        """Graphviz работал слишком долго."""
        error = subprocess.TimeoutExpired("dot", 1)
        with mock.patch("subprocess.run", side_effect=error):
            with self.assertRaisesRegex(RenderError, "время"):
                render_svg("digraph {}", "out.svg")


class AsciiTreeTest(unittest.TestCase):
    """Тесты ASCII-дерева."""

    def test_tree(self):
        """Ветви рисуются символами псевдографики."""
        lines = ascii_tree(make_graph({"A": ["B", "C"], "B": ["D"],
                                       "C": [], "D": []}))
        self.assertEqual(lines, [
            "A",
            "├── B",
            "│   └── D",
            "└── C",
        ])

    def test_repeated_package(self):
        """Уже показанный пакет не разворачивается повторно."""
        lines = ascii_tree(make_graph({"A": ["B", "C"], "B": ["D"],
                                       "C": ["D"], "D": ["E"], "E": []}))
        self.assertEqual(lines, [
            "A",
            "├── B",
            "│   └── D",
            "│       └── E",
            "└── C",
            "    └── D (*)",
        ])

    def test_cycle(self):
        """Связь, замыкающая цикл, помечается и не разворачивается."""
        lines = ascii_tree(make_graph({"A": ["B"], "B": ["A"]}))
        self.assertEqual(lines, ["A", "└── B", "    └── A (цикл)"])

    def test_self_cycle(self):
        """Пакет, зависящий сам от себя."""
        self.assertEqual(ascii_tree(make_graph({"A": ["A"]})),
                         ["A", "└── A (цикл)"])

    def test_single(self):
        """Дерево из одного пакета."""
        self.assertEqual(ascii_tree(make_graph({"A": []})), ["A"])

    def test_deep_chain_no_recursion(self):
        """Длинная цепочка выводится без рекурсии."""
        size = 2000
        edges = {f"P{i}": [f"P{i + 1}"] for i in range(size)}
        edges[f"P{size}"] = []
        lines = ascii_tree(make_graph(edges, root="P0"))
        self.assertEqual(len(lines), size + 1)
        self.assertTrue(lines[-1].endswith(f"└── P{size}"))


if __name__ == "__main__":
    unittest.main()
