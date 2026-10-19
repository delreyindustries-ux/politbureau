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
    "participation": {"es": "participacion", "ca": "participacio"},
    "strongholds": {"es": "feudos-progresistas", "ca": "feus-progressistes"},
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
    "nav_participation": {"es": "Participación 29N", "ca": "Participació 29N"},
    "nav_strongholds": {"es": "Feudos progresistas", "ca": "Feus progressistes"},
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
    "census": {"es": "electores el 29N", "ca": "electors el 29N"},
    "valid_votes": {"es": "Votos válidos", "ca": "Vots vàlids"},
    # --- districtes i renda
    "renda": {"es": "€ de renta neta por persona (INE, 2023)",
              "ca": "€ de renda neta per persona (INE, 2023)"},
    "districts_title": {"es": "Distritos", "ca": "Districtes"},
    "districts_lede": {
        "es": "Electores del 29N, renta y voto de cada distrito. Los nombres solo salen "
              "donde se ha podido comprobar que el distrito electoral coincide con el "
              "municipal; en el resto, el número del distrito censal.",
        "ca": "Electors del 29N, renda i vot de cada districte. Els noms només surten on "
              "s'ha pogut comprovar que el districte electoral coincideix amb el "
              "municipal; a la resta, el número del districte censal."},
    "district": {"es": "Distrito", "ca": "Districte"},
    "sections_n": {"es": "Secciones", "ca": "Seccions"},
    "mesas_n": {"es": "Mesas", "ca": "Meses"},
    "renda_short": {"es": "Renta/persona", "ca": "Renda/persona"},
    "final_23": {"es": "Particip. 23J", "ca": "Particip. 23J"},
    "first_29": {"es": "1.ª fuerza 29N", "ca": "1a força 29N"},
    "renda_note": {
        "es": "Renta: renta neta media por persona de 2023 (INE, Atlas de Distribución de "
              "Renta de los Hogares). No es el PIB per cápita, que el INE solo calcula por "
              "provincias. Electores del 29N por distrito: estimados como en las mesas.",
        "ca": "Renda: renda neta mitjana per persona del 2023 (INE, Atles de Distribució de "
              "Renda de les Llars). No és el PIB per càpita, que l'INE només calcula per "
              "províncies. Electors del 29N per districte: estimats com a les meses."},
    # --- mapa de la ciutat (carrers d'OpenFreeMap, nomes si es prem el boto)
    "secmap_city": {"es": "Mostrar el mapa de la ciudad", "ca": "Mostrar el mapa de la ciutat"},
    "secmap_city_note": {
        "es": "El mapa de la ciudad (calles de OpenFreeMap, datos de OpenStreetMap) solo se "
              "carga si pulsas el botón: entonces tu navegador se conecta a unpkg.com y a "
              "tiles.openfreemap.org. Más información en",
        "ca": "El mapa de la ciutat (carrers d'OpenFreeMap, dades d'OpenStreetMap) només es "
              "carrega si prems el botó: aleshores el teu navegador es connecta a unpkg.com i "
              "a tiles.openfreemap.org. Més informació a"},
    # --- mapa de seccions
    "secmap_title": {"es": "Mapa de secciones y mesas", "ca": "Mapa de seccions i meses"},
    "secmap_lede": {
        "es": "Cada mancha es una sección censal; sus mesas se reparten a los electores "
              "por orden alfabético, así que no tienen límites propios. Pasa el ratón o toca "
              "una sección para ver sus mesas. Rueda o botones para acercarte.",
        "ca": "Cada taca és una secció censal; les seves meses es reparteixen els electors "
              "per ordre alfabètic, i per això no tenen límits propis. Passa el ratolí o toca "
              "una secció per veure'n les meses. Roda o botons per apropar-t'hi."},
    "secmap_note": {
        "es": "Límites: INE, secciones censales a 1/1/2023 (las del 23J). Las secciones "
              "creadas o cambiadas después salen en gris.",
        "ca": "Límits: INE, seccions censals a 1/1/2023 (les del 23J). Les seccions "
              "creades o canviades després surten en gris."},
    # --- meses electorals
    "mesas_title": {"es": "Mesas electorales", "ca": "Meses electorals"},
    "mesas_show": {"es": "Ver las {n} mesas", "ca": "Veure les {n} meses"},
    "mesa": {"es": "Mesa", "ca": "Mesa"},
    "mesa_district": {"es": "Dist.", "ca": "Dte."},
    "mesa_section": {"es": "Secc.", "ca": "Secc."},
    "mesa_electors": {"es": "Electores 29N*", "ca": "Electors 29N*"},
    "mesa_turnout": {"es": "Participación 23J", "ca": "Participació 23J"},
    "mesa_estimate": {"es": "Estimación 29N", "ca": "Estimació 29N"},
    "mesa_first": {"es": "1.ª fuerza", "ca": "1a força"},
    "mesas_lede": {
        "es": "Censo, participación de 2023 y estimación de voto para el 29N de cada mesa. "
              "La estimación aplica a cada mesa el mismo cambio que el modelo prevé para "
              "todo el municipio, a partir de su resultado del 23J.",
        "ca": "Cens, participació del 2023 i estimació de vot per al 29N de cada mesa. "
              "L'estimació aplica a cada mesa el mateix canvi que el model preveu per a "
              "tot el municipi, a partir del seu resultat del 23J."},
    "mesas_note": {
        "es": "* Estimado: el INE publica el censo del 29N por municipio, no por mesa. Es el "
              "censo de cada mesa en 2023 multiplicado por el crecimiento de los residentes del "
              "municipio, sin el voto exterior (CERA), que no se cuenta en ninguna mesa. La "
              "participación del 29N por mesa la publica el Ministerio del Interior semanas "
              "después de la elección; la noche electoral solo la da por municipio.",
        "ca": "* Estimat: l'INE publica el cens del 29N per municipi, no per mesa. És el cens "
              "de cada mesa el 2023 multiplicat pel creixement dels residents del municipi, "
              "sense el vot exterior (CERA), que no es compta a cap mesa. La participació del "
              "29N per mesa la publica el Ministeri de l'Interior setmanes després de "
              "l'elecció; la nit electoral només la dona per municipi."},
    "belongs_to": {"es": "Pertenece a", "ca": "Pertany a"},
    "seats_title": {"es": "Diputados que elige", "ca": "Diputats que elegeix"},
    "seats_in_play": {"es": "Escaños en juego", "ca": "Escons en joc"},
    "coalition": {"es": "¿Y si se presentaran juntos?",
                  "ca": "I si es presentessin junts?"},
    "coalition_preset_left": {"es": "Todo a la izquierda del PSOE",
                             "ca": "Tot a l'esquerra del PSOE"},
    "coalition_preset_leftpsoe": {"es": "La izquierda con el PSOE",
                                  "ca": "L'esquerra amb el PSOE"},
    "coalition_clear": {"es": "Limpiar", "ca": "Netejar"},
    "coalition_scenario": {"es": "Escenario", "ca": "Escenari"},
    "sc_full": {"es": "Todo el voto se transfiere (techo)",
                "ca": "Tot el vot es transfereix (sostre)"},
    "sc_mob": {"es": "La unidad moviliza: +5%", "ca": "La unitat mobilitza: +5%"},
    "sc_leak": {"es": "Se descuelga un 10%", "ca": "Se'n despenja un 10%"},
    "sc_break": {"es": "Se descuelga un 20%", "ca": "Se'n despenja un 20%"},
    "coalition_caveat": {
        "es": "Ningún escenario es una predicción. Una coalición cambia la "
              "campaña, el mensaje y quién se siente representado, y eso no cabe "
              "en un porcentaje. El voto que no sigue a la lista conjunta se "
              "cuenta como abstención, no se reparte entre rivales: repartirlo "
              "sería inventar un trasvase que ningún dato sostiene.",
        "ca": "Cap escenari no és una predicció. Una coalició canvia la campanya, "
              "el missatge i qui s'hi sent representat, i això no cap en un "
              "percentatge. El vot que no segueix la llista conjunta es compta "
              "com a abstenció, no es reparteix entre rivals: repartir-lo seria "
              "inventar-se un transvasament que cap dada no sustenta."},
    "notice_veda": {
        "es": "<b>Veda electoral.</b> La ley (art. 69.7 de la LOREG) prohíbe publicar "
              "encuestas los cinco días anteriores a la votación. Desde el 24 de noviembre "
              "no añadimos ninguna encuesta nueva: la estimación es la del 23 de noviembre "
              "y no se actualizará hasta que cierren los colegios, el 29 a las 20:00.",
        "ca": "<b>Veda electoral.</b> La llei (art. 69.7 de la LOREG) prohibeix publicar "
              "enquestes els cinc dies anteriors a la votació. Des del 24 de novembre no "
              "afegim cap enquesta nova: l'estimació és la del 23 de novembre i no "
              "s'actualitzarà fins que tanquin els col·legis, el 29 a les 20.00.",
    },
    "notice_exit_polls": {
        "es": "<b>Colegios cerrados.</b> Cuando hay sondeos a pie de urna, la estimación "
              "se calcula solo con ellos. Son sondeos, no el recuento oficial.",
        "ca": "<b>Col·legis tancats.</b> Quan hi ha sondeigs a peu d'urna, l'estimació "
              "es calcula només amb ells. Són sondeigs, no el recompte oficial.",
    },
    "coalition_intro": {
        "es": "Pulsa dos o más partidos. La suma de escaños no es la respuesta: "
              "la ley d'Hondt no es aditiva, y los votos que a cada uno le sobraban "
              "por separado pueden sumar para un escaño más. El reparto se hace "
              "circunscripción por circunscripción, como en la realidad. Y como el "
              "electorado no se transfiere entero, verás cuatro escenarios en vez "
              "de una cifra.",
        "ca": "Prem dos o més partits. La suma d'escons no és la resposta: la llei "
              "d'Hondt no és additiva, i els vots que a cadascun li sobraven per "
              "separat poden sumar per a un escó més. El repartiment es fa "
              "circumscripció per circumscripció, com a la realitat. I com que "
              "l'electorat no es transfereix sencer, hi veuràs quatre escenaris en "
              "comptes d'una xifra."},
    "coalition_hint": {"es": "Elige al menos dos partidos.",
                       "ca": "Tria almenys dos partits."},
    "coalition_separate": {"es": "Por separado", "ca": "Per separat"},
    "coalition_together": {"es": "Juntos", "ca": "Junts"},
    "coalition_nochange": {"es": "sin cambios", "ca": "sense canvis"},
    "coalition_from": {"es": "El escaño sale de", "ca": "L'escó surt de"},
    "seat_one": {"es": "escaño", "ca": "escó"},
    "seat_many": {"es": "escaños", "ca": "escons"},
    "other_parties": {"es": "Resto de candidaturas",
                      "ca": "Resta de candidatures"},
    "other_parties_note": {
        "es": "Formaciones por debajo del 0,3%. Aparecen todas: quedarse solo con "
              "las grandes es esconder la mitad de las candidaturas presentadas.",
        "ca": "Formacions per sota del 0,3%. Hi son totes: quedar-se nomes amb les "
              "grans es amagar la meitat de les candidatures presentades."},
    "no_seat": {"es": "Candidaturas sin representación",
                "ca": "Candidatures sense representació"},
    "no_seat_note": {
        "es": "Votos que no eligieron a nadie en esta circunscripción en {year}: "
              "{count} candidaturas, {votes} votos, el {share} del voto válido.",
        "ca": "Vots que no van triar ningu en aquesta circumscripcio el {year}: "
              "{count} candidatures, {votes} vots, el {share} del vot valid."},
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
