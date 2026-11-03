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
    # Alemanya: Bundestag 2025, segon vot per Land. Fitxer kerg2.csv de la
    # Bundeswahlleiterin (Datenlizenz Deutschland - Namensnennung 2.0), baixat
    # el 03/11/2026 a data/raw/de/ amb el permis de l'Alfonso.
    "DE": {
        "adm0": "DEU", "group": "name", "dir": "de", "unit_file": "laender.json",
        "bbox": (5.6, 15.3, 47.2, 55.1),
        "base_file": "bundestag-2025.json", "loader": "de",
        "source": "Die Bundeswahlleiterin, Wiesbaden 2025 (dl-de/by-2-0)",
        "codes": {
            "Schleswig-Holstein": "01", "Hamburg": "02", "Niedersachsen": "03", "Bremen": "04",
            "Nordrhein-Westfalen": "05", "Hessen": "06", "Rheinland-Pfalz": "07",
            "Baden-Württemberg": "08", "Bayern": "09", "Saarland": "10", "Berlin": "11",
            "Brandenburg": "12", "Mecklenburg-Vorpommern": "13", "Sachsen": "14",
            "Sachsen-Anhalt": "15", "Thüringen": "16",
        },
        # Sigles de la Bundeswahlleiterin -> codis de les enquestes (eu-de).
        "parties": {"CDU": "?CDUCSU", "CSU": "?CDUCSU", "SPD": "?SOCIALDEMOCRATICPARTYOFGERMANY",
                    "AfD": "?ALTERNATIVEFORGERMANY", "GRÜNE": "?ALLIANCE90THEGREENS",
                    "Die Linke": "?THELEFT", "FDP": "?FREEDEMOCRATICPARTY",
                    "BSW": "?SAHRAWAGENKNECHTALLIANCE"},
    },
    # Regne Unit: generals del 2024 per nacio i per regio anglesa. Fitxer
    # candidacies.csv de la House of Commons Library (Open Parliament Licence v3),
    # baixat el 03/11/2026 a data/raw/gb/. Irlanda del Nord en gris: els seus
    # partits (DUP, Sinn Fein...) no surten a les enquestes de Gran Bretanya.
    "GB": {
        "adm0": "GBR", "group": "gb", "dir": "gb", "unit_file": "regions.json",
        "bbox": (-8.3, 2.0, 49.8, 60.9),
        "base_file": "ge-2024.json", "loader": "gb",
        "source": "House of Commons Library (Open Parliament Licence v3.0)",
        "codes": {
            "Scotland": "SCT", "Wales": "WLS", "Northern Ireland": "NIR",
            "Greater London": "LDN", "North West": "NW", "North East": "NE",
            "Yorkshire and the Humber": "YH", "East Midlands": "EM", "West Midlands": "WM",
            "East": "EE", "South East": "SE", "South West": "SW",
        },
        "names": {"Scotland": "Escòcia", "Wales": "Gal·les", "Northern Ireland": "Irlanda del Nord",
                  "Greater London": "Londres", "North West": "North West", "North East": "North East",
                  "Yorkshire and the Humber": "Yorkshire and the Humber",
                  "East Midlands": "East Midlands", "West Midlands": "West Midlands",
                  "East": "East of England", "South East": "South East", "South West": "South West"},
        "csv_regions": {"London": "LDN", "North West": "NW", "North East": "NE",
                        "Yorkshire and The Humber": "YH", "East Midlands": "EM",
                        "West Midlands": "WM", "East of England": "EE", "South East": "SE",
                        "South West": "SW"},
        "parties": {"Lab": "?LABOURPARTY", "Con": "?CONSERVATIVEPARTY", "RUK": "?REFORMUK",
                    "LD": "?LIBERALDEMOCRATS", "Green": "?GREENPARTIESINTHEUNITEDKINGDOM",
                    "SNP": "?SCOTTISHNATIONALPARTY", "PC": "?PLAIDCYMRU"},
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
    lon0, lon1, lat0, lat1 = spec["bbox"]

    def inside(ring):
        # Illots fora del marc (Rockall, a 300 km d'Escocia) estiraven el mapa.
        return any(lon0 <= x <= lon1 and lat0 <= y <= lat1 for x, y in ring)

    rings = {}
    for row, shape in zip(rows, shapes):
        if _clean(row.get("adm0_a3")) != spec["adm0"]:
            continue
        if spec["group"] == "gb":
            # Escocia, Gal.les i Irlanda del Nord senceres; Anglaterra per regions.
            nation = _clean(row.get("geonunit"))
            key = _clean(row.get("region")) if nation == "England" else nation
        else:
            key = _clean(row.get(spec["group"]))
        code = spec["codes"].get(key)
        if code:
            rings.setdefault(code, {"n": spec.get("names", {}).get(key, key), "r": []})["r"] += [
                r for r in shape if inside(r)]
    out = {code: {"n": v["n"], "d": _path(v["r"], xy)} for code, v in rings.items()}
    return {"w": WIDTH, "h": height, "dep": out}


def _shares(votes):
    """{territori: {partit: vots}} -> ({territori: {partit: %}}, {territori: valids})."""
    valid = {u: sum(v.values()) for u, v in votes.items()}
    return ({u: {p: round(100 * n / valid[u], 3) for p, n in v.items()} for u, v in votes.items()},
            valid)


def _load_de(spec):
    import csv
    path = ROOT / "data" / "raw" / "de" / "btw25_kerg2.csv"
    rows = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines(), delimiter=";"))
    head = next(i for i, r in enumerate(rows) if r and r[0] == "Wahlart")
    cols = {name: i for i, name in enumerate(rows[head])}
    votes, national = {}, {}
    for r in rows[head + 1:]:
        if len(r) < len(cols) or r[cols["Gruppenart"]] != "Partei" or r[cols["Stimme"]] != "2":
            continue
        n = int(r[cols["Anzahl"]] or 0)
        party = spec["parties"].get(r[cols["Gruppenname"]], "OTHER")
        kind, num = r[cols["Gebietsart"]], r[cols["Gebietsnummer"]]
        if kind == "Land":
            votes.setdefault(num, {}).setdefault(party, 0)
            votes[num][party] += n
        elif kind == "Bund":
            national[party] = national.get(party, 0) + n
    deps, valid = _shares(votes)
    nat, _ = _shares({"all": national})
    return deps, valid, nat["all"]


def _load_gb(spec):
    import csv
    path = ROOT / "data" / "raw" / "gb" / "ge2024_candidacies.csv"
    votes, national = {}, {}
    nations = {"Scotland": "SCT", "Wales": "WLS", "Northern Ireland": "NIR"}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            unit = nations.get(row["Country name"]) or spec["csv_regions"].get(row["English region name"])
            if not unit:
                continue
            n = int(row["Candidate vote count"] or 0)
            party = spec["parties"].get(row["Main party abbreviation"], "OTHER")
            if unit != "NIR":
                votes.setdefault(unit, {}).setdefault(party, 0)
                votes[unit][party] += n
            national[party] = national.get(party, 0) + n
    deps, valid = _shares(votes)
    nat, _ = _shares({"all": national})
    return deps, valid, nat["all"]


def baseline(spec, conn):
    """{territori: {partit: %}} i el total estatal de l'eleccio de base."""
    if spec.get("loader") in ("de", "gb"):
        deps, valid, national = {"de": _load_de, "gb": _load_gb}[spec["loader"]](spec)
        return {"national": national, "dep": deps, "valid": valid, "source": spec["source"]}
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
