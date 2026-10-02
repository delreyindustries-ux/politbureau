"""Resultats reals de les politiche italianes del 2022, comune a comune.

Font: microdades d'Eligendo (Ministero dell'Interno) publicades en CSV net pel
projecte ondata. Es fa servir la Camera, no el Senat, perque es la cambra que
projectem.

El creuament amb el mapa: tant el CSV de resultats com la geometria d'openpolis
porten el codi electoral del ministeri. La clau son els seus set ultims digits
(provincia + comune). Comprovat: encaixen 7.785 dels 7.830 comuni amb resultats.
NO es fan servir els codis ISTAT, que son una numeracio diferent.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "data" / "raw"

RESULTS = ("https://raw.githubusercontent.com/ondata/elezioni-politiche-2022/main/"
           "affluenza-risultati/dati/risultati/camera-italia-comune.csv")
GEOMETRY = ("https://raw.githubusercontent.com/openpolis/geojson-italy/master/"
            "geojson/limits_IT_municipalities.geojson")

ELECTION = "politiche-2022"
DATE = "2022-09-25"


def _download(url: str, name: str) -> bytes:
    path = CACHE / name
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        resp = requests.get(url, timeout=900)
        resp.raise_for_status()
        path.write_bytes(resp.content)
    return path.read_bytes()


def geo_index() -> dict:
    """{clau_electoral: (nom, codi_regio_istat)} llegit de la propia geometria."""
    data = json.loads(_download(GEOMETRY, "it_municipalities.geojson").decode("utf-8"))
    out = {}
    for feature in data["features"]:
        props = feature["properties"]
        code = str(props.get("minint_elettorale") or "")
        if len(code) >= 7:
            out[code[-7:]] = (props.get("name"), props.get("reg_istat_code"))
    return out


def votes() -> dict:
    """{clau_electoral: {llista: vots}} agregat des del CSV per candidat."""
    text = _download(RESULTS, "it_camera_comune.csv").decode("utf-8", errors="replace")
    out: dict[str, dict[str, int]] = {}
    for row in csv.DictReader(io.StringIO(text)):
        code = (row.get("codice") or "").split("-")
        if len(code) != 3:
            continue
        key = code[1].zfill(3) + code[2].zfill(4)
        try:
            n = int(row["voti"])
        except (TypeError, ValueError):
            continue
        party = (row.get("desc_lis") or "").strip()
        if not party:
            continue
        bucket = out.setdefault(key, {})
        bucket[party] = bucket.get(party, 0) + n
    return out


def store(conn, party_resolver):
    geo = geo_index()
    raw = votes()

    rows, national, higher = [], {}, {}
    matched = 0
    for key, lists in raw.items():
        valid = sum(lists.values())
        if not valid:
            continue

        per_party: dict[str, int] = {}
        for label, n in lists.items():
            party = party_resolver(label)
            if not party:
                continue
            per_party[party] = per_party.get(party, 0) + n
            # El total nacional compta TOTS els comuni, tambe els que despres no
            # es podran dibuixar: si no, el numerador i el denominador no
            # cobririen el mateix territori.
            national[party] = national.get(party, 0) + n

        info = geo.get(key)
        if not info:
            continue                      # comune fusionat o suprimit des del 2022
        matched += 1
        name, region = info
        if region:
            bucket = higher.setdefault(region, {"parties": {}, "valid": 0})
            bucket["valid"] += valid
            for party, n in per_party.items():
                bucket["parties"][party] = bucket["parties"].get(party, 0) + n

        for party, n in per_party.items():
            rows.append(("IT", ELECTION, DATE, "municipality", key, name,
                         party, n, valid, None, "eligendo/ondata"))

    for region, bucket in higher.items():
        for party, n in bucket["parties"].items():
            rows.append(("IT", ELECTION, DATE, "region", region, None,
                         party, n, bucket["valid"], None, "eligendo/ondata"))

    total = sum(sum(v.values()) for v in raw.values())
    for party, n in national.items():
        rows.append(("IT", ELECTION, DATE, "national", "IT", "Italia",
                     party, n, total, None, "eligendo/ondata"))

    conn.execute("DELETE FROM election_result WHERE country='IT' AND election = ?", (ELECTION,))
    conn.executemany(
        """INSERT INTO election_result
           (country, election, date, level, code, name, party, votes, valid_votes, census, source)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""", rows)
    conn.commit()
    return matched, len(raw) - matched, len(rows)
