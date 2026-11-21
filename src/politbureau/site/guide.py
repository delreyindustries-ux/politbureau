"""Guia del sistema electoral del Congres (21/11/2026).

Idea presa de les "guies de camp" dels simuladors electorals: com funciona el
sistema, amb l'aritmetica feta sobre un resultat real. Tot surt del resultat
oficial del 23/07/2023 (Ministeri de l'Interior) que ja fa servir la web:

  * quants vots valids hi ha per cada esco a cada provincia;
  * el repartiment d'Hondt pas a pas en una provincia petita (Avila, 3 escons);
  * on el llindar del 3 % canvia alguna cosa i on no.

Les regles: LOREG, arts. 162 (350 escons, 2 per provincia i 1 a Ceuta i a
Melilla, la resta per poblacio) i 163 (d'Hondt i 3 % a cada circumscripcio).
"""
from __future__ import annotations

from .. import parties
from . import i18n
from .build import DIST, ELECTION
from .render import render_page, write

EXAMPLE = "05"          # Avila: 3 escons, cinc partits amb vots seriosos
NAME_2023 = {"SUMAR": "Sumar"}   # el 2023 es presentava com a Sumar


def _name(p):
    return NAME_2023.get(p) or parties.meta(p, "ES", ELECTION)["name"]


def guide_page(env, cfg, data) -> int:
    from .pages import _fdate                                  # noqa: F401
    mags = data.get("magnitude_real") or data["magnitude"]
    rows = []
    for code, m in mags.items():
        meta = data["meta"].get(("province", code)) or {}
        valid = meta.get("valid_votes")
        if not m or not valid:
            continue
        votes = data["real"].get(("province", code)) or {}
        top = sorted(votes.items(), key=lambda kv: -kv[1])
        # Quant vot cal en aquesta provincia per entrar (el quocient de l'ultim esco).
        def dh(run):
            won = {p: 0 for p in run}
            last = None
            for _ in range(m):
                w = max(run, key=lambda p: (run[p] / (won[p] + 1), run[p]))
                last = run[w] / (won[w] + 1)
                won[w] += 1
            return {p: n for p, n in won.items() if n}, last
        with_thr, last = dh({p: v for p, v in votes.items() if v >= 0.03 * valid})
        without, _ = dh(dict(votes))
        # El llindar nomes canvia alguna cosa si sense ell un partit hauria entrat.
        lost = [_name(p) for p in without if p not in with_thr]
        rows.append({"code": code, "name": data["names"]["province"].get(code, code), "seats": m,
                     "valid": valid, "per_seat": valid / m, "last": last,
                     "last_pct": 100.0 * last / valid if last else None, "lost": lost})
        _ = top
    if not rows:
        return 0
    rows.sort(key=lambda r: r["per_seat"])
    cheapest, dearest = rows[0], rows[-1]
    # Exemple pas a pas
    ex_votes = data["real"].get(("province", EXAMPLE)) or {}
    ex_m = mags.get(EXAMPLE)
    ex_valid = (data["meta"].get(("province", EXAMPLE)) or {}).get("valid_votes") or 1
    ex_parties = [p for p, v in sorted(ex_votes.items(), key=lambda kv: -kv[1]) if v >= 0.01 * ex_valid][:6]
    cells = []
    for p in ex_parties:
        cells += [(ex_votes[p] / d, p, d) for d in range(1, ex_m + 2)]
    winners = sorted(cells, key=lambda c: -c[0])[:ex_m]
    win_set = {(p, d) for _, p, d in winners}
    example = {"name": data["names"]["province"].get(EXAMPLE, EXAMPLE), "seats": ex_m, "valid": ex_valid,
               "divs": list(range(1, ex_m + 2)),
               "rows": [{"name": _name(p),
                         "color": parties.meta(p, "ES", ELECTION)["color"], "votes": ex_votes[p],
                         "pct": 100.0 * ex_votes[p] / ex_valid,
                         "q": [{"v": ex_votes[p] / d, "win": (p, d) in win_set,
                                "order": next((i + 1 for i, (_, pp, dd) in enumerate(winners) if pp == p and dd == d), None)}
                               for d in range(1, ex_m + 2)]} for p in ex_parties]}
    big = [r for r in rows if r["seats"] >= 15]
    for lang in i18n.LANGS:
        es = lang == "es"
        canonical = i18n.page_url("guide", lang)
        html = render_page(
            env, cfg, "guide.html.j2", lang, canonical, {lg: i18n.page_url("guide", lg) for lg in i18n.LANGS},
            ("Cómo se vota al Congreso: provincias, d'Hondt y el umbral del 3 %" if es
             else "Com es vota al Congrés: províncies, d'Hondt i el llindar del 3 %"),
            ("Guía del sistema electoral del Congreso con los números de 2023: cuántos votos cuesta un escaño en "
             "cada provincia y un reparto d'Hondt paso a paso." if es else
             "Guia del sistema electoral del Congrés amb els números del 2023: quants vots costa un escó a cada "
             "província i un repartiment d'Hondt pas a pas."),
            rows=rows, cheapest=cheapest, dearest=dearest, example=example, big=big)
        write(DIST / canonical.strip("/") / "index.html", html)
    return len(rows)
