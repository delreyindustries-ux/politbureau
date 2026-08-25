"""Lectura de taules d'enquestes de Wikipedia.

Per que HTML i no `pandas.read_html`: Wikipedia posa els noms dels partits com a
logotips dins les cel.les de capcalera. El text n'es buit; el nom real viu a
l'atribut `title` de l'enllac o a l'`alt` de la imatge. `read_html` els perd tots.
"""
from __future__ import annotations

import datetime as dt
import re
import time
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from .. import parties

USER_AGENT = "politbureau/0.1 (projecte educatiu)"
API = "https://en.wikipedia.org/w/api.php"

# Nomes llegim taules sota aquestes seccions. "Hypothetical scenarios" i
# "Voting preferences" mesuren coses diferents i contaminarien la mitjana.
DEFAULT_SECTIONS = (
    "voting intention estimates",
    "voting intention",
    "opinion polling",
    "polling",
    "national polling",
    "statewide polling",
    "general election polling",
    "party vote",        # aixi es diu la seccio a la Wikipedia italiana
)

# Seccions que caldria excloure encara que la cadena de titols contingui un terme
# permes. "Hypothetical scenarios" son coalicions imaginaries i "Voting preferences"
# es una pregunta diferent: barrejar-les amb la intencio de vot falsejaria la mitjana.
DENIED_SECTIONS = (
    "hypothetical",
    "voting preferences",
    "leadership",
    "preferred prime minister",
    "preferred candidate",
    "approval",
    "seat projection",
    "primary",          # primaries dels EUA: hi competeixen candidats del mateix partit
    "runoff",
    "aggregation",      # mitjanes d'altri: incloure-les seria comptar dues vegades
    "approval rating",
)

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}
MONTHS.update({m[:3]: i for m, i in list(MONTHS.items())})

DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")


@dataclass
class Poll:
    pollster: str
    client: str | None
    fieldwork_start: str | None
    fieldwork_end: str | None
    sample_size: int | None
    turnout: float | None
    results: dict = field(default_factory=dict)   # codi -> (share, seats_lo, seats_hi)


# --------------------------------------------------------------------------- xarxa

MIN_INTERVAL = 0.35        # segons entre peticions: Wikipedia demana no atropellar
_last_call = 0.0


def _throttled_get(session, params, tries=4):
    """Peticio educada: espaia les crides i respecta el Retry-After d'un 429.

    Descarregar 35 pagines d'estat seguides fa que la API talli amb un 429. La
    solucio no es insistir mes fort sino esperar el que ens demanen.
    """
    global _last_call
    delay = MIN_INTERVAL
    for attempt in range(tries):
        gap = time.monotonic() - _last_call
        if gap < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - gap)
        resp = session.get(API, params=params, headers={"User-Agent": USER_AGENT}, timeout=60)
        _last_call = time.monotonic()
        if resp.status_code not in (429, 503):
            resp.raise_for_status()
            return resp
        wait = float(resp.headers.get("Retry-After") or 0) or delay
        time.sleep(min(wait, 30))
        delay *= 2
    resp.raise_for_status()
    return resp


def fetch(page: str, session: requests.Session | None = None) -> dict | None:
    """Retorna {html, url, revid, title} o None si la pagina no existeix."""
    session = session or requests.Session()
    resp = _throttled_get(session, {
        "action": "parse", "page": page, "prop": "text|revid",
        "format": "json", "formatversion": "2", "redirects": "1"})
    payload = resp.json()
    if "error" in payload:
        return None
    parsed = payload["parse"]
    title = parsed.get("title", page)
    return {
        "html": parsed["text"],
        "revid": parsed.get("revid"),
        "title": title,
        "url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"),
    }


# ----------------------------------------------------------------------- valors

# Compte amb el `%`: si s'escriu `\s*%?` l'espai opcional es menja el separador
# entre percentatge i escons, i el grup dels escons ja no troba el `\s+` que espera.
_CELL = re.compile(
    r"(?P<share>\d{1,3}(?:[.,]\d+)?)(?:\s?%)?"                 # 31.8 | 31,8 | 48% | 48 %
    r"(?:\s+(?P<lo>\d{1,3})(?:\s*[/-]\s*(?P<hi>\d{1,3}))?)?"   # 130 | 142/144
)

_EMPTY = {"", "-", "?", "n/a", "tie", "—"}


def parse_cell(text):
    """'31.8 130' -> (31.8, 130, 130) | '32.7 142/144' -> (32.7, 142, 144) | '-' -> None*3"""
    text = re.sub(r"\[[^\]]*\]", "", str(text)).translate(DASHES).strip()
    if text.lower() in _EMPTY:
        return None, None, None
    m = _CELL.search(text)
    if not m:
        return None, None, None
    share = float(m.group("share").replace(",", "."))
    if share > 100:            # gairebe sempre es un nombre d'escons mal llegit
        return None, None, None
    lo = int(m.group("lo")) if m.group("lo") else None
    hi = int(m.group("hi")) if m.group("hi") else lo
    return share, lo, hi


def parse_int(text):
    text = re.sub(r"\[[^\]]*\]", "", str(text))
    m = re.search(r"\d[\d,.\s]*", text)
    if not m:
        return None
    digits = re.sub(r"[^\d]", "", m.group(0))
    return int(digits) if digits else None


# ------------------------------------------------------------------------ dates

def _day_month(fragment):
    fragment = fragment.strip().strip(",")
    month = None
    for name, num in MONTHS.items():
        if re.search(r"\b" + name + r"\b", fragment, re.IGNORECASE):
            month = num
            break
    day = re.search(r"\b(\d{1,2})\b", fragment)
    return (int(day.group(1)) if day else None), month


def parse_fieldwork(text, anchor_year):
    """Accepta '1 Jul-12 Aug', '22-29 Dec', '31 Dec', 'August 12-14, 2026',
    'September 30 - October 2, 2026'. L'any explicit mana sobre anchor_year."""
    text = re.sub(r"\[[^\]]*\]", "", str(text)).translate(DASHES).strip()
    if not text:
        return None, None
    year_match = re.search(r"\b(?:19|20)\d{2}\b", text)
    year = int(year_match.group(0)) if year_match else anchor_year
    text = re.sub(r"\b(?:19|20)\d{2}\b", "", text)

    parts = [p for p in text.split("-") if p.strip()]
    if not parts:
        return None, None
    end_day, end_month = _day_month(parts[-1])
    start_day, start_month = _day_month(parts[0]) if len(parts) >= 2 else (end_day, end_month)

    # El mes pot faltar a qualsevol banda segons el pais: l'angles escriu
    # "August 16-17" (mes al davant) i el castella "22-29 Dec" (mes al darrere).
    if end_month is None:
        end_month = start_month
    if start_month is None:
        start_month = end_month
    if end_day is None or end_month is None:
        return None, None
    start_day = start_day or end_day

    try:
        end = dt.date(year, end_month, end_day)
        # El treball de camp no pot acabar abans de comencar: si passa, creua l'any nou.
        start_year = year - 1 if (start_month, start_day) > (end_month, end_day) else year
        start = dt.date(start_year, start_month, start_day)
    except ValueError:
        return None, None
    return start.isoformat(), end.isoformat()


# ---------------------------------------------------------------------- taules

HEADINGS = ["h1", "h2", "h3", "h4", "h5", "h6"]


def heading_chain(table):
    """Jerarquia real de seccions sobre una taula, de la mes propera a la mes alta.

    Cal caminar enrere quedant-se nomes amb els encapcalaments de nivell
    estrictament decreixent: si no, un h5 germa anterior es colaria com si fos pare.
    """
    chain, min_level, node = [], 99, table
    while True:
        node = node.find_previous(HEADINGS)
        if node is None:
            break
        level = int(node.name[1])
        if level < min_level:
            min_level = level
            chain.append(node.get_text(strip=True))
            if level <= 2:
                break
    return chain


def _section_of(table):
    return " > ".join(heading_chain(table)).lower()


def poll_tables(soup, allowed=DEFAULT_SECTIONS, denied=DENIED_SECTIONS):
    """Cedeix (taula, seccio, any_o_None).

    A Wikipedia les taules d'enquestes es parteixen per anys, i l'any es un
    encapcalament propi ('2026'). Quan hi es, val mes que qualsevol deduccio.
    """
    for table in soup.select("table.wikitable"):
        chain = heading_chain(table)
        section = " > ".join(chain).lower()
        if allowed and not any(a in section for a in allowed):
            continue
        if denied and any(d in section for d in denied):
            continue
        year = next((int(h) for h in chain if re.fullmatch(r"(?:19|20)\d{2}", h.strip())), None)
        yield table, section, year


def grid(table):
    """Expandeix la taula a una matriu rectangular resolent rowspan i colspan.

    Sense aixo els indexs de columna es desplacen: el CIS, per exemple, agrupa
    quatre files sota una sola cel.la de data amb rowspan=4, i les tres files
    seguents semblen tenir la data on hi ha la participacio.
    """
    trs = table.find_all("tr")
    matrix = [[] for _ in trs]
    for r, tr in enumerate(trs):
        col = 0
        for cell in tr.find_all(["td", "th"], recursive=False):
            while col < len(matrix[r]) and matrix[r][col] is not None:
                col += 1
            rowspan = int(cell.get("rowspan") or 1)
            colspan = int(cell.get("colspan") or 1)
            for dr in range(rowspan):
                if r + dr >= len(matrix):
                    break
                target = matrix[r + dr]
                for dc in range(colspan):
                    idx = col + dc
                    while len(target) <= idx:
                        target.append(None)
                    target[idx] = cell
            col += colspan
    return matrix


def cell_text(cell):
    if cell is None:
        return ""
    return re.sub(r"\[[^\]]*\]", "", cell.get_text(" ", strip=True)).strip()


def _parties_in_row(cells, country):
    mapping, unknown = {}, []
    for col, cell in enumerate(cells):
        if cell is None:
            continue
        link, img, abbr = cell.find("a"), cell.find("img"), cell.find("abbr")
        for label in (abbr.get("title") if abbr else None,
                      link.get("title") if link else None,
                      img.get("alt") if img else None,
                      cell.get_text(" ", strip=True)):
            if not label:
                continue
            code, known = parties.resolve(label, country)
            if code:
                mapping[col] = code
                if not known:
                    unknown.append(label)
            break
    return mapping, unknown


def header_parties(table, country, max_header_rows=3):
    """{index_columna: codi_partit} llegint title/alt dels logotips.

    Wikipedia sovint parteix la capcalera en dues files: la primera nomes agrupa
    ("Coalitions" / "Parties") i la segona porta les sigles. Provem les primeres
    files i ens quedem amb la que reconegui mes partits.
    """
    rows = grid(table)
    if not rows:
        return {}, [], 0
    best, best_unknown, best_row, best_score = {}, [], 0, (-1, -1)
    for i, row in enumerate(rows[:max_header_rows]):
        filled = [c for c in row if c is not None]
        if not filled:
            continue
        # Nomes una fila de capcalera de debo. Sense aquesta comprovacio, en taules
        # dels EUA la primera fila de dades guanya i els percentatges (51.0, 43.0)
        # acaben registrats com si fossin partits.
        if sum(1 for c in filled if c.name == "th") < len(filled) / 2:
            continue
        mapping, unknown = _parties_in_row(row, country)
        # Puntuar per codis DISTINTS i reconeguts, mai per nombre de columnes:
        # grid() replica una cel.la amb colspan=12 a dotze columnes, de manera que
        # una fila de grups ("Parties", "Coalitions") guanyaria la de sigles reals.
        codes = set(mapping.values())
        score = (len({c for c in codes if not c.startswith("?")}), len(codes))
        if score > best_score:
            best, best_unknown, best_row, best_score = mapping, unknown, i, score
    return best, best_unknown, best_row


def _best_date_col(data_rows, header_text, party_cols, anchor_year):
    """Tria la columna de dates provant-les, no fiant-se del titol.

    Cada Wikipedia posa el titol d'una manera ("Fieldwork date", "Date(s)
    administered", "Date updated") i a mes hi ha taules amb columnes de data
    duplicades. Comptar quantes files parsegen de debo es molt mes fiable.
    """
    sample = data_rows[:40]
    width = max((len(r) for r in sample), default=0)
    best_col, best_score = 1, -1
    for col in range(min(width, 6)):
        if col in party_cols:
            continue
        hits = sum(1 for row in sample
                   if len(row) > col and parse_fieldwork(cell_text(row[col]), anchor_year)[1])
        hint = 1 if col < len(header_text) and (
            "date" in header_text[col] or "fieldwork" in header_text[col]) else 0
        score = hits * 2 + hint            # el titol nomes desempata
        if score > best_score:
            best_col, best_score = col, score
    return best_col


def parse_table(table, country, anchor_year):
    party_cols, unknown, header_row = header_parties(table, country)
    if not party_cols:
        return [], unknown

    rows = grid(table)
    # grid() replica les cel.les amb rowspan a totes les files que ocupen, aixi que
    # la fila de capcalera escollida ja porta tambe les etiquetes de la fila de dalt.
    header_text = [cell_text(c).lower() for c in rows[header_row]]
    data_rows = rows[header_row + 1:]

    date_col = _best_date_col(data_rows, header_text, party_cols, anchor_year)
    sample_col = next((i for i, h in enumerate(header_text) if "sample" in h), None)
    turnout_col = next((i for i, h in enumerate(header_text) if "turnout" in h), None)
    # La casa enquestadora no sempre es la primera columna: a Italia l'ordre es
    # "Fieldwork date | Polling firm | Sample size | partits...".
    pollster_col = next(
        (i for i, h in enumerate(header_text)
         if any(k in h for k in ("polling firm", "poll source", "pollster",
                                 "source of poll", "aggregator", "polling aggregator"))),
        next((i for i in range(len(header_text))
              if i not in party_cols and i not in (date_col, sample_col, turnout_col)), 0),
    )

    polls = []
    year, previous_end = anchor_year, None

    for cells in data_rows:
        if len(cells) < 4:                     # separadors i files d'esdeveniments
            continue
        raw = cell_text(cells[pollster_col]) if len(cells) > pollster_col else ""
        if not raw:
            continue
        # Algunes taules repeteixen la capcalera enmig de les dades.
        if raw.lower() in header_text:
            continue
        # Les files de resultat electoral real son baseline, no enquestes.
        if re.search(r"\b(elections?|referendum)\b", raw, re.IGNORECASE):
            continue

        date_text = cell_text(cells[date_col]) if len(cells) > date_col else ""
        start, end = parse_fieldwork(date_text, year)
        if end and previous_end and end > previous_end:
            year -= 1                          # la taula baixa en el temps: hem creuat l'any
            start, end = parse_fieldwork(date_text, year)
        if end:
            previous_end = end

        pollster, _, client = raw.partition("/")
        turnout = None
        if turnout_col is not None and len(cells) > turnout_col:
            turnout = parse_cell(cell_text(cells[turnout_col]))[0]

        poll = Poll(
            pollster=pollster.strip() or raw,
            client=client.strip() or None,
            fieldwork_start=start,
            fieldwork_end=end,
            sample_size=(parse_int(cell_text(cells[sample_col]))
                         if sample_col is not None and len(cells) > sample_col else None),
            turnout=turnout,
        )
        for col, code in party_cols.items():
            if col >= len(cells):
                continue
            share, lo, hi = parse_cell(cell_text(cells[col]))
            if share is not None:
                poll.results[code] = (share, lo, hi)
        if poll.results:
            polls.append(poll)
    return polls, unknown
