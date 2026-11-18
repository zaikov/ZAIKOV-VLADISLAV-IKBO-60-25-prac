"""Тесты вычисления порядка загрузки зависимостей."""

import unittest

from depgraph.graph import build_graph
from depgraph.order import format_load_order, load_order


def make_graph(edges, root="A"):
    """Построить граф по словарю ``{пакет: [зависимости]}``."""
    return build_graph(root, lambda name: edges[name])


class LoadOrderTest(unittest.TestCase):
    """Тесты топологической сортировки."""

    def assert_dependencies_first(self, edges, order):
        """Проверить, что каждый пакет идёт после своих зависимостей."""
        position = {name: index for index, name in enumerate(order)}
        for name, children in edges.items():
            for child in children:
                if name in position:
                    self.assertLess(position[child], position[name])

    def test_single(self):
        """Пакет без зависимостей."""
        self.assertEqual(load_order(make_graph({"A": []})), (["A"], []))

    def test_chain(self):
        """Цепочка загружается с конца."""
        edges = {"A": ["B"], "B": ["C"], "C": []}
        self.assertEqual(load_order(make_graph(edges)), (["C", "B", "A"], []))

    def test_shared_dependency(self):
        """Общая зависимость загружается один раз и раньше всех."""
        edges = {"A": ["B", "C"], "B": ["D"], "C": ["D", "E"], "D": [],
                 "E": []}
        order, blocked = load_order(make_graph(edges))
        self.assertEqual(order, ["D", "E", "B", "C", "A"])
        self.assertEqual(blocked, [])
        self.assert_dependencies_first(edges, order)

    def test_diamond(self):
        """Многоуровневый ромб."""
        edges = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": ["E"],
                 "E": []}
        order, _ = load_order(make_graph(edges))
        self.assertEqual(order, ["E", "D", "B", "C", "A"])
        self.assert_dependencies_first(edges, order)

    def test_root_is_last(self):
        """Анализируемый пакет загружается последним."""
        edges = {"A": ["B", "C"], "B": ["C"], "C": []}
        order, _ = load_order(make_graph(edges))
        self.assertEqual(order[-1], "A")

    def test_cycle_blocks_packages(self):
        """Пакеты цикла и зависящие от них не получают места."""
        edges = {"A": ["B", "D"], "B": ["C"], "C": ["B"], "D": []}
        order, blocked = load_order(make_graph(edges))
        self.assertEqual(order, ["D"])
        self.assertEqual(blocked, ["A", "B", "C"])

    def test_self_cycle(self):
        """Пакет, зависящий сам от себя."""
        order, blocked = load_order(make_graph({"A": ["A", "B"], "B": []}))
        self.assertEqual(order, ["B"])
        self.assertEqual(blocked, ["A"])

    def test_long_chain_no_recursion(self):
        """Длинная цепочка обрабатывается без рекурсии."""
        size = 5000
        edges = {f"P{i}": [f"P{i + 1}"] for i in range(size)}
        edges[f"P{size}"] = []
        order, _ = load_order(make_graph(edges, root="P0"))
        self.assertEqual(order[0], f"P{size}")
        self.assertEqual(order[-1], "P0")


class FormatLoadOrderTest(unittest.TestCase):
    """Тесты вывода порядка загрузки."""

    def test_output(self):
        """Нумерованный список, анализируемый пакет отмечен."""
        lines, has_cycle = format_load_order(
            make_graph({"A": ["B"], "B": []})
        )
        self.assertFalse(has_cycle)
        self.assertEqual(lines, [
            "Порядок загрузки зависимостей пакета A:",
            "  1. B",
            "  2. A (анализируемый пакет)",
        ])

    def test_cycle_output(self):
        """При цикле выводятся заблокированные пакеты и сам цикл."""
        lines, has_cycle = format_load_order(
            make_graph({"A": ["B"], "B": ["A"]})
        )
        self.assertTrue(has_cycle)
        self.assertIn("для пакетов: A, B", lines[-2])
        self.assertEqual(lines[-1], "  A -> B -> A")


if __name__ == "__main__":
    unittest.main()
