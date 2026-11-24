"""Dibuja un autómata como SVG con la apariencia de una captura de JFLAP (tema oscuro).

Estados: círculo verde oliva con borde gris, etiqueta qN; inicial: triángulo hueco;
final: doble círculo; transiciones: líneas grises finas con punta abierta, la etiqueta
junto a la curva y el lazo sobre el estado. ε se muestra como λ, igual que JFLAP.
"""
from html import escape
from math import hypot

R = 20                       # radio de estado (JFLAP)
DX, DY = 150, 100            # separación entre columnas / filas
MARGEN_X, MARGEN_Y = 70, 70

C_FONDO, C_ESTADO = "#212121", "#3b3b0d"
C_BORDE, C_LINEA, C_TEXTO = "#cfcfcf", "#b4b4b4", "#e6e6e6"
FUENTE = "DejaVu Sans, Dialog, Arial, sans-serif"


def _capas(inicio, aristas):
    """Capa = camino más largo desde el inicio ignorando las aristas de retroceso (ciclos)."""
    sal = {}
    for u, v, _ in aristas:
        sal.setdefault(u, []).append(v)
    estado, atras, orden = {inicio: 1}, set(), []
    pila = [(inicio, iter(sal.get(inicio, [])))]
    while pila:
        u, it = pila[-1]
        for v in it:
            if estado.get(v) == 1:
                atras.add((u, v))
            elif v not in estado:
                estado[v] = 1
                pila.append((v, iter(sal.get(v, []))))
                break
        else:
            estado[u] = 2
            orden.append(u)
            pila.pop()
    prof = {u: 0 for u in estado}
    for u in reversed(orden):
        for v in sal.get(u, []):
            if (u, v) not in atras and v != u:
                prof[v] = max(prof[v], prof[u] + 1)
    return prof


def _hacia(x, y, cx, cy, r):
    d = hypot(cx - x, cy - y) or 1
    return x + (cx - x) * r / d, y + (cy - y) * r / d


def _tapado(p, q, pos, excepto):
    """¿Algún otro estado queda sobre el segmento p-q?"""
    (x1, y1), (x2, y2) = p, q
    L2 = (x2 - x1) ** 2 + (y2 - y1) ** 2 or 1
    for i, (x, y) in pos.items():
        if i in excepto:
            continue
        t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / L2))
        if hypot(x - (x1 + t * (x2 - x1)), y - (y1 + t * (y2 - y1))) < R + 8:
            return True
    return False


def _texto(x, y, t):
    return ('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="13" fill="%s" font-family="%s">%s</text>'
            % (x, y, C_TEXTO, FUENTE, escape(t)))


def svg_automata(nombres, inicio, finales, aristas, uid):
    """nombres: etiqueta por índice de estado; aristas: [(u, v, etiqueta)] con índices."""
    prof = _capas(inicio, aristas)
    for i in range(len(nombres)):          # estados inalcanzables (no deberían existir)
        prof.setdefault(i, 0)
    filas = {}
    for i in sorted(prof, key=lambda i: (prof[i], i)):
        filas.setdefault(prof[i], []).append(i)
    alto_max = max(len(f) for f in filas.values())
    pos = {}
    for d, miembros in filas.items():
        for k, i in enumerate(miembros):
            pos[i] = (MARGEN_X + d * DX, MARGEN_Y + (alto_max - len(miembros)) * DY / 2 + k * DY)

    pares = {}
    for u, v, e in aristas:
        pares.setdefault((u, v), []).append("λ" if e == "ε" else e)

    cuerpo, xs, ys = [], [x for x, _ in pos.values()], [y for _, y in pos.values()]
    for (u, v), etqs in pares.items():
        etq = ",".join(dict.fromkeys(etqs)).replace(", ", ",")
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        if u == v:
            a = "M %.1f %.1f C %.1f %.1f %.1f %.1f %.1f %.1f" % (
                x1 - 12, y1 - R * 0.8, x1 - 26, y1 - R - 38, x1 + 26, y1 - R - 38, x1 + 12, y1 - R * 0.8 - 1)
            cuerpo.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.2" marker-end="url(#%s-f)"/>'
                          % (a, C_LINEA, uid))
            cuerpo.append(_texto(x1, y1 - R - 34, etq))
            ys.append(y1 - R - 40)
            continue
        L = hypot(x2 - x1, y2 - y1)
        nx, ny = (y2 - y1) / L, -(x2 - x1) / L          # normal a la izquierda de u→v
        if nx * 0 + ny > 0 or (abs(ny) < 1e-6 and nx < 0):  # preferir curvar hacia arriba/derecha
            pass
        inverso = (v, u) in pares
        retroceso = prof[v] <= prof[u]
        tapado = _tapado((x1, y1), (x2, y2), pos, (u, v))
        if inverso or retroceso or tapado:
            off = max(34, 0.28 * L) if (inverso and not tapado) else max(44, 0.4 * L)
            if retroceso and not inverso:
                off = max(44, 0.4 * L)
            cx, cy = (x1 + x2) / 2 + nx * 2 * off, (y1 + y2) / 2 + ny * 2 * off
            sx, sy = _hacia(x1, y1, cx, cy, R)
            ex, ey = _hacia(x2, y2, cx, cy, R + 2)
            camino = "M %.1f %.1f Q %.1f %.1f %.1f %.1f" % (sx, sy, cx, cy, ex, ey)
            px, py = (sx + 2 * cx + ex) / 4, (sy + 2 * cy + ey) / 4
            lx, ly = px + nx * 9, py + ny * 9 + 4
            xs.append(px); ys.append(py)
        else:
            sx, sy = _hacia(x1, y1, x2, y2, R)
            ex, ey = _hacia(x2, y2, x1, y1, R + 2)
            camino = "M %.1f %.1f L %.1f %.1f" % (sx, sy, ex, ey)
            lx, ly = (sx + ex) / 2 + nx * 9, (sy + ey) / 2 + ny * 9 + 4
        cuerpo.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.2" marker-end="url(#%s-f)"/>'
                      % (camino, C_LINEA, uid))
        cuerpo.append(_texto(lx, ly, etq))
        ys.append(ly)

    estados = []
    for i, (x, y) in pos.items():
        estados.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="%s" stroke="%s" stroke-width="1.4"/>'
                       % (x, y, R, C_ESTADO, C_BORDE))
        if i in finales:
            estados.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="none" stroke="%s" stroke-width="1.4"/>'
                           % (x, y, R - 4, C_BORDE))
        estados.append(_texto(x, y + 4.5, nombres[i]))
    xi, yi = pos[inicio]
    estados.append('<path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f Z" fill="none" stroke="%s" stroke-width="1.4" '
                   'stroke-linejoin="miter"/>' % (xi - R - 24, yi - 20, xi - R, yi, xi - R - 24, yi + 20, C_BORDE))

    x0, x1 = min(xs) - R - 40, max(xs) + R + 30
    y0, y1 = min(ys) - 30, max(ys) + R + 30
    w, h = x1 - x0, y1 - y0
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.0f %.0f %.0f %.0f" width="%.0f" height="%.0f" '
        'role="img" aria-label="Diagrama del autómata (estilo JFLAP)">'
        '<defs><marker id="%s-f" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="11" markerHeight="11" '
        'markerUnits="userSpaceOnUse" orient="auto"><path d="M1 1.5 L11 6 L1 10.5" fill="none" stroke="%s" '
        'stroke-width="1.2"/></marker></defs><rect x="%.0f" y="%.0f" width="%.0f" height="%.0f" fill="%s"/>%s%s</svg>'
        % (x0, y0, w, h, w, h, uid, C_LINEA, x0, y0, w, h, C_FONDO, "".join(cuerpo), "".join(estados)))


# ------------------------------------------------------------ Etapa 3: árbol sintáctico
C_NT, C_T, C_LEX = "#7c5cff", "#2ecc9a", "#c9bfff"


def _ancho(*textos):
    return max(len(t) for t in textos) * 7.4 + 18


def svg_arbol(arbol):
    """Árbol de derivación como SVG: no terminales arriba, terminales (tokens) alineados abajo
    y, debajo de cada uno, el lexema que lo produjo. Se calcula a partir del árbol del parser."""
    hojas, internos = [], []

    def visitar(n, prof):
        if "hijos" not in n:
            hojas.append(n)
            n["_p"] = prof
            n["_w"] = _ancho(n["nodo"], "«%s»" % n["lexema"])
            return
        internos.append((n, prof))
        for h in n["hijos"]:
            visitar(h, prof + 1)

    visitar(arbol, 0)
    prof_max = max(n["_p"] for n in hojas)
    NIVEL, GAP, M = 78, 10, 20
    x = M
    for h in hojas:
        h["_x"], h["_y"] = x + h["_w"] / 2, M + 14 + h["_p"] * NIVEL
        x += h["_w"] + GAP
    ancho = x - GAP + M

    def colocar(n):
        if "hijos" in n:
            xs = [colocar(h) for h in n["hijos"]]
            n["_x"] = (xs[0] + xs[-1]) / 2
        return n["_x"]

    colocar(arbol)
    for n, p in internos:
        n["_y"] = M + 14 + p * NIVEL

    lineas, nodos = [], []
    for n, _ in internos:
        for h in n["hijos"]:
            lineas.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#5a6390" stroke-width="1.2"/>'
                          % (n["_x"], n["_y"] + 13, h["_x"], h["_y"] - 13))
        etq = "<%s>" % n["nodo"]
        w = _ancho(etq)
        nodos.append('<rect x="%.1f" y="%.1f" width="%.1f" height="26" rx="13" fill="%s22" stroke="%s"/>'
                     '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="13" fill="#e8eaf6" font-family="%s">%s</text>'
                     % (n["_x"] - w / 2, n["_y"] - 13, w, C_NT, C_NT, n["_x"], n["_y"] + 4.5, FUENTE, escape(etq)))
    for h in hojas:
        w = h["_w"]
        c_t = "#ff5d73" if h.get("error") else C_T
        nodos.append('<rect x="%.1f" y="%.1f" width="%.1f" height="26" rx="4" fill="%s22" stroke="%s"/>'
                     '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="11.5" fill="#e8eaf6" font-family="%s">%s</text>'
                     '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#5a6390" stroke-dasharray="3 3"/>'
                     '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="13" fill="%s" '
                     'font-family="ui-monospace, monospace">%s</text>'
                     % (h["_x"] - w / 2, h["_y"] - 13, w, c_t, c_t, h["_x"], h["_y"] + 4, FUENTE, escape(h["nodo"]),
                        h["_x"], h["_y"] + 13, h["_x"], h["_y"] + 30, h["_x"], h["_y"] + 45, "#ffc2cb" if h.get("error") else C_LEX,
                        escape(h["lexema"])))
    for n in hojas + [n for n, _ in internos]:
        n.pop("_x", None); n.pop("_y", None); n.pop("_w", None); n.pop("_p", None)
    alto = M + 14 + prof_max * NIVEL + 58
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.0f %.0f" width="%.0f" height="%.0f" role="img" '
            'aria-label="Árbol sintáctico de la cadena LER"><rect width="100%%" height="100%%" fill="#0c0f1d"/>%s%s</svg>'
            % (ancho, alto, ancho, alto, "".join(lineas), "".join(nodos)))
