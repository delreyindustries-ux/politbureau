"""Orquestra la ingesta: llegeix config/sources.yaml i omple la base de dades."""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup

from .. import db, veda
from . import wikipedia as wk

ROOT = Path(__file__).resolve().parents[3]
SOURCES = ROOT / "config" / "sources.yaml"


# Resta d'Europa (group: europa): cada Wikipedia titula a la seva manera la
# seccio d'enquestes, i moltes hi pengen taules per regio, d'escons o
# d'escenaris que no son intencio de vot estatal.
EUROPA_SECTIONS = ("opinion polls", "opinion poll", "poll results", "polling results",
                   "polls", "vote share", "party standings")
EUROPA_DENY = ("by state", "by region", "regional", "sub-national", "subnational",
               "constituenc", "by county", "by district", "seat", "chancellor",
               "coalition polls", "age group", "pollster bias", "acceptability",
               "other polls", "cdu and csu", "england", "scotland", "wales", "london",
               "hypothetical", "second round", "run-off", "runoff",
               # Austràlia i Canadà: enquestes d'un sol districte i projeccions d'escons.
               "electorate", "projection", "riding", "by province")


WORLD = ("europa", "mon")      # grups d'eleccions estrangeres (03/11/2026)
# Regions: el que no es intencio de vot de la regio. Escocia porta, a mes de les
# enquestes escoceses, les submostres escoceses d'enquestes de tot el Regne Unit
# (centenars de persones) i projeccions MRP: fora.
REGION_DENY = ("hypothetical", "seat", "projection", "second round", "run-off", "runoff",
               "scenario", "leadership", "approval", "preferred", "sub-sample", "subsample",
               "mrp", "constituenc", "electorate", "chancellor")


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
            "INSERT OR REPLACE INTO poll_result (poll_id, party, share, seats_lo, seats_hi, label) "
            "VALUES (?,?,?,?,?,?)",
            [(poll_id, code, share, lo, hi, poll.labels.get(code))
             for code, (share, lo, hi) in poll.results.items()],
        )
        inserted += 1
    conn.commit()
    return inserted


def read_page(conn, session, election_id, country, scope, page_name,
              scope_code=None, scope_name=None, sections=(), deny=(), match=None):
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
    # Cada Wikipedia titula les seccions a la seva manera ("Party standings",
    # "Poll results"...): l'eleccio en pot afegir de permeses i de prohibides.
    tables = wk.poll_tables(soup, wk.DEFAULT_SECTIONS + tuple(sections),
                            wk.DENIED_SECTIONS + tuple(deny))
    if match:
        # Una regio dins de la pagina de l'eleccio ("wales > sub-national poll
        # results"): mana el nom de la regio, no la llista de seccions permeses.
        tables = [(t, s, y) for t, s, y in wk.poll_tables(soup, (), wk.DENIED_SECTIONS + tuple(deny))
                  if match in s]
    for i, (table, _section, year) in enumerate(tables):
        # La mateixa regla que per a una pagina caiguda, aplicada a cada taula:
        # una taula mal formada fa perdre aquella taula, no la pagina ni la resta
        # de la descarrega. El 02/10/2026 un `rowspan="2""` d'un estat americà
        # va fer petar l'ingest sencer, governadors inclosos.
        try:
            got, unk = wk.parse_table(table, country, year or this_year)
        except Exception as exc:                  # noqa: BLE001
            msg = f"taula {i}: {type(exc).__name__}: {exc}"
            db.log_ingest(conn, election_id, page["url"], "error", 0, msg)
            print(f"   AVIS {election_id} {page_name}: {msg}", flush=True)
            continue
        polls += got
        unknown.update(unk)
    n = store(conn, election_id, country, scope, scope_code, scope_name, page, polls)
    colors = {}
    for poll in polls:
        colors.update(poll.colors)
    if colors:
        conn.execute("""CREATE TABLE IF NOT EXISTS party_style (election_id TEXT NOT NULL,
            party TEXT NOT NULL, color TEXT NOT NULL, PRIMARY KEY (election_id, party))""")
        conn.executemany("INSERT OR REPLACE INTO party_style VALUES (?,?,?)",
                         [(election_id, code, c) for code, c in colors.items()])
        conn.commit()
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

        # Veda electoral (LOREG 69.7): ni una enquesta nova fins que tanquin els
        # col.legis. La web es queda amb les que ja tenia.
        if veda.active(election):
            db.log_ingest(conn, eid, election["page"], "skipped", 0,
                          "veda electoral (LOREG art. 69.7)")
            summary.append((eid, "VEDA ELECTORAL: no es llegeix res", 0))
            continue

        if election.get("national", True):
            n, unk = read_page(conn, session, eid, country, scope, election["page"],
                               sections=tuple(election.get("sections") or ())
                               + (EUROPA_SECTIONS if election.get("group") in WORLD else ()),
                               deny=tuple(election.get("deny_sections") or ())
                               + (EUROPA_DENY if election.get("group") in WORLD else ()))
            unmapped.update(unk)
            summary.append((eid, election["page"], n))

        # Regions de les eleccions estrangeres (`regions:` a sources.yaml).
        for reg in (cfg.get("regions") or {}).get(eid, []):
            n4, unk4 = read_page(conn, session, eid, country, "region",
                                 reg.get("page") or election["page"],
                                 scope_code=reg["key"], scope_name=reg["name_ca"],
                                 sections=EUROPA_SECTIONS, deny=REGION_DENY,
                                 match=reg.get("match"))
            unmapped.update(unk4)
            summary.append((eid, f"  {reg['key']} {reg.get('page') or reg.get('match')}", n4))

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
