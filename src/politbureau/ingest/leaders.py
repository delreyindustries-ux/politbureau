"""Valoracio dels lideres (08/11/2026): aprovacio, nota i preferit per governar.

Wikipedia porta aquestes enquestes a les pagines d'enquestes de cada pais o en
pagines propies ("Leadership opinion polling for the 2026 Spanish general
election", "Opinion polling on the Sheinbaum presidency"). Cada pais les escriu a
la seva manera, pero n'hi ha tres de formes:

- aprovacio: per a cada persona (o govern), columnes "Approve / Disapprove",
  "Pos. / Neg." o "Y / N". La persona es a la capcalera de dalt o, si la taula
  nomes en porta una, la diu config/leaders.yaml;
- percentatge: "primer ministre preferit", una columna per persona;
- nota: la valoracio de 0 a 10 (Espanya) o de 0 a 5.

Quines taules es llegeixen i com es titulen es decideix a ma, a
config/leaders.yaml: aqui nomes hi ha el lector generic.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup

from .. import db
from . import wikipedia as wk

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "config" / "leaders.yaml"

SCHEMA = """
CREATE TABLE IF NOT EXISTS leader_poll (
    entry       TEXT NOT NULL,   -- id de config/leaders.yaml (ld-es)
    block       TEXT NOT NULL,   -- clau del bloc dins l'entrada (approval, score...)
    country     TEXT NOT NULL,
    subject     TEXT NOT NULL,   -- la persona o el govern valorat
    pollster    TEXT,
    client      TEXT,
    fieldwork_start TEXT,
    fieldwork_end   TEXT NOT NULL,
    sample_size INTEGER,
    yes         REAL,            -- aprovacio: aprova (%)
    no          REAL,            -- aprovacio: desaprova (%)
    value       REAL,            -- percentatge o nota
    pos         INTEGER,         -- ordre de la columna a la pagina
    source_url  TEXT NOT NULL,
    fetched_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS leader_poll_entry ON leader_poll (entry, block);
"""

YES = re.compile(r"^(approve[sd]?|approval|pos\.?|positive|y|yes|trust|favou?rable|good|"
                 r"satisfied|supports?)$", re.I)
NO = re.compile(r"^(disapprove[sd]?|disapproval|neg\.?|negative|n|no|distrust|"
                r"unfavou?rable|bad|dissatisfied|opposes?)$", re.I)
# Columnes que no son cap persona: el que no sap, el saldo, l'avantatge...
NOT_A_SUBJECT = re.compile(
    r"^(net|net approval|lead|und\.?.*|unsure.*|undecided.*|don.?t know.*|no opinion|neither|"
    r"none.*|others?.*|other/.*|all 3.*|no|\?|ref\.?|margin.*|moe|method|question.*|notes?|"
    r"sample.*|mean|average|place|indifferent|decent|n/?a|party leaders|"
    r"do not know|right direction|wrong direction|nobody|not sure|neutral|"
    r"polling.*|fieldwork.*|date.*|pollster.*|poll source|area polled|segment polled|"
    r"not\b.*|.*/ ?ud ?/.*)$", re.I)
NUM = re.compile(r"^[+\-–−]?\s*\d")


def load_config():
    with CONFIG.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _label(cell):
    """Text de la capcalera; si nomes hi ha un logotip, el text alternatiu."""
    if cell is None:
        return ""
    text = wk.cell_text(cell)
    if not text:
        img, link = cell.find("img"), cell.find("a")
        text = (img.get("alt") if img else "") or (link.get("title") if link else "") or ""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\(\s+", "(", re.sub(r"\s+\)", ")", text))
    return text


def _clean_subject(text):
    text = re.sub(r"\s*\[[^\]]*\]", "", text).strip()
    return text.rstrip("*").strip()


def parse(table, anchor_year, metric, subject=None):
    """Llista de (subject, pos, pollster, client, start, end, sample, yes, no, value)."""
    rows = wk.grid(table)
    if len(rows) < 2:
        return []
    width = max(len(r) for r in rows)

    def is_data(row):
        nums = sum(1 for c in row if c is not None and c.name == "td"
                   and NUM.match(wk.cell_text(c)))
        return nums >= 2 or (nums >= 1 and metric != "approval")

    first = next((i for i, r in enumerate(rows) if is_data(r)), None)
    if first is None or first == 0:
        return []
    head = rows[:first]
    labels = []
    for c in range(width):
        seen = []
        for r in head:
            lab = _label(r[c]) if c < len(r) else ""
            if lab and (not seen or seen[-1] != lab):
                seen.append(lab)
        labels.append(seen)
    low = [(ls[-1] if ls else "").lower() for ls in labels]
    top = [" ".join(ls).lower() for ls in labels]

    def col(*keys):
        return next((i for i, h in enumerate(top) if any(k in h for k in keys)), None)

    date_col = col("fieldwork", "date", "conducted")
    pollster_col = col("polling firm", "pollster", "poll source", "polling organisation",
                       "polling organization", "polling agency", "polling group")
    sample_col = col("sample")
    fixed = {date_col, pollster_col, sample_col}
    if date_col is None or pollster_col is None:
        return []

    cols = {}                 # columna -> (subject, "yes"|"no"|"value")
    for c, ls in enumerate(labels):
        if c in fixed or not ls:
            continue
        last = ls[-1]
        if YES.match(last) or NO.match(last):
            kind = "yes" if YES.match(last) else "no"
            name = next((x for x in reversed(ls[:-1]) if not NOT_A_SUBJECT.match(x)
                         and not YES.match(x) and not NO.match(x)), None)
            name = name or subject
            if metric == "approval" and name:
                cols[c] = (_clean_subject(name), kind)
        elif metric != "approval" and not NOT_A_SUBJECT.match(last):
            cols[c] = (_clean_subject(last), "value")
    if not cols:
        return []
    order = {}
    for c, (name, _k) in sorted(cols.items()):
        order.setdefault(name, len(order))

    out, year, previous_end = [], anchor_year, None
    today = dt.date.today()
    for cells in rows[first:]:
        if len(cells) <= max(date_col, pollster_col):
            continue
        raw = wk.cell_text(cells[pollster_col])
        if not raw or re.search(r"\b(elections?|referendum)\b", raw, re.I):
            continue
        date_text = wk.cell_text(cells[date_col])
        start, end = wk.parse_fieldwork(date_text, year)
        if end and previous_end and (dt.date.fromisoformat(end)
                                     - dt.date.fromisoformat(previous_end)).days > 90:
            year -= 1
            start, end = wk.parse_fieldwork(date_text, year)
        # Una data sense any que cau al futur es de l'any passat.
        if end and dt.date.fromisoformat(end) > today + dt.timedelta(days=7) \
                and not re.search(r"(?:19|20)\d{2}", date_text):
            year -= 1
            start, end = wk.parse_fieldwork(date_text, year)
        if not end:
            continue
        previous_end = end
        pollster, _, client = raw.partition("/")
        sample = (wk.parse_int(wk.cell_text(cells[sample_col]))
                  if sample_col is not None and sample_col < len(cells) else None)
        got, seen = {}, set()
        for c, (name, kind) in cols.items():
            if c >= len(cells) or id(cells[c]) in seen:
                continue
            seen.add(id(cells[c]))
            v = wk.parse_cell(wk.cell_text(cells[c]))[0]
            if v is None:
                continue
            got.setdefault(name, {})[kind] = v
        for name, vals in got.items():
            if metric == "approval" and ("yes" not in vals or "no" not in vals):
                continue
            if metric == "score" and not 0 <= vals.get("value", -1) <= 10:
                continue
            out.append((name, order[name], pollster.strip() or raw, client.strip() or None,
                        start, end, sample, vals.get("yes"), vals.get("no"), vals.get("value")))
    return out


def _tables(soup, section, deny=()):
    for table in soup.select("table.wikitable"):
        chain = wk.heading_chain(table)
        sec = " > ".join(chain).lower()
        if section not in sec or any(d in sec for d in deny):
            continue
        year = next((int(h) for h in chain if re.fullmatch(r"(?:19|20)\d{2}", h.strip())), None)
        yield table, year


def _subject_ca(subject):
    return subject.get("ca") if isinstance(subject, dict) else subject


def renames(entry, block):
    """{nom de la capcalera: nom en catala} de l'entrada i del bloc."""
    out = {}
    for src in (entry.get("rename") or {}, block.get("rename") or {}):
        out.update({k: _subject_ca(v) for k, v in src.items()})
    return out


def names_es(entry):
    """{nom en catala: nom en castella} dels governs ("Govern Meloni")."""
    out = {}
    for block in entry["blocks"]:
        for src in [entry.get("rename") or {}, block.get("rename") or {}] + [
                {"": t.get("subject")} for t in block["tables"]]:
            for v in src.values():
                if isinstance(v, dict):
                    out[v["ca"]] = v["es"]
    return out


def run(conn, only=None):
    conn.executescript(SCHEMA)
    cfg = load_config()
    session = requests.Session()
    pages, summary = {}, []
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    def page_of(name, lang, entry_id):
        if (name, lang) not in pages:
            try:
                page = wk.fetch(name, session, lang=lang)
            except Exception as exc:                  # noqa: BLE001
                db.log_ingest(conn, entry_id, name, "error", 0, f"{type(exc).__name__}: {exc}")
                page = None
            if page:
                page["_soup"] = BeautifulSoup(page["html"], "lxml")
            pages[(name, lang)] = page
        return pages[(name, lang)]

    for entry in cfg.get("leaders") or []:
        if only and entry["id"] not in only and entry["country"] not in only:
            continue
        for block in entry["blocks"]:
            rows, urls, k = [], [], 0
            rename = renames(entry, block)
            for spec in block["tables"]:
                page = page_of(spec.get("page") or entry["page"],
                               spec.get("lang") or entry.get("lang", "en"), entry["id"])
                if page is None:
                    continue
                for table, year in _tables(page["_soup"], spec["section"],
                                           tuple(spec.get("deny") or ())):
                    try:
                        got = parse(table, year or dt.date.today().year, block["metric"],
                                    subject=_subject_ca(spec.get("subject")))
                    except Exception as exc:          # noqa: BLE001
                        print(f"   AVIS {entry['id']} {block['key']}: {type(exc).__name__}: {exc}")
                        continue
                    # L'ordre de la pagina: la primera taula (el cap de govern,
                    # gairebe sempre) va al davant.
                    rows += [(rename.get(r[0], r[0]), k * 100 + r[1], *r[2:], page["url"])
                             for r in got]
                    k += 1
            # Cada descarrega substitueix l'anterior: si Wikipedia corregeix una
            # xifra, la bona es la d'avui, no la primera que es va llegir.
            conn.execute("DELETE FROM leader_poll WHERE entry = ? AND block = ?",
                         (entry["id"], block["key"]))
            conn.executemany(
                "INSERT INTO leader_poll (entry, block, country, subject, pos, pollster, client, "
                "fieldwork_start, fieldwork_end, sample_size, yes, no, value, source_url, "
                "fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [(entry["id"], block["key"], entry["country"], *r, now) for r in rows])
            conn.commit()
            db.log_ingest(conn, entry["id"], entry["page"], "ok", len(rows),
                          {"block": block["key"]})
            summary.append((entry["id"], block["key"], len(rows)))
    return summary


# ------------------------------------------------------------------- mitjanes

MAX_AGE = 120       # dies: hi ha paisos on la valoracio es pregunta un cop al mes
HALF_LIFE = 14


def averages(conn, entry_id, block, limit=8, asof=None):
    """[{subject, yes, no, net, value, n, last, pollsters}] amb la mateixa regla que
    la intencio de vot: la darrera enquesta de cada casa, i la que es mes nova pesa mes.

    `asof`: la mitjana tal com era aquell dia (nomes amb les enquestes ja acabades),
    per veure com ha canviat."""
    try:
        rows = conn.execute(
            "SELECT subject, pos, pollster, fieldwork_end, sample_size, yes, no, value "
            "FROM leader_poll WHERE entry = ? AND block = ? ORDER BY fieldwork_end DESC",
            (entry_id, block)).fetchall()
    except Exception:                                  # base sense la taula
        return []
    today = asof or dt.date.today()
    by = {}
    for r in rows:
        end = dt.date.fromisoformat(r["fieldwork_end"])
        age = (today - end).days
        if age > MAX_AGE or age < (0 if asof else -7):
            continue
        key = (r["pollster"] or "").lower()
        latest = by.setdefault(r["subject"], {"pos": r["pos"], "seen": {}})
        latest["pos"] = min(latest["pos"], r["pos"])
        if key in latest["seen"]:
            continue
        latest["seen"][key] = (r, max(age, 0))
    out = []
    newest = max((r["fieldwork_end"] for info in by.values() for r, _a in info["seen"].values()),
                 default=None)
    for subject, info in by.items():
        polls = list(info["seen"].values())
        w = [0.5 ** (age / HALF_LIFE) for _r, age in polls]
        tot = sum(w)

        def mean(field):
            vals = [(r[field], wi) for (r, _a), wi in zip(polls, w) if r[field] is not None]
            s = sum(wi for _v, wi in vals)
            return sum(v * wi for v, wi in vals) / s if s else None
        yes, no, value = mean("yes"), mean("no"), mean("value")
        last = max(r["fieldwork_end"] for r, _a in polls)
        # Qui fa dos mesos que no surt a cap enquesta ja no es lider (Starmer,
        # el juliol del 2026): no es compara amb els d'ara.
        if (dt.date.fromisoformat(newest) - dt.date.fromisoformat(last)).days > 60:
            continue
        out.append({"subject": subject, "pos": info["pos"], "yes": yes, "no": no,
                    "net": (yes - no) if yes is not None and no is not None else None,
                    "value": value, "n": len(polls), "last": last, "weight": tot,
                    "pollsters": sorted({r["pollster"] for r, _a in polls})})
    out.sort(key=lambda d: (d["pos"], -d["n"]))
    return out[:limit]


TREND_DAYS = 30


def with_trend(conn, entry_id, block, rows):
    """Afegeix a cada fila `delta`: com ha canviat el saldo (o el valor) en 30 dies.

    Es compara cada institut amb ell mateix: la seva darrera enquesta contra la
    darrera que tenia fa 30 dies. Comparar les dues mitjanes enganya quan hi ha
    pocs instituts: si el mes passat no hi era el que dona notes mes altes,
    sembla una pujada i nomes es un canvi de qui pregunta (Espanya, 09/11/2026:
    Sanchez +13,8 punts amb tres instituts). None si cap institut ha tornat a
    preguntar en aquests 30 dies."""
    today = dt.date.today()
    cut = today - dt.timedelta(days=TREND_DAYS)
    data = conn.execute(
        "SELECT subject, pollster, fieldwork_end, yes, no, value FROM leader_poll "
        "WHERE entry = ? AND block = ? AND fieldwork_end >= ? ORDER BY fieldwork_end DESC",
        (entry_id, block, (cut - dt.timedelta(days=MAX_AGE)).isoformat())).fetchall()
    now, before = {}, {}
    for r in data:
        key = (r["subject"], (r["pollster"] or "").lower())
        end = dt.date.fromisoformat(r["fieldwork_end"])
        if (today - end).days <= MAX_AGE:
            now.setdefault(key, r)
        if end <= cut:
            before.setdefault(key, r)

    def metric(r):
        if r["yes"] is not None and r["no"] is not None:
            return r["yes"] - r["no"]
        return r["value"]
    for row in rows:
        diffs = []
        for (subject, firm), r in now.items():
            b = before.get((subject, firm))
            if subject != row["subject"] or not b or r["fieldwork_end"] <= cut.isoformat():
                continue
            if metric(r) is not None and metric(b) is not None:
                diffs.append(metric(r) - metric(b))
        row["delta"] = sum(diffs) / len(diffs) if diffs else None
        row["delta_n"] = len(diffs)
    return rows
