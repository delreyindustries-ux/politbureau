"""Guies "com es vota" dels parlaments estrangers (pla de ruta: "guies dels
sistemes estrangers", 25/11/2026).

Una pagina per a cada parlament proporcional que la web ja simula (els del
simulador obert, sandbox.foreign_pages), amb la mitjana d'enquestes d'avui:

  * les regles: escons, metode, primer divisor, llindar, prima de majoria;
  * els escons amb la llei i amb els altres metodes (d'Hondt, Sainte-Lague,
    resta mes gran amb quota Hare), sense llindar i, a Grecia, sense prima;
  * el vot que es queda sense esco (partits sota el llindar i "altres");
  * l'index de desproporcionalitat de Gallagher de cada variant.

No hi ha el resultat complet de l'ultima eleccio de cada pais (last_error.json
nomes porta els partits grans), i per aixo la guia es fa amb la mitjana
d'avui i ho diu. Regles: config/chambers.yaml (seccio "Electoral system" de
l'article de Wikipedia de l'ultima eleccio de cada pais).

A mes, una pagina amb tots els paisos: els que tenen guia i, en text, com es
vota alla on els escons no es poden simular amb la mitjana estatal.
"""
from __future__ import annotations

import math

from ..model import seats as seatlib
from . import i18n
from .build import DIST
from .render import render_page, write

METHODS = ("dhondt", "sainte_lague", "hare", "droop")
LABEL = {"dhondt": ("d'Hondt", "d'Hondt"), "sainte_lague": ("Sainte-Laguë", "Sainte-Laguë"),
         "hare": ("Resta més gran (Hare)", "Resto mayor (Hare)"),
         "droop": ("Resta més gran (Hagenbach-Bischoff)", "Resto mayor (Hagenbach-Bischoff)")}
WORLD = {"ca": "mon", "es": "mundo"}


def _key(name: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn").lower()


def _in(of: str, place: str, es: bool) -> str:
    """'dels Paisos Baixos' -> 'als Paisos Baixos'; 'de los Paises Bajos' -> 'en los Paises Bajos'."""
    o = of or ""
    if es:
        for a, b in (("de los ", "en los "), ("de las ", "en las "), ("del ", "en el "), ("de la ", "en la ")):
            if o.startswith(a):
                return b + o[len(a):]
        return "en " + place
    for a, b in (("dels ", "als "), ("del ", "al "), ("de les ", "a les "), ("de la ", "a la "), ("de l'", "a l'")):
        if o.startswith(a):
            return b + o[len(a):]
    return "a " + place


def _gallagher(votes: dict, seats: dict, n: int) -> float:
    keys = set(votes) | set(seats)
    return math.sqrt(sum((votes.get(k, 0) - 100.0 * seats.get(k, 0) / n) ** 2 for k in keys) / 2)


def _view(e, d):
    ch = e["chamber"]
    method = "dhondt" if ch.get("method") == "proportional" else ch["method"]
    seats = ch.get("in_play") or ch["seats"]
    thr = ch.get("threshold") or 0.0
    first = ch.get("first_divisor") or 1.0
    bonus = ch.get("bonus")
    avg = [a for a in d["avg"] if a.get("share")]
    shares = {a["code"]: a["share"] for a in avg if a["code"] != "OTHER"}
    other = sum(a["share"] for a in avg if a["code"] == "OTHER")
    votes = {**shares, **({"OTHER": other} if other else {})}

    def run(m, t=thr, f=None, b=bonus):
        return seatlib.apportion(shares, seats, m, t, f if f is not None else (first if m == method else 1.0), b)

    cols = [{"key": "law", "l": ("Amb la llei", "Con la ley"), "seats": run(method)}]
    if thr:
        cols.append({"key": "nothr", "l": ("Sense llindar", "Sin umbral"), "seats": run(method, t=0.0)})
    if bonus:
        cols.append({"key": "nobonus", "l": ("Sense prima", "Sin prima"), "seats": run(method, b=None)})
    for m in ("dhondt", "sainte_lague", "hare"):
        if m == method and first == 1.0:
            continue
        cols.append({"key": m, "l": (LABEL[m][0], LABEL[m][1]) if m != method else
                     (LABEL[m][0] + " pur", LABEL[m][1] + " puro"),
                     "seats": run(m, f=1.0, b=None)})
    for c in cols:
        c["g"] = round(_gallagher(votes, c["seats"], seats), 1)
    law = cols[0]["seats"]
    rows = []
    for a in sorted(avg, key=lambda a: -a["share"]):
        if a["code"] == "OTHER":
            continue
        s = [c["seats"].get(a["code"], 0) for c in cols]
        if not any(s) and a["share"] < 1:
            continue
        rows.append({"name": a.get("person") or a["name"], "color": a["color"], "pct": a["share"],
                     "out": thr and a["share"] < thr * 100, "seats": s, "seat_pct": 100.0 * law.get(a["code"], 0) / seats})
    below = [r for r in rows if not r["seats"][0]]
    wasted = sum(a["share"] for a in avg if a["code"] != "OTHER" and not law.get(a["code"])) + other
    top = max(law.items(), key=lambda kv: kv[1]) if law else None
    return {"seats": seats, "total": ch.get("total") or seats, "majority": d.get("majority") or (ch.get("total") or seats) // 2 + 1,
            "method": method, "first": first, "thr": thr * 100, "bonus": bonus, "districts": bool(ch.get("districts")),
            "note": ch, "cols": cols, "rows": rows, "below": below, "wasted": wasted, "other": other,
            "top": top}


def pages(env, cfg, conn) -> list[dict]:
    from .pages import abroad_data, abroad_elections
    done, notes = [], []
    for eid, e in abroad_elections().items():
        ch = e.get("chamber") or {}
        if e.get("group") == "sub" or e.get("country") == "ES" or not e.get("pub"):
            continue
        method = "dhondt" if ch.get("method") == "proportional" else ch.get("method")
        pub = e["pub"]
        if method not in METHODS:
            if ch.get("note_ca"):
                notes.append({"name": {"ca": pub["name_ca"], "es": pub["name_es"]},
                              "note": {"ca": ch["note_ca"], "es": ch.get("note_es", ch["note_ca"])},
                              "eid": eid})
            continue
        try:
            d = abroad_data(conn, eid)
        except Exception:                                  # noqa: BLE001
            d = None
        if not d or not d.get("avg") or not d.get("seats"):
            continue
        v = _view(e, d)
        urls = {lang: f"{i18n.page_url('guide', lang)}{WORLD[lang]}/{pub[lang]}/" for lang in i18n.LANGS}
        for lang in i18n.LANGS:
            es = lang == "es"
            place = d["name"][lang]
            of = (d.get("of") or {}).get(lang) or pub.get(f"of_{lang}") or (("de " if es else "de ") + place)
            name = ch.get("name_es") if es and ch.get("name_es") else ch.get("name", "")
            where = _in(of, place, es)
            title = (f"Cómo se vota {where}: {name}, método y umbral" if es
                     else f"Com es vota {where}: {name}, mètode i llindar")
            desc = (f"El sistema electoral de {place} explicado con la media de encuestas de hoy: los escaños con la ley y "
                    "con otros métodos, el voto que se queda sin escaño y la desproporción." if es else
                    f"El sistema electoral {of} explicat amb la mitjana d'enquestes d'avui: els escons amb la llei "
                    "i amb altres mètodes, el vot que es queda sense escó i la desproporció.")
            sandbox_url = f"/{lang}/{i18n.page_url('sandbox', lang).strip('/').split('/', 1)[1]}/{pub[lang]}/"
            html = render_page(env, cfg, "guide-foreign.html.j2", lang, urls[lang], urls, title, desc,
                               v=v, place=place, where=where, chamber=name, of=of, country_url=d["urls"][lang],
                               sandbox_url=sandbox_url)
            write(DIST / urls[lang].strip("/") / "index.html", html)
        done.append({"eid": eid, "url": urls, "name": {"ca": pub["name_ca"], "es": pub["name_es"]},
                     "chamber": ch.get("name", ""), "method": method, "thr": v["thr"], "seats": v["seats"]})
    done.sort(key=lambda x: x["name"]["ca"])
    notes.sort(key=lambda x: x["name"]["ca"])
    index = {lang: f"{i18n.page_url('guide', lang)}{WORLD[lang]}/" for lang in i18n.LANGS}
    if done:
        for lang in i18n.LANGS:
            es = lang == "es"
            html = render_page(env, cfg, "guide-world.html.j2", lang, index[lang], index,
                               ("Cómo se vota en el mundo: sistemas electorales de " + str(len(done) + len(notes)) + " países"
                                if es else "Com es vota al món: sistemes electorals de " + str(len(done) + len(notes)) + " països"),
                               ("Método, umbral y prima de cada parlamento, con la media de encuestas de hoy, y cómo se vota "
                                "donde los escaños no se pueden simular." if es else
                                "Mètode, llindar i prima de cada parlament, amb la mitjana d'enquestes d'avui, i com es vota "
                                "allà on els escons no es poden simular."),
                               guides=sorted(done, key=lambda x: _key(x["name"][lang])),
                               notes=sorted(notes, key=lambda x: _key(x["name"][lang])), label=LABEL)
            write(DIST / index[lang].strip("/") / "index.html", html)
    cfg.setdefault("_extra_urls", {})
    for lang in i18n.LANGS:
        cfg["_extra_urls"].setdefault(lang, []).extend([x["url"][lang] for x in done] + ([index[lang]] if done else []))
    return done
