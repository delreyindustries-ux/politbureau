"""Mitjana ponderada d'enquestes.

Una enquesta d'ahir amb 4.000 entrevistes no val el mateix que una de fa dos
mesos amb 400. El pes combina dues coses:

  * recencia  -> 0.5 ** (dies_enrere / half_life_days)
  * mostra    -> sqrt(n / 1000), limitat perque una macroenquesta no domini

No s'aplica correccio per "casa" (house effect): caldria un model bayesia i,
sense saber-ho, seria pitjor el remei que la malaltia. Aixo es documenta al
README com a limitacio coneguda.
"""
from __future__ import annotations

import datetime as dt
import math
import statistics


def weight(fieldwork_end: str, sample_size, today, half_life=14.0, sample_cap=3.0):
    age = (today - dt.date.fromisoformat(fieldwork_end)).days
    recency = 0.5 ** (max(age, 0) / half_life)
    size = min(math.sqrt((sample_size or 1000) / 1000.0), sample_cap)
    return recency * size


def aggregate(polls, today=None, half_life=14.0, max_age_days=90, min_sample=300):
    """`polls`: llista de dicts {fieldwork_end, sample_size, results:{party:(share,lo,hi)}}.

    Retorna {party: {share, lo, hi, seats, n_polls}}. `lo`/`hi` son la dispersio
    entre cases enquestadores (desviacio tipica ponderada), no un interval de
    confianca estadistic: mesuren fins a quin punt els instituts discrepen.
    """
    today = today or dt.date.today()
    usable = []
    for poll in polls:
        end = poll.get("fieldwork_end")
        if not end:
            continue
        if (today - dt.date.fromisoformat(end)).days > max_age_days:
            continue
        if poll.get("sample_size") and poll["sample_size"] < min_sample:
            continue
        usable.append(poll)

    if not usable:
        return {}

    buckets: dict[str, list[tuple[float, float, int | None]]] = {}
    for poll in usable:
        w = weight(poll["fieldwork_end"], poll.get("sample_size"), today, half_life)
        for party, (share, seats_lo, seats_hi) in poll["results"].items():
            if share is None:
                continue
            seats = None
            if seats_lo is not None:
                seats = (seats_lo + (seats_hi if seats_hi is not None else seats_lo)) / 2
            buckets.setdefault(party, []).append((share, w, seats))

    out = {}
    for party, rows in buckets.items():
        total_w = sum(w for _, w, _ in rows)
        if total_w <= 0:
            continue
        mean = sum(s * w for s, w, _ in rows) / total_w
        if len(rows) > 1:
            var = sum(w * (s - mean) ** 2 for s, w, _ in rows) / total_w
            spread = math.sqrt(var)
        else:
            spread = 0.0
        seat_values = [sv for _, _, sv in rows if sv is not None]
        out[party] = {
            "share": round(mean, 2),
            "lo": round(max(mean - spread, 0.0), 2),
            "hi": round(mean + spread, 2),
            "seats": round(statistics.median(seat_values)) if seat_values else None,
            "n_polls": len(rows),
        }
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["share"]))


def normalise(shares: dict, target=100.0):
    """Reescala els percentatges perque sumin `target`. Les mitjanes de diverses
    enquestes gairebe mai sumen 100 exacte, i el mapa necessita proporcions netes."""
    total = sum(v for v in shares.values() if v)
    if not total:
        return dict(shares)
    factor = target / total
    return {k: (v * factor if v else v) for k, v in shares.items()}
