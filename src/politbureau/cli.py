"""Punt d'entrada. `python -m politbureau <ordre>`"""
from __future__ import annotations

import argparse
import sys

from . import db


def cmd_init(args):
    conn = db.connect()
    db.init(conn)
    print(f"Base de dades preparada a {db.DB_PATH}")


def cmd_ingest(args):
    from .ingest import runner
    conn = db.connect()
    db.init(conn)
    summary, unmapped = runner.run(conn, only=args.only)
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


def cmd_build(args):
    from . import build
    conn = db.connect()
    db.init(conn)
    build.run(conn)


def cmd_geo(args):
    from .geo import fetch
    fetch.run(only=args.only)


def cmd_site(args):
    from .site import run
    run(clean=not args.keep)


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

    p = sub.add_parser("ingest", help="baixa i guarda les enquestes")
    p.add_argument("--only", nargs="*", help="nomes aquestes eleccions (id de sources.yaml)")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("geo", help="baixa les geometries dels mapes")
    p.add_argument("--only", nargs="*", help="nomes aquests paisos (ES FR IT US)")
    p.set_defaults(func=cmd_geo)

    sub.add_parser("build", help="calcula mitjanes i projeccions").set_defaults(func=cmd_build)
    sub.add_parser("status", help="que hi ha a la base de dades").set_defaults(func=cmd_status)

    p = sub.add_parser("site", help="genera el lloc public estatic a dist/")
    p.add_argument("--keep", action="store_true", help="no esborrar dist/ abans")
    p.set_defaults(func=cmd_site)

    sub.add_parser("check", help="revisa el lloc generat abans de publicar").set_defaults(func=cmd_check)

    p = sub.add_parser("serve", help="arrenca el mapa a l'ordinador")
    p.add_argument("--port", type=int, default=8730)
    p.add_argument("--debug", action="store_true")
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
