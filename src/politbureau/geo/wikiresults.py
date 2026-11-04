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
# La fila del total de vegades porta el nom del pais.
_COUNTRY_TOTALS = {"austria", "norway", "czech republic", "poland", "portugal", "sweden",
                   "denmark", "romania", "croatia", "slovenia", "bulgaria", "lithuania",
                   "new zealand", "ireland", "estonia", "hungary", "greece", "mexico"}
# Columnes que no son partits pero que el lector de capcaleres deixa passar.
_NOT_PARTY = re.compile(r"TOTAL|VALID|TURNOUT|ELECTORATE|SEATS|INVALID|BLANK|QUOTA|SPOILED|"
                        r"NROFVOTES|NUMBEROFVOTES|"
                        # Viquipedia castellana (Guatemala): vots valids, nuls, en blanc...
                        r"^\?VOTOS|PARTICIPACI|ABSTENCI|^\?NULOS|NOREGISTRADOS")


def _pct(text):
    m = _NUM.match(text or "")
    return float(m.group(1).replace(",", ".")) if m else None


def _transposed(table, country):
    """Taula girada (Canada): territoris en columnes i, per a cada partit, una
    fila "Seats:" i una "Vote:". Retorna ({territori: {codi: %}}, total)."""
    cells = wk.grid(table)
    head = [wk.cell_text(c) if c is not None else "" for c in cells[0]]
    rows, total = {}, {}
    for row in cells[1:]:
        texts = [wk.cell_text(c) if c is not None else "" for c in row]
        if "Vote:" not in texts:
            continue
        at = texts.index("Vote:")
        found, _unk = wk._parties_in_row([c for c in row[:at] if c is not None][-1:], country)
        if not found:
            continue
        code = next(iter(found.values()))
        if _NOT_PARTY.search(code):
            continue
        for col in range(at + 1, min(len(texts), len(head))):
            v = _pct(texts[col])
            if v is None:
                continue
            if _TOTAL.match(head[col]):
                total[code] = v
            else:
                rows.setdefault(head[col], {})[code] = v
    return rows, total or None


def _by_columns(table, country):
    """Partits (o candidats) en files i territoris en columnes "vots | %"
    (Guatemala, Viquipedia castellana). Nomes es llegeixen les cel.les amb "%"."""
    cells = wk.grid(table)
    head = [wk.cell_text(c) if c is not None else "" for c in cells[0]]
    # Belgica (Viquipedia francesa): el "%" es a la segona fila de capcalera.
    sub = [wk.cell_text(c) if c is not None else "" for c in cells[1]] if len(cells) > 1 else []
    rows, total = {}, {}
    for row in cells[1:]:
        found, _unk = wk._parties_in_row([c for c in row[:2] if c is not None][-1:], country)
        if not found:
            continue
        code = next(iter(found.values()))
        if _NOT_PARTY.search(code):
            continue
        for col in range(2, min(len(row), len(head))):
            if row[col] is None:
                continue
            text = wk.cell_text(row[col])
            if "%" not in text and not (col < len(sub) and sub[col] == "%"):
                continue
            v = _pct(text)
            if v is None or not head[col]:
                continue
            if _TOTAL.match(head[col]):
                total.setdefault(code, v)
            else:
                rows.setdefault(head[col], {})[code] = v
    return rows, total


def region_table(page, match, country, session=None, pick="first", transposed=False,
                 lang="en", name_col=0, columns=False, nth=0):
    got = wk.fetch(page, session, lang=lang)
    if not got:
        raise RuntimeError(f"no existeix: {page}")
    soup = BeautifulSoup(got["html"], "lxml")
    if columns:
        # Els territoris venen repartits en diverses taules de la mateixa seccio.
        merged, total = {}, {}
        for table in soup.select("table.wikitable"):
            if match in wk._section_of(table):
                got_rows, got_total = _by_columns(table, country)
                for name, shares in got_rows.items():
                    merged.setdefault(name, {}).update(shares)
                total.update(got_total)
        if merged:
            return merged, total or None, got["title"]
        raise RuntimeError(f"cap taula «{match}» a {page}")
    seen = 0
    for table in soup.select("table.wikitable"):
        if match not in wk._section_of(table):
            continue
        # Filipines: grups d'illes i regions comparteixen seccio; `nth` tria la taula.
        seen += 1
        if seen <= nth:
            continue
        if transposed:
            rows, total = _transposed(table, country)
            if rows:
                return rows, total, got["title"]
            continue
        party_cols, _unknown, header_row = wk.header_parties(table, country)
        if len(set(party_cols.values())) < 2:
            continue
        first = {}
        for col, code in sorted(party_cols.items()):
            if _NOT_PARTY.search(code):
                continue
            if pick == "last":
                first[code] = col                     # "vots | %" (Luxemburg): l'ultima
            else:
                first.setdefault(code, col)           # la primera columna de cada sigla: el %
        rows, total = {}, None
        for cells in wk.grid(table)[header_row + 1:]:
            if not cells or len(cells) <= name_col or cells[name_col] is None:
                continue
            # Indonesia: "Regio | Provincia | ...": el nom es a la segona columna.
            name = re.sub(r"\[[^\]]*\]", "", wk.cell_text(cells[name_col])).strip()
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
            if _TOTAL.match(name) or name.lower() in _COUNTRY_TOTALS:
                total = shares
            else:
                rows[name] = shares
        if rows:
            return rows, total, got["title"]
    raise RuntimeError(f"cap taula «{match}» a {page}")
