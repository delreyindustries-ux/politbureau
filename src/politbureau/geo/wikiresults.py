"""Resultats per territori llegits de l'article de Wikipedia de l'eleccio (03/11/2026).

Per als paisos on no hi ha un fitxer oficial amb llicencia clara a l'abast,
l'article de Wikipedia de l'ultima eleccio porta una taula "Results by
state/region/county" (CC BY-SA 4.0, la mateixa font i llicencia que les
enquestes). Avantatge: els partits hi estan enllacats als mateixos articles que
a les taules d'enquestes, i per tant surten amb el MATEIX codi provisional.

`region_table(page, match, country)` -> {nom_territori: {codi: %}}, total.
Llegeix la primera columna de cada partit (els articles posen "%" i "escons"
sota la mateixa sigla) i la fila "Total" com a resultat estatal si hi es.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..ingest import wikipedia as wk

_NUM = re.compile(r"^\s*(\d{1,2}(?:[.,]\d+)?)\s*%?\s*$")
_TOTAL = re.compile(r"^(total|overall|national|nationwide|country|all|sum)\b", re.I)


def _pct(text):
    m = _NUM.match(text or "")
    return float(m.group(1).replace(",", ".")) if m else None


def region_table(page, match, country, session=None):
    got = wk.fetch(page, session)
    if not got:
        raise RuntimeError(f"no existeix: {page}")
    soup = BeautifulSoup(got["html"], "lxml")
    for table in soup.select("table.wikitable"):
        if match not in wk._section_of(table):
            continue
        party_cols, _unknown, header_row = wk.header_parties(table, country)
        if len(set(party_cols.values())) < 2:
            continue
        first = {}
        for col, code in sorted(party_cols.items()):
            first.setdefault(code, col)               # la primera columna de cada sigla: el %
        rows, total = {}, None
        for cells in wk.grid(table)[header_row + 1:]:
            if not cells or cells[0] is None:
                continue
            name = re.sub(r"\[[^\]]*\]", "", wk.cell_text(cells[0])).strip()
            if not name or name.lower() in {c.lower() for c in ("%", "s", "seats", "votes")}:
                continue
            shares = {}
            for code, col in first.items():
                if col < len(cells) and cells[col] is not None:
                    v = _pct(wk.cell_text(cells[col]))
                    if v is not None:
                        shares[code] = v
            if len(shares) < 2:
                continue
            if _TOTAL.match(name) or name.lower() in ("austria", "norway", "czech republic"):
                total = shares
            else:
                rows[name] = shares
        if rows:
            return rows, total, got["title"]
    raise RuntimeError(f"cap taula «{match}» a {page}")
