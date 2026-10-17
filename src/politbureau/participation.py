"""Participacio a les places de tradicio progressista (generals del 29/11/2026).

Decisio de l'Alfonso (17/10/2026): els 500 municipis amb MES vot d'esquerres de
manera sostinguda, ordenats de mes a menys electors. «De manera sostinguda» vol
dir la MITJANA del percentatge d'esquerres a les quatre generals de 2016, abril
2019, novembre 2019 i 2023, no nomes l'ultima.

Esquerra = PSOE i tot el que el cataleg posa a la seva esquerra (Podemos, Sumar,
IU, ERC, Bildu, BNG, CUP, Chunta, Nueva Canarias, Geroa Bai, Adelante...), mes
les candidatures antigues que el cataleg no reconeix pel nom (En Comu Podem,
Mas Pais, Mes Compromis, PSE-EE retallat...), llistades a LEFT_LABELS.

La seleccio es fa UNA vegada (`politbureau participacio --tria`) i es desa a
config/participacio/es-general.csv amb la participacio del 2023 a les 14 h, a
les 18 h i final, per comparar-hi la del 29N hora a hora. La de la nit
electoral la llegira un altre modul quan l'Interior obri la seva web de
resultats, i es desara a data/live/.
"""
from __future__ import annotations

import csv
import json
import re
from functools import lru_cache
from pathlib import Path

from . import census as censuslib
from . import parties

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "config" / "participacio" / "es-general.csv"
REF = ROOT / "config" / "participacio" / "es-general-2023.json"
LIVE = ROOT / "data" / "live" / "es-general-participacio.json"
ELECTIONS = ("congreso-2016", "congreso-2019a", "congreso-2019n", "congreso-2023")
SIZE = 500

# Sigles antigues que el cataleg no resol i que son d'esquerres. Es comparen
# amb slug() de les sigles (minuscules, sense accents).
LEFT_LABELS = re.compile(
    r"^(ecp|ecp-guanyem.*|pse-ee.*|mas pais.*|mes comprom.*|front repub.*|"
    r"en marea.*|anova.*|compromis.*|mes-compromis.*|eupv.*|iu.*|"
    r"izquierda unida.*|bildu.*|amaiur.*|nc-?bc|nueva canarias.*|adelante.*)$")


def is_left(label: str) -> bool:
    code, _ = parties.resolve(label, "ES")
    if code and not code.startswith("?"):
        return parties.position(code, "ES") <= parties.position("PSOE", "ES")
    return bool(LEFT_LABELS.match(parties.slug(label)))


def _shares():
    """{eleccio: {municipi: (pct_esquerra, info_del_fitxer_05)}}."""
    from .ingest import infoelectoral as ie
    out = {}
    for proc in ELECTIONS:
        tipo, year, month = ie.PROCESSES[proc]
        zf = ie.download(proc)
        cand = ie.candidacies(zf, tipo, year, month)
        left_codes = {c for c, label in cand.items() if is_left(label)}
        votes = ie.votes(zf, tipo, year, month)
        munis = turnout_records(zf, tipo, year, month)
        out[proc] = {}
        for code, info in munis.items():
            valid = info["valid"]
            if not valid:
                continue
            left = sum(n for c, n in votes.get(code, {}).items() if c in left_codes)
            out[proc][code] = (left * 100.0 / valid, info)
    return out


def turnout_records(zf, tipo, year, month) -> dict:
    """Fitxer 05 amb els avancos de participacio, que el modul d'ingesta no llegeix.

    Posicions comprovades amb el 2023 (Barcelona: 392.707 votants a les 14 h i
    533.333 a les 18 h sobre 1.084.347 electors, el 36,2 % i el 49,2 %)."""
    from .ingest import infoelectoral as ie
    out = {}
    for rec in ie._records(ie._member(zf, "05", tipo, year, month), 233):
        if rec[16:18] != "99":
            continue
        out[rec[11:13] + rec[13:16]] = {
            "name": rec[18:118].strip(),
            "census": int(rec[141:149]),
            "avance1": int(rec[173:181]),
            "avance2": int(rec[181:189]),
            "invalid": int(rec[197:205]),
            "valid": int(rec[205:213]),
        }
    return out


def select(size: int = SIZE) -> list[dict]:
    """Tria els municipis i en desa la llista. Retorna les files desades."""
    from .geo import fetch as geo
    shares = _shares()
    every = set().union(*(set(v) for v in shares.values()))
    rows = []
    for code in every:
        present = [shares[e][code][0] for e in ELECTIONS if code in shares[e]]
        if len(present) < 3:            # municipis creats fa poc: sense prou historia
            continue
        avg = sum(present) / len(present)
        last = shares["congreso-2023"].get(code)
        if not last:
            continue
        info = last[1]
        pct = lambda n: round(n * 100.0 / info["census"], 2) if info["census"] else None  # noqa: E731
        rows.append({
            "code": code,
            "name": geo.names("ES", "municipality").get(code) or info["name"],
            "province": code[:2],
            "left_avg": round(avg, 2),
            **{f"left_{e.split('-')[1]}": round(shares[e][code][0], 2) if code in shares[e] else ""
               for e in ELECTIONS},
            "census_2026": censuslib.total("es-general", "municipality", code) or "",
            "t23_14": pct(info["avance1"]),
            "t23_18": pct(info["avance2"]),
            "t23_final": pct(info["valid"] + info["invalid"]),
            "c23": info["census"], "v23_14": info["avance1"], "v23_18": info["avance2"],
            "v23_final": info["valid"] + info["invalid"],
        })
    # Referencia estatal del 2023 (tots els municipis), per comparar-hi els 500
    every23 = [i for _, i in shares["congreso-2023"].values()]
    nat = {k: sum(i[k] for i in every23) for k in ("census", "avance1", "avance2", "valid", "invalid")}
    REF.parent.mkdir(parents=True, exist_ok=True)
    REF.write_text(json.dumps({
        "census": nat["census"],
        "t14": round(nat["avance1"] * 100.0 / nat["census"], 2),
        "t18": round(nat["avance2"] * 100.0 / nat["census"], 2),
        "final": round((nat["valid"] + nat["invalid"]) * 100.0 / nat["census"], 2),
        "note": "Congres 23/07/2023, municipis (sense CERA). Font: Infoelectoral, fitxer 05.",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    rows.sort(key=lambda r: -r["left_avg"])
    chosen = rows[:size]
    chosen.sort(key=lambda r: -(r["census_2026"] or 0))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(chosen[0]))
        w.writeheader()
        w.writerows(chosen)
    return chosen


@lru_cache(maxsize=1)
def load() -> list[dict]:
    """La llista desada, amb els valors numerics ja convertits."""
    if not OUT.exists():
        return []
    rows = []
    with OUT.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            for k, v in list(r.items()):
                if k not in ("code", "name", "province"):
                    r[k] = float(v) if v not in ("", None) else None
            rows.append(r)
    return rows


def reference() -> dict:
    return json.loads(REF.read_text(encoding="utf-8")) if REF.exists() else {}


def live() -> dict:
    """Participacio de la nit electoral, si ja n'hi ha: {"updated", "stage", "munis": {codi: {...}}}."""
    if not LIVE.exists():
        return {}
    return json.loads(LIVE.read_text(encoding="utf-8"))
