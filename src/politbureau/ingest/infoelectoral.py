"""Resultats electorals reals per municipi (Ministeri de l'Interior).

https://infoelectoral.interior.gob.es/ publica els microdades de tots els
processos des de 1977 en fitxers .DAT de camps de posicio fixa dins d'un ZIP.

Sobre el format: el ZIP porta un FICHEROS.rtf que hauria de documentar-lo, pero
en realitat es un .doc binari amb l'extensio canviada i no es pot llegir com a
text. Les posicions d'aquest modul s'han determinat empiricament i validat:

  * els codis del fitxer 06 llegits com provincia(2)+municipi(3) donen 8.131
    codis diferents que coincideixen al 100% amb els codis INE del mapa;
  * el camp [205:213] del fitxer 05 quadra exactament amb la suma de vots del
    fitxer 06 per a cada municipi (comprovat sobre 400 municipis).

Compte amb una trampa: els fitxers 05 i 06 NO tenen la mateixa estructura. El 05
porta el codi de comunitat autonoma davant del de provincia i el 06 no.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

from . import gobtls

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "data" / "raw"
BASE = "https://infoelectoral.interior.gob.es/estaticos/docxl/apliextr/"

# Tipus de proces electoral segons la nomenclatura del Ministeri.
CONGRESO, MUNICIPALES, EUROPEAS = "02", "04", "07"

PROCESSES = {
    "congreso-2023":    (CONGRESO, "2023", "07"),
    "congreso-2019n":   (CONGRESO, "2019", "11"),
    "municipales-2023": (MUNICIPALES, "2023", "05"),
    "europeas-2024":    (EUROPEAS, "2024", "06"),
}


def _records(blob: bytes, width: int):
    text = blob.decode("latin-1")
    step = width + 1                      # cada registre acaba amb un salt de linia
    return [text[i:i + width] for i in range(0, len(text) - width + 1, step)]


def download(process: str) -> zipfile.ZipFile:
    tipo, year, month = PROCESSES[process]
    name = f"{tipo}{year}{month}_MUNI.zip"
    cached = CACHE / name
    if not cached.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        resp = gobtls.session().get(BASE + name, timeout=600)
        resp.raise_for_status()
        cached.write_bytes(resp.content)
    return zipfile.ZipFile(io.BytesIO(cached.read_bytes()))


def _member(zf: zipfile.ZipFile, prefix: str, tipo: str, year: str, month: str):
    want = f"{prefix}{tipo}{year[2:]}{month}.DAT"
    for name in zf.namelist():
        if name.upper() == want:
            return zf.read(name)
    raise FileNotFoundError(f"{want} no hi es dins el ZIP: {zf.namelist()}")


def candidacies(zf, tipo, year, month) -> dict:
    """{codi_candidatura: sigles}. Fitxer 03, registres de 232 caracters:
    tipus(2) any(4) mes(2) codi(6) sigles(50) denominacio(150) + 3 codis de 6."""
    out = {}
    for rec in _records(_member(zf, "03", tipo, year, month), 232):
        out[rec[8:14]] = rec[14:64].strip()
    return out


def municipalities(zf, tipo, year, month) -> dict:
    """{codi_INE: {name, census, blank, invalid, valid}}. Fitxer 05, 233 car."""
    out = {}
    for rec in _records(_member(zf, "05", tipo, year, month), 233):
        if rec[16:18] != "99":            # 99 = municipi sencer; la resta son districtes
            continue
        code = rec[11:13] + rec[13:16]    # provincia + municipi = codi INE
        out[code] = {
            "name": rec[18:118].strip(),
            "region": rec[9:11],          # el fitxer 05 SI porta el codi de CCAA
            "census": int(rec[141:149]),
            "blank": int(rec[189:197]),
            "invalid": int(rec[197:205]),
            "valid": int(rec[205:213]),
        }
    return out


def votes(zf, tipo, year, month) -> dict:
    """{codi_INE: {codi_candidatura: vots}}. Fitxer 06, 33 caracters:
    tipus(2) any(4) mes(2) volta(1) provincia(2) municipi(3) districte(2)
    candidatura(6) vots(8) electes(3).  Sense codi de CCAA, a diferencia del 05."""
    out: dict[str, dict[str, int]] = {}
    for rec in _records(_member(zf, "06", tipo, year, month), 33):
        if rec[14:16] != "99":
            continue
        code = rec[9:11] + rec[11:14]
        out.setdefault(code, {})[rec[16:22]] = int(rec[22:30])
    return out


def constituencies(zf, tipo, year, month) -> dict:
    """{codi_provincia: {'seats': n, 'parties': {codi_candidatura: (vots, escons)}}}

    Fitxer 08, registres de 33 caracters. Porta les mateixes dades a TRES nivells
    (provincia, comunitat i estat) barrejats al mateix fitxer; els agregats es
    marquen amb '99' al codi de provincia o de comunitat. Sense filtrar-los, la
    suma d'escons dona 1.050 en comptes de 350.

        tipus(2) any(4) mes(2) volta(1) ccaa(2) provincia(2) districte(1)
        candidatura(6) vots(8) escons(5)
    """
    out: dict[str, dict] = {}
    for rec in _records(_member(zf, "08", tipo, year, month), 33):
        ccaa, province = rec[9:11], rec[11:13]
        if ccaa == "99" or province == "99":      # agregats, no circumscripcions
            continue
        seats = int(rec[28:33])
        entry = out.setdefault(province, {"seats": 0, "parties": {}})
        entry["seats"] += seats
        entry["parties"][rec[14:20]] = (int(rec[20:28]), seats)
    return out


def store_constituencies(conn, process: str, party_resolver):
    """Magnitud de cada circumscripcio i escons reals que hi va treure cada partit."""
    tipo, year, month = PROCESSES[process]
    data = constituencies(download(process), tipo, year, month)
    siglas = candidacies(download(process), tipo, year, month)

    mags, results = [], {}
    for province, entry in data.items():
        mags.append((process, "province", province, entry["seats"]))
        for cand_code, (votes_, seats) in entry["parties"].items():
            party = party_resolver(siglas.get(cand_code, cand_code))
            if not party:
                continue
            prev = results.get((province, party), (0, 0))
            results[(province, party)] = (prev[0] + votes_, prev[1] + seats)

    conn.execute("DELETE FROM constituency WHERE election = ?", (process,))
    conn.execute("DELETE FROM constituency_result WHERE election = ?", (process,))
    conn.executemany(
        "INSERT INTO constituency (election, level, code, seats) VALUES (?,?,?,?)", mags)
    conn.executemany(
        """INSERT INTO constituency_result (election, level, code, party, votes, seats)
           VALUES (?,?,?,?,?,?)""",
        [(process, "province", province, party, v, s)
         for (province, party), (v, s) in results.items()])
    conn.commit()
    return len(mags), sum(m[3] for m in mags)


def load(process: str):
    """Retorna (municipis, vots, sigles) per a un proces electoral."""
    tipo, year, month = PROCESSES[process]
    zf = download(process)
    return (municipalities(zf, tipo, year, month),
            votes(zf, tipo, year, month),
            candidacies(zf, tipo, year, month))


def store(conn, process: str, party_resolver):
    """Bolca els resultats reals a `election_result`, agregant les candidatures
    que corresponen al mateix partit (per exemple PSOE i PSC compten com a PSOE).

    `party_resolver(sigles) -> codi` ve de politbureau.parties.
    """
    from .. import db  # noqa: F401  (assegura l'esquema)

    tipo, year, month = PROCESSES[process]
    date = f"{year}-{month}-01"
    munis, vote_map, siglas = load(process)

    rows, national = [], {}
    # Agregats cap amunt: el mapa ha de poder mostrar provincia i comunitat, i
    # sumar-los aqui es exacte, mentre que fer-ho despres sobre percentatges ja
    # no ho seria (municipis de mides molt diferents no es poden promitjar).
    higher: dict[tuple[str, str], dict] = {}

    # NO es fa servir meta["region"]: el codi de comunitat del Ministeri no es el
    # de l'INE (les dues Castelles van intercanviades i Valencia canvia de lloc)
    # i els mapes van amb codis INE. La pertinenca es dedueix de la geometria.
    from ..geo import regions as georegions
    region_of = georegions.table()["province"]

    for code, meta in munis.items():
        province = code[:2]
        region = region_of.get(province)
        if not region:
            continue
        for level, key in (("province", province), ("region", region)):
            bucket = higher.setdefault((level, key), {"parties": {}, "valid": 0, "census": 0})
            bucket["valid"] += meta["valid"]
            bucket["census"] += meta["census"]

        per_party: dict[str, int] = {}
        for cand_code, n in vote_map.get(code, {}).items():
            party = party_resolver(siglas.get(cand_code, cand_code))
            if not party:
                continue
            per_party[party] = per_party.get(party, 0) + n
            national[party] = national.get(party, 0) + n
            for level, key in (("province", province), ("region", region)):
                parties_ = higher[(level, key)]["parties"]
                parties_[party] = parties_.get(party, 0) + n
        for party, n in per_party.items():
            rows.append(("ES", process, date, "municipality", code, meta["name"],
                         party, n, meta["valid"], meta["census"], "infoelectoral"))

    for (level, key), bucket in higher.items():
        for party, n in bucket["parties"].items():
            rows.append(("ES", process, date, level, key, None,
                         party, n, bucket["valid"], bucket["census"], "infoelectoral"))

    total_valid = sum(m["valid"] for m in munis.values())
    total_census = sum(m["census"] for m in munis.values())
    for party, n in national.items():
        rows.append(("ES", process, date, "national", "ES", "Espanya",
                     party, n, total_valid, total_census, "infoelectoral"))

    conn.execute("DELETE FROM election_result WHERE country='ES' AND election = ?", (process,))
    conn.executemany(
        """INSERT INTO election_result
           (country, election, date, level, code, name, party, votes, valid_votes, census, source)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""", rows)
    conn.commit()
    return len(rows), len(munis)
