/* Cambres (09/11/2026): l'interior de cada parlament, vist des de la
   presidencia com una foto del ple buit, amb la forma real de la sala
   (hemicicle, ferradura o els bancs enfrontats de Westminster). S'encenen els
   llums, apareixen les files i cada seient pren el color del seu partit. Al peu,
   la facana de l'edifici, que es dibuixa sola.

   Cada <figure class="chamber"> porta les dades als atributs:
     data-b  edifici ("es-congreso", "es-senado" o el codi ISO del pais)
     data-g  [{n: nom, c: color, s: escons, p: posicio -3..3 o null}]
     data-m  majoria absoluta · data-t  escons de la cambra · data-l  idioma
   Sense JavaScript hi queda la barra d'escons que porta a dins.

   Les facanes son il·lustracions propies i esquematiques, no plans. */
(function () {
  'use strict';

  const G = 120;          // linia de terra de la facana (la caixa fa 360 x 120)
  let S = [];             // peces de la facana que s'estan dibuixant
  let K = 0;              // ordre de dibuix: retarda cada peca una mica mes

  const f = (n) => Math.round(n * 10) / 10;
  function P(d, cls) {
    S.push(`<path class="${cls || 'ln'}" d="${d}" pathLength="1" style="--i:${K++}"/>`);
  }
  const R = (x, y, w, h, cls) => P(`M${f(x)} ${f(y)}h${f(w)}v${f(h)}h${f(-w)}Z`, cls);
  const poly = (pts, cls) => P('M' + pts.map((p) => f(p[0]) + ' ' + f(p[1])).join('L') + 'Z', cls);
  const line = (x0, y0, x1, y1, cls) => P(`M${f(x0)} ${f(y0)}L${f(x1)} ${f(y1)}`, cls || 'ln th');
  const circ = (cx, cy, r, cls) =>
    P(`M${f(cx - r)} ${f(cy)}a${r} ${r} 0 1 0 ${f(2 * r)} 0a${r} ${r} 0 1 0 ${f(-2 * r)} 0Z`, cls);

  /* ---------------------------------------------------------- peces */

  const body = (x0, x1, top, cls) => R(x0, top, x1 - x0, G - top, cls);
  const cornice = (x0, x1, y) => R(x0 - 3, y - 3, x1 - x0 + 6, 3);
  function steps(x0, x1, n, h, s) {
    s = s == null ? 3 : s;
    for (let k = 0; k < n; k++) R(x0 - k * s, G - (n - k) * h, x1 - x0 + 2 * k * s, h);
    return G - n * h;
  }
  // Columnes: fust i capitell en un sol traç.
  function cols(x0, x1, yb, yt, n, w) {
    w = w || Math.max(2.2, Math.min(6, (x1 - x0) / n * 0.42));
    let d = '';
    for (let k = 0; k < n; k++) {
      const cx = n === 1 ? (x0 + x1) / 2 : x0 + (x1 - x0) * k / (n - 1);
      d += `M${f(cx - w / 2)} ${f(yb)}V${f(yt)}M${f(cx + w / 2)} ${f(yt)}V${f(yb)}` +
           `M${f(cx - w / 2 - 1.2)} ${f(yt)}h${f(w + 2.4)}`;
    }
    P(d, 'ln th');
  }
  function ped(x0, x1, y, h) {
    poly([[x0, y], [(x0 + x1) / 2, y - h], [x1, y]]);
    P(`M${f(x0 + 8)} ${f(y - 2)}L${f((x0 + x1) / 2)} ${f(y - h + 4)}L${f(x1 - 8)} ${f(y - 2)}`, 'ln th');
  }
  const ent = (x0, x1, y, h) => R(x0, y, x1 - x0, h || 6);
  // Finestres: cada una s'encen pel seu compte.
  function wins(x0, x1, y, h, nc, nr, gap, arch) {
    const cw = (x1 - x0) / nc, w = Math.max(1.6, cw * 0.46);
    gap = gap || h * 1.9;
    for (let r = 0; r < nr; r++) {
      for (let c = 0; c < nc; c++) {
        const x = x0 + cw * (c + 0.5) - w / 2, yy = y + r * gap;
        if (arch) P(`M${f(x)} ${f(yy + h)}V${f(yy + w / 2)}a${f(w / 2)} ${f(w / 2)} 0 0 1 ${f(w)} 0V${f(yy + h)}Z`, 'wn');
        else R(x, yy, w, h, 'wn');
      }
    }
  }
  function arcade(x0, x1, yb, h, n) {
    const cw = (x1 - x0) / n, w = cw * 0.62;
    for (let k = 0; k < n; k++) {
      const x = x0 + cw * (k + 0.5) - w / 2;
      P(`M${f(x)} ${f(yb)}V${f(yb - h + w / 2)}a${f(w / 2)} ${f(w / 2)} 0 0 1 ${f(w)} 0V${f(yb)}Z`, 'wn');
    }
  }
  function dome(cx, yb, r, h, cls, lantern) {
    P(`M${f(cx - r)} ${f(yb)}C${f(cx - r)} ${f(yb - h * 1.3)} ${f(cx + r)} ${f(yb - h * 1.3)} ${f(cx + r)} ${f(yb)}Z`, cls || 'ln');
    let d = '';
    for (const t of [-0.55, -0.18, 0.18, 0.55]) {
      d += `M${f(cx + t * r)} ${f(yb)}Q${f(cx + t * r * 0.9)} ${f(yb - h * 0.85)} ${f(cx)} ${f(yb - h * 0.97)}`;
    }
    P(d, 'ln th');
    if (lantern !== false) {
      R(cx - 3, yb - h - 8, 6, 8);
      P(`M${f(cx - 4)} ${f(yb - h - 8)}Q${f(cx)} ${f(yb - h - 14)} ${f(cx + 4)} ${f(yb - h - 8)}Z`);
    }
  }
  function glassDome(cx, yb, r, h) {
    P(`M${f(cx - r)} ${f(yb)}C${f(cx - r)} ${f(yb - h * 1.3)} ${f(cx + r)} ${f(yb - h * 1.3)} ${f(cx + r)} ${f(yb)}Z`, 'ln gl');
    let d = '';
    for (let k = 1; k < 8; k++) {
      const t = -1 + k / 4;
      d += `M${f(cx + t * r)} ${f(yb)}Q${f(cx + t * r)} ${f(yb - h * 0.9)} ${f(cx)} ${f(yb - h * 0.98)}`;
    }
    for (const q of [0.28, 0.55, 0.8]) {
      const w = r * Math.sqrt(1 - q * q) * 1.02;
      d += `M${f(cx - w)} ${f(yb - h * q)}H${f(cx + w)}`;
    }
    P(d, 'ln th');
  }
  // Torre: fust i coronament.
  function tower(x0, x1, yt, top, hs, yb) {
    R(x0, yt, x1 - x0, (yb == null ? G : yb) - yt);
    const m = (x0 + x1) / 2;
    hs = hs || (x1 - x0) * 1.2;
    if (top === 'spire') poly([[x0 - 1, yt], [m, yt - hs], [x1 + 1, yt]]);
    else if (top === 'cone') poly([[x0 - 2, yt], [m, yt - hs], [x1 + 2, yt]]);
    else if (top === 'cup') dome(m, yt, (x1 - x0) / 2, (x1 - x0) * 0.45, 'ln', true);
    else if (top === 'crenel') merlons(x0, x1, yt, 4);
    else cornice(x0, x1, yt);
  }
  function merlons(x0, x1, y, n) {
    const w = (x1 - x0) / (2 * n - 1);
    let d = '';
    for (let k = 0; k < n; k++) d += `M${f(x0 + 2 * k * w)} ${f(y)}v-4h${f(w)}v4`;
    P(d, 'ln th');
  }
  // Pinacles gotics al llarg d'una cornisa.
  function pinn(x0, x1, y, n, h) {
    let d = '';
    for (let k = 0; k <= n; k++) {
      const x = x0 + (x1 - x0) * k / n;
      d += `M${f(x - 1.4)} ${f(y)}L${f(x)} ${f(y - h)}L${f(x + 1.4)} ${f(y)}`;
    }
    P(d, 'ln th');
  }
  function lion(x, y, dir) {
    R(x - 7, y, 14, G - y);
    const s = dir || 1;
    P(`M${f(x - 6 * s)} ${f(y)}q${f(1 * s)} -5 ${f(5 * s)} -5h${f(4 * s)}q${f(1 * s)} -4 ${f(4 * s)} -3` +
      `q${f(1 * s)} 3 ${f(-1 * s)} 5v3Z`, 'ln');
  }
  function statue(x, y) {
    R(x - 3, y, 6, G - y);
    P(`M${f(x - 1.5)} ${f(y)}v-6h3v6M${f(x)} ${f(y - 6)}m-1.6 0a1.6 1.6 0 1 0 3.2 0a1.6 1.6 0 1 0 -3.2 0`, 'ln th');
  }

  /* ---------------------------------------------------------- banderes */

  // Simplificades: franges, creu nordica o algun tret propi.
  const FLAGS = {
    es: { h: ['#AA151B', '#F1BF00', '#F1BF00', '#AA151B'] },
    de: { h: ['#000', '#DD0000', '#FFCE00'] }, it: { v: ['#009246', '#fff', '#CE2B37'] },
    fr: { v: ['#002395', '#fff', '#ED2939'] }, at: { h: ['#C8102E', '#fff', '#C8102E'] },
    be: { v: ['#000', '#FDDA24', '#EF3340'] }, nl: { h: ['#AE1C28', '#fff', '#21468B'] },
    pl: { h: ['#fff', '#DC143C'] }, pt: { v: ['#060', '#060', '#E00', '#E00', '#E00'] },
    se: { x: ['#006AA7', '#FECC02'] }, no: { x: ['#BA0C2F', '#fff', '#00205B'] },
    dk: { x: ['#C8102E', '#fff'] }, fi: { x: ['#fff', '#002F6C'] },
    is: { x: ['#02529C', '#fff', '#DC1E35'] }, ee: { h: ['#0072CE', '#000', '#fff'] },
    lt: { h: ['#FDB913', '#006A44', '#C1272D'] }, cz: { h: ['#fff', '#D7141A'], tri: '#11457E' },
    sk: { h: ['#fff', '#0B4EA2', '#EE1C25'] }, si: { h: ['#fff', '#005DA4', '#ED1C24'] },
    hr: { h: ['#FF0000', '#fff', '#171796'] },
    gr: { h: ['#0D5EAF', '#fff', '#0D5EAF', '#fff', '#0D5EAF', '#fff', '#0D5EAF', '#fff', '#0D5EAF'], canton: 'gr' },
    tr: { h: ['#E30A17'], moon: true }, md: { v: ['#003DA5', '#FFD200', '#CC092F'] },
    me: { h: ['#C40308'], border: '#D4AF3A' }, bg: { h: ['#fff', '#00966E', '#D62612'] },
    ro: { v: ['#002B7F', '#FCD116', '#CE1126'] }, ch: { h: ['#DA291C'], plus: true, sq: true },
    lu: { h: ['#EF3340', '#fff', '#00A3E0'] }, hu: { h: ['#CE2939', '#fff', '#477050'] },
    ie: { v: ['#169B62', '#fff', '#FF883E'] }, gb: { h: ['#012169'], union: true },
    au: { h: ['#012169'], union: true, stars: '#fff' }, nz: { h: ['#012169'], union: true, stars: '#C8102E' },
    ph: { h: ['#0038A8', '#CE1126'], tri: '#fff' }, sv: { h: ['#0F47AF', '#fff', '#0F47AF'] },
    gm: { h: ['#CE1126', '#CE1126', '#fff', '#0C1C8C', '#0C1C8C', '#fff', '#3A7728', '#3A7728'] },
    lv: { h: ['#9E3039', '#9E3039', '#fff', '#9E3039', '#9E3039'] },
  };
  function flag(x, yt, code, len) {
    const F = FLAGS[code];
    if (!F) return;
    len = len || 18;
    P(`M${f(x)} ${f(yt + len)}V${f(yt - 1)}`, 'pole');
    const w = F.sq ? 12 : 18, h = 12;
    let s = '';
    const fill = (c) => `fill="${c}"`;
    if (F.x) {
      s += `<rect width="${w}" height="${h}" ${fill(F.x[0])}/>` +
           `<rect x="5" width="3" height="${h}" ${fill(F.x[1])}/><rect y="4.5" width="${w}" height="3" ${fill(F.x[1])}/>`;
      if (F.x[2]) s += `<rect x="5.9" width="1.2" height="${h}" ${fill(F.x[2])}/><rect y="5.4" width="${w}" height="1.2" ${fill(F.x[2])}/>`;
    } else if (F.h) {
      const n = F.h.length;
      F.h.forEach((c, i) => { s += `<rect y="${f(i * h / n)}" width="${w}" height="${f(h / n + 0.05)}" ${fill(c)}/>`; });
    } else if (F.v) {
      const n = F.v.length;
      F.v.forEach((c, i) => { s += `<rect x="${f(i * w / n)}" width="${f(w / n + 0.05)}" height="${h}" ${fill(c)}/>`; });
    }
    if (F.tri) s += `<path d="M0 0L${F.sq ? 6 : 8} 6L0 12Z" ${fill(F.tri)}/>`;
    if (F.canton) s += `<rect width="6.7" height="6.7" fill="#0D5EAF"/><rect x="2.7" width="1.3" height="6.7" fill="#fff"/><rect y="2.7" width="6.7" height="1.3" fill="#fff"/>`;
    if (F.moon) s += '<circle cx="6.5" cy="6" r="3.2" fill="#fff"/><circle cx="7.4" cy="6" r="2.6" fill="#E30A17"/><circle cx="10.6" cy="6" r="1.1" fill="#fff"/>';
    if (F.border) s += `<rect x=".8" y=".8" width="${w - 1.6}" height="${h - 1.6}" fill="none" stroke="${F.border}" stroke-width="1"/>`;
    if (F.plus) s += '<rect x="5" y="2.5" width="2" height="7" fill="#fff"/><rect x="2.5" y="5" width="7" height="2" fill="#fff"/>';
    if (F.union) {
      const uw = F.stars ? 9 : w, uh = F.stars ? 6 : h;
      s += `<g><path d="M0 0L${uw} ${uh}M${uw} 0L0 ${uh}" stroke="#fff" stroke-width="${f(uh / 5)}"/>` +
           `<path d="M0 0L${uw} ${uh}M${uw} 0L0 ${uh}" stroke="#C8102E" stroke-width="${f(uh / 15)}"/>` +
           `<path d="M${uw / 2} 0V${uh}M0 ${uh / 2}H${uw}" stroke="#fff" stroke-width="${f(uh / 3)}"/>` +
           `<path d="M${uw / 2} 0V${uh}M0 ${uh / 2}H${uw}" stroke="#C8102E" stroke-width="${f(uh / 5)}"/></g>`;
      if (F.stars) for (const [a, b] of [[13, 3], [15.5, 6], [13, 9.5], [11, 6.5], [4.5, 9.5]]) s += `<circle cx="${a}" cy="${b}" r=".8" fill="${F.stars}"/>`;
    }
    S.push(`<g transform="translate(${f(x)} ${f(yt - 1)})"><g class="cloth" style="--i:${K++}">${s}</g></g>`);
  }

  /* ---------------------------------------------------------- edificis */

  // Facana neoclassica: cos, ales amb finestres, portic amb columnes i fronto.
  function classic(o) {
    const x0 = o.x0 == null ? 56 : o.x0, x1 = o.x1 == null ? 304 : o.x1;
    const top = o.top || 64, p0 = o.p0 || 136, p1 = o.p1 || 224;
    body(x0, x1, top);
    cornice(x0, x1, top);
    const wr = o.wr == null ? 2 : o.wr, wc = o.wc || 5;
    if (wr) {
      wins(x0 + 6, p0 - 8, top + 10, 9, wc, wr, 17, o.arch);
      wins(p1 + 8, x1 - 6, top + 10, 9, wc, wr, 17, o.arch);
    }
    const yb = o.st ? steps(p0 - 2, p1 + 2, o.st, o.sh || 3, o.ss) : G;
    const et = o.et || top - 4;
    R(p0, et + 6, p1 - p0, yb - et - 6, 'ln sh');
    cols(p0 + 5, p1 - 5, yb, et + 8, o.nc || 6);
    ent(p0 - 3, p1 + 3, et);
    if (o.ped !== 0) ped(p0 - 4, p1 + 4, et, o.ped || 18);
    return { apex: et - (o.ped === 0 ? 0 : (o.ped || 18)) };
  }

  const B = {
    'es-congreso': {
      name: { es: 'Palacio de las Cortes', ca: 'Palau de les Corts' }, city: 'Madrid', lay: 'hemi',
      draw() {
        const c = classic({ x0: 50, x1: 310, top: 66, p0: 134, p1: 226, nc: 6, st: 4, et: 60, ped: 20, wc: 5 });
        lion(112, 100, 1); lion(248, 100, -1);
        flag(180, c.apex - 16, 'es');
      },
    },
    'es-senado': {
      name: { es: 'Palacio del Senado', ca: 'Palau del Senat' }, city: 'Madrid', lay: 'hemi',
      draw() {
        R(14, 74, 52, 46, 'ln gl'); P('M14 86H66M14 98H66M14 110H66M27 74V120M40 74V120M53 74V120', 'ln th');
        body(70, 292, 60); cornice(70, 292, 60);
        wins(76, 146, 70, 9, 4, 3, 16); wins(214, 286, 70, 9, 4, 3, 16);
        R(148, 52, 64, 68); cornice(148, 212, 52); ped(146, 214, 49, 10);
        cols(154, 206, 92, 56, 4, 3);
        R(160, 70, 40, 2); wins(154, 206, 60, 10, 3, 1);
        P('M170 120V104a10 10 0 0 1 20 0V120Z', 'wn');
        flag(180, 21, 'es');
      },
    },
    de: {
      name: { es: 'Reichstag', ca: 'Reichstag' }, city: 'Berlín', lay: 'hemi',
      draw() {
        glassDome(180, 50, 31, 30);
        body(48, 312, 62); cornice(48, 312, 62);
        tower(48, 82, 44, 'flat'); tower(278, 312, 44, 'flat');
        wins(52, 78, 52, 8, 2, 4, 16); wins(282, 308, 52, 8, 2, 4, 16);
        wins(88, 132, 72, 9, 3, 2, 18, true); wins(228, 272, 72, 9, 3, 2, 18, true);
        const yb = steps(132, 228, 3, 3);
        R(136, 64, 88, yb - 64, 'ln sh'); cols(141, 219, yb, 66, 6); ent(133, 227, 58);
        ped(132, 228, 58, 15); R(156, 59.5, 48, 2, 'ln th');
        flag(65, 26, 'de'); flag(295, 26, 'de');
      },
    },
    gb: {
      name: { es: 'Palacio de Westminster', ca: 'Palau de Westminster' }, city: 'Londres', lay: 'west',
      draw() {
        body(36, 290, 74); pinn(36, 290, 74, 36, 5);
        wins(78, 288, 82, 14, 18, 2, 19, true);
        tower(40, 74, 30, 'flat'); pinn(40, 74, 30, 4, 8); wins(44, 70, 40, 12, 3, 4, 18, true);
        R(176, 50, 12, 24); poly([[174, 50], [182, 30], [190, 50]]);
        tower(296, 316, 54, 'flat'); R(293, 38, 26, 16); circ(306, 46, 5.5, 'ln wn');
        R(296, 28, 20, 10); arcade(296, 316, 38, 9, 3); poly([[293, 28], [306, 4], [319, 28]]);
        flag(57, 4, 'gb');
      },
    },
    fr: {
      name: { es: 'Palacio Borbón', ca: 'Palau Borbó' }, city: 'París', lay: 'hemi',
      draw() {
        const c = classic({ x0: 36, x1: 324, top: 70, p0: 96, p1: 264, nc: 12, st: 4, et: 62, ped: 20, wc: 3 });
        flag(180, c.apex - 16, 'fr');
      },
    },
    it: {
      name: { es: 'Palacio de Montecitorio', ca: 'Palau de Montecitorio' }, city: 'Roma', lay: 'hemi',
      draw() {
        body(40, 320, 56); cornice(40, 320, 56);
        R(128, 50, 104, 70); cornice(128, 232, 50);
        wins(46, 124, 64, 10, 5, 3, 17); wins(236, 314, 64, 10, 5, 3, 17);
        wins(132, 228, 58, 10, 5, 3, 17);
        R(166, 34, 28, 16); arcade(168, 192, 50, 12, 2); ped(164, 196, 34, 8);
        R(156, 96, 48, 3); cols(158, 202, 120, 99, 4, 3);
        flag(180, 4, 'it');
      },
    },
    at: {
      name: { es: 'Parlamento', ca: 'Parlament' }, city: 'Viena', lay: 'hemi',
      draw() {
        body(28, 120, 68); cornice(28, 120, 68); body(240, 332, 68); cornice(240, 332, 68);
        wins(34, 116, 76, 9, 5, 2, 18); wins(244, 326, 76, 9, 5, 2, 18);
        R(30, 58, 22, 10); R(308, 58, 22, 10); statue(41, 52); statue(319, 52);
        P('M70 120L120 90H240L290 120', 'ln');
        R(120, 90, 120, 30);
        R(126, 56, 108, 34, 'ln sh'); cols(130, 230, 90, 58, 8); ent(122, 238, 50);
        ped(120, 240, 50, 16);
        flag(74, 50, 'at');
      },
    },
    be: {
      name: { es: 'Palacio de la Nación', ca: 'Palau de la Nació' }, city: 'Brussel·les',
      cityes: 'Bruselas', lay: 'hemi',
      draw() {
        const c = classic({ x0: 58, x1: 302, top: 62, p0: 148, p1: 212, nc: 4, et: 58, ped: 14, wc: 5, st: 2 });
        flag(180, c.apex - 16, 'be');
      },
    },
    nl: {
      name: { es: 'Binnenhof (sede histórica, en obras)', ca: 'Binnenhof (seu històrica, en obres)' },
      city: 'la Haia', cityes: 'La Haya', lay: 'hemi',
      draw() {
        body(28, 120, 82); poly([[26, 82], [74, 64], [122, 82]]); wins(34, 116, 90, 9, 5, 2, 16);
        body(240, 332, 82); poly([[238, 82], [286, 64], [334, 82]]); wins(244, 326, 90, 9, 5, 2, 16);
        R(132, 64, 96, 56); poly([[132, 64], [180, 26], [228, 64]]);
        circ(180, 52, 7, 'ln wn'); wins(140, 220, 74, 14, 4, 1); P('M172 120V102a8 8 0 0 1 16 0V120Z', 'wn');
        tower(122, 134, 42, 'cone', 18); tower(226, 238, 42, 'cone', 18);
        flag(128, 8, 'nl', 16);
      },
    },
    pl: {
      name: { es: 'Sejm', ca: 'Sejm' }, city: 'Varsòvia', cityes: 'Varsovia', lay: 'hemi',
      draw() {
        body(40, 320, 70); cornice(40, 320, 70);
        R(120, 54, 120, 66); cornice(120, 240, 54);
        cols(126, 234, 120, 60, 13, 3);
        wins(46, 116, 80, 10, 4, 2, 18); wins(244, 314, 80, 10, 4, 2, 18);
        flag(180, 20, 'pl');
      },
    },
    pt: {
      name: { es: 'Palacio de São Bento', ca: 'Palau de São Bento' }, city: 'Lisboa', lay: 'hemi',
      draw() {
        const c = classic({ x0: 36, x1: 324, top: 60, p0: 126, p1: 234, nc: 6, st: 6, sh: 3.2, ss: 4, et: 54, ped: 18, wc: 5 });
        statue(104, 102); statue(256, 102);
        flag(180, c.apex - 16, 'pt');
      },
    },
    se: {
      name: { es: 'Riksdagshuset', ca: 'Riksdagshuset' }, city: 'Estocolm', cityes: 'Estocolmo', lay: 'hemi',
      draw() {
        body(36, 324, 60); cornice(36, 324, 60);
        wins(42, 126, 68, 9, 5, 3, 16); wins(234, 318, 68, 9, 5, 3, 16);
        R(130, 60, 100, 60, 'ln sh'); cols(134, 226, 112, 64, 8);
        R(128, 112, 104, 8);
        P('M128 60Q180 30 232 60Z');
        flag(180, 20, 'se');
      },
    },
    no: {
      name: { es: 'Storting', ca: 'Storting' }, city: 'Oslo', lay: 'hemi',
      draw() {
        body(56, 140, 72); cornice(56, 140, 72); wins(62, 134, 80, 10, 4, 2, 18, true);
        body(220, 304, 72); cornice(220, 304, 72); wins(226, 298, 80, 10, 4, 2, 18, true);
        R(140, 58, 80, 62); cornice(140, 220, 58);
        arcade(144, 216, 84, 16, 4); arcade(144, 216, 112, 18, 4);
        dome(180, 55, 38, 12, 'ln', false);
        lion(132, 106, 1); lion(228, 106, -1);
        flag(180, 22, 'no');
      },
    },
    dk: {
      name: { es: 'Palacio de Christiansborg', ca: 'Palau de Christiansborg' },
      city: 'Copenhaguen', cityes: 'Copenhague', lay: 'hemi',
      draw() {
        body(36, 324, 62); poly([[32, 62], [44, 50], [316, 50], [328, 62]]);
        wins(42, 160, 70, 9, 7, 3, 16); wins(200, 318, 70, 9, 7, 3, 16);
        P('M168 120V104a12 12 0 0 1 24 0V120Z', 'wn');
        R(166, 30, 28, 20); arcade(168, 192, 48, 12, 2); R(170, 18, 20, 12);
        poly([[168, 18], [180, 3], [192, 18]]); circ(180, 10, 2);
        flag(60, 30, 'dk', 20);
      },
    },
    fi: {
      name: { es: 'Eduskuntatalo', ca: 'Eduskuntatalo' }, city: 'Hèlsinki', cityes: 'Helsinki', lay: 'hemi',
      draw() {
        const yb = steps(80, 280, 5, 3, 4);
        R(84, 30, 192, yb - 30); R(88, 22, 184, 8);
        R(94, 44, 172, yb - 44, 'ln sh');
        cols(98, 262, yb, 46, 14, 4.2);
        flag(180, 4, 'fi');
      },
    },
    is: {
      name: { es: 'Alþingishúsið', ca: 'Alþingishúsið' }, city: 'Reykjavík', lay: 'hemi',
      draw() {
        body(112, 248, 72); poly([[108, 72], [128, 56], [232, 56], [252, 72]]);
        wins(118, 242, 80, 10, 7, 2, 18, true);
        R(172, 100, 16, 20, 'wn');
        flag(270, 54, 'is', 66);
      },
    },
    ee: {
      name: { es: 'Castillo de Toompea', ca: 'Castell de Toompea' }, city: 'Tallinn', lay: 'fan',
      draw() {
        R(20, 86, 34, 34); merlons(20, 54, 86, 3);
        R(54, 26, 40, 94); merlons(54, 94, 26, 4); wins(62, 86, 40, 10, 2, 4, 18, true);
        body(110, 316, 68); poly([[106, 68], [118, 56], [308, 56], [320, 68]]);
        wins(116, 310, 76, 10, 9, 2, 20);
        ped(190, 236, 68, 12);
        flag(74, 4, 'ee', 18);
      },
    },
    lt: {
      name: { es: 'Seimas', ca: 'Seimas' }, city: 'Vílnius', cityes: 'Vilna', lay: 'hemi',
      draw() {
        R(150, 28, 92, 92); wins(154, 238, 34, 7, 7, 6, 12);
        body(40, 330, 82); wins(46, 146, 90, 6, 8, 2, 13); wins(246, 324, 90, 6, 6, 2, 13);
        R(36, 78, 298, 4);
        flag(122, 40, 'lt', 42);
      },
    },
    lv: {
      name: { es: 'Saeima', ca: 'Saeima' }, city: 'Riga', lay: 'hemi',
      draw() {
        body(70, 290, 60); cornice(70, 290, 60); wins(76, 284, 68, 10, 10, 3, 17, true);
        flag(180, 24, 'lv', 36);
      },
    },
    cz: {
      name: { es: 'Palacio Thun', ca: 'Palau Thun' }, city: 'Praga', lay: 'hemi',
      draw() {
        body(64, 296, 64); poly([[60, 64], [72, 52], [288, 52], [300, 64]]);
        wins(70, 290, 72, 10, 10, 2, 20);
        R(158, 94, 44, 26, 'ln sh'); cols(160, 200, 120, 96, 4, 3); ped(154, 206, 94, 8);
        flag(180, 16, 'cz', 36);
      },
    },
    sk: {
      name: { es: 'Consejo Nacional (junto al castillo)', ca: 'Consell Nacional (al costat del castell)' },
      city: 'Bratislava', lay: 'hemi',
      draw() {
        R(196, 38, 118, 48); poly([[192, 38], [255, 24], [318, 38]]);
        for (const x of [196, 300]) { R(x, 30, 14, 56); poly([[x - 1, 30], [x + 7, 18], [x + 15, 30]]); }
        wins(214, 296, 46, 7, 6, 2, 14);
        body(36, 290, 84); let d = '';
        for (let x = 42; x < 288; x += 7) d += `M${x} 88V118`;
        P(d, 'ln th'); R(32, 80, 262, 4);
        flag(160, 46, 'sk', 34);
      },
    },
    si: {
      name: { es: 'Asamblea Nacional', ca: 'Assemblea Nacional' }, city: 'Ljubljana', lay: 'hemi',
      draw() {
        R(106, 40, 148, 80); wins(110, 250, 46, 7, 10, 3, 11);
        R(158, 78, 44, 42, 'ln sh'); P('M164 82V118M172 82V118M180 82V118M188 82V118M196 82V118', 'ln th');
        flag(90, 50, 'si', 70);
      },
    },
    hr: {
      name: { es: 'Sabor', ca: 'Sabor' }, city: 'Zagreb', lay: 'hemi',
      draw() {
        R(26, 84, 66, 36); P('M24 84L58 64L94 84Z', 'ln');
        S.push('<g class="tiles" style="--i:' + (K++) + '">' + [0, 1, 2, 3].map((i) =>
          `<path d="M${40 + i * 8} 78l4 -2.4v4l-4 2.4Z" fill="${i % 2 ? '#fff' : '#C8102E'}"/><path d="M${44 + i * 8} 75.6l4 -2.4v4l-4 2.4Z" fill="${i % 2 ? '#1C3F94' : '#fff'}"/>`).join('') + '</g>');
        tower(82, 96, 50, 'spire', 16, 84);
        body(110, 324, 70); cornice(110, 324, 70);
        wins(116, 318, 78, 10, 10, 2, 20);
        R(196, 86, 44, 3);
        flag(218, 34, 'hr', 36);
      },
    },
    gr: {
      name: { es: 'Parlamento (antiguo palacio real)', ca: 'Parlament (antic palau reial)' },
      city: 'Atenes', cityes: 'Atenas', lay: 'hemi',
      draw() {
        body(36, 324, 58); cornice(36, 324, 58);
        wins(42, 318, 66, 10, 14, 2, 18);
        R(152, 82, 56, 38, 'ln sh'); cols(155, 205, 120, 84, 4, 4.4); ent(148, 212, 78);
        R(130, 112, 100, 8, 'ln sh');
        flag(180, 22, 'gr', 36);
      },
    },
    tr: {
      name: { es: 'Gran Asamblea Nacional', ca: 'Gran Assemblea Nacional' }, city: 'Ankara', lay: 'hemi',
      draw() {
        body(46, 314, 62); R(126, 46, 108, 16); R(42, 58, 276, 4);
        R(50, 66, 260, 50, 'ln sh'); cols(54, 306, 118, 66, 20, 3.4);
        flag(180, 10, 'tr', 36);
      },
    },
    md: {
      name: { es: 'Parlamento', ca: 'Parlament' }, city: 'Chișinău', lay: 'hemi',
      draw() {
        R(60, 94, 240, 26); R(140, 22, 80, 72);
        let d = ''; for (let x = 146; x < 218; x += 6) d += `M${x} 26V92`;
        P(d, 'ln th'); P('M136 22Q180 10 224 22', 'ln');
        wins(66, 136, 100, 7, 5, 1); wins(224, 294, 100, 7, 5, 1);
        flag(110, 52, 'md', 42);
      },
    },
    me: {
      name: { es: 'Asamblea', ca: 'Assemblea' }, city: 'Podgorica', lay: 'hemi',
      draw() {
        body(60, 300, 64); R(56, 60, 248, 4);
        P('M60 80H300M60 96H300', 'ln th'); wins(66, 294, 84, 8, 14, 2, 16);
        flag(180, 26, 'me', 34);
      },
    },
    bg: {
      name: { es: 'Asamblea Nacional', ca: 'Assemblea Nacional' }, city: 'Sofia', lay: 'hemi',
      draw() {
        body(70, 290, 62); cornice(70, 290, 62);
        wins(76, 146, 72, 10, 3, 2, 20, true); wins(214, 284, 72, 10, 3, 2, 20, true);
        R(148, 52, 64, 68); cornice(148, 212, 52); R(156, 56, 48, 3, 'ln th');
        arcade(152, 208, 92, 22, 3); arcade(152, 208, 118, 20, 3);
        flag(180, 16, 'bg', 36);
      },
    },
    ro: {
      name: { es: 'Palacio del Parlamento', ca: 'Palau del Parlament' }, city: 'Bucarest', lay: 'hemi',
      draw() {
        R(16, 84, 328, 36); arcade(20, 340, 118, 14, 30);
        R(56, 64, 248, 20); arcade(60, 300, 82, 12, 22);
        R(104, 46, 152, 18); arcade(108, 252, 62, 11, 14);
        R(156, 30, 48, 16); arcade(160, 200, 44, 10, 4);
        flag(180, 2, 'ro', 28);
      },
    },
    ch: {
      name: { es: 'Palacio Federal', ca: 'Palau Federal' }, city: 'Berna', lay: 'hemi',
      draw() {
        body(24, 132, 70); cornice(24, 132, 70); body(228, 336, 70); cornice(228, 336, 70);
        R(24, 62, 22, 8); R(110, 62, 22, 8); R(228, 62, 22, 8); R(314, 62, 22, 8);
        wins(30, 126, 80, 9, 5, 2, 18); wins(234, 330, 80, 9, 5, 2, 18);
        R(132, 58, 96, 62); cornice(132, 228, 58); arcade(136, 224, 120, 26, 3);
        wins(138, 222, 66, 10, 5, 1, 0, true);
        R(158, 42, 44, 16); dome(180, 42, 24, 18, 'ln cu');
        flag(180, 2, 'ch', 14);
      },
    },
    lu: {
      name: { es: 'Cámara de Diputados', ca: 'Cambra de Diputats' },
      city: 'Luxemburg', cityes: 'Luxemburgo', lay: 'hemi',
      draw() {
        body(40, 132, 64); wins(46, 126, 72, 10, 5, 2, 20);
        tower(48, 60, 54, 'spire', 16, 64); tower(112, 124, 54, 'spire', 16, 64);
        body(140, 254, 68); cornice(140, 254, 68); poly([[176, 68], [197, 54], [218, 68]]);
        wins(146, 248, 76, 10, 5, 2, 20, true);
        flag(197, 22, 'lu', 32);
      },
    },
    hu: {
      name: { es: 'Parlamento', ca: 'Parlament' }, city: 'Budapest', lay: 'hemi',
      draw() {
        body(18, 342, 76); pinn(18, 342, 76, 54, 5);
        wins(24, 150, 84, 13, 9, 2, 18, true); wins(210, 336, 84, 13, 9, 2, 18, true);
        tower(126, 138, 40, 'spire', 16, 76); tower(222, 234, 40, 'spire', 16, 76);
        R(156, 48, 48, 28); arcade(158, 202, 76, 18, 4);
        P('M152 48Q152 22 180 18Q208 22 208 48Z'); poly([[176, 18], [180, 1], [184, 18]]);
        flag(36, 54, 'hu', 22);
      },
    },
    ie: {
      name: { es: 'Leinster House', ca: 'Leinster House' }, city: 'Dublín', lay: 'horse',
      draw() {
        body(96, 264, 56); cornice(96, 264, 56);
        wins(102, 146, 64, 10, 3, 3, 17); wins(214, 258, 64, 10, 3, 3, 17);
        R(150, 66, 60, 54, 'ln sh'); cols(154, 206, 116, 68, 4, 4); ent(146, 214, 60);
        ped(144, 216, 60, 12); R(146, 116, 68, 4);
        flag(180, 30, 'ie', 18);
      },
    },
    au: {
      name: { es: 'Parliament House', ca: 'Parliament House' }, city: 'Canberra', lay: 'horse',
      draw() {
        P('M0 120Q180 92 360 120', 'ln gd');
        R(24, 100, 312, 20); wins(30, 330, 106, 6, 30, 1);
        R(140, 86, 80, 34, 'ln sh'); R(136, 82, 88, 4); cols(144, 216, 120, 88, 12, 2.4);
        P('M112 100L180 18L248 100M140 100L180 18L220 100', 'ln th');
        flag(180, 2, 'au', 16);
      },
    },
    nz: {
      name: { es: 'Parliament House y la Colmena', ca: 'Parliament House i el Rusc' },
      city: 'Wellington', lay: 'west',
      draw() {
        const yb = steps(70, 150, 3, 3);
        body(26, 194, 62); cornice(26, 194, 62);
        wins(32, 66, 70, 10, 2, 3, 16); wins(154, 188, 70, 10, 2, 3, 16);
        R(74, 66, 72, yb - 66, 'ln sh'); cols(78, 142, yb, 68, 6); ent(70, 150, 58);
        const tiers = [[200, 100, 140], [206, 88, 128], [212, 76, 116], [218, 64, 104], [224, 52, 92], [230, 42, 80]];
        for (const [x, y, w] of tiers) { R(x, y, w, (y === 100 ? 20 : 12)); P(`M${x + 2} ${y + 5}H${x + w - 2}`, 'wn'); }
        P('M230 42Q270 28 310 42Z');
        flag(110, 24, 'nz', 34);
      },
    },
    ph: {
      name: { es: 'Batasang Pambansa', ca: 'Batasang Pambansa' }, city: 'Quezon City', lay: 'hemi',
      draw() {
        body(40, 320, 66); R(30, 58, 300, 8);
        R(48, 70, 264, 46, 'ln sh'); cols(52, 308, 118, 70, 16, 3);
        poly([[130, 58], [180, 38], [230, 58]]);
        flag(180, 4, 'ph', 34);
      },
    },
    sv: {
      name: { es: 'Palacio Legislativo', ca: 'Palau Legislatiu' }, city: 'San Salvador', lay: 'hemi',
      draw() {
        body(70, 290, 56); R(66, 52, 228, 4); wins(76, 284, 62, 8, 12, 3, 17);
        flag(180, 16, 'sv', 36);
      },
    },
    gm: {
      name: { es: 'Asamblea Nacional', ca: 'Assemblea Nacional' }, city: 'Banjul', lay: 'horse',
      draw() {
        body(86, 274, 64); cornice(86, 274, 64); wins(92, 268, 72, 10, 9, 2, 20, true);
        R(162, 52, 36, 12); dome(180, 52, 18, 14, 'ln', false);
        flag(110, 28, 'gm', 36);
      },
    },
    _: {
      name: null, lay: 'hemi',
      draw() {
        classic({ x0: 60, x1: 300, top: 66, p0: 140, p1: 220, nc: 6, st: 3, et: 60, ped: 0, wc: 5 });
        R(150, 46, 60, 12); dome(180, 46, 26, 20);
      },
    },
  };

  /* ------------------------------------------------- l'interior de la sala */

  // Vist des de la presidencia, com una foto del ple buit: les files de
  // bancs pugen cap enfora, partides per escales; al fons, columnes, la
  // tribuna de public amb la barana daurada i, a dalt, el lluernari. A les
  // fosques s'encenen els apliques, despres la sala, i els diputats van
  // entrant i s'asseuen al seu escó, vestits del color del partit.

  // Colors de cada sala. Nomes les que coneixem; la resta, sala neutra.
  const ROOM = {
    'es-congreso': { wall: '#e9d9b8', upper: '#e2cfa6', wood: '#8f5d33', dark: '#4b2e18', seat: '#962c31',
                     front: '#1f1d21', gold: '#d6af55', floor: '#9d3f37', stair: '#8e3530', curtain: '#a21d22',
                     clock: true, cols: 6, colc: '#3d2b20', sky: true, lamps: true, gal2: true },
    'es-senado': { wall: '#e6d5b4', upper: '#dbc7a0', wood: '#7d4e2b', dark: '#46291a', seat: '#8e2a2f',
                   front: '#1f1d21', gold: '#cfa64c', floor: '#7d2f2a', stair: '#73302a', curtain: '#8f1d22',
                   cols: 4, colc: '#5a4030', lamps: true, gal2: true },
    fr: { wall: '#e6d2a9', upper: '#dcc597', wood: '#7a4a28', dark: '#40261a', seat: '#a8282d', gold: '#d1aa52',
          floor: '#8c2f2a', stair: '#7e2b26', curtain: '#8f1d22', cols: 8, colc: '#d3c193', lamps: true, gal2: true, sky: true },
    it: { wall: '#d9c8a3', upper: '#cfbb91', wood: '#6b4423', dark: '#3a2414', seat: '#7f2b2b', gold: '#c7a65a',
          floor: '#6e2a24', stair: '#5f2620', cols: 6, colc: '#ab966c', lamps: true, gal2: true, sky: true },
    de: { wall: '#f0f2f4', upper: '#e4e7eb', wood: '#d7d1c3', dark: '#9a9588', seat: '#4258a6', gold: '#a8b0ba',
          floor: '#9ba4b6', stair: '#8b94a6', cols: 0, dome: true },
    gb: { wall: '#6e4c2c', upper: '#5d3f23', wood: '#5c3b21', dark: '#2e1d10', seat: '#2f6d3d', gold: '#b8944b',
          floor: '#2f5d37', line: '#b3262a' },
    nz: { wall: '#a37c54', upper: '#8f6c47', wood: '#6b4a2b', dark: '#3a2616', seat: '#356d46', gold: '#b99d5e',
          floor: '#3c6b48', line: '#9c2b2b' },
    au: { wall: '#dccfb6', upper: '#cdbfa1', wood: '#ad8e66', dark: '#6b5236', seat: '#3e7c4f', gold: '#bba46b',
          floor: '#4b7c56', stair: '#43704d', cols: 0, sky: true },
    _: { wall: '#ddd9d0', upper: '#d1ccc2', wood: '#a98a64', dark: '#6b5638', seat: '#56677f', gold: '#bba46b',
         floor: '#6d7380', stair: '#5f6572', cols: 4, colc: '#c2bbab', lamps: true },
  };
  const SKIN = ['#efcfae', '#e2b48c', '#d09a70', '#b98258', '#9a6a46', '#f3d9c0', '#7d5236'];
  const HAIR = ['#2a1d14', '#4a3222', '#1a1a1a', '#6b4a2e', '#8a8a8a', '#b8b0a4', '#3a2a1e'];

  const PI = Math.PI;
  const hash = (i) => { let x = (i + 1) * 2654435761 % 4294967296; x ^= x >>> 15; return ((x >>> 0) % 1000) / 1000; };
  function mix(a, b, t) {
    const p = (h) => { h = h.replace('#', ''); if (h.length === 3) h = h.replace(/./g, '$&$&'); return [0, 2, 4].map((i) => parseInt(h.substr(i, 2), 16)); };
    const A = p(a), Bc = p(b);
    return '#' + A.map((v, i) => Math.round(v + (Bc[i] - v) * t).toString(16).padStart(2, '0')).join('');
  }
  const lite = (h, t) => mix(h, '#ffffff', t), dim = (h, t) => mix(h, '#000000', t);
  const pts2 = (a) => a.map((p) => f(p[0]) + ' ' + f(p[1])).join('L');
  const shape = (a, fill, extra) => `<path d="M${pts2(a)}Z" fill="${fill}"${extra || ''}/>`;
  const stroke = (a, col, w, extra) => `<path d="M${pts2(a)}" fill="none" stroke="${col}" stroke-width="${w}"${extra || ''}/>`;

  // Camera: X = 180 + x·F/(d+c), Y = Yh + (H - z)·F/(d+c).
  const cam = (c, H, F, Yh) => (x, d, z) => {
    const s = F / (d + c);
    return [180 + x * s, Yh + (H - z) * s, s];
  };

  function defs(u, st) {
    const g = (id, stops, attrs) => `<linearGradient id="${u}${id}" ${attrs || 'x1="0" y1="0" x2="0" y2="1"'}>` +
      stops.map(([o, c, op]) => `<stop offset="${o}" stop-color="${c}"${op != null ? ` stop-opacity="${op}"` : ''}/>`).join('') + '</linearGradient>';
    return '<defs>' +
      g('wall', [[0, lite(st.wall, 0.25)], [0.6, st.wall], [1, dim(st.wall, 0.12)]]) +
      g('wood', [[0, lite(st.wood, 0.22)], [0.35, st.wood], [1, dim(st.wood, 0.35)]]) +
      g('top', [[0, lite(st.wood, 0.35)], [1, lite(st.wood, 0.1)]]) +
      g('vel', [[0, lite(st.seat, 0.28)], [0.45, st.seat], [1, dim(st.seat, 0.4)]]) +
      g('lea', [[0, lite(st.front || st.seat, 0.3)], [0.5, st.front || st.seat], [1, dim(st.front || st.seat, 0.3)]]) +
      g('gold', [[0, lite(st.gold, 0.45)], [0.5, st.gold], [1, dim(st.gold, 0.3)]]) +
      g('col', [[0, dim(st.colc || st.dark, 0.35)], [0.35, lite(st.colc || st.dark, 0.25)], [0.6, st.colc || st.dark], [1, dim(st.colc || st.dark, 0.45)]], 'x1="0" y1="0" x2="1" y2="0"') +
      g('cur', [[0, dim(st.curtain || '#800', 0.45)], [0.3, st.curtain || '#800'], [0.55, lite(st.curtain || '#800', 0.18)], [0.8, st.curtain || '#800'], [1, dim(st.curtain || '#800', 0.45)]],
        'x1="0" y1="0" x2=".14" y2="0" spreadMethod="repeat"') +
      g('sky', [[0, '#fff6dc'], [0.55, '#f3e2b4'], [1, lite(st.upper, 0.1)]]) +
      g('glass', [[0, '#e8f2ff'], [1, '#b9cde6']]) +
      g('light', [[0, '#fff4d8', 0.22], [0.5, '#fff4d8', 0.04], [1, '#000', 0.12]]) +
      g('ray', [[0, '#fff8e4', 0.2], [0.55, '#fff8e4', 0.07], [1, '#fff8e4', 0]]) +
      g('rec', [[0, '#000', 0.55], [1, '#000', 0.2]]) +
      `<pattern id="${u}lead" width="7" height="5" patternUnits="userSpaceOnUse"><path d="M0 2.5L3.5 0L7 2.5L3.5 5Z" fill="none" stroke="${dim(st.gold, 0.45)}" stroke-width=".35"/>` +
      `<path d="M3.5 0L7 2.5L3.5 5L0 2.5Z" fill="${st.dome ? '#cfe0f5' : '#f6d48a'}" opacity=".25"/></pattern>` +
      `<radialGradient id="${u}vig" cx=".5" cy=".42" r=".78"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".55"/></radialGradient>` +
      `<radialGradient id="${u}glow"><stop offset="0" stop-color="#fff3c8" stop-opacity=".95"/><stop offset=".25" stop-color="#ffd98a" stop-opacity=".55"/><stop offset="1" stop-color="#ffb347" stop-opacity="0"/></radialGradient>` +
      `<pattern id="${u}carpet" width="9" height="6" patternUnits="userSpaceOnUse"><rect width="9" height="6" fill="${st.floor}"/>` +
      `<path d="M4.5 .6L7.6 3L4.5 5.4L1.4 3Z" fill="none" stroke="${lite(st.floor, 0.22)}" stroke-width=".5"/><circle cx="4.5" cy="3" r=".6" fill="${st.gold}" opacity=".7"/>` +
      `<circle cx="0" cy="0" r=".5" fill="${dim(st.floor, 0.25)}"/><circle cx="9" cy="6" r=".5" fill="${dim(st.floor, 0.25)}"/></pattern>` +
      `<pattern id="${u}stair" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="${st.stair || st.floor}"/><path d="M0 4L4 0" stroke="${dim(st.stair || st.floor, 0.2)}" stroke-width=".4"/></pattern>` +
      '</defs>';
  }

  // Punt d'una fila de radi r a la distancia s del seu extrem esquerre
  // (braços rectes i arc). d = cap al fons.
  function rowXY(r, s, span, arm) {
    if (s < arm) return [-r, -(arm - s)];
    if (s > arm + span * r) return [r, -(s - arm - span * r)];
    const t = PI / 2 + span / 2 - (s - arm) / r;
    return [r * Math.cos(t), r * Math.sin(t)];
  }
  function rowCurve(P3, r, z, span, arm, n, s0, s1) {
    const len = span * r + 2 * arm, out = [];
    s0 = s0 == null ? 0 : s0; s1 = s1 == null ? len : s1;
    for (let k = 0; k <= n; k++) {
      const [x, d] = rowXY(r, s0 + (s1 - s0) * k / n, span, arm);
      out.push(P3(x, d, z));
    }
    return out;
  }
  // Una fila amb A passadissos (escales): l'arc es parteix en A+1 sectors.
  function rowGeom(r, span, arm, A, HA) {
    const ga = 2 * HA * r, arc = span * r, sector = (arc - A * ga) / (A + 1), len = arc + 2 * arm;
    return {
      len, eff: len - A * ga, ga,
      sOf(se) {
        if (se <= arm) return se;
        const a = se - arm;
        if (a >= arc - A * ga) return se + A * ga;
        return arm + a + Math.min(A, Math.floor(a / sector)) * ga;
      },
      range(j) { const a0 = arm + j * (sector + ga); return [j === 0 ? 0 : a0, j === A ? len : a0 + sector]; },
      aisle(k) { return arm + k * sector + (k - 0.5) * ga; },
    };
  }
  function arcLayout(n, span, arm, A, HA) {
    const r0 = 0.42;
    const lf = (span * 0.71 + 2 * arm) / (PI * 0.71);
    const rows = Math.max(1, Math.min(15, Math.min(n, Math.round(Math.sqrt(n / (3.2 * lf))))));
    const radii = [];
    for (let i = 0; i < rows; i++) radii.push(rows === 1 ? 1 : r0 + (1 - r0) * i / (rows - 1));
    const geoms = radii.map((r) => rowGeom(r, span, arm, A, HA));
    const sum = geoms.reduce((a, g) => a + g.eff, 0);
    const counts = geoms.map((g) => Math.max(1, Math.floor(n * g.eff / sum)));
    let left = n - counts.reduce((a, b) => a + b, 0);
    for (let i = rows - 1; left > 0; i = (i - 1 + rows) % rows) { counts[i]++; left--; }
    for (let i = 0, over = -left; over > 0; i = (i + 1) % rows) if (counts[i] > 1) { counts[i]--; over--; }
    const pts = [];
    counts.forEach((c, i) => {
      const g = geoms[i], r = radii[i];
      for (let k = 0; k < c; k++) {
        const s = g.sOf(g.eff * (k + 0.5) / c);
        const [x, d] = rowXY(r, s, span, arm);
        pts.push({ x, d, s, u: s / g.len, r, row: i, sp: g.eff / c });
      }
    });
    return { pts, rows, radii, r0, geoms };
  }

  // Un diputat assegut: americana del color del partit, amb la llum de dalt a
  // l'esquerra (espatlla clara, costat dret a l'ombra), camisa i corbata o
  // coll obert, coll, cara amb ombra, orelles i pentinats diferents. De prop,
  // ulls i, alguns, ulleres. `hz`: quant es perd en la boira de la sala.
  const HAZE = '#d9d2c4';
  function person(X, Y, w, g, k, n, ca, hz) {
    const h = hash(k), h2 = hash(k + 11), h3 = hash(k + 23);
    const tw = w * 0.92, th = w * 0.8, hr = w * 0.205;
    const fog = (c) => (hz ? mix(c, HAZE, hz) : c);
    // cada americana és d'una tela una mica diferent
    const tv = hash(k + 41);
    const body = fog(tv < 0.5 ? dim(g.c, (0.5 - tv) * 0.24) : lite(g.c, (tv - 0.5) * 0.16));
    const skin = fog(SKIN[Math.floor(h * SKIN.length)]);
    // 0-1 curt, 2 clenxa, 3 llarg, 4 calb, 5 mitja melena
    const style = Math.floor(h2 * 6);
    const hair = fog(style === 4 && h3 > 0.5 ? '#9a948c' : HAIR[Math.floor(hash(k + 7) * HAIR.length)]);
    const tie = style !== 3 && style !== 5;
    const s = Math.min(0.999, (k / n) * 0.9 + hash(k + 3) * 0.1);
    X += (h3 - 0.5) * w * 0.1;
    const hy = Y - th - hr * 0.95, ry = hr * 1.12;
    let o = `<g class="mp" style="--s:${s.toFixed(3)}"><title>${esc(g.n || (ca ? 'Altres' : 'Otros'))}</title>`;
    // ombra sobre el respatller
    if (w > 2.5) o += `<ellipse cx="${f(X + w * 0.12)}" cy="${f(Y - th * 0.55)}" rx="${f(tw * 0.56)}" ry="${f(th * 0.55)}" fill="#000" opacity=".2"/>`;
    // cabell llarg, per darrere de les espatlles
    if ((style === 3 || style === 5) && w > 3.5) {
      const L = style === 3 ? th * 0.55 : th * 0.2;
      o += `<path d="M${f(X - hr * 1.18)} ${f(hy)}a${f(hr * 1.18)} ${f(ry * 1.1)} 0 0 1 ${f(hr * 2.36)} 0v${f(ry + L)}h${f(-hr * 2.36)}Z" fill="${hair}"/>`;
    }
    // tors i espatlles
    o += `<path d="M${f(X - tw / 2)} ${f(Y)}V${f(Y - th * 0.52)}Q${f(X - tw / 2)} ${f(Y - th * 0.93)} ${f(X - tw * 0.2)} ${f(Y - th)}` +
      `H${f(X + tw * 0.2)}Q${f(X + tw / 2)} ${f(Y - th * 0.93)} ${f(X + tw / 2)} ${f(Y - th * 0.52)}V${f(Y)}Z" fill="${body}"/>`;
    if (w > 3) {
      o += `<path d="M${f(X + tw * 0.16)} ${f(Y)}V${f(Y - th * 0.99)}H${f(X + tw * 0.2)}Q${f(X + tw / 2)} ${f(Y - th * 0.93)} ${f(X + tw / 2)} ${f(Y - th * 0.52)}V${f(Y)}Z" fill="#000" opacity=".2"/>` +
           `<path d="M${f(X - tw * 0.46)} ${f(Y - th * 0.55)}Q${f(X - tw * 0.45)} ${f(Y - th * 0.9)} ${f(X - tw * 0.18)} ${f(Y - th * 0.96)}" fill="none" stroke="#fff" stroke-opacity=".28" stroke-width="${f(w * 0.06)}" stroke-linecap="round"/>`;
    }
    if (w > 4.5) {
      // camisa: en V amb corbata, o coll obert
      o += `<path d="M${f(X - tw * 0.15)} ${f(Y - th)}L${f(X)} ${f(Y - th * (tie ? 0.4 : 0.6))}L${f(X + tw * 0.15)} ${f(Y - th)}Z" fill="${tie ? fog('#f4f1ea') : skin}"/>`;
      if (tie) o += `<path d="M${f(X)} ${f(Y - th * 0.94)}l${f(-tw * 0.045)} ${f(th * 0.36)}l${f(tw * 0.045)} ${f(th * 0.13)}l${f(tw * 0.045)} ${f(-th * 0.13)}Z" fill="${fog(dim(g.c, 0.45))}"/>`;
      // solapes
      o += `<path d="M${f(X - tw * 0.16)} ${f(Y - th * 0.99)}L${f(X - tw * 0.03)} ${f(Y - th * 0.38)}M${f(X + tw * 0.16)} ${f(Y - th * 0.99)}L${f(X + tw * 0.03)} ${f(Y - th * 0.38)}" stroke="${dim(body, 0.4)}" stroke-width="${f(w * 0.035)}" fill="none"/>`;
    }
    // coll i cap: uns miren endavant, d'altres es giren cap al del costat
    X += (hash(k + 51) - 0.5) * hr * 0.55;
    if (w > 3) o += `<rect x="${f(X - hr * 0.42)}" y="${f(hy + ry * 0.6)}" width="${f(hr * 0.84)}" height="${f(Y - th - hy - ry * 0.55)}" fill="${dim(skin, 0.18)}"/>`;
    if (w > 6) o += `<circle cx="${f(X - hr * 0.98)}" cy="${f(hy + ry * 0.08)}" r="${f(hr * 0.2)}" fill="${skin}"/><circle cx="${f(X + hr * 0.98)}" cy="${f(hy + ry * 0.08)}" r="${f(hr * 0.2)}" fill="${dim(skin, 0.12)}"/>`;
    o += `<ellipse cx="${f(X)}" cy="${f(hy)}" rx="${f(hr)}" ry="${f(ry)}" fill="${skin}"/>`;
    if (w > 4) o += `<path d="M${f(X + hr * 0.1)} ${f(hy - ry)}A${f(hr)} ${f(ry)} 0 0 1 ${f(X + hr * 0.1)} ${f(hy + ry)}Q${f(X + hr * 0.55)} ${f(hy)} ${f(X + hr * 0.1)} ${f(hy - ry)}Z" fill="#000" opacity=".13"/>`;
    // cabell
    if (w > 3.5) {
      const R = hr * 1.04, top = hy - ry * 1.04;
      if (style === 4) {
        o += `<path d="M${f(X - R)} ${f(hy + ry * 0.1)}q${f(R * 0.05)} ${f(-ry * 0.45)} ${f(R * 0.3)} ${f(-ry * 0.55)}M${f(X + R)} ${f(hy + ry * 0.1)}q${f(-R * 0.05)} ${f(-ry * 0.45)} ${f(-R * 0.3)} ${f(-ry * 0.55)}" stroke="${hair}" stroke-width="${f(hr * 0.28)}" fill="none" stroke-linecap="round"/>` +
             (w > 6 ? `<ellipse cx="${f(X - hr * 0.3)}" cy="${f(hy - ry * 0.62)}" rx="${f(hr * 0.25)}" ry="${f(ry * 0.12)}" fill="#fff" opacity=".3"/>` : '');
      } else if (style === 2) {
        o += `<path d="M${f(X - R)} ${f(hy - ry * 0.05)}A${f(R)} ${f(ry * 1.04)} 0 0 1 ${f(X + R)} ${f(hy - ry * 0.05)}Q${f(X + R * 0.2)} ${f(hy - ry * 0.75)} ${f(X - R * 0.35)} ${f(hy - ry * 0.55)}Q${f(X - R * 0.8)} ${f(hy - ry * 0.4)} ${f(X - R)} ${f(hy - ry * 0.05)}Z" fill="${hair}"/>`;
      } else if (style === 3 || style === 5) {
        o += `<path d="M${f(X - R * 1.06)} ${f(hy + ry * 0.5)}A${f(R * 1.06)} ${f(ry * 1.08)} 0 0 1 ${f(X + R * 1.06)} ${f(hy + ry * 0.5)}Q${f(X + R * 0.75)} ${f(hy - ry * 0.35)} ${f(X + R * 0.1)} ${f(hy - ry * 0.62)}Q${f(X - R * 0.6)} ${f(hy - ry * 0.3)} ${f(X - R * 0.8)} ${f(hy + ry * 0.5)}Z" fill="${hair}"/>`;
      } else {
        o += `<path d="M${f(X - R)} ${f(hy)}A${f(R)} ${f(ry * 1.04)} 0 0 1 ${f(X + R)} ${f(hy)}Q${f(X + R * 0.6)} ${f(hy - ry * 0.6)} ${f(X)} ${f(hy - ry * 0.55)}Q${f(X - R * 0.6)} ${f(hy - ry * 0.6)} ${f(X - R)} ${f(hy)}Z" fill="${hair}"/>`;
      }
      if (w > 6 && style !== 4) o += `<path d="M${f(X - R * 0.6)} ${f(top + ry * 0.25)}q${f(R * 0.4)} ${f(-ry * 0.2)} ${f(R * 0.8)} ${f(-ry * 0.05)}" stroke="#fff" stroke-opacity=".18" stroke-width="${f(hr * 0.15)}" fill="none"/>`;
    }
    // cara, nomes de prop
    if (w > 9) {
      const ey = hy + ry * 0.08, er = hr * 0.085;
      o += `<circle cx="${f(X - hr * 0.36)}" cy="${f(ey)}" r="${f(er)}" fill="#2a1d14"/><circle cx="${f(X + hr * 0.36)}" cy="${f(ey)}" r="${f(er)}" fill="#2a1d14"/>` +
           `<path d="M${f(X - hr * 0.22)} ${f(hy + ry * 0.55)}q${f(hr * 0.22)} ${f(ry * 0.1)} ${f(hr * 0.44)} 0" stroke="${dim(skin, 0.35)}" stroke-width="${f(hr * 0.07)}" fill="none"/>`;
      if (h3 > 0.78) o += `<path d="M${f(X - hr * 0.62)} ${f(ey)}a${f(hr * 0.24)} ${f(hr * 0.2)} 0 1 0 ${f(hr * 0.48)} 0a${f(hr * 0.24)} ${f(hr * 0.2)} 0 1 0 ${f(-hr * 0.48)} 0M${f(X + hr * 0.14)} ${f(ey)}a${f(hr * 0.24)} ${f(hr * 0.2)} 0 1 0 ${f(hr * 0.48)} 0a${f(hr * 0.24)} ${f(hr * 0.2)} 0 1 0 ${f(-hr * 0.48)} 0M${f(X - hr * 0.14)} ${f(ey)}h${f(hr * 0.28)}" stroke="#222" stroke-width="${f(hr * 0.06)}" fill="none"/>`;
    }
    return o + '</g>';
  }
  // El que hi ha damunt de l'escó: les mans, i papers, una tauleta o un got.
  function deskStuff(X, Y, w, g, k, n, hz, PX, PY) {
    const fog = (c) => (hz ? mix(c, HAZE, hz) : c);
    const r = hash(k + 31);
    let o = '';
    if (r < 0.32) o += `<path d="M${f(X - w * 0.42)} ${f(Y + w * 0.01)}l${f(w * 0.3)} ${f(-w * 0.02)}l${f(w * 0.02)} ${f(-w * 0.11)}l${f(-w * 0.3)} ${f(w * 0.02)}Z" fill="${fog('#f7f5ef')}" opacity=".95"/>`;
    else if (r < 0.46) o += `<path d="M${f(X + w * 0.08)} ${f(Y + w * 0.01)}h${f(w * 0.34)}l${f(-w * 0.03)} ${f(-w * 0.12)}h${f(-w * 0.28)}Z" fill="#1d2026"/>` +
                          `<path d="M${f(X + w * 0.12)} ${f(Y - w * 0.01)}h${f(w * 0.26)}l${f(-w * 0.02)} ${f(-w * 0.08)}h${f(-w * 0.22)}Z" fill="${fog('#8fb4e6')}" opacity=".85"/>`;
    if (r > 0.9) o += `<rect x="${f(X + w * 0.36)}" y="${f(Y - w * 0.16)}" width="${f(w * 0.07)}" height="${f(w * 0.14)}" fill="#dfefff" opacity=".55"/>`;
    if (w > 5) {
      // les mans entren amb el diputat
      const s = Math.min(0.999, (k / n) * 0.9 + hash(k + 3) * 0.1);
      const sl = fog(dim(g.c, 0.15)), sk = fog(SKIN[Math.floor(hash(k) * SKIN.length)]);
      o += `<g class="mp" style="--s:${s.toFixed(3)}">`;
      const tw = w * 0.92, th = w * 0.8;
      const hx = PX == null ? X : PX;
      for (const sg of [-1, 1]) {
        // mans damunt del faristol, just davant del cos; el braç ve de l'espatlla
        const ax = hx + sg * w * (0.22 + hash(k + 61 + sg) * 0.08), ay = Y - w * 0.035;
        if (PY != null && PY - th * 0.62 < ay) {
          o += `<path d="M${f(hx + sg * tw * 0.4)} ${f(PY - th * 0.6)}Q${f(hx + sg * tw * 0.47)} ${f((PY + ay) / 2)} ${f(ax)} ${f(ay)}" fill="none" stroke="${sl}" stroke-width="${f(w * 0.17)}" stroke-linecap="round"/>`;
        }
        o += `<ellipse cx="${f(ax - sg * w * 0.07)}" cy="${f(ay - w * 0.005)}" rx="${f(w * 0.07)}" ry="${f(w * 0.045)}" fill="${sk}"/>`;
      }
      o += '</g>';
    }
    return o;
  }
  // Cadira buida: respatller de vellut (o de pell, a la primera fila).
  const chair = (X, Y, w, hh, u, front) =>
    `<rect x="${f(X - w / 2)}" y="${f(Y - hh)}" width="${f(w)}" height="${f(hh)}" rx="${f(w * 0.3)}" fill="url(#${u}${front ? 'lea' : 'vel'})"/>` +
    (w > 4 ? `<path d="M${f(X - w * 0.3)} ${f(Y - hh * 0.8)}h${f(w * 0.6)}" stroke="#fff" stroke-opacity=".18" stroke-width="${f(w * 0.08)}"/>` : '');

  function hemiRoom(groups, lay, st, ca, u) {
    const seats = groups.reduce((a, g) => a + g.s, 0);
    const span = lay === 'fan' ? PI * 0.72 : PI, arm = lay === 'horse' ? 0.36 : 0;
    const A = seats < 40 ? 0 : lay === 'fan' ? 2 : seats >= 300 ? 4 : seats >= 120 ? 3 : 2, HA = 0.03;
    const L = arcLayout(seats, span, arm, A, HA);
    let dmin = Infinity;
    for (const p of L.pts) dmin = Math.min(dmin, p.d);
    // Com un fotògraf a la tribuna de premsa, darrere i per damunt de la
    // presidència: amb la càmera tan a prop, els extrems de les files
    // s'obrien cap als racons i la sala semblava un rombe.
    const c = 0.8 + arm - Math.max(0, dmin) * 0.5, H = 1.1;
    const zr = (r) => 0.06 + 0.34 * (r - L.r0) / (1 - L.r0);
    let m = 0;
    for (const p of L.pts) m = Math.max(m, Math.abs(p.x) / (p.d + c));
    const F = 168 / m, zTop = zr(1);
    const Yh = 108 - (H - zTop) * F / (1 + c);
    const P3 = cam(c, H, F, Yh);
    const gap = L.rows > 1 ? (1 - L.r0) / (L.rows - 1) : 0.12;
    const RW = 1 + gap * 0.9;
    let o = '', glow = '';
    const band = (r, z0, z1, fill, n, extra) =>
      shape(rowCurve(P3, r, z0, PI, 0, n || 64).concat(rowCurve(P3, r, z1, PI, 0, n || 64).reverse()), fill, extra);
    const at = (t, r, z) => P3(r * Math.cos(t), r * Math.sin(t), z);

    // Sostre: lluernari (Congres), cupula de vidre (Bundestag) o fusteria fosca.
    o += `<rect width="360" height="300" fill="${dim(st.upper, 0.55)}"/>`;
    const topCurve = rowCurve(P3, RW, 1.55, PI, 0, 64);
    if (st.sky || st.dome) {
      const VP = [180, -90];
      o += shape(topCurve.concat([[400, -20], [-40, -20]]), `url(#${u}${st.dome ? 'glass' : 'sky'})`);
      let d = '';
      for (let k = 0; k <= 64; k += 4) { const p = topCurve[k]; d += `M${f(p[0])} ${f(p[1])}L${f(p[0] + (VP[0] - p[0]) * 0.75)} ${f(p[1] + (VP[1] - p[1]) * 0.75)}`; }
      for (const q of [1.75, 2.05, 2.5]) d += 'M' + pts2(rowCurve(P3, RW * 0.97, q, PI, 0, 48));
      // vitrall emplomat (lluernari) o vidre de la cupula
      o += shape(topCurve.concat([[400, -20], [-40, -20]]), `url(#${u}lead)`, ' opacity=".8"');
      o += `<path d="${d}" fill="none" stroke="${st.dome ? '#7f95b3' : dim(st.gold, 0.25)}" stroke-width=".7" opacity=".8"/>`;
      if (st.sky) o += `<path d="${d}" fill="none" stroke="#fff" stroke-width=".25" opacity=".6"/>`;
    }
    // Paret i cornisa.
    o += band(RW, zTop - 0.03, 1.55, `url(#${u}wall)`);
    o += band(RW * 0.995, 1.5, 1.58, `url(#${u}gold)`, 64, ' opacity=".9"');
    o += stroke(rowCurve(P3, RW * 0.99, 1.47, PI, 0, 64), dim(st.upper, 0.3), 0.6);
    // Tribuna alta.
    if (st.gal2) {
      // La galeria alta: un fons a l'ombra amb seients i alguna persona,
      // pilars entre els trams i la barana.
      o += band(RW * 1.01, 1.2, 1.42, dim(st.upper, 0.7));
      o += band(RW * 1.01, 1.36, 1.42, `url(#${u}rec)`);
      for (const zz of [1.24, 1.3, 1.36]) {
        let d = '', ppl = '';
        for (let k = 1; k < 66; k++) {
          const [X, Y, s] = at(PI * (0.03 + 0.94 * k / 66), RW + (zz - 1.2) * 0.4, zz);
          d += `M${f(X - s * 0.011)} ${f(Y)}h${f(s * 0.022)}v${f(-s * 0.026)}q0 ${f(-s * 0.008)} ${f(-s * 0.011)} ${f(-s * 0.008)}q${f(-s * 0.011)} 0 ${f(-s * 0.011)} ${f(s * 0.008)}Z`;
          if (hash(k * 7 + zz * 100) < 0.42) ppl += `M${f(X - s * 0.01)} ${f(Y - s * 0.004)}v${f(-s * 0.018)}q${f(s * 0.01)} ${f(-s * 0.008)} ${f(s * 0.02)} 0v${f(s * 0.018)}ZM${f(X + s * 0.007)} ${f(Y - s * 0.03)}a${f(s * 0.007)} ${f(s * 0.007)} 0 1 0 ${f(-s * 0.014)} 0a${f(s * 0.007)} ${f(s * 0.007)} 0 1 0 ${f(s * 0.014)} 0Z`;
        }
        o += `<path d="${d}" fill="${dim(st.seat, 0.25)}"/>` + (ppl ? `<path d="${ppl}" fill="#3a3530" opacity=".85"/>` : '');
      }
      let pier = '';
      for (let k = 0; k <= 12; k++) {
        const t = PI * (0.02 + 0.96 * k / 12), a = at(t - 0.012, RW * 1.0, 1.2), b = at(t + 0.012, RW * 1.0, 1.42);
        pier += `M${f(a[0])} ${f(a[1])}H${f(b[0])}V${f(b[1])}H${f(a[0])}Z`;
      }
      o += `<path d="${pier}" fill="${st.upper}"/>`;
      o += band(RW * 0.985, 1.16, 1.2, dim(st.wood, 0.2));
      o += stroke(rowCurve(P3, RW * 0.985, 1.2, PI, 0, 64), `url(#${u}gold)`, 1.4);
    }
    // Apliques entre columnes: s'encenen els primers, a les fosques.
    const ncol = st.cols || 0;
    if (st.lamps) {
      const nl = Math.max(4, ncol + 1);
      for (let k = 0; k < nl; k++) {
        const t = PI * (0.1 + 0.8 * (k + 0.5) / nl);
        const [X, Y, s] = at(t, RW * 0.99, 1.05);
        o += `<path d="M${f(X)} ${f(Y + s * 0.03)}v${f(-s * 0.03)}m${f(-s * 0.02)} 0h${f(s * 0.04)}" stroke="url(#${u}gold)" stroke-width="${f(Math.max(0.6, s * 0.006))}"/>` +
             `<circle cx="${f(X)}" cy="${f(Y - s * 0.012)}" r="${f(s * 0.011)}" fill="#fff4cf"/>`;
        glow += `<circle class="gw" style="--i:${k}" cx="${f(X)}" cy="${f(Y - s * 0.012)}" r="${f(s * 0.09)}" fill="url(#${u}glow)"/>`;
      }
    }
    // Tribuna de convidats: dues files de cadires i la barana daurada.
    // el fons de la tribuna, a l'ombra: sense, les cadires semblen penjades a la paret
    o += band(RW + 0.08, 0.76, 0.99, dim(st.upper, 0.5)) + band(RW + 0.08, 0.93, 0.99, `url(#${u}rec)`);
    for (const [rr, zz] of [[RW + 0.03, 0.8], [RW + 0.06, 0.88]]) {
      let d = '', ppl = '';
      for (let k = 1; k < 38; k++) {
        const [X, Y, s] = at(PI * (0.05 + 0.9 * k / 38), rr, zz);
        d += `M${f(X - s * 0.014)} ${f(Y)}v${f(-s * 0.03)}q0 ${f(-s * 0.012)} ${f(s * 0.014)} ${f(-s * 0.012)}q${f(s * 0.014)} 0 ${f(s * 0.014)} ${f(s * 0.012)}v${f(s * 0.03)}Z`;
        // public i premsa: un de cada tres seients ocupat
        if (hash(k * 13 + zz * 50) < 0.34) {
          const c = ['#2d2f36', '#4a4038', '#6b6f78', '#7a2f2f', '#2f4a6b'][Math.floor(hash(k + zz * 9) * 5)];
          ppl += `<path d="M${f(X - s * 0.013)} ${f(Y - s * 0.006)}v${f(-s * 0.022)}q${f(s * 0.013)} ${f(-s * 0.01)} ${f(s * 0.026)} 0v${f(s * 0.022)}Z" fill="${c}"/>` +
                 `<circle cx="${f(X)}" cy="${f(Y - s * 0.039)}" r="${f(s * 0.008)}" fill="${SKIN[Math.floor(hash(k * 3 + zz) * SKIN.length)]}"/>`;
        }
      }
      o += `<path d="${d}" fill="url(#${u}vel)"/>` + ppl;
    }
    const RR = RW - 0.02;
    // Barana de la tribuna: plafons de fusta amb motllura daurada entre
    // pilastres i, a dalt, el passamà entapissat; a les sales modernes, vidre.
    const quad = (t0, t1, r, z0, z1) => [at(t0, r, z0), at(t1, r, z0), at(t1, r, z1), at(t0, r, z1)];
    if (st.dome) {
      o += band(RR, 0.66, 0.77, '#dcebf5', 64, ' opacity=".35"') +
           stroke(rowCurve(P3, RR, 0.77, PI, 0, 64), '#8f9aa6', 1.6) +
           stroke(rowCurve(P3, RR, 0.66, PI, 0, 64), '#8f9aa6', 0.8);
      let d = '';
      for (let k = 0; k <= 36; k++) { const a = at(PI * k / 36, RR, 0.66), b = at(PI * k / 36, RR, 0.77); d += `M${f(a[0])} ${f(a[1])}L${f(b[0])} ${f(b[1])}`; }
      o += `<path d="${d}" stroke="#8f9aa6" stroke-width=".5" opacity=".7"/>`;
    } else {
      o += band(RR, 0.655, 0.77, `url(#${u}wood)`);
      const n = 30, pw = PI / n;
      let pil = '', mold = '', inner = '';
      for (let k = 0; k < n; k++) {
        const t0 = PI * k / n, t1 = t0 + pw, e = pw * 0.07;
        pil += shape(quad(t0 - e, t0 + e, RR * 1.002, 0.655, 0.77), dim(st.wood, 0.3));
        const q1 = quad(t0 + e * 2.2, t1 - e * 2.2, RR, 0.672, 0.752), q2 = quad(t0 + e * 3.6, t1 - e * 3.6, RR, 0.684, 0.74);
        mold += 'M' + pts2(q1) + 'Z';
        inner += 'M' + pts2(q2) + 'Z';
      }
      o += pil + `<path d="${inner}" fill="${dim(st.wood, 0.18)}"/>` +
           `<path d="${mold}" fill="none" stroke="url(#${u}gold)" stroke-width=".9"/>` +
           `<path d="${inner}" fill="none" stroke="${lite(st.gold, 0.2)}" stroke-width=".4" opacity=".8"/>`;
      // passamà de vellut
      o += band(RR * 1.004, 0.77, 0.792, `url(#${u}vel)`) +
           stroke(rowCurve(P3, RR * 1.004, 0.792, PI, 0, 64), lite(st.seat, 0.35), 0.6, ' opacity=".7"');
    }
    o += stroke(rowCurve(P3, RR, 0.77, PI, 0, 64), `url(#${u}gold)`, 1.4) +
         stroke(rowCurve(P3, RR, 0.655, PI, 0, 64), `url(#${u}gold)`, 1.2) +
         stroke(rowCurve(P3, RR, 0.64, PI, 0, 64), '#000', 1.6, ' opacity=".25"');
    // Columnes estriades, amb capitell i base.
    for (let k = 0; k < ncol; k++) {
      const t = PI * (0.14 + 0.72 * k / Math.max(1, ncol - 1));
      const q = (dx, z) => { const [x, d] = [(RW - 0.04) * Math.cos(t), (RW - 0.04) * Math.sin(t)]; return P3(x + dx, d, z); };
      const wC = 0.032;
      for (const [z0, z1] of [[zTop - 0.02, 0.645], [0.78, 1.47]]) {
        o += shape([q(-wC, z0), q(wC, z0), q(wC, z1), q(-wC, z1)], `url(#${u}col)`);
        let d = '';
        for (const fx of [-0.5, 0, 0.5]) { const a = q(wC * fx, z0 + 0.02), b = q(wC * fx, z1 - 0.03); d += `M${f(a[0])} ${f(a[1])}L${f(b[0])} ${f(b[1])}`; }
        o += `<path d="${d}" stroke="#000" stroke-opacity=".22" stroke-width=".5"/>`;
        o += shape([q(-wC * 1.45, z1 - 0.025), q(wC * 1.45, z1 - 0.025), q(wC * 1.45, z1), q(-wC * 1.45, z1)], `url(#${u}gold)`);
        o += shape([q(-wC * 1.3, z0), q(wC * 1.3, z0), q(wC * 1.3, z0 + 0.02), q(-wC * 1.3, z0 + 0.02)], dim(st.colc || st.dark, 0.2));
      }
    }
    // Cortinatge amb plecs, sanefa i rellotge.
    if (st.curtain) {
      const q = (x, z) => P3(x, RW + 0.02, z);
      const [a] = q(-0.12, 1), [b] = q(0.12, 1);
      const [, yt] = q(0, 1.4), [, yb] = q(0, 0.78), [, yv] = q(0, 1.1);
      const w = b - a, mid = (a + b) / 2;
      o += `<rect x="${f(a)}" y="${f(yt)}" width="${f(w)}" height="${f(yb - yt)}" fill="${dim(st.curtain, 0.55)}"/>` +
           `<path d="M${f(a)} ${f(yt)}H${f(mid - 1.5)}V${f(yv)}Q${f(a + w * 0.1)} ${f(yv + 2)} ${f(a)} ${f(yb)}Z" fill="url(#${u}cur)"/>` +
           `<path d="M${f(b)} ${f(yt)}H${f(mid + 1.5)}V${f(yv)}Q${f(b - w * 0.1)} ${f(yv + 2)} ${f(b)} ${f(yb)}Z" fill="url(#${u}cur)"/>`;
      const vh = (yb - yt) * 0.15;
      let fr = '';
      for (let k = 0; k <= 12; k++) fr += `M${f(a - 3 + (w + 6) * k / 12)} ${f(yt + vh)}v2.2`;
      o += `<path d="M${f(a - 3)} ${f(yt)}H${f(b + 3)}v${f(vh)}q${f(-(w + 6) / 6)} 4 ${f(-(w + 6) / 3)} 0q${f(-(w + 6) / 6)} 4 ${f(-(w + 6) / 3)} 0q${f(-(w + 6) / 6)} 4 ${f(-(w + 6) / 3)} 0Z" fill="url(#${u}cur)"/>` +
           `<path d="${fr}" stroke="url(#${u}gold)" stroke-width=".9"/>` +
           `<circle cx="${f(a + w * 0.08)}" cy="${f(yv + (yb - yv) * 0.3)}" r="1.1" fill="url(#${u}gold)"/><circle cx="${f(b - w * 0.08)}" cy="${f(yv + (yb - yv) * 0.3)}" r="1.1" fill="url(#${u}gold)"/>`;
    }
    if (st.clock) {
      const [X, Y, s] = P3(0, RR - 0.01, 0.715), R = s * 0.045;
      let ticks = '';
      for (let k = 0; k < 12; k++) { const t = k * PI / 6; ticks += `M${f(X + Math.cos(t) * R * 0.78)} ${f(Y + Math.sin(t) * R * 0.78)}L${f(X + Math.cos(t) * R * 0.92)} ${f(Y + Math.sin(t) * R * 0.92)}`; }
      o += `<circle cx="${f(X)}" cy="${f(Y)}" r="${f(R * 1.18)}" fill="url(#${u}gold)"/><circle cx="${f(X)}" cy="${f(Y)}" r="${f(R)}" fill="#f6f1e3"/>` +
           `<path d="${ticks}" stroke="#333" stroke-width=".4"/>` +
           `<path class="hand" d="M${f(X)} ${f(Y)}V${f(Y - R * 0.62)}" stroke="#1a1a1a" stroke-width=".8" stroke-linecap="round"/>` +
           `<path d="M${f(X)} ${f(Y)}H${f(X + R * 0.45)}" stroke="#1a1a1a" stroke-width=".9" stroke-linecap="round"/>`;
    }

    // Graderia i terra: la massa de fusta sota les files i la catifa.
    o += shape(rowCurve(P3, 1 + gap * 0.55, zTop, span, arm, 64)
      .concat(rowCurve(P3, L.r0 - gap * 0.6, 0, span, arm, 64).reverse()), dim(st.dark, 0.15));
    const floor = rowCurve(P3, L.r0 - gap * 0.6, 0, span, arm, 64);
    o += shape(floor, `url(#${u}carpet)`) +
         stroke(rowCurve(P3, L.r0 - gap * 0.75, 0, span, arm, 64), `url(#${u}gold)`, 1) +
         stroke(rowCurve(P3, (L.r0 - gap * 0.6) * 0.55, 0, span, arm, 48), lite(st.floor, 0.25), 0.8, ' opacity=".6"');

    // On s'acaben les files (als costats, a tocar de la presidència), la
    // graderia es tanca amb un frontal esglaonat de fusta. Sense, els
    // racons de baix quedaven buits.
    if (span > PI - 0.01) {
      const dE = -arm + 0.002;
      for (const sg of [-1, 1]) {
        const pts = [P3(sg * (L.r0 - gap * 0.6), dE, 0)];
        let nose = [];
        L.radii.forEach((r, i) => {
          const z = zr(r), zi = i ? zr(L.radii[i - 1]) : 0;
          pts.push(P3(sg * (r - gap * 0.5), dE, zi), P3(sg * (r - gap * 0.5), dE, z));
          nose.push(P3(sg * (r - gap * 0.5), dE, zi), P3(sg * (r - gap * 0.5), dE, z), P3(sg * (r + gap * 0.5), dE, z));
        });
        pts.push(P3(sg * (1 + gap * 0.55), dE, zTop), P3(sg * RW * 1.4, dE, zTop), P3(sg * RW * 1.4, dE, 0));
        o += shape(pts, `url(#${u}wood)`) + shape(pts, '#000', ' opacity=".18"') + stroke(nose, lite(st.wood, 0.3), 0.8);
        // plafons
        let d = '';
        L.radii.forEach((r, i) => {
          const z = zr(r);
          const a = P3(sg * (r - gap * 0.38), dE, z * 0.15), b = P3(sg * (r + gap * 0.38), dE, Math.max(0.01, z - 0.03));
          d += `M${f(a[0])} ${f(a[1])}H${f(b[0])}V${f(b[1])}H${f(a[0])}Z`;
        });
        o += `<path d="${d}" fill="none" stroke="${dim(st.wood, 0.45)}" stroke-width=".6"/>`;
      }
    }

    // Qui seu on: d'esquerra a dreta, partit per partit.
    const order = L.pts.map((p, i) => ({ ...p, i })).sort((a, b) => a.u - b.u || a.r - b.r);
    const rank = new Map(order.map((p, k) => [p.i, k]));
    const owner = new Map();
    let gi = 0, left = groups[0].s;
    for (const p of order) {
      while (left <= 0 && gi < groups.length - 1) { gi++; left = groups[gi].s; }
      owner.set(p.i, groups[gi]); left--;
    }

    // Files, de la de fora a la de dins: cada una tapa la base de l'anterior.
    for (let row = L.rows - 1; row >= 0; row--) {
      const r = L.radii[row], z = zr(r), G0 = L.geoms[row];
      const zIn = row > 0 ? zr(L.radii[row - 1]) : 0;
      let rs = '';
      // Escales: graons entre sectors.
      for (let k = 1; k <= A; k++) {
        const sc = G0.aisle(k), ang = (sc - arm) / r;
        const t = PI / 2 + span / 2 - ang, h = HA * 0.92;
        const p = (rr, tt, zz) => at(tt, rr, zz);
        const rIn = r - gap * 0.5, rOut = r + gap * 0.5;
        rs += shape([p(rIn, t - h, z), p(rIn, t + h, z), p(rOut, t + h, z), p(rOut, t - h, z)], `url(#${u}stair)`) +
              shape([p(rIn, t - h, zIn), p(rIn, t + h, zIn), p(rIn, t + h, z), p(rIn, t - h, z)], dim(st.stair || st.floor, 0.35)) +
              stroke([p(rIn, t - h, z), p(rIn, t + h, z)], lite(st.stair || st.floor, 0.3), 0.6);
      }
      // Cadires i diputats, del fons cap endavant.
      const inRow = order.filter((p) => p.row === row).sort((a, b) => b.d - a.d);
      // Alçada del faristol: proporcional a la mida dels diputats d'aquesta
      // fila, perquè sempre els tapi fins a mig cos.
      const DT = Math.min(0.045, 0.6 * (inRow.length ? inRow[0].sp : 0.07));
      // Les files del fons es perden una mica en l'aire de la sala.
      const hz = L.rows > 1 ? 0.16 * row / (L.rows - 1) : 0;
      const wOf = new Map();
      for (const p of inRow) {
        const [X, Y, s] = P3(p.x, p.d, z + 0.012);
        const w = Math.max(1.4, p.sp * s * 0.86), hh = Math.max(1.5, w * 1.18);
        wOf.set(p.i, [w, X, Y - w * 0.12]);
        rs += chair(X, Y, w * 1.16, hh, u, row === 0 && st.front);
        rs += person(X, Y - w * 0.12, w, owner.get(p.i), rank.get(p.i), seats, ca, hz);
      }
      // Faristols: tapa clara, frontal amb plafons, i micros.
      const rd = r - gap * 0.3;
      for (let j = 0; j <= A; j++) {
        const [s0, s1] = G0.range(j);
        const k0 = s0 * rd / r, k1 = s1 * rd / r;
        const nn = Math.max(6, Math.round((s1 - s0) * 24));
        const topF = rowCurve(P3, rd, z + DT, span, arm, nn, k0, k1);
        const topB = rowCurve(P3, rd + gap * 0.13, z + DT, span, arm, nn, k0, k1);
        const bot = rowCurve(P3, rd, z - 0.035, span, arm, nn, k0, k1);
        rs += shape(topF.concat(topB.slice().reverse()), `url(#${u}top)`) +
              shape(topF.concat(bot.slice().reverse()), `url(#${u}wood)`) +
              stroke(topF, lite(st.wood, 0.45), 0.5);
      }
      let pan = '', mic = '';
      for (const p of inRow) {
        const sx = p.s * rd / r;
        const [tx, ty] = rowXY(rd, sx + p.sp * 0.5 * rd / r, span, arm);
        const A1 = P3(tx, ty, z + DT - 0.007), B1 = P3(tx, ty, z - 0.025);
        if (A1[2] * p.sp > 9) pan += `M${f(A1[0])} ${f(A1[1])}L${f(B1[0])} ${f(B1[1])}`;
        const [mx, my] = rowXY(rd + gap * 0.08, sx, span, arm);
        const M0 = P3(mx, my, z + DT), sm = M0[2];
        if (sm * p.sp > 10) mic += `M${f(M0[0])} ${f(M0[1])}q${f(sm * 0.006)} ${f(-sm * 0.03)} ${f(sm * 0.016)} ${f(-sm * 0.045)}`;
      }
      if (pan) rs += `<path d="${pan}" stroke="${dim(st.wood, 0.5)}" stroke-width=".5" opacity=".7"/>`;
      // Ombra que fa el faristol sobre la grada de sota.
      const sh = rowCurve(P3, rd, z - 0.04, span, arm, 64);
      rs += stroke(sh, '#000', 2.6, ' opacity=".14"') + stroke(sh, '#000', 1.1, ' opacity=".2"');
      // Mans, papers, tauletes i gots damunt del faristol.
      const rt = rd + gap * 0.06;
      for (const p of inRow) {
        const [tx, ty] = rowXY(rt, p.s * rt / r, span, arm);
        const [, Y] = P3(tx, ty, z + DT);
        const [pw, PX, PY] = wOf.get(p.i);
        if (PY - pw * 0.8 * 0.62 < Y) rs += deskStuff(PX, Y, pw, owner.get(p.i), rank.get(p.i), seats, hz, PX, PY);
      }
      if (mic) rs += `<path d="${mic}" fill="none" stroke="#222" stroke-width=".6" stroke-linecap="round"/>`;
      if (hz > 0.02) {
        const top = rowCurve(P3, r + gap * 0.25, z + 0.09, span, arm, 64);
        const bot = rowCurve(P3, rd, z - 0.04, span, arm, 64);
        rs += shape(top.concat(bot.reverse()), HAZE, ` opacity="${(hz * 0.35).toFixed(3)}"`);
      }
      o += rs;
    }

    // Raigs de llum que baixen del lluernari o de la cupula, d'esquerra a dreta.
    if (st.sky || st.dome) {
      const y0 = P3(0, RW, 1.5)[1], y1 = P3(0, L.r0, 0)[1];
      let rays = '';
      for (const [x, w, dx] of [[118, 16, 46], [158, 10, 52], [196, 20, 60], [238, 12, 66]]) {
        rays += `<path d="M${x} ${f(y0)}h${w}L${x + w + dx + w * 1.6} ${f(y1)}H${x + dx - w * 0.6}Z" fill="url(#${u}ray)"/>`;
      }
      o += `<g class="rays" opacity=".85">${rays}</g>`;
    }

    // Tribuna d'oradors i taula dels taquigrafs, al davant.
    const box = (x0, x1, d0, d1, z0, z1, fill, topFill) => {
      const a = P3(x0, d0, z0), b = P3(x1, d0, z0), cc = P3(x1, d0, z1), dd = P3(x0, d0, z1);
      const e = P3(x1, d1, z1), g = P3(x0, d1, z1);
      return shape([dd, cc, e, g], topFill || `url(#${u}top)`) + shape([a, b, cc, dd], fill, ` stroke="${dim(st.gold, 0.2)}" stroke-width=".6"`);
    };
    o += box(-0.2, 0.2, 0.22, 0.3, 0, 0.07, `url(#${u}wood)`);
    {
      const [lx, ly, ls] = P3(-0.12, 0.26, 0.07);
      o += `<path d="M${f(lx)} ${f(ly)}v${f(-ls * 0.05)}" stroke="url(#${u}gold)" stroke-width="${f(ls * 0.008)}"/>` +
           `<path d="M${f(lx - ls * 0.02)} ${f(ly - ls * 0.05)}h${f(ls * 0.04)}l${f(-ls * 0.008)} ${f(-ls * 0.018)}h${f(-ls * 0.024)}Z" fill="#2d6b46"/>`;
      glow += `<circle class="gw" style="--i:9" cx="${f(lx)}" cy="${f(ly - ls * 0.04)}" r="${f(ls * 0.06)}" fill="url(#${u}glow)"/>`;
    }
    o += box(-0.085, 0.085, 0.07, 0.13, 0, 0.17, `url(#${u}wood)`);
    {
      const a = P3(-0.06, 0.068, 0.04), b = P3(0.06, 0.068, 0.15);
      o += `<rect x="${f(a[0])}" y="${f(b[1])}" width="${f(b[0] - a[0])}" height="${f(a[1] - b[1])}" fill="none" stroke="url(#${u}gold)" stroke-width=".8" rx="1"/>`;
      const [mx, my, ms] = P3(0, 0.1, 0.17);
      o += `<path d="M${f(mx)} ${f(my)}q${f(ms * 0.01)} ${f(-ms * 0.04)} ${f(ms * 0.03)} ${f(-ms * 0.06)}" fill="none" stroke="#222" stroke-width="1"/>`;
    }
    // Ratlla de la majoria: el seient del mig.
    const [mx0, my0] = P3(0, L.r0 - gap * 0.4, zr(L.r0)), [mx1, my1] = P3(0, 1 + gap * 0.3, zTop + 0.06);
    o += `<path class="mj" d="M${f(mx0)} ${f(my0)}L${f(mx1)} ${f(my1)}"/>`;
    const [, yb] = P3(0, 0, 0);
    return { svg: o, glow, h: Math.ceil(Math.min(300, yb + 4)) };
  }

  // Westminster: des de la cadira del Speaker, mirant el passadis; a cada
  // costat, bancs de pell verda enfrontats que pugen cap enfora.
  function westRoom(groups, st, ca, u) {
    const seats = groups.reduce((a, g) => a + g.s, 0);
    let best = 1, diff = Infinity, acc = 0;
    for (let i = 0; i < groups.length - 1; i++) {
      acc += groups[i].s;
      const dd = Math.abs(acc - (seats - acc));
      if (dd < diff) { diff = dd; best = i + 1; }
    }
    const sides = [groups.slice(0, best), groups.slice(best)];
    const big = Math.max(...sides.map((s) => s.reduce((a, g) => a + g.s, 0)));
    const rows = Math.max(2, Math.min(7, Math.round(Math.sqrt(big / 12))));
    const ncol = Math.ceil(big / rows);
    const d0 = 0.22, D = 1.7, dd = D / ncol, c = 0.32, H = 0.62;
    const xr = (k) => 0.17 + k * 0.1, zr = (k) => 0.05 + k * 0.075;
    const xo = xr(rows) + 0.06;
    const F = 172 * (d0 + c) / xo;
    const P3 = cam(c, H, F, 72);
    const q = P3;
    const dEnd = d0 + D + 0.08;
    let o = `<rect width="360" height="300" fill="${dim(st.upper, 0.5)}"/>`, glow = '';
    // Sostre de fusta amb bigues.
    {
      let d = '';
      for (let k = 0; k <= 10; k++) {
        const dz = dEnd * k / 10, a = q(-xo, dz, 1.6), b = q(xo, dz, 1.6);
        d += `M${f(a[0])} ${f(a[1])}L${f(b[0])} ${f(b[1])}`;
      }
      o += shape([q(-xo, 0, 1.6), q(xo, 0, 1.6), q(xo, dEnd, 1.6), q(-xo, dEnd, 1.6)], dim(st.wood, 0.35)) +
           `<path d="${d}" stroke="${dim(st.wood, 0.6)}" stroke-width="1.4"/>`;
    }
    // Paret del fons: plafons, la porta i la tribuna.
    o += shape([q(-xo, dEnd, 0), q(xo, dEnd, 0), q(xo, dEnd, 1.6), q(-xo, dEnd, 1.6)], `url(#${u}wall)`);
    {
      let d = '';
      for (let k = 1; k < 12; k++) { const a = q(-xo + 2 * xo * k / 12, dEnd, 0.05), b = q(-xo + 2 * xo * k / 12, dEnd, 0.7); d += `M${f(a[0])} ${f(a[1])}L${f(b[0])} ${f(b[1])}`; }
      o += `<path d="${d}" stroke="${dim(st.wall, 0.35)}" stroke-width=".6"/>`;
      const [dx0, dy0, ds] = q(-0.06, dEnd, 0);
      o += `<path d="M${f(dx0)} ${f(dy0)}v${f(-ds * 0.34)}a${f(ds * 0.06)} ${f(ds * 0.06)} 0 0 1 ${f(ds * 0.12)} 0v${f(ds * 0.34)}Z" fill="${dim(st.dark, 0.3)}" stroke="url(#${u}gold)" stroke-width=".8"/>`;
      o += shape([q(-xo, dEnd, 0.86), q(xo, dEnd, 0.86), q(xo, dEnd, 0.95), q(-xo, dEnd, 0.95)], st.dark) +
           stroke([q(-xo, dEnd, 0.95), q(xo, dEnd, 0.95)], `url(#${u}gold)`, 1.2);
    }
    for (const sg of [-1, 1]) {
      o += shape([q(sg * xo, 0, zr(rows)), q(sg * xo, dEnd, zr(rows)), q(sg * xo, dEnd, 1.6), q(sg * xo, 0, 1.6)], `url(#${u}wall)`);
      let d = '';
      for (let k = 0; k <= 14; k++) { const a = q(sg * xo, dEnd * k / 14, zr(rows) + 0.02), b = q(sg * xo, dEnd * k / 14, 0.76); d += `M${f(a[0])} ${f(a[1])}L${f(b[0])} ${f(b[1])}`; }
      o += `<path d="${d}" stroke="${dim(st.wall, 0.4)}" stroke-width=".6"/>`;
      // galeria lateral amb public i barana
      o += shape([q(sg * xo, 0, 0.8), q(sg * xo, dEnd, 0.8), q(sg * xo, dEnd, 0.9), q(sg * xo, 0, 0.9)], st.dark) +
           stroke([q(sg * xo, 0, 0.9), q(sg * xo, dEnd, 0.9)], `url(#${u}gold)`, 1.4);
      for (let k = 0; k < 7; k++) {
        const [X, Y, s] = q(sg * (xo - 0.02), 0.15 + dEnd * (k + 0.5) / 7, 1.18);
        o += `<path d="M${f(X)} ${f(Y)}v${f(-s * 0.05)}" stroke="url(#${u}gold)" stroke-width="${f(s * 0.006)}"/><circle cx="${f(X)}" cy="${f(Y - s * 0.055)}" r="${f(s * 0.012)}" fill="#fff4cf"/>`;
        glow += `<circle class="gw" style="--i:${k}" cx="${f(X)}" cy="${f(Y - s * 0.055)}" r="${f(s * 0.1)}" fill="url(#${u}glow)"/>`;
      }
    }
    // Catifa amb les dues ratlles vermelles davant dels primers bancs.
    o += shape([q(-0.16, 0, 0), q(0.16, 0, 0), q(0.16, dEnd, 0), q(-0.16, dEnd, 0)], `url(#${u}carpet)`);
    if (st.line) for (const sg of [-1, 1]) o += stroke([q(sg * 0.135, 0, 0), q(sg * 0.135, dEnd, 0)], st.line, 1.1);
    // Bancs i diputats, dels de fora als de dins.
    let n = 0;
    const blocks = sides.map((side, si) => {
      const sg = si === 0 ? 1 : -1, cells = [];
      let k = 0;
      side.forEach((g) => { for (let j = 0; j < g.s; j++, k++) cells.push({ g, col: Math.floor(k / rows), row: k % rows }); });
      return { sg, cells };
    });
    for (const b of blocks) b.cells.forEach((cell) => { cell.k = n++; });
    for (let row = rows - 1; row >= 0; row--) {
      for (const b of blocks) {
        const sg = b.sg, x = sg * xr(row), z = zr(row), back = sg * (xr(row) + 0.07);
        o += shape([q(back, d0 - 0.03, z + 0.1), q(back, d0 + D, z + 0.1), q(back, d0 + D, z), q(back, d0 - 0.03, z)], `url(#${u}vel)`);
        let tuft = '';
        for (let k = 0; k < 30; k++) { const [X, Y] = q(back, d0 + D * (k + 0.5) / 30, z + 0.065); tuft += `M${f(X)} ${f(Y)}h.01`; }
        o += `<path d="${tuft}" stroke="#000" stroke-opacity=".35" stroke-width="1" stroke-linecap="round"/>`;
        o += shape([q(back, d0 - 0.03, z), q(back, d0 + D, z), q(x, d0 + D, z), q(x, d0 - 0.03, z)], lite(st.seat, 0.12));
        const cells = b.cells.filter((cl) => cl.row === row).sort((a, cc) => cc.col - a.col);
        for (const cl of cells) {
          const [X, Y, s] = q(sg * (xr(row) + 0.03), d0 + (cl.col + 0.5) * dd, z + 0.005);
          // Als Comuns seuen colze a colze: cada diputat té la mida d'una
          // persona de veritat a aquella distància, i el del davant tapa
          // mig cos del del darrere, com a les fotos des de la presidència.
          o += person(X, Y, Math.max(1.6, dd * s * 1.3, s * 0.072), cl.g, cl.k, seats, ca, 0.28 * cl.col / ncol);
        }
        o += shape([q(x, d0 - 0.03, z), q(x, d0 + D, z), q(x, d0 + D, z - 0.075), q(x, d0 - 0.03, z - 0.075)], `url(#${u}wood)`);
      }
    }
    // La taula, les dues tribunes de despatx i la maça.
    const T = (x, d, z) => q(x, d, z);
    o += shape([T(-0.075, 0.3, 0.1), T(0.075, 0.3, 0.1), T(0.075, 1.0, 0.1), T(-0.075, 1.0, 0.1)], `url(#${u}top)`) +
         shape([T(-0.075, 0.3, 0), T(0.075, 0.3, 0), T(0.075, 0.3, 0.1), T(-0.075, 0.3, 0.1)], `url(#${u}wood)`);
    for (const sg of [-1, 1]) {
      o += shape([T(sg * 0.035, 0.34, 0.1), T(sg * 0.065, 0.34, 0.1), T(sg * 0.065, 0.34, 0.14), T(sg * 0.035, 0.34, 0.14)], dim(st.wood, 0.3), ` stroke="url(#${u}gold)" stroke-width=".5"`);
    }
    o += stroke([T(0, 0.55, 0.11), T(0, 0.92, 0.11)], `url(#${u}gold)`, 2.2, ' stroke-linecap="round"');
    const [, yb] = q(0, d0 - 0.06, 0);
    return { svg: o, glow, h: Math.ceil(Math.min(290, yb)) };
  }

  const ORDER_OK = (gs) => gs.filter((g) => g.p != null).length >= gs.length / 2;
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  /* ---------------------------------------------------------- muntatge */

  let UID = 0;
  const still = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  function mount(fig) {
    if (fig.dataset.done) return;
    let groups;
    try { groups = JSON.parse(fig.dataset.g || '[]'); } catch (e) { return; }
    groups = groups.filter((g) => g.s > 0);
    if (!groups.length) return;
    fig.dataset.done = '1';
    const key = fig.dataset.b || '_';
    const lang = fig.dataset.l || (window.PB && PB.lang) || 'ca';
    const ca = lang !== 'es';
    const low = key.toLowerCase(), iso = low.split('-')[0];
    const b = B[key] || B[low] || B[iso] || B._;
    const st = ROOM[key] || ROOM[low] || ROOM[iso] || ROOM._;
    // Esquerra a dreta segons la posicio de Wikidata, si se'n sap prou.
    if (ORDER_OK(groups)) {
      groups = groups.map((g, i) => ({ ...g, i })).sort((a, c) =>
        (a.p == null ? 0 : a.p) - (c.p == null ? 0 : c.p) || a.i - c.i);
    }
    S = []; K = 0;
    P(`M0 ${G}H360`, 'ln gd');
    b.draw();
    const facade = S.join('');
    const u = 'pbc' + (++UID) + '-';
    const room = b.lay === 'west' ? westRoom(groups, st, ca, u) : hemiRoom(groups, b.lay, st, ca, u);
    const seats = groups.reduce((a, g) => a + g.s, 0);
    const total = +fig.dataset.t || seats, maj = +fig.dataset.m || 0;
    const label = fig.getAttribute('aria-label') || '';
    const place = b.name ? `${b.name[ca ? 'ca' : 'es']}, ${ca ? b.city : (b.cityes || b.city)}` : '';
    fig.style.setProperty('--n', K);
    fig.innerHTML =
      `<svg class="in" viewBox="0 0 360 ${room.h}" role="img" aria-label="${esc(label || place)}">` +
      defs(u, st) + `<g class="scene">${room.svg}</g>` +
      `<rect width="360" height="${room.h}" fill="url(#${u}light)"/><rect width="360" height="${room.h}" fill="url(#${u}vig)"/>` +
      `<rect class="lights" width="360" height="${room.h}"/><g class="scene glows">${room.glow}</g></svg>` +
      `<figcaption>${place ? `<svg class="fac" viewBox="0 -6 360 128" aria-hidden="true">${facade}</svg>` : ''}` +
      `<span><b class="cnt" data-n="${total}">${total}</b> ${ca ? 'escons' : 'escaños'}` +
      `${maj ? ` · ${ca ? 'majoria' : 'mayoría'} <b>${maj}</b>` : ''}` +
      `${place ? `<br><small>${esc(place)} · ${ca ? 'il·lustració esquemàtica' : 'ilustración esquemática'}</small>` : ''}</span></figcaption>`;
    if (still || !('IntersectionObserver' in window)) { fig.classList.add('go', 'still'); return; }
    const io = new IntersectionObserver((es) => {
      for (const e of es) {
        if (!e.isIntersecting) continue;
        io.disconnect();
        fig.classList.add('go');
        count(fig);
      }
    }, { threshold: 0.25 });
    io.observe(fig);
  }

  // El recompte puja mentre els diputats ocupen els seients.
  function count(fig) {
    const el = fig.querySelector('.cnt');
    if (!el) return;
    const n = +el.dataset.n, t0 = performance.now() + 2000, dur = 2700;
    el.textContent = '0';
    // Si la pestanya no pinta (rAF aturat), el total hi ha de ser igualment.
    setTimeout(() => { el.textContent = String(n); }, 5200);
    const tick = (t) => {
      const q = Math.max(0, Math.min(1, (t - t0) / dur));
      el.textContent = String(Math.round(n * q));
      if (q < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  function scan(root) {
    (root || document).querySelectorAll('figure.chamber').forEach(mount);
  }

  window.PBChamber = { scan, mount, buildings: Object.keys(B) };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => scan());
  else scan();
})();
