"""Simulador electoral obert (21/11/2026): mou el vot i mira on van els escons.

Demanat per l'Alfonso: les funcionalitats d'un simulador electoral interactiu
que Polit Bureau no tenia. Aqui:

  * el vot de cada partit a tot Espanya, amb lliscadors;
  * el vot comunitat per comunitat (la resta d'Espanya no es mou);
  * dues bases de partida: la mitjana d'avui o el resultat del 2023;
  * el Congres reparteix escons provincia per provincia (d'Hondt, 3 %), amb
    el mapa de qui guanya cada provincia i l'hemicicle;
  * una nit electoral: les provincies van entrant per tandes i es veu com
    s'omple la cambra;
  * un enllac per compartir l'escenari.

NO es una previsio: es una eina per entendre com el sistema converteix vots en
escons. El calcul el fa el navegador (web/sandbox.js) amb les mateixes dades
del simulador de coalicions (build.simulator_for): el % real del 2023 i el de
la projeccio d'avui a cada provincia. El canvi de cada partit es reparteix amb
swing proporcional, com a la projeccio de la web.
"""
from __future__ import annotations

import json
import math

from .. import parties
from ..forecast import BLOCS
from . import i18n
from .build import DIST, ELECTION, ROOT, simulator_for
from .render import render_page, write

GEO = None
# Punts de partida historics (21/11/2026): resultat real de cada provincia.
# Comprovat: amb aquests % i la llei d'Hondt surten exactament els escons reals
# de les 52 provincies a les quatre eleccions.
HISTORIC = (("y2016", "congreso-2016"), ("y2019a", "congreso-2019a"), ("y2019n", "congreso-2019n"))


def _historic() -> dict:
    """{capa: {provincia: {"m": escons, "s": {partit: % del vot valid}}}} i, a
    "_labels", les sigles de cada codi provisional en aquella eleccio."""
    from ..ingest import infoelectoral as ie
    out, labels = {}, {}
    for layer, proc in HISTORIC:
        try:
            tipo, y, m = ie.PROCESSES[proc]
            zf = ie.download(proc)
            cons = ie.constituencies(zf, tipo, y, m)
            munis = ie.municipalities(zf, tipo, y, m)
            sig = ie.candidacies(zf, tipo, y, m)
        except Exception as exc:                          # noqa: BLE001
            print(f"      avis: {proc} no disponible ({type(exc).__name__})")
            continue
        blank = {}
        for c, mm in munis.items():
            blank[c[:2]] = blank.get(c[:2], 0) + mm["blank"]
        layer_out = {}
        for prov, e in cons.items():
            votes = {}
            for cand, (v, _s) in e["parties"].items():
                code = parties.resolve(sig.get(cand, cand), "ES")[0] or f"?{cand}"
                votes[code] = votes.get(code, 0) + v
                if code.startswith("?") or code == "SUMAR":
                    best = labels.setdefault(layer, {}).get(code)
                    if not best or v > best[1]:
                        labels[layer][code] = (sig.get(cand, cand), v)
            valid = sum(votes.values()) + blank.get(prov, 0)
            if valid:
                layer_out[prov] = {"m": e["seats"],
                                   "s": {k: round(100.0 * v / valid, 3) for k, v in votes.items() if v}}
        out[layer] = layer_out
    out["_labels"] = {lay: {k: v[0] for k, v in d.items()} for lay, d in labels.items()}
    return out


def _province_paths(root) -> dict:
    """{codi: path SVG} de les provincies, a partir del TopoJSON del lloc.
    Projeccio equirectangular corregida pel cosinus de la latitud; les Canaries
    es pugen a una caixa a baix a l'esquerra, com als mapes de l'INE."""
    topo = json.loads((root / "data" / "geo" / "es.json").read_text(encoding="utf-8"))
    t = topo["transform"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * t["scale"][0] + t["translate"][0], y * t["scale"][1] + t["translate"][1]))
        arcs.append(pts)
    k = math.cos(math.radians(40))

    def proj(lon, lat):
        if lat < 30:                                    # Canaries
            lon, lat = lon + 7.5, lat + 7.0
        return ((lon + 10.0) * k * 60, (44.2 - lat) * 60)

    def ring(idx):
        out = []
        for i in idx:
            pts = arcs[i] if i >= 0 else list(reversed(arcs[~i]))
            out.extend(pts if not out else pts[1:])
        return out

    paths = {}
    for g in topo["objects"]["provinces"]["geometries"]:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        d = []
        for poly in polys:
            for r in poly:
                pts = [proj(*p) for p in ring(r)]
                # Simplificacio: fora punts a menys de 0,6 px de l'anterior.
                keep, last = [], None
                for p in pts:
                    if last is None or abs(p[0] - last[0]) + abs(p[1] - last[1]) > 0.6:
                        keep.append(p)
                        last = p
                if len(keep) >= 3:
                    d.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in keep) + "Z")
        paths[g["id"]] = "".join(d)
    return paths


TURNOUT_SHOW = (55, 60, 65, 75, 80)


def _turnout_data():
    """config/participacio.json (politbureau participacio), si existeix."""
    f = ROOT / "config" / "participacio.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except ValueError:
        return None


def _turnout_payload():
    d = _turnout_data()
    if not d or not d.get("factors"):
        return None
    c = d.get("classic")
    return {"ref": d["ref"], "max": d["max"], "factors": d["factors"],
            "classic": {"slope": c["slope"], "left": c["left"], "right": c["right"]} if c else None}


def _turnout_view(meta):
    d = _turnout_data()
    if not d or not d.get("factors"):
        return None
    show = [t for t in TURNOUT_SHOW if str(t) in d["factors"]]
    order = sorted(d["n_party"], key=lambda p: -d["n_party"][p])
    return {"ref": d["ref"], "q_ref": d["q_ref"], "n": d["n"], "studies": d["studies"], "source": d["source"],
            "classic": d.get("classic"),
            "show": show,
            "parties": [{"name": (meta.get(p) or {}).get("name", p), "color": (meta.get(p) or {}).get("color", "#999"),
                         "n": d["n_party"][p], "f": [d["factors"][str(t)].get(p, 1) for t in show]} for p in order]}


def sandbox_page(env, cfg, data, root=ROOT, conn=None) -> int:
    sim = simulator_for(data, "national", "ES")
    if not sim:
        return 0
    region_of = data["region_of"]["province"]
    provs = []
    for c in sim.get("constituencies") or sim.get("cons") or []:
        provs.append({"c": c["code"], "n": c["name"], "r": region_of.get(c["code"]),
                      "m": c["magnitude"], "v": c.get("valid") or 0,
                      "real": c["real"], "now": c["now"]})
    if not provs:
        return 0
    hist = _historic()
    labels = hist.pop("_labels", {})
    labels["real"] = {"SUMAR": "Sumar"}
    for p in provs:
        p["mm"] = {}
        for layer, by in hist.items():
            got = by.get(p["c"])
            if got:
                p[layer] = got["s"]
                p["mm"][layer] = got["m"]
    # Partits amb lliscador: els que tenen almenys un 0,8 % estatal en alguna de
    # les dues capes, o algun esco. La resta compten igual (son "altres").
    tot_v = sum(p["v"] for p in provs) or 1
    nat = {}
    layers = ["now", "real"] + list(hist)
    for layer in layers:
        for p in provs:
            for party, s in p[layer].items():
                nat.setdefault(layer, {}).setdefault(party, 0.0)
                nat[layer][party] += s * p["v"] / tot_v
    # Els historics es ponderen amb el vot valid del 2023: la diferencia amb el
    # pes real d'aquell any es petita i aqui nomes serveix per als lliscadors.
    # Partits amb lliscador, per a cada punt de partida: els que hi tenen
    # almenys un 0,8 % estatal.
    main = {layer: sorted([party for party, s in nat.get(layer, {}).items()
                           if s >= 0.8 and party != "OTHER"], key=lambda x: -nat[layer][x])
            for layer in layers}
    meta = {}
    for party in {k for layer in nat.values() for k in layer}:
        m = parties.meta(party, "ES", ELECTION)
        meta[party] = {"name": m["name"], "color": m["color"], "pos": parties.position(party, "ES")}
    regions = {}
    for p in provs:
        if p["r"]:
            regions[p["r"]] = data["names"]["region"].get(p["r"], p["r"])
    paths = _province_paths(root)
    payload = {"provinces": provs, "main": main, "meta": meta, "layers": layers, "labels": labels,
               "regions": dict(sorted(regions.items(), key=lambda kv: kv[1])),
               "blocs": {k: list(v) for k, v in BLOCS.items()}, "seats": 350, "majority": 176,
               "votes": True,      # p.v = vot valid del 2023: els marges es poden passar a vots
               "turnout": _turnout_payload(),
               "paths": {p["c"]: paths.get(p["c"], "") for p in provs}}
    js = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    try:
        links = regional_pages(env, cfg, conn, data["names"]) if conn is not None else []
    except Exception as exc:                              # noqa: BLE001
        print(f"      avis: simuladors autonomics no generats ({type(exc).__name__}: {exc})")
        links = []
    try:
        flinks = foreign_pages(env, cfg, conn) if conn is not None else []
    except Exception as exc:                              # noqa: BLE001
        print(f"      avis: simuladors estrangers no generats ({type(exc).__name__}: {exc})")
        flinks = []
    for lang in i18n.LANGS:
        canonical = i18n.page_url("sandbox", lang)
        html = render_page(
            env, cfg, "sandbox.html.j2", lang, canonical,
            {lg: i18n.page_url("sandbox", lg) for lg in i18n.LANGS},
            ("Simulador electoral: mueve el voto y mira dónde van los escaños" if lang == "es"
             else "Simulador electoral: mou el vot i mira on van els escons"),
            ("Cambia el voto de cada partido en toda España o comunidad por comunidad y mira el "
             "reparto del Congreso provincia por provincia, con noche electoral incluida." if lang == "es"
             else "Canvia el vot de cada partit a tot Espanya o comunitat per comunitat i mira el "
             "repartiment del Congrés província per província, amb nit electoral inclosa."),
            payload=js, turnout=_turnout_view(meta),
            regional_links=[{"url": x["url"][lang], "name": x["name"][lang]} for x in links],
            foreign_links=[{"url": x["url"][lang], "name": x["name"][lang]} for x in flinks])
        write(DIST / canonical.strip("/") / "index.html", html)
    return len(provs)


# ---------------------------------------------------------------- autonomiques
# Simulador obert de cada parlament autonomic amb circumscripcions (21/11/2026).
# Pes de cada circumscripcio: el cens electoral de la provincia (config/cens) on
# la circumscripcio es una provincia. A Asturies i a les Balears (comarques i
# illes) es dedueix de la taula de Wikipedia: els pesos que reprodueixen el total
# de la comunitat (error maxim de 0,08 punts). Canaries queda fora: la doble
# llista (illa i regional) no es pot simular amb aquestes dades.
PROVINCE_CODE = {
    "Barcelona": "08", "Girona": "17", "Lleida": "25", "Tarragona": "43", "Alicante": "03",
    "Castellón": "12", "Valencia": "46", "Almería": "04", "Cádiz": "11", "Córdoba": "14",
    "Granada": "18", "Huelva": "21", "Jaén": "23", "Málaga": "29", "Seville": "41", "Huesca": "22",
    "Teruel": "44", "Zaragoza": "50", "A Coruña": "15", "Lugo": "27", "Ourense": "32",
    "Pontevedra": "36", "Albacete": "02", "Ciudad Real": "13", "Cuenca": "16", "Guadalajara": "19",
    "Toledo": "45", "Álava": "01", "Biscay": "48", "Gipuzkoa": "20",
}
DISTRICT_NAME = {"Central": ("Central", "Central"), "Eastern": ("Oriental", "Oriental"),
                 "Western": ("Occidental", "Occidental")}
SKIP = {"sub-es-cn"}


def _census() -> dict:
    import csv
    out = {}
    path = ROOT / "config" / "cens" / "es-general.csv"
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["level"] == "province":
                out[r["code"]] = int(r["total"])
    return out


def _weights(base) -> list[float]:
    """Pesos de cada circumscripcio que millor reprodueixen el total de la
    comunitat (minims quadrats). Python pur: la publicacio no te numpy."""
    ds = base["districts"]
    parts = sorted(set(base["total"]))
    A = [[d["shares"].get(p, 0.0) for d in ds] for p in parts]
    y = [base["total"][p] for p in parts]
    k = len(ds)
    # Equacions normals (A'A) w = A'y, resoltes per Gauss amb pivot.
    M = [[sum(A[r][i] * A[r][j] for r in range(len(A))) for j in range(k)]
         + [sum(A[r][i] * y[r] for r in range(len(A)))] for i in range(k)]
    for c in range(k):
        piv = max(range(c, k), key=lambda r: abs(M[r][c]))
        M[c], M[piv] = M[piv], M[c]
        if abs(M[c][c]) < 1e-12:
            return [1.0 / k] * k
        for r in range(k):
            if r != c:
                f = M[r][c] / M[c][c]
                M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    w = [max(M[i][k] / M[i][i], 1e-3) for i in range(k)]
    t = sum(w)
    return [x / t for x in w]


def regional_pages(env, cfg, conn, names) -> list[dict]:
    from .. import regional
    from ..model import seats as seatlib
    from .pages import abroad_elections
    els = abroad_elections()
    census = _census()
    done = []
    for eid, base in regional.load().items():
        e = els.get(eid)
        ch = (e or {}).get("chamber") or {}
        if eid in SKIP or not e or not ch.get("districts"):
            continue
        ren = ch.get("rename") or {}

        def r_(d):
            out = {}
            for p, v in d.items():
                out[ren.get(p, p)] = out.get(ren.get(p, p), 0) + v
            return out
        before = r_(base["total"])
        avg = dict(conn.execute("SELECT party, share FROM aggregate WHERE election_id = ? AND scope_code = ''",
                                (eid,)).fetchall())
        avg = {p: v for p, v in avg.items() if p != "OTHER" and v}
        codes = [PROVINCE_CODE.get(d["name"]) for d in base["districts"]]
        weights = ([census.get(c, 0) for c in codes] if all(codes) and all(census.get(c) for c in codes)
                   else [round(x * 1e6) for x in _weights(base)])
        provs = []
        for d, c, w in zip(base["districts"], codes, weights):
            real = r_(d["shares"])
            now = seatlib.proportional_swing(real, avg, before) if avg else real
            nm = names["province"].get(c) if c else None
            label = DISTRICT_NAME.get(d["name"])
            provs.append({"c": c or d["name"], "n": nm or (label[0] if label else d["name"]),
                          "r": None, "m": d["seats"], "v": w, "real": real,
                          "now": {p: round(v, 3) for p, v in now.items() if v > 0}, "mm": {}})
        layers = ["now", "real"]
        tot_v = sum(p["v"] for p in provs) or 1
        nat = {layer: {} for layer in layers}
        for layer in layers:
            for p in provs:
                for party, s in p[layer].items():
                    nat[layer][party] = nat[layer].get(party, 0) + s * p["v"] / tot_v
        main = {layer: sorted([k for k, s in nat[layer].items() if s >= 0.8 and k != "OTHER"],
                              key=lambda k: -nat[layer][k]) for layer in layers}
        meta = {}
        for party in {k for layer in nat.values() for k in layer}:
            m = parties.meta(party, "ES", eid)
            meta[party] = {"name": m["name"], "color": m["color"], "pos": parties.position(party, "ES")}
        payload = {"provinces": provs, "main": main, "meta": meta, "layers": layers, "labels": {},
                   "regions": {}, "paths": {}, "seats": ch["seats"], "majority": ch["seats"] // 2 + 1,
                   "thr": {"d": ch.get("district_threshold", ch.get("threshold", 0.03)) * 100,
                           "r": (ch.get("region_threshold") * 100 if ch.get("region_threshold") else None),
                           "scope": ch.get("threshold_scope", "district"),
                           "rt": ch.get("threshold", 0.03) * 100},
                   "base_year": base["base"][:4]}
        js = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
        pub = e["pub"]
        for lang in i18n.LANGS:
            slug = pub[lang]
            canonical = f"/{lang}/{i18n.page_url('sandbox', lang).strip('/').split('/', 1)[1]}/{slug}/"
            place = pub["name_es"] if lang == "es" else pub["name_ca"]
            html = render_page(
                env, cfg, "sandbox.html.j2", lang, canonical,
                {lg: f"/{lg}/{i18n.page_url('sandbox', lg).strip('/').split('/', 1)[1]}/{pub[lg]}/"
                 for lg in i18n.LANGS},
                (f"Simulador electoral de {place}: mueve el voto y mira los escaños" if lang == "es"
                 else f"Simulador electoral de {place}: mou el vot i mira els escons"),
                (f"Cambia el voto de cada partido y mira el reparto del {ch['name']} "
                 "circunscripción por circunscripción." if lang == "es" else
                 f"Canvia el vot de cada partit i mira el repartiment del {ch['name']} "
                 "circumscripció per circumscripció."),
                payload=js, regional={"place": place, "chamber": ch["name"], "year": base["base"][:4],
                                      "seats": ch["seats"], "url": f"/{lang}/" + (
                                          ("encuestas-" if lang == "es" else "enquestes-") + slug) + "/"})
            write(DIST / canonical.strip("/") / "index.html", html)
        done.append({"eid": eid,
                     "url": {lg: f"/{lg}/{i18n.page_url('sandbox', lg).strip('/').split('/', 1)[1]}/{pub[lg]}/"
                             for lg in i18n.LANGS},
                     "name": {"es": pub["name_es"], "ca": pub["name_ca"]}})
    return sorted(done, key=lambda x: x["name"]["ca"])


# ---------------------------------------------------------------- estrangers
# Simulador obert dels parlaments estrangers proporcionals (21/11/2026). Es
# reparteix a escala de tot el pais amb el metode i el llindar de la llei, com
# l'estimacio de la pagina de cada pais: alla on la llei reparteix per
# circumscripcions (Portugal, Polonia...) es una aproximacio i la pagina ho diu.
POSITION_ORDER = {"extrema esquerra": -3, "esquerra": -2, "centreesquerra": -1, "centre": 0,
                  "centredreta": 1, "dreta": 2, "extrema dreta": 3}
METHOD_TEXT = {
    "dhondt": ("la ley d'Hondt", "la llei d'Hondt"),
    "sainte_lague": ("el método Sainte-Laguë", "el mètode Sainte-Laguë"),
    "hare": ("el resto mayor (cuota Hare)", "la resta més gran (quota Hare)"),
    "droop": ("el resto mayor (cuota Hagenbach-Bischoff)", "la resta més gran (quota Hagenbach-Bischoff)"),
}


def foreign_pages(env, cfg, conn) -> list[dict]:
    from .pages import abroad_data, abroad_elections
    done = []
    for eid, e in abroad_elections().items():
        ch = e.get("chamber") or {}
        method = "dhondt" if ch.get("method") == "proportional" else ch.get("method")
        if e.get("group") == "sub" or e["country"] == "ES" or method not in METHOD_TEXT:
            continue
        try:
            d = abroad_data(conn, eid)
        except Exception:                                  # noqa: BLE001
            d = None
        if not d or not d.get("avg") or not d.get("seats"):
            continue
        seats = ch.get("in_play") or ch["seats"]
        now = {a["code"]: a["share"] for a in d["avg"] if a["code"] != "OTHER" and a["share"]}
        meta = {}
        for a in d["avg"]:
            pos = ((a.get("ideo") or {}).get("ca") or {}).get("position")
            meta[a["code"]] = {"name": a.get("person") or a["name"], "color": a["color"],
                               "pos": POSITION_ORDER.get(pos, 999)}
        main = [a["code"] for a in d["avg"] if a["code"] != "OTHER" and (a["share"] >= 0.8 or a.get("seats"))]
        payload = {"provinces": [{"c": "ALL", "n": d["name"]["ca"], "r": None, "m": seats, "v": 1,
                                  "now": now, "mm": {}}],
                   "main": {"now": main}, "meta": meta, "layers": ["now"], "labels": {}, "regions": {},
                   "paths": {}, "seats": seats, "majority": d.get("majority") or seats // 2 + 1,
                   "method": {"name": method, "thr": (ch.get("threshold") or 0) * 100,
                              "first": ch.get("first_divisor", 1.0), "bonus": ch.get("bonus")}}
        js = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\u003c")
        pub = e["pub"]
        thr = ch.get("threshold") or 0
        for lang in i18n.LANGS:
            es = lang == "es"
            base = i18n.page_url("sandbox", lang).strip("/").split("/", 1)[1]
            canonical = f"/{lang}/{base}/{pub[lang]}/"
            place = d["name"][lang]
            name = ch.get("name_es") if es and ch.get("name_es") else ch.get("name", "")
            html = render_page(
                env, cfg, "sandbox.html.j2", lang, canonical,
                {lg: f"/{lg}/{i18n.page_url('sandbox', lg).strip('/').split('/', 1)[1]}/{pub[lg]}/"
                 for lg in i18n.LANGS},
                (f"Simulador electoral de {place}: mueve el voto y mira los escaños" if es
                 else f"Simulador electoral de {place}: mou el vot i mira els escons"),
                (f"Cambia el voto de cada partido y mira cómo se reparten los {seats} escaños de {name}."
                 if es else f"Canvia el vot de cada partit i mira com es reparteixen els {seats} escons de {name}."),
                payload=js, regional={"place": place, "chamber": name, "year": None, "seats": seats,
                                      "url": d["urls"][lang], "foreign": True,
                                      "method": METHOD_TEXT[method][0 if es else 1],
                                      "thr": round(thr * 100, 2), "bonus": ch.get("bonus"),
                                      "first": ch.get("first_divisor")})
            write(DIST / canonical.strip("/") / "index.html", html)
        done.append({"eid": eid, "url": {lg: f"/{lg}/{i18n.page_url('sandbox', lg).strip('/').split('/', 1)[1]}/{pub[lg]}/"
                                         for lg in i18n.LANGS},
                     "name": {"es": pub["name_es"], "ca": pub["name_ca"]}})
    return sorted(done, key=lambda x: x["name"]["ca"])
