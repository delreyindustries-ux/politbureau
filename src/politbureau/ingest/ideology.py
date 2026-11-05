"""Ideologia i posicio politica de cada partit, de Wikidata (CC0).

Les taules d'enquestes de Wikipedia enllacen cada columna a l'article del partit
(o del candidat, a les presidencials). D'aquell article es treu l'element de
Wikidata i, d'alla, la posicio a l'eix esquerra-dreta (P1387, "political
alignment") i les ideologies (P1142). Dels candidats es passa pel seu partit
actual (P102, el que no te data de final).

El resultat es desa a config/ideologies.json i es publica amb la web: no es
torna a baixar a cada actualitzacio, perque canvia molt poc. Per refrescar-lo:
`politbureau ideologia`.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

from . import runner
from . import wikipedia as wk

OUT = Path(__file__).resolve().parents[3] / "config" / "ideologies.json"
WD = "https://www.wikidata.org/w/api.php"
LANGS = ("es", "ca")
MAX_IDEOLOGIES = 3
# Quan la capcalera enllaca una alianca electoral sense ideologia a Wikidata,
# l'article del partit que l'encapcala.
OVERRIDES = {("ES", "SUMAR"): ("en", "Movimiento Sumar")}


def _get(session, url, params):
    for i in range(6):
        r = session.get(url, params={**params, "format": "json", "formatversion": 2},
                        headers={"User-Agent": wk.USER_AGENT}, timeout=60)
        if r.status_code == 200 and r.text.startswith("{"):
            return r.json()
        time.sleep(5 * (i + 1))
    r.raise_for_status()
    return {}


def _link(cell):
    """Titol de l'article enllacat a la capcalera (no fitxers ni enllacos vermells)."""
    if cell is None:
        return None
    for a in cell.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/wiki/") and ":" not in href[6:]:
            return unquote(href[6:].split("#")[0]).replace("_", " ")
    return None


def collect_links(cfg, session, only=None):
    """{pais: {codi: (llengua, titol)}} de les capcaleres de totes les eleccions."""
    out = {}
    for election in cfg["elections"]:
        if only and election["country"] not in only:
            continue
        if not election.get("national", True) or not election.get("page"):
            continue
        country, lang = election["country"], election.get("lang", "en")
        try:
            page = wk.fetch(election["page"], session, lang=lang)
        except Exception as exc:                  # noqa: BLE001
            print(f"   AVIS {election['id']}: {exc}", flush=True)
            continue
        if not page:
            continue
        world = election.get("group") in runner.WORLD
        soup = BeautifulSoup(page["html"], "lxml")
        tables = list(wk.poll_tables(
            soup,
            wk.DEFAULT_SECTIONS + tuple(election.get("sections") or ())
            + (runner.EUROPA_SECTIONS if world else ()),
            wk.DENIED_SECTIONS + tuple(election.get("deny_sections") or ())
            + (runner.EUROPA_DENY if world else ()),
            force=tuple(election.get("force_sections") or ())))
        got = out.setdefault(country, {})
        for table, _sec, _year in tables[:4]:
            try:
                mapping, _unk, row = wk.header_parties(table, country)
                rows = wk.grid(table)
            except Exception:                     # noqa: BLE001
                continue
            for col, code in mapping.items():
                if code in got or code == "OTHER" or row >= len(rows) or col >= len(rows[row]):
                    continue
                title = _link(rows[row][col])
                if title:
                    got[code] = (lang, title)
        print(f"   {election['id']}: {len(got)} partits amb enllac", flush=True)
    for (country, code), link in OVERRIDES.items():
        if country in out:
            out[country][code] = link
    return out


def _qids(session, lang, titles):
    """{titol: Q...} per a una Viquipedia (seguint redireccions)."""
    out = {}
    titles = sorted(set(titles))
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        j = _get(session, f"https://{lang}.wikipedia.org/w/api.php",
                 {"action": "query", "prop": "pageprops", "ppprop": "wikibase_item",
                  "redirects": 1, "titles": "|".join(chunk)}).get("query", {})
        final = {t: t for t in chunk}
        for n in j.get("normalized", []):
            final = {k: (n["to"] if v == n["from"] else v) for k, v in final.items()}
        for r in j.get("redirects", []):
            final = {k: (r["to"] if v == r["from"] else v) for k, v in final.items()}
        items = {p["title"]: (p.get("pageprops") or {}).get("wikibase_item")
                 for p in j.get("pages", [])}
        for t, f in final.items():
            if items.get(f):
                out[t] = items[f]
    return out


def _entities(session, ids, props="claims|labels"):
    out = {}
    ids = sorted(set(ids))
    for i in range(0, len(ids), 50):
        j = _get(session, WD, {"action": "wbgetentities", "ids": "|".join(ids[i:i + 50]),
                               "props": props, "languages": "|".join(LANGS)})
        out.update(j.get("entities") or {})
    return out


def _values(entity, prop):
    """Valors (Q...) d'una propietat: els de rang preferent si n'hi ha, i mai els obsolets."""
    claims = [c for c in (entity.get("claims") or {}).get(prop, []) if c.get("rank") != "deprecated"]
    pref = [c for c in claims if c.get("rank") == "preferred"]
    out = []
    for c in pref or claims:
        v = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(v, dict) and v.get("id"):
            out.append((v["id"], c.get("qualifiers") or {}))
    return out


def _lc(label):
    """"Democracia conservadora" -> "democracia conservadora" (pero no les sigles: "LGBT")."""
    if label and len(label) > 1 and label[0].isupper() and not label[1].isupper():
        return label[0].lower() + label[1:]
    return label


def _current_party(person):
    """Partit actual d'un candidat (P102 sense data de final), o l'ultim de la llista."""
    parties = _values(person, "P102")
    open_ = [q for q, quals in parties if "P582" not in quals]
    return (open_ or [q for q, _ in parties] or [None])[-1]


def build(cfg=None, only=None, session=None):
    cfg = cfg or runner.load_config()
    session = session or requests.Session()
    links = collect_links(cfg, session, only)
    qid = {}
    for lang in {lang for c in links.values() for lang, _ in c.values()}:
        titles = [t for c in links.values() for l, t in c.values() if l == lang]
        qid[lang] = _qids(session, lang, titles)
    first = _entities(session, [q for lang in qid for q in qid[lang].values()])
    # Candidats (P31 = Q5, esser huma): el seu partit.
    via = {}
    for q, e in first.items():
        if any(v == "Q5" for v, _ in _values(e, "P31")):
            p = _current_party(e)
            if p:
                via[q] = p
    parties = {**first, **_entities(session, [p for p in via.values() if p not in first])}
    wanted = set()
    for e in parties.values():
        wanted.update(v for v, _ in _values(e, "P1142")[:MAX_IDEOLOGIES])
        wanted.update(v for v, _ in _values(e, "P1387")[:1])
    labels = {q: {l: _lc((e.get("labels") or {}).get(l, {}).get("value")) for l in LANGS}
              for q, e in _entities(session, wanted, props="labels").items()}

    result = {}
    for country, codes in sorted(links.items()):
        for code, (lang, title) in sorted(codes.items()):
            q = qid.get(lang, {}).get(title)
            if not q:
                continue
            pq = via.get(q, q)
            e = parties.get(pq) or {}
            pos = [v for v, _ in _values(e, "P1387")[:1]]
            ide = [v for v, _ in _values(e, "P1142")[:MAX_IDEOLOGIES]]
            row = {"qid": pq}
            if pq != q:
                row["via"] = q
            for l in LANGS:
                p = [labels.get(v, {}).get(l) for v in pos]
                i = [labels.get(v, {}).get(l) for v in ide]
                row[l] = {"position": next((x for x in p if x), None),
                          "ideology": [x for x in i if x]}
            if any(row[l]["position"] or row[l]["ideology"] for l in LANGS):
                result.setdefault(country, {})[code] = row
    return result


def write(only=None):
    data = build(only=only)
    if only and OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
        old.update(data)
        data = old
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    return data
