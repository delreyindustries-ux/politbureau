"""Pagina "Qui governa el mon" (21/11/2026): mapa dels caps de govern per familia
politica (governs.py) i quina part de la poblacio i del PIB del mon governa
cadascuna. Fent clic a un pais se'n canvia la familia i els totals es mouen."""
from __future__ import annotations

import json

from . import i18n
from .build import DIST, WEB
from .render import render_page, write

CATS = [
    (-3, "#8b0000", "Extrema esquerra", "Extrema izquierda"),
    (-2, "#d7191c", "Esquerra", "Izquierda"),
    (-1, "#f07c6c", "Centreesquerra", "Centroizquierda"),
    (0, "#c9b23f", "Centre", "Centro"),
    (1, "#6fa8dc", "Centredreta", "Centroderecha"),
    (2, "#1f5fbf", "Dreta", "Derecha"),
    (3, "#0b2a6f", "Extrema dreta", "Extrema derecha"),
]
NOPOS = ("#8e8e8e", "Partit sense posició a Wikidata", "Partido sin posición en Wikidata")
NOPARTY = ("#bdbdbd", "Sense partit (independent, militar, monarca)", "Sin partido (independiente, militar, monarca)")


def _paths() -> dict:
    """{codi numeric: path SVG} del mapa del mon, equirectangular i lleuger."""
    w = json.loads((WEB / "world.json").read_text(encoding="utf-8"))
    q = w["q"]
    out = {}
    for f in w["f"]:
        if "-" in f["c"]:
            continue
        d = []
        for j, r in enumerate(f["r"]):
            ls = (f.get("l") or [""] * len(f["r"]))[j]
            x = y = 0
            pts = []
            for i in range(len(r) // 2):
                x += r[2 * i]
                y += r[2 * i + 1]
                lv = (ord(ls[i]) - 48) if ls else 0
                if lv <= 1:
                    pts.append((x / q, y / q))
            if len(pts) >= 3:
                d.append("M" + "L".join(f"{(lon + 180) * 2.5:.1f},{(85 - lat) * 2.5:.1f}" for lon, lat in pts) + "Z")
        if d:
            out[f["c"].zfill(3)] = "".join(d)
    return out


def governs_page(env, cfg) -> int:
    from .. import governs
    from .pages import _fdate
    g = governs.load()
    if not g.get("countries"):
        return 0
    paths = _paths()
    rows = {}
    for num, c in g["countries"].items():
        if "head" not in c:
            continue
        cat = c["score"] if c.get("score") is not None else ("np" if c.get("party") else "nx")
        head = c["head"] if not (c["head"][:1] == "Q" and c["head"][1:].isdigit()) else None
        rows[num] = {"n": c["name"], "h": head, "p": c.get("party"), "k": cat,
                     "pop": c.get("pop") or 0, "gdp": c.get("gdp") or 0, "d": bool(c.get("doubt")),
                     "path": paths.get(num, "")}
    cats = [{"k": k, "color": col, "ca": ca, "es": es} for k, col, ca, es in CATS]
    cats += [{"k": "np", "color": NOPOS[0], "ca": NOPOS[1], "es": NOPOS[2]},
             {"k": "nx", "color": NOPARTY[0], "ca": NOPARTY[1], "es": NOPARTY[2]}]
    payload = json.dumps({"rows": rows, "cats": cats}, ensure_ascii=False,
                         separators=(",", ":")).replace("<", "\\u003c")
    for lang in i18n.LANGS:
        canonical = i18n.page_url("governs", lang)
        html = render_page(
            env, cfg, "governs.html.j2", lang, canonical,
            {lg: i18n.page_url("governs", lg) for lg in i18n.LANGS},
            ("Quién gobierna el mundo: cada jefe de gobierno por familia política" if lang == "es"
             else "Qui governa el món: cada cap de govern per família política"),
            ("Mapa de los jefes de gobierno de cada país por la posición de su partido, y qué parte de "
             "la población y la economía del mundo gobierna cada familia." if lang == "es" else
             "Mapa dels caps de govern de cada país per la posició del seu partit, i quina part de la "
             "població i l'economia del món governa cada família."),
            payload=payload, computed=g.get("computed"), n=len(rows), fdate=_fdate)
        write(DIST / canonical.strip("/") / "index.html", html)
    return len(rows)
