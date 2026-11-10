"""Pagina de valoracio dels instituts d'enquestes (pla de ruta, fase 1).

Nomes llegeix config/pollster_ratings.json, que fa `politbureau instituts`.
"""
from __future__ import annotations

from .. import parties, pollsters
from . import i18n
from .build import DIST
from .render import render_page, write

LABEL = {"congreso-2016": "26J 2016", "congreso-2019a": "28A 2019",
         "congreso-2019n": "10N 2019", "congreso-2023": "23J 2023"}
# Colors i noms de partits que ja no son al cataleg actual.
STYLE = {"CS": ("Cs", "#EB6109"), "PODEMOS": ("Unidas Podemos", "#683064")}
MIN_ELECTIONS = 2


def _party(code):
    if code in STYLE:
        name, color = STYLE[code]
        return {"code": code, "name": name, "color": color}
    m = parties.meta(code, "ES")
    return {"code": code, "name": m["name"], "color": m["color"]}


def context():
    data = pollsters.load()
    if not data:
        return None
    elections = []
    for e in data["elections"]:
        elections.append({**e, "label": LABEL.get(e["id"], e["id"]),
                          "parties": [_party(c) for c in e["main"]]})
    rated = [r for r in data["ratings"] if r["n"] >= MIN_ELECTIONS]
    others = sorted((r for r in data["ratings"] if r["n"] < MIN_ELECTIONS),
                    key=lambda r: r["pollster"].lower())
    for r in rated + others:
        r["labels"] = [LABEL.get(x, x) for x in r["elections"]]
    from .pages import _fdate, _fmt

    def signed(v):
        return "—" if v is None else ("+" if v > 0.05 else "−" if v < -0.05 else "") + _fmt(abs(v))

    return {"fmt": _fmt, "fdate": _fdate, "signed": signed,
            "elections": elections, "rated": rated, "others": others,
            "computed": data["computed"], "window": data["window_days"],
            "main_share": data["main_share"], "min_elections": MIN_ELECTIONS,
            "beat": sum(1 for e in elections if e["average_mae"] < e["mean_mae"])}


def rating_page(env, cfg):
    ctx = context()
    if not ctx:
        return 0
    for lang in i18n.LANGS:
        canonical = i18n.page_url("pollsters", lang)
        html = render_page(
            env, cfg, "pollsters.html.j2", lang, canonical,
            {lg: i18n.page_url("pollsters", lg) for lg in i18n.LANGS},
            ("Valoración de los institutos de encuestas: quién acierta más" if lang == "es"
             else "Valoració dels instituts d'enquestes: qui l'encerta més"),
            ("Cuánto se equivocó cada instituto en las elecciones generales de 2016, 2019 y 2023, "
             "comparado con el resultado oficial." if lang == "es" else
             "Quant es va equivocar cada institut a les eleccions generals del 2016, el 2019 i "
             "el 2023, comparat amb el resultat oficial."),
            **ctx)
        write(DIST / canonical.strip("/") / "index.html", html)
    return len(ctx["rated"]) + len(ctx["others"])
