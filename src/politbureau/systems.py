"""Cada pais amb el seu sistema electoral (14/11/2026).

Els escons orientatius de config/chambers.yaml nomes servien per als sistemes
proporcionals. Aqui hi ha el que cal per als altres:

  * Majoritari uninominal (Regne Unit): el guanyador de cada circumscripcio
    s'emporta l'esco. Es projecta circumscripcio per circumscripcio a partir
    del resultat del 2024 amb el swing proporcional (el mateix metode que els
    municipis d'Espanya): el vot de cada partit es multiplica pel que ha
    crescut o caigut a les enquestes.
    Escocia, Gal.les i Londres fan servir la seva mitjana propia si n'hi ha.
    Irlanda del Nord (18 escons) no te enquestes de Westminster: es queda com
    el 2024. Dades: House of Commons Library, candidatures del 2024 (Open
    Parliament Licence v3.0).
  * Presidencials: la regla de cada constitucio per guanyar a la primera
    volta (majoria absoluta, majoria simple, el 45 % de l'Argentina...).

`politbureau sistemes` regenera config/fptp/gb-2024.json des del CSV de
data/raw/gb (que no es puja al repositori); la web nomes llegeix el JSON.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1].parent
GB_CSV = ROOT / "data" / "raw" / "gb" / "ge2024_candidacies.csv"
GB_JSON = ROOT / "config" / "fptp" / "gb-2024.json"

# Sigla de la House of Commons Library -> codi de les enquestes (eu-gb).
GB_CODES = {"Lab": "?LABOURPARTY", "Con": "?CONSERVATIVEPARTY", "LD": "?LIBERALDEMOCRATS",
            "Green": "?GREENPARTIESINTHEUNITEDKINGDOM", "RUK": "?REFORMUK",
            "SNP": "?SCOTTISHNATIONALPARTY", "PC": "?PLAIDCYMRU"}
# Escons que no surten de cap enquesta britanica: nom i color per a la cambra.
GB_EXTRA = {
    "SF": ("Sinn Féin", "#326760"), "DUP": ("DUP", "#D46A4C"), "SDLP": ("SDLP", "#2AA82C"),
    "APNI": ("Alliance", "#F6CB2F"), "UUP": ("UUP", "#48A5EE"), "TUV": ("TUV", "#0C3A6A"),
    "IND": ("Independents", "#B4B4B4"), "SPK": ("Speaker", "#4a4a4a"),
    "WPB": ("Workers Party", "#8E1B1B"),
}
# Les enquestes d'Escocia i Gal.les porten les federacions dels partits.
GB_ALIAS = {"?SCOTTISHLABOUR": "?LABOURPARTY", "?WELSHLABOUR": "?LABOURPARTY",
            "?SCOTTISHCONSERVATIVES": "?CONSERVATIVEPARTY", "?WELSHCONSERVATIVES": "?CONSERVATIVEPARTY",
            "?SCOTTISHLIBERALDEMOCRATS": "?LIBERALDEMOCRATS", "?WELSHLIBERALDEMOCRATS": "?LIBERALDEMOCRATS",
            "?SCOTTISHGREENS": "?GREENPARTIESINTHEUNITEDKINGDOM",
            "?WALESGREENPARTY": "?GREENPARTIESINTHEUNITEDKINGDOM",
            "?GREENPARTYOFENGLANDANDWALES": "?GREENPARTIESINTHEUNITEDKINGDOM",
            "?REFORMUKSCOTLAND": "?REFORMUK", "?REFORMUKWALES": "?REFORMUK"}
REGIONS = {"Scotland": "SCT", "Wales": "WLS", "Northern Ireland": "NI"}


def build_gb() -> dict:
    """CSV de candidatures del 2024 -> JSON compacte per circumscripcio."""
    seats: dict[str, dict] = {}
    for r in csv.DictReader(GB_CSV.open(encoding="utf-8-sig")):
        name = r["Constituency name"]
        region = REGIONS.get(r["Country name"]) or ("LDN" if r["English region name"] == "London" else "ENG")
        c = seats.setdefault(name, {"n": name, "r": region, "v": {}, "w": None})
        if r["Candidate is standing as Commons Speaker"] == "true":
            party = "SPK"
        elif r["Candidate is standing as independent"] == "true" or not r["Main party abbreviation"]:
            party = "IND"
        else:
            party = r["Main party abbreviation"]
        code = GB_CODES.get(party, party)
        share = round(float(r["Candidate vote share"]) * 100, 2)
        # Dos independents a la mateixa circumscripcio no son el mateix
        # candidat: compta el millor, no la suma.
        c["v"][code] = max(c["v"].get(code, 0), share) if code == "IND" else round(c["v"].get(code, 0) + share, 2)
        # Vots per a la base regional (la suma de vots, no la mitjana de %).
        c.setdefault("votes", {})
        c["votes"][code] = c["votes"].get(code, 0) + int(r["Candidate vote count"] or 0)
        if r["Candidate result position"] == "1":
            c["w"] = code
    out = {"source": "House of Commons Library, general election 2024 candidacies "
                     "(Open Parliament Licence v3.0)",
           "date": "2024-07-04", "seats": sorted(seats.values(), key=lambda c: c["n"])}
    GB_JSON.parent.mkdir(parents=True, exist_ok=True)
    GB_JSON.write_bytes(json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return out


def _load_gb():
    try:
        return json.loads(GB_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def fptp_gb(national: dict, regional: dict | None = None):
    """Escons de la Cambra dels Comuns amb el swing proporcional.

    `national`: {codi: %} de la mitjana estatal; `regional`: {"SCT"|"WLS"|"LDN":
    {codi: %}}. Retorna ({codi: escons}, {codi: (nom, color)} dels que no son a
    les enquestes, {"changed": escons que canvien de mans}) o None sense dades."""
    data = _load_gb()
    if not data:
        return None
    def canon(d):
        out = defaultdict(float)
        for code, v in (d or {}).items():
            out[GB_ALIAS.get(code, code)] += v
        return dict(out)
    national = canon(national)
    regional = {k: canon(v) for k, v in (regional or {}).items() if v}
    # Resultat del 2024 de cada ambit amb mitjana propia (i de GB sencera).
    base: dict[str, dict] = defaultdict(lambda: defaultdict(int))
    total: dict[str, int] = defaultdict(int)
    for c in data["seats"]:
        if c["r"] == "NI":
            continue
        for key in ("GB", c["r"]):
            for code, v in c["votes"].items():
                base[key][code] += v
                total[key] += v
    pct = {k: {code: 100 * v / total[k] for code, v in d.items()} for k, d in base.items()}

    seats: dict[str, int] = defaultdict(int)
    changed = 0
    for c in data["seats"]:
        if c["r"] == "NI" or c["w"] == "SPK":
            # Irlanda del Nord es queda com el 2024; el Speaker no es disputa.
            winner = c["w"]
        else:
            key = c["r"] if c["r"] in regional else "GB"
            avg = regional.get(key) or national
            ref = pct[key]
            now = dict(c["v"])
            # Swing proporcional, el mateix que als municipis d'Espanya: si un
            # partit passa del 14 al 21 % (x1,5), a cada circumscripcio el seu
            # vot es multiplica per 1,5. Amb el swing uniforme (+7 a tot
            # arreu) un partit que creix molt guanya massa poc on era fort i
            # un que cau perd vots fins i tot on no en tenia.
            for code, share in avg.items():
                if code == "OTHER":
                    continue
                r0 = ref.get(code, 0.0)
                if code in now and r0 >= 0.5:
                    now[code] = now[code] * share / r0
                elif r0 < 0.5 and share >= 1:
                    # Partit nou (Restore Britain): el seu % a tot arreu.
                    now[code] = share
            tot = sum(now.values())
            now = {k: 100 * v / tot for k, v in now.items()}
            winner = max(now, key=now.get)
        seats[winner] += 1
        changed += winner != c["w"]
    extra = {code: GB_EXTRA.get(code, (code, "#9E9E9E")) for code in seats
             if not code.startswith("?") and code != "OTHER"}
    return dict(seats), extra, {"changed": changed, "source": data["source"], "date": data["date"]}


# ------------------------------------------------------------ presidencials

# Regla de cada pais per guanyar a la primera volta. Fonts: les constitucions
# (FR art. 7, AR arts. 97-98, GT art. 184, ID art. 6A, PH art. VII.4, VE art.
# 228) i les lleis electorals (KR, UA, GM), resumides a la seccio "Electoral
# system" de l'article de Wikipedia de cada eleccio.
PRESIDENTIAL = {
    "FR": {"rule": "majority"},
    "GT": {"rule": "majority"},
    "UA": {"rule": "majority"},
    "SV": {"rule": "majority"},
    "ID": {"rule": "majority", "extra": "id"},
    "AR": {"rule": "ar"},
    "KR": {"rule": "plurality"},
    "PH": {"rule": "plurality"},
    "VE": {"rule": "plurality"},
    "GM": {"rule": "plurality"},
    "MX": {"rule": "plurality"},
}


def presidential(country: str, avg: list[dict]) -> dict | None:
    """Que passaria amb la mitjana: guanyador a la primera volta o segona volta.

    `avg`: files de la mitjana (code, share, name/person, color). Els % es
    recalculen sobre els candidats (sense indecisos), com el vot valid."""
    rule = PRESIDENTIAL.get(country)
    rows = [a for a in avg if a.get("code") != "OTHER" and a.get("share")]
    if not rule or len(rows) < 2:
        return None
    tot = sum(a["share"] for a in avg if a.get("share"))
    if not tot:
        return None
    rows = sorted(rows, key=lambda a: -a["share"])
    first, second = rows[0], rows[1]
    p1, p2 = 100 * first["share"] / tot, 100 * second["share"] / tot
    kind = rule["rule"]
    if kind == "plurality":
        wins = True
    elif kind == "majority":
        wins = p1 > 50
    else:                                   # Argentina: 45 %, o 40 % amb 10 punts
        wins = p1 >= 45 or (p1 >= 40 and p1 - p2 >= 10)
    pick = lambda a: {"name": a.get("person") or a.get("name"), "color": a.get("color")}
    return {"rule": kind, "extra": rule.get("extra"), "wins": wins,
            "first": {**pick(first), "share": round(p1, 1)},
            "second": {**pick(second), "share": round(p2, 1)},
            "lead": round(p1 - p2, 1)}
