/* Mapamundi d'enquestes (03/11/2026).
 *
 * Dibuixa web/world.json (Natural Earth, projeccio Equal Earth, ja projectat a
 * l'ordinador) com a SVG. Cada pais amb enquestes es un enllac <a> a la seva
 * pagina, pintat del color de qui encapcala la mitjana: es pot fer clic, tabular
 * i obrir en una pestanya nova sense cap JavaScript de navegacio.
 * Zoom amb la roda, els botons o pessigant; desplacament arrossegant.
 */
(function () {
  "use strict";
  var box = document.getElementById("pbworld");
  var raw = document.getElementById("pbworld-data");
  if (!box || !raw) return;
  var data = JSON.parse(raw.textContent);
  var NS = "http://www.w3.org/2000/svg";
  var tip = box.querySelector(".wtip");
  var svg, view, full, europe, world;

  fetch(window.PB.root + "assets/world.json")
    .then(function (r) { return r.json(); })
    .then(draw)
    .catch(function () { box.classList.add("failed"); });

  function el(name, attrs) {
    var n = document.createElementNS(NS, name);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }

  function draw(w) {
    full = [0, 0, w.w, w.h];
    var e = w.europe, m = w.world || [0, 0, w.w, w.h];
    europe = [e[0], e[1], e[2] - e[0], e[3] - e[1]];
    world = [m[0], m[1], m[2] - m[0], m[3] - m[1]];
    svg = el("svg", { role: "img", "aria-label": box.querySelector("[data-z=world]").textContent });
    var g = el("g", {});
    w.f.forEach(function (f) {
      var info = data[f.c];
      var path = el("path", { d: f.d, "class": info ? "has" : "" });
      if (info) {
        path.style.fill = info.color;
        var a = el("a", { href: window.PB.root + info.url.replace(/^\//, "") });
        a.setAttribute("aria-label", info.name + ": " + info.first);
        a.appendChild(path);
        a.addEventListener("mousemove", function (ev) { show(ev, info); });
        a.addEventListener("focus", function () { show(null, info); });
        a.addEventListener("mouseleave", hide);
        a.addEventListener("blur", hide);
        g.appendChild(a);
      } else {
        path.addEventListener("mousemove", function (ev) { show(ev, { name: f.n }); });
        path.addEventListener("mouseleave", hide);
        g.appendChild(path);
      }
    });
    svg.appendChild(g);
    box.insertBefore(svg, box.firstChild);
    set(fit(world));
    wire();
  }

  /* La caixa demanada, eixamplada perque tingui la proporcio del requadre. */
  function fit(b) {
    var r = box.clientWidth / box.clientHeight || 2;
    var x = b[0], y = b[1], w = b[2], h = b[3];
    if (w / h < r) { var nw = h * r; x -= (nw - w) / 2; w = nw; }
    else { var nh = w / r; y -= (nh - h) / 2; h = nh; }
    return [x, y, w, h];
  }

  function set(v) {
    // Ni mes lluny que el mon sencer ni mes a prop que un pais petit.
    var maxw = full[2] * 1.15, minw = full[2] / 60;
    if (v[2] > maxw) { var k = maxw / v[2]; v = [v[0] + v[2] * (1 - k) / 2, v[1] + v[3] * (1 - k) / 2, v[2] * k, v[3] * k]; }
    if (v[2] < minw) { var k2 = minw / v[2]; v = [v[0] - v[2] * (k2 - 1) / 2, v[1] - v[3] * (k2 - 1) / 2, v[2] * k2, v[3] * k2]; }
    view = v;
    svg.setAttribute("viewBox", v.join(" "));
    // El gruix de les fronteres no ha de creixer amb el zoom.
    svg.style.setProperty("--sw", (v[2] / box.clientWidth).toFixed(3));
  }

  function zoom(k, cx, cy) {
    var rect = svg.getBoundingClientRect();
    var fx = cx === undefined ? 0.5 : (cx - rect.left) / rect.width;
    var fy = cy === undefined ? 0.5 : (cy - rect.top) / rect.height;
    var w = view[2] * k, h = view[3] * k;
    set([view[0] + (view[2] - w) * fx, view[1] + (view[3] - h) * fy, w, h]);
  }

  function wire() {
    box.querySelectorAll("[data-z]").forEach(function (b) {
      b.addEventListener("click", function () {
        var z = b.getAttribute("data-z");
        if (z === "in") zoom(0.66);
        else if (z === "out") zoom(1.5);
        else set(fit(z === "world" ? world : europe));
      });
    });
    svg.addEventListener("wheel", function (ev) {
      ev.preventDefault();
      zoom(ev.deltaY < 0 ? 0.8 : 1.25, ev.clientX, ev.clientY);
    }, { passive: false });

    // Arrossegar (ratoli i dit) i pessigar (dos dits).
    var pts = {}, last = null, moved = false, pinch = null;
    svg.addEventListener("pointerdown", function (ev) {
      pts[ev.pointerId] = [ev.clientX, ev.clientY];
      moved = false; last = [ev.clientX, ev.clientY];
      if (Object.keys(pts).length === 2) pinch = spread();
    });
    window.addEventListener("pointermove", function (ev) {
      if (!pts[ev.pointerId]) return;
      pts[ev.pointerId] = [ev.clientX, ev.clientY];
      var ids = Object.keys(pts);
      if (ids.length === 2 && pinch) {
        var s = spread();
        var c = mid();
        zoom(pinch / s, c[0], c[1]);
        pinch = s; moved = true;
        return;
      }
      var dx = ev.clientX - last[0], dy = ev.clientY - last[1];
      if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
      if (!moved) return;
      var k = view[2] / svg.getBoundingClientRect().width;
      set([view[0] - dx * k, view[1] - dy * k, view[2], view[3]]);
      last = [ev.clientX, ev.clientY];
      hide();
    });
    window.addEventListener("pointerup", function (ev) {
      delete pts[ev.pointerId];
      if (Object.keys(pts).length < 2) pinch = null;
    });
    // Un arrossegament no ha d'acabar obrint el pais on s'ha deixat anar el dit.
    svg.addEventListener("click", function (ev) {
      if (moved) { ev.preventDefault(); moved = false; }
    }, true);
    window.addEventListener("resize", function () { set(fit(view)); });

    function spread() {
      var p = Object.values(pts);
      return Math.hypot(p[0][0] - p[1][0], p[0][1] - p[1][1]) || 1;
    }
    function mid() {
      var p = Object.values(pts);
      return [(p[0][0] + p[1][0]) / 2, (p[0][1] + p[1][1]) / 2];
    }
  }

  function show(ev, info) {
    tip.textContent = "";
    var b = document.createElement("b");
    b.textContent = info.name;
    tip.appendChild(b);
    var lines = info.first ? [info.first, info.second] : [box.getAttribute("data-empty")];
    lines.forEach(function (t) {
      if (!t) return;
      var d = document.createElement("div");
      d.textContent = t;
      tip.appendChild(d);
    });
    tip.hidden = false;
    var r = box.getBoundingClientRect();
    var x = ev ? ev.clientX - r.left + 14 : 12, y = ev ? ev.clientY - r.top + 14 : 12;
    if (x + tip.offsetWidth > r.width) x = Math.max(4, x - tip.offsetWidth - 28);
    tip.style.left = x + "px";
    tip.style.top = y + "px";
  }

  function hide() { tip.hidden = true; }
})();
