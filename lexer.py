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
    ("IDENT", "Identificador", r"P[0123456789]{4}"),
]
# Las palabras (letras/dígitos) deben coincidir completas: "IDX" no es KW_ID.
_WORD_TOKENS = [(n, c, r"(?:%s)(?![A-Za-z0123456789_])" % p) for n, c, p in TOKEN_SPEC]
_OTHER_TOKENS = [
    ("TIME", "Literal Horario", r"(?:[01][0123456789]|2[0123]):[012345][0123456789](?![0123456789])"),
    ("NUM", "Literal Numérico", r"[0123456789]+(?:\.[0123456789]+)?"),
    ("EQ", "Operador", r"="),
    ("LBRACE", "Delimitador", r"\{"),
    ("RBRACE", "Delimitador", r"\}"),
    ("SEMI", "Delimitador", r";"),
]
ALL_TOKENS = _WORD_TOKENS + _OTHER_TOKENS

MASTER = re.compile(
    "|".join("(?P<%s>%s)" % (n, p) for n, _, p in ALL_TOKENS)
    + r"|(?P<WS>\s+)|(?P<BADWORD>[A-Za-z_][A-Za-z0123456789_]*)|(?P<BAD>.)",
    re.DOTALL,
)
CATEGORY = {n: c for n, c, _ in ALL_TOKENS}

ADMITIDOS = {
    "IDENT": "P seguido de cuatro dígitos (ej.: P1023, P0048)",
    "NUM": "Entero o decimal (ej.: 7, 42, 18.5, 12.5)",
    "TIME": "HH:MM de 00:00 a 23:59 (ej.: 09:15, 17:30)",
    "NIVEL_TRAFICO": "BAJO, MEDIO, ALTO",
    "ESTADO_CLIMA": "DESPEJADO, LLUVIA, NIEBLA",
    "NIVEL_PRIORIDAD": "BAJA, MEDIA, ALTA",
}
CATALOGO = [
    {"token": n, "categoria": c, "regex": re.sub(r"\(\?![^)]*\)$", "", p),
     "admitidos": ADMITIDOS.get(n, re.sub(r"\(\?![^)]*\)$", "", p).replace("\\", ""))}
    for n, c, p in TOKEN_SPEC + _OTHER_TOKENS
]
ADMITIDOS_POR_TOKEN = {t["token"]: t["admitidos"] for t in CATALOGO}
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
            if tipo == "BAD":
                motivo = "Símbolo no permitido en el alfabeto de LER"
            elif re.fullmatch(r"P[0123456789]+", lexema):
                motivo = "IDENT inválido: el formato exige P seguido de cuatro dígitos (P[0123456789]{4})"
            else:
                motivo = "Palabra no reconocida (no coincide con ninguna palabra reservada ni literal enumerado)"
            errores.append({"lexema": lexema, "linea": linea, "columna": col, "mensaje": motivo})
            continue
        tokens.append({
            "lexema": lexema, "token": tipo, "categoria": CATEGORY[tipo], "er": ER_POR_TOKEN[tipo],
            "admitidos": ADMITIDOS_POR_TOKEN[tipo],
            "linea": linea, "columna": col,
        })
    return tokens, errores
