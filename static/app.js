const $ = (id) => document.getElementById(id);
const esc = (s) => s.replace(/[&<>"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

fetch("/api/hola").then(r => r.json()).then(d => { $("hola").textContent = "✔ " + d.mensaje; })
  .catch(() => { $("hola").textContent = "Backend no disponible"; });

async function analizar() {
  const texto = $("entrada").value;
  const res = await fetch("/api/analizar", {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({texto}),
  });
  const d = await res.json();
  if (!res.ok) { $("alertas").innerHTML = `<div class="alerta">${esc(d.error)}</div>`; return; }
  $("resumen").textContent = `${d.total} tokens · ${d.errores.length} errores`;
  $("alertas").innerHTML = d.errores.length
    ? d.errores.map(e => `<div class="alerta">Error léxico en ${e.linea}:${e.columna} — <code>${esc(e.lexema)}</code>: ${esc(e.mensaje)}</div>`).join("")
    : '<div class="alerta ok">Sin errores léxicos: todos los lexemas fueron reconocidos.</div>';
  $("tabla").querySelector("tbody").innerHTML = d.tokens.map((t, i) =>
    `<tr class="clic" data-token="${t.token}" data-lexema="${esc(t.lexema)}"><td>${i + 1}</td><td><code>${esc(t.lexema)}</code></td><td>${t.token}</td><td>${t.categoria}</td><td><code>${esc(t.er)}</code></td><td>${t.linea}:${t.columna}</td></tr>`
  ).join("") || '<tr><td colspan="6" class="vacio">Sin tokens reconocidos</td></tr>';
  $("tabla").querySelectorAll("tr.clic").forEach(tr => tr.onclick = () => {
    $("sel-token").value = tr.dataset.token; $("lexema-traza").value = tr.dataset.lexema;
    generarAutomata(); $("etapa2").scrollIntoView({behavior: "smooth"});
  });
}

$("btn-analizar").onclick = analizar;
$("btn-ejemplo").onclick = () => { $("entrada").value = EJEMPLOS.valido; analizar(); };
$("btn-limpiar").onclick = () => {
  $("entrada").value = ""; $("alertas").innerHTML = ""; $("resumen").textContent = "";
  $("tabla").querySelector("tbody").innerHTML = '<tr><td colspan="6" class="vacio">Esperando entrada…</td></tr>';
};
document.querySelectorAll(".chip").forEach(b => b.onclick = () => { $("entrada").value = EJEMPLOS[b.dataset.caso]; analizar(); });
$("archivo").onchange = async (e) => {
  const f = e.target.files[0]; if (!f) return;
  $("entrada").value = await f.text(); e.target.value = ""; analizar();
};

// ---------------------------------------------------------------- Etapa 2
const sub = (n) => String(n).replace(/\d+/g, (d) => d.split("").map((c) => "₀₁₂₃₄₅₆₇₈₉"[c]).join(""));
const lista = (xs) => "{" + xs.join(", ") + "}";

function quintupla(a) {
  const q = a.estados.map(sub).join(", ");
  return `<pre class="quint">M = (Q, Σ, δ, q₀, F)
Q  = {${esc(q)}}
Σ  = {${esc(a.alfabeto)}}
δ  : ver tabla y lista de transiciones
q₀ = ${esc(sub(a.inicial))}
F  = ${lista(a.finales.map(sub))}</pre>`;
}

function tablaTransiciones(a, extra) {
  const t = a.tabla;
  const cab = `<th>Estado</th>${extra ? "<th>Estados del AFND</th>" : ""}` + t.columnas.map((c) => `<th>${esc(c)}</th>`).join("");
  const filas = t.filas.map((f) => {
    const marca = (f.inicial ? "→" : "") + (f.final ? "*" : "");
    return `<tr><td><b>${marca} ${esc(f.estado)}</b></td>${extra ? `<td><code>${esc(f.afnd)}</code></td>` : ""}` +
      f.celdas.map((c) => `<td>${esc(c)}</td>`).join("") + "</tr>";
  }).join("");
  return `<div class="scroll"><table><thead><tr>${cab}</tr></thead><tbody>${filas}</tbody></table></div>
    <p class="small">→ estado inicial · * estado de aceptación · «—» sin transición (estado de error implícito).</p>`;
}

function bloqueAutomata(a, titulo, esAfd) {
  return `<h3>${titulo}</h3>
    <h4>Quíntupla</h4>${quintupla(a)}
    <h4>Gráfico</h4><div class="grafo">${a.svg}</div>
    <h4>Tabla de transiciones</h4>${tablaTransiciones(a, esAfd)}
    <h4>Transiciones (${a.transiciones.length})</h4>
    <details><summary>Ver lista δ</summary><pre class="quint">${esc(a.transiciones.join("\n"))}</pre></details>`;
}

function trazaHtml(t, lexema) {
  const pasos = t.pasos.map((p) => `δ(${sub(p.de)}, ${esc(p.simbolo)}) = ${sub(p.a)}`).join("\n");
  return `<h3>Recorrido de «${esc(lexema)}» en el AFD</h3>
    <div class="alerta ${t.acepta ? "ok" : ""}">${t.acepta ? "Aceptado" : "Rechazado"} por el autómata.</div>
    <pre class="quint">${pasos}</pre>`;
}

async function generarAutomata() {
  const token = $("sel-token").value, lexema = $("lexema-traza").value.trim();
  const res = await fetch(`/api/automata/${token}` + (lexema ? `?lexema=${encodeURIComponent(lexema)}` : ""));
  const d = await res.json();
  if (!res.ok) { $("auto-salida").innerHTML = `<div class="alerta">${esc(d.error)}</div>`; return; }
  $("auto-salida").innerHTML =
    `<h3>Expresión regular de <code>${d.token}</code></h3><pre class="quint">${esc(d.er)}</pre>` +
    bloqueAutomata(d.afnd, `AFND (Thompson) · ${d.afnd.estados.length} estados`, false) +
    bloqueAutomata(d.afd, `AFD (subconjuntos) · ${d.afd.estados.length} estados`, true) +
    (d.traza ? trazaHtml(d.traza, lexema) : "");
}
$("btn-auto").onclick = generarAutomata;
$("sel-token").onchange = generarAutomata;
generarAutomata();
