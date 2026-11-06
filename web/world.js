/* Globus terraqui d'enquestes (03/11/2026).
 *
 * web/world.json porta les fronteres en longitud i latitud (Natural Earth 1:10m).
 * Aqui es projecten amb la projeccio ortografica, la vista d'una esfera des de
 * l'espai, i es dibuixen en un <canvas> a cada gir. Cada punt porta un nivell de
 * detall: de lluny nomes es dibuixen els que es noten, i en apropar-se hi surten
 * tots (05/11/2026).
 *
 * El relleu (web/relief.jpg, Natural Earth SR_50M) es pinta en un segon <canvas>
 * amb WebGL, a sobre: un vel negre transparent als vessants a l'ombra i un de
 * blanc als il·luminats, que enfosqueixen o aclareixen suaument el color de
 * cada pais, sigui quin sigui. Si el navegador no te WebGL, el
 * globus surt igual pero pla.
 *
 * Sobre el globus no hi ha cap text fins que el ratoli passa per un pais.
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
  var card = box.querySelector(".wcard");
  var canvas = document.createElement("canvas");
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", box.getAttribute("data-label") || "");
  box.insertBefore(canvas, box.firstChild);
  var ctx = canvas.getContext("2d");
  var relief = makeRelief();
  // Fronteres, ressaltat i ombra de la vora, per sobre de les banderes i el relleu
  // (06/11/2026): el canvas de sota nomes pinta el mar i la terra.
  var lines = document.createElement("canvas");
  lines.className = "wlines";
  lines.setAttribute("aria-hidden", "true");
  box.insertBefore(lines, (relief && relief.el ? relief.el : canvas).nextSibling);
  var ltx = lines.getContext("2d");
  var D2R = Math.PI / 180;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Estat de la camera: centre del globus (lon, lat) i zoom (1 = globus sencer).
  // Al principi, Europa i l'Atlantic: hi ha la majoria de paisos amb enquestes.
  var lon0 = 2, lat0 = 30, zoom = 1;
  var feats = [], W = 0, H = 0, dpr = 1, R = 0, cx = 0, cy = 0;
  var spinning = !reduce, vel = 0, flight = null, hover = null, picked = null, dirty = true;
  // Colors fixos: l'espai es fosc tambe amb el tema clar (abans la terra sense
  // eleccions agafava el gris de les vores del tema i amb el clar quedava blanca).
  var C = {
    land: "#2b3346", edge: "rgba(6,9,15,0.85)", ink: "#e8ebf2",
    // Fan eleccions pero no tenen enquestes: un gris mes clar que la resta.
    vote: "#4a5872",
    sea0: "#1d3b63", sea1: "#0b1a30"
  };

  var TOL = [0.2];
  fetch(window.PB.root + "assets/world.json")
    .then(function (r) { return r.json(); })
    .then(load)
    .catch(function () { box.classList.add("failed"); });

  function load(w) {
    var q = w.q;
    TOL = w.t || TOL;
    w.f.forEach(function (f) {
      var rings = f.r.map(function (r, j) {
        var n = r.length / 2, x = 0, y = 0;
        var cl = new Float64Array(n), sl = new Float64Array(n),
            cp = new Float64Array(n), sp = new Float64Array(n), lv = new Uint8Array(n);
        var ls = f.l ? f.l[j] : "";
        for (var i = 0; i < n; i++) {
          lv[i] = ls ? ls.charCodeAt(i) - 48 : 0;
          x += r[2 * i]; y += r[2 * i + 1];
          var la = x / q * D2R, ph = y / q * D2R;
          cl[i] = Math.cos(la); sl[i] = Math.sin(la);
          cp[i] = Math.cos(ph); sp[i] = Math.sin(ph);
        }
        return { cl: cl, sl: sl, cp: cp, sp: sp, lv: lv, n: n };
      });
      var info = data[f.c] || null;
      // Una regio sense enquestes propies no es dibuixa: ja hi es el seu pais.
      if (f.c.indexOf("-") > 0 && !info) return;
      feats.push({ c: f.c, n: f.n, info: info, rings: rings, path: null,
                   region: f.c.indexOf("-") > 0 });
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
    lines.width = canvas.width; lines.height = canvas.height;
    lines.style.width = W + "px"; lines.style.height = H + "px";
    if (relief) relief.size(canvas.width, canvas.height, W, H);
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
    ltx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ltx.clearRect(0, 0, W, H);

    // El mar, sense halo ni linia a la vora (05/11/2026).
    var s = ctx.createRadialGradient(cx - R * 0.35, cy - R * 0.4, R * 0.1, cx, cy, R);
    s.addColorStop(0, C.sea0); s.addColorStop(1, C.sea1);
    ctx.fillStyle = s;
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, 2 * Math.PI); ctx.fill();

    // Quins nivells de detall es dibuixen: els que canvien la forma mes de mig
    // pixel a la mida actual del globus.
    var allow = 0.5 / (R * D2R), L = 1;
    for (var t = 1; t < TOL.length; t++) if (TOL[t - 1] > allow) L = t + 1;

    ltx.lineJoin = "round";
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
          if (r.lv[i] >= L) continue;                       // detall que no es nota
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
      // Cada pais porta la seva bandera (textura del relleu, a sobre): aqui nomes
      // la terra en gris, que es veu on no n'hi ha (Xipre del Nord, Somalilandia).
      // Sense WebGL no hi ha banderes: llavors, el color de qui va primer, com abans.
      if (!relief) {
        ctx.fillStyle = f.info && f.info.color ? f.info.color : (f.info && f.info.nopoll ? C.vote : C.land);
        ctx.fill(path, "evenodd");
      } else if (!f.region) { ctx.fillStyle = C.land; ctx.fill(path, "evenodd"); }
      if (f === hover || f === picked) {
        ltx.strokeStyle = C.ink; ltx.lineWidth = 1.8;
      } else if (f.region) {
        continue;            // Escocia, Baviera...: la bandera i la vora son del pais
      } else {
        ltx.strokeStyle = C.edge; ltx.lineWidth = 0.7;
      }
      ltx.stroke(path);
    }
    // El ressaltat, per sobre de les fronteres veines.
    [hover, picked].forEach(function (f) {
      if (f && f.path) { ltx.strokeStyle = C.ink; ltx.lineWidth = 1.8; ltx.stroke(f.path); }
    });
    // Ombra suau a la vora per donar volum.
    var sh = ltx.createRadialGradient(cx, cy, R * 0.7, cx, cy, R);
    sh.addColorStop(0, "rgba(0,0,0,0)"); sh.addColorStop(1, "rgba(0,0,0,0.3)");
    ltx.fillStyle = sh;
    ltx.beginPath(); ltx.arc(cx, cy, R, 0, 2 * Math.PI); ltx.fill();
    if (relief) relief.draw(cx * dpr, cy * dpr, R * dpr, lon0 * D2R, lat0 * D2R);
  }

  /* Relleu: un segon canvas amb WebGL, a sobre del primer i sense rebre clics.
   * Per a cada pixel del disc es desfa la projeccio ortografica (pixel -> lon,
   * lat) i es llegeix la textura equirectangular del relleu. El gris 128 es el
   * pla (transparent); per sota, ombra; per sobre, llum. */
  function makeRelief() {
    var c = document.createElement("canvas");
    c.className = "wrelief";
    c.setAttribute("aria-hidden", "true");
    var gl = null;
    try { gl = c.getContext("webgl", { alpha: true, premultipliedAlpha: true, antialias: false }); }
    catch (e) { gl = null; }
    if (!gl) return null;
    var vs = "attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}";
    var fs = [
      "#ifdef GL_FRAGMENT_PRECISION_HIGH",
      "precision highp float;",
      "#else",
      "precision mediump float;",
      "#endif",
      "uniform vec3 uC;",          // centre x, centre y (des de baix), radi (pixels)
      "uniform vec3 uV;",          // lon0, cos lat0, sin lat0
      "uniform vec2 uK;",          // intensitat de l'ombra i de la llum
      "uniform sampler2D uT;",
      "uniform sampler2D uF;",     // banderes (RGBA, equirectangular com el relleu)
      "const float PI = 3.14159265;",
      "void main(){",
      "  vec2 q = (gl_FragCoord.xy - uC.xy) / uC.z;",       // y cap amunt
      "  float rr = dot(q, q);",
      "  if (rr >= 1.) { gl_FragColor = vec4(0.); return; }",
      "  float z = sqrt(1. - rr);",
      "  float lat = asin(clamp(q.y * uV.y + z * uV.z, -1., 1.));",
      "  float lon = uV.x + atan(q.x, z * uV.y - q.y * uV.z);",
      "  vec2 uv = vec2(fract(lon / (2. * PI) + .5), .5 - lat / PI);",
      "  float g = texture2D(uT, uv).r;",
      // Banderes difuminades (06/11/2026): un nivell de mipmap mes borros, una mica
      // menys saturades i amb el gris de la terra que s'hi transparenta.
      "  vec4 fl = texture2D(uF, uv, 1.2);",
      "  float lum = dot(fl.rgb, vec3(.299, .587, .114));",
      "  fl.rgb = mix(vec3(lum), fl.rgb, .72);",
      "  fl.a *= .78;",
      // A la vora el relleu s'esvaeix: alli els pixels son molt estirats.
      "  float d = (g - .5) * 2. * (1. - smoothstep(.85, 1., rr));",
      // Vel del relleu (negre o blanc, premultiplicat) sobre la bandera.
      "  vec4 v = d < 0. ? vec4(0., 0., 0., -d * uK.x) : vec4(vec3(d * uK.y), d * uK.y);",
      "  vec4 b = vec4(fl.rgb * fl.a, fl.a);",
      "  gl_FragColor = v + b * (1. - v.a);",
      "}"].join("\n");
    function sh(type, src) {
      var o = gl.createShader(type);
      gl.shaderSource(o, src); gl.compileShader(o);
      return gl.getShaderParameter(o, gl.COMPILE_STATUS) ? o : null;
    }
    var v = sh(gl.VERTEX_SHADER, vs), f = sh(gl.FRAGMENT_SHADER, fs);
    if (!v || !f) return null;
    var prog = gl.createProgram();
    gl.attachShader(prog, v); gl.attachShader(prog, f); gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return null;
    gl.useProgram(prog);
    var buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    var ap = gl.getAttribLocation(prog, "p");
    gl.enableVertexAttribArray(ap);
    gl.vertexAttribPointer(ap, 2, gl.FLOAT, false, 0, 0);
    var uC = gl.getUniformLocation(prog, "uC"), uV = gl.getUniformLocation(prog, "uV"),
        uK = gl.getUniformLocation(prog, "uK");
    gl.uniform1i(gl.getUniformLocation(prog, "uT"), 0);
    gl.uniform1i(gl.getUniformLocation(prog, "uF"), 1);
    gl.activeTexture(gl.TEXTURE1);
    var ftex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, ftex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(4));
    gl.activeTexture(gl.TEXTURE0);
    var fimg = new Image();
    fimg.onload = function () {
      // Els mobils mes vells no carreguen textures de 8192: es redueix a la meitat.
      var src = fimg, max = gl.getParameter(gl.MAX_TEXTURE_SIZE);
      if (max < fimg.width) {
        src = document.createElement("canvas");
        src.width = max; src.height = max / 2;
        src.getContext("2d").drawImage(fimg, 0, 0, max, max / 2);
      }
      gl.activeTexture(gl.TEXTURE1);
      gl.bindTexture(gl.TEXTURE_2D, ftex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, src);
      gl.generateMipmap(gl.TEXTURE_2D);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.activeTexture(gl.TEXTURE0);
      dirty = true;
    };
    var ready = false;
    var img = new Image();
    img.onload = function () {
      var tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.LUMINANCE, gl.LUMINANCE, gl.UNSIGNED_BYTE, img);
      gl.generateMipmap(gl.TEXTURE_2D);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      ready = true; dirty = true;
    };
    img.src = window.PB.root + "assets/relief.jpg";
    fimg.src = window.PB.root + "assets/flags.webp";
    canvas.parentNode.insertBefore(c, canvas.nextSibling);
    return {
      el: c,
      size: function (w, h, cw, ch) {
        c.width = w; c.height = h;
        c.style.width = cw + "px"; c.style.height = ch + "px";
        gl.viewport(0, 0, w, h);
      },
      draw: function (x, y, r, lon, lat) {
        if (!ready) return;
        gl.clearColor(0, 0, 0, 0);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.uniform3f(uC, x, c.height - y, r);
        gl.uniform3f(uV, lon, Math.cos(lat), Math.sin(lat));
        gl.uniform2f(uK, 0.42, 0.8);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      }
    };
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
        else if (z === "americas") fly(-78, 12, 1.5);
        else if (z === "asia") fly(108, 22, 1.6);
        else fly(2, 30, 1);
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
      if (!R) return;                                  // encara no dibuixat
      var k = 90 / R;
      lon0 -= dx * k; lat0 = Math.max(-85, Math.min(85, lat0 + dy * k));
      if (!card.hidden) closeCard();
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
    // Clicar (o tocar) un pais amb enquestes porta a la seva pagina: el lloc
    // comenca al globus (05/11/2026). Un pais sense enquestes ensenya una fitxa
    // amb quan vota, perque amb el dit no hi ha "passar per sobre".
    canvas.addEventListener("click", function (ev) {
      if (moved) { moved = false; return; }
      var f = hit(ev);
      if (f && f.info && f.info.url) {
        window.location.href = window.PB.root + f.info.url.replace(/^\//, "");
        return;
      }
      if (f) openCard(f); else closeCard();
    });
    card.addEventListener("click", function (ev) {
      if (ev.target.classList.contains("x")) closeCard();
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

  /* El contingut de la bafarada i de la fitxa: nom, primer i segon amb el seu
   * color, i quantes enquestes hi ha; o quan vota, si no n'hi ha cap. */
  function fill(el, info) {
    el.textContent = "";
    var b = document.createElement("b");
    b.textContent = info.name;
    el.appendChild(b);
    function row(text, color) {
      if (!text) return;
      var d = document.createElement("div");
      if (color) {
        var sw = document.createElement("span");
        sw.className = "sw"; sw.style.background = color;
        d.appendChild(sw);
      }
      d.appendChild(document.createTextNode(text));
      el.appendChild(d);
    }
    function meta(text) {
      var d = document.createElement("div");
      d.className = "meta"; d.textContent = text; el.appendChild(d);
    }
    if (info.first) {
      row(info.first, info.color);
      row(info.second, info.c2);
      var m = [];
      if (info.pres) m.push(box.getAttribute("data-pres"));
      if (info.n) m.push(info.n + " " + box.getAttribute("data-polls"));
      if (m.length) meta(m.join(" · "));
    } else if (info.noelection) {
      row(box.getAttribute("data-noelection"));
    } else {
      row(box.getAttribute("data-empty"));
      row(info.leg ? box.getAttribute("data-leg") + ": " + info.leg : "");
      row(info.pres ? box.getAttribute("data-pres") + ": " + info.pres : "");
    }
  }

  function openCard(f) {
    hide();
    picked = f; dirty = true;
    var info = f.info || { name: f.n };
    fill(card, info);
    var x = document.createElement("button");
    x.type = "button"; x.className = "x"; x.setAttribute("aria-label", "×"); x.textContent = "×";
    card.appendChild(x);
    if (info.url) {
      var a = document.createElement("a");
      a.className = "go"; a.href = window.PB.root + info.url.replace(/^\//, "");
      a.textContent = box.getAttribute("data-open") + " →";
      card.appendChild(a);
    }
    card.hidden = false;
    box.classList.add("carded");
  }

  function closeCard() {
    card.hidden = true; box.classList.remove("carded");
    if (picked) { picked = null; dirty = true; }
  }

  function show(ev, info) {
    fill(tip, info);
    if (info.url) {
      var d = document.createElement("div");
      d.className = "meta"; d.textContent = box.getAttribute("data-click"); tip.appendChild(d);
    }
    tip.hidden = false;
    var r = box.getBoundingClientRect();
    var x = ev.clientX - r.left + 14, y = ev.clientY - r.top + 14;
    if (x + tip.offsetWidth > r.width) x = Math.max(4, x - tip.offsetWidth - 28);
    tip.style.left = x + "px";
    tip.style.top = y + "px";
  }

  function hide() { tip.hidden = true; }
})();
