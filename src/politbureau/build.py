"""Calcula les dues capes del mapa a partir de les dades crues.

  capa "real"      -> election_result, tal com la va publicar el Ministeri
  capa "estimacio" -> projection, resultat real de cada territori desplacat
                      segons el que diuen les enquestes d'avui

Es recalcula tot de zero cada vegada: es barat i evita que quedin restes
d'una execucio anterior amb enquestes que despres s'han corregit.
"""
from __future__ import annotations

import datetime as dt

import yaml

from . import db, parties
from .ingest.runner import SOURCES
from .model import aggregate as agg
from .model import seats as seatlib


def _config():
    with SOURCES.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_polls(conn, election_id, scope_code=None):
    where = "p.election_id = ?"
    args = [election_id]
    if scope_code is None:
        where += " AND (p.scope_code IS NULL OR p.scope_code = '')"
    else:
        where += " AND p.scope_code = ?"
        args.append(scope_code)

    rows = conn.execute(
        f"""SELECT p.id, p.fieldwork_end, p.sample_size, r.party, r.share, r.seats_lo, r.seats_hi
            FROM poll p JOIN poll_result r ON r.poll_id = p.id
            WHERE {where}""", args).fetchall()

    polls: dict[int, dict] = {}
    for r in rows:
        entry = polls.setdefault(r["id"], {
            "fieldwork_end": r["fieldwork_end"],
            "sample_size": r["sample_size"],
            "results": {},
        })
        entry["results"][r["party"]] = (r["share"], r["seats_lo"], r["seats_hi"])
    return list(polls.values())


def store_aggregate(conn, election_id, scope_code, result):
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    conn.executemany(
        """INSERT OR REPLACE INTO aggregate
           (computed_at, election_id, scope_code, party, share, lo, hi, n_polls)
           VALUES (?,?,?,?,?,?,?,?)""",
        [(now, election_id, scope_code or "", party, v["share"], v["lo"], v["hi"], v["n_polls"])
         for party, v in result.items()])


def baseline_shares(conn, election, level):
    """{codi_territori: {partit: % sobre vot valid}} de l'ultima eleccio real."""
    rows = conn.execute(
        """SELECT code, party, votes, valid_votes FROM election_result
           WHERE election = ? AND level = ?""", (election, level)).fetchall()
    out: dict[str, dict[str, float]] = {}
    for r in rows:
        if not r["valid_votes"]:
            continue
        out.setdefault(r["code"], {})[r["party"]] = r["votes"] * 100.0 / r["valid_votes"]
    return out


def _region_lookup():
    """Funcio (nivell, codi) -> regio, per saber si un partit territorial hi juga."""
    from .geo import regions as georegions
    table = georegions.table()
    muni, prov = table["municipality"], table["province"]

    def region_of(level, code):
        if level == "region":
            return code
        if level == "province":
            return prov.get(code)
        return muni.get(code) or prov.get(code[:2])
    return region_of


def project(conn, election_id, baseline_election,
            levels=("municipality", "province", "region")):
    """Aplica el swing nacional sobre cada territori i desa el resultat."""
    national_now = {p: v["share"] for p, v in
                    agg.aggregate(load_polls(conn, election_id)).items()}
    if not national_now:
        return 0

    national = baseline_shares(conn, baseline_election, "national")
    national_before = next(iter(national.values()), {}) if national else {}
    if not national_before:
        return 0

    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    total = 0
    for level in levels:
        # Esborrar abans d'inserir, i no confiar en INSERT OR REPLACE. La clau
        # primaria inclou el partit, de manera que un partit que avui ja no surt
        # en aquell territori no el sobreescriuria ningu i es quedaria per sempre
        # a la taula, contaminant el mapa amb dades d'un calcul anterior.
        conn.execute("DELETE FROM projection WHERE election_id = ? AND level = ?",
                     (election_id, level))
        rows, report = [], {}
        region_of = _region_lookup()
        dropped = set()
        for code, before in baseline_shares(conn, baseline_election, level).items():
            projected = seatlib.proportional_swing(before, national_now, national_before, report)

            # Un partit nou sense base estatal rebia la seva quota nacional a
            # TOT arreu, i Alianca Catalana acabava sortint a Ceuta i Melilla.
            # Els partits amb ambit declarat nomes existeixen dins del seu.
            region = region_of(level, code)
            outside = [p for p in projected
                       if not parties.stands_in(p, "ES", region)]
            if outside:
                dropped.update(outside)
                for p in outside:
                    projected.pop(p, None)
                total_share = sum(projected.values())
                if total_share:
                    projected = {p: round(v * 100.0 / total_share, 2)
                                 for p, v in projected.items()}

            rows += [(now, election_id, level, code, party, share)
                     for party, share in projected.items() if share >= 0.05]
        if dropped:
            report.setdefault("fora del seu ambit", set()).update(dropped)
        conn.executemany(
            """INSERT INTO projection
               (computed_at, election_id, level, code, party, share)
               VALUES (?,?,?,?,?,?)""", rows)
        total += len(rows)
        if report:
            for kind, who in sorted(report.items()):
                print(f"        avis [{level}] {kind}: {', '.join(sorted(who))}")
    conn.commit()
    return total


def project_seats(conn, election_id, baseline_election):
    """Llei d'Hondt sobre la projeccio provincial: escons estimats per a avui.

    Es millor que agafar la mediana de les projeccions dels instituts perque el
    calcul es reproduible i es pot resseguir circumscripcio a circumscripcio.
    """
    magnitudes = {r["code"]: r["seats"] for r in conn.execute(
        "SELECT code, seats FROM constituency WHERE election = ? AND level = 'province'",
        (baseline_election,))}
    if not magnitudes:
        return 0

    shares: dict[str, dict[str, float]] = {}
    for r in conn.execute(
            """SELECT code, party, share FROM projection
               WHERE election_id = ? AND level = 'province'""", (election_id,)):
        shares.setdefault(r["code"], {})[r["party"]] = r["share"]

    totals, detail = seatlib.allocate(shares, magnitudes)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    rows = [(now, election_id, "chamber", "", party, n) for party, n in totals.items()]
    for code, per_party in detail.items():
        rows += [(now, election_id, "province", code, party, n)
                 for party, n in per_party.items()]

    conn.execute("DELETE FROM seat_projection WHERE election_id = ?", (election_id,))
    conn.executemany(
        """INSERT INTO seat_projection
           (computed_at, election_id, level, code, party, seats) VALUES (?,?,?,?,?,?)""", rows)
    conn.commit()
    return sum(totals.values())


def aggregate_all(conn):
    """Mitjana per a cada eleccio i cada ambit territorial que tingui enquestes."""
    conn.execute("DELETE FROM aggregate")
    done = []
    combos = conn.execute(
        """SELECT election_id, COALESCE(scope_code, '') AS sc, COUNT(*) n
           FROM poll GROUP BY election_id, sc""").fetchall()
    for row in combos:
        polls = load_polls(conn, row["election_id"], row["sc"] or None)
        result = agg.aggregate(polls)
        if result:
            store_aggregate(conn, row["election_id"], row["sc"], result)
            done.append((row["election_id"], row["sc"] or "(estatal)", len(polls), len(result)))
    conn.commit()
    return done


def load_real_results(conn):
    """Baixa i desa els resultats reals que serveixen de base al mapa."""
    from .ingest import infoelectoral as ie
    resolver = lambda s: parties.resolve(s, "ES")[0]      # noqa: E731
    out = []
    for process in ("congreso-2023", "municipales-2023"):
        try:
            n_rows, n_munis = ie.store(conn, process, resolver)
            out.append((process, n_munis, n_rows))
        except Exception as exc:                       # noqa: BLE001
            db.log_ingest(conn, process, None, "error", 0, f"{type(exc).__name__}: {exc}")
            out.append((process, 0, f"ERROR {type(exc).__name__}: {exc}"))
    try:
        n_const, n_seats = ie.store_constituencies(conn, "congreso-2023", resolver)
        out.append(("congreso-2023 (circumscripcions)", n_const, f"{n_seats} escons"))
    except Exception as exc:                           # noqa: BLE001
        db.log_ingest(conn, "congreso-2023", None, "error", 0, f"{type(exc).__name__}: {exc}")
        out.append(("congreso-2023 (circumscripcions)", 0, f"ERROR {exc}"))

    from .ingest import deputies as dep

    try:
        n_cand, n_elected = dep.store(conn, "congreso-2023", resolver)
        out.append(("congreso-2023 (diputats)", n_elected, f"{n_cand} candidats titulars"))
    except Exception as exc:                           # noqa: BLE001
        db.log_ingest(conn, "congreso-2023", None, "error", 0, f"{type(exc).__name__}: {exc}")
        out.append(("congreso-2023 (diputats)", 0, f"ERROR {type(exc).__name__}: {exc}"))


    return out


def run(conn):
    print("1/3  Resultats electorals reals (Ministeri de l'Interior)")
    for process, n_munis, n_rows in load_real_results(conn):
        print(f"     {process:<20} {n_munis:>6} municipis  {n_rows} files")

    print("\n2/3  Mitjanes ponderades d'enquestes")
    for eid, scope, n_polls, n_parties in aggregate_all(conn):
        print(f"     {eid:<18} {scope:<22} {n_polls:>5} enquestes -> {n_parties} partits")

    print("\n3/3  Projeccio territorial")
    cfg = _config()
    for election in cfg["elections"]:
        eid = election["id"]
        if election["country"] == "ES":
            base = (election.get("baseline") or {}).get("election")
            if not base:
                continue
            n = project(conn, eid, base, levels=("municipality", "province", "region"))
            if n:
                print(f"     {eid:<18} {n:>7} files (swing sobre el resultat real)")

    print("\n4/4  Repartiment d'escons")
    for election in cfg["elections"]:
        chamber = election.get("chamber")
        if not chamber:
            continue
        eid = election["id"]
        n = project_seats(conn, eid, (election.get("baseline") or {}).get("election"))
        if n:
            print(f"     {eid:<18} {n:>4}/{chamber['seats']} escons (llei d'Hondt per circumscripcio)")
    print("\nFet.")
