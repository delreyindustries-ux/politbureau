"""Contorns de les seccions censals, un fitxer per municipi (data/seccions/).

Les meses electorals no tenen contorn propi: una mesa es una part d'una seccio
censal (A, B... per l'ordre alfabetic dels electors). El mapa de cada ciutat,
doncs, es dibuixa per seccions, i cada seccio porta les seves meses.

Font: INE, «Cartografia digitalizada de secciones censales», seccionat a
1/1/2023 (seccionado_2023.zip, ETRS89 UTM 30N), el de les generals del 23J. El
ZIP fa 65 MB i NO va al repositori: es processa una vegada en local i el que es
publica son els contorns ja aprimats:

    PYTHONPATH=src py -c "from politbureau.geo import seccions; print(seccions.build('seccionado_2023.zip'))"

Nomes municipis amb DUES seccions o mes (decisio de l'Alfonso, 19/10/2026): en
un poble d'una sola seccio el mapa seria una sola taca.

Sense dependencies: el .shp i el .dbf es llegeixen a ma i la projeccio UTM es
desfa amb la serie de Krüger, que a 15 graus del meridia central (Canaries)
encara te errors de mil·limetres.
"""
from __future__ import annotations

import io
import json
import math
import struct
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "seccions"
GRID = 4000          # passos de la graella al costat llarg del municipi


# --------------------------------------------------------------- UTM -> graus

_A, _F = 6378137.0, 1 / 298.257222101          # GRS80 (ETRS89)
_N = _F / (2 - _F)
_AA = _A / (1 + _N) * (1 + _N ** 2 / 4 + _N ** 4 / 64)
_BETA = (_N / 2 - 2 * _N ** 2 / 3 + 37 * _N ** 3 / 96,
         _N ** 2 / 48 + _N ** 3 / 15,
         17 * _N ** 3 / 480)
_DELTA = (2 * _N - 2 * _N ** 2 / 3 - 2 * _N ** 3,
          7 * _N ** 2 / 3 - 8 * _N ** 3 / 5,
          56 * _N ** 3 / 15)


def utm_to_lonlat(e: float, n: float, zone: int = 30) -> tuple[float, float]:
    """Inversa de Krüger (UTM nord, factor 0,9996, fals est 500 km)."""
    xi = n / (0.9996 * _AA)
    eta = (e - 500000.0) / (0.9996 * _AA)
    xi_p, eta_p = xi, eta
    for j, b in enumerate(_BETA, start=1):
        xi_p -= b * math.sin(2 * j * xi) * math.cosh(2 * j * eta)
        eta_p -= b * math.cos(2 * j * xi) * math.sinh(2 * j * eta)
    chi = math.asin(math.sin(xi_p) / math.cosh(eta_p))
    lat = chi + sum(d * math.sin(2 * j * chi) for j, d in enumerate(_DELTA, start=1))
    lon0 = math.radians(zone * 6 - 183)
    lon = lon0 + math.atan2(math.sinh(eta_p), math.cos(xi_p))
    return math.degrees(lon), math.degrees(lat)


# --------------------------------------------------------------- shapefile

def _dbf(blob: bytes) -> list[dict]:
    count, header, size = struct.unpack("<IHH", blob[4:12])
    fields, i = [], 32
    while blob[i] != 0x0D:
        fields.append((blob[i:i + 11].split(b"\0")[0].decode(), blob[i + 16]))
        i += 32
    rows, off = [], header
    for _ in range(count):
        rec, pos, row = blob[off + 1:off + size], 0, {}
        for name, width in fields:
            row[name] = rec[pos:pos + width].decode("latin-1").strip()
            pos += width
        rows.append(row)
        off += size
    return rows


def _shp(blob: bytes) -> list[list[list[tuple[float, float]]]]:
    """Una llista d'anells (punts UTM) per registre. Tipus 5 (poligon)."""
    out, off = [], 100
    while off < len(blob):
        length = struct.unpack(">i", blob[off + 4:off + 8])[0] * 2
        body = blob[off + 8:off + 8 + length]
        off += 8 + length
        if struct.unpack("<i", body[:4])[0] != 5:
            out.append([])
            continue
        parts_n, points_n = struct.unpack("<ii", body[36:44])
        parts = list(struct.unpack(f"<{parts_n}i", body[44:44 + 4 * parts_n])) + [points_n]
        base = 44 + 4 * parts_n
        pts = struct.unpack(f"<{2 * points_n}d", body[base:base + 16 * points_n])
        out.append([[(pts[2 * k], pts[2 * k + 1]) for k in range(parts[p], parts[p + 1])]
                    for p in range(parts_n)])
    return out


# --------------------------------------------------------------- sortida

def _ring(points, x0, y0, step, kx):
    """Anell quantitzat i codificat en diferencies: [x, y, dx, dy, ...].

    Es projecta amb cos(latitud) del municipi (equirectangular) i s'encaixa a
    la MATEIXA graella per a tot el municipi, de manera que les fronteres
    compartides entre seccions continuen sent identiques i no queden escletxes.
    """
    q = []
    for lon, lat in points:
        p = (round((lon * kx - x0) / step), round((y0 - lat) / step))
        if not q or p != q[-1]:
            q.append(p)
    if len(q) < 4:
        return None
    keep = [q[0]]
    for i in range(1, len(q) - 1):
        (ax, ay), (bx, by), (cx, cy) = keep[-1], q[i], q[i + 1]
        if (bx - ax) * (cy - ay) != (by - ay) * (cx - ax):
            keep.append(q[i])
    keep.append(q[-1])
    flat, px, py = [], 0, 0
    for x, y in keep:
        flat += [x - px, y - py]
        px, py = x, y
    return flat


def build(zip_path: str | Path) -> tuple[int, int, int]:
    """Llegeix el ZIP de l'INE i escriu data/seccions/<municipi>.json.
    Retorna (municipis, seccions, bytes)."""
    zf = zipfile.ZipFile(zip_path)
    shp = next(n for n in zf.namelist() if n.lower().endswith(".shp"))
    rows = _dbf(zf.read(shp[:-4] + ".dbf"))
    shapes = _shp(zf.read(shp))

    by_muni: dict[str, list] = {}
    for row, rings in zip(rows, shapes):
        if rings:
            by_muni.setdefault(row["CUMUN"], []).append((row["CDIS"], row["CSEC"], rings))

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    n_munis = n_secs = size = 0
    for muni, secs in sorted(by_muni.items()):
        if len(secs) < 2:
            continue
        geo = [(d, s, [[utm_to_lonlat(e, n) for e, n in ring] for ring in rings])
               for d, s, rings in secs]
        lats = [lat for _, _, rings in geo for ring in rings for _, lat in ring]
        lons = [lon for _, _, rings in geo for ring in rings for lon, _ in ring]
        kx = math.cos(math.radians((min(lats) + max(lats)) / 2))
        x0, y0 = min(lons) * kx, max(lats)
        span = max((max(lons) - min(lons)) * kx, max(lats) - min(lats))
        step = span / GRID
        sections = {}
        for d, s, rings in geo:
            enc = [r for r in (_ring(ring, x0, y0, step, kx) for ring in rings) if r]
            if enc:
                sections[f"{d}-{s}"] = enc
        doc = {"grid": GRID, "w": round((max(lons) - min(lons)) * kx / step),
               "h": round((max(lats) - min(lats)) / step),
               "box": [round(min(lons), 5), round(min(lats), 5),
                       round(max(lons), 5), round(max(lats), 5)],
               "s": sections}
        text = json.dumps(doc, separators=(",", ":"))
        (OUT / f"{muni}.json").write_text(text, encoding="utf-8")
        n_munis += 1
        n_secs += len(sections)
        size += len(text)
    return n_munis, n_secs, size


# --------------------------------------------------------------- districtes

def _points(ring):
    x, y, out = ring[0], ring[1], [(ring[0], ring[1])]
    for i in range(2, len(ring), 2):
        x += ring[i]
        y += ring[i + 1]
        out.append((x, y))
    return out


def district_outlines(doc: dict) -> tuple[list, dict]:
    """Limits dels districtes d'un municipi, en coordenades de la graella.

    Com que totes les seccions comparteixen la MATEIXA graella, un tram de
    frontera entre dues seccions surt identic a totes dues. Un tram es limit
    de districte si el comparteixen seccions de districtes diferents, o si
    nomes en te una (la vora del municipi). Els trams es tornen a encadenar en
    linies i es codifiquen com els anells: [x, y, dx, dy, ...].

    Retorna (linies, {districte: [x, y] on posar-hi l'etiqueta}). L'etiqueta va
    al centre de la seccio mes gran del districte, que sempre cau a dins (el
    centre del districte sencer pot caure fora si te forma de mitja lluna)."""
    owners: dict = {}
    biggest: dict = {}
    for key, rings in doc["s"].items():
        district = key.split("-")[0]
        for ring in rings:
            pts = _points(ring)
            area = cx = cy = 0.0
            for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
                if (x1, y1) != (x2, y2):
                    seg = ((x1, y1), (x2, y2)) if (x1, y1) < (x2, y2) else ((x2, y2), (x1, y1))
                    owners.setdefault(seg, set()).add(district)
                    owners.setdefault(("n", seg), []).append(district)
                cross = x1 * y2 - x2 * y1
                area += cross
                cx += (x1 + x2) * cross
                cy += (y1 + y2) * cross
            if area and abs(area) > biggest.get(district, (0, None))[0]:
                biggest[district] = (abs(area), (round(cx / (3 * area)), round(cy / (3 * area))))
    edges = [seg for seg, ds in owners.items()
             if seg[0] != "n" and (len(ds) > 1 or len(owners[("n", seg)]) == 1)]
    graph: dict = {}
    for a, b in edges:
        graph.setdefault(a, []).append(b)
        graph.setdefault(b, []).append(a)
    used: set = set()
    lines = []
    # Primer des dels extrems i les cruïlles, despres els cicles que quedin.
    starts = [p for p, n in graph.items() if len(n) != 2] + list(graph)
    for start in starts:
        for nxt in graph[start]:
            seg = (start, nxt) if start < nxt else (nxt, start)
            if seg in used:
                continue
            line, prev, cur = [start], start, nxt
            used.add(seg)
            while True:
                line.append(cur)
                if len(graph[cur]) != 2:
                    break
                cand = graph[cur][0] if graph[cur][0] != prev else graph[cur][1]
                s2 = (cur, cand) if cur < cand else (cand, cur)
                if s2 in used:
                    break
                used.add(s2)
                prev, cur = cur, cand
            flat, px, py = [], 0, 0
            for x, y in line:
                flat += [x - px, y - py]
                px, py = x, y
            lines.append(flat)
    return lines, {d: list(c) for d, (_, c) in biggest.items()}
