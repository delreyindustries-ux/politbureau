"""Esquema i accés a la base de dades SQLite."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "politbureau.db"

SCHEMA = """
PRAGMA journal_mode = WAL;

-- Una enquesta publicada. La clau única evita duplicats entre re-ingestes.
CREATE TABLE IF NOT EXISTS poll (
    id              INTEGER PRIMARY KEY,
    election_id     TEXT    NOT NULL,   -- es-general, fr-pres-2027, ...
    country         TEXT    NOT NULL,   -- ES / FR / IT / US
    scope           TEXT    NOT NULL,   -- national / region / state / municipality
    scope_code      TEXT,               -- NULL si nacional; si no, codi INE / abrev. estat
    scope_name      TEXT,
    pollster        TEXT,
    client          TEXT,
    fieldwork_start TEXT,               -- ISO-8601
    fieldwork_end   TEXT,
    sample_size     INTEGER,
    turnout         REAL,
    source_url      TEXT    NOT NULL,
    source_title    TEXT,
    fetched_at      TEXT    NOT NULL,
    UNIQUE (election_id, scope_code, pollster, fieldwork_end, sample_size)
);

-- Resultat d'un partit dins d'una enquesta.
CREATE TABLE IF NOT EXISTS poll_result (
    poll_id   INTEGER NOT NULL REFERENCES poll(id) ON DELETE CASCADE,
    party     TEXT    NOT NULL,   -- codi canònic de parties.yaml
    share     REAL,               -- percentatge de vot
    seats_lo  INTEGER,
    seats_hi  INTEGER,
    PRIMARY KEY (poll_id, party)
);

-- Resultats electorals REALS. Aquesta és la capa "dada verificada" del mapa
-- i alhora la base sobre la qual s'aplica el swing de les enquestes.
CREATE TABLE IF NOT EXISTS election_result (
    country     TEXT NOT NULL,
    election    TEXT NOT NULL,   -- congreso-2023, municipales-2023, us-pres-2024
    date        TEXT NOT NULL,
    level       TEXT NOT NULL,   -- municipality / province / region / state / national
    code        TEXT NOT NULL,   -- codi INE 5 dígits, FIPS, ...
    name        TEXT,
    party       TEXT NOT NULL,
    votes       INTEGER,
    valid_votes INTEGER,
    census      INTEGER,
    source      TEXT NOT NULL,
    PRIMARY KEY (country, election, level, code, party)
);

-- Mitjana ponderada calculada. Es recalcula sencera a cada `build`.
CREATE TABLE IF NOT EXISTS aggregate (
    computed_at TEXT NOT NULL,
    election_id TEXT NOT NULL,
    scope_code  TEXT NOT NULL DEFAULT '',
    party       TEXT NOT NULL,
    share       REAL,
    lo          REAL,
    hi          REAL,
    n_polls     INTEGER,
    PRIMARY KEY (election_id, scope_code, party)
);

-- Projecció per territori: swing de les enquestes aplicat sobre el baseline real.
CREATE TABLE IF NOT EXISTS projection (
    computed_at TEXT NOT NULL,
    election_id TEXT NOT NULL,
    level       TEXT NOT NULL,
    code        TEXT NOT NULL,
    party       TEXT NOT NULL,
    share       REAL,
    PRIMARY KEY (election_id, level, code, party)
);

-- Magnitud de cada circumscripcio (quants escons reparteix) i escons reals
-- que hi va obtenir cada partit. Surt del fitxer 08 d'infoelectoral.
CREATE TABLE IF NOT EXISTS constituency (
    election TEXT NOT NULL,
    level    TEXT NOT NULL,   -- province (Espanya) / state (EUA)
    code     TEXT NOT NULL,
    seats    INTEGER NOT NULL,
    PRIMARY KEY (election, level, code)
);

CREATE TABLE IF NOT EXISTS constituency_result (
    election TEXT NOT NULL,
    level    TEXT NOT NULL,
    code     TEXT NOT NULL,
    party    TEXT NOT NULL,
    votes    INTEGER,
    seats    INTEGER,
    PRIMARY KEY (election, level, code, party)
);

-- Escons projectats amb la llei d'Hondt sobre l'estimacio d'avui.
CREATE TABLE IF NOT EXISTS seat_projection (
    computed_at TEXT NOT NULL,
    election_id TEXT NOT NULL,
    level       TEXT NOT NULL,
    code        TEXT NOT NULL,   -- '' = total de la cambra
    party       TEXT NOT NULL,
    seats       INTEGER,
    PRIMARY KEY (election_id, level, code, party)
);

-- Candidats de cada llista provincial, amb marca dels que van sortir electes.
-- Les llistes espanyoles son tancades: l'ordre decideix qui entra.
CREATE TABLE IF NOT EXISTS deputy (
    election TEXT    NOT NULL,
    province TEXT    NOT NULL,
    party    TEXT    NOT NULL,
    position INTEGER NOT NULL,
    name     TEXT    NOT NULL,
    sex      TEXT,
    elected  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (election, province, party, position)
);

-- Registre d'ingesta: què s'ha llegit, quan, i què ha fallat.
CREATE TABLE IF NOT EXISTS ingest_log (
    ts        TEXT NOT NULL,
    source    TEXT NOT NULL,
    url       TEXT,
    status    TEXT NOT NULL,   -- ok / skipped / error
    n_polls   INTEGER DEFAULT 0,
    detail    TEXT
);

CREATE INDEX IF NOT EXISTS idx_poll_election ON poll(election_id, fieldwork_end);
CREATE INDEX IF NOT EXISTS idx_result_lookup ON election_result(country, election, level);
CREATE INDEX IF NOT EXISTS idx_projection    ON projection(election_id, level);
"""


def connect(path: Path | str = DB_PATH) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def log_ingest(conn, source, url, status, n_polls=0, detail=None):
    from datetime import datetime, timezone
    conn.execute(
        "INSERT INTO ingest_log (ts, source, url, status, n_polls, detail) VALUES (?,?,?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(timespec="seconds"), source, url,
         status, n_polls, json.dumps(detail) if isinstance(detail, (dict, list)) else detail),
    )
    conn.commit()
