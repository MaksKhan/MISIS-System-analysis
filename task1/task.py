from typing import List, Tuple
import csv
from io import StringIO

def main(s: str, e: str) -> Tuple[
    List[List[bool]],
    List[List[bool]],
    List[List[bool]],
    List[List[bool]],
    List[List[bool]]
]:
    """
    Обрабатывает CSV-строку с ребрами ориентированного дерева и возвращает матрицы смежности
    для пяти иерархических отношений.

    Args:
        s: CSV-строка, содержащая список ребер в формате "parent,child\nparent,child\n..."
        e: Идентификатор корневого узла

    Returns:
        Tuple из 5 матриц смежности (List[List[bool]]) для отношений:
        r1
        r2
        r3
        r4
        r5
    """
    # Парсим CSV-строку
    reader = csv.reader(StringIO(s.strip()))
    edges = []
    vertices = set()

    for row in reader:
        if len(row) == 2:
            parent, child = row[0].strip(), row[1].strip()
            edges.append((parent, child))
            vertices.add(parent)
            vertices.add(child)

    # Список вершин и их индексы
    vertex_list = sorted(vertices)
    n = len(vertex_list)
    vertex_to_index = {v: i for i, v in enumerate(vertex_list)}

    r1 = [[False]*n for _ in range(n)]
    r2 = [[False]*n for _ in range(n)]
    r3 = [[False]*n for _ in range(n)]
    r4 = [[False]*n for _ in range(n)]
    r5 = [[False]*n for _ in range(n)]

    children = {v: [] for v in vertices}
    parents = {v: None for v in vertices}
    for parent, child in edges:
        children[parent].append(child)
        parents[child] = parent

    # r1
    for parent, child in edges:
        i, j = vertex_to_index[parent], vertex_to_index[child]
        r1[i][j] = True

    # r2
    for parent, child in edges:
        i, j = vertex_to_index[parent], vertex_to_index[child]
        r2[j][i] = True

    def get_all_descendants(node, visited=None):
        if visited is None:
            visited = set()
        if node in visited:
            return set()
        visited.add(node)
        result = set()
        for c in children[node]:
            result.add(c)
            result |= get_all_descendants(c, visited)
        return result

    # r3
    for v in vertices:
        i = vertex_to_index[v]
        for desc in get_all_descendants(v):
            j = vertex_to_index[desc]
            r3[i][j] = True

    # r4
    for v in vertices:
        j = vertex_to_index[v]
        curr = parents[v]
        while curr is not None:
            i = vertex_to_index[curr]
            r4[j][i] = True
            curr = parents[curr]

    # r5
    siblings = {}
    for v in vertices:
        p = parents[v]
        if p is not None:
            siblings.setdefault(p, []).append(v)
    for group in siblings.values():
        for u in group:
            for v in group:
                if u != v:
                    r5[vertex_to_index[u]][vertex_to_index[v]] = True

    return r1, r2, r3, r4, r5

if __name__ == "__main__":
    csv_data = "1,2\n1,3\n3,4\n3,5"
    matrices = main(csv_data, "1")
    names = ["r1", "r2", "r3", "r4", "r5"]
    for name, mat in zip(names, matrices):
        print(f"{name}:")
        for row in mat:
            print([int(x) for x in row])
        print()
