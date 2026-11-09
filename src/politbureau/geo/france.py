"""Departaments de Franca per a la pagina d'enquestes (demanat el 03/11/2026).

Es fa UNA vegada en local i el resultat va al repositori (web/fr/), com el globus:

* `web/fr/departements.json`: el contorn de cada departament metropolita en un
  SVG de 1000 d'ample (equirectangular corregida per cos 46,5 graus, que a la
  latitud de Franca deforma menys d'un 3 %). Font: Natural Earth admin-1, 10m
  (domini public), el mateix fitxer que les regions del globus.
* `web/fr/presidentielle-2022.json`: el resultat de la primera volta de les
  presidencials del 2022 per departament, sumant els municipis que ja hi ha a la
  base de dades de l'eina local (Ministere de l'Interieur via data.gouv.fr,
  Licence Ouverte 2.0). Es la base sobre la qual es projecten les enquestes.

Ultramar (09/11/2026, demanat per ell): els cinc departaments d'ultramar, les
col·lectivitats (Saint-Pierre-et-Miquelon, Saint-Martin i Saint-Barthelemy,
Wallis-et-Futuna, Polinesia, Nova Caledonia) i els francesos de l'estranger van
en requadres sota el mapa, cadascun a la seva escala. El resultat del 2022 surt
del mateix fitxer del Ministeri (codis ZA...ZZ), que la base de dades no guarda
perque les comunes d'ultramar no tenen poligon al mapa de comunes.

Us: python -m politbureau.geo.france data/geo/world/admin1/ne_10m_admin_1_states_provinces
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from .seccions import _dbf, _shp

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "web" / "fr"
WIDTH = 1000
LON0, LON1, LAT0, LAT1 = -5.3, 9.7, 41.2, 51.2     # Franca metropolitana amb Corsega
K = math.cos(math.radians(46.5))


def _clean(v):
    if not isinstance(v, str):
        return v
    v = v.replace("\0", "").strip()
    try:
        return v.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return v


def _xy(lon, lat):
    scale = WIDTH / ((LON1 - LON0) * K)
    return (round((lon - LON0) * K * scale, 1), round((LAT1 - lat) * scale, 1))


def _path(rings):
    parts = []
    for ring in rings:
        pts = []
        for lon, lat in ring:
            p = _xy(lon, lat)
            if not pts or p != pts[-1]:
                pts.append(p)
        if len(set(pts)) < 3:
            continue
        x0, y0 = pts[0]
        seg = [f"M{x0:g} {y0:g}l"]
        for x, y in pts[1:]:
            seg.append(f"{round(x - x0, 1):g} {round(y - y0, 1):g}")
            x0, y0 = x, y
        parts.append(seg[0] + " ".join(seg[1:]) + "z")
    return "".join(parts)


def geometry(admin1: Path):
    rows = _dbf(Path(str(admin1) + ".dbf").read_bytes())
    shapes = _shp(Path(str(admin1) + ".shp").read_bytes())
    out = {}
    for row, shape in zip(rows, shapes):
        if _clean(row.get("adm0_a3")) != "FRA" or _clean(row.get("type_en")) != "Metropolitan department":
            continue
        code = _clean(row["iso_3166_2"]).split("-")[1]
        out[code] = {"n": _clean(row["name"]), "d": _path(shape)}
    height = _xy(LON0, LAT0)[1]
    extra, frames, height = overseas(admin1, height)
    out.update(extra)
    return {"w": WIDTH, "h": height, "dep": out, "insets": frames}


# Codi del Ministeri -> (codi del mapa, nom, etiqueta curta, adm0 de Natural Earth
# o None si no es dibuixa la forma sino un cercle).
OVERSEAS = [
    ("ZA", "971", "Guadeloupe", "Guadeloupe", ("FRA", "FR-GP")),
    ("ZB", "972", "Martinique", "Martinique", ("FRA", "FR-MQ")),
    ("ZC", "973", "Guyane", "Guyane", ("FRA", "FR-GF")),
    ("ZD", "974", "La Réunion", "La Réunion", ("FRA", "FR-RE")),
    ("ZM", "976", "Mayotte", "Mayotte", ("FRA", "FR-YT")),
    ("ZS", "975", "Saint-Pierre-et-Miquelon", "St-Pierre-et-Miq.", ("SPM", None)),
    ("ZX", "977", "Saint-Martin et Saint-Barthélemy", "St-Martin / St-Barth", ("MAF", "BLM")),
    ("ZW", "986", "Wallis-et-Futuna", "Wallis-et-Futuna", None),
    ("ZP", "987", "Polynésie française", "Polynésie", None),
    ("ZN", "988", "Nouvelle-Calédonie", "Nouvelle-Calédonie", ("NCL", None)),
    ("ZZ", "99", "Français de l'étranger", "Hors de France", None),
]
ROWS = [6, 5]          # requadres per fila
BOX_H = 150
LABEL_H = 26


def _fit_path(rings, x, y, w, h):
    """Els anells, escalats perque cabin al requadre (x, y, w, h), centrats."""
    lons = [lon for r in rings for lon, _ in r]
    lats = [lat for r in rings for _, lat in r]
    k = math.cos(math.radians((min(lats) + max(lats)) / 2))
    bw, bh = (max(lons) - min(lons)) * k or 1e-6, (max(lats) - min(lats)) or 1e-6
    sc = min(w / bw, h / bh)
    ox = x + (w - bw * sc) / 2
    oy = y + (h - bh * sc) / 2
    parts = []
    for ring in rings:
        pts = []
        for lon, lat in ring:
            pt = (round(ox + (lon - min(lons)) * k * sc, 1), round(oy + (max(lats) - lat) * sc, 1))
            if not pts or pt != pts[-1]:
                pts.append(pt)
        if len(set(pts)) < 3:
            continue
        x0, y0 = pts[0]
        seg = [f"M{x0:g} {y0:g}l"]
        for px, py in pts[1:]:
            seg.append(f"{round(px - x0, 1):g} {round(py - y0, 1):g}")
            x0, y0 = px, py
        parts.append(seg[0] + " ".join(seg[1:]) + "z")
    return "".join(parts)


def _circle(cx, cy, r):
    return f"M{cx - r:g} {cy:g}a{r:g} {r:g} 0 1 0 {2 * r:g} 0a{r:g} {r:g} 0 1 0 {-2 * r:g} 0z"


def overseas(admin1: Path, top: float, width: float = WIDTH):
    """Requadres d'ultramar sota el mapa: {codi: {n, d}}, els marcs i l'alcada."""
    rows = _dbf(Path(str(admin1) + ".dbf").read_bytes())
    shapes = _shp(Path(str(admin1) + ".shp").read_bytes())
    by_a3, by_iso = {}, {}
    for row, shape in zip(rows, shapes):
        by_a3.setdefault(_clean(row.get("adm0_a3")), []).extend(shape)
        by_iso[_clean(row.get("iso_3166_2"))] = shape
    deps, frames, i = {}, [], 0
    y = top + 12
    for n_row in ROWS:
        bw = width / n_row
        for j in range(n_row):
            _, code, name, label, src = OVERSEAS[i]
            i += 1
            x = j * bw
            frames.append({"x": round(x + 4, 1), "y": round(y, 1), "w": round(bw - 8, 1),
                           "h": BOX_H - 8, "t": label})
            ix, iy, iw, ih = x + 16, y + 10, bw - 32, BOX_H - 8 - LABEL_H - 16
            rings = None
            if src and src[0] == "FRA":
                rings = by_iso[src[1]]
            elif src:
                rings = [r for a3 in src if a3 for r in by_a3.get(a3, [])]
            d = (_fit_path(rings, ix, iy, iw, ih) if rings
                 else _circle(round(ix + iw / 2, 1), round(iy + ih / 2, 1), 26))
            deps[code] = {"n": name, "d": d}
        y += BOX_H
    return deps, frames, round(y + 4, 1)


def overseas_baseline(party_resolver):
    """{codi: {partit: %}} i vots valids dels territoris d'ultramar i l'estranger,
    del fitxer de meses del Ministeri (ja baixat per l'eina local)."""
    from ..ingest import france as fr
    code_of = {z: c for z, c, *_ in OVERSEAS}
    votes, valid = {}, {}
    for key, (cands, expressed) in fr.votes().items():
        code = code_of.get(key[:2])
        if not code:
            continue
        valid[code] = valid.get(code, 0) + (expressed or sum(cands.values()))
        for label, n in cands.items():
            party = party_resolver(label)
            if party:
                votes.setdefault(code, {}).setdefault(party, 0)
                votes[code][party] += n
    deps = {c: {p: round(100 * n / valid[c], 3) for p, n in ps.items()} for c, ps in votes.items()}
    return deps, valid


def baseline(conn):
    """{dep: {party: %}} i el total estatal, de la primera volta del 2022."""
    votes, valid = {}, {}
    seen = set()
    for code, party, v, val in conn.execute(
            """SELECT code, party, votes, valid_votes FROM election_result
               WHERE election = 'presidentielle-2022-t1' AND level = 'municipality'"""):
        dep = code[:2]
        votes.setdefault(dep, {}).setdefault(party, 0)
        votes[dep][party] += v or 0
        if code not in seen:
            seen.add(code)
            valid[dep] = valid.get(dep, 0) + (val or 0)
    deps = {d: {p: round(100 * n / valid[d], 3) for p, n in ps.items()} for d, ps in votes.items()}
    from .. import parties
    extra, extra_valid = overseas_baseline(lambda s: parties.resolve(s, "FR")[0])
    deps.update(extra)
    valid.update(extra_valid)
    national = {r[0]: round(100 * r[1] / r[2], 3) for r in conn.execute(
        """SELECT party, votes, valid_votes FROM election_result
           WHERE election = 'presidentielle-2022-t1' AND level = 'national'""")}
    return {"election": "presidentielle-2022-t1", "national": national, "dep": deps,
            "valid": valid,
            "source": "Ministere de l'Interieur (data.gouv.fr), Licence Ouverte 2.0"}


def build(admin1: Path):
    import sqlite3
    OUT.mkdir(parents=True, exist_ok=True)
    geo = geometry(admin1)
    (OUT / "departements.json").write_text(json.dumps(geo, separators=(",", ":"), ensure_ascii=False),
                                           encoding="utf-8")
    conn = sqlite3.connect(ROOT / "data" / "politbureau.db")
    base = baseline(conn)
    (OUT / "presidentielle-2022.json").write_text(
        json.dumps(base, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return len(geo["dep"]), len(base["dep"])


if __name__ == "__main__":
    print(build(Path(sys.argv[1])))
