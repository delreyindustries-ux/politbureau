"""Perfil dels candidats que entrarien al Congres (15/11/2026).

A l'hemicicle de la web cada escó es d'una persona: el numero k de la llista
proclamada (BOE) ocupa l'escó k que el partit guanya a la provincia. Aqui es
busca el curriculum de cadascuna a Wikidata (domini public, CC0): any i lloc de
naixement, estudis, professio i carrecs.

ATENCIO AMB ELS HOMONIMS. Posar el curriculum d'una altra persona a un
candidat seria greu. Nomes s'accepta una fitxa de Wikidata si:

  A) el nom complet (nom i dos cognoms) coincideix amb l'etiqueta o un alies,
     es una persona amb any de naixement, politic espanyol, i Wikidata no li
     dona un partit diferent del de la llista; o
  B) l'etiqueta es "nom + primer cognom", es politic, espanyol, viu, i el seu
     partit a Wikidata (P102) es el de la llista.

En cas de dubte (dues fitxes possibles, o cap senyal), el candidat es queda
sense curriculum: surt amb la provincia i el lloc a la llista, que venen del
BOE.

`politbureau perfils` ho desa a config/profiles.json; la web nomes llegeix
aquest fitxer, aixi la generacio no depen de la xarxa.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
import unicodedata
from pathlib import Path

import requests

from . import candidatures
from .ideology import WD, _values

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "config" / "profiles.json"
EXTRA = 2             # candidats de mes per llista, per si l'estimacio es mou
LANGS = ("es", "ca")
HUMAN, SPAIN, POLITICIAN = "Q5", "Q29", "Q82955"

# Paraules que ha de portar el nom del partit a Wikidata (P102) per donar per
# bona una coincidencia de tipus B. Sense entrada: nomes coincidencia A.
PARTY_WORDS = {
    "PSOE": ("socialista", "socialistes", "psoe", "psc"),
    "PP": ("partido popular", "partit popular", "people's party"),
    "VOX": ("vox",),
    "SUMAR": ("sumar", "izquierda unida", "esquerra unida", "comuns", "compromís", "más madrid",
              "catalunya en comú", "podemos", "chunta", "més per"),
    "PODEMOS": ("podemos", "podem"),
    "ERC": ("esquerra republicana",),
    "JUNTS": ("junts", "convergència", "pdecat", "partit demòcrata"),
    "EHB": ("bildu", "sortu", "eusko alkartasuna", "aralar"),
    "PNV": ("nacionalista vasco", "eaj", "euzko alderdi"),
    "BNG": ("bloque nacionalista galego",),
    "CC": ("coalición canaria",),
    "UPN": ("unión del pueblo navarro",),
}


def fold(text: str) -> str:
    t = unicodedata.normalize("NFKD", text or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def wanted(conn) -> list[dict]:
    """Candidats que entrarien avui, mes `EXTRA` per llista."""
    proj: dict = {}
    for r in conn.execute(
            """SELECT code, party, seats FROM seat_projection
               WHERE election_id = 'es-general' AND level = 'province'"""):
        proj.setdefault(r["code"], {})[r["party"]] = r["seats"]
    out = []
    for prov, by_party in candidatures.lists().items():
        for party, members in by_party.items():
            n = proj.get(prov, {}).get(party, 0)
            if not n:
                continue
            for m in members[:n + EXTRA]:
                out.append({"name": m["name"], "party": party, "province": prov})
    return out


def _labels(entity) -> set[str]:
    out = set()
    for lang, v in (entity.get("labels") or {}).items():
        out.add(fold(v.get("value", "")))
    for lang, vs in (entity.get("aliases") or {}).items():
        for v in vs:
            out.add(fold(v.get("value", "")))
    out.discard("")
    return out


def _year(entity, prop):
    for c in (entity.get("claims") or {}).get(prop, []):
        v = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(v, dict) and v.get("time"):
            m = re.match(r"[+-](\d{4})", v["time"])
            if m:
                return int(m.group(1))
    return None


def _ids(entity, prop):
    return [q for q, _ in _values(entity, prop)]


def match(person: dict, entities: list[dict], names: dict) -> dict | None:
    """L'entitat de Wikidata d'un candidat, o None si no es segur."""
    full = fold(person["name"])
    tokens = full.split()
    words = PARTY_WORDS.get(person["party"])
    good = []
    for e in entities:
        if HUMAN not in _ids(e, "P31"):
            continue
        if _year(e, "P570"):                     # mort
            continue
        # Sense any de naixement no es pot descartar un diputat del segle XIX
        # amb el mateix nom (n'hi ha molts sense dates a Wikidata): fora.
        born = _year(e, "P569")
        if not born or not (1935 <= born <= dt.date.today().year - 18):
            continue
        labels = _labels(e)
        politician = POLITICIAN in _ids(e, "P106") or bool((e.get("claims") or {}).get("P39"))
        spanish = SPAIN in _ids(e, "P27")
        party_ok = bool(words) and any(
            any(w in (names.get(q, {}).get("es", "") + " " + names.get(q, {}).get("ca", "")).lower()
                for w in words) for q in _ids(e, "P102"))
        # Si Wikidata li dona un partit i no es el de la llista, es un altre
        # (o ha canviat de partit i no ho podem saber): fora.
        conflict = bool(words) and bool(_ids(e, "P102")) and not party_ok
        if full in labels and (politician or spanish or party_ok) and not conflict:
            good.append((0, e))
        elif len(tokens) >= 3 and politician and spanish and party_ok and any(
                len(lb.split()) >= 2 and full.startswith(lb + " ") for lb in labels):
            good.append((1, e))
    if not good:
        return None
    best = min(t for t, _ in good)
    top = [e for t, e in good if t == best]
    return top[0] if len(top) == 1 else None      # dues fitxes possibles: cap


def _name(names, q, lang):
    n = names.get(q) or {}
    return n.get(lang) or n.get("es") or n.get("ca") or n.get("en")


def profile(e: dict, names: dict) -> dict:
    out: dict = {"qid": e["id"], "born": _year(e, "P569")}
    for lang in LANGS:
        d = ((e.get("descriptions") or {}).get(lang) or {}).get("value")
        place = next((_name(names, q, lang) for q in _ids(e, "P19")), None)

        def lst(prop, cap):
            seen, vals = set(), []
            for q in _ids(e, prop):
                v = _name(names, q, lang)
                if v and v.lower() not in seen:
                    seen.add(v.lower())
                    vals.append(v)
            return vals[:cap]
        out[lang] = {k: v for k, v in {
            "desc": d, "place": place, "studies": lst("P69", 3), "jobs": lst("P106", 4),
            "posts": lst("P39", 6),
            "wiki": ((e.get("sitelinks") or {}).get(lang + "wiki") or {}).get("title"),
        }.items() if v}
    return out


SPARQL = "https://query.wikidata.org/sparql"
# Tots els politics espanyols vius, d'una sola consulta. Buscar els candidats
# d'un en un (1.300 cerques) fa que Wikidata talli amb un 429.
QUERY = """SELECT ?p ?l WHERE {
  ?p wdt:P106 wd:Q82955 ; wdt:P27 wd:Q29 ; %s ?l .
  FILTER(LANG(?l) = "es")
  FILTER NOT EXISTS { ?p wdt:P570 [] }
}"""


def _index(session) -> dict[str, set[str]]:
    """{nom sense accents: {Q...}} amb etiquetes i alies en castella."""
    from . import wikipedia as wk
    out: dict[str, set[str]] = {}
    for pred in ("rdfs:label", "skos:altLabel"):
        r = session.get(SPARQL, params={"query": QUERY % pred, "format": "json"},
                        headers={"User-Agent": wk.USER_AGENT}, timeout=180)
        r.raise_for_status()
        for b in r.json()["results"]["bindings"]:
            key = fold(b["l"]["value"])
            if key:
                out.setdefault(key, set()).add(b["p"]["value"].rsplit("/", 1)[-1])
        time.sleep(2)
    return out


def _fetch(session, ids, props):
    """wbgetentities de 50 en 50, a poc a poc i respectant el Retry-After."""
    from . import wikipedia as wk
    out, ids = {}, sorted(set(ids))
    for i in range(0, len(ids), 50):
        for attempt in range(6):
            r = session.get(WD, params={"action": "wbgetentities", "ids": "|".join(ids[i:i + 50]),
                                        "props": props, "languages": "es|ca", "format": "json",
                                        "formatversion": 2},
                            headers={"User-Agent": wk.USER_AGENT}, timeout=60)
            if r.status_code == 200 and r.text.startswith("{"):
                out.update(r.json().get("entities") or {})
                break
            time.sleep(min(60, float(r.headers.get("Retry-After") or 10 * (attempt + 1))))
        else:
            r.raise_for_status()
        time.sleep(1.5)
    return out


def run(conn) -> dict:
    session = requests.Session()
    people = wanted(conn)
    index = _index(session)
    print(f"  index: {len(index)} noms de politics espanyols a Wikidata", flush=True)
    # 1) candidats possibles: el nom complet, o "nom + primer cognom"
    hits: dict[str, list[str]] = {}
    for p in people:
        key = fold(p["name"])
        tokens = key.split()
        ids = set(index.get(key, ()))
        for n in range(2, len(tokens)):
            ids |= index.get(" ".join(tokens[:n]), set())
        hits[key] = sorted(ids)
    # 2) les entitats, amb etiquetes, alies, descripcions i enllacos
    ents = _fetch(session, {q for ids in hits.values() for q in ids},
                  "claims|labels|aliases|descriptions|sitelinks")
    print(f"  {len(ents)} fitxes llegides", flush=True)
    # 3) noms dels valors que es mostren o que es fan servir per decidir
    refs = set()
    for e in ents.values():
        for prop in ("P102", "P19", "P69", "P106", "P39"):
            refs.update(_ids(e, prop))
    names = {}
    for q, e in _fetch(session, refs, "labels").items():
        names[q] = {lg: v.get("value") for lg, v in (e.get("labels") or {}).items()}
    out, n = {}, 0
    for p in people:
        key = fold(p["name"])
        e = match(p, [ents[q] for q in hits.get(key, []) if q in ents], names)
        if e:
            out[key] = profile(e, names)
            n += 1
    data = {"computed": dt.date.today().isoformat(),
            "source": "Wikidata (CC0)", "searched": len(people), "found": n, "people": out}
    OUT.write_bytes(json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8"))
    return data


def load() -> dict:
    try:
        return json.loads(OUT.read_text(encoding="utf-8")).get("people") or {}
    except (OSError, ValueError):
        return {}
