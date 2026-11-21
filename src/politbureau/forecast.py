"""Previsio amb probabilitats (10/11/2026, pla de ruta, fase 1; millorada el
21/11/2026: "millora els calculs de les simulacions").

La mitjana d'enquestes dona UN repartiment d'escons. Pero les enquestes
s'equivoquen, i amb 52 circumscripcions petites un error de dos punts pot moure
vint escons. Aqui es simula l'eleccio moltes vegades. A cada simulacio:

1. Error estatal de cada partit: normal amb desviacio `sigma * sqrt(p)` punts,
   aplicat en relatiu i amb un sostre del 25 %. `sigma` ja no es una hipotesi:
   es mesura amb l'error de la mitjana d'enquestes a l'ultima eleccio de cada
   pais que segueix la web (config/last_error.json: uns 150 partits de 26 paisos):
   arrel de la mitjana de error^2 / p. Dona 0,59 (la hipotesi era 0,6). La
   curtosi de l'error es 3,2, la d'una normal: no calen cues mes gruixudes.
   Als partits concentrats (PNB, Bildu, ERC, BNG...) p es el seu % al
   territori on es presenten, no l'estatal: abans un partit de l'1 % estatal
   rebia l'error relatiu maxim i perdia escons de franc.
   Als quatre ultims generals espanyols els errors de partits del mateix bloc
   no van en la mateixa direccio (2016: PP per sota i Cs per sobre; 2019A al
   reves), aixi que els errors son independents; la suma a 100 de cada
   provincia ja fa que el que guanya un ho perdin els altres.
2. Error de cada comunitat autonoma i de cada provincia. Calibrat amb com es
   van apartar del swing proporcional els resultats reals de 2016 a 2019A, a
   2019N i a 2023 (620 casos partit-provincia): l'apartament te una part comuna
   a tota la comunitat (REGIONAL = 0,50 punts per arrel de punt) i una propia
   de cada provincia (LOCAL = 0,27). Abans nomes hi havia la provincial, 0,35.
3. Participacio: cada simulacio sorteja la participacio (normal, centrada en
   la del 2023 i amb la desviacio de les quatre ultimes generals, TURNOUT_SD)
   i aplica com es mou cada electorat segons el model de votant probable del
   CIS (config/participacio.json, amb els factors de cada comunitat). D'aqui
   surten les probabilitats segons la participacio.
4. Llei d'Hondt a cada circumscripcio, amb el llindar del 3 %.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

from .model import seats as seatlib

ROOT = Path(__file__).resolve().parents[2]
SIGMA_DEFAULT = 0.6      # si no hi ha dades per calibrar
SIGMA = 0.59             # per a simulate_chamber (calibrat igual)
REGIONAL = 0.50          # punts per arrel de punt: error comu de la comunitat
LOCAL = 0.27             # el mateix, propi de cada provincia
CAP = 0.25               # error relatiu maxim (desviacio)
TURNOUT_SD = 2.8         # desviacio de la participacio (2016-2023: 68,7 / 74,4 / 68,5 / 69,1)
N_SIMS = 5000
MAJORITY = 176
BANDS = ((None, 65), (65, 73), (73, None))

# Blocs per a les probabilitats de majoria. Son sumes aritmetiques, no
# coalicions anunciades: la pagina ho diu.
BLOCS = {
    "right": ("PP", "VOX"),
    "left": ("PSOE", "SUMAR", "ERC", "EHB", "PODEMOS", "BNG", "JUNTS", "PNV", "CC"),
}


def calibrated_sigma():
    """(sigma, n de partits, n de paisos) a partir de config/last_error.json."""
    try:
        d = json.loads((ROOT / "config" / "last_error.json").read_text(encoding="utf-8"))["elections"]
    except (OSError, ValueError, KeyError):
        return SIGMA_DEFAULT, 0, 0
    pts, countries = [], set()
    for k, e in d.items():
        if e.get("status") != "ok":
            continue
        for r in e.get("rows", []):
            res, avg = r.get("result"), r.get("average")
            if res and res >= 1 and avg is not None:
                pts.append((avg - res) ** 2 / res)
                countries.add(k)
    if len(pts) < 30:
        return SIGMA_DEFAULT, len(pts), len(countries)
    return math.sqrt(sum(pts) / len(pts)), len(pts), len(countries)


def _turnout_model():
    try:
        return json.loads((ROOT / "config" / "participacio.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _province_shares(conn, election_id):
    shares: dict[str, dict[str, float]] = {}
    for r in conn.execute(
            """SELECT code, party, share FROM projection
               WHERE election_id = ? AND level = 'province'""", (election_id,)):
        shares.setdefault(r["code"], {})[r["party"]] = r["share"]
    return shares


def simulate(conn, election_id="es-general", baseline="congreso-2023",
             n=N_SIMS, seed=None) -> dict | None:
    """{"parties": [...], "blocs": {...}, "n": n, "by_turnout": [...], ...} o None."""
    from .build import current_national, magnitudes_for
    from .geo import regions as georegions
    national = current_national(conn, election_id)
    prov = _province_shares(conn, election_id)
    mags = magnitudes_for(conn, election_id, baseline)
    if not national or not prov or not mags:
        return None
    region_of = georegions.table()["province"]
    sigma, n_cal, n_countries = calibrated_sigma()
    tm = _turnout_model()
    rng = random.Random(seed)
    parties = sorted(national, key=lambda p: -national[p])
    # % efectiu de cada partit: al territori on es presenta (pes = escons).
    eff = {}
    for p, v in national.items():
        w_in = sum(mags.get(c, 0) for c, s in prov.items() if s.get(p, 0) > 0.5)
        w_all = sum(mags.get(c, 0) for c in prov) or 1
        terr = (sum(s.get(p, 0) * mags.get(c, 0) for c, s in prov.items() if s.get(p, 0) > 0.5) / w_in) if w_in else v
        eff[p] = max(v, terr) if w_in < 0.6 * w_all else v
    draws = {p: [] for p in parties}
    blocs = {k: [] for k in BLOCS}
    first = {p: 0 for p in parties}
    turnouts = []
    regions = sorted({region_of.get(c) for c in prov})
    ref = tm["ref"] if tm else None
    tmax = tm["max"] if tm else None
    for _ in range(n):
        factor = {p: max(0.0, 1.0 + rng.gauss(0.0, min(CAP, sigma / math.sqrt(eff[p]))))
                  for p, v in national.items() if v > 0}
        zreg = {(r, p): rng.gauss(0.0, 1.0) for r in regions for p in national}
        t = None
        if tm:
            t = min(tmax, max(50, int(round(rng.gauss(ref, TURNOUT_SD)))))
            tf_nat = tm["factors"].get(str(t), {})
        shares = {}
        for code, s in prov.items():
            r = region_of.get(code)
            tf = tf_nat if tm else {}
            if tm and r in (tm.get("regional") or {}):
                tf = {**tf_nat, **tm["regional"][r].get(str(t), {})}
            out = {}
            for p, v in s.items():
                base = v * factor.get(p, 1.0) * tf.get(p, 1.0)
                sv = math.sqrt(max(v, 0.0))
                out[p] = max(0.0, base + REGIONAL * sv * zreg.get((r, p), 0.0) + LOCAL * sv * rng.gauss(0.0, 1.0))
            tot = sum(out.values()) or 1.0
            shares[code] = {p: x * 100.0 / tot for p, x in out.items()}
        totals, _ = seatlib.allocate(shares, mags)
        for p in parties:
            draws[p].append(totals.get(p, 0))
        for k, members in BLOCS.items():
            blocs[k].append(sum(totals.get(p, 0) for p in members))
        turnouts.append(t)
        top = max(totals.items(), key=lambda kv: kv[1])[0] if totals else None
        if top in first:
            first[top] += 1

    def q(xs, a):
        ys = sorted(xs)
        return ys[min(len(ys) - 1, max(0, int(round(a * (len(ys) - 1)))))]

    out_parties = []
    for p in parties:
        xs = draws[p]
        if q(xs, 0.9) == 0:
            continue
        out_parties.append({"code": p, "median": q(xs, 0.5), "lo": q(xs, 0.1), "hi": q(xs, 0.9),
                            "first": first[p] / n,
                            "zero": sum(1 for x in xs if x == 0) / n})
    out_blocs = {k: {"median": q(xs, 0.5), "lo": q(xs, 0.1), "hi": q(xs, 0.9),
                     "majority": sum(1 for x in xs if x >= MAJORITY) / n}
                 for k, xs in blocs.items()}
    hist = {}
    for x in blocs["right"]:
        hist[x] = hist.get(x, 0) + 1
    pp_alone = sum(1 for x in draws.get("PP", []) if x >= MAJORITY) / n
    # Probabilitats segons la participacio
    by_t = []
    if tm:
        main = [p["code"] for p in out_parties[:4]]
        for lo, hi in BANDS:
            idx = [i for i, t in enumerate(turnouts) if t is not None and (lo is None or t >= lo) and (hi is None or t < hi)]
            if len(idx) < 50:
                continue
            by_t.append({"lo": lo, "hi": hi, "n": len(idx), "share": len(idx) / n,
                         "right": sum(1 for i in idx if blocs["right"][i] >= MAJORITY) / len(idx),
                         "left": sum(1 for i in idx if blocs["left"][i] >= MAJORITY) / len(idx),
                         "parties": [{"code": p, "median": q([draws[p][i] for i in idx], 0.5)} for p in main]})
    return {"n": n, "sigma": round(sigma, 3), "sigma_n": n_cal, "sigma_countries": n_countries,
            "regional": REGIONAL, "local": LOCAL, "turnout_sd": TURNOUT_SD if tm else None,
            "turnout_ref": ref, "majority": MAJORITY,
            "parties": out_parties, "blocs": out_blocs, "pp_alone": pp_alone,
            "right_hist": sorted(hist.items()), "by_turnout": by_t}


# ---------------------------------------------------- cambres proporcionals
# Previsio per a les autonomiques i per als parlaments d'altres paisos
# (15/11/2026, pla de ruta). El mateix error estatal que a les generals, sobre
# el repartiment de config/chambers.yaml. Amb poques enquestes la mitjana es
# menys fiable: la desviacio es multiplica per sqrt(1 + 1/n), que val 1,41
# amb una sola enquesta i 1,05 amb deu. Es una hipotesi, com SIGMA.
CHAMBER_SIMS = 1500


def _divisors(shares, seats, method, first_divisor):
    """D'Hondt o Sainte-Lague amb un munt: molt mes rapid que seats.apportion
    quan cal repetir-ho milers de vegades."""
    import heapq
    won = {p: 0 for p in shares}
    sl = method == "sainte_lague"
    heap = [(-v / (first_divisor if sl else 1.0), -v, p) for p, v in shares.items() if v > 0]
    heapq.heapify(heap)
    for _ in range(seats):
        if not heap:
            break
        _q, negv, p = heap[0]
        won[p] += 1
        div = (2 * won[p] + 1) if sl else (won[p] + 1)
        heapq.heapreplace(heap, (negv / div, negv, p))
    return won


def simulate_chamber(shares: dict, chamber: dict, n_polls: int = 1,
                     n: int = CHAMBER_SIMS, seed=None, project=None) -> dict | None:
    """{"parties": [{code, median, lo, hi, first, majority, zero}], "none": p}.

    `shares`: {partit: %} de la mitjana (sense "altres"); `chamber`: l'entrada
    de chambers.yaml. None si el metode no es proporcional."""
    method = chamber.get("method")
    if method == "proportional":
        method = "dhondt"
    if method not in ("dhondt", "sainte_lague", "hare", "droop"):
        return None
    seats = chamber["seats"]
    threshold = chamber.get("threshold", 0.03)
    first_divisor = chamber.get("first_divisor", 1.0)
    bonus = chamber.get("bonus")
    majority = (chamber.get("total") or seats) // 2 + 1
    base = {p: v for p, v in shares.items() if p != "OTHER" and v and v > 0}
    if len(base) < 2:
        return None
    widen = math.sqrt(1.0 + 1.0 / max(1, n_polls))
    rng = random.Random(seed)
    order = sorted(base, key=lambda p: -base[p])
    draws = {p: [] for p in order}
    first = {p: 0 for p in order}
    alone = {p: 0 for p in order}
    nobody = 0
    fast = method in ("dhondt", "sainte_lague") and not bonus
    for _ in range(n):
        sim = {p: max(0.0, v * (1.0 + rng.gauss(0.0, min(CAP, SIGMA / math.sqrt(v)) * widen)))
               for p, v in base.items()}
        if project is not None:
            # Circumscripcio per circumscripcio (regional.py, 19/11/2026).
            got = project(sim)
        elif fast:
            got = _divisors({p: v for p, v in sim.items() if v >= threshold * 100},
                            seats, method, first_divisor)
        else:
            got = seatlib.apportion(sim, seats, method, threshold, first_divisor, bonus)
        top, best = None, -1
        for p in order:
            s = got.get(p, 0)
            draws[p].append(s)
            if s > best:
                top, best = p, s
        first[top] += 1
        if best >= majority:
            alone[top] += 1
        else:
            nobody += 1

    def q(xs, a):
        ys = sorted(xs)
        return ys[min(len(ys) - 1, max(0, int(round(a * (len(ys) - 1)))))]

    rows = []
    for p in order:
        xs = draws[p]
        if q(xs, 0.9) == 0:
            continue
        rows.append({"code": p, "median": q(xs, 0.5), "lo": q(xs, 0.1), "hi": q(xs, 0.9),
                     "first": first[p] / n, "majority": alone[p] / n,
                     "in": sum(1 for x in xs if x > 0) / n})
    return {"n": n, "majority": majority, "widen": round(widen, 2), "polls": n_polls,
            "parties": rows, "none": nobody / n}
