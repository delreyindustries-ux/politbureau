"""Aprimar geometries perque el navegador les pugui pair.

El fitxer de municipis italians fa 36 MB i el de comunes franceses 12 MB, amb
coordenades de sis o set decimals. Set decimals son onze centimetres: per a un
mapa d'un pais sencer sobra amb quatre (uns onze metres).

Es quantitza, NO se simplifica amb Douglas-Peucker. La diferencia importa: si
cada poligon s'aprimes pel seu compte, dos municipis veins deixarien de compartir
exactament la frontera i el mapa s'ompliria d'escletxes blanques. Quantitzar
encaixa tots els punts a la MATEIXA graella, de manera que els punts compartits
segueixen sent identics i les fronteres continuen tancant.
"""
from __future__ import annotations

import json


def _drop_collinear(points):
    """Treu els vertexs que cauen EXACTAMENT sobre la recta dels seus veins.

    Es segur fer-ho poligon a poligon: com que el punt no aporta cap canvi de
    direccio, la linia resultant es identica: el vei que comparteixi aquella
    frontera dibuixara exactament el mateix traç encara que conservi el punt.
    Despres de quantitzar n'hi ha molts, perque els trams rectes acaben tenint
    tots els punts alineats sobre la graella.
    """
    if len(points) < 4:
        return points
    out = [points[0]]
    for i in range(1, len(points) - 1):
        (ax, ay), (bx, by), (cx, cy) = out[-1], points[i], points[i + 1]
        # Producte vectorial exactament zero = els tres punts son alineats.
        if (bx - ax) * (cy - ay) - (by - ay) * (cx - ax) != 0:
            out.append(points[i])
    out.append(points[-1])
    return out


def _quantize_ring(ring, digits):
    out, last = [], None
    for x, y in ring:
        p = (round(x, digits), round(y, digits))
        if p != last:                      # despres d'encaixar surten punts repetits
            out.append(p)
            last = p
    # Un anell necessita com a minim tres punts diferents mes el tancament.
    if len(out) >= 3 and out[0] != out[-1]:
        out.append(out[0])
    if len(out) < 4:
        return None
    out = _drop_collinear(out)
    return out if len(out) >= 4 else None


def _quantize_geometry(geom, digits):
    t = geom.get("type")
    if t == "Polygon":
        rings = [r for r in (_quantize_ring(x, digits) for x in geom["coordinates"]) if r]
        return {"type": "Polygon", "coordinates": rings} if rings else None
    if t == "MultiPolygon":
        polys = []
        for poly in geom["coordinates"]:
            rings = [r for r in (_quantize_ring(x, digits) for x in poly) if r]
            if rings:
                polys.append(rings)
        return {"type": "MultiPolygon", "coordinates": polys} if polys else None
    return None


def quantize(collection: dict, digits: int = 4, keep: tuple = ()) -> dict:
    """Retorna un FeatureCollection aprimat, conservant nomes les propietats de `keep`."""
    features = []
    for f in collection.get("features", []):
        geom = _quantize_geometry(f.get("geometry") or {}, digits)
        if not geom:
            continue
        props = f.get("properties") or {}
        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {k: props.get(k) for k in keep if props.get(k) is not None},
        })
    return {"type": "FeatureCollection", "features": features}


def dumps(collection: dict) -> str:
    return json.dumps(collection, separators=(",", ":"), ensure_ascii=False)
