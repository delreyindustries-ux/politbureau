"""Resultats de les eleccions ja fetes i composicio dels parlaments (09/11/2026).

* Quines eleccions: Wikidata (CC0), eleccions legislatives (Q1076105) i
  presidencials (Q858439) amb article a la Viquipedia anglesa.
* Els resultats: el quadre resum (infobox) d'aquell article (Viquipedia, CC BY-SA
  4.0): partit o candidat, % de vot, escons i escons de l'eleccio anterior.
* Qui governa: Wikidata, cap de govern (P6) actual del pais i el seu partit (P102).

Dues coses surten d'aqui:
  1. «Eleccions fetes fa poc» (/ca/paisos/): totes les eleccions nacionals del mon
     dels darrers 120 dies, menys els EUA, el Brasil i Russia (decisio seva).
  2. «Parlament actual» a la pagina de cada pais: els escons que va donar la darrera
     eleccio legislativa i el cap de govern d'avui.

Es desa a data/resultats/darreres.json (va al repositori: si un dia la Viquipedia
no respon, la web surt igual amb la copia anterior).

    PYTHONPATH=src py -m politbureau resultats
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "resultats" / "darreres.json"
UA = {"User-Agent": "politbureau (politbureau.es)"}
EXCLUDED = {"US", "BR", "RU"}
RECENT_DAYS = 120

# Articles que no son l'eleccio a la cambra baixa (o unica) d'un pais.
_NOT_MAIN = re.compile(r"councillors|senate|senatorial|upper house|regional|local|municipal|"
                       r"by-election|european parliament|gubernatorial|state election|provincial|"
                       r"council|recall|referendum|primar|leadership|mayoral|indirect|"
                       r"constituent|landtag|assembly of the republic of srpska|cantonal", re.I)


def _sparql(query: str) -> list[dict]:
    import time
    import requests
    for attempt in range(4):
        r = requests.get("https://query.wikidata.org/sparql", params={"query": query, "format": "json"},
                         headers={**UA, "Accept": "application/sparql-results+json"}, timeout=120)
        if r.status_code in (429, 500, 502, 503, 504) and attempt < 3:
            time.sleep(10 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()["results"]["bindings"]


def elections(since: str) -> list[dict]:
    """Eleccions legislatives i presidencials des de `since` fins avui, amb article."""
    q = f"""
SELECT ?iso ?kind ?date ?article ?nd ?ca ?es WHERE {{
  VALUES (?type ?kind) {{ (wd:Q1076105 "leg") (wd:Q858439 "pres") }}
  ?el wdt:P31/wdt:P279* ?type ; wdt:P1001 ?country ; wdt:P585 ?date .
  ?country wdt:P297 ?iso .
  FILTER(?date <= NOW() && ?date >= "{since}T00:00:00Z"^^xsd:dateTime)
  ?article schema:about ?el ; schema:isPartOf <https://en.wikipedia.org/> .
  OPTIONAL {{ ?el wdt:P156 ?n . ?n wdt:P585 ?nd . FILTER(?nd <= NOW() && ?nd > ?date) }}
  OPTIONAL {{ ?country rdfs:label ?ca . FILTER(LANG(?ca) = "ca") }}
  OPTIONAL {{ ?country rdfs:label ?es . FILTER(LANG(?es) = "es") }}
}}"""
    out, seen = [], {}
    for b in _sparql(q):
        title = b["article"]["value"].rsplit("/", 1)[-1]
        key = (b["iso"]["value"], title)
        if _NOT_MAIN.search(title.replace("_", " ")) or title.startswith("Next_"):
            continue
        if key in seen:
            seen[key]["superseded"] = seen[key]["superseded"] or bool(b.get("nd"))
            continue
        # Si Wikidata diu que la va seguir una altra eleccio ja feta, aquesta ja no
        # es la darrera encara que la seguent no surti a la consulta (Bulgaria 2023).
        out.append({"iso": b["iso"]["value"], "kind": b["kind"]["value"],
                    "date": b["date"]["value"][:10], "title": title,
                    "superseded": bool(b.get("nd")),
                    "country": {"ca": (b.get("ca") or {}).get("value"),
                                "es": (b.get("es") or {}).get("value")}})
        seen[key] = out[-1]
    return out


def heads_of_government() -> dict:
    """{iso: {"name", "party"}}: el cap de govern d'avui (P6 sense data de final)."""
    q = """
SELECT ?iso ?hLabel ?pLabel WHERE {
  ?c wdt:P297 ?iso ; p:P6 ?st . ?st ps:P6 ?h .
  FILTER NOT EXISTS { ?st pq:P582 ?end }
  OPTIONAL { ?h wdt:P102 ?p . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}"""
    out = {}
    for b in _sparql(q):
        iso = b["iso"]["value"]
        out.setdefault(iso, {"name": b["hLabel"]["value"], "party": None})
        if b.get("pLabel") and not out[iso]["party"]:
            out[iso]["party"] = b["pLabel"]["value"]
    return out


# ------------------------------------------------------------------- infobox

_SESSION = None


def _wikitext(title: str) -> str:
    """Amb la mateixa peticio educada que les enquestes (espaiada i respectant els 429)."""
    import urllib.parse
    import requests
    from .ingest.wikipedia import _throttled_get
    global _SESSION
    _SESSION = _SESSION or requests.Session()
    r = _throttled_get(_SESSION, {"action": "parse", "page": urllib.parse.unquote(title),
                                  "prop": "wikitext", "section": 0, "format": "json",
                                  "formatversion": 2, "redirects": 1}, tries=6)
    return r.json().get("parse", {}).get("wikitext", "")


def _clean(v: str) -> str:
    v = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", v, flags=re.S)
    v = re.sub(r"\{\{(?:efn|refn|ref|sfn|cn|citation needed|increase|decrease|steady|nowrap)[^{}]*\}\}",
               "", v, flags=re.I)
    v = re.sub(r"\{\{nowrap\|([^{}]*)\}\}", r"\1", v, flags=re.I)
    v = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", v)
    v = re.sub(r"\{\{[^{}]*\}\}", "", v)
    v = re.sub(r"<br\s*/?>", " ", v)
    v = re.sub(r"<[^>]+>", "", v)
    v = v.replace("'''", "").replace("''", "")
    return " ".join(v.split()).strip(" ,;")


def _strip_disambig(name: str) -> str:
    """"Liberals (Sweden)" -> "Liberals": el parentesi es de l'enllac, no del nom."""
    return re.sub(r"\s*\((?:[^()]*\b(?:party|political|[A-Z][a-z]+))\)$", "", name).strip()


def _number(v: str):
    m = re.search(r"-?\d[\d,]*\.?\d*", v or "")
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def infobox(title: str, kind: str = "leg") -> dict | None:
    """Partits (o candidats) amb %, escons i escons anteriors, i el govern."""
    text = _wikitext(title)
    i = text.find("{{Infobox")
    if i < 0:
        return None
    # Fins al final de la plantilla (comptant claus).
    depth, j = 0, i
    while j < len(text):
        if text.startswith("{{", j):
            depth += 1
            j += 2
            continue
        if text.startswith("}}", j):
            depth -= 1
            j += 2
            if depth == 0:
                break
            continue
        j += 1
    body = text[i:j]
    params: dict = {}
    for m in re.finditer(r"\n\s*\|\s*([a-z_]+?)(\d*)[ \t]*=[ \t]*(.*?)(?=\n\s*\||\n\}\}|$)", body, re.S):
        params.setdefault(m.group(1), {})[m.group(2)] = m.group(3)
    rows = []
    # Legislatives: el partit (alguns quadres porten tambe el candidat a primer
    # ministre). Presidencials: la persona.
    order = ("party",) if kind == "leg" else ("nominee", "candidate", "party")
    who = next((k for k in order if k in params), None)
    if not who:
        return None
    # Presidencials indirectes (les tria el parlament o un colegi electoral): fora.
    elect = " ".join(_clean((params.get(k) or {}).get("", "")) for k in
                     ("votes_for_election", "seats_for_election", "electoral_vote"))
    if who != "party" and re.search(r"members|electors|parliament|assembly|electoral college", elect, re.I):
        return None
    for k, raw in sorted(params[who].items(), key=lambda kv: int(kv[0] or 0)):
        name = _strip_disambig(_clean(raw))
        if not name or name.lower() == "none":
            continue
        pct = _number(_clean(params.get("percentage", {}).get(k, "")))
        seats = _number(_clean(params.get("seats", {}).get(k, "") or params.get("seats_after", {}).get(k, "")))
        last = _clean(params.get("last_election", {}).get(k, ""))
        prev = re.search(r"(\d+)\s*seats?", last) or (re.fullmatch(r"\d+", last) and re.match(r"(\d+)", last))
        rows.append({"name": name, "pct": pct,
                     "seats": int(seats) if seats is not None and who == "party" else None,
                     "prev": int(prev.group(1)) if prev else None,
                     "party": (_strip_disambig(_clean(params.get("party", {}).get(k, ""))) or None)
                     if who != "party" else None,
                     "leader": (lambda v: v if v and v.lower() != "none" else None)(
                         _clean(params.get("leader", {}).get(k, "")))})
    if not any(r["pct"] is not None for r in rows):
        return None
    def one(key):
        return _clean((params.get(key) or {}).get("", "")) or None
    def gov(key):
        v = one(key)
        return None if (not v or "=" in v or v.upper() == "TBD" or v == "}}") else v
    return {"kind": "party" if who == "party" else "candidate", "rows": rows,
            "date_text": one("election_date"),
            "seats_total": _number(one("seats_for_election") or ""),
            "majority": _number(one("majority_seats") or ""),
            "gov_title": gov("title"), "gov_after": gov("after_election"),
            "party_after": gov("after_party"), "turnout": _number(one("turnout") or "")}


# ---------------------------------------------------------------------- tot

def build(our_isos: set[str]) -> dict:
    today = dt.date.today()
    recent_since = (today - dt.timedelta(days=RECENT_DAYS)).isoformat()
    els = elections("2019-01-01")
    recent, last_leg, last_pres = [], {}, {}
    for e in sorted(els, key=lambda e: e["date"]):
        if e["kind"] == "leg":
            last_leg[e["iso"]] = e
        else:
            last_pres[e["iso"]] = e
        if e["date"] >= recent_since and e["iso"] not in EXCLUDED:
            recent.append(e)
    out = {"built": today.isoformat(), "recent": [], "parliaments": {}, "heads": {}}
    chambers = _chamber_totals()
    for e in recent:
        box = infobox(e["title"], e["kind"])
        if box and box["rows"]:
            out["recent"].append({**e, **box})
    for iso in sorted(our_isos - EXCLUDED):
        e = last_leg.get(iso)
        if not e:
            continue
        if e["date"] < "2022-01-01" or e.get("superseded"):
            continue                    # Wikidata no sempre te la darrera: millor res
        box = infobox(e["title"], "leg")
        if not box or not box["rows"]:
            continue
        total = box["seats_total"] or chambers.get(iso)
        got = sum(r["seats"] or 0 for r in box["rows"])
        # Si els escons no sumen la cambra (el quadre es del Senat, o nomes en
        # porta tres), no es mostra: una composicio a mitges enganya.
        if not total or not (0.9 * total <= got <= 1.02 * total):
            continue
        if chambers.get(iso) and abs(chambers[iso] - total) > 0.02 * chambers[iso]:
            continue
        out["parliaments"][iso] = {**e, **box, "seats_total": total}
    try:
        heads = heads_of_government()
        out["heads"] = {iso: h for iso, h in heads.items() if iso in our_isos}
    except Exception:                                  # noqa: BLE001
        pass
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def _chamber_totals() -> dict:
    """{pais: escons de la cambra} de config/chambers.yaml, per comprovar el quadre."""
    import yaml
    from .ingest.runner import load_config
    path = ROOT / "config" / "chambers.yaml"
    if not path.exists():
        return {}
    ch = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out = {}
    for e in load_config()["elections"]:
        c = ch.get(e["id"])
        if isinstance(c, dict) and c.get("seats"):
            out.setdefault(e["country"], c.get("total") or c["seats"])
    return out


def load() -> dict:
    if not OUT.exists():
        return {}
    return json.loads(OUT.read_text(encoding="utf-8"))


def our_countries() -> set[str]:
    from .ingest.runner import load_config
    return {e["country"] for e in load_config()["elections"]
            if e.get("pub") and e.get("group") in ("europa", "mon")}


# ------------------------------------------------------------------ per a la web

_PALETTE = ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F", "#EDC948", "#B07AA1",
            "#FF9DA7", "#9C755F", "#BAB0AC"]


def _color(conn, code, i, iso="XX"):
    from . import parties
    if code and not code.startswith("?"):
        c = parties.meta(code, iso, None).get("color")
        if c and c != "#9E9E9E":
            return c
    if conn is not None and code:
        row = conn.execute("SELECT color FROM party_style WHERE party = ?", (code,)).fetchone()
        if row and row[0]:
            return row[0]
    return _PALETTE[i % len(_PALETTE)]


def parliament_view(conn, iso: str) -> dict | None:
    """La composicio que va sortir de la darrera eleccio legislativa i qui governa."""
    from . import parties
    d = load()
    p = (d.get("parliaments") or {}).get(iso)
    head = (d.get("heads") or {}).get(iso)
    if not p and not head:
        return None
    rows = []
    if p:
        for i, r in enumerate(x for x in p["rows"] if x["seats"]):
            code, _ = parties.resolve(r["name"], iso)
            rows.append({"name": r["name"], "seats": r["seats"], "pct": r["pct"],
                         "prev": r["prev"], "color": _color(conn, code, i, iso)})
        rest = int(p["seats_total"]) - sum(r["seats"] for r in rows)
        if rest > 0:
            rows.append({"name": None, "seats": rest, "pct": None, "prev": None, "color": "#9E9E9E"})
    total = int(p["seats_total"]) if p else 0
    return {"rows": rows, "total": total, "majority": total // 2 + 1 if total else None,
            "date": p["date"] if p else None,
            "url": ("https://en.wikipedia.org/wiki/" + p["title"]) if p else None,
            "head": head}


def recent_view(conn, elections_cfg: list[dict]) -> list[dict]:
    """Les eleccions dels darrers 120 dies, amb la mitjana final de les enquestes
    quan l'eleccio era a la web (Nova Zelanda, Suecia...)."""
    from . import parties
    d = load()
    out = []
    for e in sorted(d.get("recent") or [], key=lambda e: e["date"], reverse=True):
        ours = next((c for c in elections_cfg if c["country"] == e["iso"] and c.get("pub")
                     and c.get("group") in ("europa", "mon")
                     and (str(c.get("date") or "") == e["date"]
                          or (e["kind"] == "pres") == (c.get("display") == "candidates"))), None)
        avg = {}
        if ours and conn is not None:
            avg = {p: s for p, s in conn.execute(
                "SELECT party, share FROM aggregate WHERE election_id = ? AND scope_code = ''",
                (ours["id"],))}
        rows = []
        for i, r in enumerate(e["rows"][:8]):
            code, _ = parties.resolve(r["name"], e["iso"])
            poll = avg.get(code)
            rows.append({**r, "color": _color(conn, code, i, e["iso"]), "poll": poll,
                         "err": (r["pct"] - poll) if (poll is not None and r["pct"] is not None) else None})
        out.append({"iso": e["iso"], "country": e["country"], "date": e["date"],
                    "kind": e["kind"], "rows": rows,
                    "seats": any(r["seats"] for r in rows),
                    "polled": any(r["poll"] is not None for r in rows),
                    "gov": e.get("gov_after"), "gov_title": e.get("gov_title"),
                    "url": "https://en.wikipedia.org/wiki/" + e["title"]})
    return out
