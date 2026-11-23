"""Les pagines que no son fitxes de territori: portada, mapa, legals i sitemap."""
from __future__ import annotations

import datetime as dt
import gzip
import json
import re
import shutil
from pathlib import Path

import yaml

from .. import parties, veda
from ..ingest.runner import load_config as load_sources
from ..geo import fetch as geo
from . import i18n
from .build import (DIST, ELECTION, ROOT, WEB, BASELINE_YEAR, simulator_for,
                    thousands)
from .render import render_page, write

LEGAL = {
    "aviso-legal": {
        "es": ("Aviso legal", """
<h2>Titular</h2>
<p>Este sitio web es titularidad de <b>{owner}</b>. Contacto: <b>{email}</b>.</p>
<p>De acuerdo con el artículo 10 de la Ley 34/2002, de servicios de la sociedad de la
información y de comercio electrónico, se hacen constar estos datos por tratarse de
un sitio que obtiene ingresos por publicidad.</p>

<h2>Qué es este sitio</h2>
<p>Publicamos dos cosas claramente separadas y nunca mezcladas:</p>
<ul>
<li><b>Resultados electorales reales</b>: el escrutinio oficial publicado por el
Ministerio del Interior. Son datos verificados.</li>
<li><b>Estimación de voto</b>: un modelo propio que parte de esos resultados y les
aplica el desplazamiento de voto que indican las encuestas publicadas.
<b>No es una encuesta ni una predicción</b>, y no existen encuestas municipales.</li>
</ul>
<p>La metodología está publicada íntegra y cualquiera puede comprobar el cálculo.</p>

<h2>Origen de los datos y condiciones de reutilización</h2>
<p>Los resultados electorales proceden del portal Infoelectoral del Ministerio del
Interior. Sus condiciones generales de reutilización permiten expresamente el uso
comercial, con la obligación de citar la fuente y no desnaturalizar la información.
Ambas se cumplen: la fuente se cita en cada página y los datos se publican sin alterar.</p>
<p>La cartografía procede del Instituto Geográfico Nacional, con licencia CC BY 4.0.</p>
<p>Los datos de encuestas se recopilan de los artículos de Wikipedia, disponibles bajo
licencia CC BY-SA 4.0. Los datos de las encuestas son hechos y sus fichas técnicas se
citan individualmente.</p>

<h2>Responsabilidad</h2>
<p>La estimación de voto es un modelo estadístico y puede equivocarse. No debe usarse
como base para ninguna decisión que dependa de conocer un resultado electoral futuro.
El titular no responde de las decisiones que terceros tomen a partir de ella.</p>
"""),
        "ca": ("Avís legal", """
<h2>Titular</h2>
<p>El titular d'aquest lloc web és <b>{owner}</b>. Contacte: <b>{email}</b>.</p>
<p>D'acord amb l'article 10 de la Llei 34/2002, de serveis de la societat de la
informació i de comerç electrònic, es fan constar aquestes dades perquè es tracta
d'un lloc que obté ingressos per publicitat.</p>

<h2>Què és aquest lloc</h2>
<p>Publiquem dues coses clarament separades i mai barrejades:</p>
<ul>
<li><b>Resultats electorals reals</b>: l'escrutini oficial publicat pel Ministeri de
l'Interior. Són dades verificades.</li>
<li><b>Estimació de vot</b>: un model propi que parteix d'aquests resultats i hi aplica
el desplaçament de vot que indiquen les enquestes publicades.
<b>No és una enquesta ni una predicció</b>, i no existeixen enquestes municipals.</li>
</ul>
<p>La metodologia està publicada sencera i qualsevol pot comprovar-ne el càlcul.</p>

<h2>Origen de les dades i condicions de reutilització</h2>
<p>Els resultats electorals provenen del portal Infoelectoral del Ministeri de
l'Interior. Les seves condicions generals de reutilització permeten expressament l'ús
comercial, amb l'obligació de citar la font i no desnaturalitzar la informació.
Totes dues es compleixen: la font se cita a cada pàgina i les dades es publiquen
sense alterar.</p>
<p>La cartografia prové de l'Institut Geogràfic Nacional, amb llicència CC BY 4.0.</p>
<p>Les dades d'enquestes es recullen dels articles de Wikipedia, disponibles amb
llicència CC BY-SA 4.0. Les dades de les enquestes són fets i les seves fitxes
tècniques se citen individualment.</p>

<h2>Responsabilitat</h2>
<p>L'estimació de vot és un model estadístic i es pot equivocar. No s'ha de fer servir
com a base de cap decisió que depengui de conèixer un resultat electoral futur.
El titular no respon de les decisions que tercers hi puguin basar.</p>
"""),
    },
    "privacidad": {
        "es": ("Política de privacidad", """
<h2>Qué datos tratamos</h2>
<p>Este sitio <b>no tiene registro de usuarios, ni formularios, ni recoge datos
personales por sí mismo</b>. No hay base de datos de visitantes.</p>

<h2>Publicidad de terceros</h2>
<p>El sitio se financia con publicidad de Google AdSense. Si aceptas las cookies,
Google puede usar cookies e identificadores para mostrar anuncios y medir su
rendimiento, y puede tratar datos como tu dirección IP, el navegador y las páginas
visitadas. Google actúa como responsable independiente de ese tratamiento.</p>
<p>Puedes consultar cómo trata Google esos datos en
<a href="https://policies.google.com/technologies/partner-sites" rel="nofollow noopener"
target="_blank">policies.google.com/technologies/partner-sites</a> y configurar tus
preferencias en <a href="https://adssettings.google.com" rel="nofollow noopener"
target="_blank">adssettings.google.com</a>.</p>

<h2>Mapa de la ciudad</h2>
<p>En la ficha de cada municipio, el botón «Mostrar el mapa de la ciudad» carga los
calles de <a href="https://openfreemap.org" rel="nofollow noopener" target="_blank">OpenFreeMap</a>
(datos de OpenStreetMap) y la librería MapLibre desde
<a href="https://unpkg.com" rel="nofollow noopener" target="_blank">unpkg.com</a>.
<b>Solo si lo pulsas</b>, tu navegador se conecta a esos dos servidores, que reciben
tu dirección IP como cualquier servidor web. No se usan cookies. Si no lo pulsas,
el mapa de secciones se dibuja sin ninguna conexión externa.</p>

<h2>Si rechazas</h2>
<p>Si rechazas las cookies, <b>no se carga ningún script de Google</b> y el sitio
funciona con normalidad. Tu decisión se guarda en el almacenamiento local de tu
navegador, que no se envía a ningún servidor y puedes borrar cuando quieras.</p>

<h2>Tus derechos</h2>
<p>Puedes ejercer los derechos de acceso, rectificación, supresión, oposición,
limitación y portabilidad escribiendo a <b>{email}</b>. También puedes reclamar ante
la Agencia Española de Protección de Datos (<a href="https://www.aepd.es"
rel="nofollow noopener" target="_blank">aepd.es</a>).</p>
"""),
        "ca": ("Política de privadesa", """
<h2>Quines dades tractem</h2>
<p>Aquest lloc <b>no té registre d'usuaris, ni formularis, ni recull dades personals
per si mateix</b>. No hi ha cap base de dades de visitants.</p>

<h2>Publicitat de tercers</h2>
<p>El lloc es finança amb publicitat de Google AdSense. Si acceptes les galetes,
Google pot fer servir galetes i identificadors per mostrar anuncis i mesurar-ne el
rendiment, i pot tractar dades com la teva adreça IP, el navegador i les pàgines
visitades. Google actua com a responsable independent d'aquest tractament.</p>
<p>Pots consultar com tracta Google aquestes dades a
<a href="https://policies.google.com/technologies/partner-sites" rel="nofollow noopener"
target="_blank">policies.google.com/technologies/partner-sites</a> i configurar les
teves preferències a <a href="https://adssettings.google.com" rel="nofollow noopener"
target="_blank">adssettings.google.com</a>.</p>

<h2>Mapa de la ciutat</h2>
<p>A la fitxa de cada municipi, el botó «Mostrar el mapa de la ciutat» carrega els
carrers d'<a href="https://openfreemap.org" rel="nofollow noopener" target="_blank">OpenFreeMap</a>
(dades d'OpenStreetMap) i la llibreria MapLibre des
d'<a href="https://unpkg.com" rel="nofollow noopener" target="_blank">unpkg.com</a>.
<b>Només si el prems</b>, el teu navegador es connecta a aquests dos servidors, que
reben la teva adreça IP com qualsevol servidor web. No es fan servir galetes. Si no
el prems, el mapa de seccions es dibuixa sense cap connexió externa.</p>

<h2>Si ho rebutges</h2>
<p>Si rebutges les galetes, <b>no es carrega cap script de Google</b> i el lloc
funciona amb normalitat. La teva decisió es guarda a l'emmagatzematge local del
navegador, no s'envia a cap servidor i la pots esborrar quan vulguis.</p>

<h2>Els teus drets</h2>
<p>Pots exercir els drets d'accés, rectificació, supressió, oposició, limitació i
portabilitat escrivint a <b>{email}</b>. També pots reclamar davant l'Agència
Espanyola de Protecció de Dades (<a href="https://www.aepd.es" rel="nofollow noopener"
target="_blank">aepd.es</a>).</p>
"""),
    },
    "cookies": {
        "es": ("Política de cookies", """
<h2>Cookies que usamos</h2>
<p>Ninguna es necesaria para que el sitio funcione. Todo el contenido se ve sin
aceptar nada.</p>
<table class="results"><thead><tr><th>Tipo</th><th>Quién</th><th>Para qué</th></tr></thead>
<tbody>
<tr><td>Publicidad</td><td>Google AdSense</td>
    <td>Mostrar anuncios y medir su rendimiento. Solo se cargan si las aceptas.</td></tr>
<tr><td>Preferencia</td><td>Este sitio</td>
    <td>Recordar si has aceptado o rechazado. Se guarda en tu navegador y no se
        envía a ningún servidor.</td></tr>
</tbody></table>

<h2>Cómo cambiar tu decisión</h2>
<p><button type="button" onclick="pbResetConsent()" class="btn">Volver a decidir</button></p>
<p>También puedes borrar el almacenamiento local del sitio desde la configuración de
tu navegador.</p>
"""),
        "ca": ("Política de galetes", """
<h2>Galetes que fem servir</h2>
<p>Cap no és necessària perquè el lloc funcioni. Tot el contingut es veu sense
acceptar res.</p>
<table class="results"><thead><tr><th>Tipus</th><th>Qui</th><th>Per a què</th></tr></thead>
<tbody>
<tr><td>Publicitat</td><td>Google AdSense</td>
    <td>Mostrar anuncis i mesurar-ne el rendiment. Només es carreguen si les acceptes.</td></tr>
<tr><td>Preferència</td><td>Aquest lloc</td>
    <td>Recordar si has acceptat o rebutjat. Es guarda al teu navegador i no s'envia
        a cap servidor.</td></tr>
</tbody></table>

<h2>Com canviar la teva decisió</h2>
<p><button type="button" onclick="pbResetConsent()" class="btn">Tornar a decidir</button></p>
<p>També pots esborrar l'emmagatzematge local del lloc des de la configuració del
teu navegador.</p>
"""),
    },
}


# La clau d'i18n.PAGES que correspon a cada document legal.
LEGAL_KEY = {"aviso-legal": "legal", "privacidad": "privacy", "cookies": "cookies"}


def legal_pages(env, cfg):
    site = cfg["site"]
    for slug, langs in LEGAL.items():
        key = LEGAL_KEY[slug]
        for lang in i18n.LANGS:
            title, body = langs[lang]
            canonical = i18n.page_url(key, lang)
            html = render_page(
                env, cfg, "page.html.j2", lang, canonical,
                {lg: i18n.page_url(key, lg) for lg in i18n.LANGS},
                f"{title} · {site['name']}", title,
                heading=title,
                body=body.format(owner=site.get("owner", ""), email=site.get("email", "")))
            write(DIST / canonical.strip("/") / "index.html", html)


def participation_page(env, cfg, urls):
    """Participacio als 500 municipis de tradicio progressista (nit del 29N)."""
    from .. import participation
    rows = participation.load()
    if not rows:
        return 0
    live = participation.live()
    munis = live.get("munis") or {}
    provs = geo.names("ES", "province")
    ref = participation.reference()
    stages = {"14h": ("avance de las 14:00", "avanç de les 14:00"),
              "18h": ("avance de las 18:00", "avanç de les 18:00"),
              "final": ("escrutinio", "escrutini")}

    def fmt_pct(v):
        return "—" if v is None else f"{v:.1f}".replace(".", ",") + " %"

    def fmt_diff(v):
        return ("+" if v >= 0 else "−") + f"{abs(v):.1f}".replace(".", ",")

    def group_now(key):
        """Participacio conjunta dels 500 amb les dades de la nit (ponderada pel cens)."""
        pairs = [((munis.get(r["code"]) or {}).get(key), r["census_2026"] or 0) for r in rows]
        pairs = [(v, w) for v, w in pairs if v is not None and w]
        if not pairs:
            return None
        return round(sum(v * w for v, w in pairs) / sum(w for _, w in pairs), 2)

    c23 = sum(r["c23"] or 0 for r in rows)
    before500 = {k: round(sum(r[f"v23_{s}"] or 0 for r in rows) * 100.0 / c23, 2)
                 for k, s in (("t14", "14"), ("t18", "18"), ("final", "final"))}
    cut = min(r["left_avg"] for r in rows)
    n = 0
    for lang in i18n.LANGS:
        canonical = i18n.page_url("participation", lang)
        view = [{**r, "url": (urls.get(("municipality", r["code"])) or {}).get(lang),
                 "province_name": provs.get(r["province"], r["province"]),
                 "now": munis.get(r["code"]) or {}} for r in rows]
        summary = [
            {"label": (f"Los {len(rows)} municipios" if lang == "es" else f"Els {len(rows)} municipis"),
             "before": before500, "now": {k: group_now(k) for k in ("t14", "t18", "final")}},
            {"label": "Toda España" if lang == "es" else "Tot Espanya",
             "before": {k: ref.get(k) for k in ("t14", "t18", "final")},
             "now": {k: (live.get("national") or {}).get(k) for k in ("t14", "t18", "final")}},
        ]
        stage = stages.get(live.get("stage"), ("", ""))[0 if lang == "es" else 1]
        html = render_page(
            env, cfg, "participation.html.j2", lang, canonical,
            {lg: i18n.page_url("participation", lg) for lg in i18n.LANGS},
            ("Participación en los feudos progresistas · 29N" if lang == "es"
             else "Participació als feus progressistes · 29N"),
            (f"Participación en los {len(rows)} municipios con más voto de izquierda de "
             "las últimas generales, hora a hora el 29N y comparada con 2023." if lang == "es" else
             f"Participació als {len(rows)} municipis amb més vot d'esquerres de les darreres "
             "generals, hora a hora el 29N i comparada amb el 2023."),
            rows=view, summary=summary, cut=cut, pct=fmt_pct, diff=fmt_diff,
            live={**live, "stage_label": stage})
        write(DIST / canonical.strip("/") / "index.html", html)
        n += 1
    return len(rows)


def strongholds_page(env, cfg, urls):
    """La llista dels 500 feus progressistes, amb el vot a l'esquerra de cada eleccio."""
    from .. import participation
    rows = participation.load()
    if not rows:
        return 0
    provs = geo.names("ES", "province")

    def fmt_pct(v):
        return "—" if v is None else f"{v:.1f}".replace(".", ",") + " %"

    for lang in i18n.LANGS:
        canonical = i18n.page_url("strongholds", lang)
        view = [{**r, "url": (urls.get(("municipality", r["code"])) or {}).get(lang),
                 "province_name": provs.get(r["province"], r["province"])} for r in rows]
        html = render_page(
            env, cfg, "strongholds.html.j2", lang, canonical,
            {lg: i18n.page_url("strongholds", lg) for lg in i18n.LANGS},
            (f"Los {len(rows)} feudos progresistas de España" if lang == "es"
             else f"Els {len(rows)} feus progressistes d'Espanya"),
            (f"Los {len(rows)} municipios con más voto a la izquierda en las generales de 2016, "
             "2019 y 2023, con su porcentaje en cada elección." if lang == "es" else
             f"Els {len(rows)} municipis amb més vot a l'esquerra a les generals del 2016, "
             "2019 i 2023, amb el seu percentatge a cada elecció."),
            rows=view, pct=fmt_pct, cut=min(r["left_avg"] for r in rows),
            total_census=sum(int(r["census_2026"] or 0) for r in rows))
        write(DIST / canonical.strip("/") / "index.html", html)
    return len(rows)


def senate_page(env, cfg, urls, view):
    """El Senat del 29N: qui guanyaria cada escó amb l'estimacio d'avui (09/11/2026)."""
    if not view:
        return 0
    # Qui seu a cada escó (19/11/2026): el mateix clic que al Congrés.
    from . import people as peoplelib
    try:
        people_url = peoplelib.write(DIST, peoplelib.senate(view, urls), stem="senadors-2026")
    except Exception as exc:                          # noqa: BLE001
        print(f"      avis: fitxes dels senadors no generades ({type(exc).__name__}: {exc})")
        people_url = {}
    for lang in i18n.LANGS:
        canonical = i18n.page_url("senate", lang)
        consts = [{**c, "url": (urls.get(("province", c["province"])) or {}).get(lang)}
                  for c in view["constituencies"]]
        lead = view["rows"][0]
        html = render_page(
            env, cfg, "senate.html.j2", lang, canonical,
            {lg: i18n.page_url("senate", lg) for lg in i18n.LANGS},
            ("El Senado el 29N: quién ganaría cada escaño" if lang == "es"
             else "El Senat el 29N: qui guanyaria cada escó"),
            (f"Estimación de los {view['elected']} senadores que se eligen el 29 de noviembre, "
             f"provincia a provincia y con nombres: {lead['name']} {lead['now']}." if lang == "es" else
             f"Estimació dels {view['elected']} senadors que s'escullen el 29 de novembre, "
             f"província a província i amb noms: {lead['name']} {lead['now']}."),
            v=view, consts=consts, people_url=people_url.get(lang, ""))
        write(DIST / canonical.strip("/") / "index.html", html)
    return len(view["constituencies"])


_DIM_TITLES = {
    "size": {"es": "Por tamaño del municipio (habitantes)", "ca": "Per mida del municipi (habitants)"},
    "renda": {"es": "Por renta neta por persona", "ca": "Per renda neta per persona"},
    "edat": {"es": "Por edad media", "ca": "Per edat mitjana"},
    "estr": {"es": "Por porcentaje de población extranjera", "ca": "Per percentatge de població estrangera"},
    "atur": {"es": "Por paro registrado (sobre la población de 18 a 64 años)",
             "ca": "Per atur registrat (sobre la població de 18 a 64 anys)"},
}


def conversation_page(env, cfg, conn):
    """Termometre de conversa (20/11/2026): atencio a xarxes, premsa i Viquipedia
    de cada partit, al costat del vot de les enquestes. No entra a la mitjana."""
    from .. import conversa
    vote = dict(conn.execute(
        "SELECT party, share FROM aggregate WHERE election_id = ? AND scope_code = ''",
        (ELECTION,)).fetchall())
    s = conversa.summary(vote)
    if not s:
        return 0
    for r in s["rows"]:
        meta = parties.meta(r["code"], "ES", ELECTION)
        r["name"], r["color"] = meta["name"], meta["color"]
        pts = [(i, v) for i, v in enumerate(s["spark"].get(r["code"]) or []) if v is not None]
        top = max((v for row in s["spark"].values() for v in row if v is not None), default=0) or 1
        if len(pts) > 1:
            n = len(s["spark"][r["code"]]) - 1 or 1
            r["path"] = "M" + " L".join(f"{120 * i / n:.1f},{26 - 24 * v / top:.1f}" for i, v in pts)
    for lang in i18n.LANGS:
        canonical = i18n.page_url("conversation", lang)
        html = render_page(
            env, cfg, "conversa.html.j2", lang, canonical,
            {lg: i18n.page_url("conversation", lg) for lg in i18n.LANGS},
            ("Termómetro de conversación: quién ocupa la conversación y quién tiene los votos" if lang == "es"
             else "Termòmetre de conversa: qui ocupa la conversa i qui té els vots"),
            ("Cuánto se habla de cada partido y de su líder en Bluesky, en la prensa y en Wikipedia, "
             "comparado con su voto en las encuestas." if lang == "es" else
             "Quant es parla de cada partit i del seu líder a Bluesky, a la premsa i a la Viquipèdia, "
             "comparat amb el seu vot a les enquestes."),
            s=s, fdate=_fdate)
        write(DIST / canonical.strip("/") / "index.html", html)
    return len(s["rows"])


def groups_page(env, cfg):
    """Com vota cada col·lectiu (20/11/2026): microdades del CIS (collectius.py)."""
    from .. import collectius
    d = collectius.load()
    if not d.get("dims"):
        return 0
    cols = []
    for p in d["parties"]:
        if p["code"] == "OTHER":
            cols.append({"code": "OTHER", "name": {"ca": "Altres", "es": "Otros"}, "color": "#9e9e9e"})
        else:
            meta = parties.meta(p["code"], "ES", ELECTION)
            name = p["cis"] if p["code"] == "SUMAR" else meta["name"]
            cols.append({"code": p["code"], "name": {"ca": name, "es": name}, "color": meta["color"]})
    months = sorted(s["month"] for s in d["studies"] if s.get("month"))
    for lang in i18n.LANGS:
        canonical = i18n.page_url("groups", lang)
        html = render_page(
            env, cfg, "groups.html.j2", lang, canonical,
            {lg: i18n.page_url("groups", lg) for lg in i18n.LANGS},
            ("Cómo vota cada colectivo: sexo, edad, origen, profesión, clase y religión" if lang == "es"
             else "Com vota cada col·lectiu: sexe, edat, origen, professió, classe i religió"),
            ("El voto de cada grupo de la sociedad según las entrevistas del CIS: mujeres y hombres, "
             "jóvenes y mayores, nacidos fuera, profesiones, clase social, ingresos y religión." if lang == "es"
             else "El vot de cada grup de la societat segons les entrevistes del CIS: dones i homes, "
             "joves i grans, nascuts fora, professions, classe social, ingressos i religió."),
            d=d, cols=cols, months=months, fdate=_fdate)
        write(DIST / canonical.strip("/") / "index.html", html)
    return len(d["dims"])


def society_page(env, cfg, conn):
    """Com vota cada tipus de municipi (09/11/2026): mida, renda, edat, estrangers i atur."""
    from .. import social as sociallib
    if not sociallib.load():
        return 0
    g = sociallib.groups(conn, parties_n=4)
    if not g["dims"]:
        return 0
    meta = {p: parties.meta(p, "ES", ELECTION) for p in g["parties"]}
    soc = sociallib.load()
    month = next((d.get("mes_atur") for d in soc.values() if d.get("mes_atur")), None)
    year = next((int(d["any"]) for d in soc.values() if d.get("any")), None)

    def th(v):
        return f"{int(round(v)):,}".replace(",", ".")

    def label(dim, b, lang):
        if dim == "size":
            if b["hi"] >= 10 ** 9:
                return ("más de " if lang == "es" else "més de ") + th(b["lo"])
            if b["lo"] == 0:
                return ("menos de " if lang == "es" else "menys de ") + th(b["hi"])
            return f"{th(b['lo'])}–{th(b['hi'])}"
        if dim == "renda":
            return f"{th(b['lo'])}–{th(b['hi'])} €"
        if dim == "edat":
            return f"{b['lo']:.1f}–{b['hi']:.1f}".replace(".", ",") + (" años" if lang == "es" else " anys")
        return f"{b['lo']:.1f}–{b['hi']:.1f} %".replace(".", ",")

    for lang in i18n.LANGS:
        canonical = i18n.page_url("society", lang)
        dims = []
        for dim, bins in g["dims"].items():
            rows = []
            for b in bins:
                other_now = 100 - sum(b["now"].values())
                other_before = 100 - sum(b["before"].values())
                rows.append({"label": label(dim, b, lang), "n": b["n"], "votes": b["votes"],
                             "cells": [{"now": b["now"][p], "d": b["now"][p] - b["before"][p]}
                                       for p in g["parties"]]
                             + [{"now": other_now, "d": other_now - other_before}]})
            dims.append({"key": dim, "title": _DIM_TITLES[dim][lang], "rows": rows,
                         "quintiles": dim != "size"})
        html = render_page(
            env, cfg, "society.html.j2", lang, canonical,
            {lg: i18n.page_url("society", lg) for lg in i18n.LANGS},
            ("Cómo vota cada tipo de municipio" if lang == "es" else "Com vota cada tipus de municipi"),
            ("Estimación de voto para el 29N y voto real de 2023 según el tamaño, la renta, la edad, "
             "la población extranjera y el paro de cada municipio." if lang == "es" else
             "Estimació de vot per al 29N i vot real del 2023 segons la mida, la renda, l'edat, "
             "la població estrangera i l'atur de cada municipi."),
            dims=dims, parties=[meta[p] for p in g["parties"]],
            month=sociallib.month_label(month, lang), year=year)
        write(DIST / canonical.strip("/") / "index.html", html)
    return len(g["dims"])


# Registre public de decisions de metode (pla de ruta, fase 1: metode public).
# Cada canvi que mou la mitjana o l'estimacio, amb la data. Fonts: els
# comentaris de config/sources.yaml i build.py, on cada regla porta la seva.
METHOD_LOG = [
    ("2026-10-03", "Més per Mallorca, Més per Menorca y Chunta Aragonesista se cuentan dentro de Sumar, como en 2023.",
     "Més per Mallorca, Més per Menorca i Chunta Aragonesista es compten dins de Sumar, com el 2023."),
    ("2026-10-03", "Aliança Catalana sale de la media: no se presenta a las generales.",
     "Aliança Catalana surt de la mitjana: no es presenta a les generals."),
    ("2026-10-05", "Veda electoral: del 24/11 a las 00:00 al 29/11 a las 20:00 no entra ninguna encuesta nueva.",
     "Veda electoral: del 24/11 a les 00:00 al 29/11 a les 20:00 no hi entra cap enquesta nova."),
    ("2026-10-07", "Podemos pasa a contarse dentro del Frente Amplio.",
     "Podemos passa a comptar-se dins del Frente Amplio."),
    ("2026-10-12", "La CUP sale de la estimación: no se presenta a las generales.",
     "La CUP surt de l'estimació: no es presenta a les generals."),
    ("2026-10-13", "Podemos vuelve a contarse por separado y no se presenta en Cataluña; UPN y PP van juntos en Navarra.",
     "Podemos torna a comptar-se per separat i no es presenta a Catalunya; UPN i PP van junts a Navarra."),
    ("2026-10-14", "Las encuestas del CIS cuentan 10 veces más (decisión editorial). UPL no se presenta en León.",
     "Les enquestes del CIS compten 10 vegades més (decisió editorial). UPL no es presenta a Lleó."),
    ("2026-10-06", "Listas únicas a la izquierda del PSOE en Canarias, Aragón y la Comunidad Valenciana: sus votos se suman.",
     "Llistes úniques a l'esquerra del PSOE a Canàries, l'Aragó i el País Valencià: els seus vots se sumen."),
    ("2026-10-16", "Aragón sale de la lista única: Podemos se presenta por separado.",
     "L'Aragó surt de la llista única: Podemos s'hi presenta per separat."),
    ("2026-10-17", "Recortes Cero va dentro del Frente Amplio en toda España.",
     "Recortes Cero va dins del Frente Amplio a tot Espanya."),
    ("2026-10-18", "Primero Canarias, escindido de Nueva Canarias, va con CC: la mitad del voto de NC en 2023 pasa a CC.",
     "Primero Canarias, escindit de Nueva Canarias, va amb CC: la meitat del vot de NC del 2023 passa a CC."),
    ("2026-10-19", "De cada instituto cuenta solo su encuesta más reciente.",
     "De cada institut només compta la seva enquesta més recent."),
    ("2026-10-21", "CHA-Frente Amplio no se presenta al Congreso por Teruel; su voto se asigna al PSOE.",
     "CHA-Frente Amplio no es presenta al Congrés per Terol; el seu vot s'assigna al PSOE."),
    ("2026-10-25", "Podemos entra en Ara Més-Front Ampli en Baleares.",
     "Podemos entra a Ara Més-Front Ampli a les Balears."),
    ("2026-11-21", "Previsión: el error de cada partido ya no es una hipótesis (0,59 × √%, medido con el error de las medias en la última elección de 26 países); se añade un error común por comunidad autónoma (0,50) y el provincial baja a 0,27, medidos con 2016-2023; los partidos regionales usan su % en su territorio; y cada simulación sortea la participación. Escenarios de participación: probabilidad de votar logística calibrada con el voto declarado de 2023, factores por comunidad e intervalo por remuestreo.",
     "Previsió: l'error de cada partit ja no és una hipòtesi (0,59 × √%, mesurat amb l'error de les mitjanes a l'última elecció de 26 països); s'hi afegeix un error comú per comunitat autònoma (0,50) i el provincial baixa a 0,27, mesurats amb 2016-2023; els partits regionals fan servir el seu % al seu territori; i cada simulació sorteja la participació. Escenaris de participació: probabilitat de votar logística calibrada amb el vot declarat del 2023, factors per comunitat i interval per remostreig."),
    ("2026-11-21", "Perfiles de votantes: para cada colectivo, sus temas, cuánto se mueve su voto y qué partidos compiten por él; para cada partido, los votantes a su alcance (segunda opción o indecisos que lo sienten cercano) y de qué hablan. Microdatos del CIS.",
     "Perfils de votants: per a cada col·lectiu, els seus temes, quant es mou el seu vot i quins partits s'hi disputen; per a cada partit, els votants a l'abast (segona opció o indecisos que el senten proper) i de què parlen. Microdades del CIS."),
    ("2026-11-23", "Simulador, escenarios de participación: comprobación en votos. Para cada participación, el voto válido y los votos de PP + Vox y de PSOE + Frente Amplio + Podemos como parte del censo, comparados con las generales de 1996 a 2023 (en parte del censo la derecha ha ido siempre del 28,0 % al 30,4 %; la izquierda estatal, del 24,3 % al 37,1 %). Avisa cuando un escenario no tiene precedentes; no cambia ninguna cifra.",
     "Simulador, escenaris de participació: comprovació en vots. Per a cada participació, el vot vàlid i els vots de PP + Vox i de PSOE + Frente Amplio + Podemos com a part del cens, comparats amb les generals de 1996 a 2023 (en part del cens la dreta ha anat sempre del 28,0 % al 30,4 %; l'esquerra estatal, del 24,3 % al 37,1 %). Avisa quan un escenari no té precedents; no canvia cap xifra."),
    ("2026-11-22", "Perfiles de votantes: una ficha por partido (los doce con muestra en el CIS y Coalición Canaria, solo con el modelo). Para cada grupo de edad, sexo, estudios, trabajo, clase, ingresos, estado civil y municipio, qué problemas citan los votantes que el partido tiene a su alcance y qué propuestas destacan en el grupo (3 puntos o más sobre la media), las propuestas puente (más apoyo entre los que puede ganar que entre los suyos) y los escaños que se juega. Los partidos de una comunidad se comparan con su comunidad. No hay grupos por ideología, religión ni origen (Reglamento (UE) 2024/900, artículo 18). Corregido: en los microdatos, Aliança Catalana se contaba como Adelante Andalucía, y Adelante Andalucía como «otros».",
     "Perfils de votants: una fitxa per partit (els dotze amb mostra al CIS i Coalición Canaria, només amb el model). Per a cada grup d'edat, sexe, estudis, feina, classe, ingressos, estat civil i municipi, quins problemes citen els votants que el partit té a l'abast i quines propostes hi destaquen (3 punts o més sobre la mitjana), les propostes pont (més suport entre els que pot guanyar que entre els seus) i els escons que es juga. Els partits d'una comunitat es comparen amb la seva comunitat. No hi ha grups per ideologia, religió ni origen (Reglament (UE) 2024/900, article 18). Corregit: a les microdades, Aliança Catalana es comptava com a Adelante Andalucía, i Adelante Andalucía com a «altres»."),
    ("2026-11-22", "Previsión (5.000 simulaciones): donde la proyección ya se ha acercado a una encuesta de la comunidad o de la circunscripción con peso w, el error del modelo que se simula allí se multiplica por la raíz de 1 − w: es lo que queda de incertidumbre al promediar dos estimaciones independientes. Los escenarios de participación del simulador y su noche electoral salen de la misma proyección.",
     "Previsió (5.000 simulacions): on la projecció ja s'ha acostat a una enquesta de la comunitat o de la circumscripció amb pes w, l'error del model que s'hi simula es multiplica per l'arrel d'1 − w: és la incertesa que queda en fer la mitjana de dues estimacions independents. Els escenaris de participació del simulador i la seva nit electoral surten de la mateixa projecció."),
    ("2026-11-22", "Encuestas de una comunidad o de una circunscripción, vía Wikipedia: el reparto entre los partidos que preguntan se acerca a su media. Comunidades: Canarias, Comunitat Valenciana, Aragón (CHA y Sumar, sumados en CHA-Frente Amplio Aragón), Cataluña, Galicia, Madrid, Murcia, Navarra y Euskadi. Circunscripciones: las cuatro gallegas, las tres vascas, las tres valencianas, Cádiz, Las Palmas y Santa Cruz de Tenerife, sobre la provincia ya acercada a su comunidad. Peso: el error del modelo (0,50 en una comunidad, 0,57 en una provincia) frente al error de las medias de encuestas (0,59), suponiendo que la mitad es común a todas las casas; se parte por dos cada 30 días desde la encuesta más reciente (hoy, del 14 % de Aragón al 47 % de Canarias). El total de esos partidos y el resto no cambian. Baleares y las demás comunidades: Wikipedia solo da escaños. León, fuera: la encuesta de SyM pone un 10,3 % en la columna de Podemos y no se sabe de qué lista es.",
     "Enquestes d'una comunitat o d'una circumscripció, via Wikipedia: el repartiment entre els partits que pregunten s'acosta a la seva mitjana. Comunitats: Canàries, País Valencià, Aragó (CHA i Sumar, sumats a CHA-Frente Amplio Aragón), Catalunya, Galícia, Madrid, Múrcia, Navarra i Euskadi. Circumscripcions: les quatre gallegues, les tres basques, les tres valencianes, Cadis, Las Palmas i Santa Cruz de Tenerife, sobre la província ja acostada a la seva comunitat. Pes: l'error del model (0,50 en una comunitat, 0,57 en una província) davant de l'error de les mitjanes d'enquestes (0,59), suposant que la meitat és comuna a totes les cases; es parteix per dos cada 30 dies des de l'enquesta més recent (avui, del 14 % de l'Aragó al 47 % de Canàries). El total d'aquests partits i la resta no canvien. Balears i les altres comunitats: Wikipedia només dona escons. Lleó, fora: l'enquesta de SyM posa un 10,3 % a la columna de Podemos i no se sap de quina llista és."),
    ("2026-11-22", "El último escaño, en votos: cuántos votos le faltan al primero que se queda fuera en cada provincia (los demás quietos), el reparto d'Hondt de cada provincia dibujado como una escala de barras y, para cada partido, su último diputado (cuántos votos puede perder antes de perderlo) y el siguiente (cuántos le faltan).",
     "L'últim escó, en vots: quants vots li falten al primer que es queda fora a cada província (els altres quiets), el repartiment d'Hondt de cada província dibuixat com una escala de barres i, per a cada partit, el seu últim diputat (quants vots pot perdre abans de perdre'l) i el següent (quants li'n falten)."),
    ("2026-11-21", "Simulador: escenarios de participación (votante probable del CIS e hipótesis clásica, contrastada con 2016-2023) y constructor de mayorías.",
     "Simulador: escenaris de participació (votant probable del CIS i hipòtesi clàssica, contrastada amb 2016-2023) i constructor de majories."),
    ("2026-11-21", "Guía «Cómo se vota al Congreso» con los números de 2023: votos por escaño en cada provincia, reparto d'Hondt paso a paso y dónde importa el umbral del 3 %.",
     "Guia «Com es vota al Congrés» amb els números del 2023: vots per escó a cada província, repartiment d'Hondt pas a pas i on importa el llindar del 3 %."),
    ("2026-11-21", "Simulador: el mismo voto con otro sistema (una sola circunscripción, Sainte-Laguë, proporcional puro) con el índice de desproporción de Gallagher, y ficha de cada provincia al tocar el mapa.",
     "Simulador: el mateix vot amb un altre sistema (una sola circumscripció, Sainte-Laguë, proporcional pur) amb l'índex de desproporció de Gallagher, i fitxa de cada província en tocar el mapa."),
    ("2026-11-21", "Para medios y docentes: tres gráficos para insertar (media, escaños y probabilidad de mayoría) con licencia CC BY-SA 4.0, y propuestas para usar la web en clase.",
     "Per a mitjans i docents: tres gràfics per inserir (mitjana, escons i probabilitat de majoria) amb llicència CC BY-SA 4.0, i propostes per fer servir la web a classe."),
    ("2026-11-21", "Simulador abierto también para 24 parlamentos de otros países, con el método y el umbral de cada ley (sin tocar nada, da los mismos escaños que la página de cada país).",
     "Simulador obert també per a 24 parlaments d'altres països, amb el mètode i el llindar de cada llei (sense tocar res, dona els mateixos escons que la pàgina de cada país)."),
    ("2026-11-21", "Simulador abierto también para nueve parlamentos autonómicos y con los resultados de 2016 y 2019 como punto de partida (reproducen exactamente los escaños reales). Corregido: el PSOE de Galicia, el País Vasco y Baleares no se emparejaba con su resultado anterior en el reparto por circunscripciones.",
     "Simulador obert també per a nou parlaments autonòmics i amb els resultats del 2016 i el 2019 com a punt de partida (reprodueixen exactament els escons reals). Corregit: el PSOE de Galícia, el País Basc i les Balears no s'aparellava amb el seu resultat anterior al repartiment per circumscripcions."),
    ("2026-11-21", "Quién gobierna el mundo: mapa de los jefes de gobierno por la posición política de su partido según Wikidata, con la parte de la población y del PIB mundial de cada familia.",
     "Qui governa el món: mapa dels caps de govern per la posició política del seu partit segons Wikidata, amb la part de la població i del PIB mundial de cada família."),
    ("2026-11-21", "Simulador electoral abierto: el usuario mueve el voto de cada partido en toda España o por comunidad y ve el reparto provincia por provincia, el mapa y una noche electoral. No es una previsión.",
     "Simulador electoral obert: l'usuari mou el vot de cada partit a tot Espanya o per comunitat i veu el repartiment província per província, el mapa i una nit electoral. No és una previsió."),
    ("2026-11-20", "Voto por colectivos con los microdatos del CIS (voto + simpatía, ponderado): sexo, edad, lugar de nacimiento, estudios, trabajo, profesión, clase, ingresos, religión, ideología, estado civil y tamaño del municipio. Grupos de menos de 100 entrevistas, fuera.",
     "Vot per col·lectius amb les microdades del CIS (vot + simpatia, ponderat): sexe, edat, lloc de naixement, estudis, feina, professió, classe, ingressos, religió, ideologia, estat civil i mida del municipi. Grups de menys de 100 entrevistes, fora."),
    ("2026-11-20", "Termómetro de conversación: cuánto se habla de cada partido en Bluesky y en Wikipedia, al lado de su voto en las encuestas. No entra en la media: en 2023 la atención no predijo el voto.",
     "Termòmetre de conversa: quant es parla de cada partit a Bluesky i a la Viquipèdia, al costat del seu vot a les enquestes. No entra a la mitjana: el 2023 l'atenció no va predir el vot."),
    ("2026-11-19", "Ocho elecciones más: Madrid, Cantabria, Baleares, Canarias, País Vasco y Melilla, y los ayuntamientos de Madrid y Sevilla. En autonómicas y municipales sin ninguna encuesta de los últimos 90 días, la media usa las de los últimos 12 meses y la página lo avisa.",
     "Vuit eleccions més: Madrid, Cantàbria, Balears, Canàries, País Basc i Melilla, i els ajuntaments de Madrid i Sevilla. A les autonòmiques i municipals sense cap enquesta dels últims 90 dies, la mitjana fa servir les dels últims 12 mesos i la pàgina ho avisa."),
    ("2026-11-15", "Previsión con probabilidades también en las autonómicas, las municipales y los parlamentos proporcionales de otros países.",
     "Previsió amb probabilitats també a les autonòmiques, les municipals i els parlaments proporcionals d'altres països."),
    ("2026-10-26", "Fuera las encuestas internas de los partidos.",
     "Fora les enquestes internes dels partits."),
    ("2026-11-01", "Fuera un sondeo interno de Vox publicado por The Objective.",
     "Fora un sondeig intern de Vox publicat per The Objective."),
    ("2026-11-10", "Previsión con probabilidades, datos abiertos, API y valoración de los institutos.",
     "Previsió amb probabilitats, dades obertes, API i valoració dels instituts."),
]


def method_page(env, cfg, stats):
    """La metodologia sencera. Es la pagina que fa creible tota la resta."""
    from .. import forecast as fc, pollsters
    from .rating import LABEL
    rating = pollsters.load() or {}
    backtest = [{"label": LABEL.get(e["id"], e["id"]), "id": e["id"], "n": e["backtest"]["n"],
                 "cutoff": e["backtest"]["cutoff"], "current": e["backtest"]["current"]["mae"],
                 "plain": e["backtest"]["plain"]["mae"], "pollster": e["mean_mae"]}
                for e in rating.get("elections", []) if e.get("backtest")]
    sig, sig_n, sig_c = fc.calibrated_sigma()
    model = {"sims": fc.N_SIMS, "sigma": round(sig, 2), "local": fc.LOCAL, "regional": fc.REGIONAL, "cap": fc.CAP,
             "sig_n": sig_n, "sig_c": sig_c, "turnout_sd": fc.TURNOUT_SD,
             "e30": round(sig * 30 ** 0.5, 1), "e7": round(sig * 7 ** 0.5, 1)}
    for lang in i18n.LANGS:
        log = [{"date": _fdate(d), "text": es if lang == "es" else ca} for d, es, ca in sorted(METHOD_LOG, key=lambda x: x[0])]
        canonical = i18n.page_url("method", lang)
        html = render_page(
            env, cfg, "method.html.j2", lang, canonical,
            {lg: i18n.page_url("method", lg) for lg in i18n.LANGS},
            ("Metodología · cómo se calcula la estimación" if lang == "es"
             else "Metodologia · com es calcula l'estimació"),
            ("Cómo se recogen las encuestas, cómo se pondera la media y cómo se "
             "proyecta sobre cada municipio. Con el contraste del modelo contra 2023."
             if lang == "es" else
             "Com es recullen les enquestes, com es pondera la mitjana i com es "
             "projecta sobre cada municipi. Amb el contrast del model contra el 2023."),
            stats=stats, baseline_year=BASELINE_YEAR, backtest=backtest, model=model, log=log,
            fmt=_fmt, fdate=_fdate)
        write(DIST / canonical.strip("/") / "index.html", html)


def map_page(env, cfg):
    for lang in i18n.LANGS:
        canonical = i18n.page_url("map", lang)
        html = render_page(
            env, cfg, "map.html.j2", lang, canonical,
            {lg: i18n.page_url("map", lg) for lg in i18n.LANGS},
            ("Mapa electoral interactivo de España: 8.131 municipios"
             if lang == "es" else
             "Mapa electoral interactiu d'Espanya: 8.131 municipis"),
            ("Mapa interactivo con el resultado real de 2023 y la estimación de voto "
             "de hoy en cada municipio, provincia y comunidad de España. Pasa el "
             "cursor para ver el reparto completo."
             if lang == "es" else
             "Mapa interactiu amb el resultat real del 2023 i l'estimació de vot "
             "d'avui a cada municipi, província i comunitat d'Espanya. Passa-hi el "
             "cursor per veure el repartiment sencer."),
            map_heading=("Mapa electoral de España" if lang == "es"
                         else "Mapa electoral d'Espanya"))
        write(DIST / canonical.strip("/") / "index.html", html)


def home_page(env, cfg, data, urls, highlights):
    # El simulador de coalicions a escala estatal: les 52 circumscripcions
    # alhora. La portada ES la pagina d'Espanya; no cal inventar-ne una altra.
    sim = simulator_for(data, "national", "ES")
    sim_json = (json.dumps(sim, ensure_ascii=False).replace("<", "\u003c")
                if sim else None)
    # Avis de veda electoral o de sondeigs a peu d'urna (generals, veda.py).
    general = next((e for e in load_sources()["elections"] if e["id"] == "es-general"), None)
    notice = {"veda": "notice_veda", "peu_urna_obert": "notice_exit_polls"}.get(veda.status(general))
    # Les autonomiques i municipals amb pagina propia (`parent: spain`, 06/11/2026).
    elections = abroad_elections()
    subs = []
    from .. import db
    leaders = leaders_view(db.connect(), "spain")
    # El Congres sencer per a l'hemicicle (cambra.js): tots els partits amb escons,
    # no nomes els deu de la taula.
    congress = [{**parties.meta(p, "ES", ELECTION), "code": p, "seats": n}
                for p, n in db.connect().execute(
                    """SELECT party, seats FROM seat_projection
                       WHERE election_id = ? AND level = 'chamber' AND seats > 0
                       ORDER BY seats DESC""", (ELECTION,))]
    # Qui seu a cada escó (15/11/2026): un JSON per idioma que cambra.js carrega
    # per obrir la fitxa de cada diputat, i la mateixa llista en HTML.
    from . import people as peoplelib
    try:
        people = peoplelib.congress(data, urls)
        people_url = peoplelib.write(DIST, people)
    except Exception as exc:                          # noqa: BLE001
        print(f"      avis: fitxes dels diputats no generades ({type(exc).__name__}: {exc})")
        people, people_url = {}, {}
    # Previsio amb probabilitats (pla de ruta, 10/11/2026): 5.000 simulacions.
    # Llavor fixa: la mateixa base dona sempre les mateixes xifres.
    from .. import forecast as forecastlib
    try:
        fc = forecastlib.simulate(db.connect(), ELECTION, n=forecastlib.N_SIMS, seed=2911)
    except Exception as exc:                          # noqa: BLE001
        print(f"      avis: previsio no calculada ({exc})")
        fc = None
    if fc:
        meta = {r["code"]: r for r in congress}
        for r in fc["parties"]:
            m = meta.get(r["code"]) or parties.meta(r["code"], "ES", ELECTION)
            r.update({"name": m["name"], "color": m["color"]})
        for b in fc.get("by_turnout") or []:
            for r in b["parties"]:
                m = meta.get(r["code"]) or parties.meta(r["code"], "ES", ELECTION)
                r.update({"name": m["name"], "color": m["color"]})
        peak = max(c for _, c in fc["right_hist"]) or 1
        fc["bars"] = [{"x": x, "h": c / peak, "maj": x >= fc["majority"]} for x, c in fc["right_hist"]]
    if cfg.get("_abroad"):
        conn = db.connect()
        for eid in cfg["_abroad"]:
            if elections[eid].get("parent") == "spain":
                d = abroad_data(conn, eid)
                if d:
                    subs.append(sub_card(d))
        subs.sort(key=lambda c: parties.slug(c["names"]["ca"]))
    try:
        from . import seatgrid
        sg = seatgrid.build(sim, lambda p: {**parties.meta(p, "ES", ELECTION),
                                            **({"name": "Sumar"} if p == "SUMAR" else {})},
                            lambda p: parties.position(p, "ES") or 999)
    except Exception as exc:                              # noqa: BLE001
        print(f"     avis: repartiment d'un cop d'ull no generat ({type(exc).__name__}: {exc})")
        sg = None
    try:
        from . import trend as trendlib
        trend = trendlib.build(db.connect(), ELECTION, highlights or [])
        if trend:
            trend["data"] = trendlib.interactive(db.connect(), ELECTION, highlights or [], since="2023-07-23",
                                                 election_day=(general or {}).get("election_date"),
                                                 marks=[("2023-07-23", "23J")])
    except Exception as exc:                              # noqa: BLE001
        print(f"     avis: grafic d'evolucio no generat ({type(exc).__name__}: {exc})")
        trend = None
    for lang in i18n.LANGS:
        canonical = i18n.page_url("spain", lang)
        html = render_page(
            env, cfg, "home.html.j2", lang, canonical,
            {lg: i18n.page_url("spain", lg) for lg in i18n.LANGS},
            f"{cfg['site']['name']} · {i18n.t('site_tagline', lang)}",
            i18n.t("site_description", lang),
            highlights=highlights, simulator=sim_json, baseline_year=BASELINE_YEAR, trend=trend, seatgrid=sg,
            notice=notice, subs=subs, leaders=leaders, congress=congress, forecast=fc,
            people_url=people_url.get(lang, ""),
            people=[{**c, "members": (people.get(lang) or {}).get("parties", {}).get(c["code"], [])}
                    for c in congress] if people else [],
            fmt=_fmt, fdate=_fdate, regions=[
                {"name": data["names"]["region"].get(c, c), "url": urls[("region", c)][lang]}
                for c in sorted(data["names"]["region"],
                                key=lambda c: data["names"]["region"].get(c, ""))
                if ("region", c) in urls])
        write(DIST / canonical.strip("/") / "index.html", html)
        # L'antiga adreca del mapamundi (/ca/enquestes/) envia a la nova portada.
        old = "encuestas" if lang == "es" else "enquestes"
        write(DIST / lang / old / "index.html", _redirect(f"/{lang}/", cfg))

    # L'arrel envia a l'idioma per defecte. Es una redireccio de client perque un
    # allotjament estatic no pot fer un 301 de servidor. L'adreca es RELATIVA:
    # GitHub Pages pot servir el lloc des d'un subdirectori i una barra inicial
    # el trauria fora del projecte.
    default = cfg["site"]["default_language"]
    base = cfg["site"]["base_url"].rstrip("/")
    write(DIST / "index.html",
          '<!doctype html><html lang="es"><head><meta charset="utf-8">'
          f'<meta http-equiv="refresh" content="0; url=./{default}/">'
          f'<link rel="canonical" href="{base}/{default}/">'
          '<title>Polit Bureau</title>'
          '<meta name="robots" content="noindex,follow"></head>'
          f'<body><p><a href="./{default}/">Polit Bureau</a></p></body></html>')
    return fc


def _redirect(target, cfg):
    """Pagina que envia a una altra adreca (un allotjament estatic no fa 301).
    L'adreca relativa a l'arrel: GitHub Pages pot servir des d'un subdirectori."""
    base = cfg["site"]["base_url"].rstrip("/")
    depth = 2
    rel = "../" * depth + target.lstrip("/")
    return ('<!doctype html><html><head><meta charset="utf-8">'
            f'<meta http-equiv="refresh" content="0; url={rel}">'
            f'<link rel="canonical" href="{base}{target}">'
            '<title>Polit Bureau</title>'
            '<meta name="robots" content="noindex,follow"></head>'
            f'<body><p><a href="{rel}">Polit Bureau</a></p></body></html>')


def sitemaps(cfg, urls):
    """Un sitemap per idioma mes un index. El limit son 50.000 URL per fitxer i
    aqui n'hi ha unes vuit mil per idioma, aixi que cap no es queda a prop."""
    base = cfg["site"]["base_url"].rstrip("/")
    today = dt.date.today().isoformat()
    files = []
    for lang in i18n.LANGS:
        entries = [f"/{lang}/"] + [i18n.page_url(k, lang)
                                   for k in ("spain", "countries", "map", "participation", "senate", "society", "opendata", "pollsters", "history", "conversation", "groups", "profiles", "sandbox", "governs", "media", "guide", "strongholds", "method", "legal", "privacy", "cookies")]
        # Pagines que nomes existeixen quan hi ha dades (l'encert del 29N).
        entries += [i18n.page_url(k, lang) for k in cfg.get("_extra_pages", [])]
        # Pagines que un modul escriu amb la seva adreca (fitxes de partit dels perfils).
        entries += (cfg.get("_extra_urls") or {}).get(lang, [])
        if cfg.get("_abroad"):
            elections = abroad_elections()
            entries += [abroad_url(elections[e], lang) for e in cfg["_abroad"]]
        entries += sorted((cfg.get("_abroad_units") or {}).get(lang, []))
        entries += sorted(u[lang] for u in urls.values() if lang in u)
        body = "\n".join(
            f"  <url><loc>{base}{u}</loc><lastmod>{today}</lastmod>"
            f"<changefreq>daily</changefreq></url>" for u in entries)
        name = f"sitemap-{lang}.xml"
        write(DIST / name,
              '<?xml version="1.0" encoding="UTF-8"?>\n'
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
              f"{body}\n</urlset>\n")
        files.append((name, len(entries)))

    index = "\n".join(f"  <sitemap><loc>{base}/{n}</loc><lastmod>{today}</lastmod></sitemap>"
                      for n, _ in files)
    write(DIST / "sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          f"{index}\n</sitemapindex>\n")
    write(DIST / "robots.txt",
          "User-agent: *\nAllow: /\n\n"
          f"Sitemap: {base}/sitemap.xml\n")
    # ads.txt: declara qui pot vendre anuncis en aquest domini. Google el fa
    # servir per verificar el lloc; es un fitxer de text i no carrega res al
    # navegador de ningu.
    client = (cfg.get("publicidad") or {}).get("adsense_client") or ""
    if client:
        write(DIST / "ads.txt",
              f"google.com, {client.removeprefix('ca-')}, DIRECT, f08c47fec0942fa0\n")
    return files


def assets(data, urls):
    """Copia el CSS i el JS i escriu les dades que necessita el mapa interactiu."""
    out = DIST / "assets"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("site.css", "site.js", "cambra.js", "map.js", "map.css", "coalition.js", "seccions.js", "sandbox.js", "perfils.js", "charts.js", "lastseat.js",
                 "world.js", "world.json", "relief.jpg", "flags.webp", "favicon.svg"):
        src = WEB / name
        if src.exists():
            shutil.copy2(src, out / name)

    # GitHub Pages passa el lloc per Jekyll si no hi ha aquest fitxer, i Jekyll
    # s'empassa qualsevol carpeta que comenci amb guio baix.
    (DIST / ".nojekyll").write_text("", encoding="utf-8")

    src_geo = geo.GEO_DIR / "es.json"
    if src_geo.exists():
        shutil.copy2(src_geo, out / "es.json")
        gz = src_geo.with_suffix(".json.gz")
        if gz.exists():
            shutil.copy2(gz, out / "es.json.gz")

    # Index del cercador: nom, adreca i nivell de cada territori. Un sol fitxer
    # per a tot el lloc, que el navegador es guarda a la memoria cau.
    index = []
    for (level, code), langs in urls.items():
        name = data["names"][level].get(code)
        if not name:
            continue
        index.append([name, parties.slug(name), level, code,
                      langs.get("es", ""), langs.get("ca", "")])
    index.sort(key=lambda r: (r[2] != "region", r[2] != "province", r[0]))
    body = json.dumps(index, ensure_ascii=False, separators=(",", ":"))
    (DIST / "assets" / "search.json").write_text(body, encoding="utf-8")
    (DIST / "assets" / "search.json.gz").write_bytes(gzip.compress(body.encode("utf-8"), 6))
    return len(index)


# Enquestes d'altres paisos: Franca i Italia (03/11/2026) i, el mateix dia, la
# resta d'Europa. Nomes la mitjana estatal i les enquestes que hi entren: cap
# mapa ni fitxa de municipi. Les eleccions que es publiquen son les que porten
# `pub` a sources.yaml (adreca i nom del pais en cada idioma).

def abroad_elections():
    """{id: config} de les eleccions estrangeres amb pagina, en l'ordre de sources.yaml.
    Les cambres per als escons orientatius venen de config/chambers.yaml."""
    try:
        chambers = yaml.safe_load((ROOT / "config" / "chambers.yaml").read_text(encoding="utf-8"))
    except OSError:
        chambers = {}
    out = {}
    for e in load_sources()["elections"]:
        if e.get("pub"):
            chamber = e.get("chamber") or (chambers or {}).get(e["id"])
            if chamber and chamber.get("ine"):
                # Ajuntaments (19/11/2026): els regidors surten del padro de l'INE i
                # l'escala de la LOREG (municipals.py), no d'un numero escrit a ma.
                from .. import municipals
                s27 = ((municipals.load().get("munis") or {}).get(chamber["ine"]) or {}).get("s27")
                if s27:
                    chamber = {**chamber, "seats": s27}
            out[e["id"]] = {**e, "chamber": chamber} if chamber else e
    return out


def abroad_url(election, lang):
    pub = election["pub"]
    return f"/es/encuestas-{pub['es']}/" if lang == "es" else f"/ca/enquestes-{pub['ca']}/"


def world_url(lang):
    """La porta d'entrada de tot el lloc: el mapamundi (portada des del 05/11/2026)."""
    return f"/{lang}/"


def _spain(conn, lang):
    """Espanya al mapamundi: la mateixa estimacio de la portada, amb enllac al mapa."""
    rows = conn.execute(
        """SELECT party, share FROM aggregate WHERE election_id = ? AND scope_code = ''
           ORDER BY share DESC LIMIT 2""", (ELECTION,)).fetchall()
    if not rows:
        return None
    n = conn.execute("""SELECT COUNT(DISTINCT pollster), MAX(fieldwork_end) FROM poll
                        WHERE election_id = ?""", (ELECTION,)).fetchone()
    first, second = ({**parties.meta(r["party"], "ES", ELECTION), "share": r["share"],
                      "person": None} for r in rows)
    return {"code": "ES", "name": "España" if lang == "es" else "Espanya",
            "url": i18n.page_url("spain", lang), "presidential": False,
            "first": first, "second": second, "n": None, "last": n[1], "spain": True}


def _candidates(conn, election_id):
    """{linia: candidat}: el nom mes preguntat de cada linia als ultims 90 dies
    (el mateix criteri que l'eina local). "A + B" son diversos noms sumats."""
    best = {}
    for r in conn.execute(
            """SELECT r.party, r.label, COUNT(*) n
               FROM poll p JOIN poll_result r ON r.poll_id = p.id
               WHERE p.election_id = ? AND r.label IS NOT NULL AND r.label != ''
                 AND p.fieldwork_end >= date('now', '-90 days')
               GROUP BY r.party, r.label ORDER BY n DESC""", (election_id,)):
        if r["party"] not in best and " + " not in r["label"]:
            best[r["party"]] = r["label"]
    return best


def _short(label):
    """"Social Democrats (Denmark)" -> "Social Democrats": la desambiguacio de
    Wikipedia no fa falta dins de la pagina del mateix pais."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", label or "").strip()


def _average(conn, eid, scope_code, country, names, persons, colors, chamber=None):
    """Mitjana i enquestes en joc d'un ambit (estatal: scope_code "", o una regio).
    None si no hi ha cap enquesta dels ultims 90 dies."""
    from ..build import load_polls
    rows = [r for r in conn.execute(
        """SELECT party, share, lo, hi, n_polls FROM aggregate
           WHERE election_id = ? AND COALESCE(scope_code, '') = ?
           ORDER BY share DESC""", (eid, scope_code))
        if r["share"] is not None and r["share"] >= 0.1
        and not (r["party"].startswith("?") and country in ("FR", "IT"))]
    if not rows:
        return None
    today = dt.date.today()
    every = [p for p in load_polls(conn, eid, scope_code or None)
             if p["fieldwork_end"] and not (p["sample_size"] and p["sample_size"] < 300)]
    used = [p for p in every if (today - dt.date.fromisoformat(p["fieldwork_end"])).days <= 90]
    # Autonomiques i municipals sense cap enquesta dels ultims 90 dies: les dels
    # ultims 12 mesos, com fa build.aggregate_all (la pagina avisa).
    stale = False
    if not used and (abroad_elections().get(eid) or {}).get("group") == "sub":
        from ..model.aggregate import SUB_MAX_AGE_DAYS
        used = [p for p in every
                if (today - dt.date.fromisoformat(p["fieldwork_end"])).days <= SUB_MAX_AGE_DAYS]
        stale = bool(used)
    if not used:
        return None
    # Escons d'Italia: proporcional estatal amb la mitjana, calculat aqui mateix.
    # Aixi la publicacio no ha de fer `build --country IT`, que baixaria cada
    # hora el resultat del 2022 municipi a municipi per a un mapa que la web no te.
    seats, margins, extra, fptp = {}, None, {}, None
    extra_districts, project = None, None
    if chamber and chamber.get("method") == "fptp" and not scope_code:
        # Majoritari uninominal (Regne Unit): circumscripcio per circumscripcio,
        # amb les mitjanes d'Escocia, Gal.les i Londres on n'hi ha (systems.py).
        from .. import systems
        reg = {sc: dict(conn.execute(
            "SELECT party, share FROM aggregate WHERE election_id = ? AND scope_code = ?",
            (eid, sc)).fetchall()) for sc in ("SCT", "WLS", "LDN")}
        got = systems.fptp_gb({r["party"]: r["share"] for r in rows}, reg)
        if got:
            seats, extra, fptp = got
    elif chamber and chamber.get("method") in ("proportional", "dhondt", "sainte_lague", "hare",
                                               "droop"):
        from ..model import seats as seatlib
        shares = {r["party"]: r["share"] for r in rows if r["party"] != "OTHER"}
        method = "dhondt" if chamber["method"] == "proportional" else chamber["method"]
        # Autonomiques amb diverses circumscripcions: provincia a provincia amb el
        # resultat real de l'eleccio anterior (regional.py, 19/11/2026).
        from .. import regional
        project = regional.projector(eid, chamber) if not scope_code else None
        if project:
            detail = {}
            seats = {p: n for p, n in project(shares, detail).items() if n}
            margins = None
            extra_districts = {"n": project.n_districts, "base": project.base,
                               "source": project.source, "detail": detail}
        else:
            seats = {p: n for p, n in seatlib.apportion(
                shares, chamber["seats"], method, chamber.get("threshold", 0.03),
                chamber.get("first_divisor", 1.0), chamber.get("bonus")).items() if n}
            margins = seatlib.margins(shares, chamber["seats"], method, chamber.get("threshold", 0.03),
                                      chamber.get("first_divisor", 1.0), chamber.get("bonus"))
    avg = []
    for r in rows:
        meta = parties.meta(r["party"], country, eid)
        if r["party"].startswith("?"):
            # Partit fora del cataleg: el nom de la capcalera i el color de Wikipedia.
            # Llevat que sources.yaml en fixi el nom (`display`): "SF N" -> "Sinn Féin".
            fixed = parties._display().get(eid, {}).get(r["party"])
            meta = {**meta, "name": fixed or _short(names.get(r["party"])) or meta["name"],
                    "color": colors.get(r["party"], meta["color"])}
        avg.append({**meta, "person": persons.get(r["party"]), "share": r["share"],
                    "lo": r["lo"], "hi": r["hi"], "n": r["n_polls"],
                    "seats": seats.get(r["party"]),
                    "ideo": parties.ideology(r["party"], country)})
    if margins and seats:
        by = {a["code"]: a for a in avg}

        def _p(code):
            a = by.get(code) or {}
            return {"name": a.get("name", code), "color": a.get("color", "#999")}
        margins = {
            "won": [{**_p(p), "n": n, "divisor": d, "quotient": q} for n, p, d, q in margins["won"]],
            "next": [{**_p(p), "divisor": d, "quotient": q, "need": need}
                     for p, d, q, need in margins["next"]],
            "cutoff": margins["cutoff"],
            "out": [{**_p(p), "share": s, "short": sh} for p, s, sh in margins["out"]]}
    else:
        margins = None
    order = [a["code"] for a in avg if a["code"] != "OTHER"][:6]
    used.sort(key=lambda p: p["fieldwork_end"], reverse=True)
    polls = [{"pollster": p["pollster"], "end": p["fieldwork_end"],
              "sample": p["sample_size"],
              "values": [(p["results"].get(c) or (None,))[0] for c in order]}
             for p in used]
    # Previsio amb probabilitats (pla de ruta, 15/11/2026): el mateix error que
    # a les generals, sobre el repartiment d'aquesta cambra. Llavor fixa.
    fc = None
    if seats and not fptp and not scope_code:
        from .. import forecast as forecastlib
        try:
            fc = forecastlib.simulate_chamber(
                {r["party"]: r["share"] for r in rows}, chamber, n_polls=len(used), seed=2911,
                project=project)
        except Exception:                              # noqa: BLE001
            fc = None
        if fc:
            by_code = {a["code"]: a for a in avg}
            for r in fc["parties"]:
                a = by_code.get(r["code"]) or {}
                r.update({"name": a.get("person") or a.get("name", r["code"]),
                          "color": a.get("color", "#999")})
    # Escons de partits que no surten a les enquestes (Irlanda del Nord,
    # independents, el Speaker): van a la cambra i a la taula, sense %.
    seat_extra = [{"code": c, "name": n, "color": col, "seats": seats[c], "person": None}
                  for c, (n, col) in sorted(extra.items(), key=lambda x: -seats[x[0]])]
    if extra_districts:
        # Columnes de la taula per circumscripcio: tots els que hi treuen algun
        # esco (ASG a La Gomera, AHI a El Hierro), no nomes els sis primers.
        extra_districts["cols"] = [a for a in avg if any(
            a["code"] in got for got in extra_districts["detail"].values())]
    return {"avg": avg, "stale": stale,
            "order": [next(a for a in avg if a["code"] == c) for c in order],
            "seat_extra": seat_extra, "seatrows": avg + seat_extra, "fptp": fptp,
            "forecast": fc, "bydist": extra_districts,
            "polls": polls, "seats": bool(seats),
            "seat_total": sum(seats.values()) if seats else 0,
            "chamber": chamber if seats else None, "margins": margins,
            "majority": ((chamber.get("total") or chamber["seats"]) // 2 + 1) if seats else 0}


def abroad_regions():
    """{eleccio: [regio, ...]} de `regions:` a sources.yaml."""
    return load_sources().get("regions") or {}


def _departments(election, national, polled=None):
    """Intencio de vot per departament (Franca): la mitjana d'avui projectada
    sobre el resultat de l'eleccio de base amb el swing proporcional, el mateix
    metode que els municipis espanyols. None si l'eleccio no en te."""
    cfg = election.get("departments")
    if not cfg:
        return None
    from ..model import seats as seatlib
    try:
        geo = json.loads((WEB / cfg["geo"]).read_text(encoding="utf-8"))
        base = json.loads((WEB / cfg["base"]).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    now = {a["code"]: a["share"] for a in national["avg"]} if national else {}
    meta = {a["code"]: a for a in national["avg"]} if national else {}
    # Belgica: sense mitjana estatal. Cada provincia es projecta amb la mitjana de
    # la seva regio i el resultat regional de l'eleccio de base.
    by_region = base.get("by_region") or {}
    family = parties.families().get(election["country"]) or {}
    deps = []
    polled = polled or {}
    for code, shape in sorted(geo["dep"].items()):
        if code in polled:
            # Aquest territori te enquestes propies (Escocia, Gal.les, Baviera...):
            # manen sobre l'estimacio, com a la seccio "Per regions".
            avg = [a for a in polled[code]["avg"] if a["code"] != "OTHER"]
            rows = [{"name": a["person"] or a["name"], "color": a["color"], "share": a["share"]}
                    for a in avg]
            alpha = round(min(1.0, max(0.3, (rows[0]["share"] - 15) / 35)), 2)
            deps.append({"code": code, "name": shape["n"], "d": shape["d"], "rows": rows[:3],
                         "full": [{**r, "base": None} for r in rows],
                         "color": rows[0]["color"], "alpha": alpha, "polled": True})
            continue
        b = base["dep"].get(code)
        if not b:
            # Territori sense resultat a la base (la Vall d'Aosta te un sistema
            # propi): es dibuixa en gris perque el mapa no tingui un forat.
            deps.append({"code": code, "name": shape["n"], "d": shape["d"], "rows": [],
                         "color": None, "alpha": 1})
            continue
        u_now, u_meta, u_before = now, meta, base["national"]
        reg = by_region.get(code)
        if reg:
            if reg not in polled or reg not in (base.get("regions") or {}):
                continue
            u_now = {a["code"]: a["share"] for a in polled[reg]["avg"]}
            u_meta = {a["code"]: a for a in polled[reg]["avg"]}
            u_before = base["regions"][reg]
        if not u_before:
            continue
        proj = seatlib.proportional_swing(b, u_now, u_before, family=family)
        # Els partits de la base que avui ja no surten a les enquestes (fusionats,
        # rebatejats o desapareguts) es treuen: si no, es quedarien congelats al seu
        # resultat i el seu vot es comptaria dues vegades amb el del seu successor.
        proj = {p: s for p, s in proj.items() if p in u_now or p == "OTHER"}
        tot = sum(proj.values()) or 1
        proj = {p: s * 100 / tot for p, s in proj.items()}
        ranked = sorted(((p, s) for p, s in proj.items() if p in u_meta and p != "OTHER"),
                        key=lambda x: -x[1])
        if not ranked:
            continue
        # La fitxa del territori: tots els partits, amb el que va treure cadascun a
        # l'eleccio de base. Si un partit no s'hi presentava, el del seu espai
        # (`via`): Han Dong-hoon porta el vot de Kim Moon-soo del 2025.
        full = []
        for p, s in ranked:
            before, via = b.get(p), False
            if before is None and family.get(p) in b:
                before, via = b[family[p]], True
            full.append({"name": u_meta[p]["person"] or u_meta[p]["name"],
                         "color": u_meta[p]["color"], "share": s, "base": before, "via": via})
        rows = full[:3]
        # Intensitat segons el % del primer: amb el 25 % es veu clar, amb el 50 % ple.
        alpha = round(min(1.0, max(0.3, (rows[0]["share"] - 15) / 35)), 2)
        deps.append({"code": code, "name": shape["n"], "d": shape["d"], "rows": rows,
                     "full": full, "color": rows[0]["color"], "alpha": alpha})
    leaders, taken = {}, set()
    for d in deps:
        if d["rows"]:
            leaders.setdefault(d["rows"][0]["name"], [d["rows"][0]["color"], 0])[1] += 1
            # Adreca de la fitxa, unica dins del pais.
            slug = parties.slug(d["name"]) or d["code"].lower()
            if slug in taken:
                slug = f"{slug}-{d['code'].lower()}"
            taken.add(slug)
            d["slug"] = slug
    return {"w": geo["w"], "h": geo["h"], "deps": deps, "regional": bool(by_region),
            "insets": geo.get("insets") or [],
            "units": {"es": cfg.get("units_es", "departamentos"), "ca": cfg.get("units_ca", "departaments")},
            "base_label": {"es": cfg.get("base_es", "la primera vuelta de 2022"),
                           "ca": cfg.get("base_ca", "la primera volta del 2022")},
            "leaders": sorted(([n, c, k] for n, (c, k) in leaders.items()), key=lambda x: -x[2])}


# Valoracio dels lideres (08/11/2026): config/leaders.yaml + ingest/leaders.py.
_LEADER_TITLES = {
    "approval": {"ca": "Aprovació", "es": "Aprobación"},
    "share": {"ca": "Preferit per governar", "es": "Preferido para gobernar"},
    "score": {"ca": "Nota dels líders (de 0 a 10)", "es": "Valoración de los líderes (de 0 a 10)"},
}


def leaders_view(conn, key):
    """Blocs de valoracio dels lideres de la pagina `key` (id d'eleccio o "spain")."""
    from ..ingest import leaders as ld
    try:
        cfg = ld.load_config()
    except FileNotFoundError:
        return []
    out = []
    for entry in cfg.get("leaders") or []:
        if entry.get("election") != key:
            continue
        es_names = ld.names_es(entry)
        for block in entry["blocks"]:
            rows = ld.averages(conn, entry["id"], block["key"])
            if block["metric"] == "approval":
                rows = [r for r in rows if r["net"] is not None]
            else:
                rows = [r for r in rows if r["value"] is not None]
                rows.sort(key=lambda r: -r["value"])
            if not rows:
                continue
            ld.with_trend(conn, entry["id"], block["key"], rows)
            src = conn.execute("SELECT source_url FROM leader_poll WHERE entry = ? AND block = ? "
                               "ORDER BY fieldwork_end DESC LIMIT 1",
                               (entry["id"], block["key"])).fetchone()
            for r in rows:
                r["name"] = {"ca": r["subject"], "es": es_names.get(r["subject"], r["subject"])}
            out.append({"key": block["key"], "metric": block["metric"],
                        "title": block.get("title") or _LEADER_TITLES[block["metric"]],
                        "rows": rows, "last": max(r["last"] for r in rows),
                        "head": entry.get("head"), "country": entry["country"],
                        "pollsters": sorted({p for r in rows for p in r["pollsters"]}),
                        "source": src[0] if src else None})
    return out


def abroad_data(conn, eid):
    """Mitjana estatal, regions, escons (si n'hi ha) i enquestes en joc d'una
    eleccio. None si no hi ha res a mostrar: llavors la pagina no s'escriu ni
    s'enllaca."""
    election = abroad_elections()[eid]
    # Un cop passat el dia de la votacio (`date`), les enquestes ja no parlen de
    # cap eleccio futura: la pagina no es publica fins que hi hagi la propera.
    if election.get("date") and dt.date.today() > dt.date.fromisoformat(str(election["date"])):
        return None
    country = election["country"]
    names = _candidates(conn, eid)
    persons = dict(names) if election.get("display") == "candidates" else {}
    persons.pop("OTHER", None)
    try:
        colors = dict(conn.execute("SELECT party, color FROM party_style WHERE election_id = ?",
                                   (eid,)).fetchall())
    except Exception:                     # base antiga sense la taula
        colors = {}
    national = (_average(conn, eid, "", country, names, persons, colors, election.get("chamber"))
                if election.get("national", True) else None)
    regions = []
    for reg in abroad_regions().get(eid, []):
        got = _average(conn, eid, str(reg["key"]), country, names, persons, colors)
        if got:
            regions.append({**got, "key": str(reg["key"]), "unit": reg.get("unit"),
                            "name": {"es": reg["name_es"], "ca": reg["name_ca"]},
                            "map": f"{election['pub'].get('map') or country}-{reg['key']}"})
    if not national and not regions:
        return None
    pub = election["pub"]
    base = national or {"avg": [], "order": [], "polls": [], "seats": False, "seat_total": 0}
    regional = (election.get("departments") or {}).get("regional")
    depmap = (_departments(election, national,
                           {str(r.get("unit") or r["key"]): r for r in regions})
              if national or (regional and regions) else None)
    for g in (depmap or {}).get("deps", []):
        if g.get("slug"):
            g["url"] = {lg: abroad_url(election, lg) + g["slug"] + "/" for lg in i18n.LANGS}
    if depmap:
        # On es mes fort cada partit: els tres territoris on l'estimacio li dona
        # mes vot. L'equivalent dels feus d'Espanya, per als sis primers partits.
        best = {}
        for g in depmap["deps"]:
            for r in g.get("full") or []:
                best.setdefault(r["name"], {"color": r["color"], "top": []})["top"].append(
                    {"name": g["name"], "url": g.get("url"), "share": r["share"]})
        order = [a["person"] or a["name"] for a in (national or {}).get("avg", [])
                 if a["code"] != "OTHER"] or list(best)
        depmap["strongholds"] = [
            {"name": n, "color": best[n]["color"],
             "top": sorted(best[n]["top"], key=lambda x: -x["share"])[:3]}
            for n in order[:6] if n in best and len(best[n]["top"]) >= 3]
    return {**base, "national": bool(national), "regions": regions, "depmap": depmap,
            "iso": country,
            "total_polls": conn.execute("SELECT COUNT(*) FROM poll WHERE election_id = ?",
                                        (eid,)).fetchone()[0],
            "presidential": election.get("display") == "candidates",
            "general": election.get("kind") == "general",
            # Eleccions regionals i municipals (`group: sub`, 06/11/2026): la pagina
            # penja del pais (`parent`) i porta el tipus d'eleccio al titol.
            "sub": election.get("group") == "sub",
            "parent": election.get("parent"),
            "kind": sub_kind(election),
            "name": {"es": pub["name_es"], "ca": pub["name_ca"]},
            # "del Regne Unit", "dels Països Baixos": quan el nom porta article.
            "of": {"es": pub.get("of_es") or f"de {pub['name_es']}",
                   "ca": pub.get("of_ca") or de(pub["name_ca"])},
            "urls": {lg: abroad_url(election, lg) for lg in i18n.LANGS},
            "leaders": leaders_view(conn, eid),
            # Com es vota on els escons no es poden estimar (chambers.yaml, method: none).
            "sysnote": ((election.get("chamber") or {})
                        if (election.get("chamber") or {}).get("method") == "none" else None),
            # Regla de cada pais per guanyar a la primera volta (systems.py).
            "pres": (_pres(country, national) if election.get("display") == "candidates"
                     and election.get("group") != "sub" else None),
            # Com va encertar la mitjana a l'ultima eleccio (pla de ruta, 14/11/2026).
            "lasterror": (None if election.get("group") == "sub"
                          else _lasterror(eid, country, national, names, colors)),
            # Parlament actual i cap de govern (09/11/2026, results.py).
            "parliament": (None if election.get("group") == "sub"
                           else _parliament(conn, country)),
            "wiki": (f"https://{election.get('lang', 'en')}.wikipedia.org/wiki/"
                     + election["page"].replace(" ", "_"))}


def _pres(country, national):
    from .. import systems
    return systems.presidential(country, (national or {}).get("avg") or [])


def _lasterror(eid, country, national, names, colors):
    """Error de la mitjana a l'ultima eleccio (config/last_error.json, que fa
    `politbureau error-anterior`). None si no s'ha pogut calcular."""
    from .. import lasterror
    r = (lasterror.load().get("elections") or {}).get(eid)
    if not r or r.get("status") != "ok":
        return None
    by = {a["code"]: a for a in (national or {}).get("avg", [])}
    rows = []
    for x in r["rows"]:
        code = x["party"]
        a = by.get(code)
        if a:
            name, color = a.get("person") or a["name"], a["color"]
        else:
            meta = parties.meta(code, country, eid)
            name, color = meta["name"], meta["color"]
            if code.startswith("?"):
                fixed = parties._display().get(eid, {}).get(code)
                name = (fixed or _short(names.get(code)) or (r.get("labels") or {}).get(code)
                        or name)
                color = colors.get(code) or (r.get("colors") or {}).get(code) or color
        rows.append({**x, "name": name, "color": color})
    return {**r, "rows": rows, "year": r["date"][:4]}


def _parliament(conn, country):
    from .. import results
    try:
        return results.parliament_view(conn, country)
    except Exception:                                  # noqa: BLE001
        return None


def _calendar():
    """data/next_elections.json (`politbureau calendari`), o res si no hi es."""
    path = ROOT / "data" / "next_elections.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _country_names():
    """{codi del globus: {"es", "ca"}}: noms dels paisos de Wikidata (CC0)."""
    path = ROOT / "config" / "country_names.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


_MONTHS = {
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
           "septiembre", "octubre", "noviembre", "diciembre"],
    "ca": ["gener", "febrer", "març", "abril", "maig", "juny", "juliol", "agost",
           "setembre", "octubre", "novembre", "desembre"],
}
_EN = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def _date_of(text):
    """"24 Aug 2027" -> date; None si nomes hi ha el mes o l'any."""
    parts = (text or "").split()
    if len(parts) != 3 or parts[1][:3].lower() not in _EN:
        return None
    try:
        return dt.date(int(parts[2]), _EN.index(parts[1][:3].lower()) + 1, int(parts[0]))
    except ValueError:
        return None


def _when(text, lang):
    """"24 Aug 2027" -> "24 d'agost del 2027" / "24 de agosto de 2027"."""
    if not text:
        return None
    parts = text.split()
    year = parts[-1]
    if len(parts) == 1:
        return year
    month = _MONTHS[lang][_EN.index(parts[-2][:3].lower())]
    day = parts[0] if len(parts) == 3 else None
    if lang == "es":
        return f"{day} de {month} de {year}" if day else f"{month} de {year}"
    de_m = f"d'{month}" if month[0] in "ao" else f"de {month}"
    return f"{day} {de_m} del {year}" if day else f"{month} del {year}"


def _fmt(v):
    return "—" if v is None else f"{v:.1f}".replace(".", ",")


def _fdate(s):
    return dt.date.fromisoformat(s).strftime("%d/%m/%Y") if s else "—"


def de(name):
    """"de França", "d'Itàlia": la preposicio catalana davant del nom del pais."""
    return f"d'{name}" if name[:1].lower() in "aeiouàèéíòóúh" else f"de {name}"


SUB_KINDS = {
    "regional": {"es": "elecciones regionales", "ca": "eleccions regionals"},
    "state": {"es": "elecciones estatales", "ca": "eleccions estatals"},
    "provincial": {"es": "elecciones provinciales", "ca": "eleccions provincials"},
    "autonomic": {"es": "elecciones autonómicas", "ca": "eleccions autonòmiques"},
    "municipal": {"es": "elecciones municipales", "ca": "eleccions municipals"},
    "mayoral": {"es": "elecciones a la alcaldía", "ca": "eleccions a l'alcaldia"},
    "local": {"es": "elecciones locales", "ca": "eleccions locals"},
}


def sub_kind(election):
    """{es, ca}: el tipus d'una eleccio regional o municipal ("eleccions
    regionals"), o None si es estatal. `pub.kind_es`/`kind_ca` el poden precisar
    ("eleccions al Parlament d'Escòcia")."""
    if election.get("group") != "sub":
        return None
    pub = election["pub"]
    base = SUB_KINDS.get(election.get("kind") or "regional", SUB_KINDS["regional"])
    return {"es": pub.get("kind_es") or base["es"], "ca": pub.get("kind_ca") or base["ca"]}


def _titles(data, lang):
    name, of = data["name"][lang], data["of"][lang]
    if data.get("sub"):
        kind = data["kind"][lang]
        what = (("candidato a candidato" if lang == "es" else "candidat a candidat")
                if data["presidential"] else
                ("partido a partido" if lang == "es" else "partit a partit"))
        if lang == "es":
            return (f"Encuestas {of} · {kind}",
                    f"Media de las encuestas de las próximas {kind} {of}, {what}, "
                    "con todos los sondeos que entran.")
        return (f"Enquestes {of} · {kind}",
                f"Mitjana de les enquestes de les properes {kind} {of}, {what}, "
                "amb tots els sondeigs que hi entren.")
    if lang == "es":
        kind = ("elecciones presidenciales" if data["presidential"] else
                "elecciones generales" if data["general"] else "elecciones legislativas")
        what = "candidato a candidato" if data["presidential"] else "partido a partido"
        return (f"Encuestas {of} · {kind}",
                f"Media de las encuestas de las próximas {kind} {of}, {what}, "
                "con todos los sondeos que entran.")
    kind = ("eleccions presidencials" if data["presidential"] else
            "eleccions generals" if data["general"] else "eleccions legislatives")
    what = "candidat a candidat" if data["presidential"] else "partit a partit"
    return (f"Enquestes {of} · {kind}",
            f"Mitjana de les enquestes de les properes {kind} {of}, {what}, "
            "amb tots els sondeigs que hi entren.")


def _unit_titles(data, g, lang):
    """Titol i descripcio de la fitxa d'un territori estranger."""
    of, units = data["of"][lang], data["depmap"]["units"][lang]
    first = g["rows"][0]
    if lang == "es":
        return (f"{g['name']}: estimación de voto · Encuestas {of}",
                f"Estimación de voto en {g['name']} para las próximas elecciones {of}: "
                f"{first['name']} va primero con un {_fmt(first['share'])} %. "
                f"Comparada con {data['depmap']['base_label']['es']}.")
    return (f"{g['name']}: estimació de vot · Enquestes {of}",
            f"Estimació de vot a {g['name']} per a les properes eleccions {of}: "
            f"{first['name']} va primer amb un {_fmt(first['share'])} %. "
            f"Comparada amb {data['depmap']['base_label']['ca']}.")


def sub_card(d):
    """El resum d'una eleccio regional o municipal per a les llistes."""
    return {"kind": d["kind"], "first": d["avg"][0] if d["avg"] else None,
            "second": d["avg"][1] if len(d["avg"]) > 1 else None,
            "n": len(d["polls"]), "last": d["polls"][0]["end"] if d["polls"] else None,
            "urls": d["urls"], "names": d["name"]}


def link_subs(done):
    """Enllaca cada eleccio regional o municipal amb el seu pais (`parent`): la
    pagina del pais en porta la llista (`subs`) i la de l'eleccio, el cami
    de tornada (`up`). `parent: spain` torna a la pagina d'Espanya."""
    by_id = dict(done)
    for _eid, d in done:
        d.setdefault("subs", [])
    for _eid, d in done:
        if not d["sub"]:
            continue
        parent = d["parent"]
        if parent == "spain":
            d["up"] = {lg: i18n.page_url("spain", lg) for lg in i18n.LANGS}
            d["up_name"] = {"es": "España", "ca": "Espanya"}
        elif parent in by_id:
            d["up"] = by_id[parent]["urls"]
            d["up_name"] = by_id[parent]["name"]
            by_id[parent]["subs"].append(sub_card(d))
    for _eid, d in done:
        d["subs"].sort(key=lambda c: parties.slug(c["names"]["ca"]))


def abroad_pages(env, cfg, conn):
    """Una pagina per eleccio estrangera i l'index d'Europa. Retorna els id escrits."""
    done = []
    for eid in cfg.get("_abroad") or []:
        data = abroad_data(conn, eid)
        if data:
            done.append((eid, data))
    link_subs(done)
    from . import trend as trendlib
    for eid, data in done:
        try:
            data["trend"] = None if data.get("stale") else trendlib.build(conn, eid, data["avg"])
            if data["trend"]:
                data["trend"]["data"] = trendlib.interactive(
                    conn, eid, data["avg"], election_day=str((abroad_elections().get(eid) or {}).get("election_date") or "") or None)
        except Exception as exc:                          # noqa: BLE001
            print(f"     avis: grafic d'evolucio de {eid} no generat ({type(exc).__name__}: {exc})")
            data["trend"] = None
        for lang in i18n.LANGS:
            title, description = _titles(data, lang)
            canonical = data["urls"][lang]
            html = render_page(env, cfg, "abroad.html.j2", lang, canonical, data["urls"],
                               title, description, d=data, fmt=_fmt, fdate=_fdate, de=de)
            write(DIST / canonical.strip("/") / "index.html", html)
            for g in (data["depmap"] or {}).get("deps", []):
                if not g.get("url"):
                    continue
                t, desc = _unit_titles(data, g, lang)
                html = render_page(env, cfg, "abroad_unit.html.j2", lang, g["url"][lang], g["url"],
                                   t, desc, d=data, u=g, fmt=_fmt, fdate=_fdate, de=de)
                write(DIST / g["url"][lang].strip("/") / "index.html", html)
                cfg.setdefault("_abroad_units", {}).setdefault(lang, []).append(g["url"][lang])
    subs = [(eid, d) for eid, d in done if d["sub"]]
    done_all, done = done, [(eid, d) for eid, d in done if not d["sub"]]
    if done:
        elections = abroad_elections()
        for lang in i18n.LANGS:
            canonical = world_url(lang)
            view, regional = [], []
            # Les regionals i municipals no pinten el globus (el pais el pinta la
            # seva eleccio estatal): van en una taula a part de la llista de paisos.
            subrows = sorted(({**c, "parent_name": d["up_name"][lang] if d.get("up_name") else "",
                               "name": d["name"][lang], "url": d["urls"][lang]}
                              for _e, d in subs for c in [sub_card(d)]),
                             key=lambda r: (parties.slug(r["parent_name"]), parties.slug(r["name"])))
            for eid, d in done:
                code = elections[eid]["pub"].get("map") or elections[eid]["country"]
                base = {"code": code, "url": d["urls"][lang], "presidential": d["presidential"]}
                if d["national"]:
                    view.append({**base, "name": d["name"][lang], "first": d["avg"][0],
                                 "second": d["avg"][1] if len(d["avg"]) > 1 else None,
                                 "n": len(d["polls"]), "last": d["polls"][0]["end"]})
                for reg in d["regions"]:
                    row = {**base, "code": reg["map"], "url": d["urls"][lang] + "#regions",
                           "name": f'{d["name"][lang]} · {reg["name"][lang]}',
                           "region": reg["name"][lang], "first": reg["avg"][0],
                           "second": reg["avg"][1] if len(reg["avg"]) > 1 else None,
                           "n": len(reg["polls"]), "last": reg["polls"][0]["end"]}
                    regional.append(row)
                    # Belgica no te mitjana estatal: a la taula hi surten les regions.
                    if not d["national"]:
                        view.append(row)
            spain = _spain(conn, lang)
            if spain:
                view.append(spain)
            # El cap de govern de cada pais (`head` a config/leaders.yaml) amb la seva
            # aprovacio, per comparar-los (09/11/2026).
            heads = []
            for name, url, blocks in (
                    [(d["name"][lang], d["urls"][lang], d.get("leaders") or [])
                     for _e, d in done]
                    + ([("España" if lang == "es" else "Espanya", spain["url"],
                         leaders_view(conn, "spain"))] if spain else [])):
                for b in blocks:
                    row = next((r for r in b["rows"] if b["metric"] == "approval"
                                and b["head"] and r["subject"] == b["head"]), None)
                    if row:
                        heads.append({"country": name, "url": url + "#lideres",
                                      "who": row["name"][lang], "yes": row["yes"],
                                      "no": row["no"], "net": row["net"],
                                      "delta": row["delta"], "last": row["last"]})
                        break
            heads.sort(key=lambda h: -h["net"])
            # El que el mapa necessita de cada pais, en JSON dins de la pagina. Si
            # un pais te legislatives i presidencials, el mapa pinta la primera
            # que surt a sources.yaml (les legislatives); la taula les porta totes.
            # Les regions (Escocia, Flandes...) es pinten per sobre del seu pais.
            mapdata = {}
            for r in view + regional:
                mapdata.setdefault(r["code"], {
                    "name": r["name"], "url": r["url"], "color": r["first"]["color"],
                    # Per a les etiquetes i la fitxa del globus: qui va primer (nom
                    # curt i %), el color del segon i quantes enquestes hi entren.
                    "lead": r["first"]["person"] or r["first"]["name"],
                    "pct": _fmt(r["first"]["share"]),
                    "c2": r["second"]["color"] if r["second"] else None,
                    "n": r.get("n"), "pres": bool(r.get("presidential")),
                    "first": f'{r["first"]["person"] or r["first"]["name"]} {_fmt(r["first"]["share"])} %',
                    "second": (f'{r["second"]["person"] or r["second"]["name"]} '
                               f'{_fmt(r["second"]["share"])} %') if r["second"] else ""})
            # La resta de paisos (03/11/2026): els que fan eleccions, amb la data de
            # les properes; els que no, amb el seu nom i prou.
            calendar, upcoming = [], {}
            today = dt.date.today()
            for code, info in _calendar().items():
                name = (_country_names().get(code) or {}).get(lang) or info["en"]
                leg, pres = _when(info.get("leg"), lang), _when(info.get("pres"), lang)
                url = (mapdata.get(code) or {}).get("url")
                calendar.append({"name": name, "leg": leg, "pres": pres, "url": url})
                # Les properes cites (120 dies) amb dia conegut, per a la franja de
                # sota del globus. Legislatives i presidencials el mateix dia, juntes.
                for kind in ("leg", "pres"):
                    day = _date_of(info.get(kind))
                    if not day or not 0 <= (day - today).days <= 120:
                        continue
                    card = upcoming.setdefault((day, code), {
                        "date": day.isoformat(), "day": day.day, "days": (day - today).days,
                        "month": _MONTHS[lang][day.month - 1], "name": name, "url": None,
                        "kinds": [], "lead": None})
                    card["kinds"].append(kind)
                    # El primer de les enquestes, nomes si son d'aquesta mateixa
                    # eleccio: el president suis l'elegeix el Parlament el 9/12, i
                    # les enquestes de Suissa son de les legislatives.
                    m = mapdata.get(code) or {}
                    if m.get("lead") and m.get("pres") == (kind == "pres"):
                        card["url"] = url
                        card["lead"] = {"name": m["lead"], "pct": m["pct"], "color": m["color"]}
                if code not in mapdata:
                    mapdata[code] = ({"name": name, "nopoll": True, "leg": leg, "pres": pres}
                                     if leg or pres else {"name": name, "noelection": True})
            for code, names in _country_names().items():
                mapdata.setdefault(code, {"name": names[lang]})
            calendar.sort(key=lambda r: parties.slug(r["name"]))
            view.sort(key=lambda r: (parties.slug(r["name"]), r["presidential"]))
            ncountries = len({elections[eid]["country"] for eid, _ in done}) + (1 if spain else 0)
            from .. import results as resultslib
            try:
                recent = resultslib.recent_view(conn, load_sources()["elections"])
            except Exception:                          # noqa: BLE001
                recent = []
            ctx = dict(
                rows=view, subrows=subrows, heads=heads, fmt=_fmt, fdate=_fdate, recent=recent,
                ncountries=ncountries,
                calendar=calendar,
                upcoming=[upcoming[k] for k in sorted(upcoming)][:10],
                npolls=sum(r["n"] or 0 for r in view),
                nsoon=len({c for _d, c in upcoming}),
                nelections=sum(1 for r in calendar if r["leg"] or r["pres"]),
                mapdata=json.dumps(mapdata, ensure_ascii=False).replace("</", "<\\/"))
            # La llista de paisos, les properes eleccions i el calendari, a part:
            # la portada es nomes el globus (05/11/2026).
            listing = i18n.page_url("countries", lang)
            write(DIST / listing.strip("/") / "index.html", render_page(
                env, cfg, "countries.html.j2", lang, listing,
                {lg: i18n.page_url("countries", lg) for lg in i18n.LANGS},
                ("Encuestas de todos los países y calendario electoral" if lang == "es"
                 else "Enquestes de tots els països i calendari electoral"),
                (f"La media de las encuestas de {ncountries} países, quién va primero en cada "
                 "uno y las próximas elecciones de todo el mundo." if lang == "es" else
                 f"La mitjana de les enquestes de {ncountries} països, qui va primer a cadascun "
                 "i les properes eleccions de tot el món."), **ctx))
            html = render_page(
                env, cfg, "world.html.j2", lang, canonical,
                {lg: world_url(lg) for lg in i18n.LANGS},
                (f"{cfg['site']['name']} · Mapa mundial de encuestas electorales" if lang == "es"
                 else f"{cfg['site']['name']} · Mapa mundial d'enquestes electorals"),
                (f"Mapa interactivo con la media de las encuestas de {ncountries} países: quién "
                 "va primero en cada uno y con qué porcentaje. Pulsa un país para ver todas "
                 "sus encuestas." if lang == "es" else
                 f"Mapa interactiu amb la mitjana de les enquestes de {ncountries} països: qui "
                 "va primer a cadascun i amb quin percentatge. Prem un país per veure'n totes "
                 "les enquestes."),
                bare=True, **ctx)
            write(DIST / canonical.strip("/") / "index.html", html)
    return [eid for eid, _ in done_all]
