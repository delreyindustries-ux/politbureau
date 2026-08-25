"""Descarrega les geometries dels mapes (TopoJSON) a data/geo/.

Es guarden en disc i no es tornen a baixar: les fronteres municipals canvien
un cop cada molts anys, no cal demanar-les cada dia.
"""
from __future__ import annotations

import gzip
import json
from functools import lru_cache
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[3]
GEO_DIR = ROOT / "data" / "geo"
SOURCES = ROOT / "config" / "sources.yaml"


def config():
    with SOURCES.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)["geo"]


def _fetch_json(url, timeout=1200):
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def level_path(country, level):
    return GEO_DIR / f"{country.lower()}-{level}.json"


def _build_geojson(country, spec):
    """Prepara cada nivell en un fitxer PROPI, quantitzant-lo pel cami.

    Un fitxer per nivell i no un de sol: el mapa de regions franceses fa mig
    mega i el de comunes trenta-cinc. Amb tot junt, obrir Franca per mirar les
    regions obligaria a baixar-ho tot. Aixi cada nivell es baixa quan es demana.

    Cada element es queda amb dues propietats, `id` i `name`; la resta no les
    fa servir ningu i ocupen.
    """
    from . import simplify

    digits = spec.get("digits", 4)
    levels = {}
    for level, src in spec["sources"].items():
        print(f"   {country}/{level}: baixant ...", flush=True)
        raw = _fetch_json(src["url"])
        for feature in raw.get("features", []):
            props = feature.get("properties") or {}
            key = props.get(src["key"])
            if key is not None and src.get("key_slice"):
                key = str(key)[src["key_slice"]:]
            feature["properties"] = {"id": str(key) if key is not None else None,
                                     "name": props.get(src.get("name"))}
        raw["features"] = [f for f in raw["features"] if f["properties"]["id"]]
        coll = simplify.quantize(raw, digits, keep=("id", "name"))
        out = level_path(country, level)
        body = simplify.dumps(coll).encode("utf-8")
        out.write_bytes(body)
        # Precomprimir aqui i no a cada peticio: son fitxers estatics de desenes
        # de megues i comprimir-los cada cop que algu canvia de nivell seria
        # llencar mig segon de CPU per res.
        out.with_suffix(".json.gz").write_bytes(gzip.compress(body, 6))
        levels[level] = len(coll["features"])
        print(f"      {levels[level]} formes -> {out.name} ({out.stat().st_size/1e6:.1f} MB)")
    return {"levels": levels}


def run(only=None, force=False):
    GEO_DIR.mkdir(parents=True, exist_ok=True)
    for country, spec in config().items():
        if only and country not in only:
            continue
        target = GEO_DIR / spec["file"]
        if target.exists() and not force:
            print(f"{country}: ja hi es ({target.name}, {target.stat().st_size/1e6:.2f} MB)")
            continue

        if spec.get("format") == "geojson":
            if all(level_path(country, lv).exists() for lv in spec["sources"]) and not force:
                print(f"{country}: ja hi es")
                continue
            payload = _build_geojson(country, spec)
            print(f"   -> {payload['levels']}")
            continue
        else:
            print(f"{country}: baixant {spec['url']} ...")
            payload = _fetch_json(spec["url"], timeout=600)
            counts = {k: len(v.get("geometries", [])) for k, v in payload.get("objects", {}).items()}

        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        target.write_bytes(body)
        target.with_suffix(".json.gz").write_bytes(gzip.compress(body, 6))
        print(f"   -> {target.name}  {target.stat().st_size/1e6:.2f} MB  {counts}")


def load(country):
    spec = config()[country]
    path = GEO_DIR / spec["file"]
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=16)
def names(country, level):
    """{codi: nom} per a un nivell territorial, sigui TopoJSON o GeoJSON.

    Els paisos servits com a GeoJSON tenen un fitxer per nivell; el de comunes
    franceses fa 35 MB, i per aixo el resultat es guarda a la memoria cau: es
    consulta a cada clic sobre el mapa.
    """
    path = level_path(country, level)
    if path.exists():
        coll = json.loads(path.read_text(encoding="utf-8"))
        return {f["properties"]["id"]: f["properties"].get("name")
                for f in coll.get("features", [])}
    data = load(country)
    if not data:
        return {}
    obj = (config()[country].get("levels") or {}).get(level)
    if not obj or obj not in data.get("objects", {}):
        return {}
    return {g.get("id"): (g.get("properties") or {}).get("name")
            for g in data["objects"][obj].get("geometries", []) if g.get("id")}
