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


# ---- Etapa 3: análisis sintáctico y árbol
from parser import validar


def test_parser_valido_y_variables():
    r = validar(EJEMPLOS["valido"])
    assert r["valido"] and r["arbol"]["nodo"] == "registro"
    assert [h["nodo"] for h in r["arbol"]["hijos"] if h["nodo"] in ("id", "hora", "prioridad")] == ["id", "hora", "prioridad"]
    assert r["variables"] == {"id": "P1023", "distancia": 18.5, "carga": 42.0, "trafico": "ALTO",
                              "clima": "LLUVIA", "hora": "17:30", "prioridad": "ALTA"}


def test_parser_falta_punto_y_coma():
    e = validar("ENTREGA{ID=P1023 DIST=18.5;CARGA=42;TRAFICO=ALTO;CLIMA=LLUVIA;HORA=17:30;PRIORIDAD=ALTA}")["error_sintactico"]
    assert e["esperado"] == ";" and e["encontrado"] == "DIST" and e["columna"] == 18


def test_parser_orden_distinto():
    r = validar("ENTREGA{ID=P1023;DIST=18.5;CARGA=42;TRAFICO=ALTO;CLIMA=LLUVIA;PRIORIDAD=ALTA;HORA=17:30}")
    assert not r["valido"] and r["error_sintactico"]["esperado"] == "HORA"


def test_parser_incompleto_y_extra():
    assert validar(EJEMPLOS["sintactico"])["error_sintactico"]["esperado"] == ";"
    assert validar("ENTREGA{ID=P1023")["error_sintactico"]["encontrado"] == "fin de la entrada"
    ok = "ENTREGA{ID=P1023;DIST=1;CARGA=2;TRAFICO=BAJO;CLIMA=NIEBLA;HORA=09:15;PRIORIDAD=MEDIA}"
    assert validar(ok)["valido"] and validar(ok + "}")["error_sintactico"]["esperado"] == "fin de la cadena"


def test_parser_valor_fuera_de_dominio():
    r = validar("ENTREGA{ID=P1023;DIST=18.5;CARGA=42;TRAFICO=EXTREMO;CLIMA=LLUVIA;HORA=17:30;PRIORIDAD=ALTA}")
    assert not r["valido"] and r["errores_lexicos"][0]["lexema"] == "EXTREMO"


def test_gramatica_cuadrupla():
    from parser import gramatica
    g = gramatica()
    assert g["S"] == "<registro>" and len(g["V"]) == 8 and len(g["P"]) == 8
    assert g["P"][0]["cuerpo"].startswith("ENTREGA { <id> ;") and "NIVEL_PRIORIDAD" in g["Sigma"]


def test_derivacion_y_svg_del_arbol():
    r = validar(EJEMPLOS["valido"])
    d = r["derivacion"]
    assert d[0]["forma"] == "<registro>" and [p["produccion"] for p in d[1:-1]] == list(range(1, 9))
    assert "<" not in d[-2]["forma"] and d[-1]["forma"] == EJEMPLOS["valido"]
    assert r["svg"].startswith("<svg") and "P1023" in r["svg"] and "&lt;registro&gt;" in r["svg"]


def test_ejemplos_invalidos_del_informe():
    assert validar(EJEMPLOS["valido2"])["valido"]
    r = validar(EJEMPLOS["ident"])
    assert not r["valido"] and r["errores_lexicos"][0]["lexema"] == "P23"
    e = validar(EJEMPLOS["falta_semi"])["error_sintactico"]
    assert e["esperado"] == ";" and e["linea"] == 2
    assert validar(EJEMPLOS["extremo"])["errores_lexicos"][0]["lexema"] == "EXTREMO"
    r = validar(EJEMPLOS["orden"])
    assert not r["errores_lexicos"] and r["error_sintactico"]["esperado"] == "HORA"
    assert r["arbol"] is None and r["arbol_parcial"]["hijos"] and r["svg"]


def test_pagina_muestra_gramatica_y_enunciado():
    from app import app
    html = app.test_client().get("/").get_data(as_text=True)
    assert "G = (V, Σ, P, S)" in html and "Enunciado del proyecto" in html and "::=" in html


def test_digitos_individuales_en_ambos_automatas():
    digitos = list("0123456789")
    for token in ("IDENT", "NUM", "TIME"):
        er = ER_POR_TOKEN[token]
        assert "-" not in er
        a = analizar_er(er)
        for tipo in ("afnd", "afd"):
            datos = a[tipo]
            assert [c for c in datos["tabla"]["columnas"] if c in digitos] == digitos
            assert all(d in datos["alfabeto"].split(", ") for d in digitos)
            for d in digitos:
                assert any(f", {d})" in t for t in datos["transiciones"])
            assert "0, 1, 2, 3, 4, 5, 6, 7, 8, 9" in datos["svg"]
        for _, simbolos, _ in a["nfa"]["trans"]:
            if simbolos and simbolos.intersection(digitos):
                assert len(simbolos) == 1
        assert all(len(s) == 1 for s in a["dfa"]["atomos"] if s.intersection(digitos))


def test_todos_los_digitos_y_limites_horarios():
    for d in "0123456789":
        assert _acepta(analizar_er(ER_POR_TOKEN["IDENT"])["dfa"], "P" + d * 4)
        assert _acepta(analizar_er(ER_POR_TOKEN["NUM"])["dfa"], d + "." + d)
    afd = analizar_er(ER_POR_TOKEN["TIME"])["dfa"]
    for h in range(26):
        for m in range(62):
            assert _acepta(afd, f"{h:02}:{m:02}") == (h < 24 and m < 60)
