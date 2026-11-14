"""Previsio amb probabilitats (10/11/2026, pla de ruta, fase 1).

La mitjana d'enquestes dona UN repartiment d'escons. Pero les enquestes
s'equivoquen, i amb 52 circumscripcions petites un error de dos punts pot moure
vint escons. Aqui es simula l'eleccio moltes vegades:

1. A cada simulacio, cada partit rep un error estatal aleatori: normal amb
   desviacio `SIGMA * sqrt(p)` punts (p = la seva mitjana), aplicat en relatiu
   i amb un sostre del 25 % per als partits petits. Amb SIGMA = 0,6 un
   partit del 30 % te una desviacio de 3,3 punts i un del 7 %, d'1,6: es l'ordre
   de l'error de les mitjanes de les generals espanyoles (2023: el PP sortia
   uns 2-3 punts massa alt i el PSOE uns 3 massa baix). Es una hipotesi, no una
   mesura: es calibrara amb l'error publicat despres del 29N.
2. L'error estatal es porta a cada provincia amb el mateix swing proporcional
   que fa servir la projeccio, mes un soroll provincial propi (`LOCAL`).
3. Llei d'Hondt a cada circumscripcio, amb el llindar del 3 %.

Del conjunt en surten la mediana i l'interval del 80 % d'escons de cada
partit i la probabilitat de les majories que importen.
"""
from __future__ import annotations

import math
import random

from .model import seats as seatlib

SIGMA = 0.6        # punts per arrel de punt: error estatal
LOCAL = 0.35       # el mateix, per al soroll propi de cada provincia
CAP = 0.25         # error relatiu maxim (desviacio) dels partits petits
N_SIMS = 5000
MAJORITY = 176

# Blocs per a les probabilitats de majoria. Son sumes aritmetiques, no
# coalicions anunciades: la pagina ho diu.
BLOCS = {
    "right": ("PP", "VOX"),
    "left": ("PSOE", "SUMAR", "ERC", "EHB", "PODEMOS", "BNG", "JUNTS", "PNV", "CC"),
}


def _province_shares(conn, election_id):
    shares: dict[str, dict[str, float]] = {}
    for r in conn.execute(
            """SELECT code, party, share FROM projection
               WHERE election_id = ? AND level = 'province'""", (election_id,)):
        shares.setdefault(r["code"], {})[r["party"]] = r["share"]
    return shares


def simulate(conn, election_id="es-general", baseline="congreso-2023",
             n=N_SIMS, seed=None) -> dict | None:
    """{"parties": [...], "blocs": {...}, "n": n, "hist": {...}} o None."""
    from .build import current_national, magnitudes_for
    national = current_national(conn, election_id)
    prov = _province_shares(conn, election_id)
    mags = magnitudes_for(conn, election_id, baseline)
    if not national or not prov or not mags:
        return None
    rng = random.Random(seed)
    parties = sorted(national, key=lambda p: -national[p])
    draws = {p: [] for p in parties}
    blocs = {k: [] for k in BLOCS}
    first = {p: 0 for p in parties}
    for _ in range(n):
        factor = {}
        for p, v in national.items():
            if v <= 0:
                continue
            # Error relatiu: SIGMA/sqrt(p), amb sostre. Sense sostre, un partit
            # regional (PNV, 1 % estatal pero 25 % a Bizkaia) rebia errors del
            # 60 % i perdia tots els escons una de cada sis vegades.
            factor[p] = max(0.0, 1.0 + rng.gauss(0.0, min(CAP, SIGMA / math.sqrt(v))))
        shares = {}
        for code, s in prov.items():
            out = {}
            for p, v in s.items():
                f = factor.get(p, 1.0)
                out[p] = max(0.0, v * f + rng.gauss(0.0, LOCAL * math.sqrt(max(v, 0.0))))
            tot = sum(out.values()) or 1.0
            shares[code] = {p: v * 100.0 / tot for p, v in out.items()}
        totals, _ = seatlib.allocate(shares, mags)
        for p in parties:
            draws[p].append(totals.get(p, 0))
        for k, members in BLOCS.items():
            blocs[k].append(sum(totals.get(p, 0) for p in members))
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
    # PP sol, i PP + Vox, com a distribucio per al grafic.
    hist = {}
    for x in blocs["right"]:
        hist[x] = hist.get(x, 0) + 1
    pp_alone = sum(1 for x in draws.get("PP", []) if x >= MAJORITY) / n
    return {"n": n, "sigma": SIGMA, "local": LOCAL, "majority": MAJORITY,
            "parties": out_parties, "blocs": out_blocs, "pp_alone": pp_alone,
            "right_hist": sorted(hist.items())}


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
                     n: int = CHAMBER_SIMS, seed=None) -> dict | None:
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
        if fast:
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
