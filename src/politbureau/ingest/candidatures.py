"""Candidatures proclamades al Congres per a les generals del 29/11/2026.

Font: BOE num. 273, de 3 de novembre de 2026, BOE-A-2026-23103 («Candidaturas
proclamadas para las elecciones al Congreso de los Diputados y al Senado»),
publicat per cada Junta Electoral Provincial (LOREG art. 47.5 i 169.4).
El text del BOE es pot reutilitzar citant-ne la font (Llei 37/2007 i avis legal
del BOE).

Les llistes son tancades i bloquejades: el k-esim escó que guanya un partit en
una provincia es per a la persona numero k de la seva llista. Amb aixo, sobre
l'estimacio d'avui, cada escó del repartiment porta nom i cognoms (09/11/2026).

El resultat es desa a `data/llistes/congreso-2026.csv` (va al repositori: el CI
no depen del BOE) i a la taula `deputy` amb election = 'congreso-2026'.
Nomes titulars; els suplents no entren mai per l'ordre del repartiment.
"""
from __future__ import annotations

import csv
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BOE_ID = "BOE-A-2026-23103"
BOE_XML = ROOT / "data" / "raw" / "es" / "boe" / f"{BOE_ID}.xml"
BOE_URL = f"https://www.boe.es/diario_boe/xml.php?id={BOE_ID}"
BOE_HTML = f"https://www.boe.es/diario_boe/txt.php?id={BOE_ID}"
CSV = ROOT / "data" / "llistes" / "congreso-2026.csv"
ELECTION = "congreso-2026"

# Noms de la Junta -> codi INE de provincia quan no coincideixen amb fetch.names.
JUNTA_ALIAS = {"alicante": "03", "alacant": "03", "valencia": "46", "castellon": "12",
               "castello": "12", "alava": "01", "araba": "01", "baleares": "07",
               "illes balears": "07", "la coruna": "15", "a coruna": "15",
               "vizcaya": "48", "guipuzcoa": "20", "gerona": "17", "lerida": "25",
               "orense": "32"}

_HEADER = re.compile(r"^\s*(\d+)\.\s*(.+?)\s*$")
_SIGLA = re.compile(r"\(([^()]*)\)\s*\.?\s*$")
_CAND = re.compile(r"^\s*(\d+)\s*\.\s*(.+?)\s*\.?\s*$")


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z ]", " ", s).split())


_AFFIL_WORDS = re.compile(r"independ|frente|front|partido|partit|izquierda|movimiento|"
                          r"recortes|sumar|bildu|geroa|podem|compromis|verds?", re.I)


def _split_affiliation(text: str):
    """"Nom Cognom (Izquierda Unida)" -> ("Nom Cognom", "Izquierda Unida").
    A les llistes de coalicio el BOE diu de quin partit es cada candidat; un
    sobrenom al final ("(Chiqui)") no es cap partit i es queda al nom."""
    m = re.search(r"\s*\(([^()]+)\)\s*$", text)
    if m:
        inner = m.group(1).strip()
        if inner.upper() == inner or _AFFIL_WORDS.search(inner):
            aff = "" if re.match(r"independ", inner, re.I) else inner
            return text[:m.start()].strip(), aff
    return text, ""


def province_codes():
    from ..geo import fetch
    out = {}
    for code, name in fetch.names("ES", "province").items():
        for part in name.split("/"):
            out[_fold(part)] = code
    out.update(JUNTA_ALIAS)
    return out


def download(force: bool = False) -> Path:
    if BOE_XML.exists() and not force:
        return BOE_XML
    import urllib.request
    BOE_XML.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(BOE_URL, headers={"User-Agent": "politbureau"})
    with urllib.request.urlopen(req, timeout=60) as r:
        BOE_XML.write_bytes(r.read())
    return BOE_XML


def parse(path: Path | None = None):
    """Llistes del Congres: dicts amb province, order (ordre al BOE), list_name,
    sigla, position, name. Una mateixa Junta pot sortir mes d'un cop (correccions
    o capçaleres repetides): mana l'ultima aparicio de cada llista."""
    root = ET.parse(path or download()).getroot()
    codes = province_codes()
    province = section = None
    lst = None
    suplents = False
    lists: dict = {}
    for p in root.iter("p"):
        cls = p.get("class", "")
        text = " ".join("".join(p.itertext()).split())
        if not text:
            continue
        if cls == "centro_negrita" and text.upper().startswith("JUNTA ELECTORAL"):
            name = re.sub(r"^JUNTA ELECTORAL( PROVINCIAL)? DE\s+", "", text, flags=re.I)
            province = codes.get(_fold(name))
            if province is None:
                raise ValueError(f"Junta sense codi de provincia: {text!r}")
            section, lst = None, None
            continue
        if cls == "centro_cursiva":
            up = _fold(text)
            section = "congreso" if up.startswith("congreso") else (
                "senado" if up.startswith("senado") else section)
            lst = None
            continue
        if section != "congreso" or province is None:
            continue
        if cls == "centro_redonda":
            m = _HEADER.match(text)
            if not m:
                continue
            full = m.group(2).rstrip(".")
            sm = _SIGLA.search(full)
            sigla = sm.group(1).strip() if sm else full
            name = full[:sm.start()].strip() if sm else full
            lst = {"province": province, "order": int(m.group(1)), "list_name": name,
                   "sigla": sigla, "members": []}
            lists[(province, int(m.group(1)))] = lst
            suplents = False
            continue
        if lst is None:
            continue
        if _fold(text).startswith("suplente"):
            # "Suplentes:" obre el bloc; "Suplente 1: ..." (format del Senat) es salta.
            if text.rstrip().endswith(":"):
                suplents = True
            continue
        if suplents:
            continue
        m = _CAND.match(text)
        if m and int(m.group(1)) == len(lst["members"]) + 1:
            lst["members"].append(_split_affiliation(m.group(2).strip().rstrip(".")))
    out = []
    for lst in lists.values():
        for i, (name, aff) in enumerate(lst["members"], 1):
            out.append({"province": lst["province"], "order": lst["order"],
                        "list_name": lst["list_name"], "sigla": lst["sigla"],
                        "position": i, "name": name, "affiliation": aff})
    out.sort(key=lambda d: (d["province"], d["order"], d["position"]))
    return out


# Sigla del BOE -> codi de l'estimacio, quan el nom de la llista no es el del
# partit estatal: coalicions territorials del Frente Amplio, UPN-PP a Navarra
# (regional_merge a sources.yaml), CC amb Primero Canarias...
SIGLA = {
    "FA": "SUMAR",
    "COMUNS-FRONT AMPLI": "SUMAR",
    "ARAMÉS-EU-MS": "SUMAR",
    "NC-BC, PODEMOS, IU, SUMAR": "SUMAR",
    "CHA-IU-MS-FRENTE AMPLIO": "SUMAR",
    "COMPROMIS-EUPV-PODEM-ERPV": "SUMAR",
    "FRENTE AMPLIO-FRONTE AMPLA": "SUMAR",
    "FRENTE AMPLIO - FRONTE AMPLA": "SUMAR",
    "FRENTE AMPLIO-FRONTE ZABALA": "SUMAR",
    "UPN-PP": "PP",
    "1.ºCAN-CCa": "CC",
    "CCa-1.ºCAN": "CC",
    "EH BILDU-ERC": "EHB",
}


def resolve(sigla: str, list_name: str):
    """Codi de partit d'una llista. Les petites que no surten a l'estimacio es
    queden amb un codi provisional: no treuen mai cap escó."""
    from .. import parties
    if sigla in SIGLA:
        return SIGLA[sigla]
    for label in (sigla, list_name):
        code, known = parties.resolve(label, "ES")
        if known and code:
            return code
    return "?" + sigla


def write_csv(path: Path = CSV):
    rows = parse()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["province", "order", "sigla", "list_name", "party", "position", "name",
                    "affiliation"])
        for r in rows:
            w.writerow([r["province"], r["order"], r["sigla"], r["list_name"],
                        resolve(r["sigla"], r["list_name"]), r["position"], r["name"],
                        r["affiliation"]])
    return len(rows)


def store(conn, path: Path = CSV):
    """Omple `deputy` (election = congreso-2026) des del CSV del repositori.
    Si una provincia te dues llistes amb el mateix codi (no hauria de passar),
    mana la primera del BOE."""
    if not path.exists():
        return 0
    rows, seen = [], {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r["province"], r["party"])
            seen.setdefault(key, r["order"])
            if seen[key] != r["order"]:
                continue
            rows.append((ELECTION, r["province"], r["party"], int(r["position"]),
                         r["name"], None, 0))
    conn.execute("DELETE FROM deputy WHERE election = ?", (ELECTION,))
    conn.executemany(
        """INSERT OR REPLACE INTO deputy
           (election, province, party, position, name, sex, elected)
           VALUES (?,?,?,?,?,?,?)""", rows)
    conn.commit()
    return len(rows)


if __name__ == "__main__":
    print(write_csv(), "candidats ->", CSV)


def lists(path: Path = CSV):
    """{provincia: {partit: [{"name", "affiliation", "position"}...]}} des del CSV,
    en l'ordre de la llista. Buit si encara no hi ha llistes."""
    out: dict = {}
    if not path.exists():
        return out
    first: dict = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r["province"], r["party"])
            first.setdefault(key, r["order"])
            if first[key] != r["order"]:
                continue
            aff = r.get("affiliation") or ""
            if _fold(aff) == _fold(r["sigla"]):
                aff = ""                  # "(FA)" dins de la llista del FA no diu res
            out.setdefault(r["province"], {}).setdefault(r["party"], []).append(
                {"name": r["name"], "affiliation": aff, "position": int(r["position"])})
    return out
