"""Escenaris de participacio (22/11/2026, demanat per l'Alfonso: "prepara
diferents escenaris depenent de la participacio").

Pregunta: si a les generals vota mes o menys gent que el 2023, qui hi guanya?
No tots els electorats es mobilitzen igual: els qui diuen que segur que
aniran a votar no voten el mateix que els qui dubten.

Font: microdades dels barometres del CIS (les mateixes que collectius.py,
data/raw/cis/, fora del git). Per a cada entrevista:
  * PROBVOTO: probabilitat (0-10) d'anar a votar a unes generals;
  * PARTICIPACIONG: si va votar el 2023;
  * VOTOSIMG: vot + simpatia;
  * PESO: el pes del CIS.

Model de votant probable (el classic de les enquestes electorals):
  1. Cada entrevista te un index de propensio: PROBVOTO, mes 0,5 si va votar
     el 2023 (0,25 si no tenia edat; N.S./N.C. de PROBVOTO compta com a 5).
     Tres de cada quatre entrevistats diuen 10 i van votar el 2023: dins d'un
     mateix grau, l'edat desempata (0,001 per any, mai no salta de grau),
     perque a Espanya la participacio puja amb l'edat. Sense aixo, per sota
     del 62 % tots els escenaris serien identics.
  2. Una participacio T vol dir que voten els T % mes propensos de
     l'electorat. Al CIS hi ha mes votants que a la realitat (diu que va votar
     un 83 % de la mostra, i el 2023 el vot valid va ser el 69 % del cens), aixi
     que la quota de la mostra s'escala: q(T) = T x q_ref / T_ref, on q_ref es
     la part de la mostra que diu que va votar el 2023 i T_ref, el vot valid
     sobre el cens de residents del 2023. Als empats de l'index de la
     frontera s'hi entra en fraccio.
  3. Per a cada partit, el factor de mobilitzacio f(T) = % del partit entre
     els votants de l'escenari T / % entre els votants de l'escenari del 2023.
     El simulador multiplica el vot de cada partit per f(T) a cada provincia i
     torna a sumar el total.

Nomes es dona factor als partits amb 300 entrevistes o mes; la resta queden a
1 (no hi ha prou mostra per saber si es mobilitzen mes o menys).

Segon model, la "hipotesi classica" (que l'Alfonso va demanar de tenir en
compte: "normalment una participacio mes alta beneficia l'esquerra"). Es
contrasta amb els resultats reals de les generals 2016-2023 (Ministeri de
l'Interior, provincia per provincia): participacio = vot valid / cens de
residents; esquerra i dreta, com a % de la suma dels dos blocs. L'unic
episodi que encaixa del tot es l'abril del 2019; la mida del model classic es
la d'aquell canvi (punts d'esquerra per punt de participacio), i la web diu
que es el cas mes favorable a la hipotesi.

El resultat (nomes agregats) va a config/participacio.json.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

from .collectius import RAW, _read, _weight

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "config" / "participacio.json"
MIN_N = 300
PARTY = {"PSOE": "PSOE", "PP": "PP", "VOX": "VOX", "Sumar": "SUMAR", "Podemos": "PODEMOS",
         "ERC": "ERC", "Se Acabó la Fiesta": "SALF", "EH Bildu": "EHB", "Junts": "JUNTS",
         "BNG": "BNG", "EAJ-PNV": "PNV", "Aliança Catalana": "AA"}
GRID = list(range(50, 86))


def _prob(v):
    v = (v or "").strip()
    try:
        return float(v.split()[0])
    except (ValueError, IndexError):
        return 5.0


def _bonus(v):
    v = (v or "").strip().lower()
    if v.startswith("votó"):
        return 0.5
    if "edad" in v:
        return 0.25
    return 0.0


def _ref_turnout():
    """Vot valid / cens de residents a les generals del 2023 (de la base de dades)."""
    from . import db
    from .site.build import BASELINE
    conn = db.connect()
    rows = conn.execute("SELECT code, MAX(valid_votes), MAX(census) FROM election_result "
                        "WHERE election = ? AND level = 'province' GROUP BY code", (BASELINE,)).fetchall()
    v = sum(r[1] or 0 for r in rows)
    c = sum(r[2] or 0 for r in rows)
    return 100.0 * v / c if c else 69.1


def _shares_at(people, q):
    """% de cada partit entre la fraccio q (0-1) mes propensa de la mostra."""
    total = sum(w for _, w, _ in people)
    need = q * total
    out, taken = {}, 0.0
    i = 0
    while i < len(people) and taken < need:
        j = i
        while j < len(people) and people[j][0] == people[i][0]:
            j += 1
        block = people[i:j]
        bw = sum(w for _, w, _ in block)
        frac = min(1.0, (need - taken) / bw) if bw else 0.0
        for _, w, p in block:
            if p:
                out[p] = out.get(p, 0.0) + w * frac
        taken += bw * frac
        i = j
    tot = sum(out.values()) or 1.0
    return {p: 100.0 * v / tot for p, v in out.items()}


# Blocs per al contrast historic (codis de cada eleccio) i per al model classic.
LEFT_HIST = {"PSOE", "PODEMOS", "SUMAR", "?ECP", "?ECPGUANYEM", "?MASPAISEQ", "?MESCOMPROM", "ERC",
             "EHB", "BNG", "CUP", "?FRONTREPUB"}
RIGHT_HIST = {"PP", "VOX", "CS", "UPN", "?NA"}
LEFT_NOW = ["PSOE", "SUMAR", "PODEMOS", "ERC", "EHB", "BNG", "CUP"]
RIGHT_NOW = ["PP", "VOX", "SALF", "UPN", "CS", "AA"]
HIST = (("congreso-2016", "2016"), ("congreso-2019a", "2019A"), ("congreso-2019n", "2019N"),
        ("congreso-2023", "2023"))


def _ols(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    res = [y - my - b * (x - mx) for x, y in zip(xs, ys)]
    return b, (sum(r * r for r in res) / (n - 2) / sxx) ** 0.5


def history() -> dict | None:
    """Participacio i pes de l'esquerra a les generals 2016-2023, i el pendent."""
    from . import parties
    from .ingest import infoelectoral as ie
    data = {}
    for proc, label in HIST:
        try:
            tipo, y, m = ie.PROCESSES[proc]
            zf = ie.download(proc)
            cons = ie.constituencies(zf, tipo, y, m)
            munis = ie.municipalities(zf, tipo, y, m)
            sig = ie.candidacies(zf, tipo, y, m)
        except Exception:                                  # noqa: BLE001
            return None
        census, valid = {}, {}
        for c, mm in munis.items():
            census[c[:2]] = census.get(c[:2], 0) + mm["census"]
            valid[c[:2]] = valid.get(c[:2], 0) + mm["valid"]
        provs = {}
        for prov, e in cons.items():
            left = right = 0
            for cand, (v, _s) in e["parties"].items():
                lab = sig.get(cand, cand)
                code = parties.resolve(lab, "ES")[0] or f"?{lab}"
                left += v if code in LEFT_HIST else 0
                right += v if code in RIGHT_HIST else 0
            if census.get(prov) and left + right:
                provs[prov] = (census[prov], valid[prov], left, right)
        data[label] = provs
    rows = []
    for _, label in HIST:
        pv = data[label].values()
        c, v = sum(x[0] for x in pv), sum(x[1] for x in pv)
        lft, rgt = sum(x[2] for x in pv), sum(x[3] for x in pv)
        rows.append({"e": label, "turnout": round(100 * v / c, 1), "left": round(100 * lft / (lft + rgt), 1)})
    # Provincia per provincia, d'una eleccio a la seguent (sense Catalunya,
    # on Junts i el 2019 distorsionen els dos blocs).
    xs, ys = [], []
    labels = [lb for _, lb in HIST]
    for a, b in zip(labels, labels[1:]):
        for p, (c1, v1, l1, r1) in data[a].items():
            if p in ("08", "17", "25", "43") or p not in data[b]:
                continue
            c2, v2, l2, r2 = data[b][p]
            xs.append(100 * v2 / c2 - 100 * v1 / c1)
            ys.append(100 * l2 / (l2 + r2) - 100 * l1 / (l1 + r1))
    slope, se = _ols(xs, ys)
    a19 = (rows[1]["left"] - rows[0]["left"]) / (rows[1]["turnout"] - rows[0]["turnout"])
    return {"rows": rows, "pooled": round(slope, 3), "pooled_se": round(se, 3), "n": len(xs),
            "april2019": round(a19, 2)}


def run() -> dict | None:
    files = sorted(RAW.glob("*/*_etiq.csv"))
    if not files:
        return None
    people, voted, everyone, n_party, studies = [], 0.0, 0.0, {}, []
    for f in files:
        studies.append(f.parent.name)
        for r in _read(f):
            w = _weight(r.get("PESO"))
            if w <= 0:
                continue
            part = r.get("PARTICIPACIONG") or ""
            if "derecho" in part.lower():           # no te dret a vot
                continue
            party = PARTY.get((r.get("VOTOSIMG") or "").strip())
            try:
                age = min(99.0, float(str(r.get("EDAD") or "").replace(",", ".")))
            except ValueError:
                age = 45.0
            idx = _prob(r.get("PROBVOTO")) + _bonus(part) + 0.001 * age
            people.append((idx, w, party))
            everyone += w
            if part.strip().lower().startswith("votó"):
                voted += w
            if party:
                n_party[party] = n_party.get(party, 0) + 1
    people.sort(key=lambda x: -x[0])
    t_ref = _ref_turnout()
    q_ref = voted / everyone
    base = _shares_at(people, q_ref)
    keep = sorted(p for p, n in n_party.items() if n >= MIN_N)
    grid = {}
    for t in GRID:
        q = min(1.0, t * q_ref / t_ref)
        s = _shares_at(people, q)
        grid[str(t)] = {p: round(s.get(p, 0) / base[p], 4) for p in keep if base.get(p)}
    t_max = math.floor(t_ref / q_ref) if q_ref else 85
    data = {"updated": dt.date.today().isoformat(), "studies": studies, "n": len(people),
            "ref": round(t_ref, 1), "q_ref": round(100 * q_ref, 1), "max": min(t_max, GRID[-1]),
            "n_party": {p: n_party[p] for p in keep}, "base": {p: round(base[p], 2) for p in keep},
            "factors": {k: v for k, v in grid.items() if int(k) <= min(t_max, GRID[-1])},
            "classic": None,
            "source": "Origen de los datos: Centro de Investigaciones Sociológicas (CIS), "
                      "barómetros " + ", ".join(studies)}
    hist = history()
    if hist:
        data["classic"] = {"slope": hist["april2019"], "left": LEFT_NOW, "right": RIGHT_NOW, "history": hist}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data
