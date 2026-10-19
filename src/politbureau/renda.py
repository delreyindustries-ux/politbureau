"""Renda neta mitjana per persona per seccio censal, districte i municipi.

Decisio de l'Alfonso (19/10/2026): ell demanava el PIB per capita dels barris,
pero el PIB nomes es calcula per provincies (INE, Comptabilitat Regional). El
que hi ha per seccio censal es la renda neta mitjana per persona de l'Atles de
Distribucio de Renda de les Llars (INE, ADRH), any 2023: els ingressos nets de
cada llar dividits pels seus membres.

Les dades venen de l'API de l'INE (una taula per provincia, nomes 2023 i nomes
aquest indicador) i es desen a data/renda/adrh-2023.csv, que si va al
repositori: el que baixa l'API no cal tornar-ho a baixar a cada publicacio.

    PYTHONPATH=src py -c "from politbureau import renda; print(renda.build('<carpeta amb els json>'))"
"""
from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "renda" / "adrh-2023.csv"
YEAR = 2023
LEVELS = {10: "section", 7: "district", 5: "municipality"}


def build(folder: str | Path) -> dict:
    """Llegeix els JSON de l'API (DATOS_TABLA?nult=1&tv=482:284048&tip=M) i
    escriu el CSV. Retorna quants valors hi ha de cada nivell."""
    rows = {}
    for path in sorted(Path(folder).glob("*.json")):
        for serie in json.loads(path.read_text(encoding="utf-8")):
            code = serie["MetaData"][0]["Codigo"]
            level = LEVELS.get(len(code))
            if not level:
                continue
            for value in serie["Data"]:
                if value.get("Anyo") == YEAR and value.get("Valor") is not None \
                        and not value.get("Secreto"):
                    rows[(level, code)] = round(value["Valor"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["level", "code", "renda_persona"])
        for (level, code), value in sorted(rows.items()):
            w.writerow([level, code, value])
    count: dict[str, int] = {}
    for level, _ in rows:
        count[level] = count.get(level, 0) + 1
    return count


@lru_cache(maxsize=1)
def load() -> dict:
    """{(nivell, codi): euros}. Seccio = codi de 10 xifres (municipi,
    districte i seccio), districte = 7, municipi = 5."""
    if not OUT.exists():
        return {}
    with OUT.open(encoding="utf-8", newline="") as fh:
        return {(r["level"], r["code"]): int(r["renda_persona"]) for r in csv.DictReader(fh)}


def section(muni: str, district: str, sec: str) -> int | None:
    return load().get(("section", f"{muni}{district}{sec[:3]}"))


def district(muni: str, district_code: str) -> int | None:
    return load().get(("district", f"{muni}{district_code}"))
