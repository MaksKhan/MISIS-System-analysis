from typing import List, Tuple
import csv
from io import StringIO
import math

def main(s: str, e: str) -> Tuple[float, float]:
    """
    Рассчитывает энтропию структуры графа и нормированную оценку структурной сложности.
    
    Args:
        s: CSV-строка с ребрами в формате "parent,child\nparent,child\n..."
        e: Идентификатор корневого узла
    
    Returns:
        Tuple[float, float]: (энтропия структуры, нормированная сложность), округлены до 1 знака
    """
    reader = csv.reader(StringIO(s.strip()))
    edges = []
    vertices = set()

    for row in reader:
        if len(row) == 2:
            parent, child = row[0].strip(), row[1].strip()
            edges.append((parent, child))
            vertices.add(parent)
            vertices.add(child)

    vertex_list = sorted(vertices)
    n = len(vertex_list)
    vertex_to_index = {v: i for i, v in enumerate(vertex_list)}

    # матрицы смежности (r1, r2, r3, r4, r5)
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

    # Все пять матриц
    matrices = [r1, r2, r3, r4, r5]

    l = [[0] * n for _ in range(5)]
    
    for rel_idx, matrix in enumerate(matrices):
        for j in range(n):
            count = sum(1 for i in range(n) if matrix[i][j])
            l[rel_idx][j] = count

    k = n - 1
    
    total_entropy = 0.0
    
    for j in range(n):
        for rel_idx in range(5):
            lij = l[rel_idx][j]
            p = lij / k if k > 0 else 0
            if p > 0:
                partial_entropy = -p * math.log2(p)
                total_entropy += partial_entropy

    c = 1.0 / (math.e * math.log(2))
    h_ref = c * n * k
    normalized_complexity = total_entropy / h_ref if h_ref > 0 else 0.0

    entropy_rounded = round(total_entropy, 1)
    normalized_rounded = round(normalized_complexity, 1)

    return (entropy_rounded, normalized_rounded)


if __name__ == "__main__":
    csv_data = "1,2\n1,3\n3,4\n3,5"
    result = main(csv_data, "1")
    print(f"Энтропия: {result[0]}, Нормированная сложность: {result[1]}")
