"""Genera el lloc public estatic a dist/.

Per que estatic: son 8.202 territoris x 2 idiomes = mes de setze mil pagines que
canvien un cop al dia. Servir-les amb Python voldria dir pagar un servidor
engegat les vint-i-quatre hores per repetir sempre la mateixa resposta. Generades
un cop i servides per un CDN gratuit, el cost d'allotjament es zero i tot el que
entri per publicitat es benefici.

Les dades de cada territori van DINS del seu HTML, no en un JSON a part. Aixi la
pagina es llegeix sencera sense cap peticio addicional, que es el que necessita
un cercador per indexar-la: si el contingut arriba per JavaScript, Google el pot
veure tard i malament.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import unicodedata
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .. import db, parties
from ..geo import fetch as geo
from ..geo import regions as georegions
from ..model import seats as seatlib
from . import i18n

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "web"
DIST = ROOT / "dist"
CONFIG = ROOT / "config" / "site.yaml"

ELECTION = "es-general"
BASELINE = "congreso-2023"
BASELINE_YEAR = "2023"
BASELINE_LABEL = {"es": "las elecciones generales del 23 de julio de 2023",
                  "ca": "les eleccions generals del 23 de juliol del 2023"}

LEVEL_NAME = {
    "municipality": {"es": "municipio", "ca": "municipi"},
    "province": {"es": "provincia", "ca": "província"},
    "region": {"es": "comunidad autónoma", "ca": "comunitat autònoma"},
}

# El nivell amb el seu article, perque "en el provincia de Murcia" no s'aguanta.
# El genere no es dedueix del codi: cal declarar-lo.
LEVEL_IN = {
    "municipality": {"es": "en el municipio de", "ca": "al municipi de"},
    "province": {"es": "en la provincia de", "ca": "a la província de"},
    "region": {"es": "en la comunidad de", "ca": "a la comunitat de"},
}


# ------------------------------------------------------------------ utilitats

def url_slug(text: str) -> str:
    """'L'Hospitalet de Llobregat' -> 'l-hospitalet-de-llobregat'."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace("'", "-").replace("’", "-").replace("/", "-")
    text = re.sub(r"[^A-Za-z0-9]+", "-", text)
    return re.sub(r"-{2,}", "-", text).strip("-").lower() or "x"


def pct(x, decimals: int = 1) -> str:
    """Percentatge amb coma decimal, que es la correcta en castella i catala."""
    if x is None:
        return "—"
    return f"{x:.{decimals}f}".replace(".", ",") + "%"


def thousands(n) -> str:
    """Separador de milers a l'espanyola: 1.234.567."""
    if n is None:
        return "—"
    return f"{int(n):,}".replace(",", ".")


def load_config() -> dict:
    with CONFIG.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# --------------------------------------------------------------- dades crues

def gather(conn) -> dict:
    """Llegeix la base de dades una sola vegada i ho deixa tot a la memoria.

    Fer una consulta per pagina serien centenars de milers de consultes; llegir
    les quatre taules senceres son uns segons i dos-cents megues de RAM.
    """
    names = {lv: geo.names("ES", lv) for lv in ("municipality", "province", "region")}
    table = georegions.table()

    real: dict = {}
    meta: dict = {}
    for r in conn.execute(
            """SELECT level, code, name, party, votes, valid_votes, census
               FROM election_result WHERE election = ?""", (BASELINE,)):
        key = (r["level"], r["code"])
        real.setdefault(key, {})[r["party"]] = r["votes"]
        if key not in meta:
            meta[key] = {"name": r["name"], "valid_votes": r["valid_votes"],
                         "census": r["census"]}

    proj: dict = {}
    for r in conn.execute(
            "SELECT level, code, party, share FROM projection WHERE election_id = ?",
            (ELECTION,)):
        proj.setdefault((r["level"], r["code"]), {})[r["party"]] = r["share"]

    magnitude = {r["code"]: r["seats"] for r in conn.execute(
        "SELECT code, seats FROM constituency WHERE election = ? AND level = 'province'",
        (BASELINE,))}
    seats_real: dict = {}
    for r in conn.execute(
            """SELECT code, party, seats FROM constituency_result
               WHERE election = ? AND seats > 0""", (BASELINE,)):
        seats_real.setdefault(r["code"], {})[r["party"]] = r["seats"]
    seats_proj: dict = {}
    for r in conn.execute(
            """SELECT code, party, seats FROM seat_projection
               WHERE election_id = ? AND level = 'province'""", (ELECTION,)):
        seats_proj.setdefault(r["code"], {})[r["party"]] = r["seats"]

    deputies: dict = {}
    for r in conn.execute(
            """SELECT province, party, position, name, elected FROM deputy
               WHERE election = ? ORDER BY province, party, position""", (BASELINE,)):
        deputies.setdefault(r["province"], []).append(dict(r))

    return {"names": names, "region_of": table, "real": real, "meta": meta,
            "proj": proj, "magnitude": magnitude, "seats_real": seats_real,
            "seats_proj": seats_proj, "deputies": deputies}


MINOR_CUT = 0.3     # per sota d'aixo la formacio va al bloc desplegable


def area_rows(data, level, code):
    """Files de la taula: partit, vots reals, % real, % estimat i diferencia.

    Hi son TOTES les formacions que van rebre vots, tambe les que no van treure
    cap escó. Les que no arriben al `MINOR_CUT` es marquen amb `minor` perque la
    pagina les pugui posar en un bloc a part: la taula principal ha de ser
    llegible, pero amagar-les seria deixar fora la meitat de les candidatures.
    """
    real = data["real"].get((level, code), {})
    proj = data["proj"].get((level, code), {})
    valid = (data["meta"].get((level, code)) or {}).get("valid_votes") or 0
    seats_real = (data["seats_real"].get(code) or {}) if level == "province" else {}
    seats_now = (data["seats_proj"].get(code) or {}) if level == "province" else {}
    rows = []
    for party in set(real) | set(proj):
        votes = real.get(party)
        share = (votes * 100.0 / valid) if (votes and valid) else None
        now = proj.get(party)
        rows.append({**parties.meta(party, "ES"), "votes": votes, "share": share,
                     "now": now,
                     "seats": seats_real.get(party, 0),
                     "seats_now": seats_now.get(party, 0),
                     "minor": (share or 0) < MINOR_CUT and (now or 0) < MINOR_CUT,
                     "delta": (now - share) if (now is not None and share is not None) else None})
    rows.sort(key=lambda r: -(r["now"] if r["now"] is not None else r["share"] or 0))
    return rows


def unrepresented(rows, level, valid_votes):
    """Les formacions que van rebre vots i cap escó, amb el seu pes conjunt.

    Nomes te sentit a la provincia, que es la circumscripcio: un municipi no
    escull diputats. A la resta de nivells retorna None i la pagina no ho pinta.
    """
    if level != "province":
        return None
    losers = [r for r in rows if not r["seats"] and r["votes"]]
    if not losers:
        return None
    votes = sum(r["votes"] for r in losers)
    return {
        "rows": sorted(losers, key=lambda r: -r["votes"]),
        "count": len(losers),
        "votes": votes,
        "share": (votes * 100.0 / valid_votes) if valid_votes else None,
    }


def lede_for(data, level, code, rows, lang):
    """La frase d'entrada, feta amb els numeros reals d'aquest territori.

    Es el que fa que cada pagina digui alguna cosa diferent: sense aixo, vuit mil
    pagines amb la mateixa redaccio i nomes la taula canviada son exactament el
    que Google penalitza com a contingut generat en massa.
    """
    name = (data["meta"].get((level, code)) or {}).get("name") \
        or data["names"][level].get(code) or code
    kind = LEVEL_IN[level][lang]
    # Uns quants noms oficials ja porten el tipus a dins ("Region de Murcia",
    # "Principado de Asturias", "Illes Balears"): repetir-lo davant donaria
    # "en la comunidad de Region de Murcia".
    if any(name.startswith(w) for w in ("Región", "Regió", "Comunidad", "Comunitat",
                                        "Ciudad", "Principado", "Illes", "País", "Pais")):
        kind = "en" if lang == "es" else "a"
    # El mes votat DE DEBO, no el primer de la taula: les files van ordenades per
    # l'estimacio d'avui, i confondre-ho fa que la frase digui que va guanyar un
    # partit que en realitat va quedar segon.
    with_real = [r for r in rows if r["share"] is not None]
    top = max(with_real, key=lambda r: r["share"]) if with_real else None
    now = rows[0] if rows and rows[0]["now"] is not None else None
    census = (data["meta"].get((level, code)) or {}).get("census")

    if lang == "es":
        parts = []
        if top:
            parts.append(f"En {BASELINE_LABEL['es']}, {top['name']} fue la fuerza más "
                         f"votada {kind} {name}, con el "
                         f"{pct(top['share'])} de los votos válidos")
            if top["votes"]:
                parts[-1] += f" ({thousands(top['votes'])} votos)"
            parts[-1] += "."
        if now:
            if top and now["code"] == top["code"]:
                parts.append(f"La estimación de hoy le da un {pct(now['now'])}.")
            else:
                parts.append(f"Con las encuestas de hoy, la estimación sitúa por delante "
                             f"a {now['name']}, con un {pct(now['now'])}.")
        if census:
            parts.append(f"{name} tiene {thousands(census)} electores.")
        return " ".join(parts)

    parts = []
    if top:
        parts.append(f"A {BASELINE_LABEL['ca']}, {top['name']} va ser la força més "
                     f"votada {kind} {name}, amb el "
                     f"{pct(top['share'])} dels vots vàlids")
        if top["votes"]:
            parts[-1] += f" ({thousands(top['votes'])} vots)"
        parts[-1] += "."
    if now:
        if top and now["code"] == top["code"]:
            parts.append(f"L'estimació d'avui li dona un {pct(now['now'])}.")
        else:
            parts.append(f"Amb les enquestes d'avui, l'estimació situa al davant "
                         f"{now['name']}, amb un {pct(now['now'])}.")
    if census:
        parts.append(f"{name} té {thousands(census)} electors.")
    return " ".join(parts)


# ------------------------------------------------------------------- adreces

def build_urls(data):
    """{(nivell, codi): {idioma: url}} + els noms i les relacions de pertinenca.

    Les adreces son jerarquiques -- /es/municipio/almeria/abla/ -- perque siguin
    llegibles i perque el nom d'un municipi nomes es unic dins de la seva
    provincia: n'hi ha vint-i-un que es diuen "Villanueva de alguna cosa".
    """
    prov_region = data["region_of"]["province"]
    slugs = {"province": {}, "region": {}, "municipality": {}}
    for code, name in data["names"]["province"].items():
        slugs["province"][code] = url_slug(name)
    for code, name in data["names"]["region"].items():
        slugs["region"][code] = url_slug(name)

    used = {}
    for code, name in sorted(data["names"]["municipality"].items()):
        prov = slugs["province"].get(code[:2], code[:2])
        base = url_slug(name)
        key = (prov, base)
        if key in used:                    # no hauria de passar, pero mes val
            base = f"{base}-{code}"        # comprovar-ho que servir dues pagines iguals
        used[key] = code
        slugs["municipality"][code] = base

    urls = {}
    for lang in i18n.LANGS:
        for code in data["names"]["region"]:
            urls.setdefault(("region", code), {})[lang] = \
                f"/{lang}/{i18n.path_for('region', lang)}/{slugs['region'][code]}/"
        for code in data["names"]["province"]:
            urls.setdefault(("province", code), {})[lang] = \
                f"/{lang}/{i18n.path_for('province', lang)}/{slugs['province'][code]}/"
        for code in data["names"]["municipality"]:
            prov = slugs["province"].get(code[:2], code[:2])
            urls.setdefault(("municipality", code), {})[lang] = \
                f"/{lang}/{i18n.path_for('municipality', lang)}/{prov}/{slugs['municipality'][code]}/"
    return urls, slugs, prov_region


def dhondt_for(data, code):
    shares = data["proj"].get(("province", code), {})
    mag = data["magnitude"].get(code)
    valid = (data["meta"].get(("province", code)) or {}).get("valid_votes")
    if not shares or not mag:
        return None
    table = seatlib.quotient_table(shares, mag)
    if not table["won"]:
        return None
    to_votes = lambda pts: int(round(pts * valid / 100)) if valid else 0   # noqa: E731
    return {
        "cutoff": table["cutoff"],
        "won": [{**parties.meta(w["party"], "ES"), "divisor": w["divisor"],
                 "quotient": w["quotient"]} for w in table["won"]],
        "next": [{**parties.meta(n["party"], "ES"), "divisor": n["divisor"],
                  "quotient": n["quotient"], "needed_votes": to_votes(n["needed"])}
                 for n in table["next"][:3]],
    }


def simulator_for(data, code):
    """Dades per al simulador de coalicions d'una circumscripcio.

    Van les dues capes, perque les dues preguntes son legitimes i diferents:
    que hauria passat el 2023 si haguessin anat junts (comprovable) i que
    passaria avui (estimacio). El calcul el fa el navegador amb la mateixa
    regla d'Hondt que `model/seats.py`, i per aixo hi va la magnitud real de
    la circumscripcio i els vots valids, no cap aproximacio.
    """
    mag = data["magnitude"].get(code)
    if not mag:
        return None
    real = data["real"].get(("province", code), {})
    proj = data["proj"].get(("province", code), {})
    valid = (data["meta"].get(("province", code)) or {}).get("valid_votes") or 0
    out = []
    for party in set(real) | set(proj):
        votes = real.get(party)
        share = (votes * 100.0 / valid) if (votes and valid) else 0.0
        now = proj.get(party) or 0.0
        if share < 0.1 and now < 0.1:
            continue
        info = parties.meta(party, "ES")
        out.append({"code": party, "name": info["name"], "color": info["color"],
                    "real": round(share, 3), "now": round(now, 3)})
    if len(out) < 2:
        return None
    out.sort(key=lambda r: -max(r["now"], r["real"]))
    return {"magnitude": mag, "valid": valid, "parties": out}


def deputies_for(data, code):
    members = data["deputies"].get(code)
    if not members:
        return None
    by_party = {}
    for m in members:
        by_party.setdefault(m["party"], []).append(m)

    def row(m, party):
        info = parties.meta(party, "ES")
        return {"color": info["color"], "party_name": info["name"], "name": m["name"],
                "code": party, "position": m["position"]}

    real = [row(m, p) for p, ms in by_party.items() for m in ms if m["elected"]]
    proj_seats = data["seats_proj"].get(code, {})
    projected = [row(m, p) for p, ms in by_party.items()
                 for m in ms[:proj_seats.get(p, 0)]]
    real.sort(key=lambda d: (parties.position(d["code"], "ES"), d["position"]))

    real_names = {d["name"] for d in real}
    proj_names = {d["name"] for d in projected}
    changes = [(d, "in") for d in projected if d["name"] not in real_names]
    changes += [(d, "out") for d in real if d["name"] not in proj_names]
    changes.sort(key=lambda kv: (kv[1], parties.position(kv[0]["code"], "ES")))
    return {"real": real, "changes": changes}
