"""Qui seu a cada escó de l'hemicicle (15/11/2026).

Les llistes espanyoles son tancades: el numero k de la llista proclamada
(BOE) ocupa l'escó k que el partit guanya a la provincia. Amb l'estimacio
d'escons per provincia es pot dir, doncs, qui entraria avui. La web ho desa en
un JSON per idioma (dist/dades/diputats-2026-<idioma>.json) que cambra.js
carrega quan l'hemicicle entra a la pantalla: en clicar un diputat surt la
seva fitxa.

El curriculum (naixement, estudis, professio, carrecs) ve de Wikidata (CC0)
a traves de config/profiles.json (`politbureau perfils`); qui no hi es surt
nomes amb les dades del BOE.
"""
from __future__ import annotations

import datetime as dt
import json

from .. import parties
from .build import ELECTION, _fold_name, region_code


def congress(data, urls, magnitudes=None) -> dict:
    """{idioma: {"parties": {codi: [persona, ...]}, ...}}."""
    from ..ingest import profiles
    bios = profiles.load()
    elected23 = {_fold_name(m["name"]) for ms in data["deputies"].values() for m in ms if m["elected"]}
    names = data["names"]["province"]
    out = {}
    for lang in ("es", "ca"):
        by_party: dict[str, list] = {}
        for code, seats in sorted(data["seats_proj"].items()):
            lists = data.get("lists", {}).get(code, {})
            region = region_code(data, "province", code)
            mag = sum(seats.values())
            for party, n in seats.items():
                members = lists.get(party) or []
                local = parties.meta(party, "ES", ELECTION, region)["name"]
                for k in range(n):
                    m = members[k] if k < len(members) else None
                    row = {"pv": names.get(code, code), "pos": k + 1, "_mag": mag, "list": local}
                    u = urls.get(("province", code))
                    if u:
                        row["u"] = u[lang]
                    if m:
                        row["n"] = m["name"]
                        if m.get("affiliation"):
                            row["af"] = m["affiliation"]
                        if _fold_name(m["name"]) in elected23:
                            row["r"] = 1
                        bio = bios.get(profiles.fold(m["name"]))
                        if bio:
                            b = dict(bio.get(lang) or {})
                            if bio.get("born"):
                                b["born"] = bio["born"]
                            b["qid"] = bio["qid"]
                            row["bio"] = b
                    by_party.setdefault(party, []).append(row)
        # Els caps de llista de les circumscripcions grans, als primers escons
        # de cada grup (cambra.js els asseu a les files de davant).
        for rows in by_party.values():
            rows.sort(key=lambda r: (r["pos"], -r["_mag"], r["pv"]))
            for r in rows:
                del r["_mag"]
        out[lang] = {"updated": dt.date.today().isoformat(),
                     "sources": ["BOE-A-2026-23103 (candidaturas proclamadas)", "Wikidata (CC0)"],
                     "parties": by_party}
    return out


def write(dist, got) -> dict:
    """Desa els JSON i retorna {idioma: cami dins del lloc} per a data-people."""
    links = {}
    for lang, payload in got.items():
        path = dist / "dades" / f"diputats-2026-{lang}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        links[lang] = f"dades/diputats-2026-{lang}.json"
    return links
