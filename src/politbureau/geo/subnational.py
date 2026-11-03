"""Mapes per territori de les eleccions estrangeres (03/11/2026).

La versio general del que geo/france.py fa per als departaments francesos: per a
cada pais, un SVG dels seus territoris (regions, lander, voivodats...) i el
resultat real de l'ultima eleccio en cadascun, que la web fa servir de base per
projectar-hi la mitjana d'enquestes d'avui (pages._departments).

Es fa UNA vegada en local i el resultat va al repositori (web/<pais>/). Contorns:
Natural Earth admin-1 10m (domini public). Resultats: els que ja te la base de
dades de l'eina local, o un fitxer oficial baixat amb el permis de l'Alfonso.

Us: python -m politbureau.geo.subnational IT data/geo/world/admin1/ne_10m_admin_1_states_provinces
"""
from __future__ import annotations

import json
import math
import sqlite3
import sys
from pathlib import Path

from .seccions import _dbf, _shp

ROOT = Path(__file__).resolve().parents[3]
WIDTH = 1000

# Cada pais: com es fan els territoris a partir de Natural Earth i d'on surt la base.
#   adm0    -> pais a Natural Earth
#   group   -> camp de Natural Earth que defineix el territori (s'hi ajunten les provincies)
#   codes   -> {valor del camp: codi del territori a la base de dades}
#   bbox    -> (lon0, lon1, lat0, lat1) del mapa
SPECS = {
    "IT": {
        "adm0": "ITA", "group": "region", "dir": "it", "unit_file": "regioni.json",
        "bbox": (6.4, 18.8, 36.4, 47.2),
        "election": "politiche-2022", "base_file": "politiche-2022.json",
        "level": "region", "source": "Ministero dell'Interno (Eligendo), via ondata",
        "codes": {
            "Piemonte": "01", "Valle d'Aosta": "02", "Lombardia": "03", "Trentino-Alto Adige": "04",
            "Veneto": "05", "Friuli-Venezia Giulia": "06", "Liguria": "07", "Emilia-Romagna": "08",
            "Toscana": "09", "Umbria": "10", "Marche": "11", "Lazio": "12", "Abruzzo": "13",
            "Molise": "14", "Campania": "15", "Apulia": "16", "Basilicata": "17", "Calabria": "18",
            "Sicily": "19", "Sardegna": "20",
        },
        "names": {"Apulia": "Puglia", "Sicily": "Sicilia"},
    },
}


def _clean(v):
    if not isinstance(v, str):
        return v
    v = v.replace("\0", "").strip()
    try:
        return v.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return v


def _projector(bbox):
    lon0, lon1, lat0, lat1 = bbox
    k = math.cos(math.radians((lat0 + lat1) / 2))
    scale = WIDTH / ((lon1 - lon0) * k)

    def xy(lon, lat):
        return (round((lon - lon0) * k * scale, 1), round((lat1 - lat) * scale, 1))
    return xy, round((lat1 - lat0) * scale, 1)


def _path(rings, xy):
    parts = []
    for ring in rings:
        pts = []
        for lon, lat in ring:
            p = xy(lon, lat)
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


def geometry(spec, admin1: Path):
    rows = _dbf(Path(str(admin1) + ".dbf").read_bytes())
    shapes = _shp(Path(str(admin1) + ".shp").read_bytes())
    xy, height = _projector(spec["bbox"])
    rings = {}
    for row, shape in zip(rows, shapes):
        if _clean(row.get("adm0_a3")) != spec["adm0"]:
            continue
        key = _clean(row.get(spec["group"]))
        code = spec["codes"].get(key)
        if code:
            rings.setdefault(code, {"n": spec.get("names", {}).get(key, key), "r": []})["r"] += shape
    out = {code: {"n": v["n"], "d": _path(v["r"], xy)} for code, v in rings.items()}
    return {"w": WIDTH, "h": height, "dep": out}


def baseline(spec, conn):
    """{territori: {partit: %}} i el total estatal de l'eleccio de base."""
    deps, valid = {}, {}
    for code, party, v, val in conn.execute(
            """SELECT code, party, votes, valid_votes FROM election_result
               WHERE election = ? AND level = ?""", (spec["election"], spec["level"])):
        if not val:
            continue
        deps.setdefault(code, {})[party] = round(100 * (v or 0) / val, 3)
        valid[code] = val
    national = {r[0]: round(100 * r[1] / r[2], 3) for r in conn.execute(
        """SELECT party, votes, valid_votes FROM election_result
           WHERE election = ? AND level = 'national'""", (spec["election"],)) if r[2]}
    return {"election": spec["election"], "national": national, "dep": deps, "valid": valid,
            "source": spec["source"]}


def build(country: str, admin1: Path):
    spec = SPECS[country]
    out = ROOT / "web" / spec["dir"]
    out.mkdir(parents=True, exist_ok=True)
    geo = geometry(spec, admin1)
    (out / spec["unit_file"]).write_text(json.dumps(geo, separators=(",", ":"), ensure_ascii=False),
                                         encoding="utf-8")
    base = baseline(spec, sqlite3.connect(ROOT / "data" / "politbureau.db"))
    (out / spec["base_file"]).write_text(json.dumps(base, separators=(",", ":"), ensure_ascii=False),
                                         encoding="utf-8")
    missing = sorted(set(geo["dep"]) - set(base["dep"]))
    return len(geo["dep"]), len(base["dep"]), missing


if __name__ == "__main__":
    print(build(sys.argv[1], Path(sys.argv[2])))
