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
  var state = { base: "now", nat: {}, reg: {}, where: "", t: null, tm: "cis", coal: [] };
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

  /* Participacio (22/11/2026). D.turnout.factors[T][partit] = quant es
     multiplica el vot del partit si la participacio es T % en lloc de la del
     2023 (model de votant probable amb les microdades del CIS: vegeu
     src/politbureau/participacio.py). S'aplica al punt de partida de les
     enquestes d'avui, abans dels lliscadors: si fixes un partit amb el seu
     lliscador, la participacio ja no el mou. */
  function turnoutOn() { return !!(D.turnout && state.base === "now" && state.t !== null); }
  function baseShares(p) {
    var s = p[state.base] || {};
    if (!turnoutOn()) return s;
    var g = turnoutFactors(p), out = {}, before = 0, after = 0, k;
    for (k in s) { before += s[k]; out[k] = s[k] * (g[k] || 1); after += out[k]; }
    if (after) for (k in out) out[k] *= before / after;
    return out;
  }
  /* Dos models: "cis" (votant probable, factors calculats a Python) i
     "classic": la participacio alta afavoreix l'esquerra. En el classic, el
     pes de l'esquerra dins de la suma esquerra + dreta puja D.turnout.classic.slope
     punts per cada punt de participacio per sobre del 2023 (la mida de
     l'abril del 2019) i baixa igual per sota; els altres partits no es mouen. */
  var FCACHE = {};
  function turnoutFactors(p) {
    var C = D.turnout.classic;
    if (state.tm !== "classic" || !C) {
      // Model CIS: factors estatals, i els de la comunitat on n'hi ha (encongits
      // cap a l'estatal a participacio.py).
      var g = D.turnout.factors[String(state.t)] || {};
      var reg = p && D.turnout.regional && D.turnout.regional[p.r];
      var gr = reg && reg[String(state.t)];
      if (!gr) return g;
      var m = {};
      for (var k in g) m[k] = g[k];
      for (var j in gr) m[j] = gr[j];
      return m;
    }
    var key = "c" + state.t;
    if (FCACHE[key]) return FCACHE[key];
    var nat = BASE.now || {}, L = 0, R = 0, g = {};
    C.left.forEach(function (k) { L += nat[k] || 0; });
    C.right.forEach(function (k) { R += nat[k] || 0; });
    var sum = L + R;
    if (!L || !R) return {};
    var Lt = L + C.slope * (state.t - D.turnout.ref) * sum / 100;
    Lt = Math.max(0.02 * sum, Math.min(0.98 * sum, Lt));
    C.left.forEach(function (k) { g[k] = Lt / L; });
    C.right.forEach(function (k) { g[k] = (sum - Lt) / R; });
    FCACHE[key] = g;
    return g;
  }
  var BASE_T = {};
  function baseNat() {
    if (!turnoutOn()) return BASE[state.base];
    var key = state.base + "|" + state.t + "|" + state.tm;
    if (!BASE_T[key]) BASE_T[key] = weighted(P, baseShares);
    return BASE_T[key];
  }
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
    // El total es mante el del punt de partida: 100 a les provincies, pero una
    // mitjana d'enquestes pot sumar 100,4 (Suecia) o 79,5 (Croacia, amb
    // indecisos). Forcar-lo a 100 movia partits per sobre o per sota del
    // llindar sense que ningu toques res.
    var cap = 0;
    for (var c0 in shares) cap += shares[c0];
    if (!cap) cap = 100;
    if (main >= cap) {
      for (var a in out) out[a] = MAIN.indexOf(a) >= 0 ? out[a] * cap / main : 0;
    } else if (other > 0) {
      var kk = (cap - main) / other;
      for (var b in out) if (MAIN.indexOf(b) < 0) out[b] *= kk;
    }
    return out;
  }

  /* L'escenari: % de cada partit a cada provincia. */
  function scenario() {
    var target = {};
    MAIN.forEach(function (k) {
      target[k] = state.nat[k] !== undefined ? state.nat[k] : (baseNat()[k] || 0);
    });
    var shares = {};
    var from = baseNat();
    P.forEach(function (p) { shares[p.c] = swing(baseShares(p), from, target); });
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

  /* Parlaments estrangers (D.method): repartiment a escala de tot el pais amb
     el metode de cada llei, el mateix que model/seats.apportion: d'Hondt,
     Sainte-Lague amb el primer divisor de cada pais, resta mes gran (Hare o
     Droop) i la prima grega. El llindar es sobre el % del total. */
  function apportion(shares, seats) {
    var M = D.method, res = {}, run = {}, k;
    for (k in shares) { res[k] = 0; if (shares[k] >= M.thr) run[k] = shares[k]; }
    var keys = Object.keys(run);
    if (!keys.length) return res;
    if (M.bonus === "gr") {
      var top = keys.reduce(function (a, b) { return run[b] > run[a] ? b : a; });
      if (run[top] >= 25) {
        var extra = Math.min(50, 20 + Math.floor((Math.min(run[top], 40) - 25) / 0.5));
        res[top] += extra; seats -= extra;
      }
    }
    if (M.name === "hare" || M.name === "droop") {
      var total = keys.reduce(function (a, b) { return a + run[b]; }, 0);
      var q = M.name === "hare" ? total / seats : total / (seats + 1), got = {}, used = 0;
      keys.forEach(function (x) { got[x] = Math.floor(run[x] / q); used += got[x]; });
      keys.slice().sort(function (a, b) { return (run[b] / q - got[b]) - (run[a] / q - got[a]); })
        .slice(0, Math.max(0, seats - used)).forEach(function (x) { got[x]++; });
      keys.forEach(function (x) { res[x] += got[x]; });
      return res;
    }
    var won = {}; keys.forEach(function (x) { won[x] = 0; });
    var div = function (n) { return M.name === "sainte_lague" ? (n === 0 ? (M.first || 1) : 2 * n + 1) : n + 1; };
    for (var i = 0; i < seats; i++) {
      var best = null, bq = -1;
      keys.forEach(function (x) {
        var qq = run[x] / div(won[x]);
        if (qq > bq || (qq === bq && run[x] > run[best])) { bq = qq; best = x; }
      });
      won[best]++;
    }
    keys.forEach(function (x) { res[x] += won[x]; });
    return res;
  }

  function allocate(shares, only) {
    var tot = {}, by = {};
    var nat = weighted(P, function (p) { return shares[p.c]; });
    P.forEach(function (p) {
      if (only && !only[p.c]) return;
      var w = D.method ? apportion(shares[p.c], mag(p)) : dhondt(shares[p.c], mag(p), nat);
      by[p.c] = w;
      for (var k in w) if (w[k]) tot[k] = (tot[k] || 0) + w[k];
    });
    return { total: tot, by: by };
  }

  /* ------------------------------------------------------------ l'ultim esco
     Repetim el repartiment d'una circumscripcio guardant l'ordre en que surt
     cada esco (22/11/2026). Serveix el mateix metode que allocate(): d'Hondt
     amb el llindar de la llei a Espanya, i als parlaments estrangers d'Hondt,
     Sainte-Lague (amb el primer divisor de cada pais) o resta mes gran.
     Tres marges, en punts de vot de la circumscripcio:
       - "traspas": vot que hauria de passar del qui te l'ultim esco al
         primer que es queda fora perque l'esco canvies de mans;
       - "sol": el que hauria de pujar el segon sense treure vot a ningu;
       - "pot perdre": el que pot baixar el primer abans de perdre'l.
     Amb dos quocients l/dl i n/dn, el traspas x compleix (n+x)/dn = (l-x)/dl,
     d'on x = (dn*l - dl*n)/(dl+dn). */
  function divOf(n) {
    var M = D.method;
    return M && M.name === "sainte_lague" ? (n === 0 ? (M.first || 1) : 2 * n + 1) : n + 1;
  }
  function lastSeat(sh, m, nat) {
    var M = D.method, run = {}, below = {}, k;
    for (k in sh) {
      if (!(sh[k] > 0)) continue;
      if (M ? sh[k] >= M.thr : passes(k, sh[k], nat)) run[k] = sh[k]; else below[k] = sh[k];
    }
    var keys = Object.keys(run);
    if (!keys.length || !m) return null;
    var thr = M ? M.thr : (THR.scope === "region" ? THR.rt : THR.d);
    var bonus = 0;
    if (M && M.bonus === "gr") {
      var top = keys.reduce(function (a, b) { return run[b] > run[a] ? b : a; });
      if (run[top] >= 25) bonus = Math.min(50, 20 + Math.floor((Math.min(run[top], 40) - 25) / 0.5));
    }
    if (M && (M.name === "hare" || M.name === "droop")) {
      m -= bonus;
      var total = keys.reduce(function (a, b) { return a + run[b]; }, 0);
      var quota = M.name === "hare" ? total / m : total / (m + 1), used = 0, got = {};
      keys.forEach(function (x) { got[x] = Math.floor(run[x] / quota); used += got[x]; });
      var rem = keys.slice().sort(function (a, b) { return (run[b] / quota - got[b]) - (run[a] / quota - got[a]); });
      var extra = m - used;
      if (extra < 1 || extra >= rem.length) return { lr: true, quota: quota };
      var lk = rem[extra - 1], rk = rem[extra];
      var rl = run[lk] / quota - got[lk], rr = run[rk] / quota - got[rk];
      return { lr: true, quota: quota, bonus: bonus, last: { k: lk, r: rl }, rival: { k: rk, r: rr },
               transfer: (rl - rr) * quota / 2 };
    }
    var won = {}, seq = [];
    keys.forEach(function (x) { won[x] = 0; });
    for (var i = 0; i < m - bonus; i++) {
      var best = null, bq = -1;
      keys.forEach(function (x) {
        var q = run[x] / divOf(won[x]);
        if (q > bq || (q === bq && run[x] > run[best])) { bq = q; best = x; }
      });
      seq.push({ k: best, q: bq, d: divOf(won[best]) });
      won[best]++;
    }
    var next = keys.map(function (x) { return { k: x, q: run[x] / divOf(won[x]), d: divOf(won[x]) }; })
      .sort(function (a, b) { return b.q - a.q; });
    var out = { seq: seq, next: next, bonus: bonus, run: run };
    var last = seq[seq.length - 1];
    if (!last) return out;
    out.last = last;
    var rival = next.filter(function (x) { return x.k !== last.k; })[0];
    if (rival) {
      var l = run[last.k], n = run[rival.k];
      out.rival = rival;
      out.transfer = Math.max(0, (rival.d * l - last.d * n) / (last.d + rival.d));
      out.gain = Math.max(0, rival.d * last.q - n);
      out.lose = Math.max(0, l - last.d * rival.q);
    }
    // Qui hauria entrat si hagues passat el llindar.
    var cut = Object.keys(below).filter(function (x) { return below[x] / divOf(0) > last.q; })
      .sort(function (a, b) { return below[b] - below[a]; })[0];
    if (cut && thr) out.cut = { k: cut, need: thr - below[cut], thr: thr };
    return out;
  }
  function fmtM(x) { return x < 0.01 ? (Math.round(x * 1000) / 1000).toFixed(3).replace(".", ",") : fmt2(x); }
  function pts(x) { return fmtM(x) + " " + (Math.abs(x - 1) < 0.005 ? (ES ? "punto" : "punt") : (ES ? "puntos" : "punts")); }
  function votes(x, p) {
    if (!D.votes || !p.v) return "";
    var v = Math.max(1, Math.round(x * p.v / 100 * (turnoutOn() ? state.t / D.turnout.ref : 1)));
    return " (≈ " + String(v).replace(/\B(?=(\d{3})+(?!\d))/g, ".") + (ES ? " votos)" : " vots)");
  }
  function lastInfo(p) {
    if (!LAST || !LAST.by[p.c]) return null;
    var nat = weighted(P, function (x) { return LAST.shares[x.c]; });
    return lastSeat(LAST.shares[p.c], mag(p), nat);
  }

  /* L'ultim esco facil d'entendre (22/11/2026): web/lastseat.js. Nomes amb
     metodes de divisors sense prima; amb resta mes gran o prima, el d'abans. */
  function lsOf(p) {
    if (!window.PBLast || !LAST || !LAST.by[p.c]) return null;
    var M = D.method;
    if (M && (M.name === "hare" || M.name === "droop" || M.bonus)) return null;
    LAST.ls = LAST.ls || {};
    if (LAST.ls[p.c] !== undefined) return LAST.ls[p.c];
    if (!LAST.nat) LAST.nat = weighted(P, function (x) { return LAST.shares[x.c]; });
    var nat = LAST.nat;
    var V = D.votes && p.v ? p.v * (turnoutOn() ? state.t / D.turnout.ref : 1) : null;
    var simple = !M && THR.scope !== "region" && (THR.r === null || THR.r === undefined);
    var thr = M ? M.thr : (simple ? THR.d : null);
    var R = window.PBLast.compute(LAST.shares[p.c] || {}, mag(p), V, {
      div: divOf, thr: thr,
      ok: function (k, x) { return M ? x >= M.thr : passes(k, x, nat); }
    });
    LAST.ls[p.c] = R.seq.length ? R : null;
    return LAST.ls[p.c];
  }
  function lsNeed(R) {
    var x = R.first.next.need;
    if (x / R.unit < 0.02) return ES ? "empate" : "empat";
    return R.votes ? window.PBLast.th(x) : f2(x);
  }
  function lsUnit(R) { return R.votes ? (ES ? " votos" : " vots") : (ES ? " puntos" : " punts"); }

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
      var dim = state.coal.length && c && state.coal.indexOf(c) < 0;
      out += '<circle cx="' + p.x.toFixed(1) + '" cy="' + p.y.toFixed(1) + '" r="' + sz + '" fill="' +
             (c ? color(c) : "var(--line, #ddd)") + '"' + (dim ? ' fill-opacity=".18"' : "") + "/>";
    });
    out += '<line x1="200" y1="8" x2="200" y2="200" stroke="currentColor" stroke-dasharray="3 3" opacity=".5"/>';
    svg.innerHTML = out;
  }

  function mapDraw(by, shares) {
    var g = $("#sb-map g"); if (!g || !Object.keys(D.paths || {}).length) return;
    var html = "";
    P.forEach(function (p) {
      var w = by[p.c], fill = "var(--line, #ddd)", tip = p.n, op = 1;
      if (w && mapMode === "last") {
        var L = lastInfo(p);
        if (L && L.last) {
          fill = color(L.last.k);
          var tr = L.transfer;
          op = tr === undefined ? 1 : Math.max(0.3, 1 - tr / 4);
          tip += ": " + (ES ? "último escaño, " : "últim escó, ") + name(L.last.k) +
            (L.rival ? (ES ? "; " + name(L.rival.k) + " a " : "; " + name(L.rival.k) + " a ") + pts(tr) : "");
        }
      } else if (w) {
        var best = null;
        for (var k in w) if (w[k] && (best === null || w[k] > w[best] ||
            (w[k] === w[best] && shares[p.c][k] > shares[p.c][best]))) best = k;
        if (best) {
          fill = color(best);
          // Com el mapa d'Espanya: el marge de vot sobre el segon gradua el color.
          var sv = Object.keys(shares[p.c]).map(function (k) { return shares[p.c][k]; }).sort(function (a, b) { return b - a; });
          var marg = shares[p.c][best] - (sv[0] === shares[p.c][best] ? (sv[1] || 0) : sv[0]);
          op = Math.max(0.4, Math.min(1, 0.42 + Math.abs(marg) / 25));
        }
        tip += ": " + order(Object.keys(w)).filter(function (k) { return w[k]; })
          .map(function (k) { return name(k) + " " + w[k]; }).join(", ");
      }
      html += '<path data-c="' + p.c + '" tabindex="0" d="' + D.paths[p.c] + '" fill="' + fill + '"' +
              (op < 1 ? ' fill-opacity="' + op.toFixed(2) + '"' : "") +
              (p.c === picked ? ' class="on"' : "") + '><title>' + tip + "</title></path>";
    });
    g.innerHTML = html;
  }

  /* ------------------------------------------------------------ cada provincia
     Clic (o Retorn) a una provincia del mapa o de la taula: la seva fitxa, amb
     el vot i els escons de cada partit i el marge de l'ultim esco. */
  var picked = null, LAST = null, mapMode = "win";
  function fmt2(x) { return (Math.round(x * 100) / 100).toFixed(2).replace(".", ","); }

  function provPanel() {
    var box = $("#sb-prov"); if (!box || !LAST) return;
    var p = P.filter(function (x) { return x.c === picked; })[0];
    if (!p) { box.hidden = true; return; }
    var sh = LAST.shares[p.c], w = LAST.by[p.c] || {}, m = mag(p);
    var codes = Object.keys(sh).filter(function (k) { return (w[k] || 0) > 0 || sh[k] >= 0.5; })
      .sort(function (a, b) { return (w[b] || 0) - (w[a] || 0) || sh[b] - sh[a]; });
    var h = '<button type="button" class="sb-x" aria-label="' + (ES ? "Cerrar" : "Tanca") + '">×</button>' +
      "<h3>" + p.n + "</h3><p>" + m + " " + (m === 1 ? (ES ? "escaño" : "escó") : (ES ? "escaños" : "escons")) + "</p>" +
      '<table class="results"><thead><tr><th>' + T.party + '</th><th class="num">' + T.vote + '</th><th class="num">' +
      T.seats + "</th></tr></thead><tbody>";
    codes.forEach(function (k) {
      h += '<tr><td><span class="sw" style="background:' + color(k) + '"></span>' + name(k) + '</td><td class="num">' +
           fmt(sh[k]) + ' %</td><td class="num">' + (w[k] ? "<b>" + w[k] + "</b>" : "–") + "</td></tr>";
    });
    h += "</tbody></table>";
    var L = lastInfo(p), LS = lsOf(p);
    if (LS) h += '<h4>' + (ES ? "Cómo se reparte" : "Com es reparteix") + '</h4><div class="sb-ls"></div>';
    if (LS && L && L.rival) h += '<details class="minor"><summary>' + (ES ? "Escaño a escaño y otras medidas del margen" : "Escó a escó i altres mesures del marge") + "</summary>";
    if (L && L.seq && L.seq.length) {
      // Escó a escó: tots si en són pocs; si no, els cinc últims.
      var from = L.seq.length > 12 ? L.seq.length - 5 : 0;
      h += "<h4>" + (ES ? "Escaño a escaño" : "Escó a escó") + "</h4>" +
        '<table class="results sb-seq"><thead><tr><th class="num">#</th><th>' + T.party + '</th><th class="num">' +
        (ES ? "Cociente" : "Quocient") + "</th></tr></thead><tbody>";
      if (from) h += '<tr class="sb-gap"><td colspan="3">… ' + (L.bonus ? L.bonus + (ES ? " de prima + " : " de prima + ") : "") +
        from + (ES ? " escaños antes" : " escons abans") + "</td></tr>";
      else if (L.bonus) h += '<tr class="sb-gap"><td colspan="3">' + L.bonus + (ES ? " escaños de prima para " : " escons de prima per a ") +
        name(Object.keys(L.run).reduce(function (a, b) { return L.run[b] > L.run[a] ? b : a; })) + "</td></tr>";
      var row = function (n, x, cls) {
        return "<tr" + (cls ? ' class="' + cls + '"' : "") + '><td class="num">' + n + '</td><td><span class="sw" style="background:' +
          color(x.k) + '"></span>' + name(x.k) + '</td><td class="num">' + fmt2(L.run[x.k]) + " ÷ " + x.d + " = " + fmt2(x.q) + "</td></tr>";
      };
      L.seq.slice(from).forEach(function (x, i) {
        h += row(from + i + 1 + (L.bonus || 0), x, from + i === L.seq.length - 1 ? "sb-lastrow" : "");
      });
      L.next.slice(0, 3).forEach(function (x) { h += row("–", x, "sb-out"); });
      h += "</tbody></table>";
    }
    if (L && L.last && !L.lr) {
      h += '<p class="note"><b>' + (ES ? "Último escaño" : "Últim escó") + "</b>: " + name(L.last.k) + ".";
      if (L.rival) {
        h += " " + (ES ? "El primero que se queda fuera es " : "El primer que es queda fora és ") + "<b>" + name(L.rival.k) + "</b>.</p>" +
          '<ul class="sb-marg"><li>' + (ES ? "Si " + pts(L.transfer) + " pasaran de " + name(L.last.k) + " a " + name(L.rival.k) +
          ", el escaño cambiaría de manos" : "Si " + pts(L.transfer) + " passessin de " + name(L.last.k) + " a " + name(L.rival.k) +
          ", l'escó canviaria de mans") + votes(L.transfer, p) + ".</li>";
        if (!L.lr) {
          h += "<li>" + (ES ? name(L.rival.k) + " subiendo sola: +" + pts(L.gain) : name(L.rival.k) + " pujant tot sol: +" + pts(L.gain)) +
            votes(L.gain, p) + ".</li><li>" + (ES ? name(L.last.k) + " puede perder " + pts(L.lose) + " antes de perderlo" :
            name(L.last.k) + " pot perdre " + pts(L.lose) + " abans de perdre'l") + votes(L.lose, p) + ".</li>";
        }
        h += "</ul>";
      } else h += "</p>";
      if (L.cut) {
        h += '<p class="note">' + name(L.cut.k) + (ES ? " se lo llevaría si llegara al umbral del " : " se l'enduria si arribés al llindar del ") +
          fmt(L.cut.thr) + " %: " + (ES ? "le faltan " : "li falten ") + pts(L.cut.need) + ".</p>";
      }
      if (L.bonus) h += '<p class="note">' + (ES ? "La prima depende del voto del primer partido y no se cuenta en estos márgenes." :
        "La prima depèn del vot del primer partit i no es compta en aquests marges.") + "</p>";
    }
    if (LS && L && L.rival) h += "</details>";
    if (L && L.lr && L.last) {
      h += '<p class="note"><b>' + (ES ? "Último escaño" : "Últim escó") + "</b> (" + (ES ? "resto mayor" : "resta més gran") + "): " +
        name(L.last.k) + ". " + name(L.rival.k) + (ES ? " se lo quitaría con un traspaso de " : " l'hi prendria amb un traspàs de ") +
        pts(L.transfer) + votes(L.transfer, p) + ".</p>";
      if (L.bonus) h += '<p class="note">' + (ES ? "La prima depende del voto del primer partido y no se cuenta en este margen." :
        "La prima depèn del vot del primer partit i no es compta en aquest marge.") + "</p>";
    }
    box.innerHTML = h;
    if (LS) window.PBLast.ladder(box.querySelector(".sb-ls"), LS, { name: name, color: color });
    box.hidden = false;
    box.querySelector(".sb-x").addEventListener("click", function () { picked = null; box.hidden = true; render(); });
  }

  /* Totes les provincies d'un cop d'ull. */
  function provTable() {
    var t = $("#sb-bydist");
    if (!t) return;
    if (!LAST || P.length < 2) { t.hidden = true; return; }
    var cols = Object.keys(LAST.total).filter(function (k) { return LAST.total[k]; })
      .sort(function (a, b) { return LAST.total[b] - LAST.total[a]; });
    var head = '<tr><th></th><th class="num">' + T.seats + "</th>" + cols.map(function (k) {
      return '<th class="num"><span class="sw" style="background:' + color(k) + '"></span>' + name(k) + "</th>";
    }).join("") + "</tr>";
    var body = P.slice().sort(function (a, b) { return mag(b) - mag(a) || (a.n < b.n ? -1 : 1); }).map(function (p) {
      var w = LAST.by[p.c] || {};
      return "<tr><td><a href=\"#sb-mapwrap\" data-c=\"" + p.c + "\">" + p.n + '</a></td><td class="num">' + mag(p) + "</td>" +
        cols.map(function (k) { return '<td class="num">' + (w[k] || "–") + "</td>"; }).join("") + "</tr>";
    }).join("");
    t.querySelector("thead").innerHTML = head;
    t.querySelector("tbody").innerHTML = body;
  }

  /* Repartiment d'un cop d'ull (21/11/2026): les 52 provincies en un mapa de
     caselles, cada esco un quadret, l'ultim esco marcat i qui l'hi disputa
     (el mateix dibuix que la pagina d'Espanya, site/seatgrid.py). */
  function f2(x) { return (Math.round(x * 100) / 100).toFixed(2).replace(".", ","); }
  function seatGrid() {
    var box = $("#sb-sg");
    if (!box || !D.layout || !LAST) return;
    var tiles = "", close = [];
    P.forEach(function (p) {
      var pos = D.layout[p.c], w = LAST.by[p.c];
      if (!pos) return;
      var style = ' style="grid-column:' + (pos[0] + 1) + ";grid-row:" + (pos[1] + 1) + '"';
      if (!w) {                                         // nit electoral: encara no escrutada
        tiles += '<div class="sg-t"' + style + '><span class="sg-h"><b>' + pos[2] + "</b><small>" + mag(p) + "</small></span></div>";
        return;
      }
      var L = lastInfo(p), seq = [], LS = lsOf(p);
      order(Object.keys(w)).forEach(function (k) { for (var i = 0; i < w[k]; i++) seq.push(k); });
      var li = L && L.last ? seq.lastIndexOf(L.last.k) : -1;
      var hot = LS && LS.first ? LS.first.next.need / LS.unit < 0.5 : (L && L.rival && L.transfer < 0.5);
      var tip = p.n + " · " + mag(p) + " " + T.seats.toLowerCase() + (L && L.rival ? " · " + (ES ? "último escaño: " : "últim escó: ") + name(L.last.k) +
        "; " + name(L.rival.k) + " a " + f2(L.transfer) + (ES ? " puntos" : " punts") + votes(L.transfer, p) : "");
      if (LS && LS.first) tip = p.n + " · " + mag(p) + " " + T.seats.toLowerCase() + " · " + (ES ? "último escaño: " : "últim escó: ") + name(LS.last.k) +
        "; " + (ES ? "primero fuera: " : "primer fora: ") + name(LS.first.k) + ", " + (ES ? "le faltan " : "li falten ") + lsNeed(LS) + lsUnit(LS);
      tiles += '<div class="sg-t' + (hot ? " hot" : "") + (p.c === picked ? " on" : "") + '" data-c="' + p.c + '" tabindex="0" role="button"' + style +
        ' title="' + tip.replace(/"/g, "&quot;") + '"><span class="sg-h"><b>' + pos[2] + "</b><small>" + mag(p) + '</small></span><span class="sg-s">' +
        seq.map(function (k, i) { return '<i style="background:' + color(k) + '"' + (i === li ? ' class="last"' : "") + "></i>"; }).join("") + "</span>" +
        (LS && LS.first ? '<span class="sg-f"><i style="background:' + color(LS.first.k) + '"></i>' + (/\d/.test(lsNeed(LS)) ? "+" : "") + lsNeed(LS) + "</span>" :
         L && L.rival ? '<span class="sg-f"><i style="background:' + color(L.rival.k) + '"></i>' + f2(L.transfer) + "</span>" : "") + "</div>";
      if (LS && LS.first) close.push({ p: p, LS: LS, m: LS.first.next.need / LS.unit });
      else if (L && L.rival) close.push({ p: p, L: L, m: L.transfer });
    });
    close.sort(function (a, b) { return a.m - b.m; });
    box.innerHTML = '<div class="sg-close"><b>' + (ES ? "Los más ajustados" : "Els més ajustats") + ":</b> " + close.slice(0, 6).map(function (x) {
      if (x.LS) {
        var nd = lsNeed(x.LS), num = /\d/.test(nd);
        return '<button type="button" class="sg-chip" data-c="' + x.p.c + '"><b>' + x.p.n + '</b> <i style="background:' + color(x.LS.last.k) + '"></i>' +
          name(x.LS.last.k) + ' <span class="vs">' + (ES ? "por delante de" : "davant de") + '</span> <i style="background:' + color(x.LS.first.k) + '"></i>' + name(x.LS.first.k) +
          " <em>" + (num ? "a " + nd + lsUnit(x.LS) : nd) + "</em></button>";
      }
      return '<button type="button" class="sg-chip" data-c="' + x.p.c + '"><b>' + x.p.n + '</b> <i style="background:' + color(x.L.last.k) + '"></i>' +
        name(x.L.last.k) + ' <span class="vs">vs</span> <i style="background:' + color(x.L.rival.k) + '"></i>' + name(x.L.rival.k) + " <em>" + f2(x.L.transfer) + "</em></button>";
    }).join("") + '</div><div class="sg-wrap"><div class="sg" style="--cols:11;--rows:9">' + tiles +
      '<div class="sg-legend" style="grid-column:8 / span 4;grid-row:7 / span 3"><p><i class="sg-demo last"></i> ' +
      (ES ? "último escaño repartido" : "últim escó repartit") + '</p><p><i class="sg-demo" style="background:var(--dim)"></i> ' +
      (window.PBLast && !(D.method && (D.method.bonus || D.method.name === "hare" || D.method.name === "droop"))
        ? (D.votes ? (ES ? "votos que le faltan al primero que se queda fuera (su color) para quitarlo" : "vots que li falten al primer que es queda fora (el seu color) per prendre'l")
                   : (ES ? "puntos que le faltan al primero que se queda fuera (su color) para quitarlo" : "punts que li falten al primer que es queda fora (el seu color) per prendre'l"))
        : (ES ? "puntos que tendrían que pasar al primero que se queda fuera (su color) para que cambiara de manos" :
        "punts que haurien de passar al primer que es queda fora (el seu color) perquè canviés de mans")) + '</p><p><span class="sg-hotdemo"></span> ' +
      (ES ? "menos de medio punto. Toca una provincia para ver su reparto." : "menys de mig punt. Toca una província per veure'n el repartiment.") + "</p></div></div></div>";
  }

  /* Diputat a diputat: l'ultim que te cada partit i el primer que es queda fora. */
  function lpChart() {
    var el = $("#sb-lp");
    if (!el || !window.PBLast || !LAST) return;
    var list = [];
    P.forEach(function (p) {
      var R = lsOf(p), pos = D.layout && D.layout[p.c];
      if (R) list.push({ c: p.c, n: p.n, a: pos ? pos[2] : p.n, R: R });
    });
    if (!list.length) { el.innerHTML = ""; return; }
    window.PBLast.parties(el, list, { name: name, color: color, nat: LAST.nat || weighted(P, function (x) { return LAST.shares[x.c]; }),
      go: function (c) { picked = c; render(); var mw = $("#sb-mapwrap"); if (mw) mw.scrollIntoView({ behavior: "smooth", block: "start" }); } });
  }

  /* Els ultims escons mes ajustats de tot el territori. */
  function closeTable() {
    var t = $("#sb-close");
    if (!t) return;
    if (!LAST) { t.hidden = true; return; }
    var rows = [];
    P.forEach(function (p) {
      var L = lastInfo(p);
      if (L && L.last && L.rival) rows.push({ p: p, L: L });
    });
    rows.sort(function (a, b) { return a.L.transfer - b.L.transfer; });
    if (!rows.length) { t.hidden = true; return; }
    t.hidden = false;
    var one = P.length < 2;
    t.querySelector("tbody").innerHTML = rows.slice(0, 12).map(function (r) {
      var L = r.L, sw = function (k) { return '<span class="sw" style="background:' + color(k) + '"></span>' + name(k); };
      return "<tr>" + (one ? "" : '<td><a href="#sb-mapwrap" data-c="' + r.p.c + '">' + r.p.n + '</a></td>') +
        "<td>" + sw(L.last.k) + "</td><td>" + sw(L.rival.k) + '</td><td class="num">' + fmtM(L.transfer) +
        "</td>" + (D.votes ? '<td class="num">' + (r.p.v ? votes(L.transfer, r.p).replace(/[()≈ ]|vots|votos/g, "") : "–") + "</td>" : "") + "</tr>";
    }).join("");
    if (one) {
      var th = t.querySelector("thead th");
      if (th && th.dataset.dist) th.remove();
    }
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
      var keep = { nat: state.nat, reg: state.reg, t: state.t };
      state.nat = {}; state.reg = {}; state.t = null;
      BASESEATS[state.base] = allocate(scenario()).total;
      state.nat = keep.nat; state.reg = keep.reg; state.t = keep.t;
    }
    return BASESEATS[state.base];
  }

  /* ------------------------------------------------------------ altres sistemes
     El mateix vot amb una altra llei (21/11/2026): la idea central dels
     simuladors electorals, que la llei decideix tant com el vot. Per a
     l'escenari d'ara mateix es calcula:
       - la llei actual;
       - una sola circumscripcio per a tot el territori, amb d'Hondt i el llindar
         de la llei aplicat a tot el territori;
       - Sainte-Lague a cada circumscripcio (amb el mateix llindar);
       - proporcional pur: tot el territori, resta mes gran (Hare), sense llindar.
     I l'index de Gallagher de cadascun: arrel de la meitat de la suma dels
     quadrats de (% de vot - % d'escons). 0 = perfectament proporcional. */
  function divisors(run, seats, sl) {
    var won = {}, keys = Object.keys(run);
    keys.forEach(function (k) { won[k] = 0; });
    if (!keys.length) return won;
    for (var i = 0; i < seats; i++) {
      var best = null, q = -1;
      keys.forEach(function (k) {
        var v = run[k] / (sl ? 2 * won[k] + 1 : won[k] + 1);
        if (v > q || (v === q && run[k] > run[best])) { q = v; best = k; }
      });
      won[best]++;
    }
    return won;
  }
  function hare(run, seats) {
    var keys = Object.keys(run), total = 0, got = {}, used = 0;
    keys.forEach(function (k) { total += run[k]; });
    if (!total) return got;
    var q = total / seats;
    keys.forEach(function (k) { got[k] = Math.floor(run[k] / q); used += got[k]; });
    keys.slice().sort(function (a, b) { return (run[b] / q - got[b]) - (run[a] / q - got[a]); })
      .slice(0, Math.max(0, seats - used)).forEach(function (k) { got[k]++; });
    return got;
  }
  function gallagher(seats, nat) {
    var n = 0, tv = 0, sum = 0, k;
    for (k in seats) n += seats[k];
    for (k in nat) tv += nat[k];
    if (!n || !tv) return null;
    var keys = {};
    for (k in nat) keys[k] = 1;
    for (k in seats) keys[k] = 1;
    for (k in keys) {
      var d = 100 * (nat[k] || 0) / tv - 100 * (seats[k] || 0) / n;
      sum += d * d;
    }
    return Math.sqrt(sum / 2);
  }
  function alternatives(shares, current) {
    var nat = weighted(P, function (p) { return shares[p.c]; });
    var total = D.seats, out = [];
    var natThr = D.method ? D.method.thr : (THR.scope === "region" ? THR.rt : THR.d);
    var add = function (key, seats) {
      var clean = {};
      for (var k in seats) if (seats[k]) clean[k] = seats[k];
      out.push({ key: key, seats: clean, g: gallagher(clean, nat) });
    };
    add("law", current);
    if (P.length > 1) {
      var run = {};
      for (var k in nat) if (nat[k] >= natThr) run[k] = nat[k];
      add("single", divisors(run, total, false));
      var sl = {};
      P.forEach(function (p) {
        var r = {};
        for (var j in shares[p.c]) if (passes(j, shares[p.c][j], nat)) r[j] = shares[p.c][j];
        var w = divisors(r, mag(p), true);
        for (var x in w) sl[x] = (sl[x] || 0) + w[x];
      });
      add("sl", sl);
    } else {
      var run1 = {};
      for (var k1 in nat) if (nat[k1] >= natThr) run1[k1] = nat[k1];
      if (!D.method || D.method.name !== "dhondt") add("dh1", divisors(run1, total, false));
      if (!D.method || D.method.name !== "sainte_lague") add("sl1", divisors(run1, total, true));
    }
    var all = {};
    for (var k2 in nat) if (nat[k2] > 0) all[k2] = nat[k2];
    add("pure", hare(all, total));
    return out;
  }
  var ALT_LABEL = ES ? {
    law: "Ley actual", single: "Una sola circunscripción (d'Hondt, umbral en todo el territorio)", sl: "Sainte-Laguë en cada circunscripción",
    dh1: "D'Hondt con el mismo umbral", sl1: "Sainte-Laguë con el mismo umbral", pure: "Proporcional puro, sin umbral"
  } : {
    law: "Llei actual", single: "Una sola circumscripció (d'Hondt, llindar a tot el territori)", sl: "Sainte-Laguë a cada circumscripció",
    dh1: "D'Hondt amb el mateix llindar", sl1: "Sainte-Laguë amb el mateix llindar", pure: "Proporcional pur, sense llindar"
  };
  function altTable(shares, current) {
    var t = $("#sb-alt"); if (!t) return;
    var rows = alternatives(shares, current);
    var cols = Object.keys(current).filter(function (k) { return current[k]; })
      .sort(function (a, b) { return current[b] - current[a]; });
    rows.forEach(function (r) {
      for (var k in r.seats) if (cols.indexOf(k) < 0 && r.seats[k]) cols.push(k);
    });
    cols = cols.slice(0, 9);
    t.querySelector("thead").innerHTML = "<tr><th></th>" + cols.map(function (k) {
      return '<th class="num"><span class="sw" style="background:' + color(k) + '"></span>' + name(k) + "</th>";
    }).join("") + '<th class="num">Gallagher</th></tr>';
    t.querySelector("tbody").innerHTML = rows.map(function (r) {
      return "<tr" + (r.key === "law" ? ' class="total"' : "") + "><td>" + ALT_LABEL[r.key] + "</td>" + cols.map(function (k) {
        var v = r.seats[k] || 0, d = v - (current[k] || 0);
        return '<td class="num">' + (v || "–") + (r.key !== "law" && d ? ' <small>(' + (d > 0 ? "+" : "−") + Math.abs(d) + ")</small>" : "") + "</td>";
      }).join("") + '<td class="num">' + (r.g === null ? "–" : fmt(r.g)) + "</td></tr>";
    }).join("");
  }

  /* ------------------------------------------------------------ escenaris de participacio */
  function turnoutLevels() {
    var T = D.turnout, ref = Math.round(T.ref), out = [];
    [50, 55, 60, 65, ref, 75, 80].forEach(function (t) {
      if (t <= T.max && out.indexOf(t) < 0 && T.factors[String(t)]) out.push(t);
    });
    return out.sort(function (a, b) { return a - b; });
  }
  function turnoutTable() {
    var box = $("#sb-turnoutbox");
    if (!box) return;
    if (!D.turnout || state.base !== "now") { box.hidden = true; return; }
    box.hidden = false;
    var keep = state.t, ref = Math.round(D.turnout.ref), rows = [];
    turnoutLevels().forEach(function (t) {
      state.t = t === ref ? null : t;
      var sh = scenario();
      rows.push({ t: t, seats: allocate(sh).total, nat: weighted(P, function (p) { return sh[p.c]; }) });
    });
    state.t = keep;
    var cur = keep === null ? ref : keep;
    var cols = MAIN.filter(function (k) { return rows.some(function (r) { return r.seats[k]; }); }).slice(0, 8);
    var t = $("#sb-turnout");
    var sum = function (r, list) { return list.reduce(function (a, k) { return a + (r.seats[k] || 0); }, 0); };
    t.querySelector("thead").innerHTML = "<tr><th>" + (ES ? "Participación" : "Participació") + "</th>" + cols.map(function (k) {
      return '<th class="num"><span class="sw" style="background:' + color(k) + '"></span>' + name(k) + "</th>";
    }).join("") + (D.blocs ? '<th class="num">' + T.right + '</th><th class="num">' + (ES ? "Bloque de la investidura" : "Bloc de la investidura") + "</th>" : "") + "</tr>";
    t.querySelector("tbody").innerHTML = rows.map(function (r) {
      var R = D.blocs ? sum(r, D.blocs.right) : 0, L = D.blocs ? sum(r, D.blocs.left) : 0;
      return '<tr data-t="' + r.t + '" tabindex="0"' + (r.t === cur ? ' class="total"' : "") + "><td>" + r.t + " %" +
        (r.t === ref ? (ES ? " (como en 2023)" : " (com el 2023)") : "") + "</td>" + cols.map(function (k) {
          return '<td class="num">' + (r.seats[k] || "–") + ' <small>' + fmt(r.nat[k] || 0) + " %</small></td>";
        }).join("") + (D.blocs ? '<td class="num">' + (R >= D.majority ? "<b>" + R + "</b>" : R) + '</td><td class="num">' +
        (L >= D.majority ? "<b>" + L + "</b>" : L) + "</td>" : "") + "</tr>";
    }).join("");
    turnoutCheck(rows);
  }
  /* Comprovacio en vots (23/11/2026): a cada participacio, quants vots i quina
     part del cens tindria cada bloc, contra el que ha votat de 1996 a 2023.
     El vot valid de cada escenari es el del 2023 per T / ref (com a la resta
     del simulador); el cens, el del 2023 amb el CERA, com a la serie historica.
     No canvia cap xifra: nomes avisa quan un escenari no te precedents. */
  function turnoutCheck(rows) {
    var box = $("#sb-tcheck"), C = D.turnout && D.turnout.check;
    if (!box) return;
    if (!C || !D.votes) { box.hidden = true; return; }
    box.hidden = false;
    var V23 = C.valid || P.reduce(function (a, p) { return a + (p.v || 0); }, 0), ref = D.turnout.ref;
    var M = function (x) { return (Math.round(x / 1e5) / 10).toFixed(1).replace(".", ",") + (ES ? " M" : " M"); };
    var names = { right: "PP + Vox", left: "PSOE + Frente Amplio + Podemos" };
    var yr = function (y) { return y.slice(0, 4) === "2019" ? (y.slice(5) === "04" ? (ES ? "abr. " : "abr. ") : (ES ? "nov. " : "nov. ")) + "2019" : y.slice(0, 4); };
    var TV = C.turnout;
    var head = "<tr><th>" + (ES ? "Participación" : "Participació") + "</th>" + (TV ? '<th class="num">' + (ES ? "Voto válido" : "Vot vàlid") +
      "<br><small>% " + (ES ? "del censo" : "del cens") + " (" + fmt(TV.min) + "-" + fmt(TV.max) + " %)</small></th>" : "");
    ["right", "left"].forEach(function (k) {
      var B = C.blocs[k];
      head += '<th class="num">' + names[k] + "<br><small>" + (ES ? "votos · % del censo" : "vots · % del cens") + " (" + C.from + "-" + C.to + ": " +
        fmt(B.min) + "-" + fmt(B.max) + " %)</small></th>";
    });
    head += "</tr>";
    var flags = [], tflag = {};
    var body = rows.map(function (r) {
      var Vt = V23 * r.t / ref, tr = "<tr" + (r.t === (state.t === null ? Math.round(ref) : state.t) ? ' class="total"' : "") + "><td>" + r.t + " %</td>";
      if (TV) {
        var tp = 100 * Vt / C.census, out = tp < TV.min - 0.05 || tp > TV.max + 0.05;
        if (out) tflag[r.t] = tp < TV.min ? (ES ? "por debajo de la más baja (" : "per sota de la més baixa (") + fmt(TV.min) + " %, " + yr(TV.min_y) + ")" :
          (ES ? "por encima de la más alta (" : "per sobre de la més alta (") + fmt(TV.max) + " %, " + yr(TV.max_y) + ")";
        tr += '<td class="num' + (out ? " sb-out" : "") + '"><b>' + fmt(tp) + " %</b>" + (out ? " ⚠" : "") + "</td>";
      }
      ["right", "left"].forEach(function (k) {
        var B = C.blocs[k], sh = B.now.reduce(function (a, q) { return a + (r.nat[q] || 0); }, 0);
        var votes = sh / 100 * Vt, pc = 100 * votes / C.census, cls = "", tip = "";
        if (pc > B.max + 0.05) { cls = "up"; tip = (ES ? "por encima del máximo (" : "per sobre del màxim (") + fmt(B.max) + " %, " + yr(B.max_y) + ")"; }
        else if (pc < B.min - 0.05) { cls = "down"; tip = (ES ? "por debajo del mínimo (" : "per sota del mínim (") + fmt(B.min) + " %, " + yr(B.min_y) + ")"; }
        if (tip) flags.push({ t: r.t, k: k, tip: tip, pc: pc });
        tr += '<td class="num' + (cls ? " sb-out" : "") + '"' + (tip ? ' title="' + tip + '"' : "") + ">" + M(votes) + " · <b" +
          (cls ? ' class="' + cls + '"' : "") + ">" + fmt(pc) + " %</b>" + (tip ? " ⚠" : "") + "</td>";
      });
      return tr + "</tr>";
    }).join("");
    box.querySelector("thead").innerHTML = head;
    box.querySelector("tbody").innerHTML = body;
    var cur = state.t === null ? Math.round(ref) : state.t, now = flags.filter(function (f) { return f.t === cur; });
    var pre = tflag[cur] ? (ES ? "Esta participación no tiene precedentes desde " : "Aquesta participació no té precedents des del ") + C.from + ": " + tflag[cur] +
      (ES ? ". Por eso los bloques también salen del rango; lo que cuenta es la participación. " : ". Per això els blocs també surten del rang; el que compta és la participació. ") : "";
    var txt = pre + (now.length ? now.map(function (f) {
      return "<b>" + names[f.k] + "</b>: " + fmt(f.pc) + " % " + (ES ? "del censo, " : "del cens, ") + f.tip;
    }).join(". ") + "." : (ES ? "Con esta participación, los dos bloques quedan dentro de lo que han votado entre " :
      "Amb aquesta participació, els dos blocs queden dins del que han votat entre ") + C.from + (ES ? " y " : " i ") + C.to + ".");
    $("#sb-tcheck-read").innerHTML = txt;
  }
  function setTurnout(t) {
    var ref = Math.round(D.turnout.ref);
    state.t = (t === ref || isNaN(t)) ? null : Math.max(50, Math.min(D.turnout.max, t));
    var inp = $("#sb-t");
    if (inp) { inp.value = state.t === null ? ref : state.t; }
    render();
  }
  function turnoutLabel() {
    var o = $("#sb-tout"); if (!o || !D.turnout) return;
    var ref = Math.round(D.turnout.ref), v = state.t === null ? ref : state.t;
    o.textContent = v + " %" + (v === ref ? (ES ? " (como en 2023)" : " (com el 2023)") : "");
    var w = $("#sb-twrap"); if (w) w.hidden = state.base !== "now";
  }

  /* ------------------------------------------------------------ coalicions
     Construeix una majoria (22/11/2026): toca els partits per sumar-los. I la
     llista de majories minimes: coalicions que arriben a la majoria i en les
     quals cap partit sobra (si en treus qualsevol, ja no hi arriben). Amb
     fins a 16 partits amb escons es miren totes les combinacions; amb mes,
     fins a sis partits. "Contigua" vol dir que els partits son veins a l'eix
     esquerra-dreta (l'ordre del web, el mateix de l'hemicicle), sense saltar-se'n
     cap amb escons: la coalicio "connectada" d'Axelrod. */
  function coalitions(total) {
    var maj = D.majority, ks = order(Object.keys(total).filter(function (k) { return total[k] > 0; }));
    var out = [], n = ks.length, MAXK = n <= 16 ? n : 6;
    function rec(start, pick, sum) {
      if (sum >= maj) {
        var minimal = pick.every(function (k) { return sum - total[k] < maj; });
        if (minimal) out.push({ ks: pick.slice(), seats: sum });
        return;
      }
      if (pick.length >= MAXK) return;
      for (var i = start; i < n; i++) { pick.push(ks[i]); rec(i + 1, pick, sum + total[ks[i]]); pick.pop(); }
    }
    rec(0, [], 0);
    out.forEach(function (c) {
      var idx = c.ks.map(function (k) { return ks.indexOf(k); }).sort(function (a, b) { return a - b; });
      c.contig = idx[idx.length - 1] - idx[0] === idx.length - 1;
    });
    out.sort(function (a, b) { return a.ks.length - b.ks.length || a.seats - b.seats; });
    return out;
  }
  function coalBox(total) {
    var box = $("#sb-coal"); if (!box) return;
    var ks = order(Object.keys(total).filter(function (k) { return total[k] > 0; }));
    state.coal = state.coal.filter(function (k) { return total[k] > 0; });
    var sum = state.coal.reduce(function (a, k) { return a + total[k]; }, 0), maj = D.majority;
    $("#sb-chips").innerHTML = ks.map(function (k) {
      var on = state.coal.indexOf(k) >= 0;
      return '<button type="button" class="sb-chip' + (on ? " on" : "") + '" aria-pressed="' + on + '" data-k="' + k +
        '"><span class="sw" style="background:' + color(k) + '"></span>' + name(k) + " <b>" + total[k] + "</b></button>";
    }).join("");
    var pct = Math.min(100, 100 * sum / D.seats), mp = 100 * maj / D.seats;
    $("#sb-coalbar").innerHTML = '<div class="sb-cfill" style="width:' + pct.toFixed(1) + '%"></div><div class="sb-cmaj" style="left:' +
      mp.toFixed(1) + '%"></div>';
    $("#sb-coalsum").innerHTML = state.coal.length ? "<b>" + sum + "</b> " + (ES ? "escaños" : "escons") + " · " +
      (sum >= maj ? (ES ? "mayoría absoluta ✔" : "majoria absoluta ✔") :
       (ES ? "faltan " : "en falten ") + (maj - sum) + (ES ? " para la mayoría (" : " per a la majoria (") + maj + ")") :
      (ES ? "Toca los partidos para sumarlos." : "Toca els partits per sumar-los.");
    var list = coalitions(total).slice(0, 16);
    $("#sb-coallist").innerHTML = list.length ? list.map(function (c) {
      return '<li><button type="button" class="sb-clink" data-ks="' + c.ks.join(",") + '">' + c.ks.map(function (k) {
        return '<span class="sw" style="background:' + color(k) + '"></span>' + name(k);
      }).join(" + ") + "</button> <b>" + c.seats + "</b>" + (c.contig ? ' <small>' + (ES ? "contigua" : "contigua") + "</small>" : "") + "</li>";
    }).join("") : "<li>" + (ES ? "Ninguna combinación llega a la mayoría." : "Cap combinació no arriba a la majoria.") + "</li>";
  }

  function render() {
    var shares = scenario();
    var res = allocate(shares);
    LAST = { shares: shares, by: res.by, total: res.total };
    var nat = weighted(P, function (p) { return shares[p.c]; });
    hemicycle(res.total, D.seats);
    mapDraw(res.by, shares);
    table(res.total, baseSeats(), nat);
    sliders(shares);
    provPanel();
    provTable();
    closeTable();
    seatGrid();
    lpChart();
    altTable(shares, res.total);
    turnoutLabel();
    turnoutTable();
    coalBox(res.total);
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
      LAST = { shares: shares, by: res.by, total: res.total };
      provTable();
      closeTable();
      seatGrid();
      if (picked) provPanel();
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
    if (state.t !== null) o.t = state.t;
    if (state.tm === "classic") o.m = "c";
    if (state.coal.length) o.k = state.coal;
    if (Object.keys(state.reg).length) {
      o.r = {};
      for (var r in state.reg) o.r[r] = round(state.reg[r]);
    }
    var s = (o.n || o.r || o.t || o.m || o.k || o.b !== "now") ? "#" + encodeURIComponent(JSON.stringify(o)) : " ";
    history.replaceState(null, "", s === " " ? location.pathname + location.search : s);
  }
  function round(o) { var x = {}; for (var k in o) x[k] = Math.round(o[k] * 10) / 10; return x; }
  function readHash() {
    try {
      var o = JSON.parse(decodeURIComponent(location.hash.slice(1)));
      if (D.main[o.b]) setBase(o.b);
      if (o.n) state.nat = o.n;
      if (o.r) state.reg = o.r;
      if (Array.isArray(o.k)) state.coal = o.k.filter(function (k) { return typeof k === "string"; });
      if (D.turnout && o.t && D.turnout.factors[String(o.t)]) state.t = o.t;
      if (D.turnout && o.m === "c" && D.turnout.classic) state.tm = "classic";
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
    $("#sb-reset").addEventListener("click", function () {
      state.nat = {}; state.reg = {}; state.t = null; stopNight();
      if ($("#sb-t") && D.turnout) $("#sb-t").value = Math.round(D.turnout.ref);
      render();
    });
    if (D.turnout && $("#sb-t")) {
      var ti = $("#sb-t");
      ti.min = 50; ti.max = D.turnout.max; ti.step = 1;
      ti.value = state.t === null ? Math.round(D.turnout.ref) : state.t;
      ti.addEventListener("input", function () { stopNight(); setTurnout(parseInt(ti.value, 10)); });
      document.querySelectorAll("input[name=sb-tm]").forEach(function (r) {
        if (r.value === "classic" && !D.turnout.classic) { r.parentNode.remove(); return; }
        r.checked = r.value === state.tm;
        r.addEventListener("change", function () { if (r.checked) { state.tm = r.value; stopNight(); render(); } });
      });
      ["click", "keydown"].forEach(function (ev) {
        $("#sb-turnout").addEventListener(ev, function (e) {
          var tr = e.target.closest && e.target.closest("tr[data-t]");
          if (!tr || (e.type === "keydown" && e.key !== "Enter" && e.key !== " ")) return;
          e.preventDefault(); stopNight(); setTurnout(parseInt(tr.dataset.t, 10));
        });
      });
    } else if ($("#sb-twrap")) $("#sb-twrap").remove();
    $("#sb-night").addEventListener("click", runNight);
    if ($("#sb-sg")) {
      ["click", "keydown"].forEach(function (ev) {
        $("#sb-sg").addEventListener(ev, function (e) {
          var t = e.target.closest && e.target.closest("[data-c]");
          if (!t || (e.type === "keydown" && e.key !== "Enter" && e.key !== " ")) return;
          e.preventDefault();
          picked = t.getAttribute("data-c");
          if (!night) render(); else { provPanel(); seatGrid(); }
          $("#sb-mapwrap").scrollIntoView({ behavior: "smooth", block: "center" });
        });
      });
    }
    if ($("#sb-coal")) {
      $("#sb-coal").addEventListener("click", function (e) {
        var chip = e.target.closest && e.target.closest(".sb-chip");
        var link = e.target.closest && e.target.closest(".sb-clink");
        if (chip) {
          var k = chip.dataset.k, i = state.coal.indexOf(k);
          if (i >= 0) state.coal.splice(i, 1); else state.coal.push(k);
        } else if (link) state.coal = link.dataset.ks.split(",");
        else if (e.target.id === "sb-coalclear") state.coal = [];
        else return;
        if (!night) render(); else { coalBox(LAST.total); hemicycle(LAST.total, D.seats); }
      });
    }
    var pick = function (e) {
      var c = e.target && e.target.getAttribute && e.target.getAttribute("data-c");
      if (!c) return;
      if (e.type === "keydown" && e.key !== "Enter" && e.key !== " ") return;
      e.preventDefault();
      picked = c;
      if (!night) render(); else provPanel();
      if (e.currentTarget.id === "sb-bydist" || e.currentTarget.id === "sb-close") $("#sb-mapwrap").scrollIntoView({ behavior: "smooth", block: "center" });
    };
    ["click", "keydown"].forEach(function (ev) {
      if ($("#sb-map")) $("#sb-map").addEventListener(ev, pick);
      if ($("#sb-bydist")) $("#sb-bydist").addEventListener(ev, pick);
      if ($("#sb-close")) $("#sb-close").addEventListener(ev, pick);
    });
    document.querySelectorAll("input[name=sb-mapmode]").forEach(function (r) {
      r.addEventListener("change", function () { if (r.checked) { mapMode = r.value; render(); } });
    });
    if (P.length < 2) $("#sb-night").style.display = "none";   // una sola circumscripcio: no hi ha recompte per tandes
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
