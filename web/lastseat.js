/* L'ultim esco, facil d'entendre (22/11/2026: "millora el repartiment de l'ultim
   esco perque sigui molt mes facil d'entendre i dona l'ultim diputat de cada
   partit que es queda fora i per quant, molt mes grafic i visual").

   PBLast.compute(percentatges, escons, vots_valids, opcions) fa la llei
   d'Hondt (o qualsevol metode de divisors) i, per a cada partit:
     - next: el seu proxim diputat, el primer que es queda fora: quants vots
       li falten si els altres no es mouen (vots nous, de l'abstencio), i a qui
       li prendria;
     - lose: l'ultim diputat que te: quants vots pot perdre abans de perdre'l,
       i qui se l'enduria.
   Si el partit no arriba al llindar (3 % a les generals) tambe hi compta.

   PBLast.ladder(...) dibuixa el repartiment d'una circumscripcio com una
   escala de barres (cada barra, vots / 1, 2, 3...: els N mes grans s'enduen
   els escons) i PBLast.parties(...) el grafic de tots els partits: a
   l'esquerra, el que pot perdre el seu ultim diputat; a la dreta, el que li
   falta per al seguent. Ho fan servir la pagina d'Espanya
   (templates/_seatgrid.html.j2) i el simulador (sandbox.js). */
(function () {
  "use strict";
  var ES = (document.documentElement.lang || "").indexOf("es") === 0;

  function th(n) { return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, "."); }
  function f2(x) { return (Math.round(x * 100) / 100).toFixed(2).replace(".", ","); }
  function ord(n) {
    if (ES) return n + ".º";
    return n + (n === 1 ? "r" : n === 2 ? "n" : n === 3 ? "r" : n === 4 ? "t" : "è");
  }
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;"); }

  function compute(sh, m, V, o) {
    o = o || {};
    var div = o.div || function (n) { return n + 1; };
    var thr = o.thr === undefined ? 3 : o.thr;           // null: llindar no provincial, no es calcula
    var ok = o.ok || function (k, x) { return thr === null || x >= thr; };
    var total = V || 100, unit = total / 100, v = {}, run = [], k;
    for (k in sh) {
      if (!(sh[k] > 0)) continue;
      v[k] = sh[k] * unit;
      if (ok(k, sh[k])) run.push(k);
    }
    var Q = [];
    run.forEach(function (x) {
      for (var i = 0; i < m; i++) Q.push({ k: x, i: i, d: div(i), q: v[x] / div(i) });
    });
    Q.sort(function (a, b) { return b.q - a.q || v[b.k] - v[a.k]; });
    var seq = Q.slice(0, m), won = {};
    seq.forEach(function (x) { won[x.k] = (won[x.k] || 0) + 1; });
    var round = V ? function (x) { return Math.max(1, Math.ceil(x + 1e-9)); } : function (x) { return Math.max(0.01, x); };
    var parties = Object.keys(v).filter(function (x) { return won[x] || sh[x] >= (o.min === undefined ? 0.5 : o.min); }).map(function (x) {
      var s = won[x] || 0, inRun = run.indexOf(x) >= 0;
      var others = Q.filter(function (y) { return y.k !== x; });
      var r = { k: x, s: s, pct: sh[x], v: v[x], run: inRun };
      // Per arribar al llindar sumant vots: (v + a) >= thr% de (total + a)
      var needT = (!inRun && thr) ? (thr / 100 * total - v[x]) / (1 - thr / 100) : 0;
      if (!inRun && !thr) {
        // llindar que no es provincial (simulador): no se sap que li falta
      } else if (m - s >= 1 && others.length >= m - s) {
        var T = others[m - s - 1];
        var need = T.q * div(s) - v[x];
        r.next = { need: round(Math.max(need, needT)), from: T.k, n: s + 1, thr: needT > need, q: v[x] / div(s), target: T.q, d: div(s) };
      } else if (!inRun && thr) {
        r.next = { need: round(needT), from: null, n: s + 1, thr: true, q: v[x] / div(s), target: v[x] / div(s), d: div(s) };
      }
      if (s > 0) {
        var U = others[m - s];
        var lose = U ? v[x] - U.q * div(s - 1) : Infinity;
        var loseT = thr ? (v[x] - thr / 100 * total) / (1 - thr / 100) : Infinity;
        var L = Math.min(lose, loseT);
        if (isFinite(L)) r.lose = { need: round(Math.max(0, L)), to: U ? U.k : null, n: s, thr: loseT < lose };
      }
      return r;
    });
    var last = seq[seq.length - 1] || null;
    var out = parties.filter(function (p) { return p.next && (!last || p.k !== last.k); })
      .sort(function (a, b) { return a.next.need - b.next.need; })[0] || null;
    return { seq: seq, won: won, v: v, parties: parties, last: last, first: out, votes: !!V, m: m, unit: unit };
  }

  function tie(R, x) { return x / R.unit < 0.02; }
  function amount(R, x) {
    if (tie(R, x)) return ES ? "empate" : "empat";
    return R.votes ? th(x) : f2(x) + " pt";
  }
  function votesWord(R, x) {
    if (tie(R, x)) return ES ? "≈0 votos (empate)" : "≈0 vots (empat)";
    if (!R.votes) return f2(x) + (ES ? " puntos" : " punts");
    return th(x) + (x === 1 ? (ES ? " voto" : " vot") : (ES ? " votos" : " vots"));
  }

  /* Escala d'una circumscripcio. o: {name, color, place, all} */
  function ladder(el, R, o) {
    if (!el) return;
    var m = R.seq.length;
    if (!m) { el.innerHTML = ""; return; }
    var name = o.name, color = o.color;
    var showAll = o.all || m <= 10;
    var outs = R.parties.filter(function (p) { return p.next; })
      .sort(function (a, b) { return a.next.need - b.next.need; }).slice(0, 4);
    var shown = [];
    R.seq.forEach(function (x, i) { if (showAll || i < 2 || i >= m - 5) shown.push(x); });
    var max = Math.max.apply(null, shown.map(function (x) { return x.q; }).concat(outs.map(function (p) { return Math.max(p.next.q, p.next.target); })));
    var cut = R.last.q;
    var W = function (q) { return (Math.max(0, q) / max * 100).toFixed(2); };
    var line = '<s class="ls-line" style="left:' + W(cut) + '%"></s>';
    var h = "";
    var L = R.last, F = R.first;
    // Frase resum
    h += '<p class="ls-sum">' + (ES ? "Último escaño (el " : "Últim escó (el ") + ord(m) + '): <b style="color:' + color(L.k) + '">' + esc(name(L.k)) + "</b>.";
    if (F) {
      h += " " + (ES ? "Primero que se queda fuera: " : "Primer que es queda fora: ") + '<b style="color:' + color(F.k) + '">' + esc(name(F.k)) + "</b>, " +
        (ES ? "le faltan " : "li falten ") + "<b>" + votesWord(R, F.next.need) + "</b>" +
        (F.next.thr ? (ES ? " (para llegar al 3 %)" : " (per arribar al 3 %)") : (ES ? " para quitárselo" : " per prendre-l'hi")) + ".";
    }
    h += "</p>";
    h += '<div class="ls">';
    R.seq.forEach(function (x, i) {
      if (!showAll && i === 2) {
        h += '<div class="ls-gap">… ' + (m - 7) + (ES ? " escaños más" : " escons més") +
          ' <button type="button" class="ls-all">' + (ES ? "verlos todos" : "veure'ls tots") + "</button></div>";
      }
      if (!(showAll || i < 2 || i >= m - 5)) return;
      var isLast = i === m - 1;
      h += '<div class="ls-r in' + (isLast ? " last" : "") + '"><div class="ls-t"><span class="ls-n">' + (i + 1) + '</span><span class="ls-p"><i style="background:' + color(x.k) + '"></i>' +
        esc(name(x.k)) + " <small>" + ord(x.i + 1) + "</small></span>" +
        (isLast ? '<span class="ls-tag">' + (ES ? "último escaño" : "últim escó") + "</span>" : "") +
        '<span class="ls-v">' + (R.votes ? th(R.v[x.k]) + " ÷ " + x.d + " = " : "") + "<b>" + amount(R, x.q) + "</b></span></div>" +
        '<div class="ls-b"><b style="width:' + W(x.q) + "%;background:" + color(x.k) + '"></b>' + line + "</div></div>";
    });
    h += '<div class="ls-cut"><span>' + (ES ? "Aquí se acaban los " + m + " escaños" : "Aquí s'acaben els " + m + " escons") + "</span></div>";
    outs.forEach(function (p) {
      var n = p.next, gapL = W(n.q), gapW = (Math.max(0, n.target - n.q) / max * 100).toFixed(2);
      h += '<div class="ls-r out"><div class="ls-t"><span class="ls-n">–</span><span class="ls-p"><i style="background:' + color(p.k) + '"></i>' +
        esc(name(p.k)) + " <small>" + ord(n.n) + "</small></span>" +
        '<span class="ls-v">' + (tie(R, n.need) ? "<b>" + amount(R, n.need) + "</b>" : (ES ? "le faltan " : "li falten ") + "<b>" + amount(R, n.need) + "</b>") +
        (n.thr ? ' <small>' + (ES ? "(3 %)" : "(3 %)") + "</small>" : "") + "</span></div>" +
        '<div class="ls-b"><b style="width:' + gapL + "%;background:" + color(p.k) + '"></b><u style="left:' + gapL + "%;width:" + gapW + "%;border-color:" + color(p.k) + '"></u>' + line + "</div></div>";
    });
    h += "</div>";
    h += '<p class="ls-how">' + (ES
      ? "Cómo se reparte: los votos de cada partido se dividen entre 1, 2, 3… y los " + m + " resultados más grandes se llevan los escaños. Cada barra es uno; la raya vertical marca el del último escaño. La parte rayada es lo que le falta a cada partido para pasarla" + (R.votes ? " (en votos hay que multiplicarla por el divisor)" : "") + "."
      : "Com es reparteix: els vots de cada partit es divideixen entre 1, 2, 3… i els " + m + " resultats més grans s'enduen els escons. Cada barra n'és un; la ratlla vertical marca el de l'últim escó. La part ratllada és el que li falta a cada partit per passar-la" + (R.votes ? " (en vots, cal multiplicar-la pel divisor)" : "") + ".") +
      (R.votes ? (ES ? " Votos aproximados." : " Vots aproximats.") : "") + "</p>";
    el.innerHTML = h;
    var b = el.querySelector(".ls-all");
    if (b) b.addEventListener("click", function () { o.all = true; ladder(el, R, o); });
  }

  /* Grafic de partits. list: [{c, n (nom), a (abreviatura), R}]. o: {name, color, nat, go(c)} */
  function parties(el, list, o) {
    if (!el) return;
    var agg = {};
    list.forEach(function (it) {
      it.R.parties.forEach(function (p) {
        var g = agg[p.k] || (agg[p.k] = { k: p.k, seats: 0, nexts: [], loses: [] });
        g.seats += p.s;
        if (p.next) g.nexts.push({ it: it, x: p.next });
        if (p.lose) g.loses.push({ it: it, x: p.lose });
      });
    });
    var rows = Object.keys(agg).map(function (k) { return agg[k]; }).filter(function (g) {
      return g.seats > 0 || ((o.nat || {})[g.k] || 0) >= 1;
    });
    rows.forEach(function (g) {
      g.nexts.sort(function (a, b) { return a.x.need - b.x.need; });
      g.loses.sort(function (a, b) { return a.x.need - b.x.need; });
    });
    rows = rows.filter(function (g) { return g.nexts.length || g.loses.length; });
    rows.sort(function (a, b) { return b.seats - a.seats || ((o.nat || {})[b.k] || 0) - ((o.nat || {})[a.k] || 0); });
    if (!rows.length) { el.innerHTML = ""; return; }
    var vals = [];
    rows.forEach(function (g) {
      if (g.nexts[0]) vals.push(g.nexts[0].x.need);
      if (g.loses[0]) vals.push(g.loses[0].x.need);
    });
    var cap = Math.max.apply(null, vals) || 1;
    var S = function (x) { return (Math.sqrt(Math.min(x, cap) / cap) * 68 + 2).toFixed(1); };
    var votes = list[0] && list[0].R.votes;
    var name = o.name, color = o.color;
    var go = function (it, txt) {
      return o.go ? '<button type="button" class="lp-go" data-c="' + esc(it.c) + '">' + esc(txt) + "</button>" : esc(txt);
    };
    var h = '<div class="lp-head"><span></span><span class="lp-hl">← ' + (ES ? "su último diputado: lo que puede perder" : "el seu últim diputat: el que pot perdre") +
      '</span><span class="lp-hr">' + (ES ? "su próximo diputado: lo que le falta" : "el seu pròxim diputat: el que li falta") + " →</span></div>";
    rows.forEach(function (g) {
      var N = g.nexts[0], Lo = g.loses[0];
      h += '<div class="lp-r"><div class="lp-p"><i style="background:' + color(g.k) + '"></i><span>' + esc(name(g.k)) + "</span><b>" + g.seats + "</b></div>";
      h += '<div class="lp-l">' + (Lo ? '<em>' + go(Lo.it, Lo.it.a) + " " + (tie(list[0].R, Lo.x.need) ? "" : "−") + amount(list[0].R, Lo.x.need) + '</em><b style="width:' + S(Lo.x.need) + "%;background:" + color(g.k) + '"></b>' : '<em class="lp-none">–</em>') + "</div>";
      h += '<div class="lp-rt">' + (N ? '<b style="width:' + S(N.x.need) + "%;background:" + color(g.k) + '"></b><em>' + go(N.it, N.it.a) + " " + (tie(list[0].R, N.x.need) ? "" : "+") + amount(list[0].R, N.x.need) + "</em>" : '<em class="lp-none">–</em>') + "</div>";
      // Frase
      var t = [];
      var R0 = list[0].R, here = function (z) { return " <small>(" + (ES ? "el " + ord(z.x.n) + " de la provincia" : "el " + ord(z.x.n) + " de la província") + ")</small>"; };
      if (Lo) t.push((ES ? "<b>Su " + ord(g.seats) + " diputado</b>, en " : "<b>El seu " + ord(g.seats) + " diputat</b>, a ") + go(Lo.it, Lo.it.n) + here(Lo) + ": " +
        (Lo.x.thr ? (ES ? "si pierde " + votesWord(list[0].R, Lo.x.need) + " baja del 3 % y se queda sin nada" : "si en perd " + votesWord(list[0].R, Lo.x.need) + " baixa del 3 % i es queda sense res")
          : (ES ? "lo pierde con " + votesWord(list[0].R, Lo.x.need) + " menos" : "el perd amb " + votesWord(list[0].R, Lo.x.need) + " menys") +
            (Lo.x.to ? (ES ? " (se lo lleva " : " (se l'enduria ") + esc(name(Lo.x.to)) + ")" : "")) + ".");
      if (N) t.push((ES ? "<b>El " + ord(g.seats + 1) + "</b>, en " : "<b>El " + ord(g.seats + 1) + "</b>, a ") + go(N.it, N.it.n) + here(N) + ": " +
        (ES ? "le faltan " : "li falten ") + votesWord(list[0].R, N.x.need) +
        (N.x.thr ? (ES ? " (tiene que llegar al 3 %)" : " (ha d'arribar al 3 %)") : (N.x.from ? (ES ? " (se lo quitaría a " : " (l'hi prendria a ") + esc(name(N.x.from)) + ")" : "")) + "." +
        (g.nexts.length > 1 ? " " + (ES ? "Después: " : "Després: ") + g.nexts.slice(1, 3).map(function (z) { return go(z.it, z.it.n) + " " + amount(list[0].R, z.x.need); }).join(", ") + "." : ""));
      h += '<div class="lp-d">' + t.join(" ") + "</div></div>";
    });
    h += '<p class="ls-how">' + (ES
      ? "Cada partido por separado y sin que los demás se muevan: votos que tendría que sumar (de la abstención, por ejemplo) para ganar un diputado más, y votos que puede perder antes de perder el último que tiene. Barras en escala de raíz cuadrada."
      : "Cada partit per separat i sense que els altres es moguin: vots que hauria de sumar (de l'abstenció, per exemple) per guanyar un diputat més, i vots que pot perdre abans de perdre l'últim que té. Barres en escala d'arrel quadrada.") +
      (votes ? (ES ? " Votos aproximados." : " Vots aproximats.") : "") + "</p>";
    el.innerHTML = h;
    if (o.go) el.querySelectorAll(".lp-go").forEach(function (b) {
      b.addEventListener("click", function () { o.go(b.getAttribute("data-c")); });
    });
  }

  window.PBLast = { compute: compute, ladder: ladder, parties: parties, ord: ord, th: th };

  /* Pagina d'Espanya: dades a <script id="ls-data">. */
  function initPage() {
    var node = document.getElementById("ls-data");
    if (!node) return;
    var D = JSON.parse(node.textContent);
    var name = function (k) { return (D.meta[k] || {}).n || k; };
    var color = function (k) { return (D.meta[k] || {}).c || "#888"; };
    var list = D.p.map(function (p) { return { c: p.c, n: p.n, a: p.a, R: compute(p.s, p.m, p.v, { thr: D.thr }) }; });
    var byC = {};
    list.forEach(function (it) { byC[it.c] = it; });
    var panel = document.getElementById("ls-panel");
    var grid = document.querySelector(".sg[data-ls]");
    function pick(c, scroll) {
      var it = byC[c];
      if (!it || !panel) return;
      panel.hidden = false;
      panel.querySelector(".ls-title").textContent = it.n + " · " + it.R.m + " " + (it.R.m === 1 ? (ES ? "escaño" : "escó") : (ES ? "escaños" : "escons"));
      ladder(panel.querySelector(".ls-body"), it.R, { name: name, color: color });
      if (grid) grid.querySelectorAll(".sg-t").forEach(function (t) { t.classList.toggle("on", t.getAttribute("data-c") === c); });
      if (scroll) panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
    if (grid) {
      grid.addEventListener("click", function (e) {
        var t = e.target.closest(".sg-t[data-c]");
        if (t) pick(t.getAttribute("data-c"), true);
      });
      grid.addEventListener("keydown", function (e) {
        var t = e.target.closest(".sg-t[data-c]");
        if (t && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); pick(t.getAttribute("data-c"), true); }
      });
    }
    document.querySelectorAll(".sg-close [data-c]").forEach(function (b) {
      b.addEventListener("click", function () { pick(b.getAttribute("data-c"), true); });
    });
    parties(document.getElementById("lp-chart"), list, { name: name, color: color, nat: D.nat, go: function (c) { pick(c, true); } });
    if (D.first) pick(D.first, false);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initPage);
  else initPage();
})();
