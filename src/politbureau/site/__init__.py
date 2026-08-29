"""Generacio del lloc public estatic."""
from __future__ import annotations

import gzip
import shutil

from .. import db, parties
from . import pages as pagemod
from .build import DIST, ELECTION, gather, load_config, build_urls, thousands
from .render import make_env, territory_pages, write


def export_data(cfg):
    """Bolca les respostes de l'API a fitxers JSON.

    Es fa amb el client de proves del propi Flask en comptes de repetir les
    consultes: aixi el que serveix el lloc estatic es exactament el que servia
    l'API, i no hi ha dues implementacions que puguin acabar dient coses diferents.
    """
    from ..server import create_app
    client = create_app().test_client()

    endpoints = {
        "geoinfo": "/api/geoinfo",
        "elections": "/api/elections",
        "summary": f"/api/summary/{ELECTION}",
        "trend": f"/api/trend/{ELECTION}",
        "polls": f"/api/polls/{ELECTION}",
        "seats": f"/api/seats/{ELECTION}",
    }
    for level in ("municipality", "province", "region"):
        for layer in ("real", "projection"):
            endpoints[f"map-{level}-{layer}"] = \
                f"/api/map/{ELECTION}?level={level}&layer={layer}"

    out = DIST / "data"
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, url in endpoints.items():
        resp = client.get(url, headers={"Accept-Encoding": "identity"})
        if resp.status_code != 200:
            print(f"     AVIS: {url} ha respost {resp.status_code}, es salta")
            continue
        body = resp.get_data()
        (out / f"{name}.json").write_bytes(body)
        (out / f"{name}.json.gz").write_bytes(gzip.compress(body, 6))
        written.append((name, len(body)))
    return written


def summary_highlights(cfg):
    """Les xifres estatals per a la portada: % i escons de cada partit."""
    conn = db.connect()
    seats = {r["party"]: r["seats"] for r in conn.execute(
        """SELECT party, seats FROM seat_projection
           WHERE election_id = ? AND level = 'chamber'""", (ELECTION,))}
    rows = conn.execute(
        """SELECT party, share FROM aggregate
           WHERE election_id = ? AND scope_code = '' ORDER BY share DESC LIMIT 10""",
        (ELECTION,)).fetchall()
    return [{**parties.meta(r["party"], "ES"), "share": r["share"],
             "seats": seats.get(r["party"])} for r in rows if r["share"] >= 0.5]


def site_stats(conn):
    def q(s, *a):
        row = conn.execute(s, a).fetchone()
        if row is None or row[0] is None:
            raise RuntimeError(
                "La base de dades no porta resultats reals, no es pot generar el "
                "lloc.\n  Consulta sense resposta: " + " ".join(s.split())
                + "\n  Executa `politbureau build` abans de `politbureau site`."
            )
        return row[0]
    return {
        "municipalities": thousands(q(
            "SELECT COUNT(DISTINCT code) FROM election_result "
            "WHERE election='congreso-2023' AND level='municipality'")),
        "valid_votes": thousands(q(
            "SELECT valid_votes FROM election_result "
            "WHERE election='congreso-2023' AND level='national' LIMIT 1")),
        "polls": thousands(q("SELECT COUNT(*) FROM poll WHERE election_id=?", ELECTION)),
        "pollsters": q("SELECT COUNT(DISTINCT pollster) FROM poll WHERE election_id=?", ELECTION),
    }


def run(clean=True):
    cfg = load_config()
    site = cfg["site"]
    if str(site.get("owner", "")).startswith("PENDENT"):
        print("  AVIS: config/site.yaml encara no te titular ni contacte.")
        print("        La LSSI-CE els exigeix a qualsevol web amb publicitat.")

    if clean and DIST.exists():
        # A Windows, si algu esta servint dist/ el rmtree falla a mitges i deixa
        # l'arbre trencat sense dir res. Val mes aturar-se i avisar que publicar
        # un lloc incomplet.
        failures = []
        shutil.rmtree(DIST, onerror=lambda f, p, e: failures.append(p))
        if failures:
            raise RuntimeError(
                f"no s'ha pogut esborrar dist/ ({len(failures)} fitxers en us). "
                "Segurament hi ha un servidor obert damunt d'aquesta carpeta: "
                "atura'l i torna-ho a provar.")
    DIST.mkdir(parents=True, exist_ok=True)

    conn = db.connect()
    print("1/6  Llegint la base de dades")
    data = gather(conn)
    urls, slugs, prov_region = build_urls(data)
    print(f"     {len(urls):,} territoris")

    env = make_env()

    print("2/6  Fitxes de territori")
    written = territory_pages(env, cfg, data, urls, prov_region)
    langs = len(cfg["site"]["languages"])
    print(f"     {len(written) * langs:,} pagines ({len(written):,} per idioma)")

    # A partir d'aqui nomes existeixen els territoris que TENEN pagina: el
    # sitemap, la portada i el cercador no poden enllacar el que no s'ha escrit.
    skipped = len(urls) - len(written)
    urls = {key: value for key, value in urls.items() if key in written}
    if skipped:
        print(f"     {skipped} territoris sense dades, exclosos de tot el lloc")

    print("3/6  Portada, mapa, metodologia i legals")
    pagemod.home_page(env, cfg, data, urls, summary_highlights(cfg))
    pagemod.map_page(env, cfg)
    pagemod.method_page(env, cfg, site_stats(conn))
    pagemod.legal_pages(env, cfg)

    print("4/6  Dades del mapa")
    for name, size in export_data(cfg):
        print(f"     {name:<26} {size/1024:>8.0f} kB")

    print("5/6  Recursos i index de cerca")
    indexed = pagemod.assets(data, urls)
    print(f"     {indexed:,} territoris indexats per al cercador")

    print("6/6  Sitemap i robots")
    for name, count in pagemod.sitemaps(cfg, urls):
        print(f"     {name:<18} {count:,} adreces")

    files = sum(1 for _ in DIST.rglob("*") if _.is_file())
    size = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file())
    print(f"\nFet: {files:,} fitxers, {size/1e6:.1f} MB a dist/")
    if files > 20000:
        print("  AVIS: Cloudflare Pages nomes admet 20.000 fitxers per desplegament.")
        print("        Amb aquest nombre cal fer servir GitHub Pages o Netlify.")
    return files
