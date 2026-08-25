"""Orquestra la ingesta: llegeix config/sources.yaml i omple la base de dades."""
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
SOURCES = ROOT / "config" / "sources.yaml"


def load_config():
    with SOURCES.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def store(conn, election, country, scope, scope_code, scope_name, page, polls):
    """Insereix enquestes. La clau UNIQUE fa que re-executar la ingesta
    sigui idempotent: les que ja hi son no es dupliquen."""
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    inserted = 0
    for poll in polls:
        if not poll.fieldwork_end:
            continue
        cur = conn.execute(
            """INSERT OR IGNORE INTO poll
               (election_id, country, scope, scope_code, scope_name, pollster, client,
                fieldwork_start, fieldwork_end, sample_size, turnout,
                source_url, source_title, fetched_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (election, country, scope, scope_code, scope_name, poll.pollster, poll.client,
             poll.fieldwork_start, poll.fieldwork_end, poll.sample_size, poll.turnout,
             page["url"], page["title"], now),
        )
        if not cur.rowcount:
            continue
        poll_id = cur.lastrowid
        conn.executemany(
            "INSERT OR REPLACE INTO poll_result (poll_id, party, share, seats_lo, seats_hi) "
            "VALUES (?,?,?,?,?)",
            [(poll_id, code, share, lo, hi) for code, (share, lo, hi) in poll.results.items()],
        )
        inserted += 1
    conn.commit()
    return inserted


def read_page(conn, session, election_id, country, scope, page_name,
              scope_code=None, scope_name=None):
    try:
        page = wk.fetch(page_name, session)
    except Exception as exc:                      # noqa: BLE001
        # Una pagina caiguda o un tall de xarxa no pot fer perdre les altres
        # trenta que ja s'havien llegit be.
        db.log_ingest(conn, election_id, page_name, "error", 0,
                      f"{type(exc).__name__}: {exc}")
        return 0, []
    if page is None:
        db.log_ingest(conn, election_id, page_name, "skipped", 0, "la pagina no existeix")
        return 0, []
    soup = BeautifulSoup(page["html"], "lxml")
    this_year = dt.date.today().year
    polls, unknown = [], set()
    for table, _section, year in wk.poll_tables(soup):
        got, unk = wk.parse_table(table, country, year or this_year)
        polls += got
        unknown.update(unk)
    n = store(conn, election_id, country, scope, scope_code, scope_name, page, polls)
    db.log_ingest(conn, election_id, page["url"], "ok", n,
                  {"parsed": len(polls), "new": n, "unmapped": sorted(unknown)[:40]})
    return n, sorted(unknown)


def discover_pages(session, hub_page, pattern):
    """Troba les pagines per estat enllacades des d'una pagina index.

    Els EUA no tenen una sola taula amb tots els estats: cada cursa te el seu
    article. Seguim els enllacos en comptes de mantenir una llista a ma.
    """
    resp = wk._throttled_get(session, {
        "action": "parse", "page": hub_page, "prop": "links",
        "format": "json", "formatversion": "2"})
    payload = resp.json()
    if "error" in payload:
        return []
    rx = re.compile(pattern)
    found = []
    for link in payload["parse"].get("links", []):
        if link.get("ns") != 0 or not link.get("exists"):
            continue
        title = link["*"] if "*" in link else link.get("title", "")
        key = title.replace(" ", "_")
        m = rx.match(key)
        if m:
            found.append((key, m.group(1).replace("_", " ")))
    return sorted(set(found))


def run(conn, only=None):
    cfg = load_config()
    session = requests.Session()
    summary, unmapped = [], set()

    for election in cfg["elections"]:
        eid = election["id"]
        if only and eid not in only:
            continue
        country, scope = election["country"], election.get("scope", "national")

        n, unk = read_page(conn, session, eid, country, scope, election["page"])
        unmapped.update(unk)
        summary.append((eid, election["page"], n))

        for extra in election.get("regional_pages", []):
            region = extra.split("(")[-1].rstrip(")").replace("_", " ") if "(" in extra else None
            n2, unk2 = read_page(conn, session, eid, country, "region", extra,
                                 scope_code=region, scope_name=region)
            unmapped.update(unk2)
            summary.append((eid, extra, n2))

        disc = election.get("discover")
        if disc:
            for page_name, state in discover_pages(session, election["page"], disc["pattern"]):
                n3, unk3 = read_page(conn, session, eid, country, "state", page_name,
                                     scope_code=state, scope_name=state)
                unmapped.update(unk3)
                summary.append((eid, page_name, n3))

    return summary, sorted(unmapped)
