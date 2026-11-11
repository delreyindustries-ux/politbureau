"""Punt d'entrada. `python -m politbureau <ordre>`"""
from __future__ import annotations

import argparse
import sys

from . import db


def cmd_init(args):
    conn = db.connect()
    db.init(conn)
    print(f"Base de dades preparada a {db.DB_PATH}")


def _elections_of(countries):
    """Els id de sources.yaml que pertanyen a aquests paisos."""
    from .ingest.runner import load_config
    wanted = {c.upper() for c in countries}
    # "EUROPA": totes les eleccions marcades `group: europa` (resta d'Europa).
    return [e["id"] for e in load_config()["elections"]
            if e["country"] in wanted or (e.get("group") or "").upper() in wanted]


def cmd_calendari(args):
    from .ingest import calendar
    n, missing = calendar.run()
    print(f"properes eleccions: {n} paisos -> data/next_elections.json")
    if missing:
        print("sense contorn al globus:", ", ".join(missing))


def cmd_ideologia(args):
    from .ingest import ideology
    data = ideology.write(only=set(args.only) if args.only else None)
    n = sum(len(v) for v in data.values())
    print(f"ideologies: {n} partits de {len(data)} paisos -> config/ideologies.json")


def cmd_ingest(args):
    from .ingest import runner
    conn = db.connect()
    db.init(conn)
    only = list(args.only or [])
    if args.country:
        only += _elections_of(args.country)
    summary, unmapped = runner.run(conn, only=only or None)
    total = sum(n for _, _, n in summary)
    print(f"\n{'ELECCIO':<18} {'PAGINA':<58} {'NOVES':>6}")
    print("-" * 84)
    for eid, page, n in summary:
        print(f"{eid:<18} {page[:58]:<58} {n:>6}")
    print("-" * 84)
    print(f"{'TOTAL':<77} {total:>6}")
    if unmapped:
        print("\nEtiquetes sense correspondencia a config/parties.yaml")
        print("(les dades s'han guardat amb un codi provisional '?...'):")
        for label in unmapped[:30]:
            print("   -", label)


def cmd_liders(args):
    from .ingest import leaders
    conn = db.connect()
    db.init(conn)
    for entry, block, n in leaders.run(conn, only=set(args.only) if args.only else None):
        print(f"{entry:<8} {block:<12} {n:>6}")


def cmd_resultats(args):
    from . import results
    out = results.build(results.our_countries())
    print(f"eleccions recents: {len(out['recent'])}")
    for e in out["recent"]:
        print(f"  {e['date']} {e['iso']} {e['title']}")
    print(f"parlaments: {len(out['parliaments'])}, caps de govern: {len(out['heads'])}")


def cmd_build(args):
    from . import build
    conn = db.connect()
    db.init(conn)
    build.run(conn, countries=[c.upper() for c in args.country] if args.country else None)


def cmd_geo(args):
    from .geo import fetch
    fetch.run(only=args.only)


def cmd_site(args):
    from .site import run
    run(clean=not args.keep)


def cmd_instituts(args):
    from . import pollsters
    data = pollsters.run()
    for e in data["elections"]:
        print(f"{e['id']}: {len(e['polls'])} instituts, error mitja {e['mean_mae']} punts, "
              f"mitjana d'enquestes {e['average_mae']}")
    print(f"desat a {pollsters.OUT}")


def cmd_congela(args):
    from . import db, final
    data = final.freeze(db.connect())
    print(f"Congelat a {final.LOCAL} (ultim camp: {data['last_fieldwork']}).")
    print("NO es puja fins despres de les 20 h del 29/11 (veda, LOREG art. 69.7).")


def cmd_check(args):
    from .site.check import run
    return run()


def cmd_serve(args):
    from .server import create_app
    app = create_app()
    print(f"\n  Polit Bureau  ->  http://127.0.0.1:{args.port}\n")
    app.run(host="127.0.0.1", port=args.port, debug=args.debug)


def cmd_status(args):
    conn = db.connect()
    db.init(conn)
    rows = conn.execute(
        """SELECT election_id, country, COUNT(*) n, MAX(fieldwork_end) darrera
           FROM poll GROUP BY election_id, country ORDER BY country, election_id"""
    ).fetchall()
    print(f"\n{'ELECCIO':<18} {'PAIS':<5} {'ENQUESTES':>10}  DARRERA")
    print("-" * 56)
    for r in rows:
        print(f"{r['election_id']:<18} {r['country']:<5} {r['n']:>10}  {r['darrera']}")
    if not rows:
        print("(buit: executa `ingest` primer)")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="politbureau", description="Mapes electorals en temps real")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="crea la base de dades").set_defaults(func=cmd_init)

    sub.add_parser("calendari", help="properes eleccions de tots els paisos (Wikipedia)"
                   ).set_defaults(func=cmd_calendari)

    p = sub.add_parser("ideologia", help="ideologia i posicio dels partits (Wikidata, CC0)")
    p.add_argument("--only", nargs="*", help="codis de pais (ES, DE...)")
    p.set_defaults(func=cmd_ideologia)

    p = sub.add_parser("ingest", help="baixa i guarda les enquestes")
    p.add_argument("--only", nargs="*", help="nomes aquestes eleccions (id de sources.yaml)")
    p.add_argument("--country", nargs="*", help="nomes aquests paisos (ES FR IT US)")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("liders", help="valoracio dels lideres (config/leaders.yaml)")
    p.add_argument("--only", nargs="*", help="nomes aquestes entrades o paisos (ld-es, GB...)")
    p.set_defaults(func=cmd_liders)

    sub.add_parser("resultats", help="resultats recents i composicio dels parlaments (Wikipedia/Wikidata)"
                   ).set_defaults(func=cmd_resultats)

    p = sub.add_parser("geo", help="baixa les geometries dels mapes")
    p.add_argument("--only", nargs="*", help="nomes aquests paisos (ES FR IT US)")
    p.set_defaults(func=cmd_geo)

    p = sub.add_parser("build", help="calcula mitjanes i projeccions")
    p.add_argument("--country", nargs="*",
                   help="nomes aquests paisos (ES FR IT US); la publicacio fa servir ES")
    p.set_defaults(func=cmd_build)
    sub.add_parser("status", help="que hi ha a la base de dades").set_defaults(func=cmd_status)

    p = sub.add_parser("site", help="genera el lloc public estatic a dist/")
    p.add_argument("--keep", action="store_true", help="no esborrar dist/ abans")
    p.set_defaults(func=cmd_site)

    sub.add_parser("instituts", help="valoracio dels instituts d'enquestes (Wikipedia + Ministeri)"
                   ).set_defaults(func=cmd_instituts)
    sub.add_parser("congela", help="desa la mitjana, els escons i la previsio d'abans de la veda (local)"
                   ).set_defaults(func=cmd_congela)
    sub.add_parser("check", help="revisa el lloc generat abans de publicar").set_defaults(func=cmd_check)

    p = sub.add_parser("serve", help="arrenca el mapa a l'ordinador")
    p.add_argument("--port", type=int, default=8730)
    p.add_argument("--debug", action="store_true")
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
