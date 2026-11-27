"""Resultats historics de les eleccions legislatives de cada pais (26/11/2026,
demanat per l'Alfonso: "adapta totes les dades que puguis d'Espanya a altres
paisos").

Com la pagina d'historia d'Espanya, pero amb el que hi ha a l'abast amb
llicencia clara:
  * quines eleccions: Wikidata (CC0), eleccions legislatives (Q1076105) des
    del 2000 amb article a la Viquipedia anglesa (results.elections);
  * el resultat: el quadre resum (infobox) de cada article (Viquipedia, CC BY-SA
    4.0): partit, % de vot, escons, participacio (results.infobox).
Nomes els partits que surten al quadre resum (els principals). Si els escons no
sumen la cambra, es desen igualment el vot i la participacio, sense escons.

Es desa a config/historic_world.json (va al repositori: no canvia gaire i la
publicacio no depen de la Viquipedia). `politbureau historic-mon`.
"""
from __future__ import annotations

import datetime as dt
import time
import json
from pathlib import Path

from . import results

ROOT = Path(__file__).resolve().parents[1].parent
OUT = ROOT / "config" / "historic_world.json"
SINCE = "2000-01-01"


def run(only: set[str] | None = None, resume: bool = False) -> dict:
    ours = results.our_countries() - results.EXCLUDED
    if only:
        ours &= only
    chambers = results._chamber_totals()
    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"countries": {}}
    data.setdefault("countries", {})
    if not only:
        done = set(data["countries"]) if resume else set()
        ours -= done
    els = [e for e in results.elections(SINCE) if e["kind"] == "leg" and e["iso"] in ours]
    by = {}
    for e in sorted(els, key=lambda e: e["date"]):
        by.setdefault(e["iso"], []).append(e)
    print(f"  {len(els)} eleccions de {len(by)} paisos", flush=True)
    for iso, lst in sorted(by.items()):
        rows = []
        seen = set()
        for e in lst:
            if e["title"] in seen:
                continue
            seen.add(e["title"])
            print(f"    {iso} {e['date']} {e['title'][:60]}", flush=True)
            box = None
            for attempt in range(3):
                try:
                    box = results.infobox(e["title"], "leg")
                    break
                except Exception:                      # noqa: BLE001  (xarxa caiguda: espera i torna-hi)
                    time.sleep(30 * (attempt + 1))
            if not box or not box["rows"]:
                continue
            total = box["seats_total"] or chambers.get(iso)
            got = sum(r["seats"] or 0 for r in box["rows"])
            seats_ok = bool(total) and 0.85 * total <= got <= 1.02 * total
            turnout = box.get("turnout")
            if turnout is not None and not 10 <= turnout <= 100:
                turnout = None                     # a vegades el quadre porta els vots, no el %
            rows.append({"date": e["date"], "title": e["title"], "turnout": turnout,
                         "seats_total": total if seats_ok else None,
                         "parties": [{"name": r["name"], "pct": r["pct"], "seats": r["seats"] if seats_ok else None}
                                     for r in box["rows"] if r["pct"] is not None or r["seats"]]})
        if rows:
            data["countries"][iso] = rows
            print(f"  {iso}: {len(rows)} eleccions ({rows[0]['date'][:4]}-{rows[-1]['date'][:4]})", flush=True)
            OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")   # desa a cada pais
    data["built"] = dt.date.today().isoformat()
    data["source"] = "Wikidata (CC0) i quadres resum de la Viquipèdia anglesa (CC BY-SA 4.0)"
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def clean(rows: list[dict]) -> list[dict]:
    """Treu el que no es pot ensenyar amb seguretat:
      * la participacio fora del 10-100 % (alguns quadres hi porten els vots);
      * les eleccions on els partits sumen mes del 102 % (quadres amb coalicions
        i partits alhora, o dues cambres: Argentina);
      * les eleccions on algun dels tres primers no te %;
      * dues entrades amb la mateixa data (dos articles de la mateixa eleccio)."""
    out, seen = [], set()
    for r in sorted(rows, key=lambda r: (r["date"], len(r["title"]))):   # el titol curt es l'article de l'eleccio
        if r["date"] in seen:
            continue
        ps = r["parties"]
        if any("=" in p["name"] or " | " in p["name"] for p in ps):
            continue                                   # quadre mal llegit (parametres en una sola linia)
        if not ps or sum(p["pct"] or 0 for p in ps) > 102 or any(p["pct"] is None for p in ps[:3]):
            continue
        t = r.get("turnout")
        seen.add(r["date"])
        out.append({**r, "turnout": t if t is not None and 10 <= t <= 100 else None})
    return out


def load() -> dict:
    try:
        d = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    d["countries"] = {iso: c for iso, rows in (d.get("countries") or {}).items() if (c := clean(rows))}
    return d


# ------------------------------------------------------------------ noms
# Els quadres de la Viquipedia anglesa porten el nom en angles ("Social
# Democratic Party of Germany") i de vegades un partit canvia de nom entre
# eleccions ("The Left" / "Die Linke"). Cada nom es busca com a titol d'article
# (amb redireccions) per saber-ne l'element de Wikidata; d'alla surten el nom en
# catala i castella, la sigla i el color. Nomes s'accepta si l'element es del
# mateix pais (P17) o, si no en te, si es un partit, una coalicio o una llista.
# Si el titol es una desambiguacio o no hi ha article, el nom es queda en angles.

_KINDS = ("political party", "alliance", "coalition", "electoral list", "front", "bloc", "parliamentary group")


_CNAMES: dict = {}


def _country_en(iso: str) -> str | None:
    """Nom angles del pais com el fa servir la Viquipedia ("Germany", "Ireland")."""
    if not _CNAMES:
        for b in results._sparql("""SELECT ?iso ?t WHERE { ?c wdt:P297 ?iso ; wdt:P31 wd:Q6256 .
  ?a schema:about ?c ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?t }"""):
            _CNAMES[b["iso"]["value"]] = b["t"]["value"]
    return _CNAMES.get(iso)


def _lookup(session, titles: list[str]) -> dict:
    """{titol demanat: element de Wikidata}, seguint redireccions i saltant desambiguacions."""
    from .ingest.wikipedia import _throttled_get
    found = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        r = _throttled_get(session, {"action": "query", "titles": "|".join(batch), "redirects": 1,
                                     "prop": "pageprops", "ppprop": "wikibase_item|disambiguation",
                                     "format": "json", "formatversion": 2}, tries=6)
        q = r.json().get("query") or {}
        back = {}
        for m in (q.get("normalized") or []) + (q.get("redirects") or []):
            back[m["to"]] = back.get(m["from"], m["from"])
        for page in q.get("pages") or []:
            pp = page.get("pageprops") or {}
            if page.get("missing") or "disambiguation" in pp or not pp.get("wikibase_item"):
                continue
            src = page["title"]
            seen = set()
            while src in back and src not in seen:
                seen.add(src)
                src = back[src]
            found[src] = pp["wikibase_item"]
    return found


def names(only: set[str] | None = None) -> dict:
    import requests
    raw = json.loads(OUT.read_text(encoding="utf-8"))
    session = requests.Session()
    table = raw.setdefault("names", {})
    for iso, rows in sorted((raw.get("countries") or {}).items()):
        if only and iso not in only:
            continue
        todo = sorted({p["name"] for r in clean(rows) for p in r["parties"]})
        direct = _lookup(session, todo)
        # Segon intent, amb el pais al titol: "Labour Party (Ireland)". Serveix per
        # als ambigus i per als que el primer intent porta on no toca.
        cname = _country_en(iso) or ""
        variants = [v for v in dict.fromkeys([cname, cname.removeprefix("Republic of "),
                                              cname.removeprefix("The "), {"GB": "UK"}.get(iso, "")]) if v]
        suffixed = {}
        for v in variants:
            alt = {f"{n} ({v})": n for n in todo if n not in suffixed and "(" not in n}
            if alt:
                for t, q in _lookup(session, list(alt)).items():
                    if t in alt:                       # la Viquipedia pot haver retocat el titol
                        suffixed[alt[t]] = q
        found = {**direct}
        for n, q in suffixed.items():
            found.setdefault(n, q)
        qids = sorted(set(direct.values()) | set(suffixed.values()))
        info = {}
        for i in range(0, len(qids), 80):
            vals = " ".join(f"wd:{x}" for x in qids[i:i + 80])
            for b in results._sparql(f"""SELECT ?x ?ca ?es ?short ?color ?iso ?kindL WHERE {{
  VALUES ?x {{ {vals} }}
  OPTIONAL {{ ?x rdfs:label ?ca . FILTER(LANG(?ca) = "ca") }}
  OPTIONAL {{ ?x rdfs:label ?es . FILTER(LANG(?es) = "es") }}
  OPTIONAL {{ ?x wdt:P1813 ?short . FILTER(LANG(?short) IN ("en", "mul", "")) }}
  OPTIONAL {{ ?x wdt:P465 ?color }}
  OPTIONAL {{ ?x wdt:P17 ?c . ?c wdt:P297 ?iso }}
  OPTIONAL {{ ?x wdt:P31 ?k . ?k rdfs:label ?kindL . FILTER(LANG(?kindL) = "en") }}
}}"""):
                x = b["x"]["value"].rsplit("/", 1)[1]
                d = info.setdefault(x, {"isos": set(), "kinds": set()})
                for k in ("ca", "es", "short", "color"):
                    if b.get(k) and not d.get(k):
                        d[k] = b[k]["value"]
                if b.get("iso"):
                    d["isos"].add(b["iso"]["value"])
                if b.get("kindL"):
                    d["kinds"].add(b["kindL"]["value"].lower())
            time.sleep(1)
        def good(qid, strict):
            d = info.get(qid)
            if not d or not any(w in k for k in d["kinds"] for w in _KINDS)                     or any("wikimedia" in k for k in d["kinds"]):
                return None
            if d["isos"]:
                return d if iso in d["isos"] else None
            return None if strict else d                # sense pais: nomes si s'ha trobat amb el pais al titol
        out = {}
        for name in todo:
            hit = None
            for qid, strict in ((direct.get(name), True), (suffixed.get(name), False)):
                if qid and (d := good(qid, strict)):
                    hit = (qid, d)
                    break
            if not hit:
                continue
            qid, d = hit
            out[name] = {"qid": qid, "ca": d.get("ca"), "es": d.get("es"), "short": d.get("short"),
                         "color": ("#" + d["color"]) if d.get("color") else None}
        table[iso] = out
        print(f"  {iso}: {len(out)} de {len(todo)} noms amb element de Wikidata", flush=True)
        OUT.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    return raw
