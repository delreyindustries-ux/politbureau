"""Normalització de noms de partit a codis canònics."""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "parties.yaml"

# Etiquetes de columna que no són partits i s'han d'ignorar.
# Es comparen ja passades per slug(), per això no hi ha accents ni barres.
_NON_PARTY_RAW = [
    "lead", "turnout", "sample size", "polling firm/commissioner", "polling firm",
    "commissioner", "fieldwork date", "date", "pollster", "sample", "margin",
    "undecided", "abstention", "n", "moe", "margin of error", "question",
    "x mark", "check mark", "candidate", "party", "scenario", "source",
    "poll source", "seats", "total", "others",
]


def slug(text: str) -> str:
    """'Coalición Canaria' -> 'coalicion canaria'. Sense accents ni signes."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\[[^\]]*\]", "", text)          # referències [12]
    text = re.sub(r"\([^)]*\)", "", text)           # desambiguacions "(Spain)"
    text = re.sub(r"[^\w\s+.'-]", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


# Si una etiqueta CONTÉ un d'aquests fragments no és cap partit. Cal comprovar-ho
# després del diccionari d'àlies, o "others" deixaria de resoldre's a OTHER.
_NON_PARTY_SUBSTRINGS = (
    "date", "sample", "polling firm", "poll source", "pollster", "administered",
    "margin of error", "turnout", "lead", "size", "moe", "link", "ref",
    "commissioner", "updated", "question", "scenario", "mark",
    # CDX/CSX son coalicions italianes: sumen partits que ja comptem per separat.
    "cdx", "csx", "coalition", "centre-right", "centre-left",
)

# Als EUA la capçalera és el nom del candidat amb el partit entre parèntesis.
# Això ens estalvia un diccionari de centenars de noms.
_US_TAG = re.compile(r"\(\s*(D|R|I|L|G|DFL|IND)\s*\)\s*$", re.IGNORECASE)
_US_MAP = {"D": "DEM", "DFL": "DEM", "R": "REP", "I": "IND", "IND": "IND",
           "L": "IND", "G": "IND"}


@lru_cache(maxsize=1)
def _non_party() -> set[str]:
    return {slug(x) for x in _NON_PARTY_RAW}


@lru_cache(maxsize=1)
def _candidates() -> dict:
    """Mapa nom_de_candidat -> codi de partit, per a França (i qualsevol altre
    país on les enquestes es facin per persona i no per sigla)."""
    with CONFIG.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    out = {}
    for country, mapping in (raw.get("_candidates") or {}).items():
        out[country] = {slug(name): code for name, code in mapping.items()}
    return out


@lru_cache(maxsize=1)
def _contains() -> dict:
    with CONFIG.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return {country: {slug(k): v for k, v in rules.items()}
            for country, rules in (raw.get("_contains") or {}).items()}


@lru_cache(maxsize=1)
def _catalog() -> dict:
    with CONFIG.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    catalog = {}
    for country, parties in raw.items():
        if country.startswith("_"):     # blocs auxiliars com _candidates
            continue
        index = {}
        for code, meta in parties.items():
            keys = {slug(code), slug(meta["name"])}
            keys.update(slug(a) for a in meta.get("aliases", []))
            for key in keys:
                if key:
                    index[key] = code
        catalog[country] = {"index": index, "meta": parties}
    return catalog


def resolve(label: str, country: str) -> tuple[str | None, bool]:
    """Retorna (codi, conegut). Si no el reconeix, inventa un codi provisional
    perquè la dada no es perdi, i marca conegut=False perquè l'ingest ho registri."""
    raw = str(label).strip()
    # El sufix (D)/(R) s'ha de llegir abans que slug() esborri els parèntesis.
    tag = _US_TAG.search(raw)
    if country == "US" and tag:
        return _US_MAP[tag.group(1).upper()], True

    key = slug(raw)
    if not key:
        return None, True
    # Les enquestes franceses fan servir "Generic LR", "Generic NFP"... per a un
    # candidat encara sense nom. El prefix no aporta res: el que compta és la sigla.
    key = re.sub(r"^generic\s+", "", key)

    # El diccionari mana per damunt de qualsevol heurística: si no, sigles d'una
    # sola lletra com la "A" d'Azione les descartaria el filtre de sota.
    index = _catalog().get(country, {}).get("index", {})
    if key in index:
        return index[key], True
    # Les sigles arriben amb i sense punts segons la font: infoelectoral escriu
    # "B.N.G." i "U.P.N." on Wikipedia posa "BNG" i "UPN".
    undotted = key.replace(".", "")
    if undotted != key and undotted in index:
        return index[undotted], True
    if key in _candidates().get(country, {}):
        return _candidates()[country][key], True
    if key in _non_party():
        return None, True
    if any(frag in key for frag in _NON_PARTY_SUBSTRINGS):
        return None, True
    # Xarxa de seguretat: xifres, percentatges i mides de mostra no són partits.
    if not re.search(r"[a-z]{2}", key) or re.fullmatch(r"[\d\s.,%-]+", raw.strip()):
        return None, True
    # Coincidència per prefix: "psoe-psc" resol a "psoe"; "pp" no ha de menjar-se "ppcv".
    for alias, code in index.items():
        if key.startswith(alias + " ") or key.startswith(alias + "-"):
            return code, True
    # slug() esborra els parentesis, i aixo amagaria el "PSOE" de "PSE-EE (PSOE)".
    # Per a la regla per contingut mirem tambe l'etiqueta amb els parentesis intactes.
    loose = re.sub(r"[^\w\s+.'-]", " ", raw).lower()
    for fragment, code in _contains().get(country, {}).items():
        if fragment in key or fragment in loose:
            return code, True
    provisional = re.sub(r"[^A-Z0-9]", "", key.upper())[:12] or "UNK"
    return f"?{provisional}", False


def meta(code: str, country: str) -> dict:
    entry = _catalog().get(country, {}).get("meta", {}) .get(code) or {}
    # Amb .get() i no amb []: una errada de picatge a parties.yaml ha de deixar
    # el partit en gris, no tombar el servidor sencer amb un KeyError.
    return {
        "code": code,
        "name": entry.get("name") or code.lstrip("?"),
        "color": entry.get("color") or "#9E9E9E",
    }


@lru_cache(maxsize=1)
def _order() -> dict:
    with CONFIG.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return {country: {code: i for i, code in enumerate(codes)}
            for country, codes in (raw.get("_order") or {}).items()}


@lru_cache(maxsize=1)
def _scopes() -> dict:
    with CONFIG.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return {country: {code: set(regions) for code, regions in rules.items()}
            for country, rules in (raw.get("_scope") or {}).items()}


def stands_in(code: str, country: str, region: str | None) -> bool:
    """Si aquest partit es presenta o no en aquesta regió.

    Nomes diu que no per als partits amb àmbit declarat a `_scope`. La resta
    es donen per estatals, que es el comportament correcte per defecte: si un
    partit no consta com a territorial, cal suposar que concorre a tot arreu.
    """
    allowed = _scopes().get(country, {}).get(code)
    if not allowed:
        return True
    return region in allowed


def position(code: str, country: str) -> int:
    """Lloc del partit a l'eix esquerra-dreta, per asseure'l a l'hemicicle.
    Els que no consten a _order van al final, no barrejats enmig."""
    return _order().get(country, {}).get(code, 999)


def palette(country: str) -> dict:
    parties = _catalog().get(country, {}).get("meta", {})
    return {code: {"name": m.get("name", code), "color": m.get("color", "#9E9E9E")}
            for code, m in parties.items()}
