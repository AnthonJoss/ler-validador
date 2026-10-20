from flask import Flask, jsonify, render_template, request

from lexer import CATALOGO, tokenize

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


if __name__ == "__main__":
    app.run(debug=True)
