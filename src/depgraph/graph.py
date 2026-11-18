"""Построение графа зависимостей с учётом транзитивности.

Граф строится обходом в ширину (BFS) с явной очередью, без рекурсии.
Каждый пакет загружается ровно один раз: уже встреченные пакеты
повторно в очередь не попадают, поэтому циклические зависимости
не приводят к бесконечному обходу. Сами циклы затем находятся
отдельно — обходом в глубину с явным стеком, тоже без рекурсии.
"""

from collections import deque
from dataclasses import dataclass, field

# Состояния вершины при поиске циклов.
VISITING = "visiting"
DONE = "done"


@dataclass
class DependencyGraph:
    """Граф зависимостей пакета.

    ``edges`` — для каждого пакета список его прямых зависимостей,
    пакеты идут в порядке обхода в ширину; ``depth`` — номер уровня
    BFS, на котором пакет был найден (у корня 0).
    """

    root: str
    edges: dict = field(default_factory=dict)
    depth: dict = field(default_factory=dict)

    def nodes(self):
        """Вернуть все пакеты графа в порядке обхода в ширину."""
        return list(self.edges)

    def edge_count(self):
        """Вернуть число связей «пакет → зависимость»."""
        return sum(len(children) for children in self.edges.values())


def build_graph(root, get_dependencies):
    """Построить граф зависимостей пакета обходом в ширину.

    :param root: имя анализируемого пакета.
    :param get_dependencies: функция, возвращающая список имён прямых
        зависимостей пакета по его имени.
    :return: объект :class:`DependencyGraph`.
    """
    graph = DependencyGraph(root)
    graph.depth[root] = 0
    # Имена пакетов NuGet не зависят от регистра: ключ — имя в нижнем
    # регистре, значение — написание, встреченное первым.
    names = {root.lower(): root}
    queue = deque([root])
    while queue:
        name = queue.popleft()
        children = []
        for dependency in get_dependencies(name):
            key = dependency.lower()
            # Новый пакет ставим в очередь; уже встреченный (в том числе
            # при цикле) только добавляем как связь.
            if key not in names:
                names[key] = dependency
                graph.depth[dependency] = graph.depth[name] + 1
                queue.append(dependency)
            child = names[key]
            if child not in children:
                children.append(child)
        graph.edges[name] = children
    return graph


def find_cycles(graph):
    """Найти циклические зависимости в графе.

    Используется обход в глубину с явным стеком: связь с пакетом,
    который сейчас находится на пути обхода, замыкает цикл.

    :return: список циклов, каждый — список имён, где первое
        и последнее имя совпадают, например ``['A', 'B', 'A']``.
    """
    state = {}
    cycles = []
    for start in graph.edges:
        if start in state:
            continue
        state[start] = VISITING
        path = [start]
        stack = [iter(graph.edges[start])]
        while stack:
            child = next(stack[-1], None)
            if child is None:
                # Все зависимости пакета обработаны — уходим с пути.
                state[path.pop()] = DONE
                stack.pop()
            elif state.get(child) == VISITING:
                cycles.append(path[path.index(child):] + [child])
            elif child not in state:
                state[child] = VISITING
                path.append(child)
                stack.append(iter(graph.edges[child]))
    return cycles


def format_graph(graph):
    """Сформировать строки вывода графа и найденных циклов."""
    lines = [
        f"Граф зависимостей пакета {graph.root}: "
        f"пакетов {len(graph.edges)}, связей {graph.edge_count()}"
    ]
    for name in graph.nodes():
        children = ", ".join(graph.edges[name]) or "(нет зависимостей)"
        lines.append(f"  [{graph.depth[name]}] {name} -> {children}")
    cycles = find_cycles(graph)
    if not cycles:
        lines.append("Циклических зависимостей нет")
        return lines
    lines.append(f"Циклические зависимости: {len(cycles)}")
    lines.extend("  " + " -> ".join(cycle) for cycle in cycles)
    return lines
