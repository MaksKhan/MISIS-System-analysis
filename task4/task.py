# file: task.py
import ast
import json


def load_data(raw):
    if isinstance(raw, (dict, list)):
        return raw

    text = raw.strip()
    try:
        return json.loads(text)
    except Exception:
        return ast.literal_eval(text)


def canon_term(value):
    if value is None:
        return value

    token = str(value).strip().lower()
    mapping = {
        "нормально": "комфортно",
        "комф": "комфортно",
        "слабо": "слабый",
        "слаб": "слабый",
        "умеренно": "умеренный",
        "умерен": "умеренный",
        "интенсивно": "интенсивный",
        "интенс": "интенсивный",
    }
    return mapping.get(token, token)


def _clip01(x):
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def interp_membership(x, points):
    if not points:
        return 0.0

    pts = [(float(a), float(b)) for a, b in points]
    pts.sort(key=lambda p: p[0])

    x0, y0 = pts[0]
    xn, yn = pts[-1]

    if x <= x0:
        return _clip01(y0)
    if x >= xn:
        return _clip01(yn)

    same_x = [y for px, y in pts if px == x]
    if same_x:
        return _clip01(max(same_x))

    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if x1 <= x <= x2:
            if x2 == x1:
                return _clip01(max(y1, y2))
            frac = (x - x1) / (x2 - x1)
            return _clip01(y1 + frac * (y2 - y1))

    return 0.0


def index_terms(container, var_name):
    result = {}
    for row in container[var_name]:
        key = canon_term(row.get("id"))
        result[key] = row.get("points")
    return result


def solve(temperature_json, heating_json, rules_json, t_current):
    temp_obj = load_data(temperature_json)
    heat_obj = load_data(heating_json)
    rules = load_data(rules_json)

    temp_terms = index_terms(temp_obj, "температура")
    heat_terms = index_terms(heat_obj, "уровень нагрева")

    t = float(t_current)
    mu_temp = {name: interp_membership(t, pts) for name, pts in temp_terms.items()}

    grid_xs = []
    for pts in heat_terms.values():
        for px, _ in pts:
            grid_xs.append(float(px))

    s_min, s_max = min(grid_xs), max(grid_xs)
    if s_max < s_min:
        s_min, s_max = s_max, s_min

    span = s_max - s_min
    if span == 0:
        return float(s_min)

    n = 10000
    step = span / n
    agg = [0.0] * (n + 1)

    for rule in rules:
        ant = canon_term(rule[0])
        cons = canon_term(rule[1])

        alpha = float(mu_temp[ant])
        if alpha <= 0.0:
            continue

        cons_pts = heat_terms[cons]
        for i in range(n + 1):
            s = s_min + step * i
            mu_cons = interp_membership(s, cons_pts)
            mu_rule = alpha if alpha < mu_cons else mu_cons
            if mu_rule > agg[i]:
                agg[i] = mu_rule

    max_mu = max(agg) if agg else 0.0
    eps = 1e-12
    for i, v in enumerate(agg):
        if v >= max_mu - eps:
            return float(s_min + step * i)

    return float(s_min)


if __name__ == "__main__":
    from constants import HEAT, TEMP

    t = solve(
        TEMP,
        HEAT,
        "[['холодно','интенсивно'],['нормально','умеренно'],['жарко','слабо']]",
        21.0,
    )
    print(t)
