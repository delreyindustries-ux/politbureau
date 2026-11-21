"""Pagina "Perfils de votants" (21/11/2026): config/perfils.json (perfils.py).

La pagina es pinta al navegador (web/perfils.js) a partir de les dades que
porta incrustades: tria un partit i veu on te vots a l'abast; tria un
col·lectiu i veu la seva fitxa.
"""
from __future__ import annotations

import json

from .. import parties
from ..perfils import OUT
from . import i18n
from .build import DIST, ELECTION
from .render import render_page, write

SPECIAL = {"UND": {"name": {"ca": "Indecisos", "es": "Indecisos"}, "color": "#bdbdbd"},
           "OTH": {"name": {"ca": "Altres partits", "es": "Otros partidos"}, "color": "#9e9e9e"}}


def perfils_page(env, cfg) -> int:
    try:
        d = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    if not d.get("dims"):
        return 0
    codes = set(d["focus"])
    for dim in d["dims"]:
        for g in dim["groups"]:
            codes |= set(g["vote"])
            for rec in g["parties"].values():
                codes |= {x["k"] for x in rec.get("from", []) + rec.get("risk", [])}
    meta = {}
    for c in sorted(codes):
        if c in SPECIAL:
            meta[c] = SPECIAL[c]
            continue
        m = parties.meta(c, "ES", ELECTION)
        name = "Sumar" if c == "SUMAR" else m["name"]
        meta[c] = {"name": {"ca": name, "es": name}, "color": m["color"]}
    payload = json.dumps({"d": d, "meta": meta}, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    for lang in i18n.LANGS:
        es = lang == "es"
        canonical = i18n.page_url("profiles", lang)
        html = render_page(
            env, cfg, "perfils.html.j2", lang, canonical, {lg: i18n.page_url("profiles", lg) for lg in i18n.LANGS},
            ("Perfiles de votantes: qué preocupa a cada colectivo y dónde hay votos por ganar" if es
             else "Perfils de votants: què preocupa a cada col·lectiu i on hi ha vots per guanyar"),
            ("Para cada grupo de la sociedad, sus temas, cuánto se mueve su voto y qué partidos compiten por él; "
             "para cada partido, los votantes a su alcance y de qué hablan. Con las entrevistas del CIS." if es else
             "Per a cada grup de la societat, els seus temes, quant es mou el seu vot i quins partits s'hi "
             "disputen; per a cada partit, els votants a l'abast i de què parlen. Amb les entrevistes del CIS."),
            payload=payload, d=d)
        write(DIST / canonical.strip("/") / "index.html", html)
    return sum(len(x["groups"]) for x in d["dims"])
