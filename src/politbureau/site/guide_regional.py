"""Guies "com es vota" dels parlaments autonomics (pla de ruta: "guies dels
altres sistemes", 25/11/2026).

Una pagina per a cada parlament amb circumscripcions (els deu de
config/regional_districts.json), feta amb el resultat real de l'ultima
eleccio, com la guia del Congres (guide.py):

  * les regles: escons, circumscripcions, llindar i on s'aplica, majoria;
  * quants electors hi ha per esco a cada circumscripcio (cens de l'INE de les
    generals, nomes on la circumscripcio es una provincia);
  * el repartiment d'Hondt pas a pas a la circumscripcio mes petita;
  * qui es queda sense esco pel llindar;
  * el mateix vot repartit en una sola circumscripcio sense llindar, i l'index
    de desproporcionalitat de Gallagher.

Dades: config/regional_districts.json (resultat de cada circumscripcio de
l'article de Wikipedia de l'eleccio, CC BY-SA 4.0) i config/chambers.yaml
(regles, seccio "Electoral system" dels mateixos articles). Es reparteix amb
els percentatges: amb una sola decimal el repartiment pot diferir en algun
esco del real; la pagina ho diu on passa.
"""
from __future__ import annotations

import math

from .. import parties
from . import i18n
from .build import DIST
from .perfils_page import _de
from .render import render_page, write

ISLAND = {"Ibiza": ("Eivissa", "Ibiza"), "Regional": ("Llista regional", "Lista regional")}
SEVILLE = {"Seville": ("Sevilla", "Sevilla"), "Biscay": ("Biscaia", "Bizkaia")}


def _dhondt(shares: dict, m: int) -> dict:
    won = {p: 0 for p in shares}
    for _ in range(m):
        if not shares:
            break
        w = max(shares, key=lambda p: (shares[p] / (won[p] + 1), shares[p]))
        won[w] += 1
    return {p: n for p, n in won.items() if n}


def _eligible(eid, ch, d, total) -> dict:
    """Partits que passen el llindar en aquesta circumscripcio."""
    thr = (ch.get("threshold") or 0) * 100
    sh = d["shares"]
    if eid == "sub-es-cn":
        if d["name"] == "Regional":
            return {p: v for p, v in sh.items() if total.get(p, 0) >= 4}
        return {p: v for p, v in sh.items() if v >= 15 or total.get(p, 0) >= 4}
    if ch.get("threshold_scope") == "region":
        return {p: v for p, v in sh.items() if total.get(p, 0) >= thr}
    return {p: v for p, v in sh.items() if v >= thr}


def _gallagher(votes: dict, seats: dict, n: int) -> float:
    keys = set(votes) | set(seats)
    return math.sqrt(sum((votes.get(k, 0) - 100.0 * seats.get(k, 0) / n) ** 2 for k in keys) / 2)


def _view(eid, base, ch, e, names, census):
    from .sandbox import DISTRICT_NAME, PROVINCE_CODE
    ren = ch.get("rename") or {}

    def r_(d):
        out = {}
        for p, v in d.items():
            out[ren.get(p, p)] = out.get(ren.get(p, p), 0) + v
        return out

    total, total_won = r_(base["total"]), r_(base.get("total_won") or {})
    n_seats = ch["seats"]
    dists = []
    for d in base["districts"]:
        d = {**d, "shares": r_(d["shares"]), "won": r_(d.get("won") or {})}
        code = PROVINCE_CODE.get(d["name"])
        lab = (DISTRICT_NAME.get(d["name"]) or ISLAND.get(d["name"]) or SEVILLE.get(d["name"]))
        name_ca = lab[0] if lab else (names.get(code) if code else d["name"])
        name_es = lab[1] if lab else (names.get(code) if code else d["name"])
        ok = _eligible(eid, ch, d, total)
        sim = _dhondt(ok, d["seats"])
        free = _dhondt(dict(d["shares"]), d["seats"])
        lost = sorted([p for p in free if free[p] > sim.get(p, 0)], key=lambda p: -d["shares"][p])
        # Quocient de l'ultim esco: el % que calia per entrar.
        qs = sorted((v / k for p, v in ok.items() for k in range(1, d["seats"] + 1)), reverse=True)
        last = qs[d["seats"] - 1] if len(qs) >= d["seats"] else None
        cen = census.get(code) if code else None
        dists.append({"name": {"ca": name_ca, "es": name_es}, "seats": d["seats"], "shares": d["shares"],
                      "won": d["won"] or sim, "sim": sim, "match": not d["won"] or sim == d["won"],
                      "lost": lost, "last": last, "census": cen,
                      "per_seat": (cen / d["seats"]) if cen else None})
    # Exemple pas a pas: la circumscripcio mes petita (de 3 escons o mes) on
    # els percentatges reprodueixen el resultat real.
    cands = sorted([x for x in dists if x["seats"] >= 3 and x["match"]], key=lambda x: x["seats"])
    ex = cands[0] if cands else None
    example = None
    if ex:
        ps = [p for p, v in sorted(ex["shares"].items(), key=lambda kv: -kv[1]) if v >= 1][:7]
        okx = _eligible(eid, ch, {"name": "", "shares": ex["shares"]}, total) if eid != "sub-es-cn" else ex["shares"]
        cells = sorted(((ex["shares"][p] / k, p, k) for p in ps if p in okx for k in range(1, ex["seats"] + 2)),
                       reverse=True)[:ex["seats"]]
        order = {(p, k): i + 1 for i, (_q, p, k) in enumerate(cells)}
        example = {"name": ex["name"], "seats": ex["seats"], "divs": list(range(1, ex["seats"] + 2)),
                   "rows": [{"code": p, "pct": ex["shares"][p], "out": p not in okx,
                             "q": [{"v": ex["shares"][p] / k, "order": order.get((p, k))}
                                   for k in range(1, ex["seats"] + 2)]} for p in ps]}
    # Una sola circumscripcio, sense llindar
    single = _dhondt({p: v for p, v in total.items() if p != "OTHER"}, n_seats)
    real = total_won or {}
    keys = sorted(set(real) | set(single), key=lambda p: -total.get(p, 0))
    compare = [{"code": p, "pct": total.get(p, 0), "real": real.get(p, 0), "single": single.get(p, 0)}
               for p in keys if real.get(p, 0) or single.get(p, 0)]
    per = [x for x in dists if x["per_seat"]]
    per.sort(key=lambda x: x["per_seat"])
    return {"eid": eid, "chamber": ch["name"], "seats": n_seats, "majority": n_seats // 2 + 1,
            "year": base["base"][:4], "thr": (ch.get("threshold") or 0) * 100,
            "scope": "cn" if eid == "sub-es-cn" else ch.get("threshold_scope", "district"),
            "districts": dists, "example": example, "compare": compare,
            "gallagher": _gallagher({p: v for p, v in total.items() if p != "OTHER"}, real, n_seats) if real else None,
            "gallagher_single": _gallagher({p: v for p, v in total.items() if p != "OTHER"}, single, n_seats),
            "cheap": per[0] if len(per) > 1 else None, "dear": per[-1] if len(per) > 1 else None,
            "mismatch": [x["name"] for x in dists if not x["match"]],
            "lost_any": [(x["name"], x["lost"]) for x in dists if x["lost"]]}


def pages(env, cfg, data) -> list[dict]:
    from .. import regional
    from .pages import abroad_elections
    from .sandbox import _census
    els = abroad_elections()
    census = _census()
    names = (data.get("names") or {}).get("province") or {}
    done = []
    for eid, base in regional.load().items():
        e = els.get(eid)
        ch = (e or {}).get("chamber") or {}
        if not e or not ch.get("districts") or not e.get("pub"):
            continue
        v = _view(eid, base, ch, e, names, census)
        pub = e["pub"]
        codes = {x["code"] for x in v["compare"]}
        for x in v["districts"]:
            codes |= set(x["shares"])
        meta = {}
        for p in codes:
            m = parties.meta(p, "ES", eid)
            nm = m["name"] if not str(m["name"]).startswith("?") else str(m["name"])[1:]
            meta[p] = {"name": nm, "color": m["color"]}
        urls = {}
        for lang in i18n.LANGS:
            urls[lang] = f"{i18n.page_url('guide', lang)}{pub[lang]}/"
        for lang in i18n.LANGS:
            es = lang == "es"
            place = pub["name_es"] if es else pub["name_ca"]
            title = (f"Cómo se vota en {place}: circunscripciones, d'Hondt y umbral" if es
                     else f"Com es vota a {place}: circumscripcions, d'Hondt i llindar")
            desc = (f"Guía del sistema electoral de {place} ({ch['name']}) con el resultado de {v['year']}: cuánto cuesta un "
                    "escaño, un reparto d'Hondt paso a paso y quién se queda fuera por el umbral." if es else
                    f"Guia del sistema electoral {_de(place, False)} ({ch['name']}) amb el resultat del {v['year']}: quant costa un "
                    "escó, un repartiment d'Hondt pas a pas i qui es queda fora pel llindar.")
            sandbox_url = f"/{lang}/{i18n.page_url('sandbox', lang).strip('/').split('/', 1)[1]}/{pub[lang]}/"
            html = render_page(env, cfg, "guide-regional.html.j2", lang, urls[lang], urls, title, desc,
                               v=v, meta=meta, place=place, sandbox_url=sandbox_url if eid != "sub-es-cn" else None,
                               polls_url=f"/{lang}/" + (("encuestas-" if es else "enquestes-") + pub[lang]) + "/")
            write(DIST / urls[lang].strip("/") / "index.html", html)
        done.append({"eid": eid, "url": urls, "name": {"es": pub["name_es"], "ca": pub["name_ca"]},
                     "chamber": ch["name"]})
    done.sort(key=lambda x: x["name"]["ca"])
    cfg.setdefault("_extra_urls", {})
    for x in done:
        for lang in i18n.LANGS:
            cfg["_extra_urls"].setdefault(lang, []).append(x["url"][lang])
    return done
