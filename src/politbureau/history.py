"""Resultats historics de les eleccions generals, 1977-2023 (pla de ruta,
pilar 2: «Resultats historics», 15/11/2026).

Per a cada eleccio al Congres, el resultat estatal: cens, participacio, vot en
blanc i nul, i vots, percentatge i escons de cada candidatura. Surt dels
fitxers d'infoelectoral (Ministeri de l'Interior), els mateixos que la resta de
la web: el 07 (dades comunes) i el 08 (candidatures) del ZIP per municipis, a
la fila «Total nacional».

  * Percentatge: sobre el vot valid (candidatures + en blanc), com el dona la
    Junta Electoral.
  * Participacio: votants (candidatures + blanc + nul) sobre el cens de
    l'escrutini.

`politbureau historic` ho calcula i ho desa a config/history_es.json; la web
nomes llegeix aquest fitxer, aixi la generacio no depen de la xarxa.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "config" / "history_es.json"

# Dia de la votacio de cada eleccio general (BOE de cada convocatoria; llista a
# https://infoelectoral.interior.gob.es, «Area de descargas»).
ELECTIONS = [
    ("1977-06-15", "1977", "06"), ("1979-03-01", "1979", "03"), ("1982-10-28", "1982", "10"),
    ("1986-06-22", "1986", "06"), ("1989-10-29", "1989", "10"), ("1993-06-06", "1993", "06"),
    ("1996-03-03", "1996", "03"), ("2000-03-12", "2000", "03"), ("2004-03-14", "2004", "03"),
    ("2008-03-09", "2008", "03"), ("2011-11-20", "2011", "11"), ("2015-12-20", "2015", "12"),
    ("2016-06-26", "2016", "06"), ("2019-04-28", "2019", "04"), ("2019-11-10", "2019", "11"),
    ("2023-07-23", "2023", "07"),
]

# Les dues eleccions del 2019 comparteixen any: el titol de l'article porta el mes.
PAGES = {"2019-04-28": "April 2019 Spanish general election",
         "2019-11-10": "November 2019 Spanish general election"}

MIN_SHARE = 1.0       # a la taula: candidatures amb escons o amb l'1 % del vot

# Families per al grafic d'evolucio: (clau, nom, color, patro de les sigles).
# Nomes les forces d'ambit estatal; l'ordre importa (la primera que casa).
FAMILIES = [
    ("PSOE", "PSOE", "#E30613", r"^P\.?S\.?O\.?E|^PSOE|^PSC|^PSE"),
    ("PP", "AP · PP", "#1D84CE", r"^P\.?P\.?$|^PP\b|^PP[- ]|^A\.?P\.?$|^AP\b|^AP[- ]|^C\.?D\.?$|^C\.?P\.?$|^AP-PDP|COALICION POPULAR|COALICION DEMOCRATICA|PARTIDO POPULAR"),
    ("UCD", "UCD", "#197E36", r"^U\.?C\.?D"),
    ("VOX", "Vox", "#63BE21", r"^VOX"),
    ("CS", "Ciudadanos", "#EB6109", r"^C'?s$|^CS$|CIUDADANOS"),
    ("UP", "Podemos · Sumar", "#6B2E68", r"PODEMOS|^SUMAR|^EN COMU|^ECP"),
    ("IU", "PCE · IU", "#B5121B", r"^P\.?C\.?E|^I\.?U\.?\b|^IU[- ]|IZQUIERDA UNIDA|^PSUC"),
    ("CDS", "CDS", "#7BB661", r"^C\.?D\.?S"),
    ("UPYD", "UPyD", "#E2007A", r"^UPY?D|^UP[yY]D"),
]


def _num(text):
    t = re.sub(r"\[.*?\]", "", text or "").replace(",", "").replace("−", "-").strip()
    m = re.match(r"-?\d+(?:\.\d+)?", t)
    return float(m.group(0)) if m else None


def family(sigla: str) -> str | None:
    s = (sigla or "").strip().upper()
    for key, _name, _color, pat in FAMILIES:
        if re.search(pat, s, re.I):
            return key
    return None


def election(date: str, year: str, month: str, session=None) -> dict:
    """Resultat estatal d'una eleccio, de la taula «Summary of the ... Congress
    of Deputies election results» de l'article de la Viquipedia anglesa."""
    from bs4 import BeautifulSoup
    from .ingest import wikipedia as wk
    title = PAGES.get(date) or f"{year} Spanish general election"
    got = wk.fetch(title, session)
    if got is None:
        raise ValueError(f"no trobo la pagina {title}")
    soup = BeautifulSoup(got["html"], "lxml")
    table = next((t for t in soup.select("table.wikitable")
                  if "Congress of Deputies election results" in t.get_text(" ", strip=True)[:200]), None)
    if table is None:
        raise ValueError(f"{title}: no trobo la taula de resultats")
    parties, tot = [], {}
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        texts = [c.get_text(" ", strip=True) for c in cells]
        if not texts:
            continue
        first = cells[0]
        color = first.get("bgcolor") or (re.search(r"background(?:-color)?:\s*([^;\"]+)", first.get("style") or "") or [None, None])[1]
        if not texts[0] and color and len(cells) >= 6:
            # fora les crides a nota del final ("People's Party (PP) 1", amb superindex)
            full = re.sub(r"[\s\d\u00b9\u00b2\u00b3\u2070-\u2079]+$", "", re.sub(r"\[.*?\]", "", texts[1])).strip()
            m = re.search(r"\(([^()]+)\)\s*$", full)
            sigla = (m.group(1) if m else full).strip()
            votes, share, seats = _num(texts[2]), _num(texts[3]), _num(texts[5])
            if votes is None or share is None:
                continue
            parties.append({"name": sigla, "full": re.sub(r"\s*\([^()]+\)\s*$", "", full),
                            "color": color.strip(), "votes": int(votes), "share": share,
                            "seats": int(seats or 0), "family": family(sigla)})
        else:
            key = texts[0].lower()
            for name, k in (("blank ballots", "blank"), ("valid votes", "valid"), ("invalid votes", "null"),
                            ("votes cast", "voters"), ("registered voters", "census"), ("total", "total")):
                if key.startswith(name) and len(texts) > 1 and k not in tot:
                    tot[k] = [_num(x) for x in texts[1:]]
    seats_total = int(next((x for x in reversed(tot.get("total") or []) if x and x < 1000), 0) or 0)
    keep = [p for p in parties if p["seats"] or p["share"] >= MIN_SHARE]
    return {"date": date, "source": got["url"],
            "census": int(tot["census"][0]) if tot.get("census") else None,
            "voters": int(tot["voters"][0]) if tot.get("voters") else None,
            "turnout": tot["voters"][1] if tot.get("voters") and len(tot["voters"]) > 1 else None,
            "blank": int(tot["blank"][0]) if tot.get("blank") else None,
            "null": int(tot["null"][0]) if tot.get("null") else None,
            "valid": int(tot["valid"][0]) if tot.get("valid") else None,
            "seats": seats_total or sum(p["seats"] for p in parties),
            "seats_listed": sum(p["seats"] for p in parties), "parties": keep}


def check_ministry(e: dict, year: str, month: str) -> float | None:
    """Diferencia, en tant per cent, entre el vot valid de la Viquipedia i el
    del fitxer del Ministeri, si el tenim al projecte (2016-2023). Serveix per
    validar el lector: les candidatures no es poden comparar una a una perque
    el Ministeri dona les coalicions per separat."""
    from .ingest import infoelectoral as ie
    path = ie.CACHE / f"{ie.CONGRESO}{year}{month}_MUNI.zip"
    if not path.exists() or not e.get("valid"):
        return None
    zf = zipfile.ZipFile(io.BytesIO(path.read_bytes()))
    line = next(r for r in ie._records(ie._member(zf, "07", ie.CONGRESO, year, month), 172)
                if r[9:11] == "99")
    valid = int(line[125:133]) + int(line[141:149])
    return abs(valid - e["valid"]) * 100 / valid


def run() -> dict:
    import requests
    session = requests.Session()
    els = []
    for date, year, month in ELECTIONS:
        e = election(date, year, month, session)
        diff = check_ministry(e, year, month)
        if diff is not None:
            e["ministry_diff"] = round(diff, 3)
        els.append(e)
        top = ", ".join(f"{p['name']} {p['share']} ({p['seats']})" for p in e["parties"][:5])
        print(f"  {date}  part. {e['turnout']} %  escons {e['seats_listed']}/{e['seats']}  "
              f"Ministeri {diff if diff is None else round(diff, 3)}  {top}", flush=True)
    data = {"computed": dt.date.today().isoformat(),
            "source": "Wikipedia (CC BY-SA 4.0), taules de resultats de cada eleccio",
            "families": [{"key": k, "name": n, "color": c} for k, n, c, _ in FAMILIES],
            "elections": els}
    OUT.write_bytes(json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8"))
    return data


def load() -> dict | None:
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
