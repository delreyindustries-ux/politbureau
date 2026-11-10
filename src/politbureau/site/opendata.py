"""Dades obertes (10/11/2026, pla de ruta, fase 1): fitxers CSV per descarregar.

Tot el que la web mostra, en brut, perque periodistes i investigadors ho
puguin comprovar i reutilitzar. Les enquestes venen de la Viquipedia
(CC BY-SA 4.0), aixi que el conjunt es publica amb la mateixa llicencia.
Mai no hi surten els Estats Units, el Brasil ni Russia (decisio de l'Alfonso).
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import io

from . import i18n
from .build import DIST, ELECTION
from .render import render_page, write

EXCLUDED = {"US", "BR", "RU"}
OUT = DIST / "dades"


def _write(name, header, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    n = 0
    for r in rows:
        w.writerow(r)
        n += 1
    body = buf.getvalue().encode("utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_bytes(body)
    (OUT / (name + ".gz")).write_bytes(gzip.compress(body, 6))
    return {"file": name, "rows": n, "bytes": len(body)}


def build_files(conn, forecast=None) -> list[dict]:
    countries = dict(conn.execute("SELECT DISTINCT election_id, country FROM poll").fetchall())
    keep = {e for e, c in countries.items() if c not in EXCLUDED}
    files = []

    files.append(dict(key="polls", **_write(
        "enquestes.csv",
        ["eleccio", "pais", "ambit", "codi_territori", "institut", "client", "inici_camp",
         "fi_camp", "mostra", "partit", "percentatge", "font"],
        ((r["election_id"], r["country"], r["scope"], r["scope_code"] or "", r["pollster"] or "",
          r["client"] or "", r["fieldwork_start"] or "", r["fieldwork_end"] or "",
          r["sample_size"] or "", r["party"], r["share"], r["source_url"])
         for r in conn.execute(
             """SELECT p.election_id, p.country, p.scope, p.scope_code, p.pollster, p.client,
                       p.fieldwork_start, p.fieldwork_end, p.sample_size, p.source_url,
                       r.party, r.share
                FROM poll p JOIN poll_result r ON r.poll_id = p.id
                WHERE r.share IS NOT NULL
                ORDER BY p.election_id, p.fieldwork_end DESC, p.pollster, r.party""")
         if r["country"] not in EXCLUDED))))

    files.append(dict(key="averages", **_write(
        "mitjanes.csv",
        ["eleccio", "codi_territori", "partit", "percentatge", "minim_instituts",
         "maxim_instituts", "enquestes", "calculat"],
        ((r["election_id"], r["scope_code"], r["party"], r["share"], r["lo"], r["hi"],
          r["n_polls"], r["computed_at"])
         for r in conn.execute(
             """SELECT * FROM aggregate ORDER BY election_id, scope_code, share DESC""")
         if r["election_id"] in keep))))

    files.append(dict(key="seats", **_write(
        "congres-2026-escons.csv",
        ["nivell", "codi_provincia", "partit", "escons"],
        ((r["level"], r["code"], r["party"], r["seats"])
         for r in conn.execute(
             """SELECT level, code, party, seats FROM seat_projection
                WHERE election_id = ? ORDER BY level, code, seats DESC""", (ELECTION,))))))

    files.append(dict(key="municipalities", **_write(
        "congres-2026-municipis.csv",
        ["codi_ine", "partit", "percentatge"],
        ((r["code"], r["party"], r["share"])
         for r in conn.execute(
             """SELECT code, party, share FROM projection
                WHERE election_id = ? AND level = 'municipality'
                ORDER BY code, share DESC""", (ELECTION,))))))

    from .. import pollsters
    rating = pollsters.load()
    if rating:
        files.append(dict(key="pollsters", **_write(
            "instituts-valoracio.csv",
            ["eleccio", "data_eleccio", "institut", "client", "fi_camp", "mostra", "partit",
             "enquesta", "resultat", "error_mitja_enquesta", "mes_menys"],
            ((e["id"], e["date"], r["pollster"], r["client"] or "", r["end"], r["sample"] or "",
              k, v, e["result"][k], r["mae"], r["plus_minus"])
             for e in rating["elections"] for r in e["polls"] for k, v in r["shares"].items()))))

    if forecast:
        files.append(dict(key="forecast", **_write(
            "congres-2026-previsio.csv",
            ["partit", "escons_mediana", "escons_p10", "escons_p90", "prob_primer_partit",
             "prob_cap_esco", "simulacions"],
            ((r["code"], r["median"], r["lo"], r["hi"], round(r["first"], 4),
              round(r["zero"], 4), forecast["n"]) for r in forecast["parties"]))))
    return files


_DESC = {
    "polls": {"es": "Todas las encuestas de la web, partido a partido: instituto, fechas de campo, muestra y enlace a la fuente.",
              "ca": "Totes les enquestes de la web, partit a partit: institut, dates de camp, mostra i enllaç a la font."},
    "averages": {"es": "La media de cada elección y territorio, con el mínimo y el máximo entre institutos.",
                 "ca": "La mitjana de cada elecció i territori, amb el mínim i el màxim entre instituts."},
    "seats": {"es": "Generales del 29N: escaños estimados en total y en cada provincia (ley d'Hondt).",
              "ca": "Generals del 29N: escons estimats en total i a cada província (llei d'Hondt)."},
    "municipalities": {"es": "Generales del 29N: estimación de voto en cada uno de los municipios, por código INE.",
                       "ca": "Generals del 29N: estimació de vot a cadascun dels municipis, per codi INE."},
    "pollsters": {"es": "Valoración de los institutos: la última encuesta de cada uno antes de las generales de 2016, 2019 y 2023 frente al resultado oficial.",
                  "ca": "Valoració dels instituts: l'última enquesta de cadascun abans de les generals del 2016, el 2019 i el 2023 davant del resultat oficial."},
    "forecast": {"es": "Generales del 29N: previsión con probabilidades (mediana, intervalo del 80 % y probabilidad de ser primer partido).",
                 "ca": "Generals del 29N: previsió amb probabilitats (mediana, interval del 80 % i probabilitat de ser primer partit)."},
}


API = DIST / "api" / "v1"
LICENCE = {"name": "CC BY-SA 4.0", "url": "https://creativecommons.org/licenses/by-sa/4.0/",
           "attribution": "Polit Bureau (politbureau.es)"}


def _json(path, obj):
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def build_api(conn, forecast=None) -> int:
    """API de nomes lectura: fitxers JSON estatics a /api/v1/, regenerats amb la web.

    index.json      llista d'eleccions amb l'enllac a la mitjana de cadascuna
    mitjanes/<id>.json  mitjana per territori (minim i maxim entre instituts)
    congres-2026.json   escons estimats (total i per provincia) i previsio
    instituts.json      valoracio dels instituts (config/pollster_ratings.json)
    """
    from .. import pollsters

    updated = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    meta = {"updated": updated, "licence": LICENCE}
    counts = dict(conn.execute(
        "SELECT election_id, COUNT(*) FROM poll GROUP BY election_id").fetchall())
    countries = dict(conn.execute("SELECT DISTINCT election_id, country FROM poll").fetchall())
    by: dict[str, dict] = {}
    for r in conn.execute("""SELECT * FROM aggregate ORDER BY election_id, scope_code, share DESC"""):
        if countries.get(r["election_id"]) in EXCLUDED or r["election_id"] not in countries:
            continue
        e = by.setdefault(r["election_id"], {})
        e.setdefault(r["scope_code"] or "", []).append(
            {"party": r["party"], "share": r["share"], "min": r["lo"], "max": r["hi"],
             "polls": r["n_polls"]})
    n = 0
    for eid, scopes in by.items():
        _json(API / "mitjanes" / f"{eid}.json",
              {**meta, "election": eid, "country": countries[eid], "scopes": scopes})
        n += 1
    _json(API / "index.json", {**meta, "elections": [
        {"id": eid, "country": countries[eid], "polls": counts.get(eid, 0),
         "average": f"/api/v1/mitjanes/{eid}.json"} for eid in sorted(by)],
        "congress_2026": "/api/v1/congres-2026.json", "pollsters": "/api/v1/instituts.json"})
    seats: dict[str, dict] = {}
    for r in conn.execute("""SELECT level, code, party, seats FROM seat_projection
                             WHERE election_id = ? ORDER BY level, code, seats DESC""", (ELECTION,)):
        key = "total" if r["level"] == "chamber" else r["code"]
        seats.setdefault(key, {})[r["party"]] = r["seats"]
    fc = None
    if forecast:
        fc = {"simulations": forecast["n"], "majority": forecast["majority"],
              "blocs": {k: {"majority_probability": round(v["majority"], 4)}
                        for k, v in forecast["blocs"].items()},
              "parties": [{"party": r["code"], "median": r["median"], "p10": r["lo"],
                           "p90": r["hi"], "first_probability": round(r["first"], 4)}
                          for r in forecast["parties"]]}
    _json(API / "congres-2026.json", {**meta, "election": ELECTION, "date": "2026-11-29",
                                      "seats": seats, "forecast": fc})
    rating = pollsters.load()
    if rating:
        _json(API / "instituts.json", {**meta, "computed": rating["computed"],
                                       "ratings": rating["ratings"],
                                       "elections": rating["elections"]})
    return n + 3


def opendata_page(env, cfg, conn, forecast=None):
    files = build_files(conn, forecast)
    n_api = build_api(conn, forecast)
    print(f"     api: {n_api} fitxers JSON a dist/api/v1/")
    today = dt.date.today().isoformat()
    for lang in i18n.LANGS:
        canonical = i18n.page_url("opendata", lang)
        rows = [{**f, "desc": _DESC[f["key"]][lang],
                 "kb": max(1, round(f["bytes"] / 1024))} for f in files]
        html = render_page(
            env, cfg, "opendata.html.j2", lang, canonical,
            {lg: i18n.page_url("opendata", lg) for lg in i18n.LANGS},
            ("Datos abiertos: encuestas, medias y estimaciones" if lang == "es"
             else "Dades obertes: enquestes, mitjanes i estimacions"),
            ("Descarga en CSV todas las encuestas, medias y estimaciones de Polit Bureau, "
             "con licencia CC BY-SA 4.0." if lang == "es" else
             "Descarrega en CSV totes les enquestes, mitjanes i estimacions de Polit Bureau, "
             "amb llicència CC BY-SA 4.0."),
            files=rows, today=today)
        write(DIST / canonical.strip("/") / "index.html", html)
    return len(files)
