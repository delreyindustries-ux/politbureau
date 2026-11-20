"""Qui governa el mon (21/11/2026): el cap de govern de cada pais, per familia
politica, i quina part de la poblacio i de l'economia del mon governa cadascuna.

Idea presa d'un simulador electoral (canviar qui governa un pais i veure com es
mou el total), feta amb dades propies: Wikidata (CC0).

  * Cap de govern: P6 sense data de final. Si n'hi ha mes d'un (Wikidata te
    declaracions velles sense tancar), el de la data d'inici mes recent. Si
    l'unica data es de fa mes de dos anys i hi ha un altre nom sense data, el
    pais queda marcat com a dubtos.
  * Partit: P102 vigent del cap de govern. Posicio: P1387 del partit, passada a
    una escala de -3 (extrema esquerra) a +3 (extrema dreta); si en te
    diverses, la mediana.
  * Poblacio (P1082) i PIB nominal (P2131): el valor preferent mes alt.

`politbureau governs` -> data/governs/governs.json (va al repositori).
"""
from __future__ import annotations

import datetime as dt
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1].parent
OUT = ROOT / "data" / "governs" / "governs.json"

POSITION = {
    "far-left politics": -3, "far-left": -3,
    "left-wing politics": -2, "left-wing": -2, "left-wing populism": -2,
    "centre-left politics": -1, "centre-left": -1,
    "centrism": 0, "centre": 0, "big tent": 0, "syncretic politics": 0, "radical centrism": 0,
    "centre-right politics": 1, "centre-right": 1,
    "right-wing politics": 2, "right-wing": 2, "right-libertarianism": 2, "right-wing populism": 2,
    "far-right politics": 3, "far-right": 3, "right-wing extremism": 3, "alt-right": 3,
    "radical right": 3,
}

Q_HEADS = """
SELECT ?num ?iso ?h ?hLabel ?start ?p ?pLabel ?posEn WHERE {
  ?c wdt:P31 wd:Q3624078 ; wdt:P299 ?num ; wdt:P297 ?iso .
  FILTER NOT EXISTS { ?c wdt:P576 [] }
  ?c p:P6 ?st . ?st ps:P6 ?h . FILTER NOT EXISTS { ?st pq:P582 [] }
  OPTIONAL { ?st pq:P580 ?start }
  OPTIONAL { ?h p:P102 ?ps . ?ps ps:P102 ?p . FILTER NOT EXISTS { ?ps pq:P582 [] }
             OPTIONAL { ?p wdt:P1387 ?pos . ?pos rdfs:label ?posEn FILTER(LANG(?posEn) = "en") } }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "es,en". }
}"""

Q_COUNTRIES = """
SELECT ?num ?iso ?ca ?es ?pop ?gdp WHERE {
  ?c wdt:P31 wd:Q3624078 ; wdt:P299 ?num ; wdt:P297 ?iso .
  FILTER NOT EXISTS { ?c wdt:P576 [] }
  OPTIONAL { ?c rdfs:label ?ca FILTER(LANG(?ca) = "ca") }
  OPTIONAL { ?c rdfs:label ?es FILTER(LANG(?es) = "es") }
  OPTIONAL { ?c wdt:P1082 ?pop }
  OPTIONAL { ?c wdt:P2131 ?gdp }
}"""


def _sparql(q):
    from .results import _sparql as run
    return run(q)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def run() -> dict:
    countries: dict = {}
    for b in _sparql(Q_COUNTRIES):
        num = b["num"]["value"].zfill(3)
        c = countries.setdefault(num, {"iso": b["iso"]["value"], "name": {}, "pop": 0, "gdp": 0})
        for lg in ("ca", "es"):
            if b.get(lg):
                c["name"][lg] = b[lg]["value"]
        c["pop"] = max(c["pop"], _num((b.get("pop") or {}).get("value")) or 0)
        c["gdp"] = max(c["gdp"], _num((b.get("gdp") or {}).get("value")) or 0)
    heads: dict = {}
    for b in _sparql(Q_HEADS):
        num = b["num"]["value"].zfill(3)
        h = heads.setdefault(num, {}).setdefault(b["h"]["value"], {
            "name": b["hLabel"]["value"], "start": (b.get("start") or {}).get("value", "")[:10],
            "party": None, "pos": []})
        if b.get("pLabel") and not h["party"]:
            h["party"] = b["pLabel"]["value"]
        lab = ((b.get("posEn") or {}).get("value") or "").lower()
        if lab in POSITION and POSITION[lab] not in h["pos"]:
            h["pos"].append(POSITION[lab])
    today = dt.date.today()
    for num, hs in heads.items():
        c = countries.get(num)
        if not c:
            continue
        dated = [h for h in hs.values() if h["start"]]
        undated = [h for h in hs.values() if not h["start"]]
        pick = max(dated, key=lambda h: h["start"]) if dated else undated[0]
        doubt = bool(dated and undated and
                     (today - dt.date.fromisoformat(pick["start"])).days > 730) or (not dated and len(undated) > 1)
        score = round(statistics.median(pick["pos"])) if pick["pos"] else None
        c.update({"head": pick["name"], "party": pick["party"], "score": score, "doubt": doubt})
    data = {"computed": today.isoformat(), "source": "Wikidata (CC0)", "countries": countries}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return data


def load() -> dict:
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
