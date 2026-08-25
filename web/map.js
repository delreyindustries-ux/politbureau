/* Polit Bureau — mapa electoral i repartiment d'escons.
 *
 * El mapa es dibuixa sobre <canvas> i no amb SVG: Espanya te 8.213 municipis i
 * vuit mil nodes al DOM fan que qualsevol desplacament vagi a rastres.
 * Per saber sobre quin territori hi ha el cursor es fa servir un segon canvas
 * ocult on cada poligon es pinta amb un color = el seu index. Llegir un pixel
 * d'aquest canvas dona el territori exacte sense calcular cap interseccio.
 */

const $ = (s) => document.querySelector(s);

/* En castella i catala el separador decimal es la coma. Escriure "32.2%" a una
   web espanyola es un anglicisme que canta molt. */
const num = (x, d = 1) => (x == null ? '—' : x.toFixed(d).replace('.', ','));
const pc = (x, d = 1) => (x == null ? '—' : num(x, d) + '%');
const state = {
  election: null, layer: 'projection', level: 'municipality',
  colourBy: -1,                 // -1 = guanyador; si no, index dins state.parties
  topo: null, shapes: [], areas: {}, parties: [], palette: {},
  bounds: null, view: { k: 1, x: 0, y: 0 }, hover: -1, elections: [],
};

// Els noms dels nivells van en l'idioma de la pagina: la mateixa aplicacio
// serveix /es/mapa/ i /ca/mapa/.
const LEVEL_LABELS = {
  es: { municipality: 'Municipios', province: 'Provincias', region: 'Comunidades' },
  ca: { municipality: 'Municipis', province: 'Províncies', region: 'Comunitats' },
};
const ORDER = ['municipality', 'province', 'region'];

/* ------------------------------------------------------------ TopoJSON */

function decodeArc(topo, i) {
  const arc = topo.arcs[i], t = topo.transform;
  const out = [];
  let x = 0, y = 0;
  for (const p of arc) {
    if (t) { x += p[0]; y += p[1]; out.push([x * t.scale[0] + t.translate[0], y * t.scale[1] + t.translate[1]]); }
    else out.push([p[0], p[1]]);
  }
  return out;
}

function ringOf(topo, idxs) {
  const pts = [];
  for (const i of idxs) {
    // Un index negatiu vol dir el mateix arc recorregut al reves.
    let a = i < 0 ? decodeArc(topo, ~i).slice().reverse() : decodeArc(topo, i);
    if (pts.length) a = a.slice(1);          // el primer punt ja hi es
    for (const p of a) pts.push(p);
  }
  return pts;
}

function shapesFromTopo(topo, objectName) {
  const obj = topo.objects[objectName];
  if (!obj) return [];
  return (obj.geometries || []).map((g) => {
    const polys = g.type === 'Polygon' ? [g.arcs] : (g.type === 'MultiPolygon' ? g.arcs : []);
    return {
      id: g.id, name: (g.properties || {}).name || g.id,
      rings: polys.map((poly) => poly.map((r) => ringOf(topo, r))),
    };
  }).filter((s) => s.id && s.rings.length);
}

/* Italia i Franca es serveixen com a GeoJSON pla: les coordenades ja venen
   desplegades i tenen exactament la forma que espera la resta del dibuix. */
function shapesFromGeo(collection) {
  return (collection.features || []).map((f) => {
    const g = f.geometry || {};
    const polys = g.type === 'Polygon' ? [g.coordinates]
      : (g.type === 'MultiPolygon' ? g.coordinates : []);
    const p = f.properties || {};
    return { id: p.id, name: p.name || p.id, rings: polys };
  }).filter((s) => s.id && s.rings.length);
}

/* --------------------------------------------------------- projeccio */

function extent(shapes, wrap) {
  let minLon = 180, maxLon = -180, minLat = 90, maxLat = -90;
  for (const s of shapes) for (const poly of s.rings) for (const ring of poly) for (const p of ring) {
    const lon = wrap && p[0] > 0 ? p[0] - 360 : p[0], lat = p[1];
    if (lon < minLon) minLon = lon; if (lon > maxLon) maxLon = lon;
    if (lat < minLat) minLat = lat; if (lat > maxLat) maxLat = lat;
  }
  return { minLon, maxLon, minLat, maxLat };
}

function project(shapes) {
  // Equirectangular amb el parallel estandard al centre del pais: per a un sol
  // estat es prou fidel i no estira el nord com faria la Mercator.
  let b = extent(shapes, false);

  // Les Aleutianes creuen l'antimeridia: part d'Alaska cau a +179 i la resta del
  // pais a -125, cosa que fa que el rang de longituds sigui de gairebe 360 graus
  // i el mapa surti diminut. Passant les longituds positives a negatives el pais
  // torna a ser continu.
  const wrap = (b.maxLon - b.minLon) > 180;
  if (wrap) b = extent(shapes, true);

  const cos = Math.cos((b.minLat + b.maxLat) / 2 * Math.PI / 180);
  for (const s of shapes) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    s.flat = s.rings.map((poly) => poly.map((ring) => {
      const a = new Float32Array(ring.length * 2);
      for (let i = 0; i < ring.length; i++) {
        const lon = wrap && ring[i][0] > 0 ? ring[i][0] - 360 : ring[i][0];
        const px = lon * cos, py = -ring[i][1];
        a[i * 2] = px; a[i * 2 + 1] = py;
        if (px < x0) x0 = px; if (px > x1) x1 = px;
        if (py < y0) y0 = py; if (py > y1) y1 = py;
      }
      return a;
    }));
    s.box = [x0, y0, x1, y1];      // per descartar el que queda fora de pantalla
    s.rings = null;                // ja no fa falta: nomes ocuparia memoria
  }
  return { x0: b.minLon * cos, x1: b.maxLon * cos, y0: -b.maxLat, y1: -b.minLat };
}

function fit(bounds, w, h) {
  // Si el canvas encara no te mida (pestanya oculta, pintat inicial), l'escala
  // sortiria negativa i el mapa quedaria del reves per sempre. Val mes no
  // enquadrar i tornar-ho a provar quan el ResizeObserver digui la mida real.
  const pad = 24;
  if (!bounds || w < 2 * pad + 10 || h < 2 * pad + 10) return null;
  const dx = bounds.x1 - bounds.x0, dy = bounds.y1 - bounds.y0;
  if (!(dx > 0) || !(dy > 0)) return null;
  const k = Math.min((w - pad * 2) / dx, (h - pad * 2) / dy);
  return { k, x: (w - (bounds.x1 + bounds.x0) * k) / 2, y: (h - (bounds.y1 + bounds.y0) * k) / 2 };
}

/* ----------------------------------------------------------- dibuix */

const cv = $('#map');
const ctx = cv.getContext('2d');
const pick = document.createElement('canvas');
const pctx = pick.getContext('2d', { willReadFrequently: true });

let fittedAt = null;      // mida del canvas quan es va enquadrar per ultim cop

function resize() {
  const r = cv.getBoundingClientRect(), dpr = Math.min(devicePixelRatio || 1, 2);
  if (r.width < 2 || r.height < 2) return;
  cv.width = Math.round(r.width * dpr); cv.height = Math.round(r.height * dpr);
  pick.width = Math.round(r.width); pick.height = Math.round(r.height);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  // Tornar a enquadrar si el mapa mai no ho ha estat o si la finestra ha canviat
  // de mida de debo. Comprovar nomes que l'escala sigui positiva no n'hi ha
  // prou: si el primer enquadrament es va fer amb el canvas a mig compondre,
  // l'escala es valida pero absurda i el mapa es queda diminut per sempre.
  // Si l'usuari ja ha mogut el mapa, no se li toca.
  const grew = !fittedAt || Math.abs(r.width - fittedAt[0]) > fittedAt[0] * 0.2
                         || Math.abs(r.height - fittedAt[1]) > fittedAt[1] * 0.2;
  if (state.bounds && (!(state.view && state.view.k > 0) || (grew && !state.moved))) {
    const view = fit(state.bounds, r.width, r.height);
    if (view) { state.view = view; fittedAt = [r.width, r.height]; }
  }
  paint();
}

/* Tres vies per assegurar que el canvas acaba amb la mida bona.
   El ResizeObserver sol no n'hi ha prou: en una pestanya de fons el navegador
   suspen els passos de renderitzat i la notificacio del canvi de mida no
   arriba mai, de manera que el mapa es queda dibuixat a la mida que tenia
   quan encara no havia acabat de compondre's -- o sigui, en blanc. */
const sizeWatcher = new ResizeObserver(resize);
sizeWatcher.observe(cv);
addEventListener('load', resize);
document.addEventListener('visibilitychange', () => { if (!document.hidden) resize(); });

function tracePath(c, s, v) {
  c.beginPath();
  for (const poly of s.flat) for (const ring of poly) {
    c.moveTo(ring[0] * v.k + v.x, ring[1] * v.k + v.y);
    for (let i = 1; i < ring.length; i++) c.lineTo(ring[i * 2] * v.k + v.x, ring[i * 2 + 1] * v.k + v.y);
    c.closePath();
  }
}

function rgba(hex, alpha) {
  const n = parseInt((hex || '#888888').slice(1), 16);
  return `rgba(${n >> 16 & 255},${n >> 8 & 255},${n & 255},${alpha.toFixed(3)})`;
}

function colourOf(row) {
  if (!row) return '#1c202b';
  if (state.colourBy < 0) {
    // Mode guanyador: el marge sobre el segon gradua la intensitat, perque un
    // municipi guanyat per mig punt no sembli igual de rotund que un de guanyat
    // per trenta.
    const p = state.parties[row[0]];
    return rgba(p ? p.color : '#888', Math.max(0.30, Math.min(1, 0.34 + row[1] / 26)));
  }
  // Mode un sol partit: la intensitat es directament el seu percentatge de vot.
  const share = row[2 + state.colourBy];
  const p = state.parties[state.colourBy];
  if (!share) return '#171a22';
  return rgba(p ? p.color : '#888', Math.max(0.10, Math.min(1, share / 45)));
}

/* Els colors es calculen un cop i es guarden, no a cada fotograma.
   Amb 35.000 comunes, construir dues cadenes "rgba(...)" per forma i per
   repintada costava mes de mig segon; precalculant-les, arrossegar el mapa
   torna a ser fluid. Nomes cal refer-ho quan canvia la capa o el partit. */
function cacheFills() {
  state.fills = state.shapes.map((s) => colourOf(state.areas[s.id]));
  state.picks = state.shapes.map((_, i) => `rgb(${i >> 16 & 255},${i >> 8 & 255},${i & 255})`);
}

/* `withPick` a fals mentre s'arrossega el mapa: el canvas d'identificacio
   nomes cal per saber sobre que hi ha el cursor, i mentre l'usuari arrossega
   no s'esta assenyalant res. Pintar-ne un de sol en comptes de dos redueix la
   feina a la meitat, que amb 35.000 comunes franceses es nota molt. */
function paint(withPick = true) {
  const w = cv.clientWidth, h = cv.clientHeight, v = state.view;
  ctx.clearRect(0, 0, w, h);
  if (withPick) pctx.clearRect(0, 0, w, h);
  else state.pickDirty = true;
  if (!(v && v.k > 0)) return;
  if (!state.fills || state.fills.length !== state.shapes.length) cacheFills();
  const thin = state.shapes.length > 2000;
  ctx.lineWidth = thin ? 0.25 : 0.6;
  ctx.strokeStyle = '#0d0f14';

  // Amb 35.000 comunes franceses, dibuixar-ho tot cada fotograma fa el mapa
  // inservible. Dues drecetes que NO canvien el que es veu:
  //  - el que cau fora de la pantalla no es dibuixa;
  //  - el que ocupa menys d'un pixel es pinta com un rectangle d'un pixel, que
  //    es exactament el mateix resultat visual i costa una fraccio del temps.
  const w2 = cv.clientWidth, h2 = cv.clientHeight;
  state.shapes.forEach((s, i) => {
    const b = s.box;
    const bx0 = b[0] * v.k + v.x, by0 = b[1] * v.k + v.y;
    const bx1 = b[2] * v.k + v.x, by1 = b[3] * v.k + v.y;
    if (bx1 < 0 || by1 < 0 || bx0 > w2 || by0 > h2) return;

    const fill = state.fills[i], pickCol = state.picks[i];
    const bw = bx1 - bx0, bh = by1 - by0;
    // Per sota d'uns dos pixels el contorn del poligon ja no es distingeix:
    // dibuixar-lo com un rectangle dona el mateix resultat a la vista i costa
    // una fraccio del temps.
    if (bw < 2 && bh < 2) {
      const side = Math.max(bw, bh, 1.1);
      ctx.fillStyle = fill; ctx.fillRect(bx0, by0, side, side);
      if (withPick) { pctx.fillStyle = pickCol; pctx.fillRect(bx0, by0, side, side); }
      return;
    }
    tracePath(ctx, s, v);
    ctx.fillStyle = fill;
    ctx.fill();
    if (!thin || v.k > 900) ctx.stroke();

    if (withPick) {
      tracePath(pctx, s, v);                     // canvas ocult d'identificacio
      pctx.fillStyle = pickCol;
      pctx.fill();
    }
  });

  if (state.hover >= 0 && state.shapes[state.hover]) {
    tracePath(ctx, state.shapes[state.hover], v);
    ctx.lineWidth = 1.6; ctx.strokeStyle = '#fff'; ctx.stroke();
  }
}

// draw() nomes programa el pintat per al seguent fotograma, de manera que
// arrossegar el mapa no encadeni vuit mil poligons per cada esdeveniment del
// ratoli. La feina de debo es a paint(), que es pot cridar directament.
let queued = false, settle = null;
function draw(interacting = false) {
  if (!queued) {
    queued = true;
    requestAnimationFrame(() => { queued = false; paint(!interacting); });
  }
  if (interacting) {
    // Quan el moviment s'atura, es refa el canvas d'identificacio perque el
    // cursor torni a saber sobre quin territori es.
    clearTimeout(settle);
    settle = setTimeout(() => { if (state.pickDirty) { state.pickDirty = false; paint(true); } }, 120);
  }
}

function at(ev) {
  if (state.pickDirty) { state.pickDirty = false; paint(true); }
  const r = cv.getBoundingClientRect();
  const x = Math.round(ev.clientX - r.left), y = Math.round(ev.clientY - r.top);
  if (x < 0 || y < 0 || x >= pick.width || y >= pick.height) return -1;
  const d = pctx.getImageData(x, y, 1, 1).data;
  if (!d[3]) return -1;
  const i = (d[0] << 16) | (d[1] << 8) | d[2];
  return i < state.shapes.length ? i : -1;
}

/* ------------------------------------------------------- interaccio */

let drag = null;
cv.addEventListener('mousedown', (e) => { drag = { x: e.clientX, y: e.clientY, v: { ...state.view }, moved: 0 }; cv.classList.add('dragging'); });
addEventListener('mouseup', () => { cv.classList.remove('dragging'); setTimeout(() => { drag = null; }, 0); });
addEventListener('mousemove', (e) => {
  if (!drag) return;
  drag.moved += Math.abs(e.movementX) + Math.abs(e.movementY);
  if (drag.moved > 4) state.moved = true;
  state.view.x = drag.v.x + (e.clientX - drag.x);
  state.view.y = drag.v.y + (e.clientY - drag.y);
  draw(true);
});
cv.addEventListener('mousemove', (e) => {
  if (drag) return;
  const i = at(e);
  if (i !== state.hover) { state.hover = i; draw(); }
  const tip = $('#tooltip');
  if (i < 0) { tip.hidden = true; return; }
  tip.innerHTML = tooltipHTML(state.shapes[i]);
  tip.hidden = false;
  const r = cv.getBoundingClientRect();
  tip.style.left = Math.min(e.clientX - r.left + 14, r.width - 250) + 'px';
  tip.style.top = Math.min(e.clientY - r.top + 14, r.height - 230) + 'px';
});
cv.addEventListener('mouseleave', () => { $('#tooltip').hidden = true; state.hover = -1; draw(); });
cv.addEventListener('wheel', (e) => {
  e.preventDefault();
  const r = cv.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
  const f = Math.exp(-e.deltaY * 0.0016), v = state.view;
  v.x = mx - (mx - v.x) * f; v.y = my - (my - v.y) * f; v.k *= f;
  state.moved = true;
  draw(true);
}, { passive: false });
cv.addEventListener('click', (e) => {
  if (drag && drag.moved > 4) return;
  const i = at(e);
  if (i < 0) return;
  const url = territoryUrl(state.level, state.shapes[i].id);
  if (url) location.href = ROOT.replace(/\/$/, '') + url;
});
addEventListener('resize', resize);

/* El tooltip mostra la intencio de vot SENCERA del territori, no nomes qui
   guanya: el guanyador sol amaga si va per mig punt o per trenta, i quin partit
   li ve al darrere. */
function tooltipHTML(shape) {
  const row = state.areas[shape.id];
  if (!row) return `<b>${shape.name}</b><span style="color:#98a0b5">sense dades</span>`;
  const ranked = state.parties
    .map((p, i) => ({ ...p, share: row[2 + i] }))
    .filter((p) => p.share > 0.2)
    .sort((a, b) => b.share - a.share)
    .slice(0, 9);
  const max = ranked.length ? ranked[0].share : 1;
  return `<b>${shape.name}</b>
    <div class="tiprows">${ranked.map((p, i) => `
      <div class="tiprow${i === 0 ? ' first' : ''}">
        <span class="sw" style="background:${p.color}"></span>
        <span class="nm">${p.name}</span>
        <span class="track"><i style="width:${p.share / max * 100}%;background:${p.color}"></i></span>
        <span class="pc">${num(p.share)}</span>
      </div>`).join('')}</div>
    <div class="tipfoot">marge del primer: ${num(row[1], 2)} punts</div>`;
}

/* -------------------------------------------------------------- dades */

/* Contra fitxers estatics, no contra una API. Les respostes son les mateixes
   perque s'han generat amb el mateix codi del servidor. */
const ROOT = document.querySelector('#mapapp').dataset.root;
const LANG = document.querySelector('#mapapp').dataset.lang;
const EID = 'es-general';

function api(u) {
  let file;
  if (u === '/api/geoinfo') file = 'data/geoinfo.json';
  else if (u === '/api/elections') file = 'data/elections.json';
  else if (u.startsWith('/geo/')) file = 'assets/es.json';
  else if (u.startsWith('/api/map/')) {
    const p = new URLSearchParams(u.split('?')[1]);
    file = `data/map-${p.get('level')}-${p.get('layer')}.json`;
  } else {
    const name = u.split('/api/')[1].split('/')[0].split('?')[0];
    file = `data/${name}.json`;
  }
  return fetch(ROOT + file).then((r) => r.json());
}

/* Clicar un territori porta a la seva pagina, que es la que Google indexa i la
   que la gent pot enllacar. L'index del cercador ja porta totes les adreces. */
let urlIndex = null;
function territoryUrl(level, code) {
  if (!urlIndex) return null;
  return urlIndex[level + '/' + code] || null;
}
fetch(ROOT + 'assets/search.json').then((r) => r.json()).then((rows) => {
  urlIndex = {};
  for (const r of rows) urlIndex[r[2] + '/' + r[3]] = LANG === 'ca' ? r[5] : r[4];
});

async function boot() {
  [state.geoinfo, state.elections] = await Promise.all([
    api('/api/geoinfo'), api('/api/elections'),
  ]);
  const first = state.elections.find((e) => e.has_map) || state.elections[0];
  if (first) await selectElection(first.id);
}

async function selectElection(id) {
  state.election = state.elections.find((e) => e.id === id);
  const country = state.election.map_country;

  const labels = LEVEL_LABELS[LANG] || LEVEL_LABELS.es;
  const lv = $('#level');
  lv.innerHTML = ORDER
    .map((k, i) => `<button data-level="${k}" class="${i === 0 ? 'on' : ''}">${labels[k]}</button>`).join('');
  lv.querySelectorAll('button').forEach((b) => {
    b.onclick = () => {
      lv.querySelectorAll('button').forEach((x) => x.classList.remove('on'));
      b.classList.add('on'); state.level = b.dataset.level; loadMap();
    };
  });
  state.level = ORDER[0];
  state.colourBy = -1;
  state.view = { k: 0, x: 0, y: 0 };      // reenquadra en canviar de pais

  $('#freshness').innerHTML =
    (LANG === 'ca'
      ? `darrer treball de camp: ${state.election.last_fieldwork}<br>${state.election.polls} enquestes · ${state.election.pollsters} cases`
      : `último trabajo de campo: ${state.election.last_fieldwork}<br>${state.election.polls} encuestas · ${state.election.pollsters} institutos`);

  await Promise.all([loadGeometry(country), loadSummary(id), loadTrend(id), loadSeats(id)]);
  await loadMap();
}

const geoCache = {};

async function shapesFor(country, level) {
  const info = (state.geoinfo || {})[country];
  if (!info) return [];
  if (info.format === 'topojson') {
    if (!geoCache[country]) geoCache[country] = await api(`/geo/${country.toLowerCase()}.json`);
    return shapesFromTopo(geoCache[country], info.levels[level]);
  }
  const key = `${country}/${level}`;
  if (!geoCache[key]) geoCache[key] = await api(`/geo/${country.toLowerCase()}/${level}.json`);
  return shapesFromGeo(geoCache[key]);
}

async function loadGeometry(country) {
  $('#loading').hidden = false;
  if (!country) {
    // Netejar-ho tot: si no, en passar dels EUA a Italia la llegenda i el
    // cartell es quedarien mostrant les dades del pais anterior.
    state.shapes = []; state.topo = null; state.areas = {}; state.parties = [];
    state.bounds = null; state.hover = -1;
    $('#legend').innerHTML = ''; $('#mapnote').innerHTML = ''; $('#colourby').innerHTML = '';
    paint();
    $('#loading').textContent = "Aquesta elecció no té mapa territorial: França i Itàlia es segueixen només a escala estatal. El resum, l'evolució i els escons són al panell de la dreta.";
    return;
  }
  state.topo = country;         // ara la geometria es carrega per nivell
}

async function loadMap() {
  if (!state.topo) return;
  const country = state.election.map_country;
  $('#loading').hidden = false;
  $('#loading').textContent = geoCache[`${country}/${state.level}`] || geoCache[country]
    ? 'calculant…'
    : "baixant la geometria… (els mapes municipals d'Itàlia i França pesen molt)";
  state.shapes = await shapesFor(country, state.level);
  state.bounds = project(state.shapes);
  state.moved = false;
  fittedAt = null;
  state.view = fit(state.bounds, cv.clientWidth, cv.clientHeight) || state.view;

  const d = await api(`/api/map/${state.election.id}?level=${state.level}&layer=${state.layer}`);
  state.areas = d.areas;
  state.parties = d.parties;
  state.palette = d.palette;
  state.fills = null;                    // colors nous: cal recalcular-los
  if (state.colourBy >= state.parties.length) state.colourBy = -1;

  const sel = $('#colourby');
  sel.innerHTML = (LANG === 'ca' ? '<option value="-1">Acolorir: partit guanyador</option>' : '<option value="-1">Colorear: partido ganador</option>') +
    state.parties.map((p, i) => `<option value="${i}">${LANG === 'ca' ? 'Acolorir: vot a' : 'Colorear: voto a'} ${p.name}</option>`).join('');
  sel.value = String(state.colourBy);
  sel.onchange = () => { state.colourBy = +sel.value; cacheFills(); renderLegend(); paint(); };

  renderLegend();
  const noParliament = { XX: `A Itàlia aquest mapa <b>no decideix res</b>: la Camera es
      reparteix per circumscripcions plurinominals i districtes uninominals, no per comuni.
      Serveix per veure on és fort cada partit.` }[country] || '';

  $('#mapnote').innerHTML = (state.layer === 'projection'
    ? (LANG === 'ca'
        ? `<b>Estimació, no un resultat.</b> No hi ha enquestes municipals: aquest mapa
           parteix del resultat real de 2023 i hi aplica el desplaçament de vot que
           marquen les enquestes d'avui. És un model, no una mesura.`
        : `<b>Estimación, no un resultado.</b> No hay encuestas municipales: este mapa
           parte del resultado real de 2023 y le aplica el desplazamiento de voto que
           marcan las encuestas de hoy. Es un modelo, no una medición.`)
    : (LANG === 'ca'
        ? `<b>Dada real.</b> Escrutini oficial de les generals del 2023, Ministeri de
           l'Interior. ${d.n.toLocaleString('es')} territoris.`
        : `<b>Dato real.</b> Escrutinio oficial de las generales de 2023, Ministerio del
           Interior. ${d.n.toLocaleString('es')} territorios.`));

  $('#loading').hidden = true;
  resize();          // el canvas pot no tenir encara la mida definitiva
}

function renderLegend() {
  const leg = $('#legend');
  if (!state.parties.length) { leg.innerHTML = ''; return; }
  if (state.colourBy < 0) {
    const counts = {};
    for (const k in state.areas) {
      const idx = state.areas[k][0];
      if (idx >= 0) counts[idx] = (counts[idx] || 0) + 1;
    }
    leg.innerHTML = (LANG === 'ca' ? '<div class="legtitle">Territoris guanyats</div>' : '<div class="legtitle">Territorios ganados</div>') +
      Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 12).map(([i, n]) => {
        const p = state.parties[i] || { name: '?', color: '#888' };
        return `<div class="row"><span class="sw" style="background:${p.color}"></span>${p.name}<span class="n">${n}</span></div>`;
      }).join('');
  } else {
    // En mode d'un sol partit la llegenda ha de ser una escala, no un recompte.
    const p = state.parties[state.colourBy];
    const steps = [5, 15, 25, 35, 45];
    leg.innerHTML = `<div class="legtitle">${LANG === 'ca' ? 'Vot a' : 'Voto a'} ${p.name}</div>` +
      steps.map((v) => `<div class="row"><span class="sw" style="background:${rgba(p.color, Math.max(0.10, Math.min(1, v / 45)))}"></span>${v}%</div>`).join('');
  }
}

function sidePanel() {
  if ($('#sum-bars')) return;
  $('#side').innerHTML = `
    <div class="pane">
      <h2 id="sum-title">—</h2>
      <div id="sum-bars"></div>
      <div id="tab-seats"></div>
      <h3>${LANG === 'ca' ? 'Evolució' : 'Evolución'}</h3>
      <div id="trend"></div>
      <p class="fine" id="sum-method"></p>
    </div>`;
}

async function loadSummary(id) {
  sidePanel();
  const d = await api(`/api/summary/${id}`);
  $('#sum-title').textContent = LANG === 'ca'
    ? 'Estimació de vot · Congrés' : 'Estimación de voto · Congreso';
  const max = Math.max(...d.parties.map((p) => p.share), 1);
  // Quantes enquestes sostenen cada xifra. No totes les cases pregunten pels
  // partits petits: Aliança.cat surt a tres enquestes i Podem a quaranta, i una
  // mitjana de tres no mereix la mateixa confiança que una de quaranta.
  const maxPolls = Math.max(...d.parties.map((p) => p.n_polls || 0), 1);
  $('#sum-bars').innerHTML = d.parties.filter((p) => p.share >= 0.4).map((p) => `
    <div class="bar">
      <div class="top">
        <span class="nm" style="color:${p.color}">${p.name}</span>
        ${p.n_polls < maxPolls * 0.5
          ? `<span class="thin" title="Només ${p.n_polls} de les ${maxPolls} enquestes recents pregunten per aquest partit">${p.n_polls} enq.</span>`
          : ''}
        <span class="pc">${pc(p.share)}</span>
      </div>
      <div class="track">
        <div class="fill" style="width:${p.share / max * 100}%;background:${p.color}"></div>
        <div class="rng" style="left:${p.lo / max * 100}%;width:${(p.hi - p.lo) / max * 100}%"></div>
      </div>
    </div>`).join('');
  $('#sum-method').innerHTML =
    `Mitjana ponderada de les enquestes dels darrers 90 dies. El pes d'una enquesta cau a la
     meitat cada 14 dies i creix amb l'arrel quadrada de la mostra. La banda clara de cada barra
     és la <b>dispersió entre cases enquestadores</b>, no un interval de confiança.
     No s'aplica cap correcció de biaix per casa.
     L'etiqueta «<span class="thin">n enq.</span>» avisa que aquell partit surt en
     poques enquestes: no totes les cases pregunten pels partits petits.`;
}

async function loadTrend(id) {
  const d = await api(`/api/trend/${id}`);
  const W = 360, H = 150, P = 22;
  const pts = d.series.flatMap((s) => s.points);
  if (!pts.length) { $('#trend').innerHTML = '<p class="fine">sense sèrie</p>'; return; }
  const xs = pts.map((p) => +new Date(p[0])), ys = pts.map((p) => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y1 = Math.max(...ys) * 1.1;
  const X = (t) => P + (+new Date(t) - x0) / (x1 - x0 || 1) * (W - P - 6);
  const Y = (v) => H - P - v / y1 * (H - P - 8);
  const paths = d.series.map((s) => {
    const dd = s.points.map((p, i) => `${i ? 'L' : 'M'}${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join('');
    return `<path d="${dd}" fill="none" stroke="${s.color}" stroke-width="1.6" opacity=".9"/>`;
  }).join('');
  const grid = [0, 10, 20, 30, 40].filter((v) => v <= y1).map((v) =>
    `<line x1="${P}" x2="${W - 6}" y1="${Y(v)}" y2="${Y(v)}" stroke="#2b3040"/>
     <text x="2" y="${Y(v) + 3}" fill="#666f88" font-size="9">${v}</text>`).join('');
  $('#trend').innerHTML = `<svg class="spark" viewBox="0 0 ${W} ${H}">${grid}${paths}</svg>
    <p class="fine">Mitjana setmanal sense ponderar, dos anys. Cada línia és un partit.</p>`;
}

/* ------------------------------------------------------------ hemicicle */

function seatPositions(total) {
  // Files concentriques, amb mes escons a les de fora perque l'arc es mes llarg.
  const rows = Math.max(1, Math.min(14, Math.min(total, Math.round(Math.sqrt(total / 3.2)))));
  const r0 = 0.46, r1 = 1;
  const radii = [];
  for (let i = 0; i < rows; i++) radii.push(rows === 1 ? r1 : r0 + (r1 - r0) * i / (rows - 1));
  const sum = radii.reduce((a, b) => a + b, 0);
  const counts = radii.map((r) => Math.max(1, Math.floor(total * r / sum)));

  let left = total - counts.reduce((a, b) => a + b, 0);
  for (let i = rows - 1; left > 0; i = (i - 1 + rows) % rows) { counts[i]++; left--; }
  for (let i = 0, over = -left; over > 0; i = (i + 1) % rows) {
    if (counts[i] > 1) { counts[i]--; over--; }
  }

  const pts = [];
  counts.forEach((n, i) => {
    for (let k = 0; k < n; k++) {
      const t = n === 1 ? 0.5 : k / (n - 1);
      pts.push({ ang: Math.PI * (1 - t), r: radii[i] });
    }
  });
  return pts.sort((a, b) => b.ang - a.ang);      // d'esquerra a dreta
}

function hemicycle(groups, total, majority) {
  const seats = groups.reduce((a, g) => a + g.seats, 0);
  if (!seats) return '<p class="fine">sense escons</p>';
  const pts = seatPositions(seats);
  const W = 360, H = 200, cx = W / 2, cy = H - 14, R = 158;
  const dot = Math.max(1.6, Math.min(5, 46 / Math.sqrt(seats)));

  let i = 0;
  const circles = groups.flatMap((g) => Array.from({ length: g.seats }, () => {
    const p = pts[i++];
    if (!p) return '';
    return `<circle cx="${(cx + Math.cos(p.ang) * p.r * R).toFixed(1)}"
      cy="${(cy - Math.sin(p.ang) * p.r * R).toFixed(1)}" r="${dot.toFixed(1)}"
      fill="${g.color}"><title>${g.name}</title></circle>`;
  })).join('');

  // Ratlla de majoria absoluta: es el numero que de veritat decideix si un
  // resultat serveix per governar.
  const line = majority
    ? `<line x1="${cx}" y1="${cy - R * 1.06}" x2="${cx}" y2="${cy - R * 0.40}"
             stroke="#e7eaf3" stroke-width="1" stroke-dasharray="3 3" opacity=".55"/>
       <text x="${cx + 5}" y="${cy - R * 1.06 + 10}" fill="#98a0b5" font-size="10">majoria ${majority}</text>`
    : '';
  return `<svg class="hemi" viewBox="0 0 ${W} ${H}">${circles}${line}
    <text x="${cx}" y="${cy - 4}" text-anchor="middle" fill="#e7eaf3"
          font-size="19" font-weight="600">${total}</text>
    <text x="${cx}" y="${cy + 10}" text-anchor="middle" fill="#666f88" font-size="9">escons</text>
  </svg>`;
}

function seatTable(groups, majority) {
  return `<table><thead><tr><th>Partit</th><th style="text-align:right">Escons</th>
    <th style="text-align:right">% cambra</th></tr></thead><tbody>` +
    [...groups].sort((a, b) => b.seats - a.seats).map((g) => `
      <tr><td><span class="sw" style="background:${g.color}"></span>${g.name}</td>
      <td class="num">${g.seats}</td>
      <td class="num">${pc(g.seats / (majority * 2 - 1) * 100)}</td></tr>`).join('') +
    '</tbody></table>';
}

async function loadSeats(id) {
  sidePanel();
  const el = $('#tab-seats');
  const d = await api(`/api/seats/${id}`);
  if (!d.chamber) {
    el.innerHTML = `<h2>Sense cambra</h2><p class="fine">${d.reason}</p>`;
    return;
  }
  const avis = [];
  if (d.approximate) avis.push(`<div class="warn"><b>Repartiment aproximat.</b>
     El Rosatellum reparteix un 37% dels escons en districtes uninominals i això no es modela.
     El gràfic dona l'ordre de magnitud, no l'escó exacte.</div>`);
  if (d.partial) avis.push(`<div class="warn"><b>Cambra parcial.</b>
     El 2026 se'n renoven ${d.in_play} dels ${d.seats}, i només ${d.allocated} tenen enquestes.
     Els altres escons no es projecten perquè no hi ha dades, no perquè estiguin buits.</div>`);

  el.innerHTML = `<h2>${d.chamber}</h2>
    ${avis.join('')}
    <h3>Estimació d'avui</h3>
    ${hemicycle(d.projection, d.allocated, d.partial ? 0 : d.majority)}
    ${seatTable(d.projection, d.majority)}
    ${d.real.length ? `<h3>Resultat real · ${d.baseline}</h3>
      ${hemicycle(d.real, d.real.reduce((a, g) => a + g.seats, 0), d.majority)}
      ${seatTable(d.real, d.majority)}` : ''}
    <p class="fine" style="margin-top:14px">${d.method === 'dhondt_province'
      ? `Llei d'Hondt aplicada a cadascuna de les 52 circumscripcions amb la seva magnitud real
         i el llindar del 3%. Aplicat als vots reals de ${d.baseline}, aquest mateix càlcul
         reprodueix 348 dels 350 escons.`
      : d.method === 'proportional'
      ? 'Repartiment proporcional estatal amb llindar del 3%.'
      : "Cada estat elegeix un senador: se l'emporta el més votat."}</p>`;
}

/* ---------------------------------------------------------- controls */

$('#layer').querySelectorAll('button').forEach((b) => {
  b.onclick = () => {
    $('#layer').querySelectorAll('button').forEach((x) => x.classList.remove('on'));
    b.classList.add('on'); state.layer = b.dataset.layer; loadMap();
  };
});


resize();
boot();
