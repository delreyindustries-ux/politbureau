"""Globus terraqui de la portada (pla el 03/11/2026, en 3D el mateix dia).

Font (05/11/2026): Natural Earth `ne_10m_admin_0_countries` (escala 1:10 milions,
domini public), baixat de naciscdn.org. Abans era la de 50m via world-atlas, i
les costes i fronteres es veien gruixudes en apropar-se. Es processa UNA vegada
en local i el resultat, `web/world.json`, va al repositori: aixi la publicacio
de cada hora no baixa res i el navegador dels visitants tampoc no demana res a
tercers.

Sahara Occidental: la 1:10m de Natural Earth 5.1.1 hi dibuixa el control de fet
(la franja a l'est del mur com a "W. Sahara" i la resta dins del Marroc). Aqui es
refa el territori sencer, separat del Marroc pel paral·lel 27°40' N, la frontera
que reconeix l'ONU (vegeu `_sahara`).

Es guarden longituds i latituds (no coordenades projectades): el globus les
projecta al navegador amb la projeccio ortografica i canvia a cada gir.

Format: {"q": 100, "t": [tolerancies], "f": [{"c": codi, "n": nom,
         "r": [[lon0, lat0, dlon, dlat, ...], ...], "l": ["0312...", ...]}]}
- graus multiplicats per `q` i arrodonits (0,01 graus, uns 1 km), cada punt com a
  diferencia de l'anterior;
- `l`: per a cada punt, el nivell de detall (0 = es veu sempre, 3 = nomes de molt
  a prop). Surt de simplificar l'anella amb Douglas-Peucker a les tolerancies `t`
  (graus), cada una sobre el resultat de la seguent. El navegador dibuixa nomes
  els nivells que es noten a la mida del globus a la pantalla: de lluny va
  rapid, i de prop hi ha tot el detall.

Regions (03/11/2026): les de `regions:` a sources.yaml (Escocia, Flandes, Ontario...)
surten de Natural Earth admin-1 a escala 10m (`ne_10m_admin_1_states_provinces`,
domini public). Cada regio ajunta les seves provincies; el codi es "<pais>-<clau>"
(GB-SCT, 124-ON) i van al final de la llista per dibuixar-se per sobre del pais.

Us: python -m politbureau.geo.world data/geo/world/ne10/ne_10m_admin_0_countries web/world.json
        [data/geo/world/admin1/ne_10m_admin_1_states_provinces]
    python -m politbureau.geo.world relief data/geo/world/relief/SR_50M.tif web/relief.jpg
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# ISO 3166-1 numeric -> codi de pais de sources.yaml. Fora d'Europa es fa servir
# el numeric directament (`pub.map` a sources.yaml).
ISO = {
    "008": "AL", "040": "AT", "056": "BE", "070": "BA", "100": "BG", "191": "HR",
    "196": "CY", "203": "CZ", "208": "DK", "233": "EE", "246": "FI", "250": "FR",
    "276": "DE", "300": "GR", "348": "HU", "352": "IS", "372": "IE", "380": "IT",
    "428": "LV", "440": "LT", "442": "LU", "470": "MT", "498": "MD", "499": "ME",
    "528": "NL", "578": "NO", "616": "PL", "620": "PT", "642": "RO", "688": "RS",
    "703": "SK", "705": "SI", "724": "ES", "752": "SE", "756": "CH", "807": "MK",
    "826": "GB",
}
Q = 100                          # 1/100 de grau
TOL = [0.2, 0.07, 0.025, 0.01]   # graus, del nivell 0 (lluny) al 3 (a prop)


def _clean(v):
    # El lector de seccions.py llegeix el dbf en latin-1; el de Natural Earth
    # es UTF-8 ("QuÃ©bec"): es torna a decodificar.
    if not isinstance(v, str):
        return v
    v = v.replace("\0", "").strip()
    try:
        return v.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return v


def _dp(pts, idx, tol):
    """Douglas-Peucker sobre els punts `idx` d'una anella tancada: els que queden.
    Distancies en graus, amb la longitud escalada pel cosinus de la latitud."""
    if len(idx) < 5:
        return idx
    k = math.cos(math.radians(sum(pts[i][1] for i in idx) / len(idx)))
    xy = [(pts[i][0] * k, pts[i][1]) for i in idx]
    # Una anella tancada es parteix pel punt mes llunya del primer.
    x0, y0 = xy[0]
    far = max(range(len(xy)), key=lambda j: (xy[j][0] - x0) ** 2 + (xy[j][1] - y0) ** 2)
    keep = {0, far, len(xy) - 1}
    stack = [(0, far), (far, len(xy) - 1)]
    t2 = tol * tol
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        (ax, ay), (bx, by) = xy[a], xy[b]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        best, bi = -1.0, -1
        for j in range(a + 1, b):
            px, py = xy[j][0] - ax, xy[j][1] - ay
            if L2:
                t = (px * dx + py * dy) / L2
                t = 0.0 if t < 0 else 1.0 if t > 1 else t
                ex, ey = px - t * dx, py - t * dy
            else:
                ex, ey = px, py
            d = ex * ex + ey * ey
            if d > best:
                best, bi = d, j
        if best > t2:
            keep.add(bi)
            stack += [(a, bi), (bi, b)]
    return [idx[j] for j in sorted(keep)]


def _encode(ring):
    """Anella -> ([lon0, lat0, dlon, dlat, ...] en 1/Q de grau, "nivells"), o None."""
    pts = []
    for lon, lat in ring:
        p = (round(lon * Q), round(lat * Q))
        if not pts or p != pts[-1]:
            pts.append(p)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    if len(set(pts)) < 3:
        return None
    deg = [(x / Q, y / Q) for x, y in pts]
    idx = list(range(len(pts)))
    level = {}
    for lv in range(len(TOL) - 1, -1, -1):
        nxt = _dp(deg, idx, TOL[lv])
        if len(nxt) < 4:          # una illa petita: es queda com al nivell seguent
            nxt = idx
        for i in nxt:
            level[i] = lv
        idx = nxt
    # Els punts que no passen ni la tolerancia mes fina no es guarden.
    pts = [pts[i] for i in sorted(level)]
    level = [level[i] for i in sorted(level)]
    out = [pts[0][0], pts[0][1]]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        out += [x1 - x0, y1 - y0]
    return out, "".join(str(v) for v in level)


def _feature(code, name, shape_rings):
    rs, ls = [], []
    for ring in shape_rings:
        got = _encode(ring)
        if got:
            rs.append(got[0])
            ls.append(got[1])
    return {"c": code, "n": name, "r": rs, "l": ls} if rs else None


def _regions(admin1: Path):
    """[{c, n, r, l}] de les regions de sources.yaml, llegides de Natural Earth admin-1."""
    import yaml
    from .seccions import _dbf, _shp
    root = Path(__file__).resolve().parents[3]
    cfg = yaml.safe_load((root / "config" / "sources.yaml").read_text(encoding="utf-8"))
    elections = {e["id"]: e for e in cfg["elections"]}
    rows = _dbf(Path(str(admin1) + ".dbf").read_bytes())
    shapes = _shp(Path(str(admin1) + ".shp").read_bytes())
    out = []
    for eid, regs in (cfg.get("regions") or {}).items():
        e = elections[eid]
        code = (e.get("pub") or {}).get("map") or e["country"]
        for reg in regs:
            want = {k: str(v) for k, v in reg["geo"].items()}
            rings = []
            for row, shape in zip(rows, shapes):
                if all(_clean(row.get(k)) == v for k, v in want.items()):
                    rings += shape
            feat = _feature(f"{code}-{reg['key']}", reg["name_ca"], rings)
            if not feat:
                raise SystemExit(f"cap provincia per a {eid} {reg['key']}: {want}")
            out.append(feat)
    return out


BORDER_27_40 = 27.66     # el paral·lel de la frontera, com el porta Natural Earth (27,6614)


def _sahara(mar, sah):
    """(Marroc, Sahara Occidental) sencers a partir dels poligons de Natural Earth.

    S'ajunten l'anella del Marroc i la de la franja (les arestes que comparteixen,
    el mur, s'anul·len) i el contorn que en surt es parteix pel paral·lel 27°40' N:
    el nord es el Marroc i el sud el Sahara Occidental. Cada part es tanca en
    linia recta de la costa al trifini amb Algeria, que es la frontera."""
    def ring(r):
        return r[:-1] if r[0] == r[-1] else r
    big = max(mar, key=len)
    m, w = ring(big), ring(max(sah, key=len))
    edges = set()
    for r in (m, w):
        edges.update(zip(r, r[1:] + r[:1]))
    edges = {e for e in edges if (e[1], e[0]) not in edges}
    nxt = {}
    for a, b in edges:
        nxt.setdefault(a, []).append(b)
    start = next(p for p in m if p in nxt)
    out, p = [start], start
    while True:
        p = nxt[p].pop()
        if p == start:
            break
        out.append(p)
    assert len(out) == len(edges), (len(out), len(edges))
    north = [q for q in out if q[1] >= BORDER_27_40]
    south = [q for q in out if q[1] <= BORDER_27_40 + 0.003]
    rest = [r for r in mar if r is not big]          # illes
    return [north] + rest, [south]


def build(src: Path, out: Path, admin1: Path | None = None):
    from .seccions import _dbf, _shp
    rows = _dbf(Path(str(src) + ".dbf").read_bytes())
    shapes = _shp(Path(str(src) + ".shp").read_bytes())
    a3s = [_clean(r["ADM0_A3"]) for r in rows]
    mar, sah = _sahara(shapes[a3s.index("MAR")], shapes[a3s.index("SAH")])
    shapes[a3s.index("MAR")], shapes[a3s.index("SAH")] = mar, sah
    features = []
    for row, shape in zip(rows, shapes):
        name, a3 = _clean(row["NAME"]), _clean(row["ADM0_A3"])
        if a3 == "ATA":
            continue
        n3 = _clean(row.get("ISO_N3_EH") or "")
        if a3 == "KOS":
            code = "XK"
        elif n3 and n3 != "-99":
            code = ISO.get(n3, n3)
        else:
            code = name          # Xipre del Nord, Somalilandia...: sense codi ISO
        feat = _feature(code, name, shape)
        if feat:
            features.append(feat)
    if admin1:
        features += _regions(admin1)
    doc = {"q": Q, "t": TOL, "f": features,
           "source": "Natural Earth 1:10m admin 0 i admin 1 (domini public)"}
    Path(out).write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False),
                         encoding="utf-8")
    npts = sum(len(lv) for f in features for lv in f["l"])
    per = [sum(s.count(str(k)) for f in features for s in f["l"]) for k in range(len(TOL))]
    return len(features), npts, per, Path(out).stat().st_size


def relief(src: Path, out: Path, width: int = 4096):
    """Textura del relleu del globus (05/11/2026).

    Font: Natural Earth `SR_50M`, "Shaded Relief Basic" a 1:50m (domini public),
    baixat de naciscdn.org: el relleu ombrejat en grisos, llum del nord-oest, en
    projeccio equirectangular (10800 x 5400). Aqui es redueix a 4096 x 2048
    (potencia de 2, la que tot navegador pot carregar com a textura) i es mou el
    gris de manera que el pla (206 a l'original, que tambe es el del mar) quedi al
    128: el globus la barreja amb els colors en mode "soft-light", on el 128 no
    canvia res, el mes fosc enfosqueix i el mes clar aclareix.
    """
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(src).convert("L").resize((width, width // 2), Image.LANCZOS)
    flat = 206
    im = im.point(lambda v: max(0, min(255, round(128 + (v - flat) * 128 / flat))))
    im.save(out, "JPEG", quality=84, optimize=True, progressive=True)
    return im.size, Path(out).stat().st_size


GAP = 2.0      # graus: mes lluny, una illa porta la seva propia bandera


def _groups(rings):
    """Agrupa els anells d'un pais en trossos propers: cada grup porta la seva
    bandera. Aixi la Guaiana Francesa o Hawaii no estiren la bandera de tot el
    pais d'un oceà a l'altre, i un arxipelag (Indonesia) en porta una de sola."""
    info = []
    for r in rings:
        lo = [x for x, _ in r]; la = [y for _, y in r]
        area = abs(sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r)))) / 2
        area *= math.cos(math.radians((min(la) + max(la)) / 2))
        info.append({"bb": [min(lo), min(la), max(lo), max(la)], "area": area, "r": r})
    info.sort(key=lambda g: -g["area"])
    groups = []
    def gap(a, b):
        """Distancia entre dos rectangles (0 si es toquen), en graus de meridia."""
        dx = max(b[0] - a[2], a[0] - b[2], 0)
        dy = max(b[1] - a[3], a[1] - b[3], 0)
        lat = math.radians((max(a[1], b[1]) + min(a[3], b[3])) / 2)
        return math.hypot(dx * math.cos(lat), dy)

    for g in info:
        for gr in groups:
            # Un tros s'afegeix a un grup si queda a prop d'algun dels seus anells.
            # Abans es mirava la distancia entre centres (18 graus) i les Canaries,
            # les Açores o Svalbard entraven al rectangle del pais: a la peninsula
            # nomes hi quedava un tros de la bandera (06/11/2026).
            if min(gap(b, g["bb"]) for b in gr["bbs"]) < GAP:
                gr["rings"].append(g["r"])
                gr["bbs"].append(g["bb"])
                bb = gr["bb"]
                gr["bb"] = [min(bb[0], g["bb"][0]), min(bb[1], g["bb"][1]),
                            max(bb[2], g["bb"][2]), max(bb[3], g["bb"][3])]
                break
        else:
            groups.append({"bb": list(g["bb"]), "rings": [g["r"]], "bbs": [g["bb"]]})
    return groups


def flags(world: Path, pngs: Path, out: Path, ne: Path, width: int = 8192):
    """Mapamundi de banderes (06/11/2026): cada pais pintat amb la seva bandera,
    estirada sobre el seu territori, en projeccio equirectangular com el relleu.
    El globus la llegeix com a textura i hi aplica l'ombra del relleu a sobre.

    Banderes: flag-icons (MIT, github.com/lipis/flag-icons), passades a PNG amb
    scripts/flags.mjs. Contorns: el mateix web/world.json (Natural Earth 1:10m).
    Fora de les terres, transparent; un pais sense bandera (Xipre del Nord,
    Somalilandia...) tambe, i el globus el deixa en gris.
    """
    import numpy as np
    from PIL import Image, ImageDraw
    from .seccions import _dbf
    w = json.loads(Path(world).read_text(encoding="utf-8"))
    # El codi de dues lletres de cada pais, pel nom (world.json porta el numeric
    # fora d'Europa): ISO_A2_EH de Natural Earth, que tambe en dona a Kosovo (XK)
    # i al Sahara Occidental (EH).
    a2 = {}
    for row in _dbf(Path(str(ne) + ".dbf").read_bytes()):
        code = _clean(row.get("ISO_A2_EH") or "")
        if code and code != "-99":
            a2[_clean(row["NAME"])] = code
    q, h = w["q"], width // 2
    sx, sy = width / 360.0, h / 180.0
    canvas = np.zeros((h, width, 4), dtype=np.uint8)
    done, missing = 0, []
    for f in w["f"]:
        code = f["c"]
        if "-" in code:                    # regions (Escocia...): ja hi es el pais
            continue
        src = Path(pngs) / f"{a2.get(f['n'], code).lower()}.png"
        if not src.exists():
            missing.append(code)
            continue
        rings = []
        for r in f["r"]:
            x = y = 0
            pts = []
            for i in range(0, len(r), 2):
                x += r[i]; y += r[i + 1]
                pts.append((x / q, y / q))
            rings.append(pts)
        flag = Image.open(src).convert("RGBA")
        for g in _groups(rings):
            x0, y0, x1, y1 = g["bb"]
            px0, px1 = int(math.floor((x0 + 180) * sx)), int(math.ceil((x1 + 180) * sx))
            py0, py1 = int(math.floor((90 - y1) * sy)), int(math.ceil((90 - y0) * sy))
            pw, ph = max(px1 - px0, 1), max(py1 - py0, 1)
            # Anells amb forats (Lesotho dins de Sud-africa): paritat, com al canvas.
            mask = np.zeros((ph, pw), dtype=bool)
            for r in g["rings"]:
                m = Image.new("1", (pw, ph), 0)
                ImageDraw.Draw(m).polygon([((lon + 180) * sx - px0, (90 - lat) * sy - py0)
                                           for lon, lat in r], fill=1)
                mask ^= np.array(m, dtype=bool)
            tile = np.array(flag.resize((pw, ph), Image.LANCZOS))
            ys, xs = np.nonzero(mask)
            yy, xx = ys + py0, (xs + px0) % width
            ok = (yy >= 0) & (yy < h)
            canvas[yy[ok], xx[ok]] = tile[ys[ok], xs[ok]]
        done += 1
    img = Image.fromarray(canvas, "RGBA")
    img.save(out, "WEBP", quality=88, method=6)
    return done, missing, img.size, Path(out).stat().st_size


if __name__ == "__main__":
    if sys.argv[1] == "relief":
        print(relief(Path(sys.argv[2]), Path(sys.argv[3])))
    elif sys.argv[1] == "flags":
        # python -m politbureau.geo.world flags web/world.json <pngs> web/flags.webp \
        #     data/geo/world/ne10/ne_10m_admin_0_countries
        print(flags(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5])))
    else:
        print(build(Path(sys.argv[1]), Path(sys.argv[2]),
                    Path(sys.argv[3]) if len(sys.argv) > 3 else None))
