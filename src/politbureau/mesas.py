"""Meses electorals de les generals del 29/11/2026: cens, participacio i vot.

Decisio de l'Alfonso (18/10/2026): una taula amb les meses de cada municipi
dins de la seva fitxa, no una pagina per mesa (en serien unes 60.000, i aixo es
el que Google castiga com a contingut generat en massa). L'estimacio de vot la
fa el MATEIX model que la dels municipis: el canvi estatal de la mitjana
d'enquestes aplicat al resultat del 23J de cada mesa (build.project_shares).

El que no hi ha, i per que:
- El cens del 29N per mesa no el publica ningu: l'INE el dona per municipi. El
  de cada mesa s'estima amb el seu cens del 23J multiplicat pel creixement dels
  residents (CER) del municipi. Nomes residents: el vot de l'exterior (CERA)
  no es compta a cap mesa, sino a la junta provincial.
- La participacio del 29N per mesa: Interior la publica a Infoelectoral
  setmanes despres de l'eleccio. La nit electoral nomes la dona per municipi
  (i aixo ja ho segueix participation.py).
- El nom i l'adreca del col.legi electoral no surten als fitxers d'Interior:
  les meses s'identifiquen per districte, seccio i lletra.
"""
from __future__ import annotations

from functools import lru_cache

from . import census as censuslib
from . import parties

ELECTION = "es-general"
BASELINE = "congreso-2023"


@lru_cache(maxsize=1)
def results() -> dict:
    """{id_mesa: {census, avance1, avance2, blank, invalid, cand, voters,
    votes: {partit: vots}}} del 23J, amb les candidatures ja convertides en
    partits com fa la ingesta municipal (PSC compta com a PSOE, etc.)."""
    from .ingest import infoelectoral as ie
    tipo, year, month = ie.PROCESSES[BASELINE]
    zf = ie.download_mesas(BASELINE)
    info = ie.mesas(zf, tipo, year, month)
    votes = ie.mesa_votes(zf, tipo, year, month)
    siglas = ie.candidacies(zf, tipo, year, month)
    party_of: dict[str, str | None] = {}
    out = {}
    for mid, row in info.items():
        per: dict[str, int] = {}
        for cand, n in votes.get(mid, {}).items():
            if cand not in party_of:
                party_of[cand] = parties.resolve(siglas.get(cand, cand), "ES")[0]
            party = party_of[cand]
            if party:
                per[party] = per.get(party, 0) + n
        out[mid] = {**row, "votes": per}
    return out


def _shares(row) -> dict:
    """% sobre els vots a candidatures, el mateix denominador que el model."""
    if not row["cand"]:
        return {}
    return {p: n * 100.0 / row["cand"] for p, n in row["votes"].items()}


def project(conn) -> dict:
    """{id_mesa: {partit: %}} estimat per al 29N."""
    from . import build as model
    now = model.current_national(conn, ELECTION)
    base = {mid: _shares(r) for mid, r in results().items() if r["cand"]}
    return model.project_shares(conn, BASELINE, now, "municipality", "ES",
                                election_id=ELECTION, baseline=base)


def by_municipality(conn) -> dict:
    """{codi_municipi: [una fila per mesa]}, per districte, seccio i mesa."""
    res = results()
    proj = project(conn)
    cens = censuslib.load(ELECTION)
    census_23: dict[str, int] = {}
    for mid, r in res.items():
        census_23[mid[:5]] = census_23.get(mid[:5], 0) + r["census"]

    out: dict[str, list] = {}
    for mid, r in res.items():
        muni = mid[:5]
        cer_29 = (cens.get(("municipality", muni)) or {}).get("cer")
        growth = cer_29 / census_23[muni] if cer_29 and census_23[muni] else None
        c = r["census"]
        _, district, section, mesa = mid.split("-")
        out.setdefault(muni, []).append({
            "id": mid, "district": district, "section": section, "mesa": mesa,
            "census_23": c,
            "census_29": round(c * growth) if growth else None,
            "t14": r["avance1"] * 100.0 / c if c else None,
            "t18": r["avance2"] * 100.0 / c if c else None,
            "final": r["voters"] * 100.0 / c if c else None,
            "real": _shares(r),
            "now": proj.get(mid, {}),
        })
    for rows in out.values():
        rows.sort(key=lambda x: x["id"])
    return out
