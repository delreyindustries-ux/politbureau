"""Calcula les dues capes del mapa a partir de les dades crues.

  capa "real"      -> election_result, tal com la va publicar el Ministeri
  capa "estimacio" -> projection, resultat real de cada territori desplacat
                      segons el que diuen les enquestes d'avui

Es recalcula tot de zero cada vegada: es barat i evita que quedin restes
d'una execucio anterior amb enquestes que despres s'han corregit.
"""
from __future__ import annotations

import datetime as dt
import json

import yaml

from . import db, parties, veda
from .ingest.runner import SOURCES
from .model import aggregate as agg
from .model import seats as seatlib


def _config():
    with SOURCES.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def pollster_weights(election_id) -> dict:
    """{institut: multiplicador} d'una eleccio (`pollster_weights` a sources.yaml).
    El nom ha de coincidir exactament amb el de la taula de Wikipedia: "CIS" no
    inclou les reestimacions d'altres cases fetes amb les dades del CIS, que
    surten com a "CIS (Target Point)", "CIS (Ateneo del Dato)"..."""
    for e in _config()["elections"]:
        if e["id"] == election_id:
            return {str(k): float(v) for k, v in (e.get("pollster_weights") or {}).items()}
    return {}


def load_polls(conn, election_id, scope_code=None):
    where = "p.election_id = ?"
    args = [election_id]
    if scope_code is None:
        where += " AND (p.scope_code IS NULL OR p.scope_code = '')"
    else:
        where += " AND p.scope_code = ?"
        args.append(scope_code)

    rows = conn.execute(
        f"""SELECT p.id, p.pollster, p.fieldwork_end, p.sample_size, r.party, r.share, r.seats_lo, r.seats_hi
            FROM poll p JOIN poll_result r ON r.poll_id = p.id
            WHERE {where}""", args).fetchall()

    # Partits que a aquesta eleccio van dins d'un altre (sources.yaml -> merge):
    # es sumen DINS de cada enquesta, abans de fer la mitjana. Sumar-los despres,
    # amb mitjanes fetes per separat, comptaria malament les enquestes que nomes
    # en pregunten un.
    merge = next((e.get("merge") or {} for e in _config()["elections"]
                  if e["id"] == election_id), {})
    weights = pollster_weights(election_id)
    polls: dict[int, dict] = {}
    for r in rows:
        entry = polls.setdefault(r["id"], {
            "pollster": (r["pollster"] or "").strip(),
            "fieldwork_end": r["fieldwork_end"],
            "sample_size": r["sample_size"],
            "weight": weights.get((r["pollster"] or "").strip(), 1.0),
            "results": {},
        })
        code = merge.get(r["party"], r["party"])
        share, lo, hi = r["share"], r["seats_lo"], r["seats_hi"]
        if code in entry["results"]:
            s0, lo0, hi0 = entry["results"][code]
            share = (s0 or 0) + (share or 0)
            lo = None if lo0 is None and lo is None else (lo0 or 0) + (lo or 0)
            hi = None if hi0 is None and hi is None else (hi0 or 0) + (hi or 0)
        entry["results"][code] = (share, lo, hi)
    return latest_per_pollster(polls)


def latest_per_pollster(polls: dict) -> list:
    """De cada casa enquestadora, NOMES la seva enquesta mes recent.

    Decisio de l'Alfonso (19/10/2026): una enquesta nova d'una casa substitueix
    l'anterior, no s'hi afegeix. Si no, les cases que publiquen cada setmana
    (EM-Analytics en porta 13 en 90 dies) pesaven molt mes que les que ho fan
    un cop al mes. La casa es el nom tal com surt a Wikipedia: "CIS (Opina
    360)" es una reestimacio d'una altra casa i compta a part del CIS.
    "Mes recent" = data final del treball de camp; a igualtat, la que s'ha
    llegit despres (id mes alt). Sense nom de casa, cada enquesta va a part."""
    latest: dict = {}
    for pid, entry in polls.items():
        house = entry["pollster"].lower() or f"#{pid}"
        rank = (entry["fieldwork_end"] or "", pid)
        if house not in latest or rank > latest[house][0]:
            latest[house] = (rank, entry)
    return [entry for _, entry in latest.values()]


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


def election_scopes(election_id) -> dict:
    """{partit: {regions on es presenta}} propis d'una eleccio, a partir de
    `scope_exclude` a sources.yaml (Podemos no es presenta a Catalunya a les
    generals del 2026, pero si a les altres eleccions)."""
    rules = next((e.get("scope_exclude") or {} for e in _config()["elections"]
                  if e["id"] == election_id), {}) if election_id else {}
    if not rules:
        return {}
    from .geo import regions as georegions
    every = {str(r) for r in georegions.table()["province"].values() if r}
    return {p: every - {str(r) for r in out} for p, out in rules.items()}


def scope_concentration(conn, baseline_election, national_before, national_now,
                        country="ES", extra=None):
    """Com projectar els partits amb ambit territorial declarat a `_scope`.

    El problema: un partit que nomes es presenta a Catalunya i que les enquestes
    situen al 0,9% ESTATAL no te el 0,9% a Catalunya. Tots aquests vots hi son a
    dins, i Catalunya son 3,5 dels 24,3 milions de vots valids de l'Estat: el
    seu percentatge catala es 0,9 x (24,3 / 3,5) = 6,3%. Sense aixo, el swing
    els deixava congelats al resultat anterior i sortien amb ZERO escons mentre
    totes les cases d'enquestes els en donaven entre 1 i 5.

    Retorna {partit: {"factor": f}} o {partit: {"share": s}}:

    * `factor` -- el partit ja tenia vots al seu ambit l'ultima vegada. Es
      multiplica el seu resultat LOCAL per aquest factor, que es el swing
      calculat dins de l'ambit en comptes de a escala estatal. Aixo conserva la
      geografia real: Teruel Existe te els vots a Terol i no repartits per
      l'Aragó, i repartir-li la quota uniformement l'hi destrossaria.
    * `share`  -- el partit no existia (Alianca Catalana no es va presentar al
      Congres el 2023). No hi ha geografia que conservar, aixi que se li dona el
      mateix percentatge a tot l'ambit.

    Nomes s'aplica als partits sense base estatal mesurable (`MIN_BASE`); els
    que en tenen ja es mouen be amb el swing normal.
    """
    valid = dict(conn.execute(
        "SELECT code, MAX(valid_votes) FROM election_result "
        "WHERE election = ? AND level = 'region' AND valid_votes IS NOT NULL "
        "GROUP BY code", (baseline_election,)).fetchall())
    nation = conn.execute(
        "SELECT MAX(valid_votes) FROM election_result "
        "WHERE election = ? AND level = 'national'", (baseline_election,)).fetchone()[0]
    if not nation or not valid:
        return {}

    out = {}
    scopes = dict(parties.scopes().get(country) or {})
    scopes.update(extra or {})
    for party, regions in scopes.items():
        now = national_now.get(party)
        base = national_before.get(party)
        if now is None or (base and base >= seatlib.MIN_BASE):
            continue
        inside = sum(valid.get(str(r), 0) for r in regions)
        if not inside:
            continue
        target = now * nation / inside          # % que li toca dins de l'ambit
        got = conn.execute(
            "SELECT SUM(votes) FROM election_result WHERE election = ? "
            "AND level = 'region' AND party = ? AND code IN "
            "(%s)" % ",".join("?" * len(regions)),
            (baseline_election, party, *sorted(regions))).fetchone()[0]
        before_in_scope = 100.0 * (got or 0) / inside
        factor = target / before_in_scope if before_in_scope > 0 else None
        if factor is not None and factor <= seatlib.MAX_FACTOR:
            out[party] = {"factor": factor}
        else:
            # O no existia, o ha crescut tant que la seva geografia anterior ja
            # no diu res. Adelante Andalucia nomes tenia vots a Cadis el 2023 i
            # les enquestes li donen tres escons, que exigeixen vots a tota
            # Andalusia: conservar-li aquella geografia li donaria el 38% de
            # Cadis, que es exactament el disbarat que aquest modul evita.
            out[party] = {"share": target}
    return out


def regional_merges(election_id):
    """Regles `regional_merge` d'una eleccio (sources.yaml)."""
    for e in _config()["elections"]:
        if e["id"] == election_id:
            return e.get("regional_merge") or []
    return []


def _election_rules(election_id, key):
    for e in _config()["elections"]:
        if e["id"] == election_id:
            return e.get(key) or []
    return []


_FILLS: dict = {}


def fill_table(conn, baseline_election, rule) -> dict:
    """{(nivell, codi): % que s'afegeix al partit} per a una regla `baseline_fill`.

    Per a cada municipi de les provincies de la regla: el % del partit a
    l'eleccio `from`, multiplicat pel que va canviar entre `from` i la de base a
    la provincia `scale_from`. Provincia i comunitat surten de sumar els vots
    imputats als municipis sobre els vots a candidatures de la base."""
    key = (baseline_election, rule["party"], rule["from"], tuple(rule["provinces"]),
           rule["scale_from"])
    if key in _FILLS:
        return _FILLS[key]
    from .ingest import infoelectoral as ie
    tipo, year, month = ie.PROCESSES[rule["from"]]
    zf = ie.download(rule["from"])
    labels = ie.candidacies(zf, tipo, year, month)
    codes = {c for c, label in labels.items()
             if parties.resolve(label, "ES")[0] == rule["party"]}
    votes = ie.votes(zf, tipo, year, month)
    munis = ie.municipalities(zf, tipo, year, month)

    def then(m):
        return sum(n for c, n in votes.get(m, {}).items() if c in codes)

    ref = rule["scale_from"]
    ref_then = (sum(then(m) for m in munis if m[:2] == ref) * 100.0
                / max(1, sum(i["valid"] for m, i in munis.items() if m[:2] == ref)))
    ref_now = baseline_shares(conn, baseline_election, "province").get(ref, {}).get(rule["party"], 0)
    factor = ref_now / ref_then if ref_then else 1.0

    valid = {(r[0], r[1]): r[2] for r in conn.execute(
        """SELECT level, code, MAX(valid_votes) FROM election_result
           WHERE election = ? GROUP BY level, code""", (baseline_election,))}
    region_of = _region_lookup()
    out, added = {}, {}
    for m, info in munis.items():
        if m[:2] not in rule["provinces"] or not info["valid"]:
            continue
        share = then(m) * 100.0 / info["valid"] * factor
        out[("municipality", m)] = share
        w = valid.get(("municipality", m), 0) * share / 100.0
        for k in (("province", m[:2]), ("region", region_of("province", m[:2]))):
            added[k] = added.get(k, 0) + w
    for k, w in added.items():
        if valid.get(k):
            out[k] = w * 100.0 / valid[k]
    _FILLS[key] = out
    return out


def baseline_rules(conn, baseline_election, election_id):
    """(fills, splits) d'una eleccio, llegits UNA vegada: es fan servir per a
    cada territori i cada mesa, i rellegir sources.yaml cada cop son minuts."""
    fills = [(rule, fill_table(conn, baseline_election, rule))
             for rule in _election_rules(election_id, "baseline_fill")]
    return fills, _election_rules(election_id, "baseline_split")


def adjust_baseline(rules, level, code, region, before):
    """Aplica `baseline_fill` i `baseline_split` (sources.yaml) al resultat de
    base d'un territori. Les meses (codi «MMMMM-DD-SSS-L») fan servir el valor
    del seu municipi."""
    fills, splits = rules
    out = dict(before)
    for rule, table in fills:
        key = ("municipality", code[:5]) if "-" in code else (level, code)
        add = table.get(key)
        if add:
            out = {p: v * (1 - add / 100.0) for p, v in out.items()}
            out[rule["party"]] = out.get(rule["party"], 0) + add
    for rule in splits:
        if region in rule["regions"] and rule["party"] in out:
            moved = out[rule["party"]] * rule["share"]
            out[rule["party"]] -= moved
            out[rule["to"]] = out.get(rule["to"], 0) + moved
    return out


def apply_regional_merge(projected, region, rules, country="ES", report=None):
    """Dins de les regions d'una regla, ajunta a `into` tots els partits a
    l'esquerra de `left_of`, o be els de la llista `parties` (coalicions que no
    son "tota l'esquerra", com UPN amb el PP a Navarra). Els percentatges ja
    sumen 100 i se sumen, aixi que no cal renormalitzar."""
    for rule in rules:
        # regions: "*" = a tot l'Estat (Recortes Cero dins del Frente Amplio).
        if rule["regions"] != "*" and region not in rule["regions"]:
            continue
        into = rule["into"]
        if rule.get("parties"):
            joined = [p for p in projected if p != into and p in rule["parties"]]
        else:
            limit = parties.position(rule["left_of"], country)
            joined = [p for p in projected
                      if p != into and parties.position(p, country) < limit]
        if not joined:
            continue
        projected[into] = round(projected.get(into, 0) + sum(projected.pop(p) for p in joined), 2)
        if report is not None:
            report.setdefault(f"llista unica ({into})", set()).update(joined)
    return projected


def project_shares(conn, baseline_election, national_now, level, country="ES",
                   report=None, election_id=None, baseline=None):
    """{codi_territori: {partit: %}}: el vot estatal `national_now` portat a cada
    territori d'un nivell. Es el cor de `project`, separat perque l'enquesta
    propia (survey/estimate.py) passi exactament pel mateix model que la mitjana
    d'enquestes i no per una copia que es pugui desajustar.

    `baseline` substitueix els resultats de base del nivell per uns altres
    ({codi: {partit: %}}): les meses electorals (mesas.py) passen per aqui amb
    codis que comencen pel del municipi, i la comunitat surt de la provincia."""
    national = baseline_shares(conn, baseline_election, "national")
    national_before = next(iter(national.values()), {}) if national else {}
    if not national_before or not national_now:
        return {}
    if report is None:
        report = {}
    extra_scopes = election_scopes(election_id)
    concentrate = scope_concentration(conn, baseline_election, national_before,
                                      national_now, country, extra_scopes)
    # La taula de pertinenca a comunitat es nomes d'Espanya.
    region_of = (_region_lookup() if country == "ES"
                 else (lambda level, code: None))
    merges = regional_merges(election_id) if election_id else []
    gone = not_standing(election_id) if election_id else set()
    out, dropped = {}, set()
    if baseline is None:
        baseline = baseline_shares(conn, baseline_election, level)
    adjust = (baseline_rules(conn, baseline_election, election_id)
              if election_id and country == "ES" else ([], []))
    for code, before in baseline.items():
        if adjust != ([], []):
            before = adjust_baseline(adjust, level, code, region_of(level, code), before)
        projected = seatlib.proportional_swing(
            before, national_now, national_before, report, concentrate,
            parties.families().get(country))

        # Un partit nou sense base estatal rebia la seva quota nacional a
        # TOT arreu, i Alianca Catalana acabava sortint a Ceuta i Melilla.
        # Els partits amb ambit declarat nomes existeixen dins del seu.
        region = region_of(level, code)
        # Tambe els que no es presenten a aquesta eleccio (`not_standing`): sense
        # enquesta estatal, el swing els deixaria congelats al resultat de base
        # (la CUP al 2023, quan el 2026 no es presenta).
        outside = [p for p in projected
                   if not parties.stands_in(p, country, region) or p in gone
                   or (p in extra_scopes and region not in extra_scopes[p])]
        if outside:
            dropped.update(outside)
            for p in outside:
                projected.pop(p, None)
            total_share = sum(projected.values())
            if total_share:
                projected = {p: round(v * 100.0 / total_share, 2)
                             for p, v in projected.items()}
        if merges:
            projected = apply_regional_merge(projected, region, merges, country, report)
        out[code] = projected
    if dropped:
        report.setdefault("fora del seu ambit", set()).update(dropped)
    return out


def current_national(conn, election_id) -> dict:
    """{partit: %} estatal d'avui segons la mitjana d'enquestes."""
    return {p: v["share"] for p, v in
            drop_not_standing(election_id,
                              agg.aggregate(load_polls(conn, election_id))).items()}


def project(conn, election_id, baseline_election,
            levels=("municipality", "province", "region"), country="ES"):
    """Aplica el swing nacional sobre cada territori i desa el resultat.

    `country` no es decoratiu: decideix quines regles d'ambit de partit
    s'apliquen. Amb "ES" escrit a ma, una eleccio italiana feia servir les
    regles d'ambit espanyoles.
    """
    national_now = current_national(conn, election_id)
    if not national_now:
        return 0
    if not baseline_shares(conn, baseline_election, "national"):
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
        report = {}
        shares = project_shares(conn, baseline_election, national_now, level,
                                country, report, election_id=election_id)
        rows = [(now, election_id, level, code, party, share)
                for code, projected in shares.items()
                for party, share in projected.items() if share >= 0.05]
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


def magnitudes_for(conn, election_id, baseline_election):
    """Diputats de cada circumscripcio per a `election_id`: els de l'eleccio de
    base, corregits amb `magnitudes` de sources.yaml quan el decret de
    convocatoria en canvia algun (el 2026, Madrid 38 i Cadis 8)."""
    mags = {r["code"]: r["seats"] for r in conn.execute(
        "SELECT code, seats FROM constituency WHERE election = ? AND level = 'province'",
        (baseline_election,))}
    for e in _config()["elections"]:
        if e["id"] == election_id:
            mags.update({str(k): int(v) for k, v in (e.get("magnitudes") or {}).items()})
    return mags


def project_seats(conn, election_id, baseline_election):
    """Llei d'Hondt sobre la projeccio provincial: escons estimats per a avui.

    Es millor que agafar la mediana de les projeccions dels instituts perque el
    calcul es reproduible i es pot resseguir circumscripcio a circumscripcio.
    """
    magnitudes = magnitudes_for(conn, election_id, baseline_election)
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


def project_states(conn, election_id):
    """Els EUA no necessiten cap swing: les enquestes ja son per estat.

    L'unica feina es lligar el nom de l'estat ("Georgia") amb el codi FIPS que
    fa servir la geometria ("13"), que es el que el mapa sap dibuixar.

    NOMES es pinten els estats amb enquestes. No hi ha resultat de base del
    qual partir, aixi que un estat sense enquestes queda en blanc: inventar-li
    un color seria presentar com a dada el que no ho es.
    """
    from .geo import fetch as geo
    fips = {(name or "").lower(): code for code, name in geo.names("US", "state").items()}
    if not fips:
        return 0

    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    rows = []
    states = conn.execute(
        """SELECT DISTINCT scope_code FROM poll
           WHERE election_id = ? AND scope = 'state' AND scope_code IS NOT NULL""",
        (election_id,)).fetchall()
    for row in states:
        name = row["scope_code"]
        code = fips.get((name or "").lower())
        if not code:
            continue
        result = drop_not_standing(election_id, agg.aggregate(load_polls(conn, election_id, name)))
        # Nomes DEM/REP/IND: qualsevol altra cosa es un candidat que no hem
        # sabut classificar, i pintar el mapa amb aixo enganyaria.
        shares = {p: v["share"] for p, v in result.items() if p in ("DEM", "REP", "IND")}
        if not shares:
            continue
        for party, share in agg.normalise(shares).items():
            rows.append((now, election_id, "state", code, party, round(share, 2)))
    # Esborrar abans d'inserir (llico 9): l'original feia INSERT OR REPLACE, i un
    # estat que deixa de tenir enquestes vigents s'hauria quedat pintat.
    conn.execute("DELETE FROM projection WHERE election_id = ? AND level = 'state'",
                 (election_id,))
    conn.executemany(
        """INSERT INTO projection
           (computed_at, election_id, level, code, party, share) VALUES (?,?,?,?,?,?)""", rows)
    conn.commit()
    return len(rows)


def project_seats_proportional(conn, election_id, chamber_seats, threshold=0.03):
    """Repartiment purament proporcional d'una cambra a escala estatal.

    S'aplica alla on no tenim ni circumscripcions ni projeccions publicades
    (Italia). NO reprodueix la llei electoral real, i per aixo el grafic ho ha
    de dir. Serveix per veure l'ordre de magnitud, no per encertar l'escon.
    """
    result = drop_not_standing(election_id, agg.aggregate(load_polls(conn, election_id)))
    shares = {p: v["share"] for p, v in result.items() if not p.startswith("?")}
    if not shares:
        return 0
    got = seatlib.dhondt(shares, chamber_seats, threshold)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    conn.execute("DELETE FROM seat_projection WHERE election_id = ?", (election_id,))
    conn.executemany(
        """INSERT INTO seat_projection
           (computed_at, election_id, level, code, party, seats) VALUES (?,?,?,?,?,?)""",
        [(now, election_id, "chamber", "", p, n) for p, n in got.items() if n])
    conn.commit()
    return sum(got.values())


def project_seats_states(conn, election_id):
    """Cada estat dels EUA elegeix un senador: el mes votat s'emporta l'escon."""
    rows_in = {}
    for r in conn.execute(
            "SELECT code, party, share FROM projection WHERE election_id = ? AND level = 'state'",
            (election_id,)):
        rows_in.setdefault(r["code"], {})[r["party"]] = r["share"]
    if not rows_in:
        return 0
    totals: dict[str, int] = {}
    rows = []
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    for code, shares in rows_in.items():
        party, _ = seatlib.winner(shares)
        if not party:
            continue
        totals[party] = totals.get(party, 0) + 1
        rows.append((now, election_id, "state", code, party, 1))
    rows += [(now, election_id, "chamber", "", p, n) for p, n in totals.items()]
    conn.execute("DELETE FROM seat_projection WHERE election_id = ?", (election_id,))
    conn.executemany(
        """INSERT INTO seat_projection
           (computed_at, election_id, level, code, party, seats) VALUES (?,?,?,?,?,?)""", rows)
    conn.commit()
    return sum(totals.values())


def not_standing(election_id) -> set:
    """Partits que surten a les enquestes pero NO es presenten a aquesta eleccio.

    Es declaren a `sources.yaml` per eleccio (`not_standing`), no al cataleg de
    partits: Alianca Catalana no es presenta a les generals pero si a les
    catalanes i a les municipals.
    """
    for e in _config()["elections"]:
        if e["id"] == election_id:
            return set(e.get("not_standing") or [])
    return set()


def drop_not_standing(election_id, shares: dict) -> dict:
    """Treu de la mitjana els partits que no es presenten.

    NO es reparteix el seu pes a la mitjana estatal: inflar tots els altres un
    1% seria una hipotesi presentada com a enquesta. Qui la reparteix es la
    projeccio, que dins de cada territori torna a sumar 100.
    """
    gone = not_standing(election_id)
    return {p: v for p, v in shares.items() if p not in gone} if gone else shares


def aggregate_all(conn):
    """Mitjana per a cada eleccio i cada ambit territorial que tingui enquestes."""
    conn.execute("DELETE FROM aggregate")
    done = []
    combos = conn.execute(
        """SELECT election_id, COALESCE(scope_code, '') AS sc, COUNT(*) n
           FROM poll GROUP BY election_id, sc""").fetchall()
    elections = {e["id"]: e for e in _config()["elections"]}
    for row in combos:
        polls = load_polls(conn, row["election_id"], row["sc"] or None)
        # Dia de la votacio: abans de les 20 h cap sondeig a peu d'urna; despres,
        # la mitjana es fa nomes amb ells (veda.py).
        polls, mode = veda.select_polls(elections.get(row["election_id"]), polls)
        if mode == "peu_urna":
            print(f"   {row['election_id']} {row['sc'] or '(estatal)'}: "
                  f"mitjana nomes amb {len(polls)} sondeigs a peu d'urna")
        result = drop_not_standing(row["election_id"], agg.aggregate(polls))
        if result:
            store_aggregate(conn, row["election_id"], row["sc"], result)
            done.append((row["election_id"], row["sc"] or "(estatal)", len(polls), len(result)))
    conn.commit()
    return done


def load_real_results(conn, countries=("ES",)):
    """Baixa i desa els resultats reals que serveixen de base al mapa.

    Retorna (proces, pais, n_territoris, files_o_ERROR). Nomes es toquen els
    paisos demanats: la publicacio de politbureau.es demana nomes "ES", i aixi
    una caiguda del servidor italia no pot aturar la web espanyola.
    """
    out = []
    if "ES" in countries:
        out += [(proc, "ES", n, rows) for proc, n, rows in _load_spain(conn)]
    if "IT" in countries:
        out.append(_load_italy(conn))
    if "FR" in countries:
        out.append(_load_france(conn))
    return out


def _load_italy(conn):
    from .ingest import italy as it
    try:
        matched, missing, rows = it.store(conn, lambda s: parties.resolve(s, "IT")[0])
        return ("politiche-2022", "IT", matched, f"{rows} files, {missing} comuni sense mapa")
    except Exception as exc:                           # noqa: BLE001
        db.log_ingest(conn, "politiche-2022", None, "error", 0, f"{type(exc).__name__}: {exc}")
        return ("politiche-2022", "IT", 0, f"ERROR {type(exc).__name__}: {exc}")


def _load_france(conn):
    from .geo import fetch as geo
    from .ingest import france as fr
    try:
        # La regio de cada comuna surt de la geometria, no de cap taula a ma.
        cache = geo.GEO_DIR / "fr-communes-regions.json"
        if cache.exists():
            region_of = json.loads(cache.read_text(encoding="utf-8"))
        else:
            from .geo import regions as georegions
            communes = json.loads(geo.level_path("FR", "municipality").read_text(encoding="utf-8"))
            regs = json.loads(geo.level_path("FR", "region").read_text(encoding="utf-8"))
            region_of = georegions.assign(communes, regs, "id", "id")
            cache.write_text(json.dumps(region_of), encoding="utf-8")
        matched, skipped, rows = fr.store(conn, lambda s: parties.resolve(s, "FR")[0], region_of)
        return ("presidentielle-2022-t1", "FR", matched,
                f"{rows} files, {skipped} comunes fora del mapa")
    except Exception as exc:                           # noqa: BLE001
        db.log_ingest(conn, "presidentielle-2022-t1", None, "error", 0,
                      f"{type(exc).__name__}: {exc}")
        return ("presidentielle-2022-t1", "FR", 0, f"ERROR {type(exc).__name__}: {exc}")


def _load_spain(conn):
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


def run(conn, countries=None):
    """Recalcula-ho tot per als paisos demanats (per defecte, tots).

    La regla de la llico 21 es mante: si falla una carrega de resultats reals,
    el build s'atura. Pero nomes es carrega el que s'ha demanat, aixi que la
    publicacio de politbureau.es (`--country ES`) no depen mai d'Italia.
    """
    cfg = _config()
    countries = tuple(countries or sorted({e["country"] for e in cfg["elections"]}))
    print(f"Paisos: {', '.join(countries)}\n")

    print("1/3  Resultats electorals reals")
    fallits = []
    for process, country, n_areas, n_rows in load_real_results(conn, countries):
        print(f"     {country} {process:<24} {n_areas:>6} territoris  {n_rows}")
        if isinstance(n_rows, str) and n_rows.startswith("ERROR"):
            fallits.append(f"{country} {process}: {n_rows}")
    if fallits:
        raise RuntimeError(
            "Sense resultats reals no hi ha res honest a publicar; aturat.\n  "
            + "\n  ".join(fallits)
            + "\nEls ZIP del Ministeri viuen a data/raw/ i van al repositori.\n"
              "Si en falta cap, baixa'l de "
              "https://infoelectoral.interior.gob.es/estaticos/docxl/apliextr/"
        )

    print("\n2/3  Mitjanes ponderades d'enquestes")
    for eid, scope, n_polls, n_parties in aggregate_all(conn):
        print(f"     {eid:<18} {scope:<22} {n_polls:>5} enquestes -> {n_parties} partits")

    print("\n3/3  Projeccio territorial")
    for election in cfg["elections"]:
        eid, country = election["id"], election["country"]
        if country not in countries:
            continue
        base = (election.get("baseline") or {}).get("election")
        if country == "ES":
            if not base:
                continue
            n = project(conn, eid, base, levels=("municipality", "province", "region"),
                        country="ES")
            if n:
                print(f"     {eid:<18} {n:>7} files (swing sobre el resultat real)")
        elif country in ("IT", "FR"):
            if not base:
                continue
            n = project(conn, eid, base, levels=("municipality", "region"), country=country)
            if n:
                print(f"     {eid:<18} {n:>7} files (swing sobre el resultat real)")
        elif country == "US":
            n = project_states(conn, eid)
            if n:
                print(f"     {eid:<18} {n:>7} files (enquestes per estat, sense swing)")

    print("\n4/4  Repartiment d'escons")
    labels = {"dhondt_province": "llei d'Hondt per circumscripcio",
              "proportional": "proporcional estatal, NO el Rosatellum",
              "fptp_state": "majoritari per estat"}
    for election in cfg["elections"]:
        chamber = election.get("chamber")
        if not chamber or election["country"] not in countries:
            continue
        eid, method = election["id"], chamber.get("method", "dhondt_province")
        if method == "dhondt_province":
            n = project_seats(conn, eid, (election.get("baseline") or {}).get("election"))
        elif method == "proportional":
            n = project_seats_proportional(conn, eid, chamber["seats"])
        elif method == "fptp_state":
            n = project_seats_states(conn, eid)
        else:
            n = 0
        if n:
            total = chamber.get("in_play") or chamber["seats"]
            print(f"     {eid:<18} {n:>4}/{total} escons ({labels.get(method, method)})")
    print("\nFet.")
