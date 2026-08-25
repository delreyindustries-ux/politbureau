"""Els 350 diputats electes del Congres, amb nom i cognoms.

Surten del fitxer 04 d'infoelectoral (candidatures presentades). Registres de
121 caracters:

    tipus(2) any(4) mes(2) volta(1) provincia(2) municipi(2) districte(2)
    candidatura(6) posicio(3) tipus_candidat(1) nom(25) cognom1(25) cognom2(25)
    sexe(1) data_naixement(8) DNI(10) electe(1)

La posicio 119 val 'S' o 'N' i marca els electes: n'hi ha exactament 350, que es
la mida del Congres. Aixo confirma que les posicions son correctes.

Les llistes espanyoles son tancades i bloquejades, o sigui que l'ordre de la
llista decideix qui entra: si a una provincia un partit treu quatre escons, son
per als quatre primers de la seva llista. Aixo permet dir, sobre l'estimacio
d'avui, qui entraria i qui es quedaria fora.
"""
from __future__ import annotations

from . import infoelectoral as ie

RECORD = 121
ELECTED_FLAG = 119


def _clean(text: str) -> str:
    return " ".join(text.split())


def parse(process: str = "congreso-2023"):
    """Llista de dicts, ordenats per provincia, candidatura i posicio."""
    tipo, year, month = ie.PROCESSES[process]
    zf = ie.download(process)
    blob = ie._member(zf, "04", tipo, year, month)
    out = []
    for rec in ie._records(blob, RECORD):
        if rec[24] != "T":                 # 'T' titular, 'S' suplent
            continue
        given, first, second = _clean(rec[25:50]), _clean(rec[50:75]), _clean(rec[75:100])
        out.append({
            "province": rec[9:11],
            "candidacy": rec[15:21],
            "position": int(rec[21:24]),
            "name": " ".join(x for x in (given, first, second) if x),
            "sex": rec[100],
            "elected": rec[ELECTED_FLAG] == "S",
        })
    out.sort(key=lambda d: (d["province"], d["candidacy"], d["position"]))
    return out


def store(conn, process: str, party_resolver):
    tipo, year, month = ie.PROCESSES[process]
    siglas = ie.candidacies(ie.download(process), tipo, year, month)

    rows = []
    for d in parse(process):
        party = party_resolver(siglas.get(d["candidacy"], d["candidacy"]))
        if not party:
            continue
        rows.append((process, d["province"], party, d["position"], d["name"],
                     d["sex"], 1 if d["elected"] else 0))

    conn.execute("DELETE FROM deputy WHERE election = ?", (process,))
    conn.executemany(
        """INSERT OR REPLACE INTO deputy
           (election, province, party, position, name, sex, elected)
           VALUES (?,?,?,?,?,?,?)""", rows)
    conn.commit()
    elected = sum(r[6] for r in rows)
    return len(rows), elected
