"""Revisio del lloc generat abans de publicar-lo.

Publicar setze mil pagines sense comprovar-les es una manera molt cara
d'assabentar-se que una plantilla tenia un enllac malament: quan Google les hagi
rastrejat totes i trobat quatre mil 404, la penalitzacio ja esta feta i costa
mesos de desfer.

Es comprova el que de veritat pot trencar-se sense que es noti:
  * cada enllac intern apunta a un fitxer que existeix;
  * cada pagina te titol, descripcio, canonic i un unic h1;
  * cap titol ni cap descripcio es repeteix (per a un cercador, dues pagines
    amb el mateix titol son duplicats);
  * el sitemap nomes llista adreces que existeixen;
  * les dades estructurades son JSON valid.
"""
from __future__ import annotations

import json
import posixpath
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urldefrag

from .build import DIST, load_config

HREF = re.compile(r'(?:href|src)="([^"]+)"')
TITLE = re.compile(r"<title>(.*?)</title>", re.S)
DESC = re.compile(r'name="description" content="(.*?)"', re.S)
CANON = re.compile(r'rel="canonical" href="(.*?)"')
H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
LDJSON = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


SKIP = ("http://", "https://", "mailto:", "tel:", "#", "data:", "javascript:")


def _target(page_dir: str, href: str) -> str | None:
    """Adreca del fitxer que hauria de servir aquest enllac, com a text.

    Es treballa amb cadenes i no amb Path.resolve(): son mig milio d'enllacos i
    resoldre'ls un per un contra el disc feia que la revisio trigues mes de deu
    minuts. Normalitzar la ruta en memoria i mirar-la en un conjunt es instantani.
    """
    href = unquote(urldefrag(href)[0]).split("?", 1)[0]
    if not href or href.startswith(SKIP):
        return None
    if href.startswith("/"):
        path = href.lstrip("/")
    else:
        path = posixpath.normpath(posixpath.join(page_dir, href)) if page_dir else \
            posixpath.normpath(href)
    if path in (".", ""):
        path = ""
    # Una adreca acabada en barra la serveix l'index.html de dins.
    if href.endswith("/") or not posixpath.splitext(path)[1]:
        path = posixpath.join(path, "index.html") if path else "index.html"
    return path.lstrip("/")


def run() -> int:
    if not DIST.exists():
        print("No hi ha dist/. Executa primer `politbureau site`.")
        return 1

    cfg = load_config()
    base_url = cfg["site"]["base_url"].rstrip("/")
    # L'inventari sencer del que existeix, llegit una sola vegada.
    existing = {f.relative_to(DIST).as_posix() for f in DIST.rglob("*") if f.is_file()}
    pages = sorted(DIST.rglob("*.html"))
    print(f"Revisant {len(pages):,} pagines i {len(existing):,} fitxers\n")

    broken = defaultdict(list)
    titles, descs = Counter(), Counter()
    missing_meta, bad_ld, multi_h1 = [], [], []
    checked = 0

    for page in pages:
        html = page.read_text(encoding="utf-8", errors="replace")
        rel = page.relative_to(DIST).as_posix()
        page_dir = posixpath.dirname(rel)

        for href in set(HREF.findall(html)):
            target = _target(page_dir, href)
            if target is None:
                continue
            checked += 1
            if target not in existing:
                broken[href].append(rel)

        title = TITLE.search(html)
        desc = DESC.search(html)
        canon = CANON.search(html)
        heads = H1.findall(html)

        # L'index de l'arrel es una redireccio amb noindex: no li cal descripcio.
        if rel == "index.html":
            continue
        if not title or not desc or not canon:
            missing_meta.append(rel)
        else:
            titles[title.group(1).strip()] += 1
            descs[desc.group(1).strip()] += 1
            if not canon.group(1).startswith(base_url):
                broken[f"canonic fora de {base_url}"].append(rel)
        if len(heads) != 1 and "index.html" != rel:
            multi_h1.append((rel, len(heads)))

        for block in LDJSON.findall(html):
            try:
                json.loads(block)
            except json.JSONDecodeError as exc:
                bad_ld.append((rel, str(exc)[:60]))

    # --- sitemap
    sitemap_missing = []
    for sm in DIST.glob("sitemap-*.xml"):
        for loc in re.findall(r"<loc>(.*?)</loc>", sm.read_text(encoding="utf-8")):
            rel = loc.replace(base_url, "").strip("/")
            if f"{rel}/index.html".lstrip("/") not in existing and rel not in existing:
                sitemap_missing.append(loc)

    # ------------------------------------------------------------- informe
    problems = 0
    print(f"  enllacos interns comprovats   {checked:,}")

    if broken:
        problems += sum(len(v) for v in broken.values())
        print(f"\n  ENLLACOS TRENCATS: {len(broken)} destins diferents")
        for href, where in sorted(broken.items(), key=lambda kv: -len(kv[1]))[:12]:
            print(f"    {href}")
            print(f"      a {len(where):,} pagines, p. ex. {where[0]}")
    else:
        print("  enllacos trencats             cap")

    if missing_meta:
        problems += len(missing_meta)
        print(f"\n  SENSE TITOL/DESCRIPCIO/CANONIC: {len(missing_meta)}")
        for r in missing_meta[:5]:
            print(f"    {r}")
    else:
        print("  metadades                     completes a totes")

    dup_t = [(t, n) for t, n in titles.items() if n > 1]
    dup_d = [(d, n) for d, n in descs.items() if n > 1]
    if dup_t or dup_d:
        problems += len(dup_t) + len(dup_d)
        print(f"\n  DUPLICATS: {len(dup_t)} titols i {len(dup_d)} descripcions repetits")
        for text, n in sorted(dup_t, key=lambda kv: -kv[1])[:5]:
            print(f"    {n}x  {text[:70]}")
        for text, n in sorted(dup_d, key=lambda kv: -kv[1])[:3]:
            print(f"    {n}x  (descripcio) {text[:60]}")
    else:
        print("  titols i descripcions         tots unics")

    if multi_h1:
        problems += len(multi_h1)
        print(f"\n  H1 REPETIT O ABSENT: {len(multi_h1)}")
        for r, n in multi_h1[:5]:
            print(f"    {r} -> {n} h1")
    else:
        print("  un sol h1 per pagina          si")

    if bad_ld:
        problems += len(bad_ld)
        print(f"\n  JSON-LD INVALID: {len(bad_ld)}")
        for r, err in bad_ld[:5]:
            print(f"    {r}: {err}")
    else:
        print("  dades estructurades           valides")

    if sitemap_missing:
        problems += len(sitemap_missing)
        print(f"\n  AL SITEMAP PERO SENSE FITXER: {len(sitemap_missing)}")
        for loc in sitemap_missing[:5]:
            print(f"    {loc}")
    else:
        print("  sitemap                       totes les adreces existeixen")

    print(f"\n{'Tot correcte.' if not problems else f'{problems:,} problemes.'}")
    return 0 if not problems else 2
