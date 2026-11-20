"""Com vota cada col·lectiu (20/11/2026, demanat per l'Alfonso: "una analisi per
a cada col·lectiu de la societat, genere, professio, etnia i altres").

Font: microdades dels barometres del CIS (respostes anonimes, una fila per
entrevista). Les condicions del CIS en permeten la reutilitzacio, tambe
comercial, citant "Origen de los datos: Centro de Investigaciones
Sociologicas" i la data d'actualitzacio.

Els fitxers en brut van a data/raw/cis/<estudi>/<estudi>_etiq.csv (fora del git:
els baixa l'Alfonso, perque el CIS demana un correu per descarregar-los). Aqui
nomes se'n treuen agregats: config/collectius.json, que es el que llegeix la web.

Mesura: "voto + simpatia" (VOTOSIMG) del CIS, ponderat amb el seu pes (PESO,
que corregeix l'excés d'entrevistats amb estudis superiors). Per a cada grup:
  * el % de cada partit entre els qui en diuen un;
  * el % que no en diu cap (no sap, no votaria, en blanc, nul, cap, no contesta);
  * el marge d'error al 95 % del partit mes votat del grup, amb la mida
    efectiva de la mostra (Kish), perque el pes en redueix la precisio.
Un grup amb menys de 100 entrevistes no es mostra.

Etnia: cap enquesta electoral espanyola la pregunta, i el CIS tampoc. El mes
proper es on va neixer la persona entrevistada i si te la nacionalitat des del
naixement. El CIS nomes entrevista persones amb nacionalitat espanyola (les que
voten a les generals): els nascuts fora son espanyols nascuts a l'estranger o
nacionalitzats, no estrangers residents.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "cis"
OUT = ROOT / "config" / "collectius.json"
MIN_N = 100

# Partits de la columna VOTOSIMG del CIS (amb el nom que hi posa el CIS).
PARTIES = [("PSOE", "PSOE"), ("PP", "PP"), ("VOX", "VOX"), ("SUMAR", "Sumar"),
           ("PODEMOS", "Podemos"), ("SALF", "Se Acabó la Fiesta")]
NONE = {"Ninguno", "En blanco", "Voto nulo", "N.S.", "N.C.", "No votaría", "No sabe todavía",
        "No votaría/Ninguno"}

LATAM = {"Venezuela", "Colombia", "Ecuador", "Argentina", "Uruguay", "Perú", "República Dominicana",
         "Chile", "Cuba", "Brasil", "Bolivia", "Paraguay", "México", "Honduras", "Nicaragua",
         "El Salvador", "Guatemala", "Costa Rica", "Panamá", "Puerto Rico"}


def _age(v):
    try:
        a = int(float(v))
    except (TypeError, ValueError):
        return None
    for lo, hi in ((18, 29), (30, 44), (45, 64)):
        if lo <= a <= hi:
            return f"{lo}-{hi}"
    return "65+" if a >= 65 else None


def _ideol(v):
    v = (v or "").split(" ")[0]
    try:
        x = int(v)
    except ValueError:
        return None
    return {1: "1-2", 2: "1-2", 3: "3-4", 4: "3-4", 5: "5-6", 6: "5-6",
            7: "7-8", 8: "7-8", 9: "9-10", 10: "9-10"}[x]


def _origin(row):
    if row.get("PAISNAC") == "En España":
        return "spain"
    if row.get("PAISNAC") == "En otro país":
        return "latam" if row.get("PAISNAC2") in LATAM else "abroad"
    return None


# (clau, titol, columna o funcio, [(valor del CIS, ca, es)]): l'ordre es el de la taula.
DIMS = [
    ("sex", {"ca": "Sexe", "es": "Sexo"}, "SEXO",
     [("Mujer", "Dones", "Mujeres"), ("Hombre", "Homes", "Hombres")]),
    ("age", {"ca": "Edat", "es": "Edad"}, lambda r: _age(r.get("EDAD")),
     [("18-29", "18 a 29 anys", "18 a 29 años"), ("30-44", "30 a 44 anys", "30 a 44 años"),
      ("45-64", "45 a 64 anys", "45 a 64 años"), ("65+", "65 anys o més", "65 años o más")]),
    ("origin", {"ca": "Lloc de naixement", "es": "Lugar de nacimiento"}, _origin,
     [("spain", "Nascuts a Espanya", "Nacidos en España"),
      ("latam", "Nascuts a Llatinoamèrica", "Nacidos en Latinoamérica"),
      ("abroad", "Nascuts a la resta del món", "Nacidos en el resto del mundo")]),
    ("natio", {"ca": "Nacionalitat espanyola", "es": "Nacionalidad española"}, "ADQUINAC",
     [("Desde que nació", "Des del naixement", "Desde el nacimiento"),
      ("La ha adquirido con posterioridad", "Adquirida després", "Adquirida después")]),
    ("studies", {"ca": "Estudis", "es": "Estudios"},
     lambda r: {"Sin estudios": "Primaria", "Primaria": "Primaria"}.get(r.get("ESTUDIOS"), r.get("ESTUDIOS")),
     [("Primaria", "Primària o menys", "Primaria o menos"),
      ("Secundaria 1ª etapa", "Secundària (1a etapa)", "Secundaria (1.ª etapa)"),
      ("Secundaria 2ª etapa", "Batxillerat", "Bachillerato"),
      ("F.P.", "Formació professional", "Formación profesional"),
      ("Superiores", "Universitaris", "Universitarios")]),
    ("work", {"ca": "Situació laboral", "es": "Situación laboral"},
     lambda r: {"Pensionista (anteriormente no ha trabajado)": "Jubilado",
                "Jubilado/a o pensionista (anteriormente ha trabajado)": "Jubilado",
                "En paro y ha trabajado antes": "Paro", "En paro y busca su primer empleo": "Paro"
                }.get(r.get("SITLAB"), r.get("SITLAB")),
     [("Trabaja", "Treballa", "Trabaja"), ("Paro", "A l'atur", "En paro"),
      ("Jubilado", "Jubilats i pensionistes", "Jubilados y pensionistas"),
      ("Estudiante", "Estudiants", "Estudiantes"),
      ("Trabajo doméstico no remunerado", "Treball domèstic no remunerat", "Trabajo doméstico no remunerado")]),
    ("employ", {"ca": "Relació laboral (qui treballa)", "es": "Relación laboral (quien trabaja)"}, "RELALAB",
     [("Asalariado/a por cuenta ajena", "Assalariats", "Asalariados"),
      ("Profesional o trabajador/a autónomo/a (sin asalariados/as)", "Autònoms sense assalariats",
       "Autónomos sin asalariados"),
      ("Empresario/a o profesional con asalariados/as", "Empresaris amb assalariats",
       "Empresarios con asalariados")]),
    ("job", {"ca": "Professió (qui treballa)", "es": "Profesión (quien trabaja)"}, "CNO11",
     [("Directores/as y gerentes", "Directius i gerents", "Directivos y gerentes"),
      ("Profesionales, científicos/as e intelectuales", "Professionals i científics",
       "Profesionales y científicos"),
      ("Técnicos/as y profesionales de nivel medio", "Tècnics de nivell mitjà", "Técnicos de nivel medio"),
      ("Personal de apoyo administrativo", "Administratius", "Administrativos"),
      ("Trabajadores/as de los servicios y vendedores/as de comercios y mercados",
       "Serveis i comerç", "Servicios y comercio"),
      ("Agricultores/as y trabajadores/as cualificados/as agropecuarios, forestales y pesqueros/as",
       "Agricultura i pesca", "Agricultura y pesca"),
      ("Oficiales/as, operarios/as, artesanos/as y trabajadores/as de artes mecánicas y de otros oficios",
       "Oficis i construcció", "Oficios y construcción"),
      ("Operadores/as de instalaciones y máquinas y ensambladores/as", "Operaris de màquines",
       "Operadores de máquinas"),
      ("Ocupaciones elementales", "Ocupacions elementals", "Ocupaciones elementales"),
      ("Ocupaciones militares y cuerpos policiales", "Militars i policies", "Militares y policías")]),
    ("class", {"ca": "Classe social (com s'hi veu)", "es": "Clase social (cómo se ve)"}, "CLASESUB",
     [("Clase alta y media alta", "Alta i mitjana-alta", "Alta y media-alta"),
      ("Clase media-media", "Mitjana", "Media"), ("Clase media-baja", "Mitjana-baixa", "Media-baja"),
      ("Clase trabajadora/obrera/proletariado", "Treballadora", "Trabajadora"),
      ("Clase baja/pobre", "Baixa o pobre", "Baja o pobre")]),
    ("income", {"ca": "Ingressos nets de la llar al mes", "es": "Ingresos netos del hogar al mes"}, "INGRESHOG",
     [("Menos de 1.100 €", "Menys de 1.100 €", "Menos de 1.100 €"),
      ("De 1.100 a 1.800 €", "1.100 a 1.800 €", "1.100 a 1.800 €"),
      ("De 1.801 a 2.700 €", "1.801 a 2.700 €", "1.801 a 2.700 €"),
      ("De 2.701 a 3.900 €", "2.701 a 3.900 €", "2.701 a 3.900 €"),
      ("De 3.901 a 5.000 €", "3.901 a 5.000 €", "3.901 a 5.000 €"),
      ("Más de 5.000 €", "Més de 5.000 €", "Más de 5.000 €")]),
    ("religion", {"ca": "Religió", "es": "Religión"}, "RELIGION",
     [("Católico/a practicante", "Catòlics practicants", "Católicos practicantes"),
      ("Católico/a no practicante", "Catòlics no practicants", "Católicos no practicantes"),
      ("Creyente de otra religión", "D'una altra religió", "De otra religión"),
      ("Agnóstico/a", "Agnòstics", "Agnósticos"),
      ("Indiferente, no creyente", "Indiferents, no creients", "Indiferentes, no creyentes"),
      ("Ateo/a", "Ateus", "Ateos")]),
    ("ideology", {"ca": "Ideologia (1 esquerra, 10 dreta)", "es": "Ideología (1 izquierda, 10 derecha)"},
     lambda r: _ideol(r.get("ESCIDEOL")),
     [("1-2", "1-2", "1-2"), ("3-4", "3-4", "3-4"), ("5-6", "5-6", "5-6"), ("7-8", "7-8", "7-8"),
      ("9-10", "9-10", "9-10")]),
    ("civil", {"ca": "Estat civil", "es": "Estado civil"},
     lambda r: {"Separado/a": "Divorciado/a"}.get(r.get("ECIVIL"), r.get("ECIVIL")),
     [("Soltero/a", "Solters", "Solteros"), ("Casado/a", "Casats", "Casados"),
      ("Divorciado/a", "Divorciats o separats", "Divorciados o separados"), ("Viudo/a", "Vidus", "Viudos")]),
    ("town", {"ca": "Mida del municipi", "es": "Tamaño del municipio"},
     lambda r: {"Menos o igual a 2.000 habitantes": "<10k", "2.001 a 10.000 habitantes": "<10k",
                "10.001 a 50.000 habitantes": "10-50k", "50.001 a 100.000 habitantes": "50-400k",
                "100.001 a 400.000 habitantes": "50-400k", "400.001 a 1.000.000 habitantes": ">400k",
                "Más de 1.000.000 habitantes": ">400k"}.get(r.get("TAMUNI")),
     [("<10k", "Fins a 10.000 habitants", "Hasta 10.000 habitantes"),
      ("10-50k", "10.001 a 50.000", "10.001 a 50.000"),
      ("50-400k", "50.001 a 400.000", "50.001 a 400.000"),
      (">400k", "Més de 400.000", "Más de 400.000")]),
]


def _read(path: Path):
    import csv
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f, delimiter=";"))
    head = [c.split(":")[0].strip() for c in rows[0]]
    return [dict(zip(head, r)) for r in rows[1:] if len(r) == len(head)]


def _weight(v):
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return 0.0


def studies() -> list[Path]:
    return sorted(RAW.glob("*/*_etiq.csv"))


def run() -> dict | None:
    files = studies()
    if not files:
        return None
    rows, meta = [], []
    for f in files:
        got = _read(f)
        sid = f.parent.name
        months = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                  "septiembre", "octubre", "noviembre", "diciembre"]
        dates = sorted(f"{r.get('IA_E1_ANYO').strip()}-{months.index(r['IA_E1_MES'].strip().lower()) + 1:02d}"
                       for r in got if r.get("IA_E1_ANYO") and (r.get("IA_E1_MES") or "").strip().lower() in months)
        meta.append({"id": sid, "n": len(got), "month": dates[len(dates) // 2] if dates else None,
                     "updated": dt.date.fromtimestamp(f.stat().st_mtime).isoformat()})
        rows += got
    by_cis = {v: k for k, v in PARTIES}

    def cell(group):
        w_tot = sum(_weight(r["PESO"]) for r in group)
        w_party = {k: 0.0 for k, _ in PARTIES}
        w_other, w_none = 0.0, 0.0
        for r in group:
            w = _weight(r["PESO"])
            v = (r.get("VOTOSIMG") or "").strip()
            if v in by_cis:
                w_party[by_cis[v]] += w
            elif v in NONE or not v:
                w_none += w
            else:
                w_other += w
        chose = sum(w_party.values()) + w_other
        if not chose:
            return None
        shares = {k: 100.0 * x / chose for k, x in w_party.items()}
        shares["OTHER"] = 100.0 * w_other / chose
        # Mida efectiva (Kish) entre els qui diuen partit
        ws = [_weight(r["PESO"]) for r in group
              if (r.get("VOTOSIMG") or "").strip() not in NONE and (r.get("VOTOSIMG") or "").strip()]
        n_eff = (sum(ws) ** 2 / sum(w * w for w in ws)) if ws else 0
        p = max(shares.values()) / 100.0
        moe = 196.0 * math.sqrt(p * (1 - p) / n_eff) if n_eff else None
        return {"n": len(group), "n_party": len(ws), "shares": {k: round(v, 1) for k, v in shares.items()},
                "none": round(100.0 * w_none / w_tot, 1) if w_tot else None,
                "moe": round(moe, 1) if moe else None}

    total = cell(rows)
    dims = []
    for key, title, col, cats in DIMS:
        fn = col if callable(col) else (lambda r, c=col: r.get(c))
        out = []
        for value, ca, es in cats:
            group = [r for r in rows if fn(r) == value]
            c = cell(group) if len(group) >= MIN_N else None
            out.append({"label": {"ca": ca, "es": es}, "n": len(group),
                        **(c or {}), "hidden": c is None})
        dims.append({"key": key, "title": title, "rows": out})
    data = {"computed": dt.date.today().isoformat(), "studies": meta, "n": len(rows),
            "parties": [{"code": k, "cis": v} for k, v in PARTIES] + [{"code": "OTHER", "cis": "Otros"}],
            "measure": "VOTOSIMG (voto + simpatía), ponderado con PESO",
            "total": total, "dims": dims}
    OUT.write_bytes(json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8"))
    return data


def load() -> dict:
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
