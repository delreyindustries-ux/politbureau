"""Jornada electoral del 29N: participacio oficial i que vol dir per als escons.

Preparat el 23/11/2026 (demanat per l'Alfonso: "prepara pel dia de les
eleccions les diferents actualitzacions per al diumenge, tenint en compte les
dades de participacio, a qui beneficia una alta participacio i el sostre de
votants del bloc de la dreta").

Com funciona el diumenge:
  1. El Ministeri de l'Interior dona la participacio a les 14 h i a les 18 h
     (avancos, sense el vot per correu) i, de nit, la final.
  2. `politbureau nit 14h 38,2` (o 18h, final) desa la xifra oficial a
     config/nit-29n.json, amb l'hora. Opcional: --font "URL".
  3. Amb la proporcio historica entre l'avanc i la participacio final (generals
     2016, 2019 abril i novembre i 2023, fitxer 05 d'Infoelectoral) se'n treu
     una forquilla de participacio final.
  4. Aquesta participacio passa als escenaris del simulador: model del CIS
     (qui diu que anira a votar), hipotesi classica (mes participacio, mes
     esquerra) i, en tots dos, amb el sostre de 12 milions de vots per a PP +
     Vox. Mateix calcul que web/sandbox.js.
  5. La web ensenya les xifres oficials de seguida. Els ESCONS amb aquesta
     participacio, nomes a partir de les 20 h: abans seria publicar una
     estimacio electoral durant la veda (LOREG, art. 69.7).

`politbureau nit taula` escriu la taula de tots els casos possibles (avanc de
les 14 h i de les 18 h -> participacio final -> escons) a direccio/, fora del git.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1].parent
OUT = ROOT / "config" / "nit-29n.json"
TABLE = ROOT / "direccio" / "nit-29n-escenaris.md"
ELECTION = "es-general"
BASELINE = "congreso-2023"

# Participacio a les 14 h, a les 18 h i final (votants sobre el cens de
# residents, sense CERA). Font: Infoelectoral, fitxer 05 de cada eleccio
# (participation.turnout_records), calculat el 23/11/2026.
HISTORY = {
    "2016": {"14h": 36.87, "18h": 51.21, "final": 69.83},
    "2019a": {"14h": 41.49, "18h": 60.74, "final": 75.75},
    "2019n": {"14h": 37.92, "18h": 56.85, "final": 69.86},
    "2023": {"14h": 40.49, "18h": 53.13, "final": 70.41},
}
STAGES = ("14h", "18h", "final")
# Del % de votants al % de vot valid del simulador (participacio.json, "ref"):
# el 2023, 69,1 de vot valid sobre 70,41 de votants.
VALID_PER_VOTER = 69.1 / 70.41
RIGHT_CAP = 12_000_000
VALID_2023 = 24_688_087          # vot valid oficial del 2023 (amb el blanc), history_es.json
RIGHT = ["PP", "VOX", "UPN"]
INVEST = ["PSOE", "SUMAR", "PODEMOS", "ERC", "EHB", "PNV", "BNG", "CC", "JUNTS", "AA"]
MAJORITY = 176


def ratios(stage):
    return {y: h["final"] / h[stage] for y, h in HISTORY.items() if h.get(stage)}


def project_final(stage, value):
    """Forquilla de participacio final a partir d'un avanc."""
    if stage == "final":
        return {"lo": value, "mid": value, "hi": value, "by": {}}
    rs = ratios(stage)
    by = {y: round(value * r, 1) for y, r in rs.items()}
    vals = sorted(by.values())
    mid = vals[len(vals) // 2] if len(vals) % 2 else (vals[len(vals) // 2 - 1] + vals[len(vals) // 2]) / 2
    return {"lo": vals[0], "mid": round(mid, 1), "hi": vals[-1], "by": by}


def to_t(final):
    """Participacio final (votants) -> la del simulador (vot valid), arrodonida."""
    return int(round(final * VALID_PER_VOTER))


# ------------------------------------------------------------------ escenaris
def _load(conn):
    from .build import magnitudes_for
    from .geo import regions as georegions
    prov = {}
    for r in conn.execute("SELECT code, party, share FROM projection WHERE election_id = ? AND level = 'province'",
                          (ELECTION,)):
        prov.setdefault(r["code"], {})[r["party"]] = r["share"]
    valid = {r[0]: r[1] or 0 for r in conn.execute(
        "SELECT code, MAX(valid_votes) FROM election_result WHERE election = ? AND level = 'province' GROUP BY code",
        (BASELINE,))}
    mags = magnitudes_for(conn, ELECTION, BASELINE)
    region_of = georegions.table()["province"]
    tf = json.loads((ROOT / "config" / "participacio.json").read_text(encoding="utf-8"))
    return prov, valid, mags, region_of, tf


def _weighted(prov, valid, shares_of):
    tot = sum(valid.get(c, 0) for c in prov) or 1
    out = {}
    for c in prov:
        for p, v in shares_of(c).items():
            out[p] = out.get(p, 0) + v * valid.get(c, 0) / tot
    return out


def scenario(conn, t, model="cis", cap=False, data=None):
    """Escons amb participacio t (vot valid, % del cens de residents), com el simulador."""
    from .model import seats as sl
    prov, valid, mags, region_of, tfd = data or _load(conn)
    ref = tfd["ref"]
    t = max(50, min(int(tfd["max"]), int(t)))
    same = t == round(ref)
    if model == "classic" and tfd.get("classic") and not same:
        C = tfd["classic"]
        nat = _weighted(prov, valid, lambda c: prov[c])
        L, R = sum(nat.get(k, 0) for k in C["left"]), sum(nat.get(k, 0) for k in C["right"])
        s = L + R
        lt = max(0.02 * s, min(0.98 * s, L + C["slope"] * (t - ref) * s / 100))
        g = {**{k: lt / L for k in C["left"]}, **{k: (s - lt) / R for k in C["right"]}}
        factor = lambda c: g                                                     # noqa: E731
    elif not same:
        nat_f = tfd["factors"].get(str(t), {})
        factor = lambda c: {**nat_f, **((tfd.get("regional") or {}).get(region_of.get(c)) or {}).get(str(t), {})}  # noqa: E731
    else:
        factor = lambda c: {}                                                    # noqa: E731
    shares = {}
    for c, s in prov.items():
        g = factor(c)
        o = {p: v * g.get(p, 1.0) for p, v in s.items()}
        k = sum(s.values()) / (sum(o.values()) or 1)
        shares[c] = {p: v * k for p, v in o.items()}
    removed = 0.0
    nat = _weighted(prov, valid, lambda c: shares[c])
    right_votes = sum(nat.get(k, 0) for k in RIGHT) / 100 * VALID_2023 * t / ref
    if cap and right_votes > RIGHT_CAP:
        kk = RIGHT_CAP / right_votes
        for c, s in shares.items():
            tot = sum(s.values())
            rs = sum(v for p, v in s.items() if p in RIGHT)
            den = tot - rs * (1 - kk)
            shares[c] = {p: (v * kk if p in RIGHT else v) * tot / den for p, v in s.items()}
        removed = right_votes - RIGHT_CAP
        right_votes = RIGHT_CAP
    seats, _ = sl.allocate(shares, mags)
    return {"t": t, "model": model, "cap": cap, "seats": seats,
            "right": sum(seats.get(p, 0) for p in RIGHT), "invest": sum(seats.get(p, 0) for p in INVEST),
            "right_votes": round(right_votes), "removed": round(removed)}


MODELS = (("cis", False), ("cis", True), ("classic", False), ("classic", True))


def scenarios_for(conn, final, data=None):
    data = data or _load(conn)
    t = to_t(final)
    return [scenario(conn, t, m, c, data) for m, c in MODELS]


# ------------------------------------------------------------------ registre
def load():
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def record(conn, stage, value, source=None, now=None):
    """Desa una xifra oficial de participacio i en recalcula els escenaris."""
    if stage not in STAGES:
        raise ValueError(f"etapa {stage!r}: ha de ser una de {STAGES}")
    d = load() or {"election": ELECTION, "date": "2026-11-29", "stages": {}}
    now = now or dt.datetime.now(dt.timezone(dt.timedelta(hours=1)))
    d["stages"][stage] = {"value": round(float(value), 2), "at": now.isoformat(timespec="minutes"),
                          "source": source or "Ministerio del Interior"}
    last = [s for s in STAGES if s in d["stages"]][-1]
    v = d["stages"][last]["value"]
    proj = project_final(last, v)
    data = _load(conn)
    d["projection"] = {"from": last, **proj, "t": to_t(proj["mid"]), "t_lo": to_t(proj["lo"]), "t_hi": to_t(proj["hi"])}
    d["scenarios"] = {"mid": scenarios_for(conn, proj["mid"], data),
                      "lo": scenarios_for(conn, proj["lo"], data),
                      "hi": scenarios_for(conn, proj["hi"], data)}
    d["history"] = HISTORY
    d["updated"] = now.isoformat(timespec="minutes")
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


# ------------------------------------------------------------------ taula
def _cell(s):
    st = s["seats"]
    return f"PP {st.get('PP', 0)} · PSOE {st.get('PSOE', 0)} · Vox {st.get('VOX', 0)} · **PP+Vox {s['right']}**"


def table(conn):
    """Tots els casos: per a cada avanc possible, participacio final i escons."""
    data = _load(conn)
    lines = ["# Nit del 29N: escenaris de participació", "",
             f"Generat el {dt.date.today().strftime('%d/%m/%Y')} amb la projecció d'aquell dia (es congela amb la veda).",
             "Participació final estimada = avanç × proporció final/avanç de les generals 2016, 2019 (abril i novembre) i 2023.",
             "Escons: mateix càlcul que el simulador. Majoria: 176.", "",
             "Models: **CIS** = qui diu que anirà a votar; **clàssica** = més participació, més esquerra;",
             "**+ sostre** = PP + Vox no passen de 12 milions de vots (els que sobren s'abstenen).", ""]
    rows = {"14h": [x / 2 for x in range(66, 93)], "18h": [float(x) for x in range(46, 65)]}
    for stage, vals in rows.items():
        lines += [f"## Avanç de les {stage[:2]} h", "",
                  "| Avanç | Final estimada (forquilla) | CIS | CIS + sostre | Clàssica | Clàssica + sostre |",
                  "|---|---|---|---|---|---|"]
        r23 = HISTORY["2023"][stage]
        for v in vals:
            p = project_final(stage, v)
            sc = scenarios_for(conn, p["mid"], data)
            cells = " | ".join(_cell(s) for s in sc)
            mark = " (2023)" if abs(v - r23) < 0.26 else ""
            lines.append(f"| {v:.1f} %{mark} | {p['mid']:.1f} % ({p['lo']:.1f}-{p['hi']:.1f}) | {cells} |".replace(".", ","))
        lines.append("")
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    TABLE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return TABLE
