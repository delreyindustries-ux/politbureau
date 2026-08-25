"""Les pagines que no son fitxes de territori: portada, mapa, legals i sitemap."""
from __future__ import annotations

import datetime as dt
import gzip
import json
import shutil
from pathlib import Path

from .. import parties
from ..geo import fetch as geo
from . import i18n
from .build import DIST, ELECTION, ROOT, WEB, BASELINE_YEAR, thousands
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
    for lang in i18n.LANGS:
        canonical = f"/{lang}/"
        html = render_page(
            env, cfg, "home.html.j2", lang, canonical,
            {lg: f"/{lg}/" for lg in i18n.LANGS},
            f"{cfg['site']['name']} · {i18n.t('site_tagline', lang)}",
            i18n.t("site_description", lang),
            highlights=highlights, regions=[
                {"name": data["names"]["region"].get(c, c), "url": urls[("region", c)][lang]}
                for c in sorted(data["names"]["region"],
                                key=lambda c: data["names"]["region"].get(c, ""))
                if ("region", c) in urls])
        write(DIST / lang / "index.html", html)

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


def sitemaps(cfg, urls):
    """Un sitemap per idioma mes un index. El limit son 50.000 URL per fitxer i
    aqui n'hi ha unes vuit mil per idioma, aixi que cap no es queda a prop."""
    base = cfg["site"]["base_url"].rstrip("/")
    today = dt.date.today().isoformat()
    files = []
    for lang in i18n.LANGS:
        entries = [f"/{lang}/"] + [i18n.page_url(k, lang)
                                   for k in ("map", "method", "legal", "privacy", "cookies")]
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
    return files


def assets(data, urls):
    """Copia el CSS i el JS i escriu les dades que necessita el mapa interactiu."""
    out = DIST / "assets"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("site.css", "site.js", "map.js", "map.css", "favicon.svg"):
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
