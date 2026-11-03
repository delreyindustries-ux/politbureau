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

Els departaments d'ultramar no hi son: la base de dades de l'eina local nomes
porta els municipis metropolitans.

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
    return {"w": WIDTH, "h": height, "dep": out}


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
