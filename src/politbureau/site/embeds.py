"""Grafics per inserir en altres webs i pagina per a mitjans i docents (21/11/2026).

Idea presa dels simuladors electorals que tenen seccions "per a periodistes" i
"per a docents": un iframe que qualsevol mitja pot enganxar, amb la font i
l'enllac. Tres grafics, en castella i catala:

  * mitjana  - la mitjana d'enquestes de les generals (barres)
  * escons   - l'estimacio d'escons del Congres (hemicicle)
  * previsio - la probabilitat de majoria de cada bloc

Les pagines porten noindex i no van al sitemap. Llicencia: CC BY-SA 4.0,
citant Polit Bureau, com la resta de dades obertes.
"""
from __future__ import annotations

import datetime as dt
import html as _html
import math

from .. import parties
from . import i18n
from .build import DIST, ELECTION
from .render import render_page, write

KINDS = ("mitjana", "escons", "previsio")
SLUG = {"ca": "incrusta", "es": "inserta"}


def _rows(conn):
    rows = conn.execute(
        """SELECT party, share FROM aggregate WHERE election_id = ? AND scope_code = ''
           ORDER BY share DESC""", (ELECTION,)).fetchall()
    out = []
    for r in rows:
        if r["party"] == "OTHER" or r["share"] < 1:
            continue
        m = parties.meta(r["party"], "ES", ELECTION)
        out.append({"code": r["party"], "name": m["name"], "color": m["color"], "share": r["share"]})
    return out[:8]


def _seats(conn):
    rows = conn.execute(
        """SELECT party, seats FROM seat_projection WHERE election_id = ? AND level = 'chamber'
           ORDER BY seats DESC""", (ELECTION,)).fetchall()
    out = []
    for r in rows:
        if not r["seats"]:
            continue
        m = parties.meta(r["party"], "ES", ELECTION)
        out.append({"code": r["party"], "name": m["name"], "color": m["color"], "seats": r["seats"],
                    "pos": parties.position(r["party"], "ES")})
    return out


def _hemicycle(seats) -> str:
    """SVG de l'hemicicle (350 punts en 12 files), d'esquerra a dreta."""
    n = sum(s["seats"] for s in seats)
    rows, r0, r1 = 12, 60, 190
    radii = [r0 + (r1 - r0) * i / (rows - 1) for i in range(rows)]
    counts = [round(n * r / sum(radii)) for r in radii]
    counts[-1] += n - sum(counts)
    pts = []
    for r, c in zip(radii, counts):
        for j in range(c):
            a = math.pi * (1 - j / max(1, c - 1))
            pts.append((a, 200 + r * math.cos(a), 200 - r * math.sin(a)))
    pts.sort(key=lambda p: -p[0])
    seq = [s["color"] for s in sorted(seats, key=lambda s: s["pos"]) for _ in range(s["seats"])]
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.2" fill="{c}"/>' for (a, x, y), c in zip(pts, seq))
    return (f'<svg viewBox="0 0 400 205" role="img" aria-label="Congreso">{dots}'
            '<line x1="200" y1="8" x2="200" y2="200" stroke="currentColor" stroke-dasharray="3 3" opacity=".5"/></svg>')


def embed_pages(env, cfg, conn, fc) -> int:
    rows, seats = _rows(conn), _seats(conn)
    if not rows:
        return 0
    updated = conn.execute("SELECT MAX(computed_at) FROM aggregate WHERE election_id = ?",
                           (ELECTION,)).fetchone()[0] if _has_col(conn) else None
    day = (updated or dt.date.today().isoformat())[:10]
    blocs = ((fc or {}).get("blocs") or {})
    n = 0
    for lang in i18n.LANGS:
        es = lang == "es"
        for kind in KINDS:
            canonical = f"/{SLUG[lang]}/{lang}/{kind}/"
            title = {
                "mitjana": ("Media de encuestas · generales del 29N" if es else "Mitjana d'enquestes · generals del 29N"),
                "escons": ("Escaños estimados del Congreso · 29N" if es else "Escons estimats del Congrés · 29N"),
                "previsio": ("Probabilidad de mayoría · 29N" if es else "Probabilitat de majoria · 29N"),
            }[kind]
            html = env.get_template("embed.html.j2").render(
                lang=lang, kind=kind, title=title, canonical=cfg["site"]["base_url"].rstrip("/") + canonical,
                rows=rows, seats=seats, hemi=_hemicycle(seats) if kind == "escons" and seats else "",
                blocs=blocs, day=day, site=cfg["site"]["base_url"].rstrip("/"),
                desc=title + (" — Polit Bureau, datos abiertos CC BY-SA 4.0" if es
                              else " — Polit Bureau, dades obertes CC BY-SA 4.0"))
            write(DIST / canonical.strip("/") / "index.html", html)
            n += 1
    # Pagina per a mitjans i docents
    for lang in i18n.LANGS:
        es = lang == "es"
        canonical = i18n.page_url("media", lang)
        page = render_page(
            env, cfg, "media.html.j2", lang, canonical,
            {lg: i18n.page_url("media", lg) for lg in i18n.LANGS},
            ("Para medios y docentes: gráficos para insertar y datos abiertos" if es
             else "Per a mitjans i docents: gràfics per inserir i dades obertes"),
            ("Gráficos de Polit Bureau para insertar en tu web, cómo citarlos y cómo usar la web en clase." if es
             else "Gràfics de Polit Bureau per inserir a la teva web, com citar-los i com fer servir la web a classe."),
            embeds=[{"kind": k, "url": f"/{SLUG[lang]}/{lang}/{k}/"} for k in KINDS],
            site_url=cfg["site"]["base_url"].rstrip("/"))
        write(DIST / canonical.strip("/") / "index.html", page)
    return n


def _has_col(conn) -> bool:
    try:
        return any(r[1] == "computed_at" for r in conn.execute("PRAGMA table_info(aggregate)"))
    except Exception:                                      # noqa: BLE001
        return False


_ = _html
