"""Mapamundi de la pagina d'enquestes (demanat el 03/11/2026).

Font: world-atlas 2.0.2, `countries-50m.json` (Natural Earth, domini public),
baixat de cdn.jsdelivr.net amb el permis de l'Alfonso. Es processa UNA vegada
en local i el resultat, `web/world.json`, va al repositori: aixi la publicacio
de cada hora no baixa res i el navegador dels visitants tampoc no demana res a
tercers.

Projeccio Equal Earth (Savric, Patterson i Jenny, 2018): conserva les arees i
no infla l'hemisferi nord com Mercator, que faria Escandinavia mes gran que
l'Europa del sud.

Us: python -m politbureau.geo.world data/geo/world/countries-50m.json web/world.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# ISO 3166-1 numeric (world-atlas) -> codi de pais de sources.yaml.
ISO = {
    "008": "AL", "040": "AT", "056": "BE", "070": "BA", "100": "BG", "191": "HR",
    "196": "CY", "203": "CZ", "208": "DK", "233": "EE", "246": "FI", "250": "FR",
    "276": "DE", "300": "GR", "348": "HU", "352": "IS", "372": "IE", "380": "IT",
    "428": "LV", "440": "LT", "442": "LU", "470": "MT", "498": "MD", "499": "ME",
    "528": "NL", "578": "NO", "616": "PL", "620": "PT", "642": "RO", "688": "RS",
    "703": "SK", "705": "SI", "724": "ES", "752": "SE", "756": "CH", "807": "MK",
    "826": "GB", "840": "US", "076": "BR",
}
WIDTH = 4000          # unitats de la viewBox; enters per estalviar bytes

A1, A2, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796
M = math.sqrt(3) / 2
X_MAX = 2.7066           # Equal Earth a lon=180, lat=0
Y_MAX = 1.3173           # a lat=90


def equal_earth(lon, lat):
    lam, phi = math.radians(lon), math.radians(lat)
    theta = math.asin(M * math.sin(phi))
    t2 = theta * theta
    t6 = t2 * t2 * t2
    x = lam * math.cos(theta) / (M * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)))
    y = theta * (A1 + A2 * t2 + t6 * (A3 + A4 * t2))
    scale = WIDTH / (2 * X_MAX)
    return round((x + X_MAX) * scale), round((Y_MAX - y) * scale)


def _arcs(topo):
    """Arcs absoluts (lon, lat) a partir dels deltes quantitzats."""
    (sx, sy), (tx, ty) = topo["transform"]["scale"], topo["transform"]["translate"]
    out = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        out.append(pts)
    return out


def _ring(arcs, idxs):
    pts = []
    for i in idxs:
        seg = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts.extend(seg if not pts else seg[1:])
    return pts


def _path(rings):
    """Anelles projectades -> "M x y l dx dy ... z", sense punts repetits."""
    parts = []
    for ring in rings:
        xy = []
        for lon, lat in ring:
            p = equal_earth(lon, lat)
            if not xy or p != xy[-1]:
                xy.append(p)
        if len(set(xy)) < 3:
            continue
        (x0, y0), d = xy[0], [f"M{xy[0][0]} {xy[0][1]}"]
        rel = []
        for x, y in xy[1:]:
            rel.append(f"{x - x0} {y - y0}")
            x0, y0 = x, y
        parts.append(d[0] + "l" + " ".join(rel) + "z")
    return "".join(parts)


def build(src: Path, out: Path):
    topo = json.loads(Path(src).read_text(encoding="utf-8"))
    arcs = _arcs(topo)
    features = []
    for g in topo["objects"]["countries"]["geometries"]:
        name = g["properties"]["name"]
        code = ISO.get(g.get("id") or "") or ("XK" if name == "Kosovo" else None)
        if name == "Antarctica":
            continue
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]] if g["type"] == "Polygon" else []
        rings = [_ring(arcs, r) for poly in polys for r in poly]
        d = _path(rings)
        if d:
            features.append({"c": code or g.get("id") or name, "n": name, "d": d})
    height = equal_earth(0, -90)[1]
    doc = {"w": WIDTH, "h": height, "f": features,
           # Caixa inicial: Europa, que es on hi ha les enquestes (x0, y0, x1, y1).
           "europe": [*equal_earth(-25, 72), *equal_earth(45, 34)],
           "source": "Natural Earth via world-atlas 2.0.2 (domini public)"}
    Path(out).write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False),
                         encoding="utf-8")
    return len(features), Path(out).stat().st_size


if __name__ == "__main__":
    print(build(Path(sys.argv[1]), Path(sys.argv[2])))
