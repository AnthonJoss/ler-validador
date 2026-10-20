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
    `<tr><td>${i + 1}</td><td><code>${esc(t.lexema)}</code></td><td>${t.token}</td><td>${t.categoria}</td><td>${t.linea}:${t.columna}</td></tr>`
  ).join("") || '<tr><td colspan="5" class="vacio">Sin tokens reconocidos</td></tr>';
}

$("btn-analizar").onclick = analizar;
$("btn-ejemplo").onclick = () => { $("entrada").value = EJEMPLOS.valido; analizar(); };
$("btn-limpiar").onclick = () => {
  $("entrada").value = ""; $("alertas").innerHTML = ""; $("resumen").textContent = "";
  $("tabla").querySelector("tbody").innerHTML = '<tr><td colspan="5" class="vacio">Esperando entrada…</td></tr>';
};
document.querySelectorAll(".chip").forEach(b => b.onclick = () => { $("entrada").value = EJEMPLOS[b.dataset.caso]; analizar(); });
$("archivo").onchange = async (e) => {
  const f = e.target.files[0]; if (!f) return;
  $("entrada").value = await f.text(); e.target.value = ""; analizar();
};
