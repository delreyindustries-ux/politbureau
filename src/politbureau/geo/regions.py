"""A quina comunitat autonoma pertany cada municipi i cada provincia.

Per que cal aixo. El Ministeri de l'Interior numera les comunitats amb un codi
PROPI que NO coincideix amb el de l'INE (el Ministeri intercanvia les dues
Castelles i col.loca Valencia en una altra posicio). Els mapes van amb codis
INE. Fiar-se que els dos sistemes coincideixen fa que Navarra es dibuixi damunt
de Murcia, i llavors el mapa diu que EH Bildu guanya a Cartagena.

En comptes de mantenir una taula copiada a ma -- que ningu no podria verificar i
que envelliria malament -- la pertinenca es dedueix de la geometria oficial de
l'Institut Geografic Nacional: es mira dins de quin poligon de comunitat cau
cada municipi. Com que cada provincia aporta desenes o centenars de municipis,
s'assigna per majoria, i aixi cap error puntual d'un poligon no arrossega res.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import fetch

CACHE = fetch.GEO_DIR / "es-regions.json"


# ------------------------------------------------------- geometria basica

def _decode_arc(topo, i):
    arc, t = topo["arcs"][i], topo.get("transform")
    out, x, y = [], 0, 0
    for p in arc:
        if t:
            x += p[0]; y += p[1]
            out.append((x * t["scale"][0] + t["translate"][0],
                        y * t["scale"][1] + t["translate"][1]))
        else:
            out.append((p[0], p[1]))
    return out


def _ring(topo, idxs):
    pts = []
    for i in idxs:
        arc = _decode_arc(topo, ~i)[::-1] if i < 0 else _decode_arc(topo, i)
        pts.extend(arc[1:] if pts else arc)
    return pts


def _polygons(topo, geometry):
    if geometry["type"] == "Polygon":
        return [geometry["arcs"]]
    if geometry["type"] == "MultiPolygon":
        return geometry["arcs"]
    return []


def _bbox(rings):
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    return min(xs), min(ys), max(xs), max(ys)


def _in_ring(x, y, ring):
    """Nombre de creuaments (ray casting). Cert si el punt es dins l'anell."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y):
            if x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
        j = i
    return inside


def _in_polygon(x, y, poly):
    """poly = [anell_exterior, forat, forat, ...]"""
    if not _in_ring(x, y, poly[0]):
        return False
    return not any(_in_ring(x, y, hole) for hole in poly[1:])


def _representative_point(rings):
    """Un punt de dins de la forma. El centroide d'una forma corbada pot caure
    a fora, aixi que si aixo passa es prova amb els vertexs desplacats cap endins."""
    ring = max(rings, key=len)
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    if _in_ring(cx, cy, ring):
        return cx, cy
    for k in range(0, len(ring), max(1, len(ring) // 12)):
        px, py = ring[k]
        tx, ty = px + (cx - px) * 0.25, py + (cy - py) * 0.25
        if _in_ring(tx, ty, ring):
            return tx, ty
    return cx, cy


# ------------------------------------------------------------- assignacio

def compute(topo=None):
    """{'municipality': {codi: regio}, 'province': {codi: regio}, 'names': {...}}"""
    topo = topo or fetch.load("ES")
    if not topo:
        return None

    regions = []
    for g in topo["objects"]["autonomous_regions"]["geometries"]:
        polys = [[_ring(topo, r) for r in poly] for poly in _polygons(topo, g)]
        if not polys:
            continue
        regions.append({
            "id": g.get("id"),
            "name": (g.get("properties") or {}).get("name"),
            "polys": polys,
            "bbox": [_bbox(p) for p in polys],
        })

    def locate(x, y):
        for reg in regions:
            for poly, (x0, y0, x1, y1) in zip(reg["polys"], reg["bbox"]):
                if x0 <= x <= x1 and y0 <= y <= y1 and _in_polygon(x, y, poly):
                    return reg["id"]
        return None

    muni_region, votes = {}, {}
    for g in topo["objects"]["municipalities"]["geometries"]:
        code = g.get("id")
        polys = _polygons(topo, g)
        if not code or not polys:
            continue
        rings = [_ring(topo, r) for r in polys[0]]
        x, y = _representative_point(rings)
        region = locate(x, y)
        if region:
            muni_region[code] = region
            votes.setdefault(code[:2], {})[region] = votes.setdefault(code[:2], {}).get(region, 0) + 1

    # Per majoria: una provincia sencera pertany a una sola comunitat, aixi que
    # el vot dels seus municipis ha de ser gairebe unanime. Si no ho es, val mes
    # saber-ho que amagar-ho.
    province_region, weak = {}, []
    for province, tally in votes.items():
        best = max(tally, key=tally.get)
        total = sum(tally.values())
        province_region[province] = best
        if tally[best] / total < 0.9:
            weak.append((province, tally[best], total))

    # Els municipis que no han caigut dins de cap poligon (illots, precisio de la
    # geometria) hereten la comunitat de la seva provincia.
    for g in topo["objects"]["municipalities"]["geometries"]:
        code = g.get("id")
        if code and code not in muni_region and code[:2] in province_region:
            muni_region[code] = province_region[code[:2]]

    return {
        "municipality": muni_region,
        "province": province_region,
        "names": {r["id"]: r["name"] for r in regions},
        "weak": weak,
    }


def assign(children: dict, parents: dict, child_key: str, parent_key: str) -> dict:
    """{clau_fill: clau_pare} per a dos FeatureCollection de GeoJSON.

    Mateix criteri que per a Espanya: es mira dins de quin poligon pare cau un
    punt interior de cada fill. Serveix per saber a quina regio pertany cada
    comuna francesa sense haver de mantenir cap taula copiada a ma.
    """
    boxes = []
    for feature in parents.get("features", []):
        code = (feature.get("properties") or {}).get(parent_key)
        geom = feature.get("geometry") or {}
        polys = (geom.get("coordinates", []) if geom.get("type") == "MultiPolygon"
                 else [geom.get("coordinates", [])] if geom.get("type") == "Polygon" else [])
        for poly in polys:
            if poly and poly[0]:
                boxes.append((code, poly, _bbox([poly[0]])))

    out = {}
    for feature in children.get("features", []):
        code = (feature.get("properties") or {}).get(child_key)
        geom = feature.get("geometry") or {}
        if not code or not geom.get("coordinates"):
            continue
        first = (geom["coordinates"][0] if geom.get("type") == "Polygon"
                 else geom["coordinates"][0][0] if geom.get("type") == "MultiPolygon" else None)
        if not first:
            continue
        x, y = _representative_point([first])
        for parent, poly, (x0, y0, x1, y1) in boxes:
            if x0 <= x <= x1 and y0 <= y <= y1 and _in_polygon(x, y, poly):
                out[code] = parent
                break
    return out


def table(refresh: bool = False) -> dict:
    if CACHE.exists() and not refresh:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    result = compute()
    if result:
        CACHE.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result or {"municipality": {}, "province": {}, "names": {}, "weak": []}
