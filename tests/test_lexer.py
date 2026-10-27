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


# ---- Etapa 2: ER -> AFND -> AFD
from automata import analizar_er, recorrer
from lexer import ER_POR_TOKEN
import re


def _acepta(dfa, s):
    return recorrer(dfa, s)["acepta"]


def test_afd_equivale_a_la_er():
    casos = {
        "TIME": ["17:30", "00:00", "23:59", "24:00", "7:30", "17:60", "17:3", "1730", ""],
        "NUM": ["42", "18.5", "18.", ".5", "0.0.1", "", "a"],
        "IDENT": ["P1023", "P123", "P12345", "p1023", ""],
        "NIVEL_TRAFICO": ["BAJO", "MEDIO", "ALTO", "ALT", "ALTOO", ""],
        "KW_ENTREGA": ["ENTREGA", "ENTREG", "ENTREGAS"],
    }
    for token, textos in casos.items():
        a = analizar_er(ER_POR_TOKEN[token])
        for t in textos:
            esperado = re.fullmatch(ER_POR_TOKEN[token], t) is not None
            assert _acepta(a["dfa"], t) == esperado, (token, t)


def test_todas_las_er_generan_automatas():
    for token, er in ER_POR_TOKEN.items():
        a = analizar_er(er)
        assert a["dfa"]["finales"] and a["afnd"]["svg"].startswith("<svg") and a["afd"]["svg"].startswith("<svg")


def test_endpoint_automata():
    from app import app
    c = app.test_client()
    r = c.get("/api/automata/TIME?lexema=17:30").get_json()
    assert r["traza"]["acepta"] and r["afd"]["finales"]
    assert c.get("/api/automata/NOPE").status_code == 404
