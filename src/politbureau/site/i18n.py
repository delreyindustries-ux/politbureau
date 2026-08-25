"""Textos del lloc public, en castella i catala.

Una sola taula amb els dos idiomes de costat: aixi es veu d'un cop d'ull si un
text s'ha quedat sense traduir, cosa que amb dos fitxers separats passa sempre.

Els noms dels territoris NO es tradueixen: es fan servir els oficials de
l'Institut Geografic Nacional en totes dues versions. Traduir-los a ull seria
inventar-se toponims.
"""
from __future__ import annotations

LANGS = ("es", "ca")

# Els trossos d'URL, que tambe canvien d'idioma perque les adreces siguin
# llegibles i es puguin indexar en cada llengua.
PATHS = {
    "es": {"municipality": "municipio", "province": "provincia", "region": "comunidad"},
    "ca": {"municipality": "municipi", "province": "provincia", "region": "comunitat"},
}

# Les pagines fixes. Tambe en l'idioma de cadascuna: una adreca /ca/privacidad/
# en una pagina en catala queda com un pedac, i els cercadors llegeixen l'URL.
PAGES = {
    "map":     {"es": "mapa", "ca": "mapa"},
    "method":  {"es": "metodologia", "ca": "metodologia"},
    "legal":   {"es": "aviso-legal", "ca": "avis-legal"},
    "privacy": {"es": "privacidad", "ca": "privadesa"},
    "cookies": {"es": "cookies", "ca": "galetes"},
}

T = {
    "site_tagline": {
        "es": "Resultados electorales y estimación de voto, municipio a municipio",
        "ca": "Resultats electorals i estimació de vot, municipi a municipi",
    },
    "site_description": {
        "es": "Resultados electorales oficiales de los 8.131 municipios de España y "
              "estimación de voto actualizada cada día con las encuestas publicadas.",
        "ca": "Resultats electorals oficials dels 8.131 municipis d'Espanya i estimació "
              "de vot actualitzada cada dia amb les enquestes publicades.",
    },
    "nav_map": {"es": "Mapa", "ca": "Mapa"},
    "nav_method": {"es": "Metodología", "ca": "Metodologia"},
    "nav_legal": {"es": "Aviso legal", "ca": "Avís legal"},
    "nav_privacy": {"es": "Privacidad", "ca": "Privadesa"},
    "nav_cookies": {"es": "Cookies", "ca": "Galetes"},
    "other_lang": {"es": "Català", "ca": "Castellano"},

    # --- fitxa de territori
    "real_result": {"es": "Resultado real", "ca": "Resultat real"},
    "estimate_today": {"es": "Estimación de hoy", "ca": "Estimació d'avui"},
    "party": {"es": "Partido", "ca": "Partit"},
    "votes": {"es": "Votos", "ca": "Vots"},
    "share": {"es": "% sobre voto válido", "ca": "% sobre vot vàlid"},
    "today": {"es": "Hoy", "ca": "Avui"},
    "change": {"es": "Cambio", "ca": "Canvi"},
    "census": {"es": "Censo electoral", "ca": "Cens electoral"},
    "valid_votes": {"es": "Votos válidos", "ca": "Vots vàlids"},
    "belongs_to": {"es": "Pertenece a", "ca": "Pertany a"},
    "seats_title": {"es": "Diputados que elige", "ca": "Diputats que elegeix"},
    "seats_in_play": {"es": "Escaños en juego", "ca": "Escons en joc"},
    "deputies_elected": {"es": "Diputados electos", "ca": "Diputats electes"},
    "with_estimate": {"es": "Con la estimación de hoy", "ca": "Amb l'estimació d'avui"},
    "enters": {"es": "entra", "ca": "entra"},
    "leaves": {"es": "sale", "ca": "surt"},
    "last_seat": {"es": "último escaño repartido", "ca": "últim escó repartit"},
    "needs": {"es": "le faltan", "ca": "li falten"},
    "municipalities_of": {"es": "Municipios de", "ca": "Municipis de"},
    "provinces_of": {"es": "Provincias de", "ca": "Províncies de"},
    "see_map": {"es": "Ver en el mapa", "ca": "Veure al mapa"},
    "updated": {"es": "Actualizado el", "ca": "Actualitzat el"},
    "search_placeholder": {"es": "Busca un municipio…", "ca": "Cerca un municipi…"},

    # --- avisos (la part honesta, i no es pot treure)
    "estimate_warning": {
        "es": "<b>Esto es una estimación, no un resultado.</b> No existen encuestas "
              "municipales: nadie encuesta este municipio. La cifra parte del "
              "resultado real y le aplica el desplazamiento de voto que marcan las "
              "encuestas de ámbito nacional.",
        "ca": "<b>Això és una estimació, no un resultat.</b> No existeixen enquestes "
              "municipals: ningú no enquesta aquest municipi. La xifra parteix del "
              "resultat real i hi aplica el desplaçament de vot que marquen les "
              "enquestes d'àmbit estatal.",
    },
    "deputies_warning": {
        "es": "Los nombres de la estimación suponen que los partidos repetirían "
              "exactamente las listas de 2023, y no lo harán. Sirven para ver cuántos "
              "escaños cambian y en qué orden, no para predecir nombres.",
        "ca": "Els noms de l'estimació suposen que els partits repetirien exactament "
              "les llistes del 2023, i no ho faran. Serveixen per veure quants escons "
              "canvien i en quin ordre, no per predir noms.",
    },

    # --- consentiment
    "cookie_title": {"es": "Cookies", "ca": "Galetes"},
    "cookie_text": {
        "es": "Este sitio usa cookies de publicidad de Google para financiarse. "
              "No se carga ninguna hasta que lo aceptes. Si rechazas, el sitio "
              "funciona igual y no verás anuncios personalizados.",
        "ca": "Aquest lloc fa servir galetes de publicitat de Google per finançar-se. "
              "No se'n carrega cap fins que ho acceptis. Si ho rebutges, el lloc "
              "funciona igual i no veuràs anuncis personalitzats.",
    },
    "cookie_accept": {"es": "Aceptar", "ca": "Acceptar"},
    "cookie_reject": {"es": "Rechazar", "ca": "Rebutjar"},
    "cookie_more": {"es": "Más información", "ca": "Més informació"},
    "ad_label": {"es": "Publicidad", "ca": "Publicitat"},

    "sources": {"es": "Fuentes", "ca": "Fonts"},
    "source_line": {
        "es": "Resultados y escaños: Ministerio del Interior. Encuestas: Wikipedia. "
              "Cartografía: Instituto Geográfico Nacional.",
        "ca": "Resultats i escons: Ministeri de l'Interior. Enquestes: Wikipedia. "
              "Cartografia: Institut Geogràfic Nacional.",
    },
}


def t(key: str, lang: str) -> str:
    entry = T.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get("es") or key


def path_for(level: str, lang: str) -> str:
    return PATHS.get(lang, PATHS["es"]).get(level, level)


def page_for(key: str, lang: str) -> str:
    return PAGES.get(key, {}).get(lang) or PAGES.get(key, {}).get("es") or key


def page_url(key: str, lang: str) -> str:
    return f"/{lang}/{page_for(key, lang)}/"
