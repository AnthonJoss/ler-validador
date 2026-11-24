"""Analizador sintáctico del lenguaje LER (descendente recursivo, LL(1)).

Gramática (símbolo inicial <registro>):
    <registro>  ::= ENTREGA { <id> ; <dist> ; <carga> ; <trafico> ; <clima> ; <hora> ; <prioridad> }
    <id>        ::= ID = IDENT          <dist>      ::= DIST = NUM
    <carga>     ::= CARGA = NUM         <trafico>   ::= TRAFICO = NIVEL_TRAFICO
    <clima>     ::= CLIMA = ESTADO_CLIMA  <hora>    ::= HORA = TIME
    <prioridad> ::= PRIORIDAD = NIVEL_PRIORIDAD
Recibe los tokens del analizador léxico y devuelve el árbol sintáctico (o el primer error).
"""
from grafico import svg_arbol
from lexer import tokenize

# (no terminal, palabra reservada, token del valor, nombre de la variable)
CAMPOS = [
    ("id", "KW_ID", "IDENT", "id"),
    ("dist", "KW_DIST", "NUM", "distancia"),
    ("carga", "KW_CARGA", "NUM", "carga"),
    ("trafico", "KW_TRAFICO", "NIVEL_TRAFICO", "trafico"),
    ("clima", "KW_CLIMA", "ESTADO_CLIMA", "clima"),
    ("hora", "KW_HORA", "TIME", "hora"),
    ("prioridad", "KW_PRIORIDAD", "NIVEL_PRIORIDAD", "prioridad"),
]
LEGIBLE = {"KW_ENTREGA": "ENTREGA", "LBRACE": "{", "RBRACE": "}", "SEMI": ";", "EQ": "=",
           "NUM": "un número", "IDENT": "un identificador P####", "TIME": "una hora HH:MM",
           "NIVEL_TRAFICO": "BAJO, MEDIO o ALTO", "ESTADO_CLIMA": "DESPEJADO, LLUVIA o NIEBLA",
           "NIVEL_PRIORIDAD": "BAJA, MEDIA o ALTA"}
for _n, _kw, _v, _ in CAMPOS:
    LEGIBLE[_kw] = _kw[3:]


TERMINAL_DE = {"KW_ENTREGA": "ENTREGA", "LBRACE": "{", "RBRACE": "}", "SEMI": ";", "EQ": "="}
for _n, _kw, _v, _ in CAMPOS:
    TERMINAL_DE[_kw] = _kw[3:]


def _rhs_registro():
    rhs = ["KW_ENTREGA", "LBRACE"]
    for k, (nombre, *_r) in enumerate(CAMPOS):
        rhs += (["SEMI"] if k else []) + ["<%s>" % nombre]
    return rhs + ["RBRACE"]


# Producciones P: lista de (cabeza, cuerpo) con los símbolos de la gramática.
PRODUCCIONES = [("<registro>", _rhs_registro())] + [
    ("<%s>" % nombre, [kw, "EQ", valor]) for nombre, kw, valor, _ in CAMPOS]


def simbolo(s):
    """Cómo se escribe un símbolo en la gramática: los tokens fijos con su lexema."""
    return TERMINAL_DE.get(s, s)


def gramatica():
    """G = (V, Σ, P, S) lista para mostrarse en la web."""
    # Σ ordenado como en el informe: palabras reservadas, tokens de valor, operador y delimitadores.
    reservadas = ["ENTREGA"] + [kw[3:] for _, kw, _, _ in CAMPOS]
    valores = [v for _, _, v, _ in CAMPOS if v not in ("NUM",)]
    valores.insert(1, "NUM")
    terminales = reservadas + valores + ["=", "{", "}", ";"]
    return {
        "V": [cab for cab, _ in PRODUCCIONES],
        "Sigma": terminales,
        "S": "<registro>",
        "P": [{"num": i + 1, "cabeza": cab, "cuerpo": " ".join(simbolo(s) for s in cuerpo)}
              for i, (cab, cuerpo) in enumerate(PRODUCCIONES)],
        "tokens": [{"token": n, "simbolo": simbolo(n)} for n in TERMINAL_DE],
    }


class ErrorSintactico(Exception):
    def __init__(self, esperado, token):
        self.esperado, self.token = esperado, token
        super().__init__(esperado)


class _Parser:
    def __init__(self, tokens):
        self.t, self.i, self.raiz = tokens, 0, None

    def actual(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def consumir(self, tipo):
        tok = self.actual()
        if tok is None or tok["token"] != tipo:
            raise ErrorSintactico(LEGIBLE.get(tipo, tipo), tok)
        self.i += 1
        return tok

    def registro(self):
        raiz = self.raiz = {"nodo": "registro", "hijos": []}
        raiz["hijos"].append(self._hoja(self.consumir("KW_ENTREGA")))
        raiz["hijos"].append(self._hoja(self.consumir("LBRACE")))
        for k, (nombre, kw, valor, _) in enumerate(CAMPOS):
            if k:
                raiz["hijos"].append(self._hoja(self.consumir("SEMI")))
            sub = {"nodo": nombre, "hijos": []}
            raiz["hijos"].append(sub)
            for t in (kw, "EQ", valor):
                sub["hijos"].append(self._hoja(self.consumir(t)))
        raiz["hijos"].append(self._hoja(self.consumir("RBRACE")))
        extra = self.actual()
        if extra is not None:
            raise ErrorSintactico("fin de la cadena", extra)
        return raiz

    @staticmethod
    def _hoja(tok):
        return {"nodo": tok["token"], "lexema": tok["lexema"]}


def parsear(tokens):
    """Devuelve (arbol, error). error = None si la cadena pertenece a L(G).
    Si hay error, arbol es el árbol parcial construido hasta el punto del fallo."""
    ps = _Parser(tokens)
    try:
        return ps.registro(), None
    except ErrorSintactico as e:
        tok = e.token
        if tok is None:
            ult = tokens[-1] if tokens else None
            pos = {"linea": ult["linea"], "columna": ult["columna"] + len(ult["lexema"])} if ult else {"linea": 1, "columna": 1}
            encontrado = "fin de la entrada"
        else:
            pos, encontrado = {"linea": tok["linea"], "columna": tok["columna"]}, tok["lexema"]
        raiz = ps.raiz
        if raiz is not None:
            # Hoja de error en el nodo abierto más profundo: el campo incompleto o la raíz.
            destino = raiz
            if raiz["hijos"] and "hijos" in raiz["hijos"][-1] and len(raiz["hijos"][-1]["hijos"]) < 3:
                destino = raiz["hijos"][-1]
            destino["hijos"].append({"nodo": "✗ ERROR", "lexema": "esperaba %s" % e.esperado, "error": True})
        return raiz, {"esperado": e.esperado, "encontrado": encontrado, **pos,
                      "mensaje": "Se esperaba %s y se encontró %s" % (e.esperado, encontrado)}


def variables(arbol):
    """Extrae del árbol las variables que alimentarán el modelo (RF06)."""
    v = {}
    for hijo in arbol["hijos"]:
        for nombre, _, _, var in CAMPOS:
            if hijo["nodo"] == nombre:
                lex = hijo["hijos"][2]["lexema"]
                v[var] = float(lex) if var in ("distancia", "carga") else lex
    return v


def derivacion(arbol):
    """Derivación por la izquierda (⇒) reconstruida desde el árbol: en cada paso se reemplaza
    el no terminal más a la izquierda por el cuerpo de su producción."""
    num = {cab: i + 1 for i, (cab, _) in enumerate(PRODUCCIONES)}
    forma = [arbol]                      # forma sentencial: nodos del árbol
    pasos = [{"forma": "<registro>", "produccion": None}]

    def texto(f):
        return " ".join("<%s>" % n["nodo"] if "hijos" in n else simbolo(n["nodo"]) for n in f)

    while True:
        k = next((i for i, n in enumerate(forma) if "hijos" in n), None)
        if k is None:
            break
        n = forma[k]
        forma = forma[:k] + n["hijos"] + forma[k + 1:]
        cab = "<%s>" % n["nodo"]
        pasos.append({"forma": texto(forma), "produccion": num[cab]})
    pasos.append({"forma": "".join(n["lexema"] for n in forma), "produccion": "lexemas"})
    return pasos


def validar(texto):
    tokens, errores = tokenize(texto)
    arbol, error = parsear(tokens)
    ok = not errores and error is None
    res = {"valido": ok, "tokens": len(tokens), "errores_lexicos": errores, "error_sintactico": error,
           "arbol": arbol if error is None else None, "arbol_parcial": arbol if error else None,
           "variables": variables(arbol) if ok else None, "derivacion": None, "svg": None}
    if arbol and arbol["hijos"]:
        res["svg"] = svg_arbol(arbol)
    if error is None and arbol:
        res["derivacion"] = derivacion(arbol)
    return res
