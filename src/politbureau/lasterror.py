"""Error de la mitjana a l'ultima eleccio de cada pais (pla de ruta, 14/11/2026).

Per a cada eleccio estrangera amb pagina a la web es refa la mitjana de
Polit Bureau tal com hauria sortit el dia abans de l'ultima eleccio, amb les
mateixes regles que la mitjana actual (build.load_polls + model.aggregate):
fora enquestes internes de partits, nomes l'ultima de cada institut, 90 dies,
300 entrevistes, pes per recencia i per mostra. Despres es compara amb el
resultat.

  * Enquestes: la pagina de la Wikipedia del cicle anterior ("Opinion polling
    for the 2024 United Kingdom general election"), llegida amb el mateix
    lector que les enquestes actuals.
  * Resultat: la fila "2024 general election" de les mateixes taules, que
    porta el resultat amb les mateixes columnes que les enquestes. Si la pagina
    anterior no en te, la de la pagina actual.
  * Error: mitjana de l'error absolut, en punts, dels partits que van treure
    almenys el 3 % (com a la valoracio d'instituts, pollsters.py).

`politbureau error-anterior` ho calcula i ho desa a config/last_error.json; la
web nomes llegeix aquest fitxer, aixi la generacio no depen de la xarxa.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import statistics
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "config" / "last_error.json"

MAIN_SHARE = 3.0      # partits que compten: >= 3 % al resultat
POLLSTER_DAYS = 30    # valoracio d'instituts: la seva ultima enquesta del mes d'abans
MIN_MAIN = 3          # cal comparar com a minim 3 partits
MIN_POLLS = 2         # i que la mitjana surti d'almenys 2 instituts
EXCLUDED = {"US", "BR", "RU"}
ORD = {1: "st", 2: "nd", 3: "rd"}


def _ordinal(n: int) -> str:
    suf = "th" if 10 <= n % 100 <= 20 else ORD.get(n % 10, "th")
    return f"{n}{suf}"


def candidates(page: str, prev_year: int) -> list[str]:
    """Noms possibles de la pagina d'enquestes del cicle anterior."""
    t = page.replace("_", " ").strip()
    out = []

    def add(x):
        x = re.sub(r"\s+", " ", x).strip()
        if x and x not in out and x != t:
            out.append(x)

    base = t
    m = re.match(r"(?i)opinion polling for the (.+)$", t)
    if m:
        base = m.group(1)
    base = re.sub(r"(?i)^the\s+", "", base)
    # "next X election" / "Next X election" -> "2024 X election"
    stem = re.sub(r"(?i)^next\s+", f"{prev_year} ", base)
    # "2027 X election" -> "2023 X election"
    stem = re.sub(r"^(?:19|20)\d{2}\b", str(prev_year), stem)
    # "46th Canadian federal election" -> "45th Canadian federal election"
    mo = re.match(r"^(\d+)(?:st|nd|rd|th)\b", stem)
    if mo:
        stem = _ordinal(int(mo.group(1)) - 1) + stem[mo.end():]
    if not re.match(r"^((?:19|20)\d{2}|\d+(?:st|nd|rd|th))\b", stem):
        stem = f"{prev_year} {stem}"
    add(f"Opinion polling for the {stem}")
    add(stem)
    # Alguns paisos: "elections" en plural o "legislative"/"parliamentary".
    if stem.endswith("election"):
        add(f"Opinion polling for the {stem}s")
    for a, b in (("parliamentary", "legislative"), ("legislative", "parliamentary"),
                 ("general", "parliamentary"), ("parliamentary", "general"),
                 ("federal", "parliamentary")):
        if a in stem:
            add(f"Opinion polling for the {stem.replace(a, b)}")
    return out


def _sections(election):
    from .ingest import runner as rn
    from .ingest import wikipedia as wk
    sections = tuple(election.get("sections") or ()) + rn.EUROPA_SECTIONS
    deny = tuple(election.get("deny_sections") or ()) + rn.EUROPA_DENY
    return wk.DEFAULT_SECTIONS + sections, wk.DENIED_SECTIONS + deny


def read(session, page_name, election):
    """(enquestes, files de resultat, url) d'una pagina, sense desar res."""
    from .ingest import wikipedia as wk
    page = wk.fetch(page_name, session, lang=election.get("lang", "en"))
    if page is None:
        return None
    soup = BeautifulSoup(page["html"], "lxml")
    allowed, denied = _sections(election)
    polls, results = [], []
    for table, _section, year in wk.poll_tables(soup, allowed, denied,
                                                force=tuple(election.get("force_sections") or ())):
        try:
            got, _unk = wk.parse_table(table, election["country"],
                                       year or _page_year(page["title"]), results=results)
        except Exception:                          # noqa: BLE001
            continue
        polls += got
    return polls, results, page


def _page_year(title):
    m = re.search(r"\b((?:19|20)\d{2})\b", title)
    return int(m.group(1)) if m else dt.date.today().year


def _shares(poll, merge, drop):
    out = {}
    for code, (share, _lo, _hi) in poll.results.items():
        if share is None or code in drop:
            continue
        c = merge.get(code, code)
        out[c] = out.get(c, 0.0) + share
    return out


# Files de resultat que no son de la mateixa cambra: europees, locals,
# regionals, referendums... (a Croacia, Grecia o Eslovaquia la fila mes recent
# de la taula era la de les europees del 2024).
_OTHER_KIND = re.compile(r"europ|\bEP\b|local|municipal|regional|county|provincial|mayor"
                         r"|referend|senate|by-?election|primar", re.I)


def _fix_year(row):
    """La data de la fila es llegeix amb l'any de la taula; si l'etiqueta porta
    l'any ("2025 parliamentary election"), mana l'etiqueta (Noruega, Polonia)."""
    m = re.search(r"\b((?:19|20)\d{2})\b", row.pollster or "")
    if m and row.fieldwork_end and row.fieldwork_end[:4] != m.group(1):
        try:
            row.fieldwork_end = dt.date(int(m.group(1)), int(row.fieldwork_end[5:7]),
                                        int(row.fieldwork_end[8:10])).isoformat()
        except ValueError:
            pass
    return row


def _result_rows(results, presidential):
    out = []
    for r in results:
        label = (r.pollster or "") + " " + (r.client or "")
        if _OTHER_KIND.search(label):
            continue
        if not presidential and re.search(r"president", label, re.I):
            continue
        if (presidential and re.search(r"parliament|legislative", label, re.I)
                and not re.search(r"president", label, re.I)):
            continue
        if r.fieldwork_end:
            out.append(_fix_year(r))
    return out


def _last_result(results, before, presidential=False):
    """La fila de resultat mes recent d'abans de `before` (amb data)."""
    rows = [r for r in _result_rows(results, presidential) if r.fieldwork_end < before]
    return max(rows, key=lambda r: r.fieldwork_end) if rows else None


def evaluate(session, election, today=None) -> dict | None:
    from .build import is_party_poll, latest_per_pollster
    from .model.aggregate import aggregate

    today = (today or dt.date.today()).isoformat()
    merge = election.get("merge") or {}
    drop = set(election.get("drop") or [])
    country = election["country"]

    presidential = election.get("display") == "candidates"
    cur = read(session, election["page"], election)
    if cur is None:
        return {"id": election["id"], "status": "no-page"}
    _polls, cur_results, _page = cur
    last = _last_result(cur_results, today, presidential)
    if last is not None:
        years = [int(last.fieldwork_end[:4])]
    else:
        # Sense fila de resultat a la pagina actual (moltes pagines "Next ..."
        # comencen de zero): l'any de la base del mapa ("les generals del 2022")
        # o, si no n'hi ha, els cinc anys d'abans.
        base = (election.get("departments") or {}).get("base_ca") or ""
        m = re.search(r"\b((?:19|20)\d{2})\b", base)
        this = dt.date.today().year
        years = [int(m.group(1))] if m else list(range(this, this - 6, -1))

    tried = []
    names = [(y, n) for y in years for n in candidates(election["page"], y)]
    # La pagina actual pot ser la del cicle anterior si l'eleccio ja ha passat.
    if any(str(y) in election["page"] for y in years):
        names.insert(0, (years[0], election["page"]))
    for year, name in names:
        if name in tried:
            continue
        tried.append(name)
        got = read(session, name, election)
        if got is None:
            continue
        polls, results, page = got
        own = _last_result(results, today, presidential)
        if last is None or (own and own.fieldwork_end[:4] == str(year) and abs(
                (dt.date.fromisoformat(own.fieldwork_end)
                 - dt.date.fromisoformat(last.fieldwork_end)).days) <= 3):
            if own is None or own.fieldwork_end[:4] != str(year):
                continue
            ref = own
        else:
            ref = last
        e_date = ref.fieldwork_end
        # La pagina ha de tenir enquestes dels 90 dies d'abans de l'eleccio.
        start = (dt.date.fromisoformat(e_date) - dt.timedelta(days=90)).isoformat()
        before = [p for p in polls if p.fieldwork_end and start <= p.fieldwork_end < e_date]
        if len(before) < MIN_POLLS:
            continue
        # Resultat: la fila d'aquesta pagina amb la data de l'eleccio (+-3 dies).
        res_row = next((r for r in _result_rows(results, presidential) if abs(
            (dt.date.fromisoformat(r.fieldwork_end) - dt.date.fromisoformat(e_date)).days) <= 3),
            None) or ref
        result = _shares(res_row, merge, drop)
        # "Altres" i independents no son cap partit: fora de la comparacio.
        for k in [k for k in result if k == "OTHER" or re.match(r"\?(OTH|OTHERS?|IND|INDEPENDENTS?)$", k)]:
            result.pop(k)
        main = sorted((k for k, v in result.items() if v >= MAIN_SHARE), key=lambda k: -result[k])

        entries = {}
        for i, p in enumerate(before):
            if is_party_poll(p.pollster, country):
                continue
            entries[i] = {"pollster": (p.pollster or "").strip(), "fieldwork_end": p.fieldwork_end,
                          "sample_size": p.sample_size,
                          "results": {k: (v, None, None) for k, v in _shares(p, merge, drop).items()}}
        # Enquestes que no sumen com un resultat: amb el vot "dos partits"
        # barrejat (Austràlia, >110 %) o amb els indecisos dins (Japó, <85 %).
        # Comparar-les amb el vot valid no seria just.
        entries = {i: e for i, e in entries.items()
                   if 85 <= sum(v for v, _a, _b in e["results"].values()) <= 110}
        latest = latest_per_pollster(entries)
        cutoff = dt.date.fromisoformat(e_date) - dt.timedelta(days=1)
        agg = aggregate(latest, today=cutoff)
        rows = [{"party": k, "average": agg[k]["share"], "result": round(result[k], 2),
                 "diff": round(agg[k]["share"] - result[k], 2)} for k in main if k in agg]
        if len(rows) < MIN_MAIN:
            return {"id": election["id"], "status": "few-parties", "page": page["url"],
                    "date": e_date, "main": main, "have": sorted(agg)}
        n_polls = max((agg[k]["n_polls"] for k in main if k in agg), default=0)
        if n_polls < MIN_POLLS:
            continue
        missing = [k for k in main if k not in agg]
        # Valoracio d'instituts (26/11/2026, com la d'Espanya): l'ultima enquesta
        # de cada institut del mes d'abans de l'eleccio contra el resultat.
        recent = (dt.date.fromisoformat(e_date) - dt.timedelta(days=POLLSTER_DAYS)).isoformat()
        first, second = (main + [None, None])[:2]
        prow = []
        for e in latest:
            if e["fieldwork_end"] < recent or not e["pollster"]:
                continue
            sh = {k: v for k, (v, _a, _b) in e["results"].items()}
            have = [k for k in main if k in sh]
            if len(have) < MIN_MAIN:
                continue
            lead = ((sh[first] - sh[second]) - (result[first] - result[second])
                    if first in sh and second in sh else None)
            prow.append({"pollster": e["pollster"], "end": e["fieldwork_end"], "sample": e.get("sample_size"),
                         "mae": round(statistics.mean(abs(sh[k] - result[k]) for k in have), 2),
                         "lead": round(lead, 2) if lead is not None else None, "n": len(have)})
        prow.sort(key=lambda r: r["mae"])
        return {"id": election["id"], "status": "ok", "date": e_date, "pollsters": prow,
                "election": (res_row.pollster or "").strip(),
                "page": page["url"], "result_from": "previous" if res_row is not last else "current",
                "cutoff": cutoff.isoformat(), "n_polls": n_polls,
                "mae": round(statistics.mean(abs(r["diff"]) for r in rows), 2),
                "rows": rows, "missing": missing,
                "labels": {k: (res_row.labels.get(k) or "") for k in main},
                "colors": {k: c for k in main
                           if (c := (res_row.colors or {}).get(k)
                               or next((p.colors.get(k) for p in before if p.colors.get(k)), None))}}
    return {"id": election["id"], "status": "no-previous-page",
            "date": last.fieldwork_end if last else None, "tried": tried}


def elections():
    from .ingest import runner as rn
    cfg = rn.load_config()
    for e in cfg["elections"]:
        if e.get("group") not in ("europa", "mon") or e.get("country") in EXCLUDED:
            continue
        if not e.get("national", True):
            continue
        yield e


def run(only=None) -> dict:
    session = requests.Session()
    # Amb `only`, es refan nomes aquells paisos i la resta es conserva.
    out = dict((load().get("elections") or {}) if only else {})
    for e in elections():
        if only and e["id"] not in only:
            continue
        try:
            r = evaluate(session, e)
        except Exception as exc:                  # noqa: BLE001
            r = {"id": e["id"], "status": "error", "error": f"{type(exc).__name__}: {exc}"}
        out[e["id"]] = r
        print(f"  {e['id']:14} {r.get('status'):18} {r.get('date') or '':10} "
              f"MAE {r.get('mae', '')}  {r.get('page') or ''}", flush=True)
    data = {"computed": dt.date.today().isoformat(), "main_share": MAIN_SHARE,
            "elections": out}
    OUT.write_bytes(json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8"))
    return data


# Noms que son el metode de l'enquesta, no l'institut (columna mal llegida).
_NOT_POLLSTER = re.compile(r"^(online|telephone|phone|cati|cawi|ivr|mixed|face[- ]to[- ]face|web|internet|sms)$", re.I)


def load() -> dict:
    try:
        data = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    for r in (data.get("elections") or {}).values():
        if r.get("pollsters"):
            r["pollsters"] = [x for x in r["pollsters"] if not _NOT_POLLSTER.match((x.get("pollster") or "").strip())]
    return data
