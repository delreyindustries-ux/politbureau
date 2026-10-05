"""Veda electoral (LOREG art. 69.7) i sondeigs a peu d'urna.

Durant els cinc dies anteriors a la votacio esta prohibit publicar, difondre o
reproduir enquestes electorals. Decisio de l'Alfonso (05/10/2026): durant la
veda NO entren enquestes noves (la web es queda amb les que ja tenia), i quan
tanquen els col.legis entren els sondeigs a peu d'urna.

A sources.yaml, per eleccio:
    election_date: "2026-11-29"
    veda: {from: "2026-11-24T00:00:00+01:00", to: "2026-11-29T20:00:00+01:00"}

`to` es el tancament dels col.legis a la peninsula (20 h), que es quan els
mitjans publiquen els sondeigs a peu d'urna. Les hores porten el desfasament
explicit (+01:00, hivern) per no dependre de la zona horaria de la maquina.
"""
from __future__ import annotations

import datetime as dt


def _now(now=None):
    return now or dt.datetime.now(dt.timezone.utc)


def window(election):
    v = (election or {}).get("veda")
    if not v:
        return None
    return dt.datetime.fromisoformat(v["from"]), dt.datetime.fromisoformat(v["to"])


def active(election, now=None) -> bool:
    """Som dins la veda: no s'ha de llegir cap enquesta nova."""
    w = window(election)
    return bool(w) and w[0] <= _now(now) < w[1]


def polls_closed(election, now=None) -> bool:
    """Els col.legis ja han tancat: es poden fer servir els sondeigs a peu d'urna."""
    w = window(election)
    return bool(w) and _now(now) >= w[1]


def is_exit_poll(election, fieldwork_end) -> bool:
    """Una enquesta amb treball de camp acabat el mateix dia de la votacio es
    un sondeig a peu d'urna (a Wikipedia no porten cap altra marca fiable)."""
    day = (election or {}).get("election_date")
    return bool(day) and str(fieldwork_end or "")[:10] == day


def select_polls(election, polls, now=None):
    """Quines enquestes entren a la mitjana.

    - Abans que tanquin els col.legis, un sondeig del dia de la votacio no hi
      entra mai (si n'hi hagues algun, publicar-lo abans de les 20 h seria il.legal).
    - Quan han tancat, si hi ha sondeigs a peu d'urna, la mitjana es fa NOMES amb
      ells: mesuren el vot real d'aquell dia i les enquestes d'abans ja no aporten res.
    Retorna (enquestes, mode) amb mode 'normal' o 'peu_urna'.
    """
    if not (election or {}).get("election_date"):
        return polls, "normal"
    exit_polls = [p for p in polls if is_exit_poll(election, p.get("fieldwork_end"))]
    if polls_closed(election, now) and exit_polls:
        return exit_polls, "peu_urna"
    return [p for p in polls if not is_exit_poll(election, p.get("fieldwork_end"))], "normal"


def status(election, now=None) -> str:
    """'veda', 'peu_urna_obert' (col.legis tancats) o 'normal'."""
    if active(election, now):
        return "veda"
    if polls_closed(election, now):
        return "peu_urna_obert"
    return "normal"
