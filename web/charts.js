/* Polit Bureau — grafic interactiu d'evolucio de les enquestes (22/11/2026).
 *
 * Idees preses de les webs de mitjanes d'enquestes (Politico Poll of Polls,
 * els models de The Economist i Silver Bulletin), no el seu codi:
 *   - botons de periode (6 mesos, 1 any, tot);
 *   - linia vertical i lectura de tots els partits en passar per una data;
 *   - franja amb la dispersio entre instituts;
 *   - marques de les eleccions anteriors i del dia de la votacio;
 *   - tocar un partit de la llegenda l'amaga o el mostra.
 * Les dades venen de site/trend.py:interactive dins de la mateixa figura.
 * Sense JavaScript es veu el grafic estatic (els ultims 12 mesos).
 */
(function () {
  "use strict";
  var ES = (document.documentElement.lang || "ca").slice(0, 2) === "es";
  var T = ES ? { m6: "6 meses", y1: "1 año", all: "Todo", days: "días", day: "día", today: "hoy", polls: "encuestas", band: "Franja: dispersión entre institutos" }
             : { m6: "6 mesos", y1: "1 any", all: "Tot", days: "dies", day: "dia", today: "avui", polls: "enquestes", band: "Franja: dispersió entre instituts" };
  var MONTHS = ES ? ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
                  : ["gen", "febr", "març", "abr", "maig", "juny", "jul", "ag", "set", "oct", "nov", "des"];
  var NS = "http://www.w3.org/2000/svg";
  function day(s) { var p = s.split("-"); return Date.UTC(+p[0], +p[1] - 1, +p[2]) / 864e5; }
  function fmtDate(d) { var x = new Date(d * 864e5); return x.getUTCDate() + " " + MONTHS[x.getUTCMonth()] + " " + x.getUTCFullYear(); }
  function f1(v) { return (Math.round(v * 10) / 10).toFixed(1).replace(".", ","); }

  function chart(fig) {
    var src = fig.querySelector("script.trend-data");
    if (!src) return;
    var D = JSON.parse(src.textContent);
    var dates = D.dates.map(day), lastData = dates[dates.length - 1];
    var endDay = D.end ? day(D.end) : null;
    var hidden = {}, range = "y1";
    var W = 760, H = 330, L = 34, R = 132, TOP = 18, B = 30;
    var wrap = document.createElement("div");
    wrap.className = "tr-ia";
    wrap.innerHTML = '<div class="tr-bar"><div class="tr-ranges" role="group">' +
      [["m6", T.m6], ["y1", T.y1], ["all", T.all]].map(function (r) {
        return '<button type="button" data-r="' + r[0] + '" aria-pressed="' + (r[0] === range) + '">' + r[1] + "</button>";
      }).join("") + '</div><div class="tr-legend"></div></div><div class="tr-box"><svg viewBox="0 0 ' + W + " " + H +
      '" role="img"></svg><div class="tr-tip" hidden></div></div><p class="tr-note">' + T.band + "</p>";
    var svg = wrap.querySelector("svg"), tip = wrap.querySelector(".tr-tip");
    var old = fig.querySelector("svg");
    if (old) old.style.display = "none";
    fig.insertBefore(wrap, fig.firstChild);

    function legend() {
      wrap.querySelector(".tr-legend").innerHTML = D.codes.map(function (c) {
        return '<button type="button" data-c="' + c + '" aria-pressed="' + !hidden[c] + '"' + (hidden[c] ? ' class="off"' : "") +
          '><i style="background:' + D.colors[c] + '"></i>' + D.names[c] + "</button>";
      }).join("");
    }

    var X, Y, x0d, x1d, idx0;
    function draw() {
      var span = range === "m6" ? 183 : range === "y1" ? 365 : 1e9;
      x0d = Math.max(dates[0], lastData - span);
      x1d = endDay && endDay > lastData ? endDay + 2 : lastData;
      idx0 = 0;
      while (idx0 < dates.length - 1 && dates[idx0] < x0d) idx0++;
      var vis = D.codes.filter(function (c) { return !hidden[c]; });
      var top = 10;
      vis.forEach(function (c) {
        for (var i = idx0; i < dates.length; i++) {
          var v = D.hi[c][i] !== null ? D.hi[c][i] : D.s[c][i];
          if (v !== null && v > top) top = v;
        }
      });
      var step = top <= 30 ? 5 : 10, ymax = (Math.floor(top / step) + 1) * step;
      X = function (d) { return L + (W - L - R) * (d - x0d) / Math.max(1, x1d - x0d); };
      Y = function (v) { return H - B - (H - B - TOP) * v / ymax; };
      var h = "";
      for (var v = 0; v <= ymax; v += step) {
        h += '<line class="gr" x1="' + L + '" x2="' + (W - R) + '" y1="' + Y(v) + '" y2="' + Y(v) + '"/><text class="yl" x="' + (L - 6) + '" y="' + (Y(v) + 4) + '">' + v + "</text>";
      }
      // mesos
      var d0 = new Date(x0d * 864e5), m = Date.UTC(d0.getUTCFullYear(), d0.getUTCMonth() + 1, 1) / 864e5;
      // trimestres alineats amb gener perque sempre surti l'any
      var every = (x1d - x0d) > 1400 ? 6 : (x1d - x0d) > 500 ? 3 : 1;
      while (m <= x1d) {
        var dm = new Date(m * 864e5);
        if (dm.getUTCMonth() % every === 0) {
          h += '<line class="tk" x1="' + X(m) + '" x2="' + X(m) + '" y1="' + (H - B) + '" y2="' + (H - B + 4) + '"/><text class="xl" x="' + X(m) + '" y="' + (H - B + 17) + '">' +
            MONTHS[dm.getUTCMonth()] + (dm.getUTCMonth() === 0 ? " " + dm.getUTCFullYear() : "") + "</text>";
        }
        m = Date.UTC(dm.getUTCFullYear(), dm.getUTCMonth() + 1, 1) / 864e5;
      }
      // marques
      (D.marks || []).forEach(function (mk) {
        var dd = day(mk.d);
        if (dd < x0d || dd > x1d) return;
        h += '<line class="mk" x1="' + X(dd) + '" x2="' + X(dd) + '" y1="' + TOP + '" y2="' + (H - B) + '"/><text class="mkl" x="' + (X(dd) + 4) + '" y="' + (TOP + 10) + '">' + mk.l + "</text>";
      });
      if (endDay && endDay > lastData) {
        var left = Math.round(endDay - Date.now() / 864e5);
        h += '<rect class="fut" x="' + X(lastData) + '" y="' + TOP + '" width="' + (X(x1d) - X(lastData)) + '" height="' + (H - B - TOP) + '"/>' +
          '<line class="mk end" x1="' + X(endDay) + '" x2="' + X(endDay) + '" y1="' + TOP + '" y2="' + (H - B) + '"/>';
        if (left >= 0) h += '<text class="mkl end" x="' + (X(endDay) - 4) + '" y="' + (TOP + 10) + '">' + fmtDate(endDay).replace(/ \d{4}$/, "") +
          (left > 0 ? " · " + left + " " + (left === 1 ? T.day : T.days) : "") + "</text>";
      }
      // franges, punts i linies
      vis.forEach(function (c) {
        var up = [], dn = [];
        for (var i = idx0; i < dates.length; i++) {
          if (D.lo[c][i] === null || D.hi[c][i] === null) continue;
          up.push(X(dates[i]).toFixed(1) + " " + Y(D.hi[c][i]).toFixed(1));
          dn.unshift(X(dates[i]).toFixed(1) + " " + Y(D.lo[c][i]).toFixed(1));
        }
        if (up.length > 1) h += '<path class="band" fill="' + D.colors[c] + '" d="M' + up.join(" L") + " L" + dn.join(" L") + 'Z"/>';
      });
      vis.forEach(function (c) {
        var dd = "";
        D.polls.forEach(function (p) {
          var pd = day(p[0]);
          if (pd >= x0d && p[2][c] !== undefined) dd += "M" + X(pd).toFixed(1) + " " + Y(p[2][c]).toFixed(1) + "h0";
        });
        if (dd) h += '<path class="dots" stroke="' + D.colors[c] + '" d="' + dd + '"/>';
      });
      var ends = [];
      vis.forEach(function (c) {
        var pts = [];
        for (var i = idx0; i < dates.length; i++) if (D.s[c][i] !== null) pts.push([X(dates[i]), Y(D.s[c][i]), D.s[c][i]]);
        if (pts.length < 2) return;
        h += '<path class="ln" stroke="' + D.colors[c] + '" d="M' + pts.map(function (p) { return p[0].toFixed(1) + " " + p[1].toFixed(1); }).join(" L") + '"/>';
        var e = pts[pts.length - 1];
        ends.push({ c: c, x: e[0], y: e[1], v: e[2] });
      });
      ends.sort(function (a, b) { return a.y - b.y; });
      var prev = null;
      ends.forEach(function (e) { e.ly = prev === null ? e.y : Math.max(e.y, prev + 13); prev = e.ly; });
      var over = ends.length ? ends[ends.length - 1].ly - (H - B - 2) : 0;
      if (over > 0) ends.forEach(function (e) { e.ly -= over; });
      var lx = X(x1d) + 8;
      ends.forEach(function (e) {
        h += '<circle class="endpt" cx="' + e.x.toFixed(1) + '" cy="' + e.y.toFixed(1) + '" r="3.4" fill="' + D.colors[e.c] + '"/>' +
          '<text class="el" x="' + lx + '" y="' + (e.ly + 4).toFixed(1) + '"><tspan fill="' + D.colors[e.c] + '">●</tspan> ' + D.names[e.c] +
          ' <tspan class="ev">' + f1(e.v) + "</tspan></text>";
      });
      h += '<line class="cross" x1="0" x2="0" y1="' + TOP + '" y2="' + (H - B) + '" visibility="hidden"/><g class="hov"></g>' +
        '<rect class="hit" x="' + L + '" y="' + TOP + '" width="' + (W - L - R) + '" height="' + (H - B - TOP) + '" fill="transparent"/>';
      svg.innerHTML = h;
      bindHover();
    }

    function bindHover() {
      var hit = svg.querySelector(".hit"), cross = svg.querySelector(".cross"), hov = svg.querySelector(".hov");
      function move(ev) {
        var pt = ev.touches ? ev.touches[0] : ev;
        var r = svg.getBoundingClientRect();
        var sx = (pt.clientX - r.left) * W / r.width;
        var d = x0d + (sx - L) / (W - L - R) * (x1d - x0d);
        var best = idx0, bd = 1e9;
        for (var i = idx0; i < dates.length; i++) { var q = Math.abs(dates[i] - d); if (q < bd) { bd = q; best = i; } }
        var x = X(dates[best]);
        cross.setAttribute("x1", x); cross.setAttribute("x2", x); cross.setAttribute("visibility", "visible");
        var vis = D.codes.filter(function (c) { return !hidden[c] && D.s[c][best] !== null; })
          .sort(function (a, b) { return D.s[b][best] - D.s[a][best]; });
        hov.innerHTML = vis.map(function (c) {
          return '<circle cx="' + x + '" cy="' + Y(D.s[c][best]) + '" r="4" fill="' + D.colors[c] + '" class="hp"/>';
        }).join("");
        var n = D.polls.filter(function (p) { var pd = day(p[0]); return pd <= dates[best] && pd > dates[best] - 30; }).length;
        tip.innerHTML = "<b>" + fmtDate(dates[best]) + "</b>" + vis.map(function (c) {
          var band = D.lo[c][best] !== null ? ' <small>' + f1(D.lo[c][best]) + "–" + f1(D.hi[c][best]) + "</small>" : "";
          return '<div><i style="background:' + D.colors[c] + '"></i>' + D.names[c] + " <b>" + f1(D.s[c][best]) + "</b>" + band + "</div>";
        }).join("") + "<small>" + n + " " + T.polls + " (30 " + T.days + ")</small>";
        tip.hidden = false;
        var px = x / W * r.width;
        tip.style.left = (px > r.width / 2 ? px - tip.offsetWidth - 12 : px + 12) + "px";
        tip.style.top = "8px";
      }
      function leave() { cross.setAttribute("visibility", "hidden"); hov.innerHTML = ""; tip.hidden = true; }
      hit.addEventListener("mousemove", move);
      hit.addEventListener("touchstart", move, { passive: true });
      hit.addEventListener("touchmove", move, { passive: true });
      hit.addEventListener("mouseleave", leave);
      hit.addEventListener("touchend", function () { setTimeout(leave, 1800); });
    }

    wrap.querySelector(".tr-ranges").addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b) return;
      range = b.dataset.r;
      wrap.querySelectorAll(".tr-ranges button").forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
      draw();
    });
    wrap.querySelector(".tr-legend").addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b) return;
      var c = b.dataset.c;
      hidden[c] = !hidden[c];
      if (D.codes.every(function (k) { return hidden[k]; })) hidden[c] = false;
      legend(); draw();
    });
    legend();
    draw();
  }

  function init() { document.querySelectorAll("figure.trend").forEach(chart); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
