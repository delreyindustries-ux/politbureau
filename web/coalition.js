/* Simulador de coalicions d'una circumscripcio.
 *
 * Pregunta que respon: si dos o mes partits s'haguessin presentat en una sola
 * llista, quants escons haurien tret? La suma NO es la resposta, perque la llei
 * d'Hondt no es additiva: els vots que a cada partit li sobraven per separat
 * poden sumar prou per a un esco mes.
 *
 * Verificat sobre les 52 circumscripcions i les dues capes (6.316 parelles):
 * en 437 casos la coalicio guanya escons i en cap no en perd. Es la propietat
 * coneguda del metode d'Hondt, i el simulador no la contradiu enlloc.
 *
 * El repartiment ha de donar EXACTAMENT el mateix que `model/seats.py`. Si
 * canvia alla, ha de canviar aqui: dues regles diferents per al mateix numero
 * es la manera mes segura de publicar dues xifres que no quadren.
 */
(function () {
  "use strict";

  var THRESHOLD = 0.03;

  function dhondt(shares, seats) {
    var codes = Object.keys(shares), res = {}, valid = 0, i, p;
    for (i = 0; i < codes.length; i++) { res[codes[i]] = 0; valid += shares[codes[i]]; }
    if (!valid || seats <= 0) return res;

    var running = codes.filter(function (c) { return shares[c] / valid >= THRESHOLD; });
    if (!running.length) return res;

    for (i = 0; i < seats; i++) {
      var best = null, bq = -1, bv = -1;
      for (var j = 0; j < running.length; j++) {
        p = running[j];
        var q = shares[p] / (res[p] + 1);
        // Mateix desempat que a Python: primer el quocient, despres els vots.
        if (q > bq || (q === bq && shares[p] > bv)) { best = p; bq = q; bv = shares[p]; }
      }
      res[best] += 1;
    }
    return res;
  }

  function fmt(n, d) {
    return n.toFixed(d === undefined ? 1 : d).replace(".", ",");
  }

  function thousands(n) {
    return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  }

  function boot() {
    var host = document.getElementById("coalition");
    if (!host) return;

    var data;
    try { data = JSON.parse(document.getElementById("coalition-data").textContent); }
    catch (e) { return; }
    if (!data || !data.parties || data.parties.length < 2) return;

    var T = host.dataset;
    var layer = "now";
    var picked = {};

    var list = host.querySelector(".cparties");
    var out = host.querySelector(".cresult");
    var tabs = host.querySelectorAll(".clayer button");

    function shares() {
      var s = {};
      data.parties.forEach(function (p) { if (p[layer] > 0) s[p.code] = p[layer]; });
      return s;
    }

    function render() {
      var base = shares(), seats = dhondt(base, data.magnitude);
      var chosen = data.parties.filter(function (p) { return picked[p.code] && base[p.code]; });

      // Els botons: escons actuals de cada partit en aquesta capa.
      Array.prototype.forEach.call(list.children, function (li) {
        var code = li.dataset.code;
        li.querySelector(".cs").textContent = seats[code] || 0;
        li.querySelector(".cpc").textContent = fmt(base[code] || 0) + "%";
        li.classList.toggle("on", !!picked[code]);
        li.hidden = !base[code];
      });

      if (chosen.length < 2) {
        out.innerHTML = "<p class=\"note\">" + T.hint + "</p>";
        return;
      }

      var merged = {}, sum = 0, before = 0;
      Object.keys(base).forEach(function (c) { merged[c] = base[c]; });
      chosen.forEach(function (p) {
        sum += base[p.code];
        before += seats[p.code] || 0;
        delete merged[p.code];
      });
      merged.__coalition__ = sum;

      var after = dhondt(merged, data.magnitude);
      var got = after.__coalition__ || 0;
      var delta = got - before;

      var names = chosen.map(function (p) { return p.name; }).join(" + ");
      var votes = data.valid ? Math.round(sum * data.valid / 100) : 0;

      var verdict = delta > 0
        ? "<strong class=\"gain\">+" + delta + " " + (delta === 1 ? T.seat : T.seats) + "</strong>"
        : "<strong class=\"same\">" + T.nochange + "</strong>";

      var html = "<p class=\"csum\">" + names + " &middot; " + fmt(sum, 2) + "%"
        + (votes ? " &middot; " + thousands(votes) + " " + T.votes : "") + "</p>"
        + "<p class=\"cverdict\">" + T.separate + ": <b>" + before + "</b> &rarr; "
        + T.together + ": <b>" + got + "</b> &nbsp; " + verdict + "</p>";

      // Qui perd l'esco que guanya la coalicio. Sense aixo el simulador diu
      // que algu suma pero no d'on surt, i el repartiment sembla magia.
      if (delta > 0) {
        var moved = [];
        Object.keys(base).forEach(function (c) {
          if (picked[c]) return;
          var d = (after[c] || 0) - (seats[c] || 0);
          if (d !== 0) {
            var p = data.parties.filter(function (x) { return x.code === c; })[0];
            moved.push((p ? p.name : c) + " " + (d > 0 ? "+" : "") + d);
          }
        });
        if (moved.length) {
          html += "<p class=\"note\">" + T.from + ": " + moved.join(", ") + "</p>";
        }
      }
      out.innerHTML = html;
    }

    data.parties.forEach(function (p) {
      var li = document.createElement("li");
      li.dataset.code = p.code;
      li.innerHTML = "<span class=\"sw\" style=\"background:" + p.color + "\"></span>"
        + "<span class=\"cn\">" + p.name + "</span>"
        + "<span class=\"cpc\"></span><span class=\"cs\"></span>";
      li.setAttribute("role", "button");
      li.setAttribute("tabindex", "0");
      li.addEventListener("click", function () {
        picked[p.code] = !picked[p.code];
        render();
      });
      li.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); li.click(); }
      });
      list.appendChild(li);
    });

    Array.prototype.forEach.call(tabs, function (b) {
      b.addEventListener("click", function () {
        layer = b.dataset.layer;
        Array.prototype.forEach.call(tabs, function (x) {
          x.classList.toggle("on", x === b);
        });
        render();
      });
    });

    render();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
