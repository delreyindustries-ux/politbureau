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

Ampliat el mateix dia ("fes-la molt mes detallada i amb moltes mes dades"):
  * qui son: pes a l'electorat (i quanta gent, sobre el cens del 2023), edat
    mitjana, % de dones, universitaris, jubilats, nascuts fora...;
  * participacio: probabilitat mitjana d'anar a votar, % que segur que hi va,
    % que va votar el 2023;
  * opinions sobre politiques concretes (preguntes d'actualitat de cada
    barometre: les onze mesures d'habitatge, fronteres, pacte pel clima,
    preocupacio pel clima, Ucraina, l'Orient Mitja, confianca en els lider);
  * nota dels ministres, vot directe, record del 2023, cap a on han anat els
    votants de cada partit, partit mes proper, moment de decidir;
  * per a cada partit, el retrat dels seus votants i dels que te a l'abast
    (per sexe, edat, estudis, classe, religio...) i les seves opinions;
  * segments creuats: sexe x edat.

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


# --------------------------------------------------------------------- opinions
# Preguntes d'actualitat de cada barometre (21/11/2026). Es troben pel text de
# la pregunta, perque el codi canvia d'un estudi a l'altre (el canvi climatic es
# P8 al 3571 i al 3582 i P13 al 3577). (clau, bloc, ca, es, text de la
# pregunta, respostes que compten com a "si"). El % es sobre qui respon
# (sense N.S., N.C. ni "no procede").
_MUCH = ("Mucho", "Bastante")
_MUCH2 = ("Mucho", "Bastante", "Muy preocupado/a", "Bastante preocupado/a")
OPINIONS = [
    ("viv_desah", "housing", "Prohibir els desnonaments de llars vulnerables fins al 2030",
     "Prohibir los desahucios de hogares vulnerables hasta 2030", "VIVIENDA_1:", ("A favor",)),
    ("viv_prorroga", "housing", "Pròrroga automàtica de dos anys dels lloguers que acaben",
     "Prórroga automática de dos años de los alquileres que terminan", "VIVIENDA_2:", ("A favor",)),
    ("viv_temporada", "housing", "Endurir els lloguers de temporada i per habitacions",
     "Endurecer los alquileres de temporada y por habitaciones", "VIVIENDA_3:", ("A favor",)),
    ("viv_fons", "housing", "Prohibir temporalment la compra d'habitatges als fons voltor",
     "Prohibir temporalmente la compra de viviendas a los fondos buitre", "VIVIENDA_4:", ("A favor",)),
    ("viv_ibi", "housing", "Més IBI als pisos buits i turístics", "Más IBI a los pisos vacíos y turísticos",
     "VIVIENDA_5:", ("A favor",)),
    ("viv_propietaris", "housing", "Rebaixes d'impostos als propietaris que abaixin o congelin el lloguer",
     "Rebajas de impuestos a propietarios que bajen o congelen el alquiler", "VIVIENDA_6:", ("A favor",)),
    ("viv_inquilins", "housing", "Rebaixes d'impostos als inquilins", "Rebajas de impuestos a los inquilinos",
     "VIVIENDA_7:", ("A favor",)),
    ("viv_turistics", "housing", "Impost del 10 % als pisos turístics", "Impuesto del 10 % a los pisos turísticos",
     "VIVIENDA_8:", ("A favor",)),
    ("viv_indefinits", "housing", "Lloguers indefinits", "Alquileres indefinidos", "VIVIENDA_9:", ("A favor",)),
    ("viv_ico", "housing", "Crèdit de l'ICO de 50.000 € sense interessos per a la primera casa",
     "Crédito del ICO de 50.000 € sin intereses para la primera vivienda", "VIVIENDA_10:", ("A favor",)),
    ("viv_iva", "housing", "IVA del 4 % per construir habitatge protegit", "IVA del 4 % para construir vivienda protegida",
     "VIVIENDA_11:", ("A favor",)),
    ("viv_dret", "housing", "L'habitatge, abans dret constitucional que bé de mercat",
     "La vivienda, antes derecho constitucional que bien de mercado", "Prioridad de vivienda como derecho",
     ("El derecho a la vivienda como un derecho constitucional",)),
    ("vulnerables", "housing", "Davant d'un desnonament, abans protegir el vulnerable que complir el contracte",
     "Ante un desahucio, antes proteger al vulnerable que cumplir el contrato",
     "cumplimiento de la ley o la protección de personas vulnerables", ("La protección de personas vulnerables",)),
    ("fronteres", "security", "Cal reforçar les fronteres per evitar entrades massives",
     "Hay que reforzar las fronteras para evitar entradas masivas", "refuerzo de las fronteras",
     ("Sí, cree que es necesario",)),
    ("papa_immig", "security", "D'acord amb el que diu el papa Lleó XIV sobre la immigració",
     "De acuerdo con lo que dice el papa León XIV sobre la inmigración", "manifestaciones del papa León XIV sobre la inmigración",
     ("De acuerdo", "Muy de acuerdo")),
    ("pacte_clima", "climate", "Cal un pacte d'Estat per a les emergències del canvi climàtic",
     "Hace falta un pacto de Estado para las emergencias del cambio climático", "pacto de Estado para hacer frente",
     ("Sí es necesario",)),
    ("clima", "climate", "Li preocupa (molt o bastant) el canvi climàtic",
     "Le preocupa (mucho o bastante) el cambio climático", "preocupación por el cambio climático", _MUCH),
    ("incendis", "climate", "Li preocupen (molt o bastant) els incendis", "Le preocupan (mucho o bastante) los incendios",
     "preocupación por los incendios", _MUCH),
    ("ucraina", "world", "Li preocupa (molt o bastant) la invasió russa d'Ucraïna",
     "Le preocupa (mucho o bastante) la invasión rusa de Ucrania", "preocupación por la invasión de Rusia", _MUCH2),
    ("orient", "world", "Li preocupa (molt o bastant) el conflicte a l'Orient Mitjà",
     "Le preocupa (mucho o bastante) el conflicto en Oriente Próximo", "preocupación por el conflicto en Oriente", _MUCH2),
    ("conf_pte", "leaders", "Confia (molt o bastant) en Pedro Sánchez", "Confía (mucho o bastante) en Pedro Sánchez",
     "confianza en el presidente del Gobierno", ("Mucha confianza", "Bastante confianza")),
    ("conf_opo", "leaders", "Confia (molt o bastant) en Alberto Núñez Feijóo",
     "Confía (mucho o bastante) en Alberto Núñez Feijóo", "confianza en el líder del principal partido de la oposición",
     ("Mucha confianza", "Bastante confianza")),
]
BLOCKS = {"housing": ("Habitatge", "Vivienda"), "security": ("Fronteres i immigració", "Fronteras e inmigración"),
          "climate": ("Clima i emergències", "Clima y emergencias"), "world": ("Món", "Mundo"),
          "leaders": ("Confiança en els líders", "Confianza en los líderes")}
NOT_VALID = {"", "N.S.", "N.C.", "N.P.", "No procede", "N.S., no tiene información suficiente"}
MVOTO = [("Lo decide mucho antes", "molt abans de la campanya", "mucho antes de la campaña"),
         ("Lo decide al comienzo", "a l'inici de la campanya", "al inicio de la campaña"),
         ("Lo decide durante la última semana", "l'última setmana", "la última semana"),
         ("Lo decide durante la jornada de reflexión", "la jornada de reflexió", "la jornada de reflexión"),
         ("Lo decide el mismo día", "el mateix dia", "el mismo día")]
DIRECT = {"No sabe todavía": "UND", "N.S.": "UND", "No votaría": "ABS", "En blanco": "BLANK", "Voto nulo": "BLANK"}
COMPOSE = [
    ("women", "Dones", "Mujeres", lambda r: r.get("SEXO") == "Mujer"),
    ("univ", "Universitaris", "Universitarios", lambda r: r.get("ESTUDIOS") == "Superiores"),
    ("working", "Treballen", "Trabajan", lambda r: r.get("SITLAB") == "Trabaja"),
    ("retired", "Jubilats i pensionistes", "Jubilados y pensionistas",
     lambda r: (r.get("SITLAB") or "").startswith(("Jubilado", "Pensionista"))),
    ("abroad", "Nascuts fora d'Espanya", "Nacidos fuera de España", lambda r: r.get("PAISNAC") == "En otro país"),
    ("catholic", "Catòlics practicants", "Católicos practicantes", lambda r: r.get("RELIGION") == "Católico/a practicante"),
    ("big", "Viuen en ciutats de més de 100.000 habitants", "Viven en ciudades de más de 100.000 habitantes",
     lambda r: r.get("TAMUNI") in ("100.001 a 400.000 habitantes", "400.001 a 1.000.000 habitantes",
                                   "Más de 1.000.000 habitantes")),
]
# Retrat dels votants de cada partit: aquestes dimensions de collectius.DIMS.
PORTRAIT_DIMS = ("sex", "age", "studies", "work", "class", "income", "religion", "town", "origin")


def _direct(r):
    v = (r.get("INTENCIONG") or "").strip()
    return PARTY.get(v) or DIRECT.get(v) or ("OTH" if v and v not in ("N.C.",) else None)


def _opinions(a: "_Acc"):
    out = {}
    for key, *_rest in OPINIONS:
        col = "_op_" + key
        num = den = 0.0
        n = 0
        pos = OPINION_POS[key]
        for r, w in zip(a.rows, a.w):
            v = r.get(col)
            if v is None or v.strip() in NOT_VALID:
                continue
            den += w
            n += 1
            if v.strip() in pos:
                num += w
        if n >= MIN_SUB:
            out[key] = round(100.0 * num / den, 1)
    return out


OPINION_POS = {k: set(pos) for k, _b, _c, _e, _m, pos in OPINIONS}


def _ministers(a: "_Acc"):
    """Nota mitjana de cada ministre entre qui el coneix (n >= 50)."""
    sums = {}
    for r, w in zip(a.rows, a.w):
        for name, v in (r.get("_minis") or {}).items():
            x = _num(v)
            if x is None:
                continue
            s = sums.setdefault(name, [0.0, 0.0, 0])
            s[0] += w * x
            s[1] += w
            s[2] += 1
    rows = [(nm, s[0] / s[1], s[2]) for nm, s in sums.items() if s[2] >= MIN_SUB]
    rows.sort(key=lambda x: -x[1])
    return [{"name": nm, "mean": round(m, 1), "n": n} for nm, m, n in rows]


def profile(rows, all_issues, electorate, dims_fn=None, deep=False):
    a = _Acc(rows)
    issues = a.issues()
    personal = a.issues(("PPERSONAL1", "PPERSONAL2", "PPERSONAL3"))
    vote = a.dist(_party)
    distinct = sorted(((k, v, v / all_issues[k]) for k, v in issues.items()
                       if all_issues.get(k) and v >= 5 and v / all_issues[k] >= 1.25), key=lambda x: -x[2])[:4]
    eligible = lambda r: not any(x in (r.get("PARTICIPACIONG") or "").lower() for x in ("edad", "derecho"))  # noqa: E731
    out = {
        "n": len(rows),
        "size": round(100.0 * a.tot / TOTAL_W, 1),
        "people": round(electorate * a.tot / TOTAL_W, -3),
        "who": {k: round(a.pct(fn), 1) for k, _c, _e, fn in COMPOSE},
        "age": round(a.mean(lambda r: _num(r.get("EDAD"))) or 0, 1),
        "issues": [{"k": k, "l": _label(k), "p": round(v, 1), "lift": round(v / all_issues[k], 2)
                    if all_issues.get(k) else None} for k, v in _top(issues, 12)],
        "distinct": [{"k": k, "l": _label(k), "p": round(v, 1), "lift": round(x, 2)} for k, v, x in distinct],
        "personal": [{"k": k, "l": _label(k), "p": round(v, 1)} for k, v in _top(personal, 6)],
        "vote": {k: round(v, 1) for k, v in sorted(vote.items(), key=lambda kv: -kv[1])},
        "direct": {k: round(v, 1) for k, v in _top(a.dist(_direct), 10)},
        "recall": {k: round(v, 1) for k, v in _top(a.dist(lambda r: _party(r, "RECUVOTOG") or (
            "ABS" if (r.get("PARTICIPACIONG") or "").startswith("No votó") else None), base=eligible), 8)},
        "volatile": round(a.pct(lambda r: (r.get("FIDEVOTO") or "").startswith("Según lo que más")), 1),
        "always": round(a.pct(lambda r: (r.get("FIDEVOTO") or "").startswith("Votan siempre")), 1),
        "late": round(a.pct(lambda r: (r.get("MVOTO") or "").startswith(("Lo decide al comienzo", "Lo decide durante",
                                                                           "Lo decide el mismo"))), 1),
        "when": [{"l": {"ca": ca, "es": es}, "p": round(a.pct(lambda r, m=m: (r.get("MVOTO") or "").startswith(m)), 1)}
                 for m, ca, es in MVOTO],
        "undecided": round(a.pct(lambda r: (r.get("INTENCIONG") or "").strip() in UNDECIDED), 1),
        "sure": round(a.pct(lambda r: (r.get("PROBVOTO") or "").startswith("10")), 1),
        "prob": round(a.mean(lambda r: _num(r.get("PROBVOTO"))) or 0, 1),
        "voted23": round(a.pct(lambda r: (r.get("PARTICIPACIONG") or "").startswith("Votó"), base=eligible) or 0, 1),
        "ideology": round(a.mean(lambda r: _num(r.get("ESCIDEOL"))) or 0, 1),
        "ideo_dist": [round(a.pct(lambda r, lo=lo: (_num(r.get("ESCIDEOL")) or 0) in (lo, lo + 1),
                                  base=lambda r: _num(r.get("ESCIDEOL")) is not None) or 0, 1) for lo in (1, 3, 5, 7, 9)],
        "eco_personal": round(a.pct(lambda r: r.get("ECOPER") in ("Buena", "Muy buena"),
                                    base=lambda r: r.get("ECOPER") not in ("N.S.", "N.C.", None, "")) or 0, 1),
        "eco_spain": round(a.pct(lambda r: r.get("ECOESP") in ("Buena", "Muy buena"),
                                 base=lambda r: r.get("ECOESP") not in ("N.S.", "N.C.", None, "")) or 0, 1),
        "leaders": [{"name": nm, "mean": round(a.mean(lambda r, c=col: _num(r.get(c))) or 0, 1),
                     "good": round(a.pct(lambda r, c=col: (_num(r.get(c)) or 0) >= 6,
                                         base=lambda r, c=col: _num(r.get(c)) is not None) or 0, 1)} for col, nm in LEADERS],
        "pm": [{"name": k, "p": round(v, 1)} for k, v in _top(a.dist(lambda r: (r.get("PREFPTE") or "").strip() or None), 6)],
        "close": {k: round(v, 1) for k, v in _top(a.dist(lambda r: _party(r, "CERCANIA") or (
            "NONE" if (r.get("CERCANIA") or "").startswith("Ninguno") else None)), 6)},
        "ops": _opinions(a),
        "ministers": (lambda m: m if deep else m[:3] + m[-2:] if len(m) > 5 else m)(_ministers(a)),
        "parties": {},
    }
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
            "reach_people": round(electorate * (wr.tot if wr else 0) / TOTAL_W, -3),
            "n_reach": len(reach),
        }
        if len(was) >= MIN_SUB:
            wa = _Acc(was)
            rec["loyal"] = round(wa.pct(lambda r: _party(r, "INTENCIONG") == p), 1)
            rec["went"] = [{"k": k, "p": round(v, 1)} for k, v in _top(wa.dist(_direct), 4) if k != p][:3]
            rec["n_was"] = len(was)
        if wr and len(reach) >= MIN_SUB:
            src = wr.dist(lambda r: _party(r, "INTENCIONG") or
                          ("UND" if (r.get("INTENCIONG") or "").strip() in UNDECIDED else "OTH"))
            rec["from"] = [{"k": k, "p": round(v, 1)} for k, v in _top(src, 3)]
            rec["issues"] = [{"k": k, "l": _label(k), "p": round(v, 1)} for k, v in _top(wr.issues(), 5)]
            if deep:
                rec["ops_reach"] = _opinions(wr)
                rec["ideo_reach"] = round(wr.mean(lambda r: _num(r.get("ESCIDEOL"))) or 0, 1)
                rec["age_reach"] = round(wr.mean(lambda r: _num(r.get("EDAD"))) or 0, 1)
                rec["who_reach"] = {k: round(wr.pct(fn), 1) for k, _c, _e, fn in COMPOSE}
        if len(voters) >= MIN_SUB:
            wv = _Acc(voters)
            rec["risk"] = [{"k": k, "p": round(v, 1)} for k, v in _top(wv.dist(lambda r: _party(r, "INTENCIONGALTER")), 3) if k != p][:2]
            rec["n_voters"] = len(voters)
            if deep:
                rec["ops_voters"] = _opinions(wv)
                rec["issues_voters"] = [{"k": k, "l": _label(k), "p": round(v, 1)} for k, v in _top(wv.issues(), 5)]
                rec["ideo_voters"] = round(wv.mean(lambda r: _num(r.get("ESCIDEOL"))) or 0, 1)
                rec["age_voters"] = round(wv.mean(lambda r: _num(r.get("EDAD"))) or 0, 1)
                rec["who_voters"] = {k: round(wv.pct(fn), 1) for k, _c, _e, fn in COMPOSE}
                rec["sure_voters"] = round(wv.pct(lambda r: (r.get("PROBVOTO") or "").startswith("10")), 1)
                if dims_fn:
                    rec["portrait"] = dims_fn(voters, reach)
        out["parties"][p] = rec
    return out


def _load(path: Path):
    """Com collectius._read, pero desa a cada fila les preguntes d'actualitat
    (per text de la pregunta) i les notes dels ministres (pel nom)."""
    import csv
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f, delimiter=";"))
    full = rows[0]
    head = [c.split(":")[0].strip() for c in full]
    op_idx = {}
    for key, _b, _c, _e, match, _pos in OPINIONS:
        for i, c in enumerate(full):
            if (c.startswith(match) if match.endswith(":") else match in c):
                op_idx[key] = i
                break
    minis = [(i, c.split(":", 1)[1].strip()) for i, c in enumerate(full) if c.startswith("VALMINIS_") and ":" in c]
    out = []
    for r in rows[1:]:
        if len(r) != len(head):
            continue
        d = dict(zip(head, r))
        for key, i in op_idx.items():
            d["_op_" + key] = r[i]
        if minis:
            d["_minis"] = {nm: r[i] for i, nm in minis}
        out.append(d)
    return out


def _electorate():
    try:
        from . import db
        from .site.build import BASELINE
        conn = db.connect()
        rows = conn.execute("SELECT code, MAX(census) FROM election_result WHERE election = ? AND level = 'province' "
                            "GROUP BY code", (BASELINE,)).fetchall()
        return sum(r[1] or 0 for r in rows) or 35_140_881
    except Exception:                                      # noqa: BLE001
        return 35_140_881


TOTAL_W = 1.0
# Segments creuats (21/11/2026): sexe x edat.
CROSS = [(f"sexage:{s}:{ag}", {"ca": f"{sca} de {agca}", "es": f"{ses} de {ages}"},
          lambda r, s=s, ag=ag: r.get("SEXO") == s and _age_of(r) == ag)
         for s, sca, ses in (("Mujer", "Dones", "Mujeres"), ("Hombre", "Homes", "Hombres"))
         for ag, agca, ages in (("18-29", "18 a 29 anys", "18 a 29 años"), ("30-44", "30 a 44 anys", "30 a 44 años"),
                                ("45-64", "45 a 64 anys", "45 a 64 años"), ("65+", "65 anys o més", "65 años o más"))]


def _age_of(r):
    from .collectius import _age
    return _age(r.get("EDAD"))


def run() -> dict | None:
    global TOTAL_W
    files = sorted(RAW.glob("*/*_etiq.csv"))
    if not files:
        return None
    rows, studies = [], []
    for f in files:
        studies.append(f.parent.name)
        rows += [r for r in _load(f) if _weight(r.get("PESO")) > 0]
    TOTAL_W = _Acc(rows).tot
    electorate = _electorate()
    all_issues = _Acc(rows).issues()
    dimfns = []
    for key, title, col, cats in DIMS:
        fn = col if callable(col) else (lambda r, c=col: r.get(c))
        dimfns.append((key, title, fn, cats))

    def portrait(voters, reach):
        """Com es reparteixen els votants (i els que te a l'abast) a cada dimensio."""
        av, ar, at = _Acc(voters), _Acc(reach) if reach else None, _Acc(rows)
        res = []
        for key, title, fn, cats in dimfns:
            if key not in PORTRAIT_DIMS:
                continue
            base = lambda r, f=fn, vals={c[0] for c in cats}: f(r) in vals            # noqa: E731
            cells = []
            for value, ca, es in cats:
                pick = lambda r, f=fn, v=value: f(r) == v                           # noqa: E731
                cells.append({"l": {"ca": ca, "es": es}, "v": round(av.pct(pick, base=base) or 0, 1),
                              "r": round(ar.pct(pick, base=base) or 0, 1) if ar and len(reach) >= MIN_SUB else None,
                              "t": round(at.pct(pick, base=base) or 0, 1)})
            res.append({"key": key, "title": title, "cells": cells})
        return res

    total = profile(rows, all_issues, electorate, dims_fn=portrait, deep=True)
    dims = []
    cross = []
    for gid, label, fn in CROSS:
        g = [r for r in rows if fn(r)]
        if len(g) >= MIN_N:
            cross.append({"id": gid, "label": label, **profile(g, all_issues, electorate)})
    if cross:
        dims.append({"key": "sexage", "title": {"ca": "Sexe i edat", "es": "Sexo y edad"}, "groups": cross})
    for key, title, fn, cats in dimfns:
        groups = []
        for value, ca, es in cats:
            g = [r for r in rows if fn(r) == value]
            if len(g) < MIN_N:
                continue
            groups.append({"id": f"{key}:{value}", "label": {"ca": ca, "es": es},
                           **profile(g, all_issues, electorate)})
        if groups:
            dims.append({"key": key, "title": title, "groups": groups})
    ops_meta = [{"k": k, "b": b, "l": {"ca": ca, "es": es}} for k, b, ca, es, _m, _p in OPINIONS]
    data = {"computed": dt.date.today().isoformat(), "studies": studies, "n": len(rows), "focus": FOCUS,
            "electorate": electorate, "ops": ops_meta,
            "blocks": {k: {"ca": v[0], "es": v[1]} for k, v in BLOCKS.items()},
            "compose": [{"k": k, "l": {"ca": ca, "es": es}} for k, ca, es, _f in COMPOSE],
            "total": total, "dims": dims,
            "source": "Origen de los datos: Centro de Investigaciones Sociológicas (CIS), barómetros "
                      + ", ".join(studies)}
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return data
