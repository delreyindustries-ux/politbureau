"""Dades de les municipals del 23/05/2027, municipi a municipi (19/11/2026).

Per a cada un dels 8.131 municipis:

  * Resultat del 28/05/2023: vots i regidors de cada candidatura. Ministeri de
    l'Interior, fitxers de la carpeta data/raw (04202305_MUNI.zip):
      - fitxer 06: vots i electes per candidatura als municipis de mes de 250
        habitants (llistes tancades);
      - fitxer 12: candidat a candidat als de 250 o menys (llistes obertes), amb
        la marca d'electe ('S'). Alla no se sumen vots per partit: cada elector
        pot votar diversos candidats i la suma no vol dir res.
  * Poblacio oficial de l'INE (Revisio del Padro, taula 29005, l'ultima
    publicada) i els regidors que li toquen segons l'escala de la LOREG (art.
    179), la mateixa que reprodueix Wikipedia a cada article de les municipals.

ATENCIO: els regidors del 2027 es fixen amb el padro de l'1/1/2026, que l'INE
publica al desembre del 2026. Fins aleshores es calculen amb l'ultim publicat
(1/1/2025) i el fitxer ho diu (`pop_year`). Cal tornar-ho a executar quan surti:
`politbureau municipals`.

Escriu data/municipals/municipis.json (va al repositori: la web no depen de cap
servidor alie per generar-se).
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "municipals" / "municipis.json"
INE = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/29005?nult=1&tip=AM"
UA = {"User-Agent": "politbureau (politbureau.es)"}


def councillors(pop: int) -> int:
    """Regidors segons la poblacio (LOREG art. 179.1)."""
    for limit, n in ((100, 3), (250, 5), (1000, 7), (2000, 9), (5000, 11), (10000, 13),
                     (20000, 17), (50000, 21), (100000, 25)):
        if pop <= limit:
            return n
    n = 25 + math.ceil((pop - 100000) / 100000)
    return n + 1 if n % 2 == 0 else n


def population(session=None) -> tuple[dict, int]:
    """({codi INE: habitants}, any) de l'ultima Revisio del Padro de l'INE."""
    import requests
    s = session or requests.Session()
    r = s.get(INE, headers=UA, timeout=300)
    r.raise_for_status()
    out, year = {}, None
    for row in r.json():
        meta = {m["T3_Variable"]: m for m in row.get("MetaData") or []}
        if (meta.get("Sexo") or {}).get("Codigo") != "0":
            continue
        code = (meta.get("Municipios") or {}).get("Codigo")
        data = (row.get("Data") or [None])[0]
        if not code or len(code) != 5 or not data or data.get("Valor") is None:
            continue
        out[code] = int(data["Valor"])
        year = data.get("Anyo") or year
    return out, year


def results_2023() -> dict:
    """{codi: {"n": nom, "v": vots valids o None, "r": [[sigla, codi, vots, regidors]]}}."""
    from . import parties
    from .ingest import infoelectoral as ie
    tipo, year, month = ie.PROCESSES["municipales-2023"]
    zf = ie.download("municipales-2023")
    munis = ie.municipalities(zf, tipo, year, month)
    sig = ie.candidacies(zf, tipo, year, month)
    out: dict = {}
    for code, m in munis.items():
        out[code] = {"n": m["name"], "v": m["valid"], "r": {}}
    # Mes de 250 habitants: vots i electes per candidatura (fitxer 06).
    for rec in ie._records(ie._member(zf, "06", tipo, year, month), 33):
        if rec[14:16] != "99":
            continue
        code, cand = rec[9:11] + rec[11:14], rec[16:22]
        votes, won = int(rec[22:30]), int(rec[30:33])
        row = out.setdefault(code, {"n": "", "v": None, "r": {}})["r"].setdefault(cand, [0, 0])
        row[0] += votes
        row[1] += won
    # 250 habitants o menys: candidat a candidat (fitxer 12), electes marcats 'S'.
    # Format (FICHEROS.doc del mateix ZIP): tipus(2) any(4) mes(2) volta(1)
    # provincia(2) municipi(3) candidatura(6) vots de la candidatura(3)
    # regidors de la candidatura(2) i despres el candidat. Aquest fitxer acaba
    # les linies amb CR+LF: per aixo splitlines i no _records.
    small = set()
    for rec in ie._member(zf, "12", tipo, year, month).decode("latin-1").splitlines():
        if len(rec) < 25:
            continue
        code, cand = rec[9:11] + rec[11:14], rec[14:20]
        small.add(code)
        entry = out.setdefault(code, {"n": "", "v": None, "r": {}})
        entry["r"][cand] = [None, int(rec[23:25])]
    for code in small:
        out[code]["v"] = None                 # llistes obertes: sense vot per partit
        out[code]["open"] = True
    for code, entry in out.items():
        rows = []
        for cand, (votes, won) in entry["r"].items():
            name = sig.get(cand, cand)
            rows.append([name, parties.resolve(name, "ES")[0], votes, won])
        rows.sort(key=lambda r: (-r[3], -(r[2] or 0)))
        entry["r"] = rows
    return out


def run() -> dict:
    pop, pop_year = population()
    res = results_2023()
    munis = {}
    for code in sorted(set(pop) | set(res)):
        r = res.get(code) or {}
        p = pop.get(code)
        won = sum(x[3] for x in r.get("r", []))
        munis[code] = {k: v for k, v in {
            "n": r.get("n") or None, "pop": p,
            "s27": councillors(p) if p else None,
            "s23": won or None, "v": r.get("v"), "open": r.get("open"),
            "r": r.get("r") or None}.items() if v is not None}
    data = {"computed": dt.date.today().isoformat(), "election": "2027-05-23",
            "pop_year": pop_year,
            "sources": {
                "results": "Ministerio del Interior, infoelectoral (04202305_MUNI.zip)",
                "population": f"INE, Revisión del Padrón Municipal a 1/1/{pop_year} (tabla 29005)",
                "scale": "LOREG, art. 179.1"},
            "munis": munis}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return data


_CACHE = None


def load() -> dict:
    global _CACHE
    if _CACHE is None:
        try:
            _CACHE = json.loads(OUT.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _CACHE = {}
    return _CACHE
