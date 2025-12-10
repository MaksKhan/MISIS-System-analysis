# task3/task.py
import json
from typing import Any, Dict, List, Set


def _normalize_ranking(obj: Any) -> List[List[Any]]:
    """
    Преобразует ранжировку из JSON-формата в список списков (кластеры).
    Примеры:
      [1, [2, 3], 4] -> [[1], [2, 3], [4]]
      ["1", "2", ["3", "4"]] -> [["1"], ["2"], ["3", "4"]]
    """
    if not isinstance(obj, list):
        raise ValueError("Ожидался список на верхнем уровне JSON")

    clusters: List[List[Any]] = []
    for block in obj:
        if isinstance(block, list):
            clusters.append(list(block))
        else:
            clusters.append([block])
    return clusters


def _collect_items(r1: List[List[Any]], r2: List[List[Any]]) -> List[Any]:
    """
    Собирает множество всех объектов из обеих ранжировок
    и возвращает их в фиксированном порядке.
    Порядок: сначала те, что приводятся к int (по возрастанию),
    затем остальные (лексикографически по str).
    """
    items_set: Set[Any] = set()
    for cl in r1:
        items_set.update(cl)
    for cl in r2:
        items_set.update(cl)

    def _key(x: Any):
        try:
            return (0, int(x))
        except Exception:
            return (1, str(x))

    return sorted(items_set, key=_key)


def _build_position_map(r: List[List[Any]]) -> Dict[Any, int]:
    """
    Для каждой альтернативы возвращает индекс кластера (позицию в ранжировке).
    """
    pos: Dict[Any, int] = {}
    for idx, cl in enumerate(r):
        for x in cl:
            pos[x] = idx
    return pos


def _build_relation_matrix(items: List[Any],
                           ranking: List[List[Any]]) -> List[List[int]]:
    """
    Строит матрицу отношения Y (квазипорядок «не хуже»)
    по кластерной ранжировке. Для объектов xi, xj:
      y_ij = 1, если позиция(xi) <= позиция(xj) (xi не хуже xj, включая равенство/кластер),
      y_ij = 0 иначе.
    На диагонали всегда 1.
    """
    n = len(items)
    pos = _build_position_map(ranking)

    # если какой-то объект отсутствует в ранжировке (на практике не должно быть),
    # считаем его в конце
    default_pos = len(ranking)

    Y = [[0] * n for _ in range(n)]
    for i, xi in enumerate(items):
        pi = pos.get(xi, default_pos)
        for j, xj in enumerate(items):
            if i == j:
                Y[i][j] = 1
            else:
                pj = pos.get(xj, default_pos)
                Y[i][j] = 1 if pi <= pj else 0
    return Y


def _transpose(M: List[List[int]]) -> List[List[int]]:
    n = len(M)
    return [[M[j][i] for j in range(n)] for i in range(n)]


def _boolean_product(A: List[List[int]],
                     B: List[List[int]]) -> List[List[int]]:
    """
    Булево произведение матриц A и B:
      (A ◦ B)_ij = OR_k (A_ik AND B_kj)
    """
    n = len(A)
    res = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            val = 0
            for k in range(n):
                if A[i][k] and B[k][j]:
                    val = 1
                    break
            res[i][j] = val
    return res


def _boolean_or(A: List[List[int]],
                B: List[List[int]]) -> List[List[int]]:
    n = len(A)
    res = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            res[i][j] = 1 if (A[i][j] or B[i][j]) else 0
    return res


def _transitive_closure(M: List[List[int]]) -> List[List[int]]:
    """
    Транзитивное замыкание булевой матрицы (алгоритм Уоршелла).
    """
    n = len(M)
    closure = [row[:] for row in M]
    for k in range(n):
        for i in range(n):
            if closure[i][k]:
                row_i = closure[i]
                row_k = closure[k]
                for j in range(n):
                    if row_k[j]:
                        row_i[j] = 1
    return closure


def _find_components_from_matrix(E_star: List[List[int]]) -> List[Set[int]]:
    """
    Выделяет компоненты связности по матрице эквивалентности E*.
    Считаем, что i и j в одном кластере, если E*[i][j] = E*[j][i] = 1.
    """
    n = len(E_star)
    visited = [False] * n
    components: List[Set[int]] = []

    for start in range(n):
        if visited[start]:
            continue
        comp: Set[int] = set()
        stack = [start]
        visited[start] = True
        while stack:
            v = stack.pop()
            comp.add(v)
            for u in range(n):
                if not visited[u] and E_star[v][u] and E_star[u][v]:
                    visited[u] = True
                    stack.append(u)
        components.append(comp)

    return components


def _build_cluster_order(components: List[Set[int]],
                         C: List[List[int]]) -> List[Set[int]]:
    """
    Строит порядок между кластерами по матрице C.
    Для двух кластеров A и B:
      A < B, если есть i∈A, j∈B с C_ij = 1 и C_ji = 0,
      и нет ни одной пары, дающей строгое предпочтение в обратную сторону.
    Затем выполняется топологическая сортировка кластеров.
    """
    m = len(components)
    edges = {i: set() for i in range(m)}
    indeg = [0] * m

    # вспомогательная функция сравнения двух кластеров
    def compare_clusters(a_idx: int, b_idx: int):
        A = components[a_idx]
        B = components[b_idx]
        a_before_b = False
        b_before_a = False

        for i in A:
            for j in B:
                if C[i][j] and not C[j][i]:
                    a_before_b = True
                if C[j][i] and not C[i][j]:
                    b_before_a = True
                if a_before_b and b_before_a:
                    # оба направления есть, считаем их непредпочитаемыми
                    return None

        if a_before_b and not b_before_a:
            return "A<B"
        if b_before_a and not a_before_b:
            return "B<A"
        return None

    # строим ориентированный ацикличный граф кластеров
    for i in range(m):
        for j in range(m):
            if i == j:
                continue
            rel = compare_clusters(i, j)
            if rel == "A<B":
                if j not in edges[i]:
                    edges[i].add(j)
            elif rel == "B<A":
                if i not in edges[j]:
                    edges[j].add(i)

    # пересчитать входящие степени
    indeg = [0] * m
    for i in range(m):
        for j in edges[i]:
            indeg[j] += 1

    # топологическая сортировка (Кана)
    order: List[int] = []
    queue = [i for i in range(m) if indeg[i] == 0]

    while queue:
        v = queue.pop(0)
        order.append(v)
        for u in edges[v]:
            indeg[u] -= 1
            if indeg[u] == 0:
                queue.append(u)

    if len(order) != m:
        # На всякий случай, если что-то пошло не так, вернем в исходном порядке
        return components

    return [components[i] for i in order]


def main(json_rank_1: str, json_rank_2: str) -> str:
    """
    json_rank_1, json_rank_2 – JSON-строки с кластерными ранжировками.
    Пример формата:
        "[1, [2, 3], 4, [5, 6, 7], 8, 9, 10]"
    или
        "[\"1\", \"2\", [\"3\", \"4\"]]"

    Возвращает JSON-строку вида:
    {
      "stage1": {
        "contradiction_core": [[...], [...]]
      },
      "stage2": {
        "cluster_ranking": [1, 2, 3, [4, 5], 6, ...]
      }
    }
    При необходимости можно изменить в конце, чтобы возвращать только
    кластерную ранжировку (stage2["cluster_ranking"]).
    """
    # 1. Парсим входные JSON-строки
    r1_raw = json.loads(json_rank_1)
    r2_raw = json.loads(json_rank_2)

    r1 = _normalize_ranking(r1_raw)
    r2 = _normalize_ranking(r2_raw)

    # 2. Общее множество объектов и матрицы отношений YA, YB
    items = _collect_items(r1, r2)
    YA = _build_relation_matrix(items, r1)
    YB = _build_relation_matrix(items, r2)

    # 3. Шаг 2 алгоритма: матрица противоречий P и ядро противоречий S(A, B)
    YA_T = _transpose(YA)
    YB_T = _transpose(YB)

    P1 = _boolean_product(YA, YB_T)
    P2 = _boolean_product(YA_T, YB)
    P = _boolean_or(P1, P2)

    n = len(items)
    # множество пар индексов с pij = 0 (ядро противоречий)
    core_pairs: Set[tuple[int, int]] = set()
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if P[i][j] == 0:
                # работаем с неориентированной парой (min, max)
                pair = (min(i, j), max(i, j))
                core_pairs.add(pair)

    # Преобразуем ядро противоречий в кластеры объектов (компоненты связности по парам)
    # Граф только по вершинам, участвующим в противоречиях
    involved_vertices: Set[int] = set()
    for u, v in core_pairs:
        involved_vertices.add(u)
        involved_vertices.add(v)

    contradiction_components: List[List[Any]] = []
    if involved_vertices:
        visited = set()
        for v in involved_vertices:
            if v in visited:
                continue
            stack = [v]
            comp_idx: Set[int] = set()
            visited.add(v)
            while stack:
                cur = stack.pop()
                comp_idx.add(cur)
                for a, b in core_pairs:
                    if a == cur and b not in visited:
                        visited.add(b)
                        stack.append(b)
                    elif b == cur and a not in visited:
                        visited.add(a)
                        stack.append(a)
            # сортируем внутри кластера по исходному порядку items
            contradiction_components.append(
                [items[i] for i in sorted(comp_idx)]
            )

    # 4. Шаг 3: матрица согласованного порядка C = YA ◦ YB
    C = _boolean_product(YA, YB)

    # Для всех противоречивых пар делаем их эквивалентными: c_ij = c_ji = 1
    for i, j in core_pairs:
        C[i][j] = 1
        C[j][i] = 1

    # 5. Шаг 4: матрица эквивалентности E = C ◦ C^T, затем транзитивное замыкание E*
    C_T = _transpose(C)
    E = _boolean_product(C, C_T)
    E_star = _transitive_closure(E)

    # Кластеры – компоненты связности по E*
    components = _find_components_from_matrix(E_star)

    # 6. Шаг 5: упорядочивание кластеров
    ordered_components = _build_cluster_order(components, C)

    # 7. Формируем итоговую кластерную ранжировку
    cluster_ranking: List[Any] = []
    for comp in ordered_components:
        # элементы внутри кластера – по порядку индексов
        elems = [items[i] for i in sorted(comp)]
        if len(elems) == 1:
            cluster_ranking.append(elems[0])
        else:
            cluster_ranking.append(elems)

    result = {
        "stage1": {
            "contradiction_core": contradiction_components
        },
        "stage2": {
            "cluster_ranking": cluster_ranking
        }
    }

    # Если нужно возвращать только результат этапа 2, замените на:
    # return json.dumps(cluster_ranking, ensure_ascii=False)
    return json.dumps(result, ensure_ascii=False)
