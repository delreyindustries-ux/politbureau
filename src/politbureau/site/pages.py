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


def method_page(env, cfg, stats):
    """La metodologia sencera. Es la pagina que fa creible tota la resta."""
    for lang in i18n.LANGS:
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
            stats=stats, baseline_year=BASELINE_YEAR)
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
    for lang in i18n.LANGS:
        canonical = i18n.page_url("spain", lang)
        html = render_page(
            env, cfg, "home.html.j2", lang, canonical,
            {lg: i18n.page_url("spain", lg) for lg in i18n.LANGS},
            f"{cfg['site']['name']} · {i18n.t('site_tagline', lang)}",
            i18n.t("site_description", lang),
            highlights=highlights, simulator=sim_json, baseline_year=BASELINE_YEAR,
            notice=notice, regions=[
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
                                   for k in ("spain", "map", "participation", "strongholds", "method", "legal", "privacy", "cookies")]
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
    for name in ("site.css", "site.js", "map.js", "map.css", "coalition.js", "seccions.js",
                 "world.js", "world.json", "favicon.svg"):
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
    used = [p for p in load_polls(conn, eid, scope_code or None)
            if p["fieldwork_end"]
            and (today - dt.date.fromisoformat(p["fieldwork_end"])).days <= 90
            and not (p["sample_size"] and p["sample_size"] < 300)]
    if not used:
        return None
    # Escons d'Italia: proporcional estatal amb la mitjana, calculat aqui mateix.
    # Aixi la publicacio no ha de fer `build --country IT`, que baixaria cada
    # hora el resultat del 2022 municipi a municipi per a un mapa que la web no te.
    seats, margins = {}, None
    if chamber and chamber.get("method") in ("proportional", "dhondt", "sainte_lague", "hare",
                                             "droop"):
        from ..model import seats as seatlib
        shares = {r["party"]: r["share"] for r in rows if r["party"] != "OTHER"}
        method = "dhondt" if chamber["method"] == "proportional" else chamber["method"]
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
            meta = {**meta, "name": _short(names.get(r["party"])) or meta["name"],
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
    return {"avg": avg, "order": [next(a for a in avg if a["code"] == c) for c in order],
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
            "units": {"es": cfg.get("units_es", "departamentos"), "ca": cfg.get("units_ca", "departaments")},
            "base_label": {"es": cfg.get("base_es", "la primera vuelta de 2022"),
                           "ca": cfg.get("base_ca", "la primera volta del 2022")},
            "leaders": sorted(([n, c, k] for n, (c, k) in leaders.items()), key=lambda x: -x[2])}


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
            "total_polls": conn.execute("SELECT COUNT(*) FROM poll WHERE election_id = ?",
                                        (eid,)).fetchone()[0],
            "presidential": election.get("display") == "candidates",
            "general": election.get("kind") == "general",
            "name": {"es": pub["name_es"], "ca": pub["name_ca"]},
            # "del Regne Unit", "dels Països Baixos": quan el nom porta article.
            "of": {"es": pub.get("of_es") or f"de {pub['name_es']}",
                   "ca": pub.get("of_ca") or de(pub["name_ca"])},
            "urls": {lg: abroad_url(election, lg) for lg in i18n.LANGS},
            "wiki": (f"https://{election.get('lang', 'en')}.wikipedia.org/wiki/"
                     + election["page"].replace(" ", "_"))}


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


def _titles(data, lang):
    name, of = data["name"][lang], data["of"][lang]
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


def abroad_pages(env, cfg, conn):
    """Una pagina per eleccio estrangera i l'index d'Europa. Retorna els id escrits."""
    done = []
    for eid in cfg.get("_abroad") or []:
        data = abroad_data(conn, eid)
        if not data:
            continue
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
        done.append((eid, data))
    if done:
        elections = abroad_elections()
        for lang in i18n.LANGS:
            canonical = world_url(lang)
            view, regional = [], []
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
                rows=view, fmt=_fmt, fdate=_fdate, ncountries=ncountries, calendar=calendar,
                upcoming=[upcoming[k] for k in sorted(upcoming)][:10],
                npolls=sum(r["n"] or 0 for r in view),
                nsoon=len({c for _d, c in upcoming}),
                nelections=sum(1 for r in calendar if r["leg"] or r["pres"]),
                mapdata=json.dumps(mapdata, ensure_ascii=False).replace("</", "<\\/"))
            write(DIST / canonical.strip("/") / "index.html", html)
    return [eid for eid, _ in done]
