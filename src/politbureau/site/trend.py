"""Grafic d'evolucio de les enquestes (21/11/2026).

Per a una eleccio: una linia per partit amb la mitjana d'enquestes al llarg
de l'ultim any i un punt per a cada enquesta. La mitjana de cada dia es la
mateixa regla que fa servir la web per a la d'avui, simplificada: de cada
institut, la seva enquesta mes recent dels 30 dies anteriors; despres, una
mitjana mobil de tres setmanes perque la linia no tremoli.

Tot surt dibuixat (coordenades SVG) per a la plantilla _trend.html.j2: la
pagina no necessita JavaScript per veure'l.
"""
from __future__ import annotations

import datetime as dt

from .render import visible

W, H = 720, 300
LEFT, RIGHT, TOP, BOTTOM = 34, 128, 14, 28
WINDOW = 30           # dies que compten per a la mitjana de cada dia
STEP = 7              # un punt de la linia per setmana
MAX_LINES = 8
DOT_LINES = 5         # punts de cada enquesta nomes dels cinc primers
MONTHS = {"ca": ["gen", "febr", "març", "abr", "maig", "juny", "jul", "ag", "set", "oct", "nov", "des"],
          "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]}


def _d(s):
    return dt.date.fromisoformat(str(s)[:10])


def build(conn, election_id, rows, days=365):
    """rows: la mitjana d'avui de la pagina ([{code, name, color, share}]).
    Retorna el dibuix o None si hi ha massa poques enquestes."""
    rows = [r for r in rows if r.get("code") and r["code"] != "OTHER" and (r.get("share") or 0) >= 1][:MAX_LINES]
    if not rows:
        return None
    codes = [r["code"] for r in rows]
    polls = conn.execute(
        "SELECT id, pollster, fieldwork_end FROM poll WHERE election_id = ? AND scope = 'national' "
        "AND fieldwork_end IS NOT NULL ORDER BY fieldwork_end", (election_id,)).fetchall()
    if len(polls) < 8:
        return None
    last = _d(polls[-1][2])
    start = last - dt.timedelta(days=days)
    polls = [p for p in polls if _d(p[2]) >= start - dt.timedelta(days=WINDOW)]
    if len(polls) < 8:
        return None
    ids = [p[0] for p in polls]
    shares = {}
    q = ",".join("?" * len(codes))
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        for pid, party, share in conn.execute(
                f"SELECT poll_id, party, share FROM poll_result WHERE poll_id IN ({','.join('?' * len(chunk))}) "
                f"AND party IN ({q})", (*chunk, *codes)):
            if share:                                     # 0 = no el preguntaven
                shares.setdefault(pid, {})[party] = share
    polls = [(p[0], p[1], _d(p[2])) for p in polls if p[0] in shares]
    if len(polls) < 8:
        return None
    # Mitjana de cada setmana
    days_ = []
    d = start
    while d <= last:
        days_.append(d)
        d += dt.timedelta(days=STEP)
    if days_[-1] != last:
        days_.append(last)
    series = {c: [] for c in codes}
    for day in days_:
        latest = {}
        for pid, who, end in polls:
            if day - dt.timedelta(days=WINDOW) < end <= day:
                if who not in latest or end >= latest[who][1]:
                    latest[who] = (pid, end)
        for c in codes:
            vals = [shares[pid][c] for pid, _e in latest.values() if c in shares[pid]]
            series[c].append(sum(vals) / len(vals) if vals else None)
    by_code = {r["code"]: r for r in rows}
    for c in codes:                                       # mitjana mobil de tres punts
        s = series[c]
        s = [None if s[i] is None else
             sum(x for x in s[max(0, i - 1):i + 2] if x is not None) /
             len([x for x in s[max(0, i - 1):i + 2] if x is not None]) for i in range(len(s))]
        # La linia es una mitjana simple; la de la web pondera cada institut.
        # Es desplaca sencera perque acabi exactament a la mitjana d'avui: el
        # que ensenya es el cami, i el punt final, la xifra de la pagina.
        lastv = next((v for v in reversed(s) if v is not None), None)
        off = (by_code[c]["share"] - lastv) if lastv is not None else 0
        series[c] = [None if v is None else max(0.0, v + off) for v in s]
    top = max([v for s in series.values() for v in s if v is not None] +
              [shares[p][c] for p, _w, e in polls if e >= start for c in shares[p]] + [10])
    step = 5 if top <= 30 else 10
    ymax = (int(top // step) + 1) * step
    x0, x1 = LEFT, W - RIGHT
    y0, y1 = H - BOTTOM, TOP
    span = (last - start).days or 1
    X = lambda day: x0 + (x1 - x0) * (day - start).days / span            # noqa: E731
    Y = lambda v: y0 - (y0 - y1) * v / ymax                                 # noqa: E731
    lines = []
    for c in codes:
        pts = [(X(day), Y(v)) for day, v in zip(days_, series[c]) if v is not None]
        if len(pts) < 2:
            continue
        path = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        lastv = next(v for v in reversed(series[c]) if v is not None)
        lines.append({"code": c, "name": by_code[c].get("person") or by_code[c]["name"],
                      "color": visible(by_code[c]["color"]), "d": path, "last": lastv, "y": pts[-1][1], "x": pts[-1][0]})
    if not lines:
        return None
    # Etiquetes del final sense trepitjar-se (13 px entre si)
    order = sorted(lines, key=lambda l: l["y"])
    prev = None
    for ln in order:
        ln["ly"] = ln["y"] if prev is None else max(ln["y"], prev + 13)
        prev = ln["ly"]
    over = order[-1]["ly"] - (y0 - 2) if order else 0
    if over > 0:
        for ln in order:
            ln["ly"] -= over
    dots = []
    for ln in lines[:DOT_LINES]:
        c = ln["code"]
        pts = [f"M{X(e):.1f} {Y(shares[p][c]):.1f}h0" for p, _w, e in polls if e >= start and c in shares[p]]
        dots.append({"color": ln["color"], "d": "".join(pts)})
    grid = [{"y": round(Y(v), 1), "v": v} for v in range(0, ymax + 1, step)]
    ticks = []
    m = dt.date(start.year, start.month, 1)
    while m <= last:
        if m >= start:
            ticks.append({"x": round(X(m), 1), "m": m.month - 1, "year": m.year if m.month == 1 else None})
        m = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    return {"w": W, "h": H, "x0": x0, "x1": x1, "y0": y0, "y1": y1, "grid": grid, "ticks": ticks,
            "lines": lines, "dots": dots, "months": MONTHS, "start": start.isoformat(), "end": last.isoformat(),
            "n": len([p for p in polls if p[2] >= start]), "window": WINDOW}
