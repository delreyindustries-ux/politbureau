"""Servidor local. Serveix el mapa i les dades que el mapa demana."""
from __future__ import annotations

import gzip
import json
from functools import lru_cache
from pathlib import Path

import yaml
from flask import Flask, jsonify, request, send_from_directory

from . import db, parties
from .geo import fetch as geo
from .ingest.runner import SOURCES
from .model import seats as seatlib

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"


def _config():
    with SOURCES.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


LEVEL_LABEL = {"municipality": "Municipi", "province": "Província",
               "region": "Comunitat", "state": "Estat"}


@lru_cache(maxsize=1)
def _search_index():
    """Tots els territoris que es poden buscar, amb el nom ja normalitzat.

    Es construeix un sol cop: son quinze mil entrades i recorrer-les senceres
    per cada tecla premuda costa menys d'un mil.lisegon, de manera que no cal
    cap estructura mes sofisticada.
    """
    out = []
    for country, spec in geo.config().items():
        levels = list(spec.get("levels") or spec.get("sources") or {})
        for level in levels:
            for code, name in geo.names(country, level).items():
                if not name:
                    continue
                out.append({"country": country, "level": level, "code": code,
                            "name": name, "key": parties.slug(name),
                            "label": LEVEL_LABEL.get(level, level)})
    return out


def create_app():
    app = Flask(__name__, static_folder=None)
    cfg = _config()
    elections = {e["id"]: e for e in cfg["elections"]}

    # ---------------------------------------------------------------- pagina
    @app.get("/")
    def index():
        return send_from_directory(WEB, "index.html")

    @app.get("/<path:asset>")
    def static_asset(asset):
        return send_from_directory(WEB, asset)

    def _serve_geo(path):
        """Serveix la versio ja comprimida si el navegador l'accepta.

        send_from_directory transmet el fitxer sense passar pel filtre de
        compressio, aixi que els .gz es preparen en generar la geometria i
        aqui nomes s'escull quin dels dos s'envia.
        """
        if not path.exists():
            return jsonify({"error": "sense geometria per a aquest nivell"}), 404
        packed = path.with_suffix(".json.gz")
        if packed.exists() and "gzip" in (request.headers.get("Accept-Encoding") or ""):
            resp = send_from_directory(packed.parent, packed.name)
            resp.headers["Content-Encoding"] = "gzip"
            resp.headers["Content-Type"] = "application/json"
            return resp
        return send_from_directory(path.parent, path.name)

    @app.get("/geo/<country>.json")
    def geometry(country):
        return _serve_geo(geo.GEO_DIR / geo.config()[country.upper()]["file"])

    @app.get("/geo/<country>/<level>.json")
    def geometry_level(country, level):
        """Un nivell territorial concret, per als paisos servits com a GeoJSON."""
        return _serve_geo(geo.level_path(country.upper(), level))

    @app.get("/api/geoinfo")
    def api_geoinfo():
        """Quins mapes hi ha i en quin format, perque el client sapiga que demanar."""
        out = {}
        for country, spec in geo.config().items():
            if spec.get("format") == "geojson":
                levels = [lv for lv in spec["sources"] if geo.level_path(country, lv).exists()]
                if levels:
                    out[country] = {"format": "geojson", "levels": levels,
                                    "note": spec.get("note")}
            elif (geo.GEO_DIR / spec["file"]).exists():
                out[country] = {"format": "topojson", "levels": spec.get("levels", {})}
        return jsonify(out)

    @app.after_request
    def compress(response):
        """Comprimir la geometria. El fitxer de comunes franceses fa 35 MB en
        text i 7 comprimit: sense aixo, canviar de nivell es fa etern."""
        if (response.direct_passthrough
                or "gzip" not in (request.headers.get("Accept-Encoding") or "")
                or response.status_code != 200):
            return response
        ctype = response.headers.get("Content-Type", "")
        if not any(t in ctype for t in ("json", "javascript", "text/")):
            return response
        data = response.get_data()
        if len(data) < 4096:
            return response
        response.set_data(gzip.compress(data, 5))
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Content-Length"] = len(response.get_data())
        return response

    # ----------------------------------------------------------------- API
    @app.get("/api/elections")
    def api_elections():
        """Que hi ha disponible de debo: nomes el que te enquestes a la base."""
        conn = db.connect()
        counts = {(r["election_id"]): r for r in conn.execute(
            """SELECT election_id, COUNT(*) n, MAX(fieldwork_end) last,
                      COUNT(DISTINCT pollster) houses
               FROM poll GROUP BY election_id""")}
        has_map = {r["election_id"] for r in conn.execute(
            "SELECT DISTINCT election_id FROM projection")}
        mapped = {c for c, spec in geo.config().items()
                  if (geo.GEO_DIR / spec["file"]).exists()
                  or any(geo.level_path(c, lv).exists() for lv in (spec.get("sources") or {}))}
        out = []
        for eid, meta in elections.items():
            row = counts.get(eid)
            if not row:
                continue
            out.append({
                "id": eid,
                "label": meta.get("label", eid),
                "country": meta["country"],
                "polls": row["n"],
                "pollsters": row["houses"],
                "last_fieldwork": row["last"],
                "has_map": eid in has_map,
                "map_country": meta["country"] if meta["country"] in mapped else None,
                "baseline": (meta.get("baseline") or {}).get("election"),
                "chamber": (meta.get("chamber") or {}).get("name"),
            })
        return jsonify(out)

    @app.get("/api/summary/<election_id>")
    def api_summary(election_id):
        conn = db.connect()
        country = elections.get(election_id, {}).get("country", "ES")
        rows = conn.execute(
            """SELECT party, share, lo, hi, n_polls FROM aggregate
               WHERE election_id = ? AND scope_code = '' ORDER BY share DESC""",
            (election_id,)).fetchall()
        seats = {r["party"]: r["seats"] for r in conn.execute(
            """SELECT r.party, CAST(AVG((r.seats_lo + r.seats_hi) / 2.0) AS INT) seats
               FROM poll p JOIN poll_result r ON r.poll_id = p.id
               WHERE p.election_id = ? AND r.seats_lo IS NOT NULL
                 AND p.fieldwork_end >= date('now', '-30 days')
               GROUP BY r.party""", (election_id,))}
        return jsonify({
            "election": election_id,
            "parties": [{
                **parties.meta(r["party"], country),
                "share": r["share"], "lo": r["lo"], "hi": r["hi"],
                "n_polls": r["n_polls"], "seats": seats.get(r["party"]),
            } for r in rows],
        })

    @app.get("/api/trend/<election_id>")
    def api_trend(election_id):
        """Serie temporal per partit: mitjana movil setmanal dels darrers 2 anys."""
        conn = db.connect()
        country = elections.get(election_id, {}).get("country", "ES")
        rows = conn.execute(
            """SELECT strftime('%Y-%W', p.fieldwork_end) wk,
                      MIN(p.fieldwork_end) day, r.party, AVG(r.share) share, COUNT(*) n
               FROM poll p JOIN poll_result r ON r.poll_id = p.id
               WHERE p.election_id = ? AND p.fieldwork_end >= date('now', '-730 days')
               GROUP BY wk, r.party HAVING n >= 1 ORDER BY day""", (election_id,)).fetchall()
        series: dict[str, list] = {}
        for r in rows:
            series.setdefault(r["party"], []).append([r["day"], round(r["share"], 2)])
        top = sorted(series, key=lambda p: -(series[p][-1][1] if series[p] else 0))[:8]
        return jsonify({"series": [{**parties.meta(p, country), "points": series[p]}
                                   for p in top]})

    @app.get("/api/map/<election_id>")
    def api_map(election_id):
        """{codi: [partit, percentatge, marge]} per pintar el mapa.

        `layer=real` -> resultat electoral tal qual el va publicar el Ministeri
        `layer=projection` -> estimacio d'avui (swing de les enquestes)
        """
        conn = db.connect()
        level = request.args.get("level", "municipality")
        layer = request.args.get("layer", "projection")
        meta = elections.get(election_id, {})
        country = meta.get("country", "ES")

        if layer == "real":
            base = (meta.get("baseline") or {}).get("election")
            rows = conn.execute(
                """SELECT code, party, votes * 100.0 / valid_votes AS share
                   FROM election_result
                   WHERE election = ? AND level = ? AND valid_votes > 0""",
                (base, level)).fetchall()
        else:
            rows = conn.execute(
                "SELECT code, party, share FROM projection WHERE election_id = ? AND level = ?",
                (election_id, level)).fetchall()

        shares: dict[str, dict[str, float]] = {}
        for r in rows:
            shares.setdefault(r["code"], {})[r["party"]] = r["share"]

        # Quins partits val la pena enviar, i en quin ordre.
        # El filtre va pel maxim local (un partit regional fort a la seva
        # comarca ha de sortir-hi), pero l'ORDRE va pel pes total: si
        # s'ordenes pel maxim, un partit que treu el 40% en un sol poble
        # passaria davant de Sumar a la llista desplegable.
        peak: dict[str, float] = {}
        weight: dict[str, float] = {}
        for values in shares.values():
            for party, share in values.items():
                if share > peak.get(party, 0):
                    peak[party] = share
                weight[party] = weight.get(party, 0) + share
        keep = sorted((p for p in peak if peak[p] >= 3.0),
                      key=lambda x: -weight[x])[:16]
        index = {p: i for i, p in enumerate(keep)}

        # Format compacte: una llista d'ordre fix de partits i, per a cada
        # territori, [guanyador, marge, share0, share1, ...]. Amb 8.131 municipis
        # i un objecte per partit la resposta es dispararia a diversos megues.
        out = {}
        for code, values in shares.items():
            party, margin = seatlib.winner(values)
            if not party:
                continue
            vector = [0.0] * len(keep)
            for other, share in values.items():
                if other in index:
                    vector[index[other]] = round(share, 1)
            out[code] = [index.get(party, -1), margin] + vector

        used = set(keep) | {v[0] for v in shares.values() for v in [seatlib.winner(v)] if v[0]}
        return jsonify({
            "level": level, "layer": layer, "n": len(out),
            "parties": [parties.meta(p, country) for p in keep],
            "palette": {p: parties.meta(p, country) for p in used},
            "areas": out,
        })

    @app.get("/api/seats/<election_id>")
    def api_seats(election_id):
        """Composicio de la cambra: la real de l'ultima eleccio i l'estimada d'avui."""
        conn = db.connect()
        meta = elections.get(election_id, {})
        chamber = meta.get("chamber")
        country = meta.get("country", "ES")
        if not chamber:
            return jsonify({
                "chamber": None,
                "reason": "Aquesta elecció no reparteix escons "
                          "(les presidencials franceses elegeixen una persona, no una cambra).",
            })

        base = (meta.get("baseline") or {}).get("election")
        # HAVING SUM(seats), no HAVING seats: `seats` tambe es el nom d'una
        # columna real i SQLite li dona prioritat sobre l'alies, de manera que
        # el filtre s'aplicaria a una fila qualsevol del grup. Vox i Sumar treuen
        # zero escons a moltes provincies i desapareixien de la cambra sencera.
        real = {r["party"]: r["total"] for r in conn.execute(
            """SELECT party, SUM(seats) AS total FROM constituency_result
               WHERE election = ? GROUP BY party HAVING SUM(seats) > 0""", (base,))}
        proj = {r["party"]: r["seats"] for r in conn.execute(
            """SELECT party, seats FROM seat_projection
               WHERE election_id = ? AND level = 'chamber'""", (election_id,))}

        def block(source):
            return sorted(
                ({**parties.meta(p, country), "seats": n} for p, n in source.items() if n),
                key=lambda x: (parties.position(x["code"], country), -x["seats"]))

        total = sum(proj.values())
        return jsonify({
            "chamber": chamber["name"],
            "seats": chamber["seats"],
            "allocated": total,
            "majority": chamber["seats"] // 2 + 1,
            "method": chamber.get("method"),
            "approximate": bool(chamber.get("approximate")),
            "partial": bool(chamber.get("partial")),
            "in_play": chamber.get("in_play"),
            "real": block(real),
            "projection": block(proj),
            "baseline": base,
        })

    @app.get("/api/area/<election_id>/<code>")
    def api_area(election_id, code):
        """Detall d'un territori quan s'hi fa clic: real i estimacio, costat a costat."""
        conn = db.connect()
        meta = elections.get(election_id, {})
        country = meta.get("country", "ES")
        base = (meta.get("baseline") or {}).get("election")
        level = request.args.get("level", "municipality")

        real = conn.execute(
            """SELECT party, votes, valid_votes, census, name FROM election_result
               WHERE election = ? AND level = ? AND code = ? ORDER BY votes DESC""",
            (base, level, code)).fetchall()
        proj = conn.execute(
            """SELECT party, share FROM projection
               WHERE election_id = ? AND level = ? AND code = ? ORDER BY share DESC""",
            (election_id, level, code)).fetchall()

        # Els agregats (provincia, comunitat) es desen sense nom perque el nom no
        # esta a les dades del ministeri: el posa el mapa. Cal el `or`, no nomes
        # comprovar si hi ha resultats, o la fitxa sortiria titulada "null".
        name = (real[0]["name"] if real else None) or geo.names(country, level).get(code) or code
        valid = real[0]["valid_votes"] if real else 0
        return jsonify({
            "code": code, "name": name,
            "census": real[0]["census"] if real else None,
            "valid_votes": valid,
            "real": [{**parties.meta(r["party"], country), "votes": r["votes"],
                      "share": round(r["votes"] * 100.0 / valid, 2) if valid else None}
                     for r in real],
            "projection": [{**parties.meta(r["party"], country), "share": r["share"]}
                           for r in proj],
        })

    @app.get("/api/constituency/<election_id>/<code>")
    def api_constituency(election_id, code):
        """Escons d'una circumscripcio i que caldria perque el repartiment canviés."""
        conn = db.connect()
        meta = elections.get(election_id, {})
        country = meta.get("country", "ES")
        base = (meta.get("baseline") or {}).get("election")

        row = conn.execute(
            "SELECT seats FROM constituency WHERE election = ? AND level = 'province' AND code = ?",
            (base, code)).fetchone()
        if not row:
            return jsonify({"magnitude": None})
        magnitude = row["seats"]

        shares = {r["party"]: r["share"] for r in conn.execute(
            """SELECT party, share FROM projection
               WHERE election_id = ? AND level = 'province' AND code = ?""",
            (election_id, code))}
        valid = conn.execute(
            """SELECT valid_votes FROM election_result
               WHERE election = ? AND level = 'province' AND code = ? LIMIT 1""",
            (base, code)).fetchone()
        valid_votes = valid["valid_votes"] if valid else None

        rows = seatlib.sensitivity(shares, magnitude, votes_total=valid_votes)
        # Nomes el que te sentit ensenyar: qui te escons i qui podria arribar-hi.
        # Una llista amb catorze partits al 0,05% amaga la informacio util.
        rows = [r for r in rows if r["seats"] or r["share"] >= 0.5][:12]

        real = {r["party"]: r["seats"] for r in conn.execute(
            """SELECT party, seats FROM constituency_result
               WHERE election = ? AND level = 'province' AND code = ? AND seats > 0""",
            (base, code))}

        # L'escó que balla: el canvi mes barat de tota la circumscripcio.
        candidates = [(r["gain_points"], r["party"], "gain") for r in rows
                      if r["gain_points"] is not None]
        candidates += [(r["lose_points"], r["party"], "lose") for r in rows
                       if r["lose_points"] is not None]
        pivot = min(candidates, default=None)

        # La taula de divisors: l'aritmetica exacta de com s'ha repartit la
        # circumscripcio i quants vots falten al seguent per entrar-hi.
        table = seatlib.quotient_table(shares, magnitude)
        to_votes = (lambda pts: int(round(pts * valid_votes / 100))
                    if valid_votes else None)

        return jsonify({
            "code": code,
            "magnitude": magnitude,
            "valid_votes": valid_votes,
            "threshold": 3.0,
            "rows": [{**parties.meta(r["party"], country), **r} for r in rows],
            "real": [{**parties.meta(p, country), "seats": n}
                     for p, n in sorted(real.items(), key=lambda kv: -kv[1])],
            "pivot": ({"points": pivot[0], "kind": pivot[2],
                       **parties.meta(pivot[1], country)} if pivot else None),
            "dhondt": {
                "cutoff": round(table["cutoff"], 3) if table["cutoff"] else None,
                "won": [{**parties.meta(w["party"], country), "divisor": w["divisor"],
                         "quotient": round(w["quotient"], 3)} for w in table["won"]],
                "next": [{**parties.meta(n["party"], country), "divisor": n["divisor"],
                          "quotient": round(n["quotient"], 3),
                          "needed": round(n["needed"], 2),
                          "needed_votes": to_votes(n["needed"]),
                          "below_threshold": bool(n.get("below_threshold"))}
                         for n in table["next"][:5]],
            },
        })

    @app.get("/api/deputies/<election_id>/<code>")
    def api_deputies(election_id, code):
        """Qui representa aquesta circumscripcio, amb nom i cognoms.

        Les llistes espanyoles son tancades i bloquejades: l'ordre decideix qui
        entra. Aixo permet dir, sobre l'estimacio d'avui, qui hi seria i qui no,
        SEMPRE que els partits repetissin les llistes del 2023 -- cosa que no
        faran. Es una lectura, no una prediccio de noms, i la pantalla ho diu.
        """
        conn = db.connect()
        meta = elections.get(election_id, {})
        country = meta.get("country", "ES")
        base = (meta.get("baseline") or {}).get("election")

        rows = conn.execute(
            """SELECT party, position, name, sex, elected FROM deputy
               WHERE election = ? AND province = ? ORDER BY party, position""",
            (base, code)).fetchall()
        if not rows:
            return jsonify({"real": [], "projected": []})

        projected_seats = {r["party"]: r["seats"] for r in conn.execute(
            """SELECT party, seats FROM seat_projection
               WHERE election_id = ? AND level = 'province' AND code = ?""",
            (election_id, code))}

        by_party: dict[str, list] = {}
        for r in rows:
            by_party.setdefault(r["party"], []).append(dict(r))

        real, projected = [], []
        for party, members in by_party.items():
            # `name` es el del diputat i `party_name` el del partit: si es fessin
            # servir tots dos la clau "name", el segon esborraria el primer.
            info = parties.meta(party, country)
            base_row = {"code": info["code"], "color": info["color"],
                        "party_name": info["name"]}
            for m in members:
                if m["elected"]:
                    real.append({**base_row, "position": m["position"],
                                 "name": m["name"], "sex": m["sex"]})
            for m in members[:projected_seats.get(party, 0)]:
                projected.append({**base_row, "position": m["position"],
                                  "name": m["name"], "sex": m["sex"],
                                  "was_elected": bool(m["elected"])})

        real.sort(key=lambda d: (parties.position(d["code"], country), d["position"]))
        projected.sort(key=lambda d: (parties.position(d["code"], country), d["position"]))
        elected_names = {d["name"] for d in real}
        for d in projected:
            d["new"] = d["name"] not in elected_names
        return jsonify({"real": real, "projected": projected, "baseline": base})

    @app.get("/api/search")
    def api_search():
        """Cerca de territoris per nom. Sense accents i sense distingir majuscules."""
        query = parties.slug(request.args.get("q", ""))
        if len(query) < 2:
            return jsonify([])
        hits = []
        for entry in _search_index():
            if entry["key"].startswith(query):
                hits.append((0, entry))
            elif query in entry["key"]:
                hits.append((1, entry))
            if len(hits) > 400:
                break
        # Primer els que comencen igual, i dins de cada grup el territori mes gran
        # (una comunitat abans que un poble amb el mateix nom).
        order = {"region": 0, "province": 1, "state": 1, "municipality": 2}
        hits.sort(key=lambda h: (h[0], order.get(h[1]["level"], 3), len(h[1]["name"])))
        return jsonify([h[1] for h in hits[:25]])

    @app.get("/api/polls/<election_id>")
    def api_polls(election_id):
        """Les enquestes que hi ha darrere de la mitjana. Sense aixo el numero
        no es pot comprovar, i un numero que no es pot comprovar no val res."""
        conn = db.connect()
        country = elections.get(election_id, {}).get("country", "ES")
        rows = conn.execute(
            """SELECT id, pollster, client, fieldwork_start, fieldwork_end,
                      sample_size, source_url, source_title
               FROM poll WHERE election_id = ?
               ORDER BY fieldwork_end DESC LIMIT 60""", (election_id,)).fetchall()
        ids = [r["id"] for r in rows]
        marks = ",".join("?" * len(ids)) or "NULL"
        results: dict[int, dict] = {}
        for r in conn.execute(
                f"SELECT poll_id, party, share FROM poll_result WHERE poll_id IN ({marks})", ids):
            results.setdefault(r["poll_id"], {})[r["party"]] = r["share"]
        return jsonify([{
            "pollster": r["pollster"], "client": r["client"],
            "start": r["fieldwork_start"], "end": r["fieldwork_end"],
            "sample": r["sample_size"], "url": r["source_url"], "title": r["source_title"],
            "results": [{**parties.meta(p, country), "share": s}
                        for p, s in sorted(results.get(r["id"], {}).items(),
                                           key=lambda kv: -kv[1])[:8]],
        } for r in rows])

    @app.get("/api/sources")
    def api_sources():
        conn = db.connect()
        rows = conn.execute(
            """SELECT source_title, source_url, COUNT(*) n, MAX(fetched_at) fetched
               FROM poll GROUP BY source_url ORDER BY n DESC""").fetchall()
        return jsonify([dict(r) for r in rows])

    return app
