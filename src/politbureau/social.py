"""Dades socials per municipi i com hi vota cada grup (09/11/2026, demanat per ell).

Fonts (es baixen una vegada; el resultat va a data/social/municipis.csv):
  * INE, Atles de Distribucio de Renda de les Llars (ADRH), «Indicadores
    demograficos» (taula 30832, tot Espanya): poblacio, edat mitjana, % de 65 anys
    o mes, % de menors de 18, % de poblacio espanyola i mida mitjana de la llar.
    L'any mes recent que porta la taula.
  * SEPE, «Paro registrado por municipios» (dades obertes), el darrer mes publicat.
    Quan hi ha menys de 5 aturats el SEPE escriu «<5»: es compta com a 2.
  * La renda per persona ja hi era (renda.py, ADRH 2023).

L'atur es dona sobre la poblacio de 18 a 64 anys, que es calcula amb els
percentatges de l'ADRH (100 - menors de 18 - 65 o mes). No es la taxa d'atur
de l'EPA (aquesta es sobre la poblacio activa i no existeix per municipi): es
una aproximacio per comparar municipis entre ells.

    PYTHONPATH=src py -m politbureau.social <taula_ine.csv> <paro_sepe.csv>
"""
from __future__ import annotations

import csv
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "social" / "municipis.csv"

_IND = {"Población": "poblacio", "Edad media de la población": "edat",
        "Porcentaje de población de 65 y más años": "pct65",
        "Porcentaje de población menor de 18 años": "pct18",
        "Porcentaje de población española": "pct_esp",
        "Tamaño medio del hogar": "llar"}
FIELDS = ["code", "any", "poblacio", "edat", "pct65", "pct18", "pct_estr", "llar",
          "mes_atur", "atur", "pct_atur"]


def _num(s: str):
    s = (s or "").strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def read_ine(path: Path) -> tuple[dict, int]:
    """{municipi: {camp: valor}} de l'any mes recent, nomes files de municipi."""
    by_year: dict = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f, delimiter=";")
        next(r)
        for row in r:
            if len(row) < 6 or row[1] or row[2]:
                continue                       # districte o seccio
            field = _IND.get(row[3])
            year = row[4].strip()
            val = _num(row[5])
            if not field or val is None or not year.isdigit():
                continue
            code = row[0].split(" ", 1)[0]
            by_year.setdefault(int(year), {}).setdefault(code, {})[field] = val
    year = max(y for y, d in by_year.items() if len(d) > 7000)
    return by_year[year], year


def read_sepe(path: Path) -> tuple[dict, str]:
    """{municipi: aturats} del darrer mes del fitxer."""
    rows = list(csv.reader(open(path, encoding="latin-1"), delimiter=";"))
    months = [r[0] for r in rows if r and r[0].strip().isdigit()]
    last = max(months)
    out = {}
    for r in rows:
        if r and r[0] == last:
            v = r[8].strip()
            out[r[6].strip().zfill(5)] = 2 if v.startswith("<") else int(v or 0)
    return out, last


def build(ine_csv: Path, sepe_csv: Path) -> int:
    ine, year = read_ine(Path(ine_csv))
    paro, month = read_sepe(Path(sepe_csv))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(FIELDS)
        for code in sorted(set(ine) | set(paro)):
            d = ine.get(code, {})
            pob = d.get("poblacio")
            atur = paro.get(code)
            work = None
            if pob and d.get("pct65") is not None and d.get("pct18") is not None:
                work = pob * (100 - d["pct65"] - d["pct18"]) / 100
            pct_atur = round(100 * atur / work, 1) if (atur is not None and work) else None
            w.writerow([code, year if d else "", int(pob) if pob else "", d.get("edat", ""),
                        d.get("pct65", ""), d.get("pct18", ""),
                        round(100 - d["pct_esp"], 1) if d.get("pct_esp") is not None else "",
                        d.get("llar", ""), month if atur is not None else "",
                        atur if atur is not None else "",
                        pct_atur if pct_atur is not None else ""])
            n += 1
    return n


@lru_cache(maxsize=1)
def load() -> dict:
    """{municipi: {camp: valor}} (numeros o None)."""
    if not OUT.exists():
        return {}
    out = {}
    with open(OUT, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["code"]] = {k: (float(v) if v not in ("", None) and k not in ("code", "mes_atur")
                                  else (v or None)) for k, v in r.items()}
    return out


def month_label(yyyymm: str | None, lang: str) -> str:
    if not yyyymm:
        return ""
    ca = ["gener", "febrer", "març", "abril", "maig", "juny", "juliol", "agost", "setembre",
          "octubre", "novembre", "desembre"]
    es = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre"]
    m = int(yyyymm[4:6]) - 1
    return f"{(es if lang == 'es' else ca)[m]} {yyyymm[:4]}"


# ------------------------------------------------- com vota cada grup de municipis

SIZE = [(0, 1000), (1000, 5000), (5000, 20000), (20000, 100000), (100000, 10 ** 9)]


def groups(conn, election="es-general", baseline="congreso-2023", parties_n=6) -> dict:
    """Vot estimat d'avui i vot real del 2023 per grups de municipis: per mida, per
    renda, per edat mitjana, per % d'estrangers i per atur. Cada grup pesa els
    seus municipis pels vots valids del 2023 (un poble de 200 habitants no pesa
    com Madrid). Els talls de renda, edat, estrangers i atur son quintils
    (cinc grups amb el mateix nombre de votants)."""
    from . import renda as rendalib
    soc = load()
    rd = rendalib.load()
    valid, real = {}, {}
    for code, party, votes, vv in conn.execute(
            """SELECT code, party, votes, valid_votes FROM election_result
               WHERE election = ? AND level = 'municipality'""", (baseline,)):
        valid[code] = vv or 0
        real.setdefault(code, {})[party] = votes or 0
    proj: dict = {}
    for code, party, share in conn.execute(
            "SELECT code, party, share FROM projection WHERE election_id = ? AND level = 'municipality'",
            (election,)):
        proj.setdefault(code, {})[party] = share or 0
    codes = [c for c in valid if c in proj and valid[c]]
    metric = {
        "size": {c: (soc.get(c) or {}).get("poblacio") for c in codes},
        "renda": {c: rd.get(("municipality", c)) for c in codes},
        "edat": {c: (soc.get(c) or {}).get("edat") for c in codes},
        "estr": {c: (soc.get(c) or {}).get("pct_estr") for c in codes},
        "atur": {c: (soc.get(c) or {}).get("pct_atur") for c in codes},
    }
    # Els partits que es mostren: els primers de l'estimacio estatal.
    tot_now: dict = {}
    for c in codes:
        for p, s in proj[c].items():
            tot_now[p] = tot_now.get(p, 0) + s * valid[c]
    top = [p for p, _ in sorted(tot_now.items(), key=lambda x: -x[1]) if p != "OTHER"][:parties_n]

    def summarise(members):
        w = sum(valid[c] for c in members) or 1
        now = {p: sum(proj[c].get(p, 0) * valid[c] for c in members) / w for p in top}
        before = {p: 100 * sum(real[c].get(p, 0) for c in members) / w for p in top}
        return {"n": len(members), "votes": int(w), "now": now, "before": before}

    out = {"parties": top, "dims": {}}
    for dim, vals in metric.items():
        have = [c for c in codes if vals.get(c) is not None]
        if len(have) < 1000:
            continue
        if dim == "size":
            bins = []
            for lo, hi in SIZE:
                members = [c for c in have if lo <= vals[c] < hi]
                if members:
                    bins.append({"lo": lo, "hi": hi, **summarise(members)})
        else:
            have.sort(key=lambda c: vals[c])
            total = sum(valid[c] for c in have)
            bins, acc, cur = [], 0, []
            for c in have:
                cur.append(c)
                acc += valid[c]
                if acc >= total * (len(bins) + 1) / 5 and len(bins) < 4:
                    bins.append({"lo": vals[cur[0]], "hi": vals[cur[-1]], **summarise(cur)})
                    cur = []
            if cur:
                bins.append({"lo": vals[cur[0]], "hi": vals[cur[-1]], **summarise(cur)})
        out["dims"][dim] = bins
    return out


if __name__ == "__main__":
    print(build(Path(sys.argv[1]), Path(sys.argv[2])), "municipis ->", OUT)
