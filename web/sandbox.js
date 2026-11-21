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
    var v = Math.max(1, Math.round(x * p.v / 100));
    return " (≈ " + String(v).replace(/\B(?=(\d{3})+(?!\d))/g, ".") + (ES ? " votos)" : " vots)");
  }
  function lastInfo(p) {
    if (!LAST || !LAST.by[p.c]) return null;
    var nat = weighted(P, function (x) { return LAST.shares[x.c]; });
    return lastSeat(LAST.shares[p.c], mag(p), nat);
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
        if (best) fill = color(best);
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
    var L = lastInfo(p);
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
    if (L && L.lr && L.last) {
      h += '<p class="note"><b>' + (ES ? "Último escaño" : "Últim escó") + "</b> (" + (ES ? "resto mayor" : "resta més gran") + "): " +
        name(L.last.k) + ". " + name(L.rival.k) + (ES ? " se lo quitaría con un traspaso de " : " l'hi prendria amb un traspàs de ") +
        pts(L.transfer) + votes(L.transfer, p) + ".</p>";
      if (L.bonus) h += '<p class="note">' + (ES ? "La prima depende del voto del primer partido y no se cuenta en este margen." :
        "La prima depèn del vot del primer partit i no es compta en aquest marge.") + "</p>";
    }
    box.innerHTML = h;
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
      var keep = { nat: state.nat, reg: state.reg };
      state.nat = {}; state.reg = {};
      BASESEATS[state.base] = allocate(scenario()).total;
      state.nat = keep.nat; state.reg = keep.reg;
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
    altTable(shares, res.total);
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
