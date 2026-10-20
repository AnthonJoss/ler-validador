import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import EJEMPLOS
from lexer import tokenize


def test_valido():
    t, e = tokenize(EJEMPLOS["valido"])
    assert not e and len(t) == 30
    assert [x["token"] for x in t][:6] == ["KW_ENTREGA", "LBRACE", "KW_ID", "EQ", "IDENT", "SEMI"]
    assert t[-4]["token"] == "KW_PRIORIDAD" and t[-2]["token"] == "NIVEL_PRIORIDAD"
    assert any(x["token"] == "TIME" and x["lexema"] == "17:30" for x in t)


def test_error_lexico():
    t, e = tokenize(EJEMPLOS["lexico"])
    assert [x["lexema"] for x in e] == ["#", "medio"]


def test_sintactico_sin_errores_lexicos():
    t, e = tokenize(EJEMPLOS["sintactico"])
    assert not e
