"""Qui seu avui a cada parlament estranger (26/11/2026, demanat per l'Alfonso:
"adapta totes les dades que puguis d'Espanya a altres paisos" -> fitxa de cada
escó, com al Congres).

Tot de Wikidata (CC0): les persones amb el carrec de diputat de la cambra
(P39) obert (sense data de fi) i vives, el seu partit (P102 sense data de fi),
la circumscripcio (P768), i el curriculum (naixement, estudis, professio).

Nomes es publica un pais si Wikidata hi te la cambra sencera: entre el 90 % i
el 105 % dels escons. Primer es proven els mandats que van comencar despres de
les darreres eleccions; si no surten, tots els mandats oberts, pero nomes si el
80 % o mes tenen data d'inici. Si no quadra,
el pais es queda sense fitxes (millor res que una cambra a mitges). Tambe si
mes del 20 % no hi tenen partit.

`politbureau diputats-mon` ho desa a config/mps_world.json; la web nomes
llegeix aquest fitxer.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests

from . import results

ROOT = Path(__file__).resolve().parents[1].parent
OUT = ROOT / "config" / "mps_world.json"
ENDPOINT = "https://query.wikidata.org/sparql"

# Carrec de diputat de la cambra baixa (o unica) de cada pais, comprovat a ma a
# Wikidata el 26/11/2026. El Regne Unit fa servir un carrec per legislatura.
POSITIONS = {
    "AT": "Q17535155", "AU": "Q18912794", "BE": "Q15705021", "DE": "Q1939555", "EE": "Q21100241",
    "FI": "Q17592486", "GB": "Q126063447", "GM": "Q21295984", "GR": "Q18915989", "HR": "Q18643511",
    "IE": "Q654291", "IS": "Q21272959", "LT": "Q18507240", "LU": "Q21328592", "MD": "Q18390049",
    "NO": "Q9045502", "NZ": "Q18145518", "PT": "Q19953703", "SE": "Q10655178", "SI": "Q21296001",
    "SK": "Q19967563", "SV": "Q21328618", "TR": "Q21030356",
}
LOW, HIGH = 0.90, 1.05

# Alineament politic (P1387), per la seva etiqueta castellana a Wikidata ->
# posicio de render._POSITION, per asseure els grups d'esquerra a dreta.
ALIGN = {"extrema izquierda": "extrema izquierda", "izquierda radical": "izquierda radical",
         "izquierda": "izquierda", "centroizquierda": "centroizquierda", "centro": "centrismo",
         "centrismo": "centrismo", "centroderecha": "centroderecha", "derecha": "derecha",
         "extrema derecha": "extrema derecha", "derecha radical": "extrema derecha",
         "izquierda política": "izquierda", "derecha política": "derecha"}


def _post(query: str) -> list[dict]:
    for attempt in range(4):
        try:
            r = requests.post(ENDPOINT, data={"query": query, "format": "json"},
                              headers={**results.UA, "Accept": "application/sparql-results+json"}, timeout=180)
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(30 * (attempt + 1))            # la xarxa ha caigut: espera i torna-hi
            continue
        if r.status_code in (429, 500, 502, 503, 504) and attempt < 3:
            time.sleep(15 * (attempt + 1))
            continue
        r.raise_for_status()
        time.sleep(1.5)                                   # educat amb el servei
        return r.json()["results"]["bindings"]
    return []


def _q(b, k):
    v = b.get(k, {}).get("value")
    return v.rsplit("/", 1)[1] if v and v.startswith("http://www.wikidata.org/entity/") else v


def _members(pos: str) -> dict:
    rows = _post(f"""SELECT ?p ?name ?s ?dist ?distLabel ?born ?roleL WHERE {{
  ?p p:P39 ?st . ?st ps:P39 wd:{pos} . FILTER NOT EXISTS {{ ?st pq:P582 ?e }}
  FILTER NOT EXISTS {{ ?p wdt:P570 ?dd }}
  OPTIONAL {{ ?st pq:P580 ?s }} OPTIONAL {{ ?st pq:P768 ?dist }} OPTIONAL {{ ?p wdt:P569 ?born }}
  OPTIONAL {{ ?p rdfs:label ?name . FILTER(LANG(?name) = "mul") }}
  OPTIONAL {{ ?st pq:P2868 ?role . ?role rdfs:label ?roleL . FILTER(LANG(?roleL) = "en") }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,mul,de,sv,fr,nl,ga,ca,es". ?dist rdfs:label ?distLabel . }}
}}""")
    out, subs = {}, set()
    for b in rows:
        q = _q(b, "p")
        # Suplents (Noruega: "permanent deputy member"): no son els elegits.
        if re.search(r"deputy|substitute|alternate", (b.get("roleL") or {}).get("value", ""), re.I):
            subs.add(q)
        m = out.setdefault(q, {"qid": q, "starts": set(), "dist": None, "born": None, "name": None})
        if b.get("s"):
            m["starts"].add(b["s"]["value"][:10])
        if b.get("distLabel") and not m["dist"] and not re.fullmatch(r"Q\d+", b["distLabel"]["value"]):
            m["dist"] = b["distLabel"]["value"]
        if b.get("born") and not m["born"]:
            m["born"] = b["born"]["value"][:4]
        if b.get("name") and not m["name"]:
            m["name"] = b["name"]["value"]
    return {q: m for q, m in out.items() if q not in subs}


def _labels(pos: str) -> dict:
    """Nom de cada diputat (mul o angles; si no, ca/es)."""
    rows = _post(f"""SELECT ?p ?l WHERE {{
  ?p p:P39 ?st . ?st ps:P39 wd:{pos} . FILTER NOT EXISTS {{ ?st pq:P582 ?e }}
  FILTER NOT EXISTS {{ ?p wdt:P570 ?dd }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "mul,en,ca,es". ?p rdfs:label ?l . }}
}}""")
    return {_q(b, "p"): b["l"]["value"] for b in rows if b.get("l")}


def _parties(pos: str) -> dict:
    """{persona: [(partit, inici)]}: afiliacions sense data de fi."""
    rows = _post(f"""SELECT ?p ?party ?s WHERE {{
  ?p p:P39 ?st . ?st ps:P39 wd:{pos} . FILTER NOT EXISTS {{ ?st pq:P582 ?e }}
  FILTER NOT EXISTS {{ ?p wdt:P570 ?dd }}
  ?p p:P102 ?ps . ?ps ps:P102 ?party . FILTER NOT EXISTS {{ ?ps pq:P582 ?pe }}
  FILTER NOT EXISTS {{ ?ps wikibase:rank wikibase:DeprecatedRank }}
  OPTIONAL {{ ?ps pq:P580 ?s }}
}}""")
    out = defaultdict(list)
    for b in rows:
        out[_q(b, "p")].append((_q(b, "party"), (b.get("s") or {}).get("value", "")[:10]))
    return out


def _bios(pos: str) -> dict:
    out = defaultdict(dict)
    for lang in ("ca", "es"):
        rows = _post(f"""SELECT ?p ?desc ?placeL ?wiki
       (GROUP_CONCAT(DISTINCT ?eduL; separator="|") AS ?edu) (GROUP_CONCAT(DISTINCT ?jobL; separator="|") AS ?job) WHERE {{
  ?p p:P39 ?st . ?st ps:P39 wd:{pos} . FILTER NOT EXISTS {{ ?st pq:P582 ?e }}
  FILTER NOT EXISTS {{ ?p wdt:P570 ?dd }}
  OPTIONAL {{ ?p schema:description ?desc . FILTER(LANG(?desc) = "{lang}") }}
  OPTIONAL {{ ?p wdt:P19 ?place . ?place rdfs:label ?placeL . FILTER(LANG(?placeL) = "{lang}") }}
  OPTIONAL {{ ?p wdt:P69 ?eduI . ?eduI rdfs:label ?eduL . FILTER(LANG(?eduL) = "{lang}") }}
  OPTIONAL {{ ?p wdt:P106 ?jobI . ?jobI rdfs:label ?jobL . FILTER(LANG(?jobL) = "{lang}") }}
  OPTIONAL {{ ?art schema:about ?p ; schema:isPartOf <https://{lang}.wikipedia.org/> ; schema:name ?wiki }}
}} GROUP BY ?p ?desc ?placeL ?wiki""")
        for b in rows:
            d = out[_q(b, "p")].setdefault(lang, {})
            for k, src in (("desc", "desc"), ("place", "placeL"), ("wiki", "wiki")):
                if b.get(src) and not d.get(k):
                    d[k] = b[src]["value"]
            for k, src in (("studies", "edu"), ("jobs", "job")):
                vals = [x for x in (b.get(src) or {}).get("value", "").split("|") if x]
                if vals and not d.get(k):
                    d[k] = sorted(vals)[:4]
    return out


def _party_info(qids: list[str]) -> dict:
    if not qids:
        return {}
    vals = " ".join(f"wd:{q}" for q in qids)
    rows = _post(f"""SELECT ?x ?ca ?es ?en ?short ?color ?align WHERE {{
  VALUES ?x {{ {vals} }}
  OPTIONAL {{ ?x rdfs:label ?ca . FILTER(LANG(?ca) = "ca") }}
  OPTIONAL {{ ?x rdfs:label ?es . FILTER(LANG(?es) = "es") }}
  OPTIONAL {{ ?x rdfs:label ?en . FILTER(LANG(?en) IN ("en", "mul")) }}
  OPTIONAL {{ ?x wdt:P1813 ?short . FILTER(LANG(?short) IN ("en", "mul", "")) }}
  OPTIONAL {{ ?x wdt:P465 ?color }}
  OPTIONAL {{ ?x wdt:P1387 ?al . ?al rdfs:label ?align . FILTER(LANG(?align) = "es") }}
}}""")
    out = {}
    for b in rows:
        q = _q(b, "x")
        d = out.setdefault(q, {"qid": q, "align": []})
        for k in ("ca", "es", "en", "short", "color"):
            if b.get(k) and not d.get(k):
                d[k] = b[k]["value"]
        if b.get("align"):
            d["align"].append(b["align"]["value"].lower())
    return out


def _position(aligns: list[str]) -> str | None:
    for a in aligns:
        if a in ALIGN:
            return ALIGN[a]
    return None


def country(iso: str, pos: str, seats: int, election: str) -> dict | None:
    ms = _members(pos)
    since = (dt.date.fromisoformat(election) - dt.timedelta(days=40)).isoformat()
    recent = {q: m for q, m in ms.items() if any(s >= since for s in m["starts"])}
    pick, rule = None, None
    # Els mandats oberts nomes valen si gairebe tots tenen data d'inici: un mandat
    # sense inici ni fi pot ser d'un exdiputat a qui Wikidata no ha tancat el carrec.
    dated = sum(1 for m in ms.values() if m["starts"]) / len(ms) if ms else 0
    for cand, name in ((recent, "despres de les eleccions"), (ms if dated >= 0.8 else {}, "mandats oberts")):
        if LOW * seats <= len(cand) <= HIGH * seats:
            pick, rule = cand, name
            break
    print(f"  {iso}: {len(recent)} recents, {len(ms)} oberts, {seats} escons -> "
          f"{'ok (' + rule + ')' if pick else 'no quadra'}", flush=True)
    if not pick:
        return None
    names = _labels(pos)
    aff = _parties(pos)
    bios = _bios(pos)
    # El partit de cada diputat: el mes comu a la cambra d'entre els seus oberts
    # (aixi qui te el partit i la federacio regional queda amb el gran).
    freq = Counter(p for q in pick for p, _s in aff.get(q, []))
    party_of = {}
    for q in pick:
        opts = aff.get(q) or []
        if opts:
            party_of[q] = max(opts, key=lambda ps: (freq[ps[0]], ps[1]))[0]
    info = _party_info(sorted({p for p in party_of.values() if p}))
    groups = defaultdict(list)
    for q, m in pick.items():
        name = names.get(q) or m["name"]
        if not name or name == q:
            continue
        row = {"n": name, "qid": q}
        if m["dist"]:
            row["w"] = m["dist"]
        bio = {}
        for lang in ("ca", "es"):
            b = dict((bios.get(q) or {}).get(lang) or {})
            if m["born"]:
                b["born"] = m["born"]
            if b:
                bio[lang] = b
        if bio:
            row["bio"] = bio
        groups[party_of.get(q) or ""].append(row)
    out = []
    for p, members in groups.items():
        i = info.get(p) or {}
        out.append({"qid": p or None, "ca": i.get("ca") or i.get("en"), "es": i.get("es") or i.get("en"),
                    "short": i.get("short"), "color": ("#" + i["color"]) if i.get("color") else None,
                    "position": _position(i.get("align") or []),
                    "members": sorted(members, key=lambda r: r["n"])})
    out.sort(key=lambda g: (-len(g["members"]), g["ca"] or "~"))
    total = sum(len(g["members"]) for g in out)
    unknown = sum(len(g["members"]) for g in out if not g["qid"])
    if total and unknown / total > 0.2:
        print(f"  {iso}: {unknown} de {total} sense partit a Wikidata -> fora", flush=True)
        return None
    return {"position": pos, "rule": rule, "seats": seats, "election": election,
            "count": sum(len(g["members"]) for g in out), "groups": out}


def run(only: set[str] | None = None) -> dict:
    parl = results.load().get("parliaments") or {}
    data = load() if only else {}
    data.setdefault("countries", {})
    for iso, pos in sorted(POSITIONS.items()):
        if (only and iso not in only) or iso not in parl or iso in results.EXCLUDED:
            continue
        p = parl[iso]
        try:
            got = country(iso, pos, int(p["seats_total"]), p["date"])
        except Exception as exc:                      # noqa: BLE001
            print(f"  {iso}: error {str(exc)[:80]}", flush=True)
            continue
        if got:
            data["countries"][iso] = got
        else:
            data["countries"].pop(iso, None)
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    data["built"] = dt.date.today().isoformat()
    data["source"] = "Wikidata (CC0)"
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def load() -> dict:
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
