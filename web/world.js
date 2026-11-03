/* Globus terraqui d'enquestes (03/11/2026).
 *
 * web/world.json porta les fronteres en longitud i latitud (Natural Earth). Aqui
 * es projecten amb la projeccio ortografica, la vista d'una esfera des de
 * l'espai, i es dibuixen en un <canvas> a cada gir.
 *
 * Arrossegar fa girar el globus (amb inercia), la roda o el pessic apropen, i
 * els botons Europa i Mon hi volen. Al principi gira sol, a poc a poc, fins que
 * algu el toca (no gira si el sistema demana menys moviment).
 * Cada pais amb enquestes va del color de qui encapcala la mitjana i en fer-hi
 * clic s'obre la seva pagina. La taula de sota porta els mateixos enllacos per a
 * qui no pugui fer servir el globus.
 */
(function () {
  "use strict";
  var box = document.getElementById("pbworld");
  var raw = document.getElementById("pbworld-data");
  if (!box || !raw) return;
  var data = JSON.parse(raw.textContent);
  var tip = box.querySelector(".wtip");
  var canvas = document.createElement("canvas");
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", box.getAttribute("data-label") || "");
  box.insertBefore(canvas, box.firstChild);
  var ctx = canvas.getContext("2d");
  var D2R = Math.PI / 180;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Estat de la camera: centre del globus (lon, lat) i zoom (1 = globus sencer).
  var lon0 = -20, lat0 = 25, zoom = 1;
  var feats = [], W = 0, H = 0, dpr = 1, R = 0, cx = 0, cy = 0;
  var spinning = !reduce, vel = 0, flight = null, hover = null, dirty = true;
  var css = getComputedStyle(document.documentElement);
  function v(name, fallback) { return (css.getPropertyValue(name) || "").trim() || fallback; }
  var C = {
    land: v("--line", "#262b38"), edge: v("--bg", "#0f1116"), ink: v("--ink", "#e8ebf2"),
    // Fan eleccions pero no tenen enquestes: un gris mes clar que la resta.
    vote: "#4a5872",
    sea0: "#1d3b63", sea1: "#0b1a30", glow: "rgba(110,170,255,0.35)"
  };

  fetch(window.PB.root + "assets/world.json")
    .then(function (r) { return r.json(); })
    .then(load)
    .catch(function () { box.classList.add("failed"); });

  function load(w) {
    var q = w.q;
    w.f.forEach(function (f) {
      var rings = f.r.map(function (r) {
        var n = r.length / 2, x = 0, y = 0;
        var cl = new Float64Array(n), sl = new Float64Array(n),
            cp = new Float64Array(n), sp = new Float64Array(n);
        for (var i = 0; i < n; i++) {
          x += r[2 * i]; y += r[2 * i + 1];
          var la = x / q * D2R, ph = y / q * D2R;
          cl[i] = Math.cos(la); sl[i] = Math.sin(la);
          cp[i] = Math.cos(ph); sp[i] = Math.sin(ph);
        }
        return { cl: cl, sl: sl, cp: cp, sp: sp, n: n };
      });
      var info = data[f.c] || null;
      // Una regio sense enquestes propies no es dibuixa: ja hi es el seu pais.
      if (f.c.indexOf("-") > 0 && !info) return;
      feats.push({ c: f.c, n: f.n, info: info, rings: rings, path: null, region: f.c.indexOf("-") > 0 });
    });
    // Els paisos amb dades, al final: es dibuixen per sobre i es proven primer.
    feats.sort(function (a, b) { return (a.info ? 1 : 0) - (b.info ? 1 : 0); });
    resize();
    wire();
    requestAnimationFrame(frame);
  }

  function resize() {
    dpr = window.devicePixelRatio || 1;
    W = box.clientWidth; H = box.clientHeight;
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    canvas.style.width = W + "px"; canvas.style.height = H + "px";
    dirty = true;
  }

  /* Projeccio ortografica. Els punts de la cara oculta es porten a la vora del
   * disc en la mateixa direccio: aixi un pais mig amagat queda tallat net a
   * l'horitzo en lloc de fer una taca estranya. */
  function draw() {
    R = Math.min(W, H) * 0.46 * zoom;
    cx = W / 2; cy = H / 2;
    var cL = Math.cos(lon0 * D2R), sL = Math.sin(lon0 * D2R);
    var cP = Math.cos(lat0 * D2R), sP = Math.sin(lat0 * D2R);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);

    // Atmosfera i mar.
    var g = ctx.createRadialGradient(cx, cy, R * 0.98, cx, cy, R * 1.12);
    g.addColorStop(0, C.glow); g.addColorStop(1, "rgba(110,170,255,0)");
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(cx, cy, R * 1.12, 0, 2 * Math.PI); ctx.fill();
    var s = ctx.createRadialGradient(cx - R * 0.35, cy - R * 0.4, R * 0.1, cx, cy, R);
    s.addColorStop(0, C.sea0); s.addColorStop(1, C.sea1);
    ctx.fillStyle = s;
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, 2 * Math.PI); ctx.fill();

    graticule(cL, sL, cP, sP);

    ctx.lineJoin = "round";
    for (var k = 0; k < feats.length; k++) {
      var f = feats[k], path = new Path2D(), any = false;
      for (var j = 0; j < f.rings.length; j++) {
        var r = f.rings[j], vis = 0, n = r.n, i;
        // Primer, si se'n veu algun punt: un anell del tot amagat no es dibuixa.
        for (i = 0; i < n; i += 3) {
          var cd = r.cl[i] * cL + r.sl[i] * sL;
          if (sP * r.sp[i] + cP * r.cp[i] * cd > 0) { vis = 1; break; }
        }
        if (!vis) continue;
        for (i = 0; i < n; i++) {
          var cosd = r.cl[i] * cL + r.sl[i] * sL;          // cos(lon - lon0)
          var sind = r.sl[i] * cL - r.cl[i] * sL;          // sin(lon - lon0)
          var x = r.cp[i] * sind;
          var y = cP * r.sp[i] - sP * r.cp[i] * cosd;
          if (sP * r.sp[i] + cP * r.cp[i] * cosd < 0) {    // cara oculta
            var m = Math.hypot(x, y) || 1;
            x /= m; y /= m;
          }
          var px = cx + x * R, py = cy - y * R;
          if (i) path.lineTo(px, py); else path.moveTo(px, py);
        }
        path.closePath();
        any = true;
      }
      f.path = any ? path : null;
      if (!any) continue;
      var has = f.info && f.info.color;
      ctx.fillStyle = has ? f.info.color : (f.info && f.info.nopoll ? C.vote : C.land);
      ctx.fill(path, "evenodd");
      if (f === hover) {
        ctx.strokeStyle = C.ink; ctx.lineWidth = 1.6;
      } else if (f.region) {
        // Una regio son diverses provincies: la vora del seu propi color amaga
        // les fronteres internes (les de Flandes, les dels comtats escocesos).
        ctx.strokeStyle = f.info ? f.info.color : C.land; ctx.lineWidth = 0.6;
      } else {
        ctx.strokeStyle = C.edge; ctx.lineWidth = has ? 0.8 : 0.5;
      }
      ctx.stroke(path);
    }
    // Ombra suau a la vora per donar volum.
    var sh = ctx.createRadialGradient(cx, cy, R * 0.75, cx, cy, R);
    sh.addColorStop(0, "rgba(0,0,0,0)"); sh.addColorStop(1, "rgba(0,0,0,0.35)");
    ctx.fillStyle = sh;
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, 2 * Math.PI); ctx.fill();
  }

  function graticule(cL, sL, cP, sP) {
    ctx.strokeStyle = "rgba(255,255,255,0.07)";
    ctx.lineWidth = 0.6;
    ctx.beginPath();
    function line(points) {
      var pen = false;
      points.forEach(function (p) {
        var la = p[0] * D2R, ph = p[1] * D2R;
        var cl = Math.cos(la), sl = Math.sin(la), cp = Math.cos(ph), sp = Math.sin(ph);
        var cosd = cl * cL + sl * sL, sind = sl * cL - cl * sL;
        if (sP * sp + cP * cp * cosd < 0) { pen = false; return; }
        var px = cx + cp * sind * R, py = cy - (cP * sp - sP * cp * cosd) * R;
        if (pen) ctx.lineTo(px, py); else ctx.moveTo(px, py);
        pen = true;
      });
    }
    var lo, la, pts;
    for (lo = -180; lo < 180; lo += 30) {
      pts = [];
      for (la = -80; la <= 80; la += 4) pts.push([lo, la]);
      line(pts);
    }
    for (la = -60; la <= 60; la += 30) {
      pts = [];
      for (lo = -180; lo <= 180; lo += 4) pts.push([lo, la]);
      line(pts);
    }
    ctx.stroke();
  }

  var dragging = false, moved = false, last = null, pts = {}, pinch = null;

  function frame() {
    if (flight) {
      var t = Math.min(1, (performance.now() - flight.t0) / flight.ms);
      var e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      lon0 = flight.l0 + flight.dl * e;
      lat0 = flight.p0 + (flight.p1 - flight.p0) * e;
      zoom = flight.z0 + (flight.z1 - flight.z0) * e;
      if (t >= 1) flight = null;
      dirty = true;
    } else if (vel && !dragging) {
      lon0 -= vel; vel *= 0.94;
      if (Math.abs(vel) < 0.01) vel = 0;
      dirty = true;
    } else if (spinning) {
      lon0 += 0.08; dirty = true;
    }
    if (dirty) { draw(); dirty = false; }
    requestAnimationFrame(frame);
  }

  function stop() { spinning = false; flight = null; }

  function fly(lon, lat, z) {
    stop(); vel = 0;
    var dl = ((lon - lon0) % 360 + 540) % 360 - 180;     // pel cami curt
    flight = { t0: performance.now(), ms: 900, l0: lon0, dl: dl, p0: lat0, p1: lat, z0: zoom, z1: z };
  }

  function setZoom(z) { zoom = Math.max(0.8, Math.min(14, z)); dirty = true; }

  function wire() {
    box.querySelectorAll("[data-z]").forEach(function (b) {
      b.addEventListener("click", function () {
        var z = b.getAttribute("data-z");
        if (z === "in") { stop(); setZoom(zoom * 1.5); }
        else if (z === "out") { stop(); setZoom(zoom / 1.5); }
        else if (z === "europe") fly(12, 50, 3.2);
        else fly(-20, 25, 1);
      });
    });
    canvas.addEventListener("wheel", function (ev) {
      ev.preventDefault(); stop();
      setZoom(zoom * (ev.deltaY < 0 ? 1.15 : 1 / 1.15));
    }, { passive: false });

    canvas.addEventListener("pointerdown", function (ev) {
      stop(); vel = 0;
      pts[ev.pointerId] = [ev.clientX, ev.clientY];
      dragging = true; moved = false; last = [ev.clientX, ev.clientY];
      if (Object.keys(pts).length === 2) pinch = spread();
      if (canvas.setPointerCapture) canvas.setPointerCapture(ev.pointerId);
    });
    canvas.addEventListener("pointermove", function (ev) {
      if (!dragging) { hoverAt(ev); return; }
      pts[ev.pointerId] = [ev.clientX, ev.clientY];
      if (Object.keys(pts).length === 2 && pinch) {
        var sp = spread(); setZoom(zoom * sp / pinch); pinch = sp; moved = true; return;
      }
      var dx = ev.clientX - last[0], dy = ev.clientY - last[1];
      if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
      if (!moved) return;
      // Graus per pixel: un radi del globus son 90 graus.
      var k = 90 / R;
      lon0 -= dx * k; lat0 = Math.max(-85, Math.min(85, lat0 + dy * k));
      vel = dx * k * 0.6;
      last = [ev.clientX, ev.clientY];
      dirty = true; hide();
    });
    function up(ev) {
      delete pts[ev.pointerId];
      if (Object.keys(pts).length < 2) pinch = null;
      if (Object.keys(pts).length === 0) dragging = false;
    }
    canvas.addEventListener("pointerup", up);
    canvas.addEventListener("pointercancel", up);
    canvas.addEventListener("pointerleave", function () {
      if (!dragging) { hover = null; hide(); dirty = true; }
    });
    canvas.addEventListener("click", function (ev) {
      if (moved) { moved = false; return; }
      var f = hit(ev);
      if (f && f.info && f.info.url) window.location.href = window.PB.root + f.info.url.replace(/^\//, "");
    });
    window.addEventListener("resize", resize);

    function spread() {
      var p = Object.keys(pts).map(function (k) { return pts[k]; });
      return Math.hypot(p[0][0] - p[1][0], p[0][1] - p[1][1]) || 1;
    }
  }

  function hit(ev) {
    var rect = canvas.getBoundingClientRect();
    var x = ev.clientX - rect.left, y = ev.clientY - rect.top;
    if ((x - cx) * (x - cx) + (y - cy) * (y - cy) > R * R) return null;
    // isPointInPath fa servir la transformacio actual: la del dibuix (dpr).
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    for (var k = feats.length - 1; k >= 0; k--) {
      var f = feats[k];
      if (f.path && ctx.isPointInPath(f.path, x * dpr, y * dpr, "evenodd")) return f;
    }
    return null;
  }

  function hoverAt(ev) {
    var f = hit(ev);
    if (f !== hover) { hover = f; dirty = true; }
    canvas.style.cursor = f && f.info && f.info.url ? "pointer" : "grab";
    if (!f) { hide(); return; }
    show(ev, f.info || { name: f.n });
  }

  function show(ev, info) {
    tip.textContent = "";
    var b = document.createElement("b");
    b.textContent = info.name;
    tip.appendChild(b);
    var lines = info.first ? [info.first, info.second]
      : info.noelection ? [box.getAttribute("data-noelection")]
      : [box.getAttribute("data-empty"),
         info.leg ? box.getAttribute("data-leg") + ": " + info.leg : "",
         info.pres ? box.getAttribute("data-pres") + ": " + info.pres : ""];
    lines.forEach(function (t) {
      if (!t) return;
      var d = document.createElement("div");
      d.textContent = t;
      tip.appendChild(d);
    });
    tip.hidden = false;
    var r = box.getBoundingClientRect();
    var x = ev.clientX - r.left + 14, y = ev.clientY - r.top + 14;
    if (x + tip.offsetWidth > r.width) x = Math.max(4, x - tip.offsetWidth - 28);
    tip.style.left = x + "px";
    tip.style.top = y + "px";
  }

  function hide() { tip.hidden = true; }
})();
