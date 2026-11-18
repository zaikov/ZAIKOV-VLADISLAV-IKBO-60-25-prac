"""Визуализация графа зависимостей: Graphviz, SVG и ASCII-дерево.

Текстовое описание графа формируется на языке DOT (Graphviz),
а изображение SVG строит внешняя программа ``dot`` из пакета
Graphviz. Связи, входящие в циклы, выделяются красным цветом.
"""

import subprocess

from depgraph.graph import find_cycles

DOT_COMMAND = "dot"
RENDER_TIMEOUT = 60
ROOT_COLOR = "#c6dafc"
NODE_COLOR = "#eef3fb"
CYCLE_COLOR = "#d93025"
# Символы для рисования ASCII-дерева.
BRANCH = "├── "
LAST_BRANCH = "└── "
PIPE = "│   "
SPACE = "    "
REPEAT_MARK = " (*)"
CYCLE_MARK = " (цикл)"


class RenderError(Exception):
    """Ошибка построения изображения графа программой Graphviz."""


def quote(name):
    """Записать имя пакета как строку DOT в двойных кавычках."""
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def cycle_edges(graph):
    """Вернуть множество связей ``(пакет, зависимость)`` из циклов."""
    edges = set()
    for cycle in find_cycles(graph):
        # Цикл [A, B, C, A] состоит из связей A->B, B->C, C->A.
        edges.update(zip(cycle, cycle[1:]))
    return edges


def to_dot(graph):
    """Сформировать описание графа на языке Graphviz DOT.

    :param graph: объект :class:`~depgraph.graph.DependencyGraph`.
    :return: текст на языке DOT.
    """
    in_cycle = cycle_edges(graph)
    lines = [
        f"digraph {quote(graph.root)} {{",
        "    rankdir=TB;",
        f'    node [shape=box, style="rounded,filled", '
        f'fillcolor="{NODE_COLOR}", fontname="Helvetica"];',
        '    edge [color="#5f6368"];',
        f'    {quote(graph.root)} [fillcolor="{ROOT_COLOR}", penwidth=2];',
    ]
    for name in graph.nodes():
        # Пакет без зависимостей и без входящих связей иначе
        # не попал бы на рисунок — описываем каждую вершину явно.
        lines.append(f"    {quote(name)};")
        for child in graph.edges[name]:
            style = ""
            if (name, child) in in_cycle:
                style = f' [color="{CYCLE_COLOR}", penwidth=2]'
            lines.append(f"    {quote(name)} -> {quote(child)}{style};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_svg(dot_text, output_file):
    """Построить изображение SVG по описанию DOT программой Graphviz.

    :param dot_text: описание графа на языке DOT.
    :param output_file: путь к файлу SVG.
    :raises RenderError: если Graphviz не установлен или завершился
        с ошибкой.
    """
    command = [DOT_COMMAND, "-Tsvg", "-o", output_file]
    try:
        subprocess.run(
            command, input=dot_text, text=True, capture_output=True,
            check=True, timeout=RENDER_TIMEOUT,
        )
    except FileNotFoundError:
        raise RenderError(
            "не найдена программа Graphviz 'dot' — установите Graphviz "
            "(macOS: brew install graphviz)"
        ) from None
    except subprocess.CalledProcessError as error:
        details = error.stderr.strip() or f"код {error.returncode}"
        message = f"Graphviz завершился с ошибкой: {details}"
        raise RenderError(message) from None
    except subprocess.TimeoutExpired:
        message = "Graphviz не уложился в отведённое время"
        raise RenderError(message) from None


def ascii_tree(graph):
    """Сформировать строки ASCII-дерева зависимостей.

    Дерево разворачивается от анализируемого пакета обходом в глубину
    с явным стеком. Пакет, уже показанный выше, повторно
    не разворачивается и помечается ``(*)``; связь, замыкающая цикл,
    помечается ``(цикл)``.
    """
    lines = []
    shown = set()
    # Элемент стека: (пакет, отступ, последний ли у родителя, предки).
    stack = [(graph.root, None, True, ())]
    while stack:
        name, prefix, last, ancestors = stack.pop()
        lines.append(tree_line(name, prefix, last, ancestors, shown))
        if name in ancestors or name in shown:
            continue
        shown.add(name)
        child_prefix = "" if prefix is None else (
            prefix + (SPACE if last else PIPE)
        )
        children = graph.edges[name]
        last_index = len(children) - 1
        # Кладём в стек в обратном порядке, чтобы первая зависимость
        # оказалась наверху стека и была выведена первой.
        for index, child in reversed(list(enumerate(children))):
            stack.append((
                child, child_prefix, index == last_index,
                ancestors + (name,),
            ))
    return lines


def tree_line(name, prefix, last, ancestors, shown):
    """Сформировать одну строку ASCII-дерева."""
    if prefix is None:
        return name
    mark = ""
    if name in ancestors:
        mark = CYCLE_MARK
    elif name in shown:
        mark = REPEAT_MARK
    return f"{prefix}{LAST_BRANCH if last else BRANCH}{name}{mark}"
