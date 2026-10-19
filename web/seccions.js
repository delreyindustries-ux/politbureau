/* Polit Bureau — mapa de seccions i meses d'un municipi.
 *
 * Les meses no tenen contorn: son parts d'una seccio censal (per ordre
 * alfabetic dels electors). Cada taca es una seccio, i en passar-hi per sobre
 * surten les seves meses. Els contorns venen quantitzats i codificats en
 * diferencies ([x, y, dx, dy, ...]), que es justament el que demana un path SVG
 * amb ordres relatives: no cal descodificar res.
 *
 * Dues vistes:
 *  - SVG (per defecte): nomes les seccions i els limits dels districtes. No fa
 *    cap peticio fora del lloc.
 *  - Mapa de la ciutat: carrers d'OpenFreeMap (dades d'OpenStreetMap) amb
 *    MapLibre, i les seccions a sobre. Nomes es carrega si el visitant prem el
 *    boto (decisio de l'Alfonso, 19/10/2026): el seu navegador envia la IP a
 *    unpkg.com i a tiles.openfreemap.org, i aixo no es pot fer sense que ho
 *    triï ell (RGPD; la politica de privadesa ho explica).
 */
(function () {
  const box = document.getElementById('secmap');
  if (!box) return;
  const svg = document.getElementById('secmap-svg');
  const info = document.getElementById('secmap-info');
  const legend = document.getElementById('secmap-legend');
  const select = document.getElementById('secmap-by');
  const cityBtn = document.getElementById('secmap-city');
  const NS = 'http://www.w3.org/2000/svg';
  const MAPLIBRE = 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl';
  const STYLE = 'https://tiles.openfreemap.org/styles/positron';
  const ca = document.documentElement.lang === 'ca';
  const T = ca ? {
    first: '1a força 29N (estimació)', turnout: 'Participació 23J (final)',
    t14: 'Participació 23J a les 14:00', share: 'Estimació 29N: ',
    dist: 'Dte.', sec: 'Secc.', mesas: 'Meses', electors: 'Electors 29N (est.)',
    part: 'Participació 23J', est: 'Estimació 29N', nodata: 'Sense dades d\'aquesta secció',
    renda: 'Renda per persona (INE 2023)', loading: 'Carregant el mapa…',
    failed: 'No s\'ha pogut carregar el mapa de la ciutat.', back: 'Tornar al mapa simple',
  } : {
    first: '1.ª fuerza 29N (estimación)', turnout: 'Participación 23J (final)',
    t14: 'Participación 23J a las 14:00', share: 'Estimación 29N: ',
    dist: 'Dist.', sec: 'Secc.', mesas: 'Mesas', electors: 'Electores 29N (est.)',
    part: 'Participación 23J', est: 'Estimación 29N', nodata: 'Sin datos de esta sección',
    renda: 'Renta por persona (INE 2023)', loading: 'Cargando el mapa…',
    failed: 'No se ha podido cargar el mapa de la ciudad.', back: 'Volver al mapa simple',
  };
  const num = (x, d = 1) => (x == null ? '—' : x.toFixed(d).replace('.', ','));
  const pc = (x) => (x == null ? '—' : num(x) + '%');
  const eur = (x) => (x == null ? '—' : Math.round(x).toLocaleString('es-ES') + ' €');
  const thousands = (n) => (n == null ? '—' : Math.round(n).toLocaleString('es-ES'));

  let doc, view, full, paths = {}, labels = [], mode = 'first', gl = null, glBox = null;

  fetch(box.dataset.src).then((r) => r.json()).then((d) => { doc = d; init(); })
    .catch(() => { box.hidden = true; });

  const ringPath = (r) => 'M' + r[0] + ' ' + r[1] + 'l' + r.slice(2).join(' ');
  const districtName = (d) => (doc.d.districts || {})[d];

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
      path.setAttribute('d', rings.map((r) => ringPath(r) + 'z').join(''));
      path.setAttribute('fill-rule', 'evenodd');
      path.dataset.k = key;
      paths[key] = path;
      frag.appendChild(path);
    }
    svg.appendChild(frag);

    // Limits i noms dels districtes, per sobre de les seccions i sense
    // capturar el ratoli (el hover ha de seguir anant a la seccio).
    if (doc.db && doc.db.length) {
      const g = document.createElementNS(NS, 'g');
      g.setAttribute('class', 'districts');
      const line = document.createElementNS(NS, 'path');
      line.setAttribute('d', doc.db.map(ringPath).join(''));
      g.appendChild(line);
      for (const [d, [x, y]] of Object.entries(doc.dl || {})) {
        const t = document.createElementNS(NS, 'text');
        t.setAttribute('x', x);
        t.setAttribute('y', y);
        t.textContent = districtName(d) || d;
        labels.push(t);
        g.appendChild(t);
      }
      svg.appendChild(g);
    }
    setView();
    paint();
    wire();
    if (cityBtn) cityBtn.onclick = cityMap;
  }

  function setView() {
    svg.setAttribute('viewBox', `${view.x} ${view.y} ${view.w} ${view.h}`);
    // La lletra de les etiquetes es manté de mida constant en pantalla.
    const r = svg.getBoundingClientRect();
    const k = Math.max(view.w / (r.width || 1), view.h / (r.height || 1));
    for (const t of labels) t.setAttribute('font-size', (12 * k).toFixed(1));
  }

  // Escala d'un sol to (el de l'accent o el del partit) amb opacitat segons el
  // valor: funciona igual en mode clar i fosc, i el gris queda per "sense dades".
  function range(get) {
    const vals = Object.values(doc.d.sections).map(get).filter((v) => v != null);
    return [Math.min(...vals), Math.max(...vals)];
  }

  // {seccio: [color, opacitat]} segons el que s'hagi triat al desplegable.
  function styles() {
    const S = doc.d.sections, P = doc.d.parties;
    const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#5b8def';
    let get, colour;
    if (mode === 'first') {
      get = (s) => (s.f == null ? null : s.s[s.f]);
      colour = (s) => P[s.f].color;
    } else if (mode === 'renda') {
      get = (s) => s.r;
      colour = () => accent;
    } else if (mode === 'turnout' || mode === 't14') {
      const i = mode === 'turnout' ? 2 : 0;
      get = (s) => s.t[i];
      colour = () => accent;
    } else {
      const i = +mode.slice(1);
      get = (s) => s.s[i];
      colour = () => P[i].color;
    }
    const [lo, hi] = range(get);
    const span = hi - lo || 1;
    const out = {};
    for (const key of Object.keys(doc.s)) {
      const s = S[key];
      const v = s ? get(s) : null;
      out[key] = v == null ? ['#8a8f9c', 0.25] : [colour(s), +(0.22 + 0.78 * (v - lo) / span).toFixed(2)];
    }
    return { out, lo, hi, hue: mode === 'first' ? null : colour(Object.values(S)[0] || {}) };
  }

  function paint() {
    const { out, lo, hi, hue } = styles();
    for (const [key, path] of Object.entries(paths)) {
      path.setAttribute('fill', out[key][0]);
      path.setAttribute('fill-opacity', out[key][1]);
    }
    if (gl && gl.getSource('sec')) gl.getSource('sec').setData(sectionsGeo(out));
    drawLegend(lo, hi, hue);
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

  function show(key) {
    const s = doc.d.sections[key];
    const [d, sec] = key.split('-');
    for (const p of svg.querySelectorAll('path.on')) p.classList.remove('on');
    const path = paths[key];
    if (path) { path.classList.add('on'); path.parentNode.insertBefore(path, svg.querySelector('g.districts')); }
    if (gl) gl.setFilter('sec-on', ['==', ['get', 'k'], key]);
    const dname = districtName(d);
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
      if (e.pointerType === 'mouse' && e.target.dataset.k) show(e.target.dataset.k);
    });
    svg.addEventListener('pointerdown', (e) => {
      drag = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y }; moved = false;
      svg.classList.add('drag');
    });
    const end = (e) => {
      if (drag && !moved && e.target.dataset && e.target.dataset.k) show(e.target.dataset.k);
      drag = null; svg.classList.remove('drag');
    };
    svg.addEventListener('pointerup', end);
    svg.addEventListener('pointerleave', () => { drag = null; svg.classList.remove('drag'); });
    svg.addEventListener('wheel', (e) => {
      e.preventDefault();
      zoom(e.deltaY < 0 ? 1.25 : 0.8, e);
    }, { passive: false });
    for (const b of box.querySelectorAll('.secmap-zoom button')) {
      b.onclick = () => {
        if (gl) return +b.dataset.z ? gl.zoomTo(gl.getZoom() + (b.dataset.z > 1 ? 1 : -1)) : gl.fitBounds(glBox, { padding: 20 });
        return +b.dataset.z ? zoom(+b.dataset.z) : (view = { ...full }, setView());
      };
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

  /* ------------------------------------------------- mapa de la ciutat */

  // Desfa la quantitzacio de geo/seccions.py: de la graella a graus.
  function toLonLat() {
    const [lon0, lat0, lon1, lat1] = doc.box;
    const kx = Math.cos(((lat0 + lat1) / 2) * Math.PI / 180);
    const step = Math.max((lon1 - lon0) * kx, lat1 - lat0) / doc.grid;
    return (r) => {
      const out = [];
      let x = 0, y = 0;
      for (let i = 0; i < r.length; i += 2) {
        x += r[i]; y += r[i + 1];
        out.push([+(lon0 + x * step / kx).toFixed(6), +(lat1 - y * step).toFixed(6)]);
      }
      return out;
    };
  }

  function sectionsGeo(out) {
    const conv = toLonLat();
    return {
      type: 'FeatureCollection',
      features: Object.entries(doc.s).map(([key, rings]) => ({
        type: 'Feature',
        properties: { k: key, c: out[key][0], o: out[key][1] },
        geometry: { type: 'Polygon', coordinates: rings.map((r) => { const p = conv(r); p.push(p[0]); return p; }) },
      })),
    };
  }

  function load(tag, attrs) {
    return new Promise((ok, ko) => {
      const el = document.createElement(tag);
      Object.assign(el, attrs, { onload: ok, onerror: ko });
      document.head.appendChild(el);
    });
  }

  async function cityMap() {
    cityBtn.disabled = true;
    cityBtn.textContent = T.loading;
    try {
      if (!window.maplibregl) {
        await Promise.all([
          load('link', { rel: 'stylesheet', href: MAPLIBRE + '.css', crossOrigin: 'anonymous' }),
          load('script', { src: MAPLIBRE + '.js', crossOrigin: 'anonymous' }),
        ]);
      }
    } catch (e) {
      cityBtn.textContent = T.failed;
      return;
    }
    const div = document.createElement('div');
    div.id = 'secmap-gl';
    svg.style.display = 'none';
    svg.parentNode.insertBefore(div, svg);
    const [lon0, lat0, lon1, lat1] = doc.box;
    glBox = [[lon0, lat0], [lon1, lat1]];
    gl = new maplibregl.Map({
      container: div, style: STYLE, bounds: glBox,
      fitBoundsOptions: { padding: 20 }, attributionControl: { compact: true },
      cooperativeGestures: false,
    });
    gl.on('load', () => {
      const { out } = styles();
      const conv = toLonLat();
      gl.addSource('sec', { type: 'geojson', data: sectionsGeo(out) });
      gl.addLayer({ id: 'sec-fill', type: 'fill', source: 'sec',
        paint: { 'fill-color': ['get', 'c'], 'fill-opacity': ['*', 0.75, ['get', 'o']] } });
      gl.addLayer({ id: 'sec-line', type: 'line', source: 'sec',
        paint: { 'line-color': '#ffffff', 'line-width': 0.5, 'line-opacity': 0.7 } });
      gl.addLayer({ id: 'sec-on', type: 'line', source: 'sec', filter: ['==', ['get', 'k'], ''],
        paint: { 'line-color': '#111111', 'line-width': 2.5 } });
      if (doc.db && doc.db.length) {
        gl.addSource('dist', { type: 'geojson', data: {
          type: 'Feature', properties: {},
          geometry: { type: 'MultiLineString', coordinates: doc.db.map(conv) } } });
        gl.addLayer({ id: 'dist-line', type: 'line', source: 'dist',
          paint: { 'line-color': '#1d2433', 'line-width': 2.2 } });
        gl.addSource('dist-label', { type: 'geojson', data: {
          type: 'FeatureCollection',
          features: Object.entries(doc.dl || {}).map(([d, xy]) => ({
            type: 'Feature', properties: { n: districtName(d) || d },
            geometry: { type: 'Point', coordinates: conv(xy)[0] } })) } });
        gl.addLayer({ id: 'dist-name', type: 'symbol', source: 'dist-label',
          layout: { 'text-field': ['get', 'n'], 'text-font': ['Noto Sans Bold'], 'text-size': 13,
            'text-allow-overlap': false },
          paint: { 'text-color': '#1d2433', 'text-halo-color': '#ffffff', 'text-halo-width': 1.6 } });
      }
      gl.on('mousemove', 'sec-fill', (e) => { gl.getCanvas().style.cursor = 'pointer'; show(e.features[0].properties.k); });
      gl.on('mouseleave', 'sec-fill', () => { gl.getCanvas().style.cursor = ''; });
      gl.on('click', 'sec-fill', (e) => show(e.features[0].properties.k));
      cityBtn.textContent = T.back;
      cityBtn.disabled = false;
      cityBtn.onclick = simpleMap;
    });
  }

  function simpleMap() {
    gl.remove();
    gl = null;
    document.getElementById('secmap-gl').remove();
    svg.style.display = '';
    setView();
    cityBtn.textContent = cityBtn.dataset.label;
    cityBtn.onclick = cityMap;
  }
})();
