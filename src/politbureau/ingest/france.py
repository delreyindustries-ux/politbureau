"""Resultats reals de la presidencial francesa de 2022 (1a volta), comuna a comuna.

Font: Ministere de l'Interieur via data.gouv.fr. No publiquen un fitxer per
comuna, nomes per mesa electoral, aixi que s'agreguen les meses.

Format del fitxer: 21 columnes fixes i despres blocs de SET columnes repetits,
un per candidat (numero de plafo, sexe, cognom, nom, vots, %inscrits, %expressats).
El codi de la comuna es el del departament seguit del de la comuna: junts fan
el codi INSEE que fa servir el mapa.

Limitacio coneguda: la geometria de france-geojson nomes cobreix la metropoli i
Corsega. Els departaments d'ultramar surten al fitxer de resultats pero no tenen
poligon, i per tant no es dibuixen. Es registra quants se n'han descartat.
"""
from __future__ import annotations

import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "data" / "raw"

RESULTS = ("https://static.data.gouv.fr/resources/"
           "election-presidentielle-des-10-et-24-avril-2022-resultats-definitifs-du-1er-tour/"
           "20220414-152542/resultats-par-niveau-burvot-t1-france-entiere.txt")
GEOMETRY = ("https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/"
            "communes.geojson")

ELECTION = "presidentielle-2022-t1"
DATE = "2022-04-10"

FIXED_COLUMNS = 21          # fins a "% Exp/Vot"
BLOCK = 7                   # plafo, sexe, cognom, nom, vots, %ins, %exp
EXPRESSED = 18              # index de la columna "Exprimes"


def _download(url: str, name: str) -> bytes:
    path = CACHE / name
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        with requests.get(url, timeout=1800, stream=True) as resp:
            resp.raise_for_status()
            with path.open("wb") as fh:
                for chunk in resp.iter_content(1 << 20):
                    fh.write(chunk)
    return path.read_bytes()


def geo_index() -> dict:
    """{codi_INSEE: nom} de les comunes que el mapa sap dibuixar."""
    data = json.loads(_download(GEOMETRY, "fr_communes.geojson").decode("utf-8"))
    return {f["properties"]["code"]: f["properties"].get("nom")
            for f in data["features"] if f["properties"].get("code")}


def votes():
    """{codi_INSEE: ({candidat: vots}, expressats)} sumant totes les meses."""
    text = _download(RESULTS, "fr_presidentielle_t1_burvot.txt").decode("latin-1")
    out: dict[str, list] = {}
    lines = text.splitlines()
    for line in lines[1:]:
        if not line.strip():
            continue
        f = line.split(";")
        if len(f) <= FIXED_COLUMNS:
            continue
        code = f[0].strip().zfill(2) + f[4].strip().zfill(3)
        try:
            expressed = int(f[EXPRESSED])
        except (ValueError, IndexError):
            expressed = 0
        entry = out.setdefault(code, [{}, 0])
        entry[1] += expressed
        for i in range(FIXED_COLUMNS, len(f) - BLOCK + 1, BLOCK):
            surname, given, count = f[i + 2].strip(), f[i + 3].strip(), f[i + 4].strip()
            if not surname or not count.isdigit():
                continue
            name = f"{given} {surname}".strip()
            entry[0][name] = entry[0].get(name, 0) + int(count)
    return out


def store(conn, party_resolver, region_of=None):
    """`region_of` es {codi_INSEE: codi_regio}; si no es dona, no s'agrega per regio."""
    geo = geo_index()
    raw = votes()

    rows, national, higher = [], {}, {}
    matched, skipped = 0, 0
    for code, (candidates, expressed) in raw.items():
        name = geo.get(code)
        valid = expressed or sum(candidates.values())
        if not valid:
            continue

        per_party: dict[str, int] = {}
        for label, n in candidates.items():
            party = party_resolver(label)
            if not party:
                continue
            per_party[party] = per_party.get(party, 0) + n
            # El total nacional es de TOTA Franca, tambe de l'ultramar. Si nomes
            # se sumessin les comunes que tenen poligon, el numerador deixaria
            # fora l'ultramar mentre el denominador l'inclou, i cada candidat
            # sortiria un punt per sota del seu resultat de debo.
            national[party] = national.get(party, 0) + n

        if name is None:
            skipped += 1              # ultramar: hi ha resultats pero no poligon
            continue
        matched += 1
        region = (region_of or {}).get(code)
        if region:
            bucket = higher.setdefault(region, {"parties": {}, "valid": 0})
            bucket["valid"] += valid
            for party, n in per_party.items():
                bucket["parties"][party] = bucket["parties"].get(party, 0) + n

        for party, n in per_party.items():
            rows.append(("FR", ELECTION, DATE, "municipality", code, name,
                         party, n, valid, None, "ministere de l'interieur"))

    for region, bucket in higher.items():
        for party, n in bucket["parties"].items():
            rows.append(("FR", ELECTION, DATE, "region", region, None,
                         party, n, bucket["valid"], None, "ministere de l'interieur"))

    total = sum(v[1] for v in raw.values())
    for party, n in national.items():
        rows.append(("FR", ELECTION, DATE, "national", "FR", "França",
                     party, n, total, None, "ministere de l'interieur"))

    conn.execute("DELETE FROM election_result WHERE country='FR' AND election = ?", (ELECTION,))
    conn.executemany(
        """INSERT INTO election_result
           (country, election, date, level, code, name, party, votes, valid_votes, census, source)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""", rows)
    conn.commit()
    return matched, skipped, len(rows)
