"""Renderitzat de les pagines: plantilles, blocs d'anunci i fitxes de territori."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from .. import parties
from . import i18n
from .build import (BASELINE_YEAR, DIST, LEVEL_NAME, WEB, area_rows, deputies_for,
                    unrepresented,
                    dhondt_for, lede_for, pct, thousands)


def make_env():
    env = Environment(loader=FileSystemLoader(str(WEB / "templates")),
                      autoescape=select_autoescape(["html", "xml"]),
                      trim_blocks=True, lstrip_blocks=True)
    env.filters["thousands"] = thousands
    env.filters["pct"] = pct
    return env


def ad_block(cfg, name, lang):
    """Un bloc d'anunci.

    Si no hi ha identificador d'AdSense configurat no escriu res: aixi el lloc
    es pot desenvolupar, provar i fins i tot publicar sense carregar cap
    rastrejador ni demanar consentiment de res.
    """
    client = (cfg.get("publicidad") or {}).get("adsense_client") or ""
    slot = ((cfg.get("publicidad") or {}).get("slots") or {}).get(name) or ""
    if not client or not slot:
        return ""
    return (
        '<aside class="ad">'
        f'<span class="adlabel">{i18n.t("ad_label", lang)}</span>'
        '<ins class="adsbygoogle" style="display:block" '
        f'data-ad-client="{client}" data-ad-slot="{slot}" '
        'data-ad-format="auto" data-full-width-responsive="true"></ins>'
        '</aside>')


def render_page(env, cfg, template, lang, canonical, alternates, title,
                description, structured=None, **ctx):
    site = cfg["site"]
    depth = len([p for p in canonical.strip("/").split("/") if p])
    return env.get_template(template).render(
        lang=lang,
        root="../" * depth,
        base_url=site["base_url"].rstrip("/"),
        site_name=site["name"],
        canonical=canonical,
        alternates=alternates,
        other_lang_url=alternates.get("ca" if lang == "es" else "es", "/"),
        title=title,
        description=description,
        structured_data=structured,
        built_on=dt.date.today().strftime("%d/%m/%Y"),
        adsense_client=(cfg.get("publicidad") or {}).get("adsense_client") or "",
        ga_id=(cfg.get("analitica") or {}).get("ga_measurement_id") or "",
        paths=i18n.PATHS,
        t=lambda key: i18n.t(key, lang),
        page=lambda key: i18n.page_for(key, lang),
        ad=lambda name: Markup(ad_block(cfg, name, lang)),
        **ctx)


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _qualifier(area, level, parent, kind):
    """Que va entre parentesis darrere del nom, per distingir pagines homonimes.

    Hi ha vint-i-un municipis que comparteixen nom amb un altre d'una altra
    provincia, i set comunitats uniprovincials on comunitat i provincia es diuen
    igual. Amb el nom sol, dues pagines diferents tenen el mateix titol i
    competeixen entre elles al cercador.
    """
    if level == "municipality" and parent and parent != area["name"]:
        return parent
    return kind


def _titles(area, kind, top, lang, level, parent):
    tag = _qualifier(area, level, parent, kind)
    if lang == "es":
        return (f"{area['name']} ({tag}): resultados electorales {BASELINE_YEAR} "
                f"y estimación de voto",
                f"Resultados de {area['name']} ({tag}) en las generales de "
                f"{BASELINE_YEAR}: {top} fue la fuerza más votada. Datos oficiales "
                f"del Ministerio del Interior y estimación de voto actualizada.")
    return (f"{area['name']} ({tag}): resultats electorals {BASELINE_YEAR} "
            f"i estimació de vot",
            f"Resultats de {area['name']} ({tag}) a les generals del "
            f"{BASELINE_YEAR}: {top} va ser la força més votada. Dades oficials "
            f"del Ministeri de l'Interior i estimació de vot actualitzada.")


def territory_pages(env, cfg, data, urls, prov_region):
    """Una pagina per territori i idioma. Es el gruix del lloc."""
    # Nomes territoris que existeixen de debo. es-atlas porta uns quants codis
    # municipals amb prefixos 53 i 54 que no corresponen a cap provincia real,
    # i sense aquest filtre el generador els buscaria i petaria.
    municipalities_of, provinces_of = {}, {}
    for code in data["names"]["municipality"]:
        if ("municipality", code) in urls:
            municipalities_of.setdefault(code[:2], []).append(code)
    for prov, region in prov_region.items():
        if ("province", prov) in urls and ("region", region) in urls:
            provinces_of.setdefault(region, []).append(prov)
    for prov in municipalities_of:
        municipalities_of[prov].sort(key=lambda c: data["names"]["municipality"].get(c, ""))

    # Quins territoris acaben tenint pagina de debo. es-atlas inclou Gibraltar i
    # uns quants codis amb prefix 53 i 54 que no son municipis espanyols i no
    # tenen cap resultat electoral. Sense retornar aquest conjunt, el sitemap i
    # la portada els enllacen i el lloc surt amb 168 adreces mortes.
    written_keys = set()
    for level in ("region", "province", "municipality"):
        for code, name in sorted(data["names"][level].items()):
            rows = area_rows(data, level, code)
            if not rows:
                continue          # territoris sense dades: no es publica una pagina buida
            info = data["meta"].get((level, code)) or {}
            area = {"code": code, "name": info.get("name") or name,
                    "census": info.get("census"), "valid_votes": info.get("valid_votes")}
            dh = dhondt_for(data, code) if level == "province" else None
            dep = deputies_for(data, code) if level == "province" else None
            mag = data["magnitude"].get(code) if level == "province" else None

            for lang in i18n.LANGS:
                canonical = urls[(level, code)][lang]
                crumbs, children, siblings = [], [], []
                ch_title = si_title = ""

                if level == "municipality":
                    region = (data["region_of"]["municipality"].get(code)
                              or prov_region.get(code[:2]))
                    if region and ("region", region) in urls:
                        crumbs.append({"name": data["names"]["region"].get(region, region),
                                       "url": urls[("region", region)][lang]})
                    if ("province", code[:2]) in urls:
                        crumbs.append({"name": data["names"]["province"].get(code[:2], code[:2]),
                                       "url": urls[("province", code[:2])][lang]})
                    # Enllacos cap als veins de la mateixa provincia. Son el cami
                    # pel qual un cercador arriba als municipis petits: a Cabra de
                    # Mora no hi enllaca ningu mes.
                    peers = municipalities_of.get(code[:2], [])
                    pos = peers.index(code) if code in peers else 0
                    ring = [c for c in peers[max(0, pos - 12):pos + 13] if c != code]
                    siblings = [{"name": data["names"]["municipality"][c],
                                 "url": urls[("municipality", c)][lang]} for c in ring]
                    si_title = (i18n.t("municipalities_of", lang) + " "
                                + data["names"]["province"].get(code[:2], ""))

                elif level == "province":
                    region = prov_region.get(code)
                    if region and ("region", region) in urls:
                        crumbs.append({"name": data["names"]["region"].get(region, region),
                                       "url": urls[("region", region)][lang]})
                    children = [{"name": data["names"]["municipality"][c],
                                 "url": urls[("municipality", c)][lang]}
                                for c in municipalities_of.get(code, [])]
                    ch_title = i18n.t("municipalities_of", lang) + " " + area["name"]

                else:
                    children = [{"name": data["names"]["province"].get(p, p),
                                 "url": urls[("province", p)][lang]}
                                for p in sorted(provinces_of.get(code, []),
                                                key=lambda p: data["names"]["province"].get(p, ""))]
                    ch_title = i18n.t("provinces_of", lang) + " " + area["name"]

                kind = LEVEL_NAME[level][lang]
                with_real = [x for x in rows if x["share"] is not None]
                winner = max(with_real, key=lambda x: x["share"])["name"] if with_real                     else rows[0]["name"]
                parent = (data["names"]["province"].get(code[:2])
                          if level == "municipality" else None)
                title, desc = _titles(area, kind, winner, lang, level, parent)
                structured = json.dumps({
                    "@context": "https://schema.org",
                    "@type": "Dataset",
                    "name": title,
                    "description": desc,
                    "isAccessibleForFree": True,
                    "creator": {"@type": "Organization", "name": cfg["site"]["name"]},
                    "spatialCoverage": {"@type": "Place", "name": area["name"]},
                    "license": "https://creativecommons.org/licenses/by/4.0/",
                }, ensure_ascii=False)

                html = render_page(
                    env, cfg, "territory.html.j2", lang, canonical,
                    urls[(level, code)], title, desc, structured,
                    area=area, rows=[r for r in rows if not r["minor"]],
                    minor_rows=[r for r in rows if r["minor"]],
                    no_seat=unrepresented(rows, level, area["valid_votes"]),
                    level=level,
                    lede=lede_for(data, level, code, rows, lang),
                    baseline_year=BASELINE_YEAR, magnitude=mag,
                    dhondt=dh, deputies=dep,
                    crumbs=crumbs, children=children, children_title=ch_title,
                    siblings=siblings, siblings_title=si_title)
                write(DIST / canonical.strip("/") / "index.html", html)
                written_keys.add((level, code))
    return written_keys
