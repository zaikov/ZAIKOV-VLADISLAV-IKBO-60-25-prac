"""Тесты построения графа зависимостей и поиска циклов."""

import unittest

from depgraph.graph import build_graph, find_cycles, format_graph


def lookup(edges):
    """Вернуть функцию получения зависимостей из словаря ``edges``."""
    return lambda name: edges[name]


class BuildGraphTest(unittest.TestCase):
    """Тесты обхода в ширину."""

    def test_transitive(self):
        """В граф попадают и транзитивные зависимости."""
        graph = build_graph("A", lookup({"A": ["B"], "B": ["C"], "C": []}))
        self.assertEqual(graph.nodes(), ["A", "B", "C"])
        self.assertEqual(graph.edges["B"], ["C"])

    def test_bfs_order_and_depth(self):
        """Пакеты обходятся по уровням, уровень — расстояние от корня."""
        edges = {"A": ["B", "C"], "B": ["D"], "C": ["E"], "D": [], "E": []}
        graph = build_graph("A", lookup(edges))
        self.assertEqual(graph.nodes(), ["A", "B", "C", "D", "E"])
        self.assertEqual(graph.depth, {"A": 0, "B": 1, "C": 1, "D": 2,
                                       "E": 2})

    def test_shared_dependency_loaded_once(self):
        """Общая зависимость загружается один раз."""
        calls = []
        edges = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}

        def source(name):
            """Запомнить вызов и вернуть зависимости."""
            calls.append(name)
            return edges[name]
        graph = build_graph("A", source)
        self.assertEqual(calls, ["A", "B", "C", "D"])
        self.assertEqual(graph.edge_count(), 4)

    def test_cycle_terminates(self):
        """Цикл не приводит к бесконечному обходу."""
        graph = build_graph("A", lookup({"A": ["B"], "B": ["A"]}))
        self.assertEqual(graph.nodes(), ["A", "B"])
        self.assertEqual(graph.edges["B"], ["A"])

    def test_case_insensitive_names(self):
        """Имена NuGet сравниваются без учёта регистра."""
        edges = {"Root": ["Lib", "lib"], "Lib": ["ROOT"]}
        graph = build_graph("Root", lookup(edges))
        self.assertEqual(graph.nodes(), ["Root", "Lib"])
        self.assertEqual(graph.edges["Root"], ["Lib"])
        self.assertEqual(graph.edges["Lib"], ["Root"])

    def test_no_recursion_on_deep_graph(self):
        """Длинная цепочка не упирается в предел глубины рекурсии."""
        size = 5000
        edges = {f"P{i}": [f"P{i + 1}"] for i in range(size)}
        edges[f"P{size}"] = []
        graph = build_graph("P0", lookup(edges))
        self.assertEqual(len(graph.nodes()), size + 1)

    def test_source_error_propagates(self):
        """Ошибка получения зависимостей передаётся вызывающему коду."""
        def source(name):
            """Сообщить об ошибке для любого пакета."""
            raise LookupError(name)
        with self.assertRaises(LookupError):
            build_graph("A", source)


class FindCyclesTest(unittest.TestCase):
    """Тесты поиска циклических зависимостей."""

    def cycles(self, edges, root="A"):
        """Построить граф и вернуть найденные циклы."""
        return find_cycles(build_graph(root, lookup(edges)))

    def test_no_cycles(self):
        """Ромбовидный граф без циклов."""
        edges = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        self.assertEqual(self.cycles(edges), [])

    def test_self_cycle(self):
        """Пакет зависит сам от себя."""
        self.assertEqual(self.cycles({"A": ["A"]}), [["A", "A"]])

    def test_three_packages(self):
        """Цикл из трёх пакетов."""
        edges = {"A": ["B"], "B": ["C"], "C": ["A"]}
        self.assertEqual(self.cycles(edges), [["A", "B", "C", "A"]])

    def test_several_cycles(self):
        """Несколько циклов в одном графе."""
        edges = {"A": ["B", "C"], "B": ["A"], "C": ["D"], "D": ["C"]}
        self.assertEqual(
            self.cycles(edges), [["A", "B", "A"], ["C", "D", "C"]]
        )

    def test_deep_cycle_no_recursion(self):
        """Длинный цикл обрабатывается без рекурсии."""
        size = 5000
        edges = {f"P{i}": [f"P{(i + 1) % size}"] for i in range(size)}
        cycles = find_cycles(build_graph("P0", lookup(edges)))
        self.assertEqual(len(cycles[0]), size + 1)


class FormatGraphTest(unittest.TestCase):
    """Тесты вывода графа."""

    def test_output(self):
        """Вывод содержит уровни, связи и циклы."""
        graph = build_graph("A", lookup({"A": ["B"], "B": ["A", "C"],
                                         "C": []}))
        lines = format_graph(graph)
        self.assertEqual(
            lines[0], "Граф зависимостей пакета A: пакетов 3, связей 3"
        )
        self.assertIn("  [1] B -> A, C", lines)
        self.assertIn("  [2] C -> (нет зависимостей)", lines)
        self.assertEqual(lines[-1], "  A -> B -> A")

    def test_no_cycles_message(self):
        """Если циклов нет, об этом сообщается."""
        lines = format_graph(build_graph("A", lookup({"A": []})))
        self.assertEqual(lines[-1], "Циклических зависимостей нет")


if __name__ == "__main__":
    unittest.main()
