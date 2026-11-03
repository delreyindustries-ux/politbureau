"""Globus terraqui de la pagina d'enquestes (pla el 03/11/2026, en 3D el mateix dia).

Font: world-atlas 2.0.2, `countries-50m.json` (Natural Earth, domini public),
baixat de cdn.jsdelivr.net amb el permis de l'Alfonso. Es processa UNA vegada
en local i el resultat, `web/world.json`, va al repositori: aixi la publicacio
de cada hora no baixa res i el navegador dels visitants tampoc no demana res a
tercers.

Es guarden longituds i latituds (no coordenades projectades): el globus les
projecta al navegador amb la projeccio ortografica, que es la vista d'una
esfera des de l'espai, i canvia a cada gir.

Format: {"q": 20, "f": [{"c": codi, "n": nom, "r": [[lon0, lat0, dlon, dlat, ...], ...]}]}
amb els graus multiplicats per `q` i arrodonits (0,05 graus, uns 5 km), i
cada punt com a diferencia de l'anterior per estalviar bytes.

Regions (03/11/2026): les de `regions:` a sources.yaml (Escocia, Flandes, Ontario...)
surten de Natural Earth admin-1 a escala 10m (`ne_10m_admin_1_states_provinces`,
domini public, baixat de naciscdn.org amb el permis de l'Alfonso). Cada regio
ajunta les seves provincies; el codi es "<pais>-<clau>" (GB-SCT, 124-ON) i van al
final de la llista per dibuixar-se per sobre del pais.

Us: python -m politbureau.geo.world data/geo/world/countries-50m.json web/world.json
        [data/geo/world/admin1/ne_10m_admin_1_states_provinces]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# ISO 3166-1 numeric (world-atlas) -> codi de pais de sources.yaml. Fora d'Europa
# es fa servir el numeric directament (`pub.map` a sources.yaml).
ISO = {
    "008": "AL", "040": "AT", "056": "BE", "070": "BA", "100": "BG", "191": "HR",
    "196": "CY", "203": "CZ", "208": "DK", "233": "EE", "246": "FI", "250": "FR",
    "276": "DE", "300": "GR", "348": "HU", "352": "IS", "372": "IE", "380": "IT",
    "428": "LV", "440": "LT", "442": "LU", "470": "MT", "498": "MD", "499": "ME",
    "528": "NL", "578": "NO", "616": "PL", "620": "PT", "642": "RO", "688": "RS",
    "703": "SK", "705": "SI", "724": "ES", "752": "SE", "756": "CH", "807": "MK",
    "826": "GB",
}
Q = 20                  # 1/20 de grau


def _arcs(topo):
    """Arcs absoluts (lon, lat) a partir dels deltes quantitzats."""
    (sx, sy), (tx, ty) = topo["transform"]["scale"], topo["transform"]["translate"]
    out = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        out.append(pts)
    return out


def _ring(arcs, idxs):
    pts = []
    for i in idxs:
        seg = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts.extend(seg if not pts else seg[1:])
    return pts


def _encode(ring):
    """Anella -> [lon0, lat0, dlon, dlat, ...] en 1/Q de grau, sense punts repetits."""
    pts = []
    for lon, lat in ring:
        p = (round(lon * Q), round(lat * Q))
        if not pts or p != pts[-1]:
            pts.append(p)
    if len(set(pts)) < 3:
        return None
    out = [pts[0][0], pts[0][1]]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        out += [x1 - x0, y1 - y0]
    return out


def _regions(admin1: Path):
    """[{c, n, r}] de les regions de sources.yaml, llegides de Natural Earth admin-1."""
    import yaml
    from .seccions import _dbf, _shp
    root = Path(__file__).resolve().parents[3]
    cfg = yaml.safe_load((root / "config" / "sources.yaml").read_text(encoding="utf-8"))
    elections = {e["id"]: e for e in cfg["elections"]}
    rows = _dbf(Path(str(admin1) + ".dbf").read_bytes())
    shapes = _shp(Path(str(admin1) + ".shp").read_bytes())

    def clean(v):
        # El lector de seccions.py llegeix el dbf en latin-1; el de Natural Earth
        # es UTF-8 ("QuÃ©bec"): es torna a decodificar.
        if not isinstance(v, str):
            return v
        v = v.replace("\0", "").strip()
        try:
            return v.encode("latin-1").decode("utf-8")
        except UnicodeError:
            return v

    out = []
    for eid, regs in (cfg.get("regions") or {}).items():
        e = elections[eid]
        code = (e.get("pub") or {}).get("map") or e["country"]
        for reg in regs:
            want = {k: str(v) for k, v in reg["geo"].items()}
            rings = []
            for row, shape in zip(rows, shapes):
                if all(clean(row.get(k)) == v for k, v in want.items()):
                    rings += [r for r in (_encode(ring) for ring in shape) if r]
            if not rings:
                raise SystemExit(f"cap provincia per a {eid} {reg['key']}: {want}")
            out.append({"c": f"{code}-{reg['key']}", "n": reg["name_ca"], "r": rings})
    return out


def build(src: Path, out: Path, admin1: Path | None = None):
    topo = json.loads(Path(src).read_text(encoding="utf-8"))
    arcs = _arcs(topo)
    features = []
    for g in topo["objects"]["countries"]["geometries"]:
        name = g["properties"]["name"]
        if name == "Antarctica":
            continue
        code = ISO.get(g.get("id") or "") or ("XK" if name == "Kosovo" else None)
        polys = (g["arcs"] if g["type"] == "MultiPolygon"
                 else [g["arcs"]] if g["type"] == "Polygon" else [])
        rings = [r for r in (_encode(_ring(arcs, idx)) for poly in polys for idx in poly) if r]
        if rings:
            features.append({"c": code or g.get("id") or name, "n": name, "r": rings})
    if admin1:
        features += _regions(admin1)
    doc = {"q": Q, "f": features,
           "source": "Natural Earth via world-atlas 2.0.2 (domini public)"}
    Path(out).write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False),
                         encoding="utf-8")
    return len(features), Path(out).stat().st_size


if __name__ == "__main__":
    print(build(Path(sys.argv[1]), Path(sys.argv[2]),
                Path(sys.argv[3]) if len(sys.argv) > 3 else None))
