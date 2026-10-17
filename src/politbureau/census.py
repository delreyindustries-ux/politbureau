"""Cens electoral propi d'una eleccio (config/cens/<eleccio>.csv).

El resultat de base (el 2023) porta el cens d'aquella eleccio, i nomes el dels
residents a Espanya. Quan l'INE publica el cens de l'eleccio que ve, es desa a
config/cens i aquest es el que mostren les fitxes i el mapa.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

DIR = Path(__file__).resolve().parents[2] / "config" / "cens"


@lru_cache(maxsize=None)
def load(election_id: str | None) -> dict:
    """{(nivell, codi): {"cer", "cera", "total"}}; buit si l'eleccio no en te."""
    if not election_id:
        return {}
    path = DIR / f"{election_id}.csv"
    if not path.exists():
        return {}
    out = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            out[(row["level"], row["code"])] = {
                "cer": int(row["cer"]), "cera": int(row["cera"]), "total": int(row["total"])}
    return out


def total(election_id: str | None, level: str, code: str) -> int | None:
    return (load(election_id).get((level, code)) or {}).get("total")
