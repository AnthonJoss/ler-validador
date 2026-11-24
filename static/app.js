const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const post = (url, texto) => fetch(url, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({texto})});

fetch("/api/hola").then((r) => r.json()).then((d) => { $("hola").textContent = "✔ " + d.mensaje; })
  .catch(() => { $("hola").textContent = "Backend no disponible"; });

// ------------------------------------------------------------ zoom de gráficos SVG
function herramientas() {
  return `<div class="herramientas"><button data-escala="ajustar">Ajustar</button><button data-escala="ampliar">Ampliar</button>
    <button data-escala="reducir">Reducir</button><button data-escala="original">Tamaño real</button></div>`;
}
function escalar(marco, modo) {
  const svg = marco.querySelector("svg");
  if (!svg) return;
  const natural = Number(svg.dataset.ancho || (svg.dataset.ancho = svg.getAttribute("width")));
  const actual = Number(svg.dataset.factor || 1);
  let f = actual;
  if (modo === "ajustar") f = Math.min(1, Math.max(250, marco.clientWidth - 2) / natural);
  if (modo === "original") f = 1;
  if (modo === "ampliar") f = Math.min(2.4, actual * 1.35);
  if (modo === "reducir") f = Math.max(0.15, actual / 1.35);
  svg.dataset.factor = f;
  svg.style.width = natural * f + "px";
  svg.style.height = "auto";
}
document.addEventListener("click", (ev) => {
  const b = ev.target.closest(".herramientas button");
  if (b) escalar(b.parentElement.nextElementSibling, b.dataset.escala);
});
const grafico = (svg, clase = "") => `${herramientas()}<div class="marco ${clase}">${svg}</div>`;

// ------------------------------------------------------------ análisis completo
async function analizarTodo() {
  const texto = $("entrada").value;
  if (!texto.trim()) {
    $("lex-estado").innerHTML = '<div class="aviso error">La entrada está vacía: escribe una cadena LER o carga un archivo.</div>';
    return;
  }
  const [rl, rs] = await Promise.all([post("/api/analizar", texto), post("/api/validar", texto)]);
  const lex = await rl.json(), sin = await rs.json();
  if (!rl.ok) { $("lex-estado").innerHTML = `<div class="aviso error">${esc(lex.error)}</div>`; return; }
  pintarLexico(lex);
  pintarSintactico(sin);
  pintarAutomatas(lex.tokens);
}

// ------------------------------------------------------------ 2. léxico
function pintarLexico(d) {
  $("lex-estado").innerHTML = d.errores.length
    ? `<div class="aviso error"><b>Análisis léxico con ${d.errores.length} error(es).</b>` +
      d.errores.map((e) => `<br>Línea ${e.linea}, col. ${e.columna} — <code>${esc(e.lexema)}</code>: ${esc(e.mensaje)}`).join("") + "</div>"
    : `<div class="aviso ok">Análisis léxico correcto: ${d.total} lexemas reconocidos.</div>`;
  $("tabla").querySelector("tbody").innerHTML = d.tokens.map((t, i) =>
    `<tr class="clic" data-token="${t.token}" title="Ver su autómata"><td>${i + 1}</td><td><span class="pill">${t.token}</span></td>
     <td><code>${esc(t.lexema)}</code></td><td class="adm">${esc(t.admitidos)}</td><td><code>${esc(t.er)}</code></td><td>${t.linea}:${t.columna}</td></tr>`
  ).join("") || '<tr><td colspan="6" class="adm">No se reconoció ningún token.</td></tr>';
  $("tabla").querySelectorAll("tr.clic").forEach((tr) => tr.onclick = () => {
    const card = document.querySelector(`.auto-card[data-token="${tr.dataset.token}"]`);
    if (card) { card.open = true; card.scrollIntoView({behavior: "smooth"}); }
  });
}

// ------------------------------------------------------------ 3. sintáctico
function arbolTexto(n, pref = "", ultimo = true, raiz = true) {
  const rama = raiz ? "" : pref + (ultimo ? "└─ " : "├─ ");
  const et = n.lexema !== undefined ? `${n.nodo}  «${n.lexema}»` : `<${n.nodo}>`;
  let out = rama + et + "\n";
  const hijos = n.hijos || [];
  hijos.forEach((h, i) => { out += arbolTexto(h, raiz ? "" : pref + (ultimo ? "   " : "│  "), i === hijos.length - 1, false); });
  return out;
}

const NOMBRES = {id: "ID PEDIDO", distancia: "Distancia (km)", carga: "Carga (kg)", trafico: "Tráfico", clima: "Clima", hora: "Hora prevista", prioridad: "Prioridad"};

function pintarSintactico(d) {
  let h = "";
  if (d.error_sintactico) {
    const e = d.error_sintactico;
    h += `<div class="aviso error"><b>Error sintáctico</b> en línea ${e.linea}, columna ${e.columna}: se esperaba <code>${esc(e.esperado)}</code> y se encontró <code>${esc(e.encontrado)}</code>.</div>`;
  } else if (d.errores_lexicos.length) {
    h += '<div class="aviso error">La estructura cumple la gramática, pero la cadena se rechaza por los errores léxicos (ver paso 2).</div>';
  } else {
    h += '<div class="aviso ok">Sintaxis correcta: la cadena pertenece al lenguaje L(G) de LER.</div>';
  }

  if (d.variables) {
    const v = d.variables;
    const rep = `EVENTO DE REPARTO: ${v.id}\n\nCARGA Y RECORRIDO\nDistancia: ${v.distancia} km\nCarga: ${v.carga} kg\n\nCONDICIONES\nTráfico: ${v.trafico}\nClima: ${v.clima}\n\nPROGRAMACIÓN\nHora prevista: ${v.hora}\nPrioridad: ${v.prioridad}`;
    const filas = Object.entries(v).map(([k, x]) => `<tr><td>${esc(NOMBRES[k] || k)}</td><td><code>${esc(String(x))}</code></td><td>${typeof x === "number" ? "numérica" : "categórica"}</td></tr>`).join("");
    h += `<div class="bloque-gris"><h3>Representación obtenida</h3><pre class="codigo">${esc(rep)}</pre>
      <p class="subt">Variables extraídas para el modelo predictivo</p>
      <div class="scroll"><table class="tabla-lex"><thead><tr><th>Variable</th><th>Valor</th><th>Tipo</th></tr></thead><tbody>${filas}</tbody></table></div></div>`;
  }

  if (d.derivacion) {
    const filas = d.derivacion.map((p, i) => {
      const reg = p.produccion === null ? "S" : p.produccion === "lexemas" ? "lexemas" : `P${p.produccion}`;
      return `<tr><td>${i ? "⇒" : ""}</td><td>${esc(p.forma)}</td><td class="regla">${reg}</td></tr>`;
    }).join("");
    h += `<div class="bloque-gris"><h3>Derivación por la izquierda</h3>
      <div class="scroll"><table class="deriv"><tbody>${filas}</tbody></table></div>
      <p class="nota">En cada paso se reemplaza el no terminal más a la izquierda por el cuerpo de su producción; el último paso sustituye cada token por su lexema.</p></div>`;
  }

  const arbol = d.arbol || d.arbol_parcial;
  if (d.svg) {
    h += `<div class="bloque-gris"><h3>${d.arbol ? "Árbol sintáctico" : "Árbol sintáctico parcial (hasta el error)"}</h3>
      ${grafico(d.svg, "claro")}
      <p class="leyenda">Óvalos violetas: no terminales · rectángulos verdes: terminales (tokens) · debajo: el lexema · rojo: punto del error.</p>
      <details class="detalle"><summary>Ver árbol en texto</summary><pre class="codigo">${esc(arbolTexto(arbol))}</pre></details></div>`;
  }
  $("sint-salida").innerHTML = h;
  $("sint-salida").querySelectorAll(".marco").forEach((m) => escalar(m, "ajustar"));
}

// ------------------------------------------------------------ 4. autómatas
function pintarAutomatas(tokens) {
  const vistos = new Map();
  (tokens && tokens.length ? tokens : CATALOGO.map((c) => ({token: c.token, er: c.regex, lexema: ""})))
    .forEach((t) => { if (!vistos.has(t.token)) vistos.set(t.token, t); });
  $("lista-automatas").innerHTML = [...vistos.values()].map((t) => {
    const er = t.er ?? CATALOGO.find((c) => c.token === t.token).regex;
    return `<details class="auto-card" data-token="${t.token}" data-lexema="${esc(t.lexema)}">
      <summary><b>${t.token}</b><span class="mono">${esc(er)}</span><span class="ver">Ver desarrollo</span></summary>
      <div class="auto-cuerpo"><p class="cargando">Generando autómatas…</p></div></details>`;
  }).join("");
  document.querySelectorAll(".auto-card").forEach((c) => c.addEventListener("toggle", () => { if (c.open) cargarAutomata(c); }));
}

const conj = (xs) => "{" + xs.join(", ") + "}";

function tablaHtml(a) {
  const t = a.tabla;
  const cab = "<th>Estado</th>" + t.columnas.map((c) => `<th>${esc(c)}</th>`).join("");
  const filas = t.filas.map((f) => `<tr><td class="est"><b>${f.inicial ? "→ " : ""}${f.final ? "* " : ""}${esc(f.estado)}</b></td>` +
    f.celdas.map((c) => `<td>${esc(c)}</td>`).join("") + "</tr>").join("");
  return `<div class="scroll"><table class="tabla-lex"><thead><tr>${cab}</tr></thead><tbody>${filas}</tbody></table></div>
    <p class="leyenda">→ inicial · * final · — sin transición</p>`;
}
const paso = (n, titulo, cuerpo) => `<div class="paso-formal"><span class="num">${n}</span><div><h4>${titulo}</h4>${cuerpo}</div></div>`;

async function cargarAutomata(card) {
  if (card.dataset.cargado) return;
  card.dataset.cargado = "1";
  const token = card.dataset.token, lexema = card.dataset.lexema;
  const cuerpo = card.querySelector(".auto-cuerpo");
  const r = await fetch(`/api/automata/${token}` + (lexema ? `?lexema=${encodeURIComponent(lexema)}` : ""));
  const d = await r.json();
  if (!r.ok) { cuerpo.innerHTML = `<div class="aviso error">${esc(d.error)}</div>`; return; }
  const n = d.afnd, a = d.afd;
  let h = paso(4, "Expresión regular", `
      <p class="dato"><b>Lexema:</b> <code>${esc(lexema || "—")}</code></p>
      <p class="dato"><b>Token:</b> ${esc(token)}</p>
      <p class="dato"><b>ER:</b> <code>${esc(d.er)}</code></p>`);
  h += paso(5, "AFND (construcción de Thompson)", `
      <p class="dato"><b>Inicial:</b> ${esc(n.inicial)} · <b>Final:</b> ${esc(conj(n.finales))} · ${n.estados.length} estados</p>
      ${grafico(n.svg)}
      <p class="subt">Transiciones</p><div class="trans">${n.transiciones.map((t) => `<span>${esc(t)}</span>`).join("")}</div>`);
  h += paso(6, "Conversión AFND → AFD (construcción de subconjuntos)", `
      <p class="nota">Cada estado del AFD es la ε-clausura de un conjunto de estados del AFND.</p>
      <div class="comp">${a.tabla.filas.map((f) => `<span>${esc(f.estado)} = ${esc(f.afnd)}</span>`).join("")}</div>`);
  h += paso(7, "AFD y tabla de transición", `${grafico(a.svg)}<p class="subt">Tabla de transición</p>${tablaHtml(a)}`);
  h += paso(8, "Transiciones del AFD", `<div class="trans">${a.transiciones.map((t) => `<span>${esc(t)}</span>`).join("")}</div>`);
  h += paso(9, "Quíntupla M = (Q, Σ, δ, q₀, F)", `<dl class="quint">
      <dt>Q</dt><dd>${esc(conj(a.estados))}</dd>
      <dt>Σ</dt><dd>${esc(a.alfabeto)}</dd>
      <dt>δ</dt><dd><pre>${esc(a.transiciones.join("\n"))}</pre></dd>
      <dt>q₀</dt><dd>${esc(a.inicial)}</dd>
      <dt>F</dt><dd>${esc(conj(a.finales))}</dd></dl>`);
  if (d.traza) {
    const pasos = d.traza.pasos.map((p) => `δ(${p.de}, ${p.simbolo}) = ${p.a}`).join("\n");
    h += paso("✓", `Recorrido de «${esc(lexema)}» en el AFD`, `
      <div class="aviso ${d.traza.acepta ? "ok" : "error"}">${d.traza.acepta ? "Aceptado: termina en un estado final." : "Rechazado por el autómata."}</div>
      <pre class="codigo">${esc(pasos)}</pre>`);
  }
  cuerpo.innerHTML = h;
  cuerpo.querySelectorAll(".marco").forEach((m) => escalar(m, "ajustar"));
}

// ------------------------------------------------------------ eventos
$("btn-analizar").onclick = analizarTodo;
$("btn-limpiar").onclick = () => {
  $("entrada").value = "";
  $("lex-estado").innerHTML = '<div class="aviso info">Ingresa una cadena LER para comenzar.</div>';
  $("tabla").querySelector("tbody").innerHTML = "";
  $("sint-salida").innerHTML = '<div class="aviso info">El resultado aparecerá al analizar una cadena.</div>';
  pintarAutomatas(null);
};
document.querySelectorAll("[data-caso]").forEach((b) => b.onclick = () => { $("entrada").value = EJEMPLOS[b.dataset.caso]; analizarTodo(); });
$("archivo").onchange = async (e) => {
  const f = e.target.files[0]; if (!f) return;
  $("archivo-nombre").textContent = f.name;
  $("entrada").value = await f.text(); e.target.value = ""; analizarTodo();
};
pintarAutomatas(null);
