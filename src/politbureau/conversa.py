"""Termometre de conversa: visibilitat i conversa de cada partit (20/11/2026).

Tres mesures d'atencio, cadascuna com a quota sobre els partits seguits
(config/conversa.yaml), al costat de la quota de vot de les enquestes:

  * visibilitat: visites d'usuaris als articles de la Viquipedia del partit i
    del seu lider (es, ca, eu, gl). Wikimedia Pageviews API, dades CC0.
  * xarxes: missatges de Bluesky que els mencionen (API publica). Nomes es
    compten: no es desa cap text, autor ni enllac.
  * premsa: GDELT DOC 2.0 hi era previst, pero el 20/11/2026 tornava "limit
    requests" fins i tot amb 6 segons entre consultes: fora fins que sigui fiable.

NO entra a la mitjana de vot (vegeu la prova del 23J al cap de conversa.yaml).

`politbureau conversa` ho baixa i ho desa a data/conversa/conversa.json. Si una
font falla, es conserva el que hi havia d'aquella font.
"""
from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path
from urllib.parse import quote

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "conversa.yaml"
OUT = ROOT / "data" / "conversa" / "conversa.json"
UA = {"User-Agent": "politbureau (politbureau.es)"}
WIKI_LANGS = ("es", "ca", "eu", "gl")
BSKY = "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts"


def config() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def _get(session, url, params=None, tries=6, pause=0.2):
    for attempt in range(tries):
        try:
            r = session.get(url, params=params, headers=UA, timeout=60)
        except Exception:                                # noqa: BLE001
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code == 200:
            time.sleep(pause)
            return r
        if r.status_code in (404, 400):
            return None
        time.sleep(float(r.headers.get("Retry-After") or 5 * (attempt + 1)))
    return None


# ------------------------------------------------------------------ Viquipedia
def _wiki_titles(session, titles):
    """{titol es: {idioma: titol}} resolent redireccions i enllacos d'idioma."""
    out = {}
    r = _get(session, "https://es.wikipedia.org/w/api.php", {
        "action": "query", "titles": "|".join(titles), "redirects": 1, "prop": "langlinks",
        "lllimit": "max", "format": "json", "formatversion": 2})
    if not r:
        return out
    q = r.json().get("query") or {}
    back = {}
    for x in (q.get("normalized") or []) + (q.get("redirects") or []):
        back[x["to"]] = back.get(x["from"], x["from"])
    for p in q.get("pages") or []:
        if p.get("missing"):
            continue
        orig = back.get(p["title"], p["title"])
        langs = {"es": p["title"]}
        for ll in p.get("langlinks") or []:
            if ll["lang"] in WIKI_LANGS:
                langs[ll["lang"]] = ll["title"]
        out[orig] = langs
    return out


def wiki(session, cfg, start, end) -> dict:
    """{partit: {data: visites}}."""
    titles = sorted({t for p in cfg["parties"].values() for t in p.get("wiki", [])})
    resolved = {}
    for i in range(0, len(titles), 40):
        resolved.update(_wiki_titles(session, titles[i:i + 40]))
    out = {}
    for code, p in cfg["parties"].items():
        series: dict = {}
        for t in p.get("wiki", []):
            for lang, title in (resolved.get(t) or {}).items():
                url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
                       f"{lang}.wikipedia/all-access/user/{quote(title.replace(' ', '_'), safe='')}"
                       f"/daily/{start:%Y%m%d}/{end:%Y%m%d}")
                r = _get(session, url, pause=0.05)
                for it in (r.json().get("items") if r else None) or []:
                    d = f"{it['timestamp'][:4]}-{it['timestamp'][4:6]}-{it['timestamp'][6:8]}"
                    series[d] = series.get(d, 0) + it["views"]
        out[code] = series
    return out


# ------------------------------------------------------------------ Bluesky
def _bsky_count(term, day, lang):
    import requests
    params = {"q": term, "limit": 1, "lang": lang,
              "since": f"{day:%Y-%m-%d}T00:00:00Z",
              "until": f"{day + dt.timedelta(days=1):%Y-%m-%d}T00:00:00Z"}
    for attempt in range(5):
        try:
            r = requests.get(BSKY, params=params, headers=UA, timeout=30)
        except Exception:                                # noqa: BLE001
            time.sleep(3 * (attempt + 1))
            continue
        if r.status_code == 200:
            return int(r.json().get("hitsTotal") or 0)
        time.sleep(float(r.headers.get("Retry-After") or 3 * (attempt + 1)))
    raise RuntimeError(f"Bluesky no respon ({term}, {day})")


def bluesky(cfg, days, old=None) -> dict:
    """{partit: {data: missatges}} en castella i catala. Una consulta per terme,
    dia i idioma: l'API torna el total de resultats (`hitsTotal`) sense paginar.
    Nomes es demanen els dies que no hi son a `old` (i sempre els dos ultims).
    Si un missatge porta dos termes del mateix partit, compta dues vegades:
    passa igual a tots els partits."""
    from concurrent.futures import ThreadPoolExecutor
    old = old or {}
    fresh = {d.isoformat() for d in days[-2:]}
    jobs = []
    for code, p in cfg["parties"].items():
        have = old.get(code) or {}
        for day in days:
            if day.isoformat() in have and day.isoformat() not in fresh:
                continue
            for term in p.get("terms", []):
                for lang in ("es", "ca"):
                    jobs.append((code, day, term, lang))
    with ThreadPoolExecutor(max_workers=8) as pool:
        counts = list(pool.map(lambda j: _bsky_count(j[2], j[1], j[3]), jobs))
    out = {code: {k: v for k, v in (old.get(code) or {}).items()
                  if k >= days[0].isoformat()} for code in cfg["parties"]}
    redo = {(c, d.isoformat()) for c, d, _t, _l in jobs}
    for c, d in redo:
        out[c][d] = 0
    for (code, day, _t, _l), n in zip(jobs, counts):
        out[code][day.isoformat()] += n
    return out


def _signature(cfg) -> str:
    """Si canvien els termes o els articles, la serie vella ja no compara."""
    import hashlib
    return hashlib.sha1(json.dumps(cfg["parties"], sort_keys=True).encode()).hexdigest()[:12]


def run() -> dict:
    import requests
    cfg = config()
    session = requests.Session()
    end = dt.date.today() - dt.timedelta(days=1)                 # l'ultim dia sencer
    start = end - dt.timedelta(days=cfg.get("history_days", 60) - 1)
    try:
        old = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        old = {}
    sig = _signature(cfg)
    same = old.get("signature") == sig
    data = {"computed": dt.date.today().isoformat(), "end": end.isoformat(), "signature": sig,
            "sources": {"wiki": "Wikimedia Pageviews API (CC0)",
                        "bsky": "Bluesky, app.bsky.feed.searchPosts (castella i catala)"},
            "series": {}}
    bdays = [end - dt.timedelta(days=k) for k in range(cfg.get("bsky_days", 28) - 1, -1, -1)]
    got = {}
    for key, fn in (("wiki", lambda: wiki(session, cfg, start, end)),
                    ("bsky", lambda: bluesky(cfg, bdays, (old.get("series") or {}).get("bsky")
                                             if same else None))):
        try:
            res = fn()
            if not any(res.values()):
                raise RuntimeError("cap dada")
            got[key] = res
            print(f"  {key:<5} {sum(sum(s.values()) for s in res.values()):>10,} en total", flush=True)
        except Exception as exc:                                  # noqa: BLE001
            print(f"  {key:<5} ERROR ({type(exc).__name__}: {exc}); es conserva l'anterior", flush=True)
            got[key] = ((old.get("series") or {}).get(key) or {}) if same else {}
    data["series"] = got
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return data


def load() -> dict:
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _window_sum(series: dict, end: dt.date, days: int, offset: int = 0) -> float:
    total = 0
    for k in range(offset, offset + days):
        total += series.get((end - dt.timedelta(days=k)).isoformat(), 0)
    return total


def summary(vote: dict) -> dict | None:
    """Quotes de la finestra (ultims `window_days` dies sencers) i de la
    setmana anterior, per font, i la quota de vot de cada partit sobre els
    mateixos partits. `vote`: {partit: % de la mitjana}."""
    d = load()
    if not d.get("series"):
        return None
    cfg = config()
    w = cfg.get("window_days", 7)
    end = dt.date.fromisoformat(d["end"])
    codes = list(cfg["parties"])
    out = {"end": d["end"], "computed": d["computed"], "window": w, "capped": d.get("bsky_capped") or [],
           "sources": [], "rows": []}
    shares, prev = {}, {}
    for key in ("wiki", "bsky"):
        s = d["series"].get(key) or {}
        now = {c: _window_sum(s.get(c) or {}, end, w) for c in codes}
        before = {c: _window_sum(s.get(c) or {}, end, w, w) for c in codes}
        tn, tb = sum(now.values()), sum(before.values())
        if not tn:
            continue
        out["sources"].append(key)
        shares[key] = {c: 100.0 * now[c] / tn for c in codes}
        prev[key] = {c: (100.0 * before[c] / tb) if tb else None for c in codes}
        out.setdefault("totals", {})[key] = tn
    if not shares:
        return None
    vt = sum(vote.get(c, 0) for c in codes) or 1.0
    for c in codes:
        att = [shares[k][c] for k in shares]
        mean = sum(att) / len(att)
        pv = [prev[k][c] for k in prev if prev[k][c] is not None]
        mean_prev = sum(pv) / len(pv) if len(pv) == len(att) else None
        v = 100.0 * vote.get(c, 0) / vt if vote.get(c) else None
        out["rows"].append({"code": c, "vote": v, "att": mean,
                            "by": {k: shares[k][c] for k in shares},
                            "gap": (mean - v) if v is not None else None,
                            "trend": (mean - mean_prev) if mean_prev is not None else None})
    out["rows"].sort(key=lambda r: -r["att"])
    # Serie diaria de la quota d'atencio (Viquipedia i premsa: les que tenen 60 dies).
    days = sorted({day for k in ("wiki",) for s in (d["series"].get(k) or {}).values() for day in s})
    days = [x for x in days if x <= d["end"]][-cfg.get("history_days", 60):]
    spark = {c: [] for c in codes}
    for day in days:
        per = []
        for k in ("wiki",):
            s = d["series"].get(k) or {}
            tot = sum((s.get(c) or {}).get(day, 0) for c in codes)
            if tot:
                per.append({c: 100.0 * (s.get(c) or {}).get(day, 0) / tot for c in codes})
        for c in codes:
            spark[c].append(sum(p[c] for p in per) / len(per) if per else None)
    out["days"], out["spark"] = days, spark
    return out
