"""Dibuja un autómata como SVG (sin Graphviz) a partir de sus aristas."""
from collections import deque
from html import escape
from math import hypot

R = 18          # radio de estado
DX, DY = 96, 70  # separación entre capas / filas
MARGEN = 36

C_LINEA, C_TEXTO, C_FONDO, C_ACENTO = "#9aa3c7", "#e8eaf6", "#0c0f1d", "#7c5cff"


def _capas(n, inicio, aristas):
    """Capa = camino más largo desde el inicio ignorando las aristas de retroceso (ciclos)."""
    sal = {}
    for u, v, _ in aristas:
        sal.setdefault(u, []).append(v)
    estado, atras, orden = {}, set(), []
    pila = [(inicio, iter(sal.get(inicio, [])))]
    estado[inicio] = 1
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
    for u in reversed(orden):  # orden topologico del DAG
        for v in sal.get(u, []):
            if (u, v) not in atras and v != u:
                prof[v] = max(prof[v], prof[u] + 1)
    return prof


def svg_automata(nombres, inicio, finales, aristas, uid):
    """nombres: etiqueta por índice de estado; aristas: [(u, v, etiqueta)] con índices."""
    n = len(nombres)
    prof = _capas(n, inicio, aristas)
    filas = {}
    for i in sorted(prof, key=lambda i: (prof[i], i)):
        filas.setdefault(prof[i], []).append(i)
    ancho_max = max(len(f) for f in filas.values())
    pos = {}
    for d, miembros in filas.items():
        for k, i in enumerate(miembros):
            y = MARGEN + 2 * DY * 0 + (ancho_max - len(miembros)) * DY / 2 + k * DY
            pos[i] = (MARGEN + 30 + d * DX, y + 50)

    # aristas fusionadas por par ordenado (ya vienen únicas en el AFD; el AFND puede repetir pares)
    pares = {}
    for u, v, e in aristas:
        pares.setdefault((u, v), []).append(e)
    cuerpo, extremos = [], []
    for (u, v), etqs in pares.items():
        etq = " | ".join(dict.fromkeys(etqs))
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        if u == v:
            camino = ("M %.1f %.1f C %.1f %.1f %.1f %.1f %.1f %.1f"
                      % (x1 - 9, y1 - R + 2, x1 - 30, y1 - R - 42, x1 + 30, y1 - R - 42, x1 + 9, y1 - R + 2))
            lx, ly = x1, y1 - R - 34
            extremos.append(ly)
        else:
            inverso = (v, u) in pares
            dl = abs(prof[v] - prof[u])
            if prof[v] <= prof[u]:       # arista de retroceso: por arriba
                h = -(34 + 12 * dl)
            elif dl > 1 or inverso:      # salto hacia adelante o par bidireccional: por abajo
                h = 30 + 14 * dl
            else:
                h = 0
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            if h == 0:
                cx, cy = mx, my
            elif abs(x1 - x2) < 1:
                cx, cy = mx + h, my
            else:
                cx, cy = mx, min(y1, y2) + h if h < 0 else max(y1, y2) + h
            sx, sy = _hacia(x1, y1, cx, cy, R)
            ex, ey = _hacia(x2, y2, cx, cy, R + 3)
            camino = "M %.1f %.1f Q %.1f %.1f %.1f %.1f" % (sx, sy, cx, cy, ex, ey)
            lx, ly = (sx + 2 * cx + ex) / 4, (sy + 2 * cy + ey) / 4 - (0 if h == 0 else 0)
            if h == 0:
                ly -= 9
            extremos.append(ly)
        w = max(14, 6.6 * len(etq) + 8)
        cuerpo.append(
            '<path d="%s" fill="none" stroke="%s" stroke-width="1.5" marker-end="url(#%s-f)"/>' % (camino, C_LINEA, uid)
            + '<rect x="%.1f" y="%.1f" width="%.1f" height="16" rx="4" fill="%s" opacity=".92"/>' % (lx - w / 2, ly - 8, w, C_FONDO)
            + '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="12" fill="%s" '
              'font-family="ui-monospace,monospace">%s</text>' % (lx, ly + 4, C_TEXTO, escape(etq)))

    estados = []
    for i in range(n):
        x, y = pos[i]
        estados.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="%s" stroke="%s" stroke-width="2"/>'
                       % (x, y, R, C_FONDO, C_ACENTO))
        if i in finales:
            estados.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="none" stroke="%s" stroke-width="2"/>'
                           % (x, y, R - 5, C_ACENTO))
        estados.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="12" fill="%s" '
                       'font-family="ui-monospace,monospace">%s</text>' % (x, y + 4, C_TEXTO, escape(nombres[i])))
    xi, yi = pos[inicio]
    estados.append('<path d="M %.1f %.1f L %.1f %.1f" stroke="%s" stroke-width="1.5" marker-end="url(#%s-f)"/>'
                   % (xi - R - 26, yi, xi - R - 2, yi, C_LINEA, uid))

    ys = [p[1] for p in pos.values()] + extremos
    top, bottom = min(ys) - 24, max(ys) + R + 14
    w = max(p[0] for p in pos.values()) + R + MARGEN
    top = min(top, 0)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 %.0f %.0f %.0f" width="%.0f" height="%.0f" '
        'role="img" aria-label="Diagrama del autómata">'
        '<defs><marker id="%s-f" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
        'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="%s"/></marker></defs>%s%s</svg>'
        % (top, w, bottom - top, w, bottom - top, uid, C_LINEA, "".join(cuerpo), "".join(estados)))


def _hacia(x, y, cx, cy, r):
    """Punto a distancia r del centro (x,y) en dirección al punto (cx,cy)."""
    d = hypot(cx - x, cy - y) or 1
    return x + (cx - x) * r / d, y + (cy - y) * r / d
