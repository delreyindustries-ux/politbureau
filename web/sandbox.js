/* Polit Bureau — simulador electoral obert (21/11/2026).
 *
 * L'usuari mou el vot de cada partit (a tot Espanya o en una comunitat) i el
 * navegador reparteix els 350 escons provincia per provincia, com mana la llei:
 * d'Hondt amb un llindar del 3 % del vot valid de cada provincia.
 *
 * Com es porta un % estatal a cada provincia: swing proporcional. Si el PP
 * passa del 30 al 33 % a tot Espanya, a cada provincia es multiplica per 1,1.
 * Els partits sense lliscador ("altres") s'escalen perque cada provincia torni
 * a sumar 100. Aixi el % estatal que surt es exactament el del lliscador.
 * Un canvi en una comunitat es fa igual, pero nomes dins d'aquella comunitat.
 */
(function () {
  "use strict";
  var el = document.getElementById("sandbox-data");
  if (!el) return;
  var D = JSON.parse(el.textContent);
  var ES = (document.documentElement.lang || "ca").slice(0, 2) === "es";
  var T = ES ? {
    all: "Toda España", party: "Partido", vote: "Voto", seats: "Escaños", diff: "Cambio", others: "Otros",
    maj: "mayoría absoluta", right: "PP + Vox", left: "La suma que invistió a Sánchez en 2023",
    count: "escrutado", night: "▶ Noche electoral", stop: "■ Parar", reset: "Volver al punto de partida",
    copied: "Enlace copiado", share: "Copiar el enlace de este escenario", region: "Dónde cambias el voto",
    nobody: "Nadie tiene mayoría absoluta", has: "tiene mayoría absoluta", noseat: "sin escaño"
  } : {
    all: "Tot Espanya", party: "Partit", vote: "Vot", seats: "Escons", diff: "Canvi", others: "Altres",
    maj: "majoria absoluta", right: "PP + Vox", left: "La suma que va investir Sánchez el 2023",
    count: "escrutat", night: "▶ Nit electoral", stop: "■ Atura", reset: "Torna al punt de partida",
    copied: "Enllaç copiat", share: "Copia l'enllaç d'aquest escenari", region: "On canvies el vot",
    nobody: "Ningú no té majoria absoluta", has: "té majoria absoluta", noseat: "sense escó"
  };
  var P = D.provinces, META = D.meta, MAIN = D.main.now;
  var state = { base: "now", nat: {}, reg: {}, where: "" };
  var night = null;

  function fmt(x) { return (Math.round(x * 10) / 10).toFixed(1).replace(".", ","); }
  function name(c) {
    var l = (D.labels || {})[state.base] || {};
    return l[c] || (META[c] || {}).name || c.replace(/^\?/, "");
  }
  function color(c) { return (META[c] || {}).color || "#9e9e9e"; }

  /* % de cada partit en un conjunt de provincies, ponderat pel vot valid. */
  function weighted(provs, layerOf) {
    var tot = 0, out = {};
    provs.forEach(function (p) { tot += p.v; });
    provs.forEach(function (p) {
      var s = layerOf(p);
      for (var k in s) out[k] = (out[k] || 0) + s[k] * p.v / (tot || 1);
    });
    return out;
  }

  function baseShares(p) { return p[state.base] || {}; }
  function mag(p) { return (p.mm && p.mm[state.base]) || p.m; }
  function setBase(b) { state.base = b; MAIN = D.main[b] || D.main.now; }
  var BASE = {};
  (D.layers || ["now", "real"]).forEach(function (b) {
    BASE[b] = weighted(P, function (p) { return p[b] || {}; });
  });

  function swing(shares, from, to) {
    var out = {};
    for (var k in shares) out[k] = shares[k];
    var main = 0, other = 0;
    MAIN.forEach(function (k) {
      if (to[k] === undefined) return;
      var f = from[k] || 0;
      out[k] = f > 0 ? (shares[k] || 0) * to[k] / f : to[k];
    });
    for (var j in out) { if (MAIN.indexOf(j) >= 0) main += out[j]; else other += out[j]; }
    if (main >= 100) {
      for (var a in out) out[a] = MAIN.indexOf(a) >= 0 ? out[a] * 100 / main : 0;
    } else if (other > 0) {
      var kk = (100 - main) / other;
      for (var b in out) if (MAIN.indexOf(b) < 0) out[b] *= kk;
    }
    return out;
  }

  /* L'escenari: % de cada partit a cada provincia. */
  function scenario() {
    var target = {};
    MAIN.forEach(function (k) {
      target[k] = state.nat[k] !== undefined ? state.nat[k] : (BASE[state.base][k] || 0);
    });
    var shares = {};
    P.forEach(function (p) { shares[p.c] = swing(baseShares(p), BASE[state.base], target); });
    Object.keys(state.reg).forEach(function (r) {
      var provs = P.filter(function (p) { return p.r === r; });
      var cur = weighted(provs, function (p) { return shares[p.c]; });
      provs.forEach(function (p) { shares[p.c] = swing(shares[p.c], cur, state.reg[r]); });
    });
    return shares;
  }

  /* Llindar: 3 % a cada provincia al Congres. Als parlaments autonomics, el
     de cada llei (D.thr): a cada circumscripcio, a tota la comunitat
     (scope "region") o qualsevol dels dos (Canaries). */
  var THR = D.thr || { d: 3, r: null, scope: "district" };
  function passes(k, share, nat) {
    if (THR.scope === "region") return (nat[k] || 0) >= THR.rt;
    return share >= THR.d || (THR.r !== null && THR.r !== undefined && (nat[k] || 0) >= THR.r);
  }
  function dhondt(shares, seats, nat) {
    var run = [], won = {};
    for (var k in shares) if (passes(k, shares[k], nat || {})) { run.push(k); won[k] = 0; }
    for (var i = 0; i < seats; i++) {
      var best = null, q = -1;
      run.forEach(function (k) {
        var v = shares[k] / (won[k] + 1);
        if (v > q || (v === q && shares[k] > shares[best])) { q = v; best = k; }
      });
      if (best === null) break;
      won[best]++;
    }
    return won;
  }

  function allocate(shares, only) {
    var tot = {}, by = {};
    var nat = weighted(P, function (p) { return shares[p.c]; });
    P.forEach(function (p) {
      if (only && !only[p.c]) return;
      var w = dhondt(shares[p.c], mag(p), nat);
      by[p.c] = w;
      for (var k in w) if (w[k]) tot[k] = (tot[k] || 0) + w[k];
    });
    return { total: tot, by: by };
  }

  /* ------------------------------------------------------------ dibuix */
  var $ = function (s) { return document.querySelector(s); };

  function order(codes) {
    return codes.slice().sort(function (a, b) {
      return ((META[a] || {}).pos || 999) - ((META[b] || {}).pos || 999);
    });
  }

  function hemicycle(total, n) {
    var svg = $("#sb-hemi"); if (!svg) return;
    var sz = n > 200 ? 5.2 : n > 100 ? 6.5 : 8;
    var rows = n > 200 ? 12 : n > 100 ? 9 : n > 50 ? 7 : 5, pts = [], r0 = 60, r1 = 190, i, j;
    var per = [], sum = 0;
    for (i = 0; i < rows; i++) { var rr = r0 + (r1 - r0) * i / (rows - 1); per.push(rr); sum += rr; }
    var counts = per.map(function (rr) { return Math.round(n * rr / sum); });
    var diff = n - counts.reduce(function (a, b) { return a + b; }, 0);
    counts[rows - 1] += diff;
    per.forEach(function (rr, ii) {
      for (j = 0; j < counts[ii]; j++) {
        var a = Math.PI * (1 - j / Math.max(1, counts[ii] - 1));
        pts.push({ x: 200 + rr * Math.cos(a), y: 200 - rr * Math.sin(a), a: a });
      }
    });
    pts.sort(function (p, q) { return q.a - p.a; });
    var seq = [];
    order(Object.keys(total)).forEach(function (k) { for (var s = 0; s < total[k]; s++) seq.push(k); });
    var out = "";
    pts.forEach(function (p, ii) {
      var c = seq[ii];
      out += '<circle cx="' + p.x.toFixed(1) + '" cy="' + p.y.toFixed(1) + '" r="' + sz + '" fill="' +
             (c ? color(c) : "var(--line, #ddd)") + '"/>';
    });
    out += '<line x1="200" y1="8" x2="200" y2="200" stroke="currentColor" stroke-dasharray="3 3" opacity=".5"/>';
    svg.innerHTML = out;
  }

  function mapDraw(by, shares) {
    var g = $("#sb-map g"); if (!g || !Object.keys(D.paths || {}).length) return;
    var html = "";
    P.forEach(function (p) {
      var w = by[p.c], fill = "var(--line, #ddd)", tip = p.n;
      if (w) {
        var best = null;
        for (var k in w) if (w[k] && (best === null || w[k] > w[best] ||
            (w[k] === w[best] && shares[p.c][k] > shares[p.c][best]))) best = k;
        if (best) fill = color(best);
        tip += ": " + order(Object.keys(w)).filter(function (k) { return w[k]; })
          .map(function (k) { return name(k) + " " + w[k]; }).join(", ");
      }
      html += '<path d="' + D.paths[p.c] + '" fill="' + fill + '"><title>' + tip + "</title></path>";
    });
    g.innerHTML = html;
  }

  function table(total, base, nat) {
    var codes = MAIN.slice();
    Object.keys(total).forEach(function (k) { if (codes.indexOf(k) < 0) codes.push(k); });
    codes.sort(function (a, b) { return (total[b] || 0) - (total[a] || 0) || (nat[b] || 0) - (nat[a] || 0); });
    var h = "";
    codes.forEach(function (k) {
      var s = total[k] || 0, d = s - (base[k] || 0);
      if (!s && !(nat[k] >= 0.8)) return;
      h += "<tr><td><span class=\"sw\" style=\"background:" + color(k) + "\"></span>" + name(k) +
           "</td><td class=\"num\">" + fmt(nat[k] || 0) + " %</td><td class=\"num\"><b>" + s +
           "</b></td><td class=\"num\">" + (d > 0 ? "+" + d : d < 0 ? "−" + (-d) : "=") + "</td></tr>";
    });
    $("#sb-table tbody").innerHTML = h;
    var sum = function (list) { return list.reduce(function (a, k) { return a + (total[k] || 0); }, 0); };
    var lead = order(Object.keys(total)).sort(function (a, b) { return total[b] - total[a]; })[0];
    var h = "";
    if (D.blocs) {
      var R = sum(D.blocs.right), L = sum(D.blocs.left);
      h += "<span><b>" + R + "</b> " + T.right + (R >= D.majority ? " ✔" : "") + "</span>" +
           "<span><b>" + L + "</b> " + T.left + (L >= D.majority ? " ✔" : "") + "</span>";
    }
    h += "<span>" + (lead && total[lead] >= D.majority ? name(lead) + " " + T.has : T.nobody) +
         " (" + D.majority + ")</span>";
    $("#sb-blocs").innerHTML = h;
  }

  var BASESEATS = {};
  function baseSeats() {
    if (!BASESEATS[state.base]) {
      var keep = { nat: state.nat, reg: state.reg };
      state.nat = {}; state.reg = {};
      BASESEATS[state.base] = allocate(scenario()).total;
      state.nat = keep.nat; state.reg = keep.reg;
    }
    return BASESEATS[state.base];
  }

  function render() {
    var shares = scenario();
    var res = allocate(shares);
    var nat = weighted(P, function (p) { return shares[p.c]; });
    hemicycle(res.total, D.seats);
    mapDraw(res.by, shares);
    table(res.total, baseSeats(), nat);
    sliders(shares);
    writeHash();
  }

  /* ------------------------------------------------------------ controls */
  function current(shares) {
    if (!state.where) return weighted(P, function (p) { return shares[p.c]; });
    return weighted(P.filter(function (p) { return p.r === state.where; }),
                    function (p) { return shares[p.c]; });
  }

  function sliders(shares) {
    var box = $("#sb-sliders"), cur = current(shares);
    if (box.dataset.where !== state.where || box.dataset.base !== state.base || !box.children.length) {
      box.dataset.where = state.where; box.dataset.base = state.base;
      box.innerHTML = MAIN.map(function (k) {
        return '<label class="sb-row"><span class="sw" style="background:' + color(k) + '"></span>' +
          '<span class="sb-name">' + name(k) + '</span><input type="range" min="0" max="60" step="0.1" data-k="' +
          k + '"><output></output></label>';
      }).join("");
      box.querySelectorAll("input").forEach(function (inp) {
        inp.addEventListener("input", function () { move(inp.dataset.k, parseFloat(inp.value)); });
      });
    }
    box.querySelectorAll("input").forEach(function (inp) {
      var v = cur[inp.dataset.k] || 0;
      if (document.activeElement !== inp) inp.value = v;
      inp.nextElementSibling.textContent = fmt(v) + " %";
    });
  }

  function move(k, v) {
    stopNight();
    var shares = scenario(), cur = current(shares);
    var target = !state.where ? state.nat : (state.reg[state.where] || {});
    MAIN.forEach(function (j) { if (target[j] === undefined) target[j] = cur[j] || 0; });
    v = Math.max(0, Math.min(v, 99.5));
    target[k] = v;
    // Si la suma passa de 99,5 %, els altres partits amb barra baixen en
    // proporcio al que tenen: qui puja treu vot a tots, no a un de sol.
    var others = 0;
    MAIN.forEach(function (j) { if (j !== k) others += target[j]; });
    if (v + others > 99.5 && others > 0) {
      var f = (99.5 - v) / others;
      MAIN.forEach(function (j) { if (j !== k) target[j] *= f; });
    }
    if (state.where) state.reg[state.where] = target; else state.nat = target;
    render();
  }

  /* ------------------------------------------------------------ nit electoral */
  function stopNight() {
    if (night) { clearInterval(night.timer); night = null; $("#sb-night").textContent = T.night; $("#sb-count").textContent = ""; }
  }

  function runNight() {
    if (night) { stopNight(); render(); return; }
    var shares = scenario(), seed = 2911;
    var queue = P.map(function (p) { return p.c; });
    for (var i = queue.length - 1; i > 0; i--) {           // barreja amb llavor fixa
      seed = (seed * 9301 + 49297) % 233280;
      var j = Math.floor(seed / 233280 * (i + 1)), t = queue[i]; queue[i] = queue[j]; queue[j] = t;
    }
    var done = {}, totalV = P.reduce(function (a, p) { return a + p.v; }, 0), countedV = 0;
    night = { timer: null };
    $("#sb-night").textContent = T.stop;
    function step() {
      for (var n = 0; n < 2 && queue.length; n++) {
        var c = queue.shift(); done[c] = true;
        countedV += (P.filter(function (p) { return p.c === c; })[0] || {}).v || 0;
      }
      var res = allocate(shares, done);
      hemicycle(res.total, D.seats);
      mapDraw(res.by, shares);
      table(res.total, baseSeats(), weighted(P.filter(function (p) { return done[p.c]; }),
                                              function (p) { return shares[p.c]; }));
      $("#sb-count").textContent = fmt(100 * countedV / totalV) + " % " + T.count;
      if (!queue.length) { clearInterval(night.timer); night = null; $("#sb-night").textContent = T.night; }
    }
    step();
    night.timer = setInterval(step, 650);
  }

  /* ------------------------------------------------------------ enllac */
  function writeHash() {
    var o = { b: state.base };
    if (Object.keys(state.nat).length) o.n = round(state.nat);
    if (Object.keys(state.reg).length) {
      o.r = {};
      for (var r in state.reg) o.r[r] = round(state.reg[r]);
    }
    var s = (o.n || o.r || o.b !== "now") ? "#" + encodeURIComponent(JSON.stringify(o)) : " ";
    history.replaceState(null, "", s === " " ? location.pathname + location.search : s);
  }
  function round(o) { var x = {}; for (var k in o) x[k] = Math.round(o[k] * 10) / 10; return x; }
  function readHash() {
    try {
      var o = JSON.parse(decodeURIComponent(location.hash.slice(1)));
      if (D.main[o.b]) setBase(o.b);
      if (o.n) state.nat = o.n;
      if (o.r) state.reg = o.r;
    } catch (e) { /* sense escenari a l'enllac */ }
  }

  /* ------------------------------------------------------------ inici */
  function init() {
    readHash();
    var sel = $("#sb-where");
    if (!Object.keys(D.regions || {}).length) sel.parentNode.style.display = "none";
    if (!Object.keys(D.paths || {}).length && $("#sb-map")) $("#sb-map").style.display = "none";
    sel.innerHTML = '<option value="">' + T.all + "</option>" +
      Object.keys(D.regions).map(function (r) { return '<option value="' + r + '">' + D.regions[r] + "</option>"; }).join("");
    sel.addEventListener("change", function () { state.where = sel.value; render(); });
    document.querySelectorAll("input[name=sb-base]").forEach(function (r) {
      if (!D.main[r.value]) { r.parentNode.style.display = "none"; return; }
      r.checked = r.value === state.base;
      r.addEventListener("change", function () { setBase(r.value); state.nat = {}; state.reg = {}; stopNight(); render(); });
    });
    $("#sb-reset").addEventListener("click", function () { state.nat = {}; state.reg = {}; stopNight(); render(); });
    $("#sb-night").addEventListener("click", runNight);
    $("#sb-night").textContent = T.night;
    $("#sb-share").addEventListener("click", function () {
      writeHash();
      var done = function () { $("#sb-share").textContent = T.copied; setTimeout(function () { $("#sb-share").textContent = T.share; }, 2000); };
      if (navigator.clipboard) navigator.clipboard.writeText(location.href).then(done, done); else done();
    });
    render();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
