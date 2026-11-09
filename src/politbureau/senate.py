"""Senat: qui guanyaria cada escó el 29N amb l'estimacio d'avui (09/11/2026).

Regles (LOREG art. 165 i 166, text vigent des de la LO 2/2026):
  * 4 senadors per provincia; cada elector en vota fins a 3.
  * Gran Canaria, Mallorca i Tenerife: 3 senadors, fins a 2 vots.
  * Ceuta i Melilla: 2 senadors, fins a 2 vots.
  * Eivissa, Formentera, Menorca, Fuerteventura, La Gomera, El Hierro, Lanzarote
    i La Palma: 1 senador, 1 vot. (La LO 2/2026 va separar Eivissa i Formentera.)
  * Surten els candidats amb mes vots.
  En total, 209 senadors electes. Els altres 57 els designen els parlaments
  autonomics i no depenen del 29N.

Model: vot de partit. Cada candidat d'una llista rep el % que l'estimacio del
Congres dona a la seva llista (la suma dels partits que la formen: «Senado de
Progreso» = PSOE + Frente Amplio). Amb vot de partit, a una provincia la primera
llista treu 3 escons i la segona 1. El candidat concret de cada llista que
entraria no es pot saber (hi ha vot personal); es pren l'ordre del BOE.

Excepcio: a La Gomera i El Hierro el 2023 van guanyar partits insulars (ASG i
AHI) que cap enquesta no mesura. Si tornen a presentar-s'hi, es mante el del 2023.

Fonts: candidatures, BOE-A-2026-23103 (03/11/2026); composicio actual del Senat,
«Anexo:Senadores de la XV legislatura de España» (Viquipedia, CC BY-SA 4.0),
desada a data/senat/xv-legislatura.csv.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV_2026 = ROOT / "data" / "llistes" / "senado-2026.csv"
CSV_XV = ROOT / "data" / "senat" / "xv-legislatura.csv"
WIKI_XV = "Anexo:Senadores_de_la_XV_legislatura_de_España"

ISLAND_NAMES = {"07-MA": "Mallorca", "07-ME": "Menorca", "07-EI": "Eivissa",
                "07-FO": "Formentera", "35-GC": "Gran Canaria", "35-LZ": "Lanzarote",
                "35-FV": "Fuerteventura", "38-TF": "Tenerife", "38-LP": "La Palma",
                "38-LG": "La Gomera", "38-EH": "El Hierro"}
ISLAND_NAMES_ES = {**ISLAND_NAMES, "07-EI": "Ibiza"}

# Municipis de cada illa petita (codi INE). La resta de la provincia va a l'illa gran.
ISLAND_MUNIS = {
    "07-ME": {"07002", "07015", "07023", "07032", "07037", "07052", "07064", "07902"},
    "07-EI": {"07026", "07046", "07048", "07050", "07054"},
    "07-FO": {"07024"},
    "35-LZ": {"35004", "35010", "35018", "35024", "35028", "35029", "35034"},
    "35-FV": {"35003", "35007", "35014", "35015", "35017", "35030"},
    "38-LP": {"38007", "38008", "38009", "38014", "38016", "38024", "38027", "38029",
              "38030", "38033", "38037", "38045", "38047", "38053"},
    "38-LG": {"38002", "38003", "38021", "38036", "38049", "38050"},
    "38-EH": {"38013", "38048", "38901"},
}
BIG_ISLAND = {"07": "07-MA", "35": "35-GC", "38": "38-TF"}

# Partits insulars sense enquestes que van guanyar el 2023 (vegeu el docstring).
HOLD_2023 = {"38-LG", "38-EH"}


def seats_votes(code: str) -> tuple[int, int]:
    """(escons, vots per elector) de la circumscripcio."""
    if code in ("07-MA", "35-GC", "38-TF"):
        return 3, 2
    if code in ("51", "52"):
        return 2, 2
    if "-" in code:
        return 1, 1
    return 4, 3


def island_of(muni: str) -> str | None:
    prov = muni[:2]
    if prov not in BIG_ISLAND:
        return None
    for isl, munis in ISLAND_MUNIS.items():
        if muni in munis:
            return isl
    return BIG_ISLAND[prov]


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
    return " ".join(re.sub(r"[^A-Z0-9]", " ", s).split())


# Partits de l'estimacio del Congres que formen cada candidatura del Senat.
# S'aplica sobre el nom i la sigla del BOE junts (en majuscules i sense accents).
_RULES = [
    (r"\bSDP\b|SENADO DE PROGRESO", {"PSOE", "SUMAR"}),
    (r"\bPSOE\b|\bPSC\b|\bPSIB\b|SOCIALISTA", {"PSOE"}),
    (r"\bIU\b|\bIUN\b|\bMS\b|\bSUMAR\b|COMPROMIS|\bEUPV\b|\bCHA\b|\bEUIB\b|\bMES PER\b|"
     r"COMUNS|\bC DEM\b|FRONT AMPLI|FRENTE AMPLIO|\bNC BC\b|\bEZAN\b|BATZARRE|\bMM\b|"
     r"ARA EIVISSA|\bEM\b|\bEU\b|\bGXF\b", {"SUMAR"}),
    (r"\bPODEMOS\b|\bPODEM\b", {"PODEMOS"}),
    (r"PARTIDO POPULAR|PARTIT POPULAR|\bPP\b|\bUPN\b", {"PP"}),
    (r"\bVOX\b", {"VOX"}),
    (r"\bERC\b|ESQUERRA REPUBLICANA", {"ERC"}),
    (r"BILDU", {"EHB"}),
    (r"\bJXCAT\b|JUNTS PER", {"JUNTS"}),
    (r"\bPNV\b|\bEAJ\b", {"PNV"}),
    (r"\bBNG\b|B N G|BLOQUE NACIONALISTA", {"BNG"}),
    (r"COALICION CANARIA|\bCCA\b", {"CC"}),
    (r"ADELANTE ANDALUCIA", {"AA"}),
    (r"TERUEL EXISTE", {"EXISTE"}),
    (r"SORIA YA|\bSY\b", {"SY"}),
    (r"GEROA BAI|\bGBAI\b", {"GBAI"}),
    (r"\bPACMA\b", {"PACMA"}),
]

# Etiqueta curta per al recompte, amb el color del partit que hi mana.
_FAMILY_RULES = [
    (r"\bSDP\b|SENADO DE PROGRESO|ACORD DE PROGRES|AL SENAT|\bPSOE\b|\bPSC\b|SOCIALISTA", "PSOE"),
    (r"^ERC|ESQUERRA REPUBLICANA DE CATALUNYA EUSKAL", "ERC"),
    (r"BILDU", "EHB"),
    (r"PARTIDO POPULAR|PARTIT POPULAR|\bPP\b|\bUPN\b|SA UNIO", "PP"),
]


# Candidatures que les regles no poden llegir be: partits insulars que cap enquesta
# mesura (l'ASG no es el PSOE encara que porti «Socialista» al nom) i Sa Unio, on
# «Compromís» es Compromís amb Formentera, no el valencià.
LOCAL = {
    "ASG": ("ASG", set(), "Agrupación Socialista Gomera"),
    "A.H.I.": ("AHI", set(), "Agrupación Herreña Independiente"),
    "ASAMBLEA HERREÑA": ("AH", set(), "Asamblea Herreña"),
    "IxLG": ("IxLG", set(), "Iniciativa por La Gomera"),
    "FV": ("FV", set(), "Formentera Viva"),
    "SA UNIÓ": ("PP", {"PP"}, None),
    "NC-BC, PODEMOS, IU, SUMAR": ("NC", {"SUMAR", "PODEMOS"}, None),
}
LOCAL_NAMES = {fam: name for fam, _, name in LOCAL.values() if name}


def components(sigla: str, list_name: str) -> set:
    if sigla in LOCAL:
        return set(LOCAL[sigla][1])
    text = _fold(f"{list_name} {sigla}")
    out = set()
    for rx, codes in _RULES:
        if re.search(rx, text):
            out |= codes
    if not out:
        from . import parties
        for label in (sigla, list_name):
            code, known = parties.resolve(label, "ES")
            if known and code:
                return {code}
    return out


def family(sigla: str, list_name: str) -> str:
    """El partit amb que es compta l'escó al total (PSOE per a Senado de Progreso)."""
    if sigla in LOCAL:
        return LOCAL[sigla][0]
    sig = _fold(sigla)
    for rx, fam in _FAMILY_RULES:
        if re.search(rx, sig) or re.search(rx, _fold(list_name)):
            return fam
    comps = components(sigla, list_name)
    if len(comps) == 1:
        return next(iter(comps))
    return "?" + sigla


def write_csv(path: Path = CSV_2026):
    from .ingest import candidatures
    rows = candidatures.parse(chamber="senado")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["constituency", "order", "sigla", "list_name", "components", "family",
                    "position", "name"])
        for r in rows:
            w.writerow([r["province"], r["order"], r["sigla"], r["list_name"],
                        "+".join(sorted(components(r["sigla"], r["list_name"]))),
                        family(r["sigla"], r["list_name"]), r["position"], r["name"]])
    return len(rows)


def lists_2026(path: Path = CSV_2026) -> dict:
    """{circumscripcio: [{order, sigla, list_name, components, family, names}]}."""
    out: dict = {}
    if not path.exists():
        return out
    by_key: dict = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r["constituency"], int(r["order"]))
            if key not in by_key:
                by_key[key] = {"order": int(r["order"]), "sigla": r["sigla"],
                               "list_name": r["list_name"],
                               "components": [c for c in r["components"].split("+") if c],
                               "family": r["family"], "names": []}
                out.setdefault(r["constituency"], []).append(by_key[key])
            by_key[key]["names"].append(r["name"])
    return out


# ------------------------------------------------------------ composicio actual

_CIRC_ALIAS = {"vizcaya": "48", "guipuzcoa": "20", "alava": "01", "la coruna": "15",
               "orense": "32", "gerona": "17", "lerida": "25", "lerida lerida": "25",
               "alicante": "03", "castellon": "12", "valencia": "46",
               "ibiza formentera": "07-IF", "ibiza": "07-EI", "eivissa": "07-EI"}


def _circ_code(name: str) -> str | None:
    from .ingest.candidatures import province_codes
    key = _fold(name).lower()
    for code, isl in ISLAND_NAMES.items():
        if key == _fold(isl).lower():
            return code
    return _CIRC_ALIAS.get(key) or province_codes().get(key)


def fetch_composition(path: Path = CSV_XV):
    """Desa la composicio actual del Senat (una vegada; la pagina canvia poc)."""
    import requests
    from bs4 import BeautifulSoup
    resp = requests.get("https://es.wikipedia.org/w/api.php",
                        params={"action": "parse", "format": "json", "formatversion": 2,
                                "prop": "text", "page": WIKI_XV},
                        headers={"User-Agent": "politbureau (politbureau.es)"}, timeout=60)
    resp.raise_for_status()
    html = resp.json()["parse"]["text"]
    table = BeautifulSoup(html, "html.parser").find_all("table", class_="wikitable")[1]
    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = [re.sub(r"\[\s*\d+\s*\]", "", c.get_text(" ", strip=True)).replace("​", "").strip()
                 for c in tr.find_all(["td", "th"])]
        if len(cells) < 8:
            continue
        name, group, party, where, since = cells[0], cells[2], cells[4], cells[5], cells[6]
        if where.lower().startswith("designad"):
            kind, code, body = "designat", "", where.split(":", 1)[1].strip()
        else:
            kind, code, body = "electe", _circ_code(where), ""
            if not code:
                raise ValueError(f"Circumscripcio desconeguda: {where!r}")
        rows.append([kind, code, body, party, group, name, since])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["kind", "constituency", "designated_by", "party", "group", "name", "since"])
        w.writerows(rows)
    return len(rows)


_PARTY_2023 = {"PSC": "PSOE", "PSE-EE": "PSOE", "PSdeG-PSOE": "PSOE", "EAJ-PNV": "PNV",
               "EH Bildu": "EHB", "JxCat": "JUNTS", "Vox": "VOX", "Geroa Bai": "GBAI",
               "UPN": "PP", "CCa": "CC", "Más Madrid": "SUMAR", "Compromís": "SUMAR"}


def composition(path: Path = CSV_XV) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["family"] = _PARTY_2023.get(r["party"], r["party"])
    return rows


# ------------------------------------------------------------------- projeccio

def shares(conn, election="es-general", baseline="congreso-2023") -> dict:
    """{circumscripcio: {partit: %}}: la provincia tal qual; les illes, sumant els
    municipis amb el pes dels vots valids del 2023."""
    out: dict = {}
    for code, party, share in conn.execute(
            "SELECT code, party, share FROM projection WHERE election_id = ? AND level = 'province'",
            (election,)):
        if code not in BIG_ISLAND:
            out.setdefault(code, {})[party] = share or 0
    weight = {}
    for code, valid in conn.execute(
            """SELECT code, MAX(valid_votes) FROM election_result
               WHERE election = ? AND level = 'municipality'
                 AND substr(code, 1, 2) IN ('07', '35', '38') GROUP BY code""", (baseline,)):
        weight[code] = valid or 0
    acc: dict = {}
    tot: dict = {}
    for code, party, share in conn.execute(
            """SELECT code, party, share FROM projection WHERE election_id = ? AND level = 'municipality'
               AND substr(code, 1, 2) IN ('07', '35', '38')""", (election,)):
        isl = island_of(code)
        w = weight.get(code, 0)
        if not isl or not w:
            continue
        acc.setdefault(isl, {}).setdefault(party, 0.0)
        acc[isl][party] += (share or 0) * w
    for code, w in weight.items():
        isl = island_of(code)
        if isl:
            tot[isl] = tot.get(isl, 0) + w
    for isl, ps in acc.items():
        out[isl] = {p: v / tot[isl] for p, v in ps.items()}
    return out


def project(conn) -> list[dict]:
    """Una entrada per circumscripcio: llistes amb el seu %, electes i marge."""
    lists = lists_2026()
    sh = shares(conn)
    held = {}
    for r in composition():
        if r["kind"] == "electe":
            held.setdefault(r["constituency"], []).append(r)
    out = []
    for code, cands in sorted(lists.items()):
        seats, votes = seats_votes(code)
        s = sh.get(code, {})
        rows = []
        for lst in cands:
            measured = [c for c in lst["components"] if c in s]
            share = sum(s[c] for c in measured) if measured else None
            rows.append({**lst, "share": share})
        rows.sort(key=lambda r: (-(r["share"] if r["share"] is not None else -1), r["order"]))
        hold = None
        if code in HOLD_2023 and held.get(code):
            winner = held[code][0]["party"]
            hold = next((r for r in rows if _fold(winner) in (_fold(r["sigla"]), _fold(r["list_name"]))
                         or _fold(r["sigla"]).replace(" ", "") == _fold(winner).replace(" ", "")), None)
        elected = []
        if hold:
            elected.append({"name": hold["names"][0], "family": hold["family"],
                            "list": hold, "held": True})
        else:
            for r in rows:
                if r["share"] is None:
                    continue
                for name in r["names"][:votes]:
                    if len(elected) < seats:
                        elected.append({"name": name, "family": r["family"], "list": r})
                if len(elected) >= seats:
                    break
        # Marge: el darrer escó contra la primera llista que es queda fora.
        margin = None
        if not hold and elected:
            last = elected[-1]["list"]
            out_lists = [r for r in rows if r["share"] is not None and r is not last
                         and not any(e["list"] is r for e in elected)]
            if out_lists:
                margin = last["share"] - out_lists[0]["share"]
        unmeasured = [r for r in rows if r["share"] is None and r["family"].startswith("?") is False]
        out.append({"code": code, "seats": seats, "votes": votes, "lists": rows,
                    "elected": elected, "margin": margin, "held": bool(hold),
                    "unmeasured": [r for r in rows if r["share"] is None],
                    "before": held.get(code, []) if code != "07-EI" and code != "07-FO"
                    else held.get("07-IF", [])})
    return out


def totals(projection: list[dict]) -> dict:
    n: dict = {}
    for c in projection:
        for e in c["elected"]:
            n[e["family"]] = n.get(e["family"], 0) + 1
    return n


# ------------------------------------------------------------------ per a la web

def _meta(fam: str) -> dict:
    from . import parties
    if fam in LOCAL_NAMES:
        return {"code": fam, "name": LOCAL_NAMES[fam], "color": "#9E9E9E"}
    m = parties.meta(fam, "ES", "es-general")
    if fam == "PSOE":
        m = {**m, "name": "PSOE · Senado de Progreso"}
    return m


def view(conn) -> dict | None:
    """Tot el que pinten la pagina del Senat i les fitxes de provincia."""
    from .geo import fetch
    proj = project(conn)
    if not proj:
        return None
    provs = fetch.names("ES", "province")
    comp = composition()
    before_fam: dict = {}
    for r in comp:
        if r["kind"] == "electe":
            before_fam[r["family"]] = before_fam.get(r["family"], 0) + 1
    designated: dict = {}
    for r in comp:
        if r["kind"] == "designat":
            designated[r["family"]] = designated.get(r["family"], 0) + 1
    now = totals(proj)
    fams = sorted(set(now) | set(before_fam) | set(designated),
                  key=lambda f: -(now.get(f, 0) + designated.get(f, 0)))
    rows = []
    for f in fams:
        m = _meta(f)
        if f == "Independiente":
            m = {"code": f, "name": "Independent", "color": "#9E9E9E"}
        rows.append({**m, "now": now.get(f, 0), "before": before_fam.get(f, 0),
                     "designated": designated.get(f, 0),
                     "total": now.get(f, 0) + designated.get(f, 0)})
    elected = sum(c["seats"] for c in proj)
    n_designated = sum(designated.values())
    house = elected + n_designated
    consts = []
    for c in proj:
        code = c["code"]
        name = {"ca": ISLAND_NAMES.get(code) or provs.get(code, code),
                "es": ISLAND_NAMES_ES.get(code) or provs.get(code, code)}
        won: dict = {}
        for e in c["elected"]:
            won[e["family"]] = won.get(e["family"], 0) + 1
        prev: dict = {}
        for r in c["before"]:
            prev[r["family"]] = prev.get(r["family"], 0) + 1
        consts.append({
            "code": code, "province": code[:2], "name": name, "seats": c["seats"],
            "votes": c["votes"], "held": c["held"], "margin": c["margin"],
            "elected": [{**_meta(e["family"]), "person": e["name"],
                         "list": e["list"]["list_name"].title() if e["list"]["list_name"].isupper()
                         else e["list"]["list_name"]} for e in c["elected"]],
            "lists": [{**_meta(r["family"]) , "sigla": r["sigla"], "share": r["share"]}
                      for r in c["lists"] if r["share"] is not None][:5],
            "unmeasured": [r["sigla"] for r in c["unmeasured"] if not r["family"].startswith("?")
                           or r["family"][1:] in LOCAL_NAMES],
            "won": [{**_meta(f), "n": n} for f, n in sorted(won.items(), key=lambda x: -x[1])],
            "before": [{**_meta(f), "n": n} for f, n in sorted(prev.items(), key=lambda x: -x[1])],
            "merged_2023": code in ("07-EI", "07-FO"),
            "changed": won != prev and code not in ("07-EI", "07-FO"),
        })
    consts.sort(key=lambda c: _fold(c["name"]["es"]))
    return {"rows": rows, "elected": elected, "designated": n_designated, "house": house,
            "majority": house // 2 + 1, "constituencies": consts,
            "changed": sum(1 for c in consts if c["changed"]),
            "close": sorted((c for c in consts if c["margin"] is not None and c["margin"] < 3),
                            key=lambda c: c["margin"])}
