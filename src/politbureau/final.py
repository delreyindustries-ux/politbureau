"""L'encert del 29N (pla de ruta, fase 1: publicar l'error el 30N).

Dos passos, perque durant la veda no es pot publicar res sobre enquestes:

1. `politbureau congela`, qualsevol dia de veda abans de les 20 h del 29/11:
   desa a data/final-29n.json (LOCAL, la carpeta data/ no es puja) la mitjana,
   els escons i la previsio tal com eren abans de la veda. Durant la veda no hi
   entra cap enquesta nova, aixi que son les xifres que la web tenia el 23/11.
   Despres de les 20 h del 29/11 es copia a config/final-29n.json i es puja.

2. El 30/11 s'omple config/resultat-29n.yaml amb el resultat provisional del
   Ministeri de l'Interior (percentatge sobre vot valid i escons de cada
   partit, amb les mateixes sigles que la web). Amb els dos fitxers, la web
   genera la pagina de l'encert: la mitjana contra el resultat, els escons
   contra l'interval de la previsio i els instituts d'enquestes del 2026.
"""
from __future__ import annotations

import datetime as dt
import json
import statistics
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1].parent
LOCAL = ROOT / "data" / "final-29n.json"
FROZEN = ROOT / "config" / "final-29n.json"
RESULT = ROOT / "config" / "resultat-29n.yaml"
ELECTION = "es-general"
DATE = "2026-11-29"
VEDA_FROM = "2026-11-24"
WINDOW_DAYS = 21
MAIN_SHARE = 3.0


def freeze(conn) -> dict:
    """Desa l'estat d'abans de la veda. Nomes llegeix la base de dades."""
    from . import forecast as fc
    from .build import current_national

    national = current_national(conn, ELECTION)
    seats = {r[0]: r[1] for r in conn.execute(
        """SELECT party, seats FROM seat_projection
           WHERE election_id = ? AND level = 'chamber'""", (ELECTION,)).fetchall()}
    last = conn.execute("SELECT MAX(fieldwork_end) FROM poll WHERE election_id = ?",
                        (ELECTION,)).fetchone()[0]
    sim = fc.simulate(conn, ELECTION, n=fc.N_SIMS, seed=2911)
    data = {
        "frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "last_fieldwork": last,
        "average": {p: round(v, 2) for p, v in sorted(national.items(), key=lambda kv: -kv[1])},
        "seats": seats,
        "forecast": sim and {"n": sim["n"], "parties": sim["parties"], "blocs": sim["blocs"],
                             "pp_alone": sim["pp_alone"]},
    }
    if last and last >= VEDA_FROM:
        raise RuntimeError(f"Hi ha enquestes del {last}, dins de la veda: no es congela.")
    LOCAL.parent.mkdir(parents=True, exist_ok=True)
    LOCAL.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def _load():
    try:
        frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
        result = yaml.safe_load(RESULT.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError):
        return None, None
    if not result or not result.get("shares"):
        return None, None
    return frozen, result


def _pollsters(conn, result, main):
    """L'ultima enquesta de cada institut abans de la veda contra el resultat."""
    from .build import load_polls
    start = (dt.date.fromisoformat(VEDA_FROM) - dt.timedelta(days=WINDOW_DAYS)).isoformat()
    rows = []
    for p in load_polls(conn, ELECTION):
        end = p.get("fieldwork_end") or ""
        if not (start <= end < VEDA_FROM):
            continue
        shares = {k: v[0] for k, v in p["results"].items() if v[0] is not None}
        have = [k for k in main if k in shares]
        if len(have) < min(4, len(main)):
            continue
        rows.append({"pollster": p["pollster"], "end": end,
                     "mae": round(statistics.mean(abs(shares[k] - result[k]) for k in have), 2)})
    rows.sort(key=lambda r: r["mae"])
    return rows


def report(conn) -> dict | None:
    """Tot el que ensenya la pagina, o None si encara no hi ha resultat."""
    frozen, res = _load()
    if not frozen:
        return None
    result = {k: float(v) for k, v in res["shares"].items()}
    real_seats = {k: int(v) for k, v in (res.get("seats") or {}).items()}
    main = [k for k, v in sorted(result.items(), key=lambda kv: -kv[1]) if v >= MAIN_SHARE]
    avg = frozen["average"]
    fc = {r["code"]: r for r in ((frozen.get("forecast") or {}).get("parties") or [])}
    parties = []
    for k in sorted(set(result) | {p for p, v in avg.items() if v >= 1}, key=lambda p: -result.get(p, 0)):
        f = fc.get(k)
        rs = real_seats.get(k)
        parties.append({
            "code": k, "average": avg.get(k), "result": result.get(k),
            "error": None if avg.get(k) is None or k not in result else round(avg[k] - result[k], 2),
            "seats": frozen["seats"].get(k), "real_seats": rs,
            "median": f and f["median"], "lo": f and f["lo"], "hi": f and f["hi"],
            "inside": None if not f or rs is None else f["lo"] <= rs <= f["hi"],
        })
    have = [k for k in main if k in avg]
    mae = round(statistics.mean(abs(avg[k] - result[k]) for k in have), 2) if have else None
    polls = _pollsters(conn, result, main)
    better = sum(1 for r in polls if mae is not None and r["mae"] < mae)
    blocs = (frozen.get("forecast") or {}).get("blocs") or {}
    from .forecast import BLOCS, MAJORITY
    bloc_seats = {k: sum(real_seats.get(p, 0) for p in members) for k, members in BLOCS.items()}
    with_interval = [p for p in parties if p["inside"] is not None]
    return {
        "frozen": frozen, "source": res.get("source"), "retrieved": res.get("retrieved"),
        "provisional": bool(res.get("provisional", True)),
        "main": main, "parties": parties, "mae": mae,
        "pollster_mae": round(statistics.mean(r["mae"] for r in polls), 2) if polls else None,
        "polls": polls, "rank": better + 1, "n_polls": len(polls),
        "inside": sum(1 for p in with_interval if p["inside"]), "n_inside": len(with_interval),
        "blocs": {k: {"prob": blocs.get(k, {}).get("majority"), "seats": bloc_seats[k],
                      "won": bloc_seats[k] >= MAJORITY} for k in BLOCS} if real_seats else {},
    }
