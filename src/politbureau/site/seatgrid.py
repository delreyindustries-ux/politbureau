"""Repartiment d'un cop d'ull (21/11/2026): les 52 circumscripcions en un mapa
de caselles, cada esco un quadret del color del partit, l'ultim esco marcat i
qui l'hi disputa.

La casella de cada provincia va mes o menys on es al mapa (LAYOUT: columna i
fila d'una graella d'11 x 9; les Canaries a baix a l'esquerra, com als mapes
de l'INE). El calcul es el de la llei: d'Hondt amb el 3 % del vot valid de la
provincia; el marge es el mateix que el del simulador (web/sandbox.js,
lastSeat): els punts que haurien de passar del qui te l'ultim esco al primer
que es queda fora perque canvies de mans.
"""
from __future__ import annotations

# codi INE: (columna, fila, abreviatura)
LAYOUT = {
    "15": (1, 0, "ACO"), "27": (2, 0, "LUG"), "33": (3, 0, "AST"), "39": (4, 0, "CAN"), "48": (5, 0, "BIZ"),
    "20": (6, 0, "GIP"),
    "36": (1, 1, "PON"), "32": (2, 1, "OUR"), "24": (3, 1, "LEO"), "34": (4, 1, "PAL"), "09": (5, 1, "BUR"),
    "01": (6, 1, "ARA"), "31": (7, 1, "NAV"), "22": (8, 1, "HUE"), "25": (9, 1, "LLE"), "17": (10, 1, "GIR"),
    "49": (3, 2, "ZAM"), "47": (4, 2, "VLL"), "42": (5, 2, "SOR"), "26": (6, 2, "RIO"), "50": (7, 2, "ZAR"),
    "43": (9, 2, "TAR"), "08": (10, 2, "BCN"),
    "37": (3, 3, "SAL"), "05": (4, 3, "AVI"), "40": (5, 3, "SEG"), "19": (6, 3, "GUA"), "44": (7, 3, "TER"),
    "12": (8, 3, "CAS"), "07": (10, 3, "BAL"),
    "10": (3, 4, "CAC"), "45": (4, 4, "TOL"), "28": (5, 4, "MAD"), "16": (6, 4, "CUE"), "46": (7, 4, "VAL"),
    "06": (3, 5, "BAD"), "13": (4, 5, "CRE"), "02": (6, 5, "ALB"), "03": (7, 5, "ALA"),
    "21": (2, 6, "HVA"), "41": (3, 6, "SEV"), "14": (4, 6, "CÓR"), "23": (5, 6, "JAE"), "30": (6, 6, "MUR"),
    "11": (3, 7, "CAD"), "29": (4, 7, "MAL"), "18": (5, 7, "GRA"), "04": (6, 7, "ALM"),
    "35": (0, 8, "LPA"), "38": (1, 8, "TFE"), "51": (3, 8, "CEU"), "52": (5, 8, "MEL"),
}
COLS, ROWS = 11, 9


def last_seat(shares: dict, seats: int, threshold: float = 3.0):
    """Repartiment d'Hondt d'una provincia i la lluita per l'ultim esco.
    Retorna (escons {partit: n}, info) o (escons, None) si no hi ha rival."""
    run = {k: v for k, v in shares.items() if v and v >= threshold}
    won = {k: 0 for k in run}
    last = None
    for _ in range(seats):
        if not run:
            break
        k = max(run, key=lambda p: (run[p] / (won[p] + 1), run[p]))
        last = (k, run[k] / (won[k] + 1), won[k] + 1)
        won[k] += 1
    won = {k: n for k, n in won.items() if n}
    if not last:
        return won, None
    lk, lq, ld = last
    rivals = sorted(((p, run[p] / (won.get(p, 0) + 1), won.get(p, 0) + 1) for p in run if p != lk),
                    key=lambda x: -x[1])
    info = {"last": lk}
    if rivals:
        rk, _rq, rd = rivals[0]
        info.update(rival=rk, transfer=max(0.0, (rd * run[lk] - ld * run[rk]) / (ld + rd)))
    # Un partit per sota del llindar que se l'enduria si el passes
    cut = sorted((p for p, v in shares.items() if v and v < threshold and v > lq), key=lambda p: -shares[p])
    if cut:
        info["cut"] = cut[0]
    return won, info


def build(sim: dict, meta, order, threshold: float = 3.0):
    """sim: simulator_for(...) (amb les "constituencies"); meta(partit) ->
    {name, color}; order(partit) -> posicio a l'eix esquerra-dreta."""
    cons = (sim or {}).get("constituencies") or (sim or {}).get("cons") or []
    tiles, close = [], []
    for c in cons:
        pos = LAYOUT.get(c["code"])
        if not pos:
            continue
        won, info = last_seat(c["now"], c["magnitude"], threshold)
        seq = []
        for p in sorted(won, key=order):
            seq += [p] * won[p]
        last_idx = None
        if info:
            # El quadret marcat: l'ultim del partit que s'endu l'ultim esco.
            idx = [i for i, p in enumerate(seq) if p == info["last"]]
            last_idx = idx[-1] if idx else None
        t = {"code": c["code"], "name": c["name"], "abbr": pos[2], "col": pos[0] + 1, "row": pos[1] + 1,
             "m": c["magnitude"], "seq": [{"p": p, "c": meta(p)["color"]} for p in seq], "last_idx": last_idx,
             "info": None}
        if info and info.get("rival"):
            tr = info["transfer"]
            votes = round(tr * (c.get("valid") or 0) / 100) if c.get("valid") else None
            t["info"] = {"last": meta(info["last"])["name"], "last_c": meta(info["last"])["color"],
                         "rival": meta(info["rival"])["name"], "rival_c": meta(info["rival"])["color"],
                         "tr": tr, "votes": votes, "hot": tr < 0.5}
            close.append(t)
        tiles.append(t)
    close.sort(key=lambda t: t["info"]["tr"])
    return {"tiles": tiles, "cols": COLS, "rows": ROWS, "close": close[:8],
            "max_m": max((t["m"] for t in tiles), default=1)}
