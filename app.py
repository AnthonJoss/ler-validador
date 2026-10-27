from functools import lru_cache

from flask import Flask, jsonify, render_template, request

from automata import analizar_er, recorrer
from lexer import CATALOGO, ER_POR_TOKEN, tokenize

app = Flask(__name__)

EJEMPLOS = {
    "valido": "ENTREGA{ID=P1023;DIST=18.5;CARGA=42;TRAFICO=ALTO;CLIMA=LLUVIA;HORA=17:30;PRIORIDAD=ALTA}",
    "lexico": "ENTREGA{ID=P1023;DIST=18.5#;CARGA=42;TRAFICO=medio;CLIMA=LLUVIA;HORA=17:30;PRIORIDAD=ALTA}",
    "sintactico": "ENTREGA{ID=P1023 DIST=18.5;CARGA=42;TRAFICO=ALTO}",
}


@app.get("/")
def index():
    return render_template("index.html", ejemplos=EJEMPLOS, catalogo=CATALOGO)


@app.get("/api/hola")
def hola():
    return jsonify(mensaje="Hola Mundo desde Flask")


@app.post("/api/analizar")
def analizar():
    texto = request.get_json(silent=True) or {}
    texto = texto.get("texto", "")
    if not texto.strip():
        return jsonify(error="La entrada está vacía."), 400
    if len(texto) > 100_000:
        return jsonify(error="La entrada supera el máximo de 100 000 caracteres."), 413
    tokens, errores = tokenize(texto)
    return jsonify(tokens=tokens, errores=errores, total=len(tokens))


@lru_cache(maxsize=None)
def _automata(token):
    return analizar_er(ER_POR_TOKEN[token])


@app.get("/api/automata/<token>")
def automata(token):
    if token not in ER_POR_TOKEN:
        return jsonify(error="Token desconocido: %s" % token), 404
    a = _automata(token)
    res = {"token": token, "er": a["er"], "afnd": a["afnd"], "afd": a["afd"]}
    lexema = request.args.get("lexema", "")
    if lexema and len(lexema) <= 200:
        res["traza"] = recorrer(a["dfa"], lexema)
    return jsonify(res)


if __name__ == "__main__":
    app.run(debug=True)
