"""Perfils de votants (21/11/2026, demanat per l'Alfonso: "una funcio de perfils
de votants, tenint en compte tots els col·lectius, els seus interessos politics
i com se'ls podria convencer; molt util per als partits").

Font: les mateixes microdades del CIS que collectius.py (data/raw/cis/, fora
del git). Nomes en surten agregats: config/perfils.json.

Per a cada col·lectiu (els mateixos grups de collectius.DIMS, mes "tothom"):
  * temes: % que esmenta cada problema d'Espanya (PESPANNA1-3, fins a tres
    respostes) i dels seus problemes personals (PPERSONAL1-3); els temes que
    el distingeixen son els que hi pesen almenys 1,25 vegades mes que a la
    mitjana i els esmenta com a minim un 5 %;
  * vot: VOTOSIMG (vot + simpatia), sobre qui diu un partit;
  * com de mobil es: % que vota "segons el que el convenci en cada moment"
    (FIDEVOTO), % que decideix durant la campanya o despres (MVOTO), % que
    encara no sap a qui votara (INTENCIONG "No sabe todavia" o N.S.);
  * ideologia mitjana (1-10), economia personal i d'Espanya (% bona o molt
    bona), nota mitjana dels quatre lideres (VALORALIDERES_1-4) i preferit
    per presidir el Govern (PREFPTE).
  * per a cada partit:
      - el seu % al grup i la fidelitat: dels seus votants del 2023
        (RECUVOTOG), quants el tornarien a votar;
      - "a l'abast": votants probables (PROBVOTO 5 o mes) que avui no el
        voten (INTENCIONG, el vot directe, sense la simpatia) pero el tenen de
        segona opcio (INTENCIONGALTER), o que no saben a qui votaran i el
        consideren el mes proper (CERCANIA); en % del grup;
      - d'on vindrien (el partit que voten ara els qui el tenen de segona
        opcio) i on pot perdre (la segona opcio dels seus votants);
      - de que parlen els votants a l'abast: els seus problemes principals.

Tot ponderat amb PESO. Grups de menys de 100 entrevistes, fora; un subgrup
(per exemple, els votants a l'abast d'un partit en un grup) de menys de 50,
sense temes.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from .collectius import DIMS, RAW, _read, _weight

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "config" / "perfils.json"
MIN_N = 100
MIN_SUB = 50

PARTY = {"PSOE": "PSOE", "PP": "PP", "VOX": "VOX", "Sumar": "SUMAR", "Podemos": "PODEMOS",
         "ERC": "ERC", "Se Acabó la Fiesta": "SALF", "EH Bildu": "EHB", "Junts": "JUNTS",
         "BNG": "BNG", "EAJ-PNV": "PNV", "Aliança Catalana": "AA"}
FOCUS = ["PP", "PSOE", "VOX", "SUMAR", "PODEMOS", "SALF", "ERC"]
UNDECIDED = {"No sabe todavía", "N.S."}
LEADERS = [("VALORALIDERES_1", "Pedro Sánchez"), ("VALORALIDERES_2", "Alberto Núñez Feijóo"),
           ("VALORALIDERES_3", "Yolanda Díaz"), ("VALORALIDERES_4", "Santiago Abascal")]
SKIP_ISSUE = {"N.S.", "N.C.", "Otras respuestas", "", "N.P.", "No procede", "Ninguno"}
# Noms curts dels problemes del CIS (ca, es). La resta es mostra tal com ve.
ISSUE = {
    "La vivienda": ("Habitatge", "Vivienda"),
    "El Gobierno y partidos o políticos/as concretos/as": ("El Govern i els polítics", "El Gobierno y los políticos"),
    "Los problemas políticos en general": ("La política en general", "La política en general"),
    "La crisis económica, los problemas de índole económica": ("Economia", "Economía"),
    "El mal comportamiento de los/as políticos/as": ("Comportament dels polítics", "Comportamiento de los políticos"),
    "La inmigración": ("Immigració", "Inmigración"),
    "Los extremismos": ("Extremismes", "Extremismos"),
    "La corrupción y el fraude": ("Corrupció", "Corrupción"),
    "Los problemas relacionados con la calidad del empleo": ("Qualitat de la feina", "Calidad del empleo"),
    "Lo que hacen los partidos políticos": ("El que fan els partits", "Lo que hacen los partidos"),
    "El paro": ("Atur", "Paro"),
    "Los problemas relacionados con la juventud. Falta de apoyo y oportunidades para los/as jóvenes":
        ("Joventut i oportunitats", "Juventud y oportunidades"),
    "Las desigualdades, incluida la de género, diferencias de clases, la pobreza":
        ("Desigualtat i pobresa", "Desigualdad y pobreza"),
    "La falta de acuerdos, unidad y capacidad de colaboración. Situación e inestabilidad política":
        ("Falta d'acords", "Falta de acuerdos"),
    "Aumento de la crispación social, revueltas sociales": ("Crispació", "Crispación"),
    "Crisis con Marruecos. Fronteras de Ceuta y Melilla": ("Marroc i fronteres", "Marruecos y fronteras"),
    "La crisis de valores": ("Crisi de valors", "Crisis de valores"),
    "Los problemas de índole social": ("Problemes socials", "Problemas sociales"),
    "La sanidad": ("Sanitat", "Sanidad"),
    "La subida de los impuestos": ("Impostos", "Impuestos"),
    "El funcionamiento de los servicios públicos": ("Serveis públics", "Servicios públicos"),
    "El funcionamiento de la democracia": ("Funcionament de la democràcia", "Funcionamiento de la democracia"),
    "La inseguridad ciudadana": ("Inseguretat", "Inseguridad"),
    "Papel de los medios de comunicación y redes: desinformación, manipulación informativa, difusión de bulos":
        ("Desinformació", "Desinformación"),
    "La educación": ("Educació", "Educación"),
    "La Administración de Justicia": ("Justícia", "Justicia"),
    "El cambio climático": ("Canvi climàtic", "Cambio climático"),
    "La falta de confianza en los/las políticos/as y las instituciones": ("Desconfiança en les institucions",
                                                                        "Desconfianza en las instituciones"),
    "Las pensiones": ("Pensions", "Pensiones"),
    "Los problemas de índole económica": ("Economia", "Economía"),
    "Los problemas relacionados con la mujer": ("Problemes de les dones", "Problemas de las mujeres"),
    "La violencia contra la mujer": ("Violència masclista", "Violencia machista"),
    "Las guerras en general": ("Guerres", "Guerras"),
    "El nacionalismo, independencia de Cataluña": ("Independentisme", "Independentismo"),
    "Los problemas de la agricultura, ganadería y pesca": ("Camp i pesca", "Campo y pesca"),
    "La dependencia": ("Dependència", "Dependencia"),
    "La okupación de viviendas": ("Ocupació d'habitatges", "Okupación de viviendas"),
    "Las preocupaciones y situaciones personales": ("Situació personal", "Situación personal"),
    "La subida de precios. La inflación. Pérdida de poder adquisitivo": ("Preus i inflació", "Precios e inflación"),
}


def _num(v):
    try:
        return float((v or "").split()[0])
    except (ValueError, IndexError):
        return None


def _label(issue):
    ca, es = ISSUE.get(issue, (issue, issue))
    return {"ca": ca, "es": es}


class _Acc:
    """Sumes ponderades d'un conjunt d'entrevistes."""

    def __init__(self, rows):
        self.rows = rows
        self.w = [_weight(r.get("PESO")) for r in rows]
        self.tot = sum(self.w) or 1.0

    def pct(self, pred, base=None):
        num = den = 0.0
        for r, w in zip(self.rows, self.w):
            if base and not base(r):
                continue
            den += w
            if pred(r):
                num += w
        return 100.0 * num / den if den else None

    def mean(self, fn):
        num = den = 0.0
        for r, w in zip(self.rows, self.w):
            x = fn(r)
            if x is not None:
                num += w * x
                den += w
        return num / den if den else None

    def dist(self, fn, base=None):
        out, den = {}, 0.0
        for r, w in zip(self.rows, self.w):
            if base and not base(r):
                continue
            k = fn(r)
            if k is None:
                continue
            den += w
            out[k] = out.get(k, 0.0) + w
        return {k: 100.0 * v / den for k, v in out.items()} if den else {}

    def issues(self, cols=("PESPANNA1", "PESPANNA2", "PESPANNA3")):
        out = {}
        for r, w in zip(self.rows, self.w):
            seen = {(r.get(c) or "").strip() for c in cols} - SKIP_ISSUE
            for i in seen:
                out[i] = out.get(i, 0.0) + w
        return {k: 100.0 * v / self.tot for k, v in out.items()}


def _party(r, col="VOTOSIMG"):
    return PARTY.get((r.get(col) or "").strip())


def _probable(r):
    p = _num(r.get("PROBVOTO"))
    return p is None or p >= 5


def _top(d, n, min_pct=0.0):
    return [(k, v) for k, v in sorted(d.items(), key=lambda kv: -kv[1]) if v >= min_pct][:n]


def profile(rows, all_issues):
    a = _Acc(rows)
    issues = a.issues()
    personal = a.issues(("PPERSONAL1", "PPERSONAL2", "PPERSONAL3"))
    vote = a.dist(_party)
    distinct = sorted(((k, v, v / all_issues[k]) for k, v in issues.items()
                       if all_issues.get(k) and v >= 5 and v / all_issues[k] >= 1.25), key=lambda x: -x[2])[:3]
    with_party = lambda r: bool(_party(r))                               # noqa: E731
    out = {
        "n": len(rows),
        "issues": [{"k": k, "l": _label(k), "p": round(v, 1), "lift": round(v / all_issues[k], 2)
                    if all_issues.get(k) else None} for k, v in _top(issues, 6)],
        "distinct": [{"k": k, "l": _label(k), "p": round(v, 1), "lift": round(x, 2)} for k, v, x in distinct],
        "personal": [{"k": k, "l": _label(k), "p": round(v, 1)} for k, v in _top(personal, 3)],
        "vote": {k: round(v, 1) for k, v in sorted(vote.items(), key=lambda kv: -kv[1])},
        "volatile": round(a.pct(lambda r: (r.get("FIDEVOTO") or "").startswith("Según lo que más")), 1),
        "late": round(a.pct(lambda r: (r.get("MVOTO") or "").startswith(("Lo decide al comienzo", "Lo decide durante",
                                                                           "Lo decide el mismo"))), 1),
        "undecided": round(a.pct(lambda r: (r.get("INTENCIONG") or "").strip() in UNDECIDED), 1),
        "ideology": round(a.mean(lambda r: _num(r.get("ESCIDEOL"))) or 0, 1),
        "eco_personal": round(a.pct(lambda r: r.get("ECOPER") in ("Buena", "Muy buena"),
                                    base=lambda r: r.get("ECOPER") not in ("N.S.", "N.C.", None, "")) or 0, 1),
        "eco_spain": round(a.pct(lambda r: r.get("ECOESP") in ("Buena", "Muy buena"),
                                 base=lambda r: r.get("ECOESP") not in ("N.S.", "N.C.", None, "")) or 0, 1),
        "leaders": [{"name": nm, "mean": round(a.mean(lambda r, c=col: _num(r.get(c))) or 0, 1)} for col, nm in LEADERS],
        "pm": [{"name": k, "p": round(v, 1)} for k, v in _top(a.dist(lambda r: (r.get("PREFPTE") or "").strip() or None), 4)],
        "parties": {},
    }
    _ = with_party
    for p in FOCUS:
        voters = [r for r in rows if _party(r, "INTENCIONG") == p]
        was = [r for r in rows if _party(r, "RECUVOTOG") == p]
        reach = [r for r in rows if _probable(r) and _party(r, "INTENCIONG") != p and (
            _party(r, "INTENCIONGALTER") == p or
            ((r.get("INTENCIONG") or "").strip() in UNDECIDED and _party(r, "CERCANIA") == p))]
        wr = _Acc(reach) if reach else None
        rec = {
            "share": vote.get(p, 0.0) and round(vote[p], 1),
            "reach": round(100.0 * (wr.tot if wr else 0) / a.tot, 1),
            "n_reach": len(reach),
        }
        if len(was) >= MIN_SUB:
            rec["loyal"] = round(_Acc(was).pct(lambda r: _party(r) == p), 1)
        if wr and len(reach) >= MIN_SUB:
            src = wr.dist(lambda r: _party(r, "INTENCIONG") or
                          ("UND" if (r.get("INTENCIONG") or "").strip() in UNDECIDED else "OTH"))
            rec["from"] = [{"k": k, "p": round(v, 1)} for k, v in _top(src, 3)]
            ri = wr.issues()
            rec["issues"] = [{"k": k, "l": _label(k), "p": round(v, 1)} for k, v in _top(ri, 3)]
        if len(voters) >= MIN_SUB:
            alt = _Acc(voters).dist(lambda r: _party(r, "INTENCIONGALTER"))
            rec["risk"] = [{"k": k, "p": round(v, 1)} for k, v in _top(alt, 2) if k != p]
            rec["n_voters"] = len(voters)
        out["parties"][p] = rec
    return out


def run() -> dict | None:
    files = sorted(RAW.glob("*/*_etiq.csv"))
    if not files:
        return None
    rows, studies = [], []
    for f in files:
        studies.append(f.parent.name)
        rows += [r for r in _read(f) if _weight(r.get("PESO")) > 0]
    all_issues = _Acc(rows).issues()
    total = profile(rows, all_issues)
    dims = []
    for key, title, col, cats in DIMS:
        fn = col if callable(col) else (lambda r, c=col: r.get(c))
        groups = []
        for value, ca, es in cats:
            g = [r for r in rows if fn(r) == value]
            if len(g) < MIN_N:
                continue
            groups.append({"id": f"{key}:{value}", "label": {"ca": ca, "es": es}, **profile(g, all_issues)})
        if groups:
            dims.append({"key": key, "title": title, "groups": groups})
    data = {"computed": dt.date.today().isoformat(), "studies": studies, "n": len(rows), "focus": FOCUS,
            "total": total, "dims": dims,
            "source": "Origen de los datos: Centro de Investigaciones Sociológicas (CIS), barómetros "
                      + ", ".join(studies)}
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return data
