"""Analizador léxico del lenguaje LER (Lenguaje de Eventos de Reparto)."""
import re

# (nombre, categoría, expresión regular). El orden define la prioridad.
TOKEN_SPEC = [
    ("KW_ENTREGA", "Palabra Reservada", r"ENTREGA"),
    ("KW_ID", "Palabra Reservada", r"ID"),
    ("KW_DIST", "Palabra Reservada", r"DIST"),
    ("KW_CARGA", "Palabra Reservada", r"CARGA"),
    ("KW_TRAFICO", "Palabra Reservada", r"TRAFICO"),
    ("KW_CLIMA", "Palabra Reservada", r"CLIMA"),
    ("KW_HORA", "Palabra Reservada", r"HORA"),
    ("KW_PRIORIDAD", "Palabra Reservada", r"PRIORIDAD"),
    ("NIVEL_TRAFICO", "Literal Enumerado", r"BAJO|MEDIO|ALTO"),
    ("ESTADO_CLIMA", "Literal Enumerado", r"DESPEJADO|LLUVIA|NIEBLA"),
    ("NIVEL_PRIORIDAD", "Literal Enumerado", r"BAJA|MEDIA|ALTA"),
    ("IDENT", "Identificador", r"P[0-9]{4}"),
]
# Las palabras (letras/dígitos) deben coincidir completas: "IDX" no es KW_ID.
_WORD_TOKENS = [(n, c, r"(?:%s)(?![A-Za-z0-9_])" % p) for n, c, p in TOKEN_SPEC]
_OTHER_TOKENS = [
    ("TIME", "Literal Horario", r"(?:[01][0-9]|2[0-3]):[0-5][0-9](?![0-9])"),
    ("NUM", "Literal Numérico", r"[0-9]+(?:\.[0-9]+)?"),
    ("EQ", "Operador", r"="),
    ("LBRACE", "Delimitador", r"\{"),
    ("RBRACE", "Delimitador", r"\}"),
    ("SEMI", "Delimitador", r";"),
]
ALL_TOKENS = _WORD_TOKENS + _OTHER_TOKENS

MASTER = re.compile(
    "|".join("(?P<%s>%s)" % (n, p) for n, _, p in ALL_TOKENS)
    + r"|(?P<WS>\s+)|(?P<BADWORD>[A-Za-z_][A-Za-z0-9_]*)|(?P<BAD>.)",
    re.DOTALL,
)
CATEGORY = {n: c for n, c, _ in ALL_TOKENS}

CATALOGO = [
    {"token": n, "categoria": c, "regex": re.sub(r"\(\?![^)]*\)$", "", p)}
    for n, c, p in TOKEN_SPEC + _OTHER_TOKENS
]
# ER pura de cada token (sin el lookahead de delimitación); alimenta los autómatas de la etapa 2.
ER_POR_TOKEN = {t["token"]: t["regex"] for t in CATALOGO}


def tokenize(texto):
    """Devuelve (tokens, errores). Cada elemento lleva línea y columna (1-based)."""
    tokens, errores = [], []
    linea, inicio_linea = 1, 0
    for m in MASTER.finditer(texto):
        tipo, lexema = m.lastgroup, m.group()
        col = m.start() - inicio_linea + 1
        if tipo == "WS":
            n = lexema.count("\n")
            if n:
                linea += n
                inicio_linea = m.start() + lexema.rfind("\n") + 1
            continue
        if tipo in ("BAD", "BADWORD"):
            motivo = (
                "Palabra no reconocida (el lenguaje solo admite MAYÚSCULAS definidas)"
                if tipo == "BADWORD"
                else "Símbolo no permitido en el alfabeto de LER"
            )
            errores.append({"lexema": lexema, "linea": linea, "columna": col, "mensaje": motivo})
            continue
        tokens.append({
            "lexema": lexema, "token": tipo, "categoria": CATEGORY[tipo], "er": ER_POR_TOKEN[tipo],
            "linea": linea, "columna": col,
        })
    return tokens, errores
