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


# ------------------------------------------------------------- model v2
# Millora del 21/11/2026 ("millora els calculs ... dels escenaris depenent la
# participacio"):
#   * Probabilitat de votar suau en lloc d'un tall per index amb empats: cada
#     entrevista te p_i = logistica(alfa + s_i), on s_i = b1 * PROBVOTO + b2 *
#     edat. b1 i b2 s'estimen amb una regressio logistica ponderada: com
#     prediuen la probabilitat declarada i l'edat que la persona digui que va
#     votar el 2023 (PARTICIPACIONG). Per a una participacio T, alfa es tria
#     perque la mitjana ponderada de p_i sigui q(T) (mateixa escala d'abans).
#   * Interval: les entrevistes es remostregen (bootstrap, BOOT vegades) i es
#     donen els percentils 10 i 90 de cada factor.
#   * Factors per comunitat autonoma, encongits cap a l'estatal:
#     f_r = f + (f_r_cru - f) * n_r / (n_r + K_SHRINK), nomes on hi ha
#     MIN_REGION entrevistes o mes; un partit amb menys de 80 entrevistes a la
#     comunitat hi fa servir el factor estatal.
CCAA = {"Andalucía": "01", "Aragón": "02", "Asturias (Principado de)": "03", "Balears (Illes)": "04",
        "Canarias": "05", "Cantabria": "06", "Castilla y León": "07", "Castilla-La Mancha": "08",
        "Cataluña": "09", "Comunitat Valenciana": "10", "Extremadura": "11", "Galicia": "12",
        "Madrid (Comunidad de)": "13", "Murcia (Región de)": "14", "Navarra (Comunidad Foral de)": "15",
        "País Vasco": "16", "Rioja (La)": "17", "Ceuta (Ciudad Autónoma de)": "18", "Melilla (Ciudad Autónoma de)": "19"}
K_SHRINK = 1000
MIN_REGION = 300
MIN_REGION_PARTY = 80
BOOT = 60
SHOW = (50, 55, 60, 65, 75, 80)


def _sig(x):
    if x < -40:
        return 0.0
    if x > 40:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


def _solve3(a, b):
    """Resol a (3x3) x = b per Gauss."""
    m = [row[:] + [bb] for row, bb in zip(a, b)]
    for i in range(3):
        piv = max(range(i, 3), key=lambda r: abs(m[r][i]))
        m[i], m[piv] = m[piv], m[i]
        for r in range(3):
            if r != i and m[i][i]:
                f = m[r][i] / m[i][i]
                for c in range(i, 4):
                    m[r][c] -= f * m[i][c]
    return [m[i][3] / m[i][i] for i in range(3)]


def _fit_logit(xs, ys, ws, iters=30):
    """Regressio logistica ponderada (IRLS) amb tres coeficients."""
    beta = [0.0, 0.0, 0.0]
    for _ in range(iters):
        h = [[0.0] * 3 for _ in range(3)]
        g = [0.0] * 3
        for x, y, w in zip(xs, ys, ws):
            p = _sig(sum(b * xi for b, xi in zip(beta, x)))
            v = w * p * (1 - p)
            for i in range(3):
                g[i] += w * (y - p) * x[i]
                for j in range(3):
                    h[i][j] += v * x[i] * x[j]
        step = _solve3(h, g)
        beta = [b + s for b, s in zip(beta, step)]
        if max(abs(s) for s in step) < 1e-7:
            break
    return beta


def _alpha(scores, ws, target):
    """alfa tal que la mitjana ponderada de logistica(alfa + s) = target.
    Biseccio: la mitjana creix sempre amb alfa, aixi que sempre convergeix."""
    tot = sum(ws)
    lo, hi = -40.0, 40.0
    for _ in range(45):
        mid = (lo + hi) / 2
        if sum(w * _sig(mid + s) for s, w in zip(scores, ws)) / tot < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _shares(sample, alpha):
    out, tot = {}, 0.0
    for s, w, party, _r in sample:
        if party:
            v = w * _sig(alpha + s)
            out[party] = out.get(party, 0.0) + v
            tot += v
    return {p: 100.0 * v / tot for p, v in out.items()} if tot else {}


def _factors(sample, q_ref, t_ref, levels, keep):
    scores = [x[0] for x in sample]
    ws = [x[1] for x in sample]
    base = _shares(sample, _alpha(scores, ws, q_ref))
    out = {}
    for t in levels:
        q = min(0.999, t * q_ref / t_ref)
        s = _shares(sample, _alpha(scores, ws, q))
        out[t] = {p: s.get(p, 0) / base[p] for p in keep if base.get(p)}
    return out


def run() -> dict | None:
    import random
    files = sorted(RAW.glob("*/*_etiq.csv"))
    if not files:
        return None
    rows, studies = [], []
    for f in files:
        studies.append(f.parent.name)
        for r in _read(f):
            w = _weight(r.get("PESO"))
            part = (r.get("PARTICIPACIONG") or "").strip().lower()
            if w <= 0 or "derecho" in part:                # sense dret a vot
                continue
            try:
                age = min(99.0, float(str(r.get("EDAD") or "").replace(",", ".")))
            except ValueError:
                age = 45.0
            rows.append({"w": w, "prob": _prob(r.get("PROBVOTO")), "age": age, "part": part,
                         "party": PARTY.get((r.get("VOTOSIMG") or "").strip()), "reg": CCAA.get(r.get("CCAA"))})
    # 1. Com prediuen la probabilitat declarada i l'edat el vot del 2023.
    fit = [x for x in rows if "edad" not in x["part"] and x["part"] in ("votó", "no votó")]
    beta = _fit_logit([(1.0, x["prob"] / 10.0, (x["age"] - 50.0) / 20.0) for x in fit],
                      [1.0 if x["part"] == "votó" else 0.0 for x in fit], [x["w"] for x in fit])
    for x in rows:
        x["s"] = beta[1] * x["prob"] / 10.0 + beta[2] * (x["age"] - 50.0) / 20.0
    sample = [(x["s"], x["w"], x["party"], x["reg"]) for x in rows]
    everyone = sum(x["w"] for x in rows)
    voted = sum(x["w"] for x in rows if x["part"].startswith("votó"))
    t_ref = _ref_turnout()
    q_ref = voted / everyone
    t_max = min(math.floor(t_ref / q_ref) if q_ref else 85, GRID[-1])
    levels = [t for t in GRID if t <= t_max]
    n_party = {}
    for x in rows:
        if x["party"]:
            n_party[x["party"]] = n_party.get(x["party"], 0) + 1
    keep = sorted(p for p, n in n_party.items() if n >= MIN_N)
    nat = _factors(sample, q_ref, t_ref, levels, keep)
    # 2. Interval (bootstrap)
    rng = random.Random(2911)
    boots = {t: {p: [] for p in keep} for t in SHOW if t in nat}
    for _ in range(BOOT):
        bs = [sample[rng.randrange(len(sample))] for _ in sample]
        fb = _factors(bs, q_ref, t_ref, list(boots), keep)
        for t in boots:
            for p in keep:
                if p in fb[t]:
                    boots[t][p].append(fb[t][p])

    def pct(xs, a):
        ys = sorted(xs)
        return ys[min(len(ys) - 1, max(0, int(round(a * (len(ys) - 1)))))] if ys else None
    ci = {str(t): {p: [round(pct(v, 0.1), 4), round(pct(v, 0.9), 4)] for p, v in d.items() if v}
          for t, d in boots.items()}
    # 3. Comunitats autonomes
    regional, n_region = {}, {}
    for code in sorted(set(CCAA.values())):
        sub = [x for x in sample if x[3] == code]
        n_region[code] = len(sub)
        if len(sub) < MIN_REGION:
            continue
        counts = {}
        for x in sub:
            if x[2]:
                counts[x[2]] = counts.get(x[2], 0) + 1
        rk = [p for p in keep if counts.get(p, 0) >= MIN_REGION_PARTY]
        if not rk:
            continue
        raw = _factors(sub, q_ref, t_ref, levels, rk)
        shrink = len(sub) / (len(sub) + K_SHRINK)
        regional[code] = {str(t): {p: round(nat[t][p] + (raw[t][p] - nat[t][p]) * shrink, 4)
                                   for p in rk if p in raw[t] and p in nat[t]} for t in levels}
    data = {"updated": dt.date.today().isoformat(), "studies": studies, "n": len(rows), "model": 2,
            "ref": round(t_ref, 1), "q_ref": round(100 * q_ref, 1), "max": t_max,
            "logit": {"b0": round(beta[0], 3), "prob": round(beta[1], 3), "age": round(beta[2], 3), "n": len(fit)},
            "n_party": {p: n_party[p] for p in keep},
            "factors": {str(t): {p: round(v, 4) for p, v in d.items()} for t, d in nat.items()},
            "ci": ci, "boot": BOOT, "regional": regional, "n_region": n_region, "shrink_k": K_SHRINK,
            "classic": None,
            "source": "Origen de los datos: Centro de Investigaciones Sociológicas (CIS), "
                      "barómetros " + ", ".join(studies)}
    hist = history()
    if hist:
        data["classic"] = {"slope": hist["april2019"], "left": LEFT_NOW, "right": RIGHT_NOW, "history": hist}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data
