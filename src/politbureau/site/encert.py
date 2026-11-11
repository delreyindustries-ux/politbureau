"""Pagina de l'encert del 29N: nomes es genera quan hi ha el resultat (final.py)."""
from __future__ import annotations

from .. import final, parties
from . import i18n
from .build import DIST
from .render import render_page, write


def accuracy_page(env, cfg, conn) -> bool:
    rep = final.report(conn)
    if not rep:
        return False
    from .pages import _fdate, _fmt

    def signed(v):
        return "—" if v is None else ("+" if v > 0.05 else "−" if v < -0.05 else "") + _fmt(abs(v))

    for p in rep["parties"]:
        m = parties.meta(p["code"], "ES", "es-general")
        p["name"], p["color"] = m["name"], m["color"]
    for lang in i18n.LANGS:
        canonical = i18n.page_url("accuracy", lang)
        html = render_page(
            env, cfg, "accuracy.html.j2", lang, canonical,
            {lg: i18n.page_url("accuracy", lg) for lg in i18n.LANGS},
            ("29N: cuánto acertamos" if lang == "es" else "29N: quant l'hem encertat"),
            ("La media de encuestas y la previsión de Polit Bureau frente al resultado de las "
             "generales del 29 de noviembre de 2026, partido a partido." if lang == "es" else
             "La mitjana d'enquestes i la previsió de Polit Bureau davant del resultat de les "
             "generals del 29 de novembre de 2026, partit a partit."),
            r=rep, fmt=_fmt, fdate=_fdate, signed=signed)
        write(DIST / canonical.strip("/") / "index.html", html)
    cfg.setdefault("_extra_pages", []).append("accuracy")
    return True
