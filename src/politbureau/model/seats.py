"""Repartiment d'escons i projeccio territorial.

Dues peces independents:

  * `dhondt`  -- la regla que fa servir Espanya a cada circumscripcio.
  * `swing`   -- projecta el resultat d'avui sobre un territori concret partint
                 del resultat REAL de l'ultima eleccio en aquell territori.

Sobre el swing: si el PP puja de 33 a 38 punts a escala estatal, no vol dir que
pugi 5 punts a tot arreu. El model proporcional reparteix el creixement segons
la forca previa de cada partit a cada municipi, cosa que evita l'absurd de donar
percentatges negatius alla on un partit gairebe no existia.
"""
from __future__ import annotations


def dhondt(votes: dict, seats: int, threshold: float = 0.03) -> dict:
    """Reparteix `seats` escons entre partits segons els vots rebuts.

    `threshold` es la barrera sobre vot valid de la circumscripcio (3% a Espanya).
    """
    valid = sum(votes.values())
    if not valid or seats <= 0:
        return {party: 0 for party in votes}

    running = {p: v for p, v in votes.items() if v / valid >= threshold}
    result = {p: 0 for p in votes}
    if not running:
        return result

    for _ in range(seats):
        winner = max(running, key=lambda p: (votes[p] / (result[p] + 1), votes[p]))
        result[winner] += 1
    return result


# El swing es una divisio, i dividir per un numero minuscul fa esclatar el
# resultat. Adelante Andalucia va treure el 0,037% estatal el 2023 i les
# enquestes li donen l'1%: el factor surt 26,8 i el model l'acabava fent
# guanyar Cadis. Aquests dos guardians ho impedeixen.
MIN_BASE = 0.5          # per sota, el denominador es soroll i no s'aplica cap factor
MIN_FACTOR, MAX_FACTOR = 0.2, 5.0


def proportional_swing(baseline: dict, national_now: dict, national_before: dict,
                       report: dict | None = None) -> dict:
    """Projecta un territori.

    `baseline`        -- % real de cada partit en aquell territori a l'ultima eleccio
    `national_before` -- % real de cada partit al conjunt del pais a la mateixa eleccio
    `national_now`    -- % que li donen les enquestes d'avui

    Cada partit es multiplica pel seu factor nacional (ara / abans) i despres es
    reescala el territori perque torni a sumar 100. Si `report` es un diccionari,
    s'hi anoten els partits que s'han hagut de frenar, per poder-ho auditar.
    """
    projected = {}
    for party, before_local in baseline.items():
        now = national_now.get(party)
        before = national_before.get(party)
        if now is None or not before or before < MIN_BASE:
            # Sense equivalent nacional (regionalistes) o amb una base massa
            # petita per mesurar-ne el moviment: val mes deixar-lo quiet que
            # moure'l a cegues.
            projected[party] = before_local
            if report is not None and now is not None and before and before < MIN_BASE:
                report.setdefault("frozen", set()).add(party)
        else:
            raw = now / before
            factor = min(max(raw, MIN_FACTOR), MAX_FACTOR)
            if report is not None and factor != raw:
                report.setdefault("clamped", set()).add(party)
            projected[party] = before_local * factor

    # Partits nous que no existien a l'ultima eleccio en aquell territori.
    for party, now in national_now.items():
        if party not in projected and not national_before.get(party):
            projected[party] = now

    total = sum(projected.values())
    if not total:
        return projected
    return {p: round(v * 100.0 / total, 2) for p, v in projected.items()}


def allocate(shares_by_constituency: dict, magnitudes: dict,
             threshold: float = 0.03) -> tuple[dict, dict]:
    """Reparteix una cambra sencera circumscripcio per circumscripcio.

    Retorna (total_per_partit, per_circumscripcio). Es important fer-ho aixi i
    no repartir els 350 escons d'un sol cop a escala estatal: la llei d'Hondt
    aplicada a 52 circumscripcions petites premia molt els partits grans i els
    territorialment concentrats, i castiga els que tenen un vot repartit. Un
    repartiment estatal donaria a Sumar el doble d'escons dels que treu.
    """
    totals: dict[str, int] = {}
    detail: dict[str, dict[str, int]] = {}
    for code, shares in shares_by_constituency.items():
        seats = magnitudes.get(code)
        if not seats:
            continue
        got = dhondt(shares, seats, threshold)
        detail[code] = {p: n for p, n in got.items() if n}
        for party, n in got.items():
            if n:
                totals[party] = totals.get(party, 0) + n
    return dict(sorted(totals.items(), key=lambda kv: -kv[1])), detail


def quotient_table(shares: dict, magnitude: int, threshold: float = 0.03,
                   extra: int = 5) -> dict:
    """La taula de divisors: com es reparteix la circumscripcio, escó per escó.

    La llei d'Hondt divideix els vots de cada partit per 1, 2, 3... i dona els
    escons als quocients mes alts. Ensenyar aquesta taula es la manera honesta de
    respondre "quants vots falten": el partit que ve al darrere necessita que el
    seu seguent quocient superi el de l'ultim escó repartit, i aixo es una resta.

    Retorna {'won': [...], 'next': [...], 'cutoff': quocient_de_l_ultim_escó}.
    Cada fila porta el partit, el divisor, el quocient i, per a les que es queden
    fora, quants vots li faltarien.
    """
    valid = sum(shares.values())
    if not valid or magnitude <= 0:
        return {"won": [], "next": [], "cutoff": None, "threshold_share": 0}

    floor = valid * threshold
    running = {p: v for p, v in shares.items() if v >= floor}

    rows = []
    for party, votes in running.items():
        for divisor in range(1, magnitude + extra + 1):
            rows.append({"party": party, "divisor": divisor,
                         "quotient": votes / divisor})
    rows.sort(key=lambda r: -r["quotient"])

    won = rows[:magnitude]
    cutoff = won[-1]["quotient"] if won else 0.0

    # Dels que es queden fora nomes interessa, per a cada partit, el seu MILLOR
    # quocient: els altres son escons encara mes lluny i nomes farien soroll.
    seen, following = set(), []
    for row in rows[magnitude:]:
        if row["party"] in seen:
            continue
        seen.add(row["party"])
        needed = cutoff * row["divisor"] - shares.get(row["party"], 0)
        following.append({**row, "needed": max(needed, 0.0)})
        if len(following) >= extra:
            break

    # Partits que ni tan sols arriben al llindar del 3%. Tenen DUES barreres:
    # primer el llindar i despres el quocient de l'ultim escó. Comptar nomes la
    # primera els posaria enganyosament a prop -- a Soria un partit del 0,9%
    # semblaria mes a prop d'un escó que Soria Ya, que hi va pel 18,8%.
    for party, votes in shares.items():
        if party in running or votes < 0.05 or len(following) >= extra + 3:
            continue
        following.append({"party": party, "divisor": 1, "quotient": votes,
                          "needed": max(floor - votes, cutoff - votes),
                          "below_threshold": True})

    following.sort(key=lambda r: r["needed"])
    return {"won": won, "next": following, "cutoff": cutoff,
            "threshold_share": floor}


def _shift(shares: dict, party: str, delta: float) -> dict:
    """Dona `delta` punts a `party` traient-los proporcionalment de la resta.

    Es important treure'ls i no afegir-los i prou: si el total creixes, tots els
    quocients es mourien alhora i el resultat no voldria dir res. Aixo modela el
    que passa de veritat, que es que un partit guanya vots a costa dels altres.
    """
    out = dict(shares)
    out[party] = out.get(party, 0.0) + delta
    rest = sum(v for p, v in shares.items() if p != party)
    if rest <= 0:
        return out
    for p, v in shares.items():
        if p != party:
            out[p] = max(0.0, v - delta * v / rest)
    return out


def _seats_of(shares, party, magnitude, threshold):
    return dhondt(shares, magnitude, threshold).get(party, 0)


def margin_to_change(shares: dict, party: str, magnitude: int, direction: int,
                     threshold: float = 0.03, precision: float = 0.005,
                     limit: float = 40.0) -> float | None:
    """Punts percentuals que li falten a `party` per guanyar (+1) o perdre (-1) un escó.

    Es resol per cerca binaria sobre el desplacament de vot i no amb una formula
    tancada: la llei d'Hondt no es continua i, quan un partit puja, els altres
    baixen i els seus quocients tambe es mouen. Provar-ho de debo es exacte.
    """
    base = _seats_of(shares, party, magnitude, threshold)
    target = base + direction
    if target < 0 or target > magnitude:
        return None

    def reaches(delta):
        moved = _shift(shares, party, delta * direction)
        got = _seats_of(moved, party, magnitude, threshold)
        return got >= target if direction > 0 else got <= target

    if not reaches(limit):
        return None                      # no passa ni movent 40 punts
    lo, hi = 0.0, limit
    while hi - lo > precision:
        mid = (lo + hi) / 2
        if reaches(mid):
            hi = mid
        else:
            lo = mid
    return round(hi, 2)


def sensitivity(shares: dict, magnitude: int, threshold: float = 0.03,
                votes_total: int | None = None) -> list:
    """Quant li falta a cada partit per moure un escó en aquesta circumscripció.

    Retorna, per partit: escons actuals, i quants punts (i quants vots, si es
    coneix el cens de vots vàlids) hauria de guanyar per sumar-ne un o perdre per
    quedar-se'n un menys.
    """
    allocation = dhondt(shares, magnitude, threshold)
    out = []
    for party, share in sorted(shares.items(), key=lambda kv: -kv[1]):
        if share < 0.05:
            continue
        seats = allocation.get(party, 0)
        gain = margin_to_change(shares, party, magnitude, +1, threshold)
        lose = margin_to_change(shares, party, magnitude, -1, threshold) if seats else None
        row = {"party": party, "share": round(share, 2), "seats": seats,
               "gain_points": gain, "lose_points": lose}
        if votes_total:
            row["gain_votes"] = int(round(gain * votes_total / 100)) if gain is not None else None
            row["lose_votes"] = int(round(lose * votes_total / 100)) if lose is not None else None
        out.append(row)
    return out


def winner(shares: dict):
    """Partit mes votat i marge sobre el segon. El mapa acoloreix amb el primer
    i fa servir el marge per graduar la intensitat."""
    if not shares:
        return None, 0.0
    ranked = sorted(shares.items(), key=lambda kv: -(kv[1] or 0))
    top = ranked[0]
    margin = top[1] - (ranked[1][1] if len(ranked) > 1 else 0)
    return top[0], round(margin, 2)
