/* Polit Bureau — mapa de seccions i meses d'un municipi.
 *
 * Les meses no tenen contorn: son parts d'una seccio censal (per ordre
 * alfabetic dels electors). Cada taca es una seccio, i en passar-hi per sobre
 * surten les seves meses. Els contorns venen quantitzats i codificats en
 * diferencies ([x, y, dx, dy, ...]), que es justament el que demana un path SVG
 * amb ordres relatives: no cal descodificar res.
 *
 * SVG i no canvas: la ciutat mes gran (Madrid) te unes 2.400 seccions, i a
 * aquesta escala el DOM ho aguanta be i a canvi tenim hover i clic gratis.
 */
(function () {
  const box = document.getElementById('secmap');
  if (!box) return;
  const svg = document.getElementById('secmap-svg');
  const info = document.getElementById('secmap-info');
  const legend = document.getElementById('secmap-legend');
  const select = document.getElementById('secmap-by');
  const NS = 'http://www.w3.org/2000/svg';
  const ca = document.documentElement.lang === 'ca';
  const T = ca ? {
    first: '1a força 29N (estimació)', turnout: 'Participació 23J (final)',
    t14: 'Participació 23J a les 14:00', share: 'Estimació 29N: ',
    dist: 'Dte.', sec: 'Secc.', mesas: 'Meses', electors: 'Electors 29N (est.)',
    part: 'Participació 23J', est: 'Estimació 29N', nodata: 'Sense dades d\'aquesta secció',
    renda: 'Renda per persona (INE 2023)',
  } : {
    first: '1.ª fuerza 29N (estimación)', turnout: 'Participación 23J (final)',
    t14: 'Participación 23J a las 14:00', share: 'Estimación 29N: ',
    dist: 'Dist.', sec: 'Secc.', mesas: 'Mesas', electors: 'Electores 29N (est.)',
    part: 'Participación 23J', est: 'Estimación 29N', nodata: 'Sin datos de esta sección',
    renda: 'Renta por persona (INE 2023)',
  };
  const num = (x, d = 1) => (x == null ? '—' : x.toFixed(d).replace('.', ','));
  const pc = (x) => (x == null ? '—' : num(x) + '%');
  const eur = (x) => (x == null ? '—' : Math.round(x).toLocaleString('es-ES') + ' €');
  const thousands = (n) => (n == null ? '—' : Math.round(n).toLocaleString('es-ES'));

  let doc, view, full, paths = {}, mode = 'first';

  fetch(box.dataset.src).then((r) => r.json()).then((d) => { doc = d; init(); })
    .catch(() => { box.hidden = true; });

  function init() {
    const P = doc.d.parties;
    const opts = [['first', T.first], ['turnout', T.turnout], ['t14', T.t14], ['renda', T.renda]]
      .concat(P.map((p, i) => ['p' + i, T.share + p.name]));
    select.innerHTML = opts.map(([v, l]) => `<option value="${v}">${l}</option>`).join('');
    select.onchange = () => { mode = select.value; paint(); };

    full = { x: -doc.w * 0.02, y: -doc.h * 0.02, w: doc.w * 1.04, h: doc.h * 1.04 };
    view = { ...full };
    const frag = document.createDocumentFragment();
    for (const [key, rings] of Object.entries(doc.s)) {
      const path = document.createElementNS(NS, 'path');
      path.setAttribute('d', rings.map((r) => 'M' + r[0] + ' ' + r[1] + 'l' + r.slice(2).join(' ') + 'z').join(''));
      path.setAttribute('fill-rule', 'evenodd');
      path.dataset.k = key;
      paths[key] = path;
      frag.appendChild(path);
    }
    svg.appendChild(frag);
    setView();
    paint();
    wire();
  }

  function setView() {
    svg.setAttribute('viewBox', `${view.x} ${view.y} ${view.w} ${view.h}`);
  }

  // Escala d'un sol to (el de l'accent o el del partit) amb opacitat segons el
  // valor: funciona igual en mode clar i fosc, i el gris queda per "sense dades".
  function range(get) {
    const vals = Object.values(doc.d.sections).map(get).filter((v) => v != null);
    return [Math.min(...vals), Math.max(...vals)];
  }

  function paint() {
    const S = doc.d.sections, P = doc.d.parties;
    const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#5b8def';
    let get, colour, lo, hi;
    if (mode === 'first') {
      get = (s) => (s.f == null ? null : s.s[s.f]);
      [lo, hi] = range(get);
      colour = (s) => P[s.f].color;
    } else if (mode === 'renda') {
      get = (s) => s.r;
      [lo, hi] = range(get);
      colour = () => accent;
    } else if (mode === 'turnout' || mode === 't14') {
      const i = mode === 'turnout' ? 2 : 0;
      get = (s) => s.t[i];
      [lo, hi] = range(get);
      colour = () => accent;
    } else {
      const i = +mode.slice(1);
      get = (s) => s.s[i];
      [lo, hi] = range(get);
      colour = () => P[i].color;
    }
    const span = hi - lo || 1;
    for (const [key, path] of Object.entries(paths)) {
      const s = S[key];
      const v = s ? get(s) : null;
      if (v == null) { path.setAttribute('fill', '#8a8f9c'); path.setAttribute('fill-opacity', '0.25'); continue; }
      path.setAttribute('fill', colour(s));
      path.setAttribute('fill-opacity', (0.22 + 0.78 * (v - lo) / span).toFixed(2));
    }
    drawLegend(lo, hi, mode === 'first' ? null : colour(Object.values(S)[0] || {}));
  }

  function drawLegend(lo, hi, hue) {
    const S = doc.d.sections, P = doc.d.parties;
    if (mode === 'first') {
      const count = {};
      for (const s of Object.values(S)) if (s.f != null) count[s.f] = (count[s.f] || 0) + 1;
      legend.innerHTML = Object.entries(count).sort((a, b) => b[1] - a[1]).map(([i, n]) =>
        `<span><span class="sw" style="background:${P[i].color}"></span>${P[i].name} · ${n}</span>`).join('');
      return;
    }
    const f = mode === 'renda' ? eur : pc;
    legend.innerHTML = `<span>${f(lo)}<span class="grad" style="background:linear-gradient(90deg, ${hue}38, ${hue})"></span>${f(hi)}</span>`;
  }

  function show(key, evt) {
    const s = doc.d.sections[key];
    const [d, sec] = key.split('-');
    for (const p of svg.querySelectorAll('path.on')) p.classList.remove('on');
    const path = paths[key];
    if (path) { path.classList.add('on'); path.parentNode.appendChild(path); }
    const dname = (doc.d.districts || {})[d];
    let html = `<b>${T.dist} ${d}${dname ? ' ' + dname : ''} · ${T.sec} ${sec}</b><br>`;
    if (!s) {
      html += T.nodata;
    } else {
      const P = doc.d.parties;
      const top = s.s.map((v, i) => [v, i]).sort((a, b) => b[0] - a[0]).slice(0, 4);
      html += `${T.mesas}: ${s.m.join(', ')}<br>${T.electors}: ${thousands(s.c)}<br>`
        + `${T.renda}: ${eur(s.r)}<br>`
        + `${T.part}: 14:00 ${pc(s.t[0])} · 18:00 ${pc(s.t[1])} · Final ${pc(s.t[2])}<br>`
        + `${T.est}: ` + top.map(([v, i]) =>
          `<span class="sw" style="background:${P[i].color}"></span>${P[i].name} ${pc(v)}`).join(' · ');
    }
    info.innerHTML = html;
    info.hidden = false;
  }

  function wire() {
    let drag = null, moved = false;
    svg.addEventListener('pointermove', (e) => {
      if (drag) {
        const r = svg.getBoundingClientRect();
        const k = Math.max(view.w / r.width, view.h / r.height);
        const dx = (e.clientX - drag.x) * k, dy = (e.clientY - drag.y) * k;
        if (Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y) > 3) moved = true;
        view.x = drag.vx - dx; view.y = drag.vy - dy; setView();
        return;
      }
      if (e.pointerType === 'mouse' && e.target.dataset.k) show(e.target.dataset.k, e);
    });
    svg.addEventListener('pointerdown', (e) => {
      drag = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y }; moved = false;
      svg.classList.add('drag');
    });
    const end = (e) => {
      if (drag && !moved && e.target.dataset && e.target.dataset.k) show(e.target.dataset.k, e);
      drag = null; svg.classList.remove('drag');
    };
    svg.addEventListener('pointerup', end);
    svg.addEventListener('pointerleave', () => { drag = null; svg.classList.remove('drag'); });
    svg.addEventListener('wheel', (e) => {
      e.preventDefault();
      zoom(e.deltaY < 0 ? 1.25 : 0.8, e);
    }, { passive: false });
    for (const b of box.querySelectorAll('.secmap-zoom button')) {
      b.onclick = () => (+b.dataset.z ? zoom(+b.dataset.z) : (view = { ...full }, setView()));
    }
  }

  // Apropa mantenint quiet el punt de sota el cursor (o el centre, amb els botons).
  function zoom(f, e) {
    const r = svg.getBoundingClientRect();
    const k = Math.max(view.w / r.width, view.h / r.height);
    const cx = e ? view.x + (e.clientX - r.left) * k - (r.width * k - view.w) / 2 : view.x + view.w / 2;
    const cy = e ? view.y + (e.clientY - r.top) * k - (r.height * k - view.h) / 2 : view.y + view.h / 2;
    const w = Math.min(full.w * 1.5, Math.max(full.w / 60, view.w / f));
    const h = w * view.h / view.w;
    view = { x: cx - (cx - view.x) * w / view.w, y: cy - (cy - view.y) * h / view.h, w, h };
    setView();
  }
})();
