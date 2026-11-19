"""Порядок загрузки зависимостей пакета.

Пакет можно загрузить только после того, как загружены все его
зависимости. Такой порядок — топологическая сортировка графа;
она выполняется алгоритмом Кана без рекурсии:

1. сначала загружаются пакеты без зависимостей;
2. после загрузки пакета у каждого зависящего от него пакета
   становится на одну незагруженную зависимость меньше;
3. пакет, у которого все зависимости загружены, ставится в очередь.

Если в графе есть цикл, пакеты цикла (и всё, что от них зависит)
так и не становятся готовыми: порядок для них определить нельзя.
Реальный менеджер NuGet в этом случае тоже завершается ошибкой.
"""

from collections import deque

from depgraph.graph import find_cycles


def load_order(graph):
    """Вычислить порядок загрузки пакетов графа.

    Пакеты без зависимостей готовы к загрузке сразу; они берутся
    в порядке обхода в ширину, чтобы результат был одинаковым
    при каждом запуске.

    :param graph: объект :class:`~depgraph.graph.DependencyGraph`.
    :return: кортеж ``(порядок, заблокированные)``: список пакетов
        в порядке загрузки и список пакетов, которые нельзя
        загрузить из-за циклических зависимостей.
    """
    waiting = count_dependencies(graph)
    dependents = find_dependents(graph)
    ready = deque(name for name in graph.nodes() if not waiting[name])
    order = []
    while ready:
        name = ready.popleft()
        order.append(name)
        ready.extend(release_dependents(name, dependents, waiting))
    blocked = [name for name in graph.nodes() if waiting[name]]
    return order, blocked


def count_dependencies(graph):
    """Вернуть для каждого пакета число его незагруженных зависимостей.

    В начале не загружена ни одна зависимость, поэтому это просто
    число прямых зависимостей пакета.
    """
    return {name: len(children) for name, children in graph.edges.items()}


def find_dependents(graph):
    """Построить обратные связи: какие пакеты зависят от данного."""
    dependents = {name: [] for name in graph.edges}
    for name, children in graph.edges.items():
        for child in children:
            dependents[child].append(name)
    return dependents


def release_dependents(name, dependents, waiting):
    """Отметить загрузку пакета ``name`` у зависящих от него пакетов.

    У каждого такого пакета становится на одну незагруженную
    зависимость меньше. Пакеты, у которых все зависимости загружены,
    становятся готовыми к загрузке.

    :param dependents: обратные связи из :func:`find_dependents`.
    :param waiting: счётчики из :func:`count_dependencies`, изменяются.
    :return: список пакетов, ставших готовыми.
    """
    released = []
    for parent in dependents[name]:
        waiting[parent] -= 1
        if not waiting[parent]:
            released.append(parent)
    return released


def format_load_order(graph):
    """Сформировать строки вывода порядка загрузки.

    :return: кортеж ``(строки, есть_ли_цикл)``.
    """
    order, blocked = load_order(graph)
    lines = [f"Порядок загрузки зависимостей пакета {graph.root}:"]
    for number, name in enumerate(order, start=1):
        mark = " (анализируемый пакет)" if name == graph.root else ""
        lines.append(f"  {number}. {name}{mark}")
    if not order:
        lines.append("  (ни один пакет нельзя загрузить)")
    if not blocked:
        return lines, False
    lines.append(
        "Порядок загрузки нельзя определить из-за циклических "
        "зависимостей для пакетов: " + ", ".join(blocked)
    )
    lines.extend("  " + " -> ".join(cycle) for cycle in find_cycles(graph))
    return lines, True
