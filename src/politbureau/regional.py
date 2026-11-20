"""Escons de les autonomiques circumscripcio per circumscripcio (19/11/2026).

Fins ara els parlaments autonomics amb mes d'una circumscripcio (Catalunya,
Andalusia, Galicia, Balears, Canaries, el Pais Basc...) es repartien com si tot
el territori fos una sola circumscripcio, i la pagina ho deia. Aixo dona massa
escons als partits petits: la llei d'Hondt en provincies de 7, 8 o 15 escons
els castiga molt mes que en una sola de 75.

Ara es fa com a les generals:

  1. El resultat REAL de l'ultima eleccio a cada circumscripcio: la taula
     "Distribution by constituency" de l'article de Wikipedia de l'eleccio
     anterior (CC BY-SA 4.0), que porta el % i els escons de cada partit.
  2. Swing proporcional (model/seats.proportional_swing): cada partit es
     multiplica per mitjana d'avui / resultat de l'eleccio anterior al conjunt
     del territori, i cada circumscripcio torna a sumar 100.
  3. D'Hondt a cada circumscripcio amb el llindar que mana la llei
     (config/chambers.yaml): a cada circumscripcio, a tot el territori, o les
     dues coses com a Canaries (15 % a l'illa o 4 % a tot l'arxipelag).

`politbureau circumscripcions` baixa les taules i les desa a
config/regional_districts.json; la web nomes llegeix aquest fitxer.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1].parent
OUT = ROOT / "config" / "regional_districts.json"
API = "https://en.wikipedia.org/w/api.php"
UA = {"User-Agent": "politbureau (politbureau.es)"}
SECTION = re.compile(r"^(Distribution|Results) by constituency$", re.I)


def _call(session, params):
    for attempt in range(10):
        r = session.get(API, params={**params, "format": "json", "formatversion": 2},
                        headers=UA, timeout=60)
        if r.status_code == 200 and r.text.startswith("{"):
            time.sleep(1.5)
            return r.json()
        time.sleep(float(r.headers.get("Retry-After") or 10 * (attempt + 1)) + 1)
    r.raise_for_status()
    raise RuntimeError(f"Wikipedia no respon ({r.status_code})")


def _num(text):
    t = (text or "").replace("−", "").replace("–", "").replace("−", "").strip()
    t = t.replace(",", ".").rstrip("%").strip()
    try:
        return float(t)
    except ValueError:
        return 0.0


def parse_table(html: str) -> dict | None:
    """{"districts": [{name, seats, shares, won}], "total": {partit: %}} o None."""
    from bs4 import BeautifulSoup
    from .ingest import wikipedia as wk
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table", class_="wikitable"):
        g = wk.grid(table)
        sub = next((i for i, row in enumerate(g)
                    if sum(1 for c in row if wk.cell_text(c) == "%") >= 2), None)
        if sub is None:
            continue
        # Capcalera: la sigla del text (PSOE, CCa, NC-BC) es la que fan servir les
        # taules d'enquestes; l'enllac porta el nom angles ("Socialist Party of
        # the Canaries"), que no. Primer el que es reconegui; si res, la sigla.
        from . import parties
        mapping = {}
        for c, cell in enumerate(g[0]):
            if cell is None or c == 0:
                continue
            link, abbr = cell.find("a"), cell.find("abbr")
            labels = [wk.cell_text(cell), link.get("title") if link else None,
                      abbr.get("title") if abbr else None]
            code = next((parties.resolve(lb, "ES")[0] for lb in labels
                         if lb and parties.resolve(lb, "ES")[1]), None)
            mapping[c] = code or parties.resolve(labels[0], "ES")[0]
        cols = []
        for c, cell in enumerate(g[sub]):
            if wk.cell_text(cell) == "%" and mapping.get(c):
                seats_col = c + 1 if c + 1 < len(g[sub]) and wk.cell_text(g[sub][c + 1]) == "S" else None
                cols.append((mapping[c], c, seats_col))
        if len(cols) < 2:
            continue
        districts, total = [], None
        for row in g[sub + 1:]:
            if not row or row[0] is None or row[0].name != "td":
                continue
            name = wk.cell_text(row[0])
            if not name:
                continue
            shares, won = {}, {}
            for code, c, sc in cols:
                v = _num(wk.cell_text(row[c]) if c < len(row) else "")
                if v:
                    shares[code] = shares.get(code, 0.0) + v
                if sc is not None and sc < len(row):
                    n = int(_num(wk.cell_text(row[sc])))
                    if n:
                        won[code] = won.get(code, 0) + n
            if name.lower() == "total":
                total = {"shares": shares, "won": won}
            elif shares:
                districts.append({"name": name, "seats": sum(won.values()), "shares": shares,
                                  "won": won})
        if districts and total:
            return {"districts": districts, "total": total["shares"], "total_won": total["won"]}
    return None


def fetch(session, title: str) -> dict | None:
    secs = _call(session, {"action": "parse", "page": title, "prop": "sections"})["parse"]["sections"]
    idx = next((s["index"] for s in secs if SECTION.match(s["line"].strip())), None)
    if not idx:
        return None
    html = _call(session, {"action": "parse", "page": title, "prop": "text", "section": idx})["parse"]["text"]
    got = parse_table(html)
    if got:
        got["source"] = "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
    return got


def run(chambers: dict, only=None) -> dict:
    """Baixa la taula de cada cambra amb `base:` a chambers.yaml."""
    import requests
    session = requests.Session()
    try:
        data = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    for eid, ch in chambers.items():
        if not isinstance(ch, dict) or not ch.get("base") or (only and eid not in only):
            continue
        got = fetch(session, ch["base"])
        if not got:
            print(f"  {eid:<12} {ch['base']}: sense taula per circumscripcio")
            continue
        seats = sum(d["seats"] for d in got["districts"])
        ok = "" if seats == ch["seats"] else f"  ATENCIO: {seats} escons a la taula, {ch['seats']} a la cambra"
        print(f"  {eid:<12} {len(got['districts']):>2} circumscripcions, {seats} escons{ok}")
        data[eid] = {"base": ch["base"], "retrieved": dt.date.today().isoformat(), **got}
    OUT.write_bytes(json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8"))
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


def projector(eid: str, chamber: dict):
    """Funcio {partit: %} -> {partit: escons} per circumscripcions, o None si
    aquesta cambra no en te taula (llavors es reparteix com una de sola)."""
    base = load().get(eid)
    if not chamber or not chamber.get("districts") or not base:
        return None
    from .model import seats as seatlib
    # `rename`: la mateixa llista amb una altra etiqueta a les enquestes
    # (Mes per Mallorca hi surt com a "Mes"; IU-Moviment Sumar d'Arago, com a "IU").
    ren = chamber.get("rename") or {}

    def _r(d):
        out = {}
        for p, v in d.items():
            out[ren.get(p, p)] = out.get(ren.get(p, p), 0) + v
        return out
    before = _r(base["total"])
    dists = [{**d, "shares": _r(d["shares"])} for d in base["districts"] if d["seats"]]
    if sum(d["seats"] for d in dists) != chamber["seats"]:
        return None                       # la llei ha canviat: millor no inventar
    local = chamber.get("district_threshold", chamber.get("threshold", 0.03))
    region = chamber.get("region_threshold")
    scope = chamber.get("threshold_scope", "district")

    def project(shares: dict, detail: dict | None = None) -> dict:
        now = {p: v for p, v in shares.items() if p != "OTHER" and v and v > 0}
        if not now:
            return {}
        tot = sum(now.values())
        regional = {p: v * 100.0 / tot for p, v in now.items()}
        totals: dict = {}
        for d in dists:
            sh = seatlib.proportional_swing(d["shares"], now, before)
            sh = {p: v for p, v in sh.items() if p in now and v > 0}
            if scope == "region":
                lim = chamber.get("threshold", 0.03) * 100
                running = {p: v for p, v in sh.items() if regional.get(p, 0) >= lim}
            else:
                s = sum(sh.values()) or 1.0
                running = {p: v for p, v in sh.items()
                           if v * 100.0 / s >= local * 100
                           or (region is not None and regional.get(p, 0) >= region * 100)}
            got = seatlib.dhondt(running, d["seats"], 0.0) if running else {}
            if detail is not None:
                detail[d["name"]] = {p: n for p, n in got.items() if n}
            for p, n in got.items():
                if n:
                    totals[p] = totals.get(p, 0) + n
        return totals
    project.n_districts = len(dists)
    project.source = base.get("source")
    project.base = base.get("base")
    return project
