"""Pagina dels resultats historics de les generals, 1977-2023 (pla de ruta,
pilar 2). Nomes llegeix config/history_es.json, que fa `politbureau historic`.
"""
from __future__ import annotations

import json

from .. import history
from . import i18n
from .build import DIST
from .render import render_page, write

W, H, L, R, T, B = 720, 300, 34, 12, 12, 26      # grafic d'evolucio (viewBox)


def context():
    data = history.load()
    if not data or not data.get("elections"):
        return None
    els = data["elections"]
    n = len(els)
    x = lambda i: L + (W - L - R) * i / (n - 1)
    top = 50.0
    y = lambda v: T + (H - T - B) * (1 - v / top)
    fams = []
    for f in data["families"]:
        pts = []
        for i, e in enumerate(els):
            v = sum(p["share"] for p in e["parties"] if p.get("family") == f["key"])
            pts.append((i, v) if v > 0 else None)
        # trams seguits: un partit que desapareix no baixa a zero, s'acaba
        segs, cur = [], []
        for pt in pts + [None]:
            if pt:
                cur.append(pt)
            elif cur:
                segs.append(cur)
                cur = []
        path = " ".join("M" + "L".join(f"{x(i):.1f} {y(v):.1f}" for i, v in seg) for seg in segs)
        dots = [{"x": round(x(i), 1), "y": round(y(v), 1), "v": v, "year": els[i]["date"][:4]}
                for seg in segs for i, v in seg]
        last = max((pt for pt in pts if pt), key=lambda pt: pt[0], default=None)
        if dots:
            fams.append({**f, "path": path, "dots": dots,
                         "lx": round(x(last[0]) + 4, 1), "ly": round(y(last[1]) + 3, 1)})
    rows = []
    for e in reversed(els):
        first = e["parties"][0]
        maj = e["seats"] // 2 + 1
        rows.append({**e, "year": e["date"][:4], "first": first, "majority": maj,
                     "absolute": first["seats"] >= maj,
                     "bar": [{"name": p["name"], "color": p["color"], "seats": p["seats"]}
                             for p in e["parties"] if p["seats"]]})
    from .pages import _fdate, _fmt
    return {"fmt": _fmt, "fdate": _fdate, "elections": rows, "families": fams,
            "computed": data["computed"],
            "chart": {"w": W, "h": H, "l": L, "r": W - R, "b": H - B,
                      "grid": [{"v": v, "y": round(y(v), 1)} for v in (0, 10, 20, 30, 40, 50)],
                      "ticks": [{"x": round(x(i), 1), "year": e["date"][:4],
                                 # les dues del 2019: abril i novembre
                                 "label": e["date"][2:4] + ({"04": "A", "11": "N"}[e["date"][5:7]]
                                                            if e["date"][:4] == "2019" else "")}
                                for i, e in enumerate(els)]}}


def historic_page(env, cfg):
    ctx = context()
    if not ctx:
        return 0
    for lang in i18n.LANGS:
        canonical = i18n.page_url("history", lang)
        html = render_page(
            env, cfg, "historic.html.j2", lang, canonical,
            {lg: i18n.page_url("history", lg) for lg in i18n.LANGS},
            ("Resultados de las elecciones generales en España, 1977-2023" if lang == "es"
             else "Resultats de les eleccions generals a Espanya, 1977-2023"),
            ("Votos, porcentajes, escaños y participación de las 16 elecciones generales desde 1977, "
             "con la evolución de cada partido." if lang == "es" else
             "Vots, percentatges, escons i participació de les 16 eleccions generals des del 1977, "
             "amb l'evolució de cada partit."),
            **ctx)
        write(DIST / canonical.strip("/") / "index.html", html)
    # El mateix, a l'API de dades obertes.
    data = history.load()
    api = DIST / "api" / "v1"
    api.mkdir(parents=True, exist_ok=True)
    (api / "generals-historic.json").write_bytes(json.dumps(
        {"licence": {"name": "CC BY-SA 4.0", "url": "https://creativecommons.org/licenses/by-sa/4.0/",
                     "attribution": "Polit Bureau (politbureau.es), amb dades de Wikipedia"},
         "computed": data["computed"], "elections": data["elections"]},
        ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return len(ctx["elections"])
