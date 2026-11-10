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
    "forecast": {"es": "Generales del 29N: previsión con probabilidades (mediana, intervalo del 80 % y probabilidad de ser primer partido).",
                 "ca": "Generals del 29N: previsió amb probabilitats (mediana, interval del 80 % i probabilitat de ser primer partit)."},
}


def opendata_page(env, cfg, conn, forecast=None):
    files = build_files(conn, forecast)
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
