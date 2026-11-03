"""Properes eleccions de tots els paisos (demanat el 03/11/2026).

Font: Wikipedia, "List of next general elections" (CC BY-SA 4.0): una taula per
continent amb, per a cada estat, les ultimes i les properes legislatives i
presidencials. La web en fa servir la data de les properes per als paisos que
no tenen enquestes: aixi al globus hi son tots els que fan eleccions, i no
nomes els que tenen enquestes a Wikipedia.

Escriu data/next_elections.json: {codi_del_globus: {"en": nom, "leg": "Jul 2031",
"pres": "Sep 2029"}}, amb el mateix codi que web/world.json (ISO numeric, o la
sigla de dues lletres als paisos europeus).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from . import wikipedia as wk
from ..geo.world import ISO

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "next_elections.json"
PAGE = "List of next general elections"

# Nom de la taula de Wikipedia -> nom de Natural Earth (web/world.json).
ALIASES = {
    "Cape Verde": "Cabo Verde", "Central African Republic": "Central African Rep.",
    "Democratic Republic of the Congo": "Dem. Rep. Congo", "Republic of the Congo": "Congo",
    "Equatorial Guinea": "Eq. Guinea", "Eswatini": "eSwatini", "Ivory Coast": "Côte d'Ivoire",
    "Sahrawi Arab Democratic Republic": "W. Sahara", "Sao Tome and Principe": "São Tomé and Principe",
    "South Sudan": "S. Sudan", "Antigua and Barbuda": "Antigua and Barb.",
    "Dominican Republic": "Dominican Rep.", "Saint Kitts and Nevis": "St. Kitts and Nevis",
    "Saint Vincent and the Grenadines": "St. Vin. and Gren.",
    "United States": "United States of America", "Bosnia and Herzegovina": "Bosnia and Herz.",
    "Czech Republic": "Czechia", "North Macedonia": "Macedonia", "Vatican City": "Vatican",
    "Marshall Islands": "Marshall Is.", "Solomon Islands": "Solomon Is.", "Cook Islands": "Cook Is.",
    "Northern Cyprus": "N. Cyprus",
}
# Fora: Russia (decisio de l'Alfonso des del principi: "tot Europa menys Russia"),
# la Unio Europea (no es un estat) i els territoris sense contorn al globus.
SKIP = {"Russia", "European Union", "Abkhazia", "South Ossetia", "Transnistria", "Tuvalu"}


def _date(text):
    """"24 Aug 2027", "Jul 2031" o res ("— N/a", "TBD", buit)."""
    text = re.sub(r"\[[^\]]*\]", "", text or "").strip()
    m = re.search(r"(?:(\d{1,2})\s+)?([A-Z][a-z]{2})[a-z]*\.?\s+(\d{4})", text)
    if m:
        return " ".join(x for x in m.groups() if x)
    m = re.search(r"\b(20\d{2})\b", text)
    return m.group(1) if m else None


def run(session=None):
    session = session or requests.Session()
    page = wk.fetch(PAGE, session)
    if not page:
        raise RuntimeError(f"no s'ha pogut llegir «{PAGE}»")
    world = json.loads((ROOT / "web" / "world.json").read_text(encoding="utf-8"))
    by_name = {f["n"]: f["c"] for f in world["f"]}
    out, missing = {}, []
    for table in BeautifulSoup(page["html"], "lxml").select("table.wikitable"):
        for row in wk.grid(table)[2:]:
            cells = [wk.cell_text(c) for c in row]
            if len(cells) < 7 or not cells[0] or cells[0] in SKIP:
                continue
            name = cells[0]
            code = by_name.get(ALIASES.get(name, name))
            if code is None and name == "Kosovo":
                code = "XK"
            if code is None:
                missing.append(name)
                continue
            code = ISO.get(code, code)
            leg, pres = _date(cells[3]), _date(cells[6])
            out[code] = {"en": name, "leg": leg, "pres": pres}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    return len(out), missing
