"""Valoracio dels instituts d'enquestes (pla de ruta, fase 1; 10/11/2026).

Per a cada eleccio general passada es compara l'ultima enquesta de cada
institut feta en les tres setmanes anteriors amb el resultat oficial. L'error
d'una enquesta es la mitjana de l'error absolut, en punts, dels partits que van
treure almenys el 3 % del vot valid. La nota d'un institut es el seu
"mes-menys": quant s'equivoca mes (+) o menys (-) que la resta d'instituts a
la mateixa eleccio, de mitjana sobre les eleccions que ha cobert.

  * Enquestes: taules de la Wikipedia en angles (CC BY-SA 4.0), llegides amb el
    mateix lector que les enquestes actuals.
  * Resultats: fitxers 07 i 08 del Ministeri de l'Interior (infoelectoral),
    amb el vot CERA inclos: vot valid = candidatures + en blanc.

`politbureau instituts` ho calcula i ho desa a config/pollster_ratings.json; la
web nomes llegeix aquest fitxer, aixi la generacio no depen de la xarxa.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "config" / "pollster_ratings.json"

WINDOW_DAYS = 21          # enquestes amb el camp acabat les tres setmanes d'abans
MAIN_SHARE = 3.0          # partits que compten: >= 3 % del vot valid
MIN_MAIN = 4              # una enquesta ha de donar com a minim 4 d'aquests partits

ELECTIONS = [
    # id, data, pagina de la Wikipedia, proces del Ministeri
    ("congreso-2016", "2016-06-26", "Opinion_polling_for_the_2016_Spanish_general_election"),
    ("congreso-2019a", "2019-04-28", "Opinion_polling_for_the_April_2019_Spanish_general_election"),
    ("congreso-2019n", "2019-11-10", "Opinion_polling_for_the_November_2019_Spanish_general_election"),
    ("congreso-2023", "2023-07-23", "Opinion_polling_for_the_2023_Spanish_general_election"),
]

# Sigles que el cataleg de partits no coneix (son d'abans del 2023) o que cal
# sumar a un altre partit per comparar com ho fan les taules de la Wikipedia:
# la columna "Unidos/Unidas Podemos" ja porta En Comu Podem, i el PSE-EE es el PSOE.
CANON = {
    "?C's": "CS", "?C'S": "CS", "?CS": "CS", "?Cs": "CS",
    "?ECP": "PODEMOS", "?ECPGUANYEM": "PODEMOS",
    "?PSEEEPSO": "PSOE",
}
NAMES = {"CS": "Ciudadanos", "PODEMOS": "Unidas Podemos", "SUMAR": "Sumar"}

# Variants d'escriptura del mateix institut a la Wikipedia.
ALIASES = {"SigmaDos": "Sigma Dos", "SyM Consulting": "SyM Consulting",
           "SYM Consulting": "SyM Consulting", "Electomanía": "ElectoPanel"}
# Enquestes internes de partits, no d'instituts.
PARTY_POLLSTERS = {"PSOE", "PP", "Podemos", "Vox", "Cs", "Ciudadanos", "Sumar"}


def _canon(code: str) -> str:
    return CANON.get(code, code)


def _pollster(name: str) -> str:
    name = re.sub(r"\s+", " ", (name or "").strip())
    # "CIS (SocioMétrica)": reestimacio d'un altre institut amb les dades del CIS.
    m = re.match(r"CIS \((.+)\)$", name)
    if m:
        name = m.group(1).strip()
    return ALIASES.get(name, name)


def official(process: str) -> dict[str, float]:
    """Percentatge de cada partit sobre el vot valid estatal, CERA inclos."""
    from .ingest import infoelectoral as ie
    from . import parties

    tipo, year, month = ie.PROCESSES[process]
    zf = ie.download(process)
    siglas = ie.candidacies(zf, tipo, year, month)
    votes: dict[str, int] = defaultdict(int)
    for rec in ie._records(ie._member(zf, "08", tipo, year, month), 33):
        if rec[9:11] == "99" and rec[11:13] == "99":          # total nacional
            label = siglas.get(rec[14:20], rec[14:20])
            code = parties.resolve(label, "ES")[0] or ("?" + parties.slug(label).upper()[:10])
            votes[_canon(code)] += int(rec[20:28])
    cand = sum(votes.values())
    # Fitxer 07, registre "Total nacional": ... blanc(8) nuls(8) candidatures(8) escons(5) ...
    line = next(r for r in ie._records(ie._member(zf, "07", tipo, year, month), 172)
                if r[9:11] == "99")
    pos = line.rfind(f"{cand:08d}")
    if pos < 16:
        raise ValueError(f"{process}: no trobo el total de candidatures al fitxer 07")
    blank = int(line[pos - 16:pos - 8])
    valid = cand + blank
    return {k: 100 * v / valid for k, v in votes.items()}


def _polls(page: str, date: str):
    from bs4 import BeautifulSoup
    from .ingest import wikipedia as wk

    from . import parties

    got = wk.fetch(page)
    soup = BeautifulSoup(got["html"], "lxml")
    out = []
    # El 2016 la columna de Ciudadanos es diu "C's", i l'apostrof fa que el
    # cataleg no la reconegui. Nomes per a aquest calcul, no per a l'ingest.
    original = parties.resolve

    def resolve(label, country):
        code, known = original(label, country)
        if code is None and re.fullmatch(r"C['’]s", (label or "").strip()):
            return "?CS", False
        return code, known

    parties.resolve = resolve
    try:
        for table, _section, year in wk.poll_tables(soup, wk.DEFAULT_SECTIONS, wk.DENIED_SECTIONS):
            polls, _unk = wk.parse_table(table, "ES", year or int(date[:4]))
            out += polls
    finally:
        parties.resolve = original
    return out, got["url"]


def evaluate(process: str, date: str, page: str) -> dict:
    result = official(process)
    main = sorted((k for k, v in result.items() if v >= MAIN_SHARE), key=lambda k: -result[k])
    first, second = main[0], main[1]
    e_day = dt.date.fromisoformat(date)
    start = (e_day - dt.timedelta(days=WINDOW_DAYS)).isoformat()
    polls, url = _polls(page, date)

    last: dict[str, object] = {}
    for p in polls:
        end = p.fieldwork_end
        # El mateix dia de l'eleccio nomes hi ha sondeigs a peu d'urna: fora.
        if not end or not (start <= end < date):
            continue
        name = _pollster(p.pollster)
        if not name or name in PARTY_POLLSTERS:
            continue
        shares = {}
        for code, (share, _lo, _hi) in p.results.items():
            c = _canon(code)
            if share is not None:
                shares[c] = shares.get(c, 0) + share
        if sum(1 for k in main if k in shares) < MIN_MAIN:
            continue
        prev = last.get(name)
        if prev is None or end > prev["end"]:
            last[name] = {"end": end, "shares": shares, "sample": p.sample_size,
                          "client": p.client}

    rows = []
    for name, p in last.items():
        errs = [abs(p["shares"][k] - result[k]) for k in main if k in p["shares"]]
        lead = None
        if first in p["shares"] and second in p["shares"]:
            lead = (p["shares"][first] - p["shares"][second]) - (result[first] - result[second])
        rows.append({"pollster": name, "client": p["client"], "end": p["end"],
                     "sample": p["sample"], "mae": round(statistics.mean(errs), 2),
                     "lead": round(lead, 2) if lead is not None else None,
                     "shares": {k: p["shares"][k] for k in main if k in p["shares"]}})
    mean_mae = statistics.mean(r["mae"] for r in rows)
    for r in rows:
        r["plus_minus"] = round(r["mae"] - mean_mae, 2)
    rows.sort(key=lambda r: r["mae"])

    # La mitjana simple de les ultimes enquestes de cada institut: com ho hauria
    # fet una mitjana d'enquestes, sense ponderar.
    avg = {k: statistics.mean(r["shares"][k] for r in rows if k in r["shares"]) for k in main}
    return {"id": process, "date": date, "source": url, "main": main,
            "result": {k: round(result[k], 2) for k in main},
            "average": {k: round(v, 2) for k, v in avg.items()},
            "average_mae": round(statistics.mean(abs(avg[k] - result[k]) for k in main), 2),
            "mean_mae": round(mean_mae, 2), "polls": rows}


def ratings(elections: list[dict]) -> list[dict]:
    by = defaultdict(list)
    for e in elections:
        for r in e["polls"]:
            by[r["pollster"]].append((e["id"], r))
    out = []
    for name, items in by.items():
        pm = statistics.mean(r["plus_minus"] for _, r in items)
        out.append({"pollster": name, "n": len(items),
                    "elections": [eid for eid, _ in items],
                    "mae": round(statistics.mean(r["mae"] for _, r in items), 2),
                    "plus_minus": round(pm, 2),
                    "lead": round(statistics.mean(abs(r["lead"]) for _, r in items
                                                  if r["lead"] is not None), 2)
                    if any(r["lead"] is not None for _, r in items) else None})
    # Primer els que han cobert mes eleccions; dins de cada grup, el mes-menys.
    out.sort(key=lambda r: (r["n"] < 2, r["plus_minus"]))
    return out


def run() -> dict:
    elections = [evaluate(pid, date, page) for pid, date, page in ELECTIONS]
    data = {
        "computed": dt.date.today().isoformat(),
        "window_days": WINDOW_DAYS, "main_share": MAIN_SHARE,
        "names": NAMES,
        "elections": elections,
        "ratings": ratings(elections),
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def load() -> dict | None:
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
