"""Pagina "Perfils de votants" (21/11/2026): config/perfils.json (perfils.py).

La pagina general es pinta al navegador (web/perfils.js) a partir de les dades
que porta incrustades: tria un partit i veu on te vots a l'abast; tria un
col·lectiu i veu la seva fitxa.

Fitxa de cada partit (22/11/2026, demanat per l'Alfonso: "fes-ho personalitzat
per a cada partit d'Espanya; sobretot com poden adaptar el seu discurs i
propostes a cada votant sabent quins temes els interessen"): una pagina
estatica per partit amb
  * el retrat dels seus votants i dels que te a l'abast, comparats amb tot
    Espanya o, als partits d'una comunitat, amb la seva comunitat;
  * per a cada grup (edat, sexe, estudis, feina, classe, ingressos, municipi
    i, des del 23/11/2026, perfils concrets, origen, nacionalitat, religio,
    ideologia i l'eix nacional), de que parlen els votants a l'abast, quant
    mes que la mitjana, quines propostes del CIS hi tenen mes suport i
    propostes concretes del cataleg (propostes.py) per als seus temes;
  * el cataleg de propostes concretes per tema, en l'orientacio del partit;
  * els temes i les propostes "pont": on els votants a l'abast pensen diferent
    dels seus votants;
  * on es juga els escons al model (llei d'Hondt sobre la projeccio).
Tot son agregats del CIS. L'avis del Reglament (UE) 2024/900 hi es a cada fitxa.
"""
from __future__ import annotations

import json

from .. import db, parties, propostes
from ..perfils import MIN_SUB, OUT
from . import i18n
from .build import DIST, ELECTION
from .render import render_page, write

SPECIAL = {"UND": {"name": {"ca": "Indecisos", "es": "Indecisos"}, "color": "#bdbdbd"},
           "OTH": {"name": {"ca": "Altres partits", "es": "Otros partidos"}, "color": "#9e9e9e"},
           "ABS": {"name": {"ca": "Abstenció", "es": "Abstención"}, "color": "#e0e0e0"},
           "BLANK": {"name": {"ca": "Blanc o nul", "es": "Blanco o nulo"}, "color": "#eeeeee"},
           "NONE": {"name": {"ca": "Cap", "es": "Ninguno"}, "color": "#e0e0e0"}}
# Fitxes: els partits del CIS (perfils.FOCUS) i CC, que te diputat pero no
# prou mostra (nomes el model).
SLUG = {"PP": "pp", "PSOE": "psoe", "VOX": "vox", "SUMAR": "frente-amplio", "PODEMOS": "podemos",
        "SALF": "se-acabo-la-fiesta", "ERC": "erc", "EHB": "eh-bildu", "JUNTS": "junts", "PNV": "pnv",
        "BNG": "bng", "AA": "adelante-andalucia", "CC": "coalicion-canaria"}
# Al CIS, el codi SUMAR es la resposta "Sumar" (i "Frente Amplio", IU).
CIS_NAME = {"SUMAR": "Frente Amplio (Sumar)"}
NEAR = 3.0          # punts: escons "en joc" al model
# Preguntes que son propostes (les altres son preocupacions o confianca).
PROPOSALS = {"viv_desah", "viv_prorroga", "viv_temporada", "viv_fons", "viv_ibi", "viv_propietaris",
             "viv_inquilins", "viv_turistics", "viv_indefinits", "viv_ico", "viv_iva", "viv_dret",
             "vulnerables", "fronteres", "papa_immig", "pacte_clima"}
LIFT_GAP = 3.0      # punts sobre la mitjana per dir que una proposta "hi destaca"


def _de(word, es):
    """'de' o "d'" davant d'un mot en catala."""
    if es:
        return "de " + word
    w = word.lower()
    return ("d'" if w[:1] in "aeiouàèéíòóú" or (w[:1] == "h" and w[1:2] in "aeiouàèéíòóú") else "de ") + word


def _meta(codes):
    meta = {}
    for c in sorted(codes):
        if c in SPECIAL:
            meta[c] = SPECIAL[c]
            continue
        m = parties.meta(c, "ES", ELECTION)
        name = "Sumar" if c == "SUMAR" else m["name"]
        meta[c] = {"name": {"ca": name, "es": name}, "color": m["color"]}
    return meta


# ------------------------------------------------------------------ model
def _seat_stakes():
    """{partit: {"seats", "share", "win": [...], "lose": [...]}} amb la projeccio
    per provincia: llei d'Hondt amb el llindar del 3 %, i els punts (i vots,
    amb el vot valid del 2023) que li falten per al seguent esco o que te de
    marge abans de perdre l'ultim, la resta quiets."""
    from ..build import magnitudes_for
    from ..geo import fetch as geo
    conn = db.connect()
    prov = {}
    for r in conn.execute("SELECT code, party, share FROM projection WHERE election_id = ? AND level = 'province'",
                          (ELECTION,)):
        prov.setdefault(r["code"], {})[r["party"]] = r["share"]
    if not prov:
        return {}
    try:
        mags = magnitudes_for(conn, ELECTION, "congreso-2023")
    except Exception:                                   # noqa: BLE001
        return {}
    valid = {r[0]: r[1] or 0 for r in conn.execute(
        "SELECT code, MAX(valid_votes) FROM election_result WHERE election = 'congreso-2023' AND level = 'province' "
        "GROUP BY code")}
    names = geo.names("ES", "province")
    nat = dict(conn.execute("SELECT party, share FROM aggregate WHERE election_id = ? AND scope_code = ''",
                            (ELECTION,)).fetchall())
    out = {}
    for code, s in prov.items():
        m = mags.get(code)
        if not m:
            continue
        ok = {p: v for p, v in s.items() if v >= 3.0}
        # Empat de quocients: el guanya qui te mes vots (com model/seats.py).
        q = [(x[0], x[2]) for x in sorted(((v / d, v, p) for p, v in ok.items() for d in range(1, m + 1)),
                                         reverse=True)]
        won = {}
        for _, p in q[:m]:
            won[p] = won.get(p, 0) + 1
        for p, v in s.items():
            if v < 1.0:
                continue
            k = won.get(p, 0)
            others = [x for x in q if x[1] != p]
            tgt = others[m - k - 1][0] if 0 <= m - k - 1 < len(others) else 0.0
            need = max(tgt * (k + 1) - v, 3.0 - v if v < 3.0 else 0.0)
            rec = out.setdefault(p, {"seats": 0, "share": nat.get(p), "win": [], "lose": []})
            rec["seats"] += k
            row = {"code": code, "name": names.get(code, code), "share": round(v, 1), "seats": k, "m": m}
            # Ja te tots els escons de la circumscripcio (Melilla): no n'hi ha cap mes.
            if k < m and need <= NEAR:
                rec["win"].append({**row, "pts": round(need, 2), "tie": need < 0.02,
                                   "votes": round(need / 100 * valid.get(code, 0), -2)})
            if k:
                nxt = others[m - k][0] if m - k < len(others) else 0.0
                lose = v - nxt * k
                if lose <= NEAR:
                    rec["lose"].append({**row, "pts": round(lose, 2), "tie": lose < 0.02,
                                        "votes": round(lose / 100 * valid.get(code, 0), -2)})
    for rec in out.values():
        rec["win"].sort(key=lambda r: r["pts"])
        rec["lose"].sort(key=lambda r: r["pts"])
    return out


# ------------------------------------------------------------------ fitxa
def _fmt(x, dec=1):
    if x is None:
        return "–"
    return f"{x:.{dec}f}".replace(".", ",")


def _people(n, es):
    if not n:
        return "0"
    if n >= 1e6:
        return _fmt(n / 1e6) + (" millones" if es else " milions")
    return f"{round(n / 1000):,}".replace(",", ".") + " mil"


def _party_view(p, d, meta, stakes, lang):
    """Tot el que surt a la fitxa d'un partit, ja calculat i en l'idioma."""
    L, es = lang, lang == "es"
    ops = {o["k"]: o for o in d["ops"]}
    scope = (d.get("scopes") or {}).get(p)
    base = scope["total"] if scope else d["total"]
    dims = scope["dims"] if scope else [x for x in d["dims"] if x["key"] in d.get("segment_dims", [])]
    where = scope["label"][L] if scope else ("España" if es else "Espanya")
    rec = (base.get("parties") or {}).get(p) or {}
    enough = (rec.get("n_voters") or 0) >= MIN_SUB
    nm = lambda k: (meta.get(k) or {}).get("name", {}).get(L, k)          # noqa: E731
    col = lambda k: (meta.get(k) or {}).get("color", "#999")               # noqa: E731
    view = {"code": p, "where": where, "de_where": _de(where, es), "scoped": bool(scope), "enough": enough,
            "n_scope": scope["n"] if scope else d["n"], "rec": rec}

    # Indicadors
    view["kpis"] = [k for k in [
        (_fmt(rec.get("share")) + " %", ("del voto declarado en " if es else "del vot declarat a ") + where) if enough else None,
        (_people(rec.get("reach_people"), es), ("votantes a su alcance" if es else "votants a l'abast") +
         f" ({_fmt(rec.get('reach'))} %)") if rec.get("n_reach") else None,
        (_fmt(rec.get("loyal")) + " %", "de sus votantes de 2023 lo repetirían" if es else
         "dels seus votants del 2023 el repetirien") if rec.get("loyal") is not None else None,
        (_fmt(rec.get("sure_voters")) + " %", "de sus votantes irá seguro a votar" if es else
         "dels seus votants anirà segur a votar") if rec.get("sure_voters") is not None else None,
    ] if k]

    # D'on venen i on van
    flow = lambda xs: [{"name": nm(x["k"]), "color": col(x["k"]), "p": x["p"]} for x in xs or []]  # noqa: E731
    view["from"], view["risk"], view["went"] = flow(rec.get("from")), flow(rec.get("risk")), flow(rec.get("went"))

    # Retrat: votants, a l'abast i la mitjana de l'ambit
    who_v, who_r, who_t = rec.get("who_voters") or {}, rec.get("who_reach") or {}, base.get("who") or {}
    view["portrait"] = [{"l": c["l"][L], "v": who_v.get(c["k"]), "r": who_r.get(c["k"]), "t": who_t.get(c["k"])}
                        for c in d["compose"]]
    view["portrait"] = [{"l": "Edad media" if es else "Edat mitjana", "v": rec.get("age_voters"),
                         "r": rec.get("age_reach"), "t": base.get("age"), "unit": ""}] + view["portrait"]
    view["portrait_full"] = [{"title": x["title"][L], "cells": [{"l": c["l"][L], "v": c["v"], "r": c["r"], "t": c["t"]}
                                                               for c in x["cells"]]}
                             for x in rec.get("portrait") or []]

    # Temes: votants i a l'abast, amb el pes a l'ambit
    all_iss = {s["k"]: s["p"] for s in base.get("issues") or []}
    iv = {s["k"]: s for s in rec.get("issues_voters") or []}
    ir = {s["k"]: s for s in rec.get("issues") or []}
    keys = list(dict.fromkeys(list(ir) + list(iv)))
    view["issues"] = sorted([{"l": (ir.get(k) or iv.get(k))["l"][L], "v": (iv.get(k) or {}).get("p"),
                              "r": (ir.get(k) or {}).get("p"), "t": all_iss.get(k)} for k in keys],
                            key=lambda x: -(x["r"] or x["v"] or 0))
    imax = max([x["v"] or 0 for x in view["issues"]] + [x["r"] or 0 for x in view["issues"]] + [1])
    for x in view["issues"]:
        x["wv"], x["wr"] = round(100 * (x["v"] or 0) / imax), round(100 * (x["r"] or 0) / imax)

    # Propostes "pont": on els votants a l'abast en donen mes (o menys) suport
    # que els seus votants
    ov, orr, ot = rec.get("ops_voters") or {}, rec.get("ops_reach") or {}, base.get("ops") or {}
    rows = []
    for k, o in ops.items():
        if k not in ov or k not in PROPOSALS:
            continue
        gap = orr[k] - ov[k] if k in orr else None
        rows.append({"l": o["l"][L], "block": d["blocks"][o["b"]][L], "v": ov[k], "r": orr.get(k), "t": ot.get(k),
                     "gap": gap})
    view["ops"] = rows
    view["bridge"] = sorted([r for r in rows if r["gap"] is not None and r["gap"] >= 5], key=lambda r: -r["gap"])[:4]
    view["wedge"] = sorted([r for r in rows if r["gap"] is not None and r["gap"] <= -5], key=lambda r: r["gap"])[:4]
    view["consensus"] = sorted([r for r in rows if r["r"] is not None and r["r"] >= 70 and r["v"] >= 70],
                               key=lambda r: -min(r["r"], r["v"]))[:4]

    # Grups: com adaptar el discurs. Propostes que hi destaquen: les que el grup
    # sencer recolza almenys LIFT_GAP punts mes que la mitjana de l'ambit (mes
    # mostra que nomes els votants a l'abast, que poques vegades arriben a 50
    # respostes per pregunta); al costat, el suport entre els seus votants a
    # l'abast quan n'hi ha prou.
    segs = []
    for dm in dims:
        for g in dm["groups"]:
            gr = (g.get("parties") or {}).get(p) or {}
            if (gr.get("n_reach") or 0) < MIN_SUB:
                continue
            gops, gall = gr.get("ops_reach") or {}, g.get("ops") or {}
            props = sorted(([ops[k]["l"][L], v, v - ot[k], gops.get(k)]
                            for k, v in gall.items() if k in PROPOSALS and k in ot and v - ot[k] >= LIFT_GAP),
                           key=lambda x: -x[2])[:3]
            # Propostes concretes: els temes on els seus votants a l'abast
            # pesen mes que la mitjana (×), i les del tipus de grup.
            tr, tt = gr.get("topics_r") or {}, base.get("topics") or {}
            hot = sorted([t for t, v in tr.items() if v >= 8 and tt.get(t)],
                         key=lambda t: -(tr[t] / tt[t]) * min(1.0, tr[t] / 15))
            conc = propostes.for_group(p, L, hot[:6], propostes.tags_for(g["id"], d.get("persona_tags")))
            for c in conc:
                tp = next((t for t in hot if c["topic"] and propostes.TOPICS[t][0 if L == "ca" else 1] == c["topic"]), None)
                c["p"] = tr.get(tp) if tp else None
                c["lift"] = round(tr[tp] / tt[tp], 2) if tp and tt.get(tp) else None
            segs.append({
                "conc": conc,
                "key": dm["key"], "label": g["label"][L], "dim": dm["title"][L], "n": gr["n_reach"],
                "reach": gr.get("reach"), "people": gr.get("reach_people") or 0,
                "people_s": _people(gr.get("reach_people"), es), "share": gr.get("share"),
                "loyal": gr.get("loyal"),
                "from": flow(gr.get("from"))[:2],
                "issues": [{"l": s["l"][L], "p": s["p"], "lift": s.get("lift")} for s in (gr.get("issues") or [])[:4]],
                "props": [{"l": a, "p": b, "gap": c, "reach": e} for a, b, c, e in props],
                "small": gr["n_reach"] < 100,
            })
    segs.sort(key=lambda x: -x["people"])
    view["segments"] = segs
    # Primer, sexe x edat: vuit grups que no se solapen i cobreixen tothom.
    # Despres, els altres grups (sense "sexe", que ja hi es) on te mes gent a l'abast.
    view["seg_main"] = [x for x in segs if x["key"] == "sexage"]
    # Despres, per families de grups (23/11/2026): perfils concrets, origen,
    # eix nacional, religio i ideologia, i la resta.
    fams = [("persona", ("Perfiles concretos", "Perfils concrets"), ("persona",), True),
            ("origin", ("Origen y nacionalidad", "Origen i nacionalitat"), ("origin2", "migr", "origin", "natio"), True),
            ("national", ("Eje nacional", "Eix nacional"), ("national",), True),
            ("ideology", ("Ideología", "Ideologia"), ("ideology",), False),
            ("religion", ("Religión", "Religió"), ("religion",), False),
            ("other", ("Estudios, trabajo, clase, ingresos y municipio", "Estudis, feina, classe, ingressos i municipi"),
             ("age", "studies", "work", "employ", "job", "class", "income", "civil", "town"), False)]
    view["seg_fams"] = [{"key": k, "title": t[0] if es else t[1], "open": op,
                         "cards": [x for x in segs if x["key"] in keys]} for k, t, keys, op in fams]
    view["seg_fams"] = [f for f in view["seg_fams"] if f["cards"]]
    view["seg_more"] = []
    # Lectura en una frase per a cada grup
    for sgm in segs:
        hot = [x for x in sgm["issues"] if x["lift"] and x["lift"] >= 1.15] or sgm["issues"][:1]
        bits = []
        if hot:
            j = " y " if es else " i "
            first = hot[0]["l"].lower()
            words = j.join(f"<b>{x['l'].lower()}</b>" for x in hot[:2])
            bits.append(("Hablarles de " + words) if es else
                        ("Parlar-los " + ("d'" if _de(first, False).startswith("d'") else "de ") + words))
        if sgm["props"]:
            pr = sgm["props"][0]
            bits.append((f"la propuesta que más destaca en el grupo: «{pr['l']}» ({_fmt(pr['p'])} %, +{_fmt(pr['gap'])} sobre la media)" if es else
                         f"la proposta que més hi destaca: «{pr['l']}» ({_fmt(pr['p'])} %, +{_fmt(pr['gap'])} sobre la mitjana)"))
        sgm["read"] = "; ".join(bits)

    # Resum en una frase
    summ = []
    if segs:
        top = (view["seg_main"] or segs)[:3]
        summ.append(("Donde tiene más votantes a su alcance: " if es else "On té més votants a l'abast: ") +
                    ", ".join(f"<b>{x['label'].lower()}</b> ({x['people_s']})" for x in top) + ".")
    if view["from"]:
        f0 = view["from"][0]
        summ.append((f"Los votantes que puede ganar votan hoy sobre todo a {f0['name']} ({_fmt(f0['p'])} %)." if es else
                     f"Els votants que pot guanyar voten avui sobretot {f0['name']} ({_fmt(f0['p'])} %).")
                    if f0["name"] not in ("Indecisos",) else
                    (f"Los votantes que puede ganar son sobre todo indecisos ({_fmt(f0['p'])} %)." if es else
                     f"Els votants que pot guanyar són sobretot indecisos ({_fmt(f0['p'])} %)."))
    if view["risk"]:
        r0 = view["risk"][0]
        summ.append((f"Si pierde votantes, se van sobre todo a {r0['name']} ({_fmt(r0['p'])} % de los que tienen segunda opción)." if es else
                     f"Si perd votants, se'n van sobretot a {r0['name']} ({_fmt(r0['p'])} % dels qui tenen segona opció)."))
    gap_iss = sorted([x for x in view["issues"] if x["v"] is not None and x["r"] is not None and abs(x["r"] - x["v"]) >= 3],
                     key=lambda x: -(x["r"] - x["v"]))
    if gap_iss and gap_iss[0]["r"] - gap_iss[0]["v"] >= 3:
        g0 = gap_iss[0]
        summ.append((f"A los que puede ganar les preocupa más que a los suyos: <b>{g0['l'].lower()}</b> ({_fmt(g0['r'])} % frente a {_fmt(g0['v'])} %)." if es else
                     f"Als que pot guanyar els preocupa més que als seus: <b>{g0['l'].lower()}</b> ({_fmt(g0['r'])} % davant {_fmt(g0['v'])} %)."))
    if view["bridge"]:
        b0 = view["bridge"][0]
        summ.append((f"Y apoyan más: «{b0['l']}» (+{_fmt(b0['gap'])} puntos sobre sus votantes)." if es else
                     f"I donen més suport a: «{b0['l']}» (+{_fmt(b0['gap'])} punts sobre els seus votants)."))
    view["summary"] = summ

    # Cataleg de propostes per tema (23/11/2026): totes les del partit, amb
    # quant esmenten el tema els seus votants i els que te a l'abast.
    tv, trr, tall = rec.get("topics_v") or {}, rec.get("topics_r") or {}, base.get("topics") or {}
    cat = propostes.catalog(p, L)
    view["catalog"] = sorted([{"key": t, "l": propostes.TOPICS[t][0 if L == "ca" else 1], "v": tv.get(t), "r": trr.get(t),
                               "t": tall.get(t), "props": props} for t, props in cat.items()],
                             key=lambda x: -((x["r"] or 0) + (x["v"] or 0) + 0.01 * (x["t"] or 0)))
    view["n_catalog"] = sum(len(x["props"]) for x in view["catalog"])

    # Model
    st = stakes.get(p) or {}
    view["model"] = {"seats": st.get("seats"), "share": st.get("share"), "win": st.get("win", [])[:8],
                     "lose": st.get("lose", [])[:8]}
    return view


def party_pages(env, cfg, d, meta):
    stakes = _seat_stakes()
    pages = [p for p in list(d["focus"]) + ["CC"] if p in SLUG]
    urls = {lang: [] for lang in i18n.LANGS}
    links = {lang: [] for lang in i18n.LANGS}
    for lang in i18n.LANGS:
        base = i18n.page_url("profiles", lang)
        for p in pages:
            m = parties.meta(p, "ES", ELECTION)
            links[lang].append({"code": p, "name": m["name"], "color": m["color"], "url": base + SLUG[p] + "/"})
    allmeta = dict(meta)
    for p in pages:
        if p not in allmeta:
            m = parties.meta(p, "ES", ELECTION)
            allmeta[p] = {"name": {"ca": m["name"], "es": m["name"]}, "color": m["color"]}
    for p in pages:
        m = parties.meta(p, "ES", ELECTION)
        for lang in i18n.LANGS:
            es = lang == "es"
            canonical = i18n.page_url("profiles", lang) + SLUG[p] + "/"
            v = _party_view(p, d, allmeta, stakes, lang)
            name = m["name"]
            title = (f"{name}: quién le vota, qué le preocupa y cómo hablar a cada grupo" if es else
                     f"{name}: qui el vota, què el preocupa i com parlar a cada grup")
            desc = (f"Perfil de los votantes de {name} y de los que tiene a su alcance en {v['where']}: temas, "
                    f"propuestas que conectan con cada grupo y escaños en juego. Con las entrevistas del CIS." if es else
                    f"Perfil dels votants de {name} i dels que té a l'abast a {v['where']}: temes, propostes que "
                    f"connecten amb cada grup i escons en joc. Amb les entrevistes del CIS.")
            html = render_page(env, cfg, "perfil-partit.html.j2", lang, canonical,
                               {lg: i18n.page_url("profiles", lg) + SLUG[p] + "/" for lg in i18n.LANGS},
                               title, desc, v=v, name=name, color=m["color"], cis_name=CIS_NAME.get(p, name),
                               d=d, links=links[lang], fmt=_fmt)
            write(DIST / canonical.strip("/") / "index.html", html)
            urls[lang].append(canonical)
    cfg.setdefault("_extra_urls", {})
    for lang, us in urls.items():
        cfg["_extra_urls"].setdefault(lang, []).extend(us)
    return links


def perfils_page(env, cfg) -> int:
    try:
        d = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    if not d.get("dims"):
        return 0
    codes = set(d["focus"])
    for g in [d["total"]] + [g for dim in d["dims"] for g in dim["groups"]]:
        codes |= set(g["vote"]) | set(g.get("direct", {})) | set(g.get("recall", {})) | set(g.get("close", {}))
        for rec in g["parties"].values():
            codes |= {x["k"] for x in rec.get("from", []) + rec.get("risk", []) + rec.get("went", [])}
    for sc in (d.get("scopes") or {}).values():
        for rec in sc["total"]["parties"].values():
            codes |= {x["k"] for x in rec.get("from", []) + rec.get("risk", []) + rec.get("went", [])}
    meta = _meta(codes)
    links = party_pages(env, cfg, d, meta)
    # La pagina general no porta el que nomes fan servir les fitxes (les
    # opinions per grup i els ambits de comunitat): pesaria tres vegades mes.
    light = {k: v for k, v in d.items() if k != "scopes"}
    light["dims"] = [{**dm, "groups": [{**{k: v for k, v in g.items() if k != "topics"}, "parties": {p: {k: v for k, v in r.items() if k not in ("ops_reach", "topics_r")}
                                                         for p, r in g["parties"].items()}}
                                       for g in dm["groups"]]} for dm in d["dims"]]
    payload = json.dumps({"d": light, "meta": meta}, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
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
            payload=payload, d=d, links=links[lang])
        write(DIST / canonical.strip("/") / "index.html", html)
    return sum(len(x["groups"]) for x in d["dims"])
