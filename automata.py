"""Etapa 2: ER -> AFND (Thompson) -> AFD (subconjuntos) -> quíntupla, tabla y transiciones.

Todo se calcula a partir del texto de la expresión regular; nada está dibujado a mano.
Sintaxis de ER soportada: literales, escapes (\\.), clases [a-z], grupos (...) y (?:...),
alternancia |, y los cuantificadores * + ? {n} {n,m}.
"""
from collections import deque

from grafico import svg_automata

EPS = "ε"


# ---------------------------------------------------------------- parser de ER
class _Parser:
    def __init__(self, er):
        self.s, self.i = er, 0

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else None

    def eat(self, c=None):
        ch = self.peek()
        if ch is None or (c is not None and ch != c):
            raise ValueError("Se esperaba %r en la posición %d de %r" % (c, self.i, self.s))
        self.i += 1
        return ch

    def parse(self):
        nodo = self.alt()
        if self.peek() is not None:
            raise ValueError("Carácter inesperado %r en la posición %d" % (self.peek(), self.i))
        return nodo

    def alt(self):
        ramas = [self.cat()]
        while self.peek() == "|":
            self.eat()
            ramas.append(self.cat())
        return ramas[0] if len(ramas) == 1 else ("alt", ramas)

    def cat(self):
        partes = []
        while self.peek() not in (None, "|", ")"):
            partes.append(self.rep())
        if not partes:
            raise ValueError("Expresión vacía en la posición %d" % self.i)
        return partes[0] if len(partes) == 1 else ("cat", partes)

    def rep(self):
        nodo = self.atom()
        while self.peek() in ("*", "+", "?", "{"):
            q = self.eat()
            if q == "*":
                nodo = ("star", nodo)
            elif q == "+":
                nodo = ("plus", nodo)
            elif q == "?":
                nodo = ("opt", nodo)
            else:
                lo = self.numero()
                hi = lo
                if self.peek() == ",":
                    self.eat()
                    hi = self.numero()
                self.eat("}")
                nodo = self.expandir(nodo, lo, hi)
        return nodo

    def numero(self):
        ini = self.i
        while self.peek() is not None and self.peek().isdigit():
            self.i += 1
        if ini == self.i:
            raise ValueError("Se esperaba un número en la posición %d" % ini)
        return int(self.s[ini:self.i])

    @staticmethod
    def expandir(nodo, lo, hi):
        """x{n,m} se desarrolla como x…x (n veces) seguido de (m-n) x?."""
        if hi < lo or hi == 0:
            raise ValueError("Cuantificador {%d,%d} inválido" % (lo, hi))
        partes = [nodo] * lo + [("opt", nodo)] * (hi - lo)
        return partes[0] if len(partes) == 1 else ("cat", partes)

    def atom(self):
        c = self.eat()
        if c == "(":
            if self.s.startswith("?:", self.i):
                self.i += 2
            nodo = self.alt()
            self.eat(")")
            return nodo
        if c == "[":
            return ("chr", self.clase())
        if c == "\\":
            return ("chr", frozenset(self.eat()))
        if c in "*+?{}|)]." or c == "^" or c == "$":
            raise ValueError("Símbolo %r sin escapar en la posición %d" % (c, self.i - 1))
        return ("chr", frozenset(c))

    def clase(self):
        if self.peek() == "^":
            raise ValueError("Las clases negadas no están soportadas")
        chars = set()
        while self.peek() != "]":
            a = self.eat()
            if a == "\\":
                a = self.eat()
            if self.peek() == "-" and self.s[self.i + 1:self.i + 2] not in ("]", ""):
                self.eat()
                b = self.eat()
                chars.update(chr(k) for k in range(ord(a), ord(b) + 1))
            else:
                chars.add(a)
        self.eat("]")
        return frozenset(chars)


def parsear(er):
    return _Parser(er).parse()


# ------------------------------------------------------------ utilidades de símbolos
def _misma_clase(a, b):
    """Evita rangos que mezclan clases, como '0-:' (el ':' sigue al '9' en ASCII)."""
    return any(f(chr(a)) and f(chr(b)) for f in (str.isdigit, str.isupper, str.islower))


def fmt_conjunto(chars):
    """{'0',...,'9',':'} -> '0-9, :'  (rangos de 3 o más consecutivos)."""
    cs = sorted(ord(c) for c in chars)
    partes, i = [], 0
    while i < len(cs):
        j = i
        while j + 1 < len(cs) and cs[j + 1] == cs[j] + 1 and _misma_clase(cs[j], cs[j + 1]):
            j += 1
        if j - i >= 2:
            partes.append("%s-%s" % (chr(cs[i]), chr(cs[j])))
        else:
            partes.extend(chr(c) for c in cs[i:j + 1])
        i = j + 1
    return ", ".join(partes)


def particion(conjuntos):
    """Divide el alfabeto en clases de caracteres que se comportan igual en todo el autómata."""
    grupos = {}
    for ch in sorted(set().union(*conjuntos)):
        firma = tuple(ch in c for c in conjuntos)
        grupos.setdefault(firma, set()).add(ch)
    return sorted((frozenset(g) for g in grupos.values()), key=min)


def nombre_afd(i):
    return chr(65 + i % 26) + (str(i // 26) if i >= 26 else "")


# --------------------------------------------------------------- AFND (Thompson)
class _Thompson:
    def __init__(self):
        self.n = 0
        self.trans = []  # (origen, frozenset|None, destino)

    def nuevo(self):
        self.n += 1
        return self.n - 1

    def construir(self, nodo, s):
        """Añade el fragmento de `nodo` partiendo de s y devuelve su estado final."""
        tipo = nodo[0]
        if tipo == "chr":
            f = self.nuevo()
            self.trans.append((s, nodo[1], f))
            return f
        if tipo == "cat":  # el final de una parte es el inicio de la siguiente
            for parte in nodo[1]:
                s = self.construir(parte, s)
            return s
        if tipo == "alt":
            f = self.nuevo()
            for rama in nodo[1]:
                a = self.nuevo()
                self.trans.append((s, None, a))
                self.trans.append((self.construir(rama, a), None, f))
            return f
        a = self.nuevo()
        self.trans.append((s, None, a))
        e = self.construir(nodo[1], a)
        f = self.nuevo()
        self.trans.append((e, None, f))
        if tipo in ("star", "plus"):
            self.trans.append((e, None, a))
        if tipo in ("star", "opt"):
            self.trans.append((s, None, f))
        return f


def construir_afnd(er):
    t = _Thompson()
    ini = t.nuevo()
    fin = t.construir(parsear(er), ini)
    # renumerar por orden de aparición desde el inicio (q0, q1, ...)
    adj = {}
    for u, _, v in t.trans:
        adj.setdefault(u, []).append(v)
    orden, cola = {ini: 0}, deque([ini])
    while cola:
        u = cola.popleft()
        for v in adj.get(u, []):
            if v not in orden:
                orden[v] = len(orden)
                cola.append(v)
    trans = sorted(((orden[u], c, orden[v]) for u, c, v in t.trans),
                   key=lambda x: (x[0], x[1] is None, min(x[1]) if x[1] else "", x[2]))
    sets = [c for _, c, _ in trans if c is not None]
    atomos = particion(sets)
    return {"n": len(orden), "inicio": 0, "final": orden[fin], "trans": trans, "atomos": atomos}


# ------------------------------------------------------------ AFND -> AFD (subconjuntos)
def _cierre(estados, eps):
    pila, res = list(estados), set(estados)
    while pila:
        for v in eps.get(pila.pop(), ()):
            if v not in res:
                res.add(v)
                pila.append(v)
    return frozenset(res)


def construir_afd(nfa):
    eps, mov = {}, {}
    for u, c, v in nfa["trans"]:
        if c is None:
            eps.setdefault(u, []).append(v)
        else:
            for k, a in enumerate(nfa["atomos"]):
                if a <= c:
                    mov.setdefault((u, k), []).append(v)
    inicial = _cierre({nfa["inicio"]}, eps)
    ids, cola, delta = {inicial: 0}, deque([inicial]), {}
    while cola:
        S = cola.popleft()
        for k in range(len(nfa["atomos"])):
            alcanzados = {v for u in S for v in mov.get((u, k), ())}
            if not alcanzados:
                continue
            T = _cierre(alcanzados, eps)
            if T not in ids:
                ids[T] = len(ids)
                cola.append(T)
            delta[(ids[S], k)] = ids[T]
    conjuntos = sorted(ids, key=ids.get)
    return {
        "n": len(ids), "inicio": 0, "atomos": nfa["atomos"], "delta": delta,
        "composicion": [sorted(S) for S in conjuntos],
        "finales": [ids[S] for S in conjuntos if nfa["final"] in S],
    }


# ------------------------------------------------------------------ salida legible
def _etq(atomo):
    return fmt_conjunto(atomo)


def _lista(xs):
    return "{" + ", ".join(xs) + "}" if xs else "∅"


def datos_afnd(nfa):
    q = lambda i: "q%d" % i
    cols = [_etq(a) for a in nfa["atomos"]] + [EPS]
    celdas = {}
    for u, c, v in nfa["trans"]:
        ks = [len(nfa["atomos"])] if c is None else [k for k, a in enumerate(nfa["atomos"]) if a <= c]
        for k in ks:
            celdas.setdefault((u, k), []).append(v)
    filas = [{
        "estado": q(i), "inicial": i == nfa["inicio"], "final": i == nfa["final"],
        "celdas": [_lista([q(v) for v in sorted(celdas.get((i, k), []))]) for k in range(len(cols))],
    } for i in range(nfa["n"])]
    sigma = sorted(set().union(*nfa["atomos"]))
    return {
        "estados": [q(i) for i in range(nfa["n"])],
        "alfabeto": fmt_conjunto(sigma),
        "inicial": q(nfa["inicio"]), "finales": [q(nfa["final"])], "inicio": nfa["inicio"],
        "tabla": {"columnas": cols, "filas": filas},
        "transiciones": ["δ(%s, %s) = %s" % (
            q(u), EPS if c is None else _etq(c), _lista([q(v)])) for u, c, v in nfa["trans"]],
        "aristas": [(u, v, EPS if c is None else _etq(c)) for u, c, v in nfa["trans"]],
    }


def datos_afd(dfa):
    q = nombre_afd
    cols = [_etq(a) for a in dfa["atomos"]]
    sigma = sorted(set().union(*dfa["atomos"]))
    filas = [{
        "estado": q(i), "inicial": i == dfa["inicio"], "final": i in dfa["finales"],
        "afnd": _lista(["q%d" % s for s in dfa["composicion"][i]]),
        "celdas": [q(dfa["delta"][(i, k)]) if (i, k) in dfa["delta"] else "—" for k in range(len(cols))],
    } for i in range(dfa["n"])]
    trans = [(u, k, v) for (u, k), v in sorted(dfa["delta"].items())]
    return {
        "estados": [q(i) for i in range(dfa["n"])],
        "alfabeto": fmt_conjunto(sigma),
        "inicial": q(dfa["inicio"]), "finales": [q(i) for i in dfa["finales"]], "inicio": dfa["inicio"],
        "tabla": {"columnas": cols, "filas": filas},
        "transiciones": ["δ(%s, %s) = %s" % (q(u), cols[k], q(v)) for u, k, v in trans],
        "aristas": _fusionar([(u, v, dfa["atomos"][k]) for u, k, v in trans]),
    }


def _fusionar(aristas):
    """Une las aristas paralelas (u,v) en una sola con la unión de sus símbolos."""
    por_par = {}
    for u, v, a in aristas:
        por_par.setdefault((u, v), set()).update(a)
    return [(u, v, fmt_conjunto(cs)) for (u, v), cs in por_par.items()]


def recorrer(dfa, lexema):
    """Traza del lexema sobre el AFD: lista de pasos y si termina en estado de aceptación."""
    q, estado, pasos = nombre_afd, dfa["inicio"], []
    for ch in lexema:
        k = next((k for k, a in enumerate(dfa["atomos"]) if ch in a), None)
        destino = dfa["delta"].get((estado, k)) if k is not None else None
        pasos.append({"de": q(estado), "simbolo": ch,
                      "a": q(destino) if destino is not None else "✗"})
        if destino is None:
            return {"pasos": pasos, "acepta": False}
        estado = destino
    return {"pasos": pasos, "acepta": estado in dfa["finales"]}


def analizar_er(er):
    """Devuelve todo lo necesario para presentar las cuatro salidas de la etapa 2."""
    nfa = construir_afnd(er)
    dfa = construir_afd(nfa)
    afnd, afd = datos_afnd(nfa), datos_afd(dfa)
    afnd["svg"] = svg_automata(afnd["estados"], afnd["inicio"], {nfa["final"]}, afnd["aristas"], "nfa")
    afd["svg"] = svg_automata(afd["estados"], afd["inicio"], set(dfa["finales"]), afd["aristas"], "dfa")
    return {"er": er, "nfa": nfa, "dfa": dfa, "afnd": afnd, "afd": afd}
