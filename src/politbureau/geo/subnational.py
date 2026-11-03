"""Mapes per territori de les eleccions estrangeres (03/11/2026).

La versio general del que geo/france.py fa per als departaments francesos: per a
cada pais, un SVG dels seus territoris (regions, lander, voivodats...) i el
resultat real de l'ultima eleccio en cadascun, que la web fa servir de base per
projectar-hi la mitjana d'enquestes d'avui (pages._departments).

Es fa UNA vegada en local i el resultat va al repositori (web/<pais>/). Contorns:
Natural Earth admin-1 10m (domini public). Resultats: els que ja te la base de
dades de l'eina local, o un fitxer oficial baixat amb el permis de l'Alfonso.

Us: python -m politbureau.geo.subnational IT data/geo/world/admin1/ne_10m_admin_1_states_provinces
"""
from __future__ import annotations

import json
import re
import math
import sqlite3
import sys
from pathlib import Path

from .seccions import _dbf, _shp

ROOT = Path(__file__).resolve().parents[3]
WIDTH = 1000

# Cada pais: com es fan els territoris a partir de Natural Earth i d'on surt la base.
#   adm0    -> pais a Natural Earth
#   group   -> camp de Natural Earth que defineix el territori (s'hi ajunten les provincies)
#   codes   -> {valor del camp: codi del territori a la base de dades}
#   bbox    -> (lon0, lon1, lat0, lat1) del mapa
SPECS = {
    "IT": {
        "adm0": "ITA", "group": "region", "dir": "it", "unit_file": "regioni.json",
        "bbox": (6.4, 18.8, 36.4, 47.2),
        "election": "politiche-2022", "base_file": "politiche-2022.json",
        "level": "region", "source": "Ministero dell'Interno (Eligendo), via ondata",
        "codes": {
            "Piemonte": "01", "Valle d'Aosta": "02", "Lombardia": "03", "Trentino-Alto Adige": "04",
            "Veneto": "05", "Friuli-Venezia Giulia": "06", "Liguria": "07", "Emilia-Romagna": "08",
            "Toscana": "09", "Umbria": "10", "Marche": "11", "Lazio": "12", "Abruzzo": "13",
            "Molise": "14", "Campania": "15", "Apulia": "16", "Basilicata": "17", "Calabria": "18",
            "Sicily": "19", "Sardegna": "20",
        },
        "names": {"Apulia": "Puglia", "Sicily": "Sicilia"},
    },
    # Alemanya: Bundestag 2025, segon vot per Land. Fitxer kerg2.csv de la
    # Bundeswahlleiterin (Datenlizenz Deutschland - Namensnennung 2.0), baixat
    # el 03/11/2026 a data/raw/de/ amb el permis de l'Alfonso.
    "DE": {
        "adm0": "DEU", "group": "name", "dir": "de", "unit_file": "laender.json",
        "bbox": (5.6, 15.3, 47.2, 55.1),
        "base_file": "bundestag-2025.json", "loader": "de",
        "source": "Die Bundeswahlleiterin, Wiesbaden 2025 (dl-de/by-2-0)",
        "codes": {
            "Schleswig-Holstein": "01", "Hamburg": "02", "Niedersachsen": "03", "Bremen": "04",
            "Nordrhein-Westfalen": "05", "Hessen": "06", "Rheinland-Pfalz": "07",
            "Baden-Württemberg": "08", "Bayern": "09", "Saarland": "10", "Berlin": "11",
            "Brandenburg": "12", "Mecklenburg-Vorpommern": "13", "Sachsen": "14",
            "Sachsen-Anhalt": "15", "Thüringen": "16",
        },
        # Sigles de la Bundeswahlleiterin -> codis de les enquestes (eu-de).
        "parties": {"CDU": "?CDUCSU", "CSU": "?CDUCSU", "SPD": "?SOCIALDEMOCRATICPARTYOFGERMANY",
                    "AfD": "?ALTERNATIVEFORGERMANY", "GRÜNE": "?ALLIANCE90THEGREENS",
                    "Die Linke": "?THELEFT", "FDP": "?FREEDEMOCRATICPARTY",
                    "BSW": "?SAHRAWAGENKNECHTALLIANCE"},
    },
    # Regne Unit: generals del 2024 per nacio i per regio anglesa. Fitxer
    # candidacies.csv de la House of Commons Library (Open Parliament Licence v3),
    # baixat el 03/11/2026 a data/raw/gb/. Irlanda del Nord en gris: els seus
    # partits (DUP, Sinn Fein...) no surten a les enquestes de Gran Bretanya.
    "GB": {
        "adm0": "GBR", "group": "gb", "dir": "gb", "unit_file": "regions.json",
        "bbox": (-8.3, 2.0, 49.8, 60.9),
        "base_file": "ge-2024.json", "loader": "gb",
        "source": "House of Commons Library (Open Parliament Licence v3.0)",
        "codes": {
            "Scotland": "SCT", "Wales": "WLS", "Northern Ireland": "NIR",
            "Greater London": "LDN", "North West": "NW", "North East": "NE",
            "Yorkshire and the Humber": "YH", "East Midlands": "EM", "West Midlands": "WM",
            "East": "EE", "South East": "SE", "South West": "SW",
        },
        "names": {"Scotland": "Escòcia", "Wales": "Gal·les", "Northern Ireland": "Irlanda del Nord",
                  "Greater London": "Londres", "North West": "North West", "North East": "North East",
                  "Yorkshire and the Humber": "Yorkshire and the Humber",
                  "East Midlands": "East Midlands", "West Midlands": "West Midlands",
                  "East": "East of England", "South East": "South East", "South West": "South West"},
        "csv_regions": {"London": "LDN", "North West": "NW", "North East": "NE",
                        "Yorkshire and The Humber": "YH", "East Midlands": "EM",
                        "West Midlands": "WM", "East of England": "EE", "South East": "SE",
                        "South West": "SW"},
        "parties": {"Lab": "?LABOURPARTY", "Con": "?CONSERVATIVEPARTY", "RUK": "?REFORMUK",
                    "LD": "?LIBERALDEMOCRATS", "Green": "?GREENPARTIESINTHEUNITEDKINGDOM",
                    "SNP": "?SCOTTISHNATIONALPARTY", "PC": "?PLAIDCYMRU"},
    },
    # Paisos Baixos: Tweede Kamer 2025 per provincia. TK2025_uitslag.csv de la
    # Kiesraad (data.overheid.nl, CC0), baixat el 03/11/2026 a data/raw/nl/.
    "NL": {
        "adm0": "NLD", "group": "name", "dir": "nl", "unit_file": "provincies.json",
        "bbox": (3.2, 7.3, 50.7, 53.6),
        "base_file": "tk-2025.json", "loader": "nl",
        "source": "Kiesraad, via data.overheid.nl (CC0)",
        "codes": {"Groningen": "P20", "Friesland": "P21", "Drenthe": "P22", "Overijssel": "P23",
                  "Flevoland": "P24", "Gelderland": "P25", "Utrecht": "P26", "Noord-Holland": "P27",
                  "Zuid-Holland": "P28", "Zeeland": "P29", "Noord-Brabant": "P30", "Limburg": "P31"},
        "names": {"Friesland": "Fryslân"},
        "parties": {"D66": "?DEMOCRATS66", "PVV (Partij voor de Vrijheid)": "?PARTYFORFREEDOM",
                    "VVD": "?PEOPLESPARTYFORFREEDOMANDDEMOCRACY",
                    # GroenLinks-PvdA es ara Progressief Nederland: la seva base.
                    "GROENLINKS / Partij van de Arbeid (PvdA)": "?PROGRESSIEFNEDERLAND",
                    "CDA": "?CHRISTIANDEMOCRATICAPPEAL", "JA21": "?JA21",
                    "Forum voor Democratie": "?FORUMFORDEMOCRACY", "BBB": "?FARMERCITIZENMOVEMENT",
                    "DENK": "?DENK", "Staatkundig Gereformeerde Partij (SGP)": "?REFORMEDPOLITICALPARTY",
                    "Partij voor de Dieren": "?PARTYFORTHEANIMALS", "ChristenUnie": "?CHRISTIANUNION",
                    "SP (Socialistische Partij)": "?SOCIALISTPARTY", "50PLUS": "?50PLUS",
                    "Volt": "?VOLTNETHERLANDS"},
    },
    # Australia: Cambra de Representants 2025, primeres preferencies per estat.
    # Fitxer de l'AEC (CC BY 4.0), baixat el 03/11/2026 a data/raw/au/. La LNP de
    # Queensland i el CLP del Territori del Nord, amb els liberals.
    "AU": {
        "adm0": "AUS", "group": "name", "dir": "au", "unit_file": "states.json",
        "bbox": (112.5, 154.0, -44.0, -9.8),
        "base_file": "house-2025.json", "loader": "au",
        "source": "Australian Electoral Commission (CC BY 4.0)",
        "codes": {"New South Wales": "NSW", "Victoria": "VIC", "Queensland": "QLD",
                  "Western Australia": "WA", "South Australia": "SA", "Tasmania": "TAS",
                  "Australian Capital Territory": "ACT", "Northern Territory": "NT"},
        "parties": {"ALP": "?AUSTRALIANLABORPARTY", "LP": "?LIBERALPARTYOFAUSTRALIA",
                    "LNP": "?LIBERALPARTYOFAUSTRALIA", "CLP": "?LIBERALPARTYOFAUSTRALIA",
                    "NP": "?NATIONALPARTYOFAUSTRALIA", "GRN": "?AUSTRALIANGREENS",
                    "ON": "?ONENATION"},
    },
}

# Paisos amb la base llegida de l'article de Wikipedia de l'ultima eleccio
# (geo/wikiresults.py, CC BY-SA 4.0). `units`: {codi: (nom a la taula de
# Wikipedia, [noms a Natural Earth], nom que es mostra)}.
_JP = ["Aichi", "Akita", "Aomori", "Chiba", "Ehime", "Fukui", "Fukuoka", "Fukushima", "Gifu",
       "Gunma", "Hiroshima", "Hokkaidō", "Hyōgo", "Ibaraki", "Ishikawa", "Iwate", "Kagawa",
       "Kagoshima", "Kanagawa", "Kumamoto", "Kyōto", "Kōchi", "Mie", "Miyagi", "Miyazaki",
       "Nagano", "Nagasaki", "Nara", "Niigata", "Okayama", "Okinawa", "Saga", "Saitama", "Shiga",
       "Shimane", "Shizuoka", "Tochigi", "Tokushima", "Tokyo", "Tottori", "Toyama", "Wakayama",
       "Yamagata", "Yamaguchi", "Yamanashi", "Ōita", "Ōsaka"]
_NO = ["Østfold", "Akershus", "Oslo", "Hedmark", "Oppland", "Buskerud", "Vestfold", "Telemark",
       "Aust-Agder", "Vest-Agder", "Rogaland", "Hordaland", "Sogn og Fjordane", "Møre og Romsdal",
       "Sør-Trøndelag", "Nord-Trøndelag", "Nordland", "Troms", "Finnmark"]


def _ascii(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


WIKI = {
    "AT": {"adm0": "AUT", "dir": "at", "bbox": (9.4, 17.3, 46.3, 49.1),
           "page": "2024 Austrian legislative election", "match": "results by state",
           "label": "Nationalratswahl 2024",
           "units": {"B": ("Burgenland", ["Burgenland"], "Burgenland"),
                     "K": ("Carinthia", ["Kärnten"], "Kärnten"),
                     "NO": ("Lower Austria", ["Niederösterreich"], "Niederösterreich"),
                     "OO": ("Upper Austria", ["Oberösterreich"], "Oberösterreich"),
                     "S": ("Salzburg", ["Salzburg"], "Salzburg"),
                     "ST": ("Styria", ["Steiermark"], "Steiermark"),
                     "T": ("Tyrol", ["Tirol"], "Tirol"),
                     "V": ("Vorarlberg", ["Vorarlberg"], "Vorarlberg"),
                     "W": ("Vienna", ["Wien"], "Wien")}},
    "SK": {"adm0": "SVK", "dir": "sk", "bbox": (16.8, 22.6, 47.7, 49.65),
           "page": "2023 Slovak parliamentary election", "match": "by region",
           "units": {"BA": ("Bratislava Region", ["Bratislavský"], "Bratislava"),
                     "TT": ("Trnava Region", ["Trnavský"], "Trnava"),
                     "TN": ("Trenčín Region", ["Trenciansky"], "Trenčín"),
                     "NR": ("Nitra Region", ["Nitriansky"], "Nitra"),
                     "ZA": ("Žilina Region", ["Žilinský"], "Žilina"),
                     "BB": ("Banská Bystrica Region", ["Banskobystrický"], "Banská Bystrica"),
                     "PO": ("Prešov Region", ["Prešov"], "Prešov"),
                     "KE": ("Košice Region", ["Košický"], "Košice")}},
    "NO": {"adm0": "NOR", "dir": "no", "bbox": (4.4, 31.3, 57.9, 71.3),
           "page": "2025 Norwegian parliamentary election", "match": "results by constituency",
           "units": {_ascii(n).upper().replace(" ", "")[:6]: (n, [n], n) for n in _NO}},
    "FI": {"adm0": "FIN", "dir": "fi", "bbox": (20.4, 31.7, 59.7, 70.1),
           "page": "2023 Finnish parliamentary election", "match": "by electoral district",
           # Les circumscripcions agrupen regions. Hel.sinki es una circumscripcio
           # dins de la regio d'Uusimaa: el mapa pinta Uusimaa amb la resta de la
           # regio i Hel.sinki surt nomes a la taula.
           "units": {"UUS": ("Uusimaa", ["Uusimaa"], "Uusimaa"),
                     "VS": ("Varsinais-Suomi", ["Finland Proper"], "Varsinais-Suomi"),
                     "SAT": ("Satakunta", ["Satakunta"], "Satakunta"),
                     "HAM": ("Häme", ["Tavastia Proper", "Päijät-Häme"], "Häme"),
                     "PIR": ("Pirkanmaa", ["Pirkanmaa"], "Pirkanmaa"),
                     "KS": ("Southeast Finland", ["Kymenlaakso", "South Karelia"], "Kaakkois-Suomi"),
                     "SK": ("Savo-Karelia", ["North Karelia", "Northern Savonia", "Southern Savonia"],
                            "Savo-Karjala"),
                     "VAA": ("Vaasa", ["Ostrobothnia", "Southern Ostrobothnia", "Central Ostrobothnia"],
                             "Vaasa"),
                     "KSU": ("Central Finland", ["Central Finland"], "Keski-Suomi"),
                     "OUL": ("Oulu", ["Northern Ostrobothnia", "Kainuu"], "Oulu"),
                     "LAP": ("Lapland", ["Lapland"], "Lappi")}},
    "JP": {"adm0": "JPN", "dir": "jp", "bbox": (128.0, 146.2, 30.0, 45.6),
           "page": "2026 Japanese general election", "match": "by prefecture",
           # Okinawa queda fora del marc: el mapa el deixa de banda, la taula no.
           "units": {_ascii(n).upper()[:4] + str(i): (_ascii(n), [n], _ascii(n))
                     for i, n in enumerate(_JP)}},
    "PL": {"adm0": "POL", "dir": "pl", "bbox": (14.1, 24.2, 49.0, 54.9),
           "page": "2023 Polish parliamentary election", "match": "by constituency",
           # 41 circumscripcions del Sejm agrupades en els 16 voivodats.
           "units": {"DS": (["Legnica", "Wałbrzych", "Wrocław"], ["Lower Silesian"], "Dolnośląskie"),
                     "KP": (["Bydgoszcz", "Toruń"], ["Kuyavian-Pomeranian"], "Kujawsko-Pomorskie"),
                     "LU": (["Lublin", "Chełm"], ["Lublin"], "Lubelskie"),
                     "LB": (["Zielona Góra"], ["Lubusz"], "Lubuskie"),
                     "LD": (["Łódź", "Piotrków Trybunalski", "Sieradz"], ["Łódź"], "Łódzkie"),
                     "MA": (["Kraków I", "Kraków II", "Nowy Sącz", "Tarnów"], ["Lesser Poland"],
                            "Małopolskie"),
                     "MZ": (["Płock", "Radom", "Siedlce", "Warsaw I", "Warsaw II"], ["Masovian"],
                            "Mazowieckie"),
                     "OP": (["Opole"], ["Opole"], "Opolskie"),
                     "PK": (["Krosno", "Rzeszów"], ["Subcarpathian"], "Podkarpackie"),
                     "PD": (["Białystok"], ["Podlachian"], "Podlaskie"),
                     "PM": (["Gdańsk", "Słupsk"], ["Pomeranian"], "Pomorskie"),
                     "SL": (["Bielsko-Biała I", "Bielsko-Biała II", "Częstochowa", "Katowice I",
                             "Katowice II", "Katowice III"], ["Silesian"], "Śląskie"),
                     "SK": (["Kielce"], ["Świętokrzyskie"], "Świętokrzyskie"),
                     "WN": (["Elbląg", "Olsztyn"], ["Warmian-Masurian"], "Warmińsko-Mazurskie"),
                     "WP": (["Kalisz", "Konin", "Piła", "Poznań"], ["Greater Poland"], "Wielkopolskie"),
                     "ZP": (["Koszalin", "Szczecin"], ["West Pomeranian"], "Zachodniopomorskie")}},
    "PT": {"adm0": "PRT", "dir": "pt", "bbox": (-9.6, -6.1, 36.9, 42.2),
           "page": "2025 Portuguese legislative election", "match": "distribution by constituency",
           # Les enquestes fan servir les sigles; la taula de resultats, el nom sencer.
           "alias": {"?DEMOCRATICALLIANCE": "?AD", "?CHEGA": "?CH", "?SOCIALISTPARTY": "?PS",
                     "?LIBERALINITIATIVE": "?IL", "?DEMOCRATICUNITYCOALITION": "?CDU",
                     "?LEFTBLOC": "?BE", "?PEOPLEANIMALSNATURE": "?PAN"},
           # Acores i Madeira queden fora del marc: surten a la taula, no al mapa.
           "units": {_ascii(ne).upper().replace(" ", "")[:6]: (w, [ne], {"Azores": "Açores"}.get(ne, ne)) for w, ne in [
               ("Aveiro", "Aveiro"), ("Beja", "Beja"), ("Braga", "Braga"), ("Bragança", "Bragança"),
               ("Castelo Branco", "Castelo Branco"), ("Coimbra", "Coimbra"), ("Évora", "Évora"),
               ("Faro", "Faro"), ("Guarda", "Guarda"), ("Leiria", "Leiria"), ("Lisbon", "Lisboa"),
               ("Portalegre", "Portalegre"), ("Porto", "Porto"), ("Santarém", "Santarém"),
               ("Setúbal", "Setúbal"), ("Viana do Castelo", "Viana do Castelo"),
               ("Vila Real", "Vila Real"), ("Viseu", "Viseu"), ("Azores", "Azores"),
               ("Madeira", "Madeira")]}},
    "SE": {"adm0": "SWE", "dir": "se", "bbox": (10.9, 24.2, 55.3, 69.1),
           "page": "2026 Swedish general election", "match": "results by constituency",
           "alias": {"?SOCIALDEMOCRATS": "?SWEDISHSOCIALDEMOCRATICPARTY"},
           # Estocolm, Escania i Västra Götaland tenen mes d'una circumscripcio.
           "units": {"AB": (["Stockholm Municipality", "Stockholm County"], ["Stockholm"], "Stockholm"),
                     "C": ("Uppsala", ["Uppsala"], "Uppsala"),
                     "D": ("Södermanland", ["Södermanland"], "Södermanland"),
                     "E": ("Östergötland", ["Östergötland"], "Östergötland"),
                     "F": ("Jönköping", ["Jönköping"], "Jönköping"),
                     "G": ("Kronoberg", ["Kronoberg"], "Kronoberg"),
                     "H": ("Kalmar", ["Kalmar"], "Kalmar"),
                     "I": ("Gotland", ["Gotland"], "Gotland"),
                     "K": ("Blekinge", ["Blekinge"], "Blekinge"),
                     "M": (["Malmö Municipality", "Skåne W", "Skåne S", "Skåne NE"], ["Skåne"], "Skåne"),
                     "N": ("Halland", ["Halland"], "Halland"),
                     "O": (["Göteborg Municipality", "Västra Götaland W", "Västra Götaland N",
                            "Västra Götaland S", "Västra Götaland E"], ["Västra Götaland"],
                           "Västra Götaland"),
                     "S": ("Värmland", ["Värmland"], "Värmland"),
                     "T": ("Örebro", ["Orebro"], "Örebro"),
                     "U": ("Västmanland", ["Västmanland"], "Västmanland"),
                     "W": ("Dalarna", ["Dalarna"], "Dalarna"),
                     "X": ("Gävleborg", ["Gävleborg"], "Gävleborg"),
                     "Y": ("Västernorrland", ["Västernorrland"], "Västernorrland"),
                     "Z": ("Jämtland", ["Jämtland"], "Jämtland"),
                     "AC": ("Västerbotten", ["Västerbotten"], "Västerbotten"),
                     "BD": ("Norrbotten", ["Norrbotten"], "Norrbotten")}},
    "CZ": {"adm0": "CZE", "dir": "cz", "bbox": (12.0, 18.9, 48.5, 51.1),
           "page": "2025 Czech parliamentary election", "match": "results by region",
           "alias": {"?ANO2011": "?ANO", "?MAYORSANDINDEPENDENTS": "?STAN",
                     "?CZECHPIRATEPARTY": "?PIRATI", "?FREEDOMANDDIRECTDEMOCRACY": "?SPD"},
           "units": {"PHA": ("Prague", ["Prague"], "Praha"),
                     "STC": ("Central Bohemia", ["Středočeský"], "Středočeský"),
                     "JHC": ("South Bohemia", ["Jihočeský"], "Jihočeský"),
                     "PLK": ("Plzeň", ["Plzeňský"], "Plzeňský"),
                     "KVK": ("Karlovy Vary", ["Karlovarský"], "Karlovarský"),
                     "ULK": ("Ústí nad Labem", ["Ústecký"], "Ústecký"),
                     "LBK": ("Liberec", ["Liberecký"], "Liberecký"),
                     "HKK": ("Hradec Králové", ["Královéhradecký"], "Královéhradecký"),
                     "PAK": ("Pardubice", ["Pardubický"], "Pardubický"),
                     "VYS": ("Vysočina", ["Vysočina"], "Vysočina"),
                     "JHM": ("South Moravia", ["Jihomoravský"], "Jihomoravský"),
                     "OLK": ("Olomouc", ["Olomoucký"], "Olomoucký"),
                     "ZLK": ("Zlín", ["Zlínský"], "Zlínský"),
                     "MSK": ("Moravia-Silesia", ["Moravskoslezský"], "Moravskoslezský")}},
    "HU": {"adm0": "HUN", "dir": "hu", "bbox": (16.1, 22.9, 45.7, 48.6),
           "page": "2026 Hungarian parliamentary election",
           "match": "party list results by county",
           "alias": {"?TISZAPARTY": "?TISZA", "?DEMOCRATICCOALITION": "?DK",
                     "?HUNGARIANTWOTAILEDDOGPARTY": "?MKKP"},
           # Natural Earth separa les ciutats amb rang de comtat: van amb el seu comtat.
           "units": {"BK": ("Bács-Kiskun", ["Bács-Kiskun", "Kecskemét"], "Bács-Kiskun"),
                     "BA": ("Baranya", ["Baranya", "Pécs"], "Baranya"),
                     "BE": ("Békés", ["Békés", "Békéscsaba"], "Békés"),
                     "BZ": ("Borsod–Abaúj–Zemplén", ["Borsod-Abaúj-Zemplén", "Miskolc"],
                            "Borsod-Abaúj-Zemplén"),
                     "BU": ("Budapest", ["Budapest"], "Budapest"),
                     "CS": ("Csongrád-Csanád", ["Csongrád", "Szeged", "Hódmezôvásárhely"],
                            "Csongrád-Csanád"),
                     "FE": ("Fejér", ["Fejér", "Székesfehérvár", "Dunaújváros"], "Fejér"),
                     "GS": ("Győr–Moson–Sopron", ["Gyor-Moson-Sopron", "Gyôr", "Sopron"],
                            "Győr-Moson-Sopron"),
                     "HB": ("Hajdú–Bihar", ["Hajdú-Bihar", "Debrecen"], "Hajdú-Bihar"),
                     "HE": ("Heves", ["Heves", "Eger"], "Heves"),
                     "JN": ("Jász–Nagykun–Szolnok", ["Jász-Nagykun-Szolnok", "Szolnok"],
                            "Jász-Nagykun-Szolnok"),
                     "KE": ("Komárom-Esztergom", ["Komárom-Esztergom", "Tatabánya"],
                            "Komárom-Esztergom"),
                     "NO": ("Nógrád", ["Nógrád", "Salgótarján"], "Nógrád"),
                     "PE": ("Pest", ["Pest", "Érd"], "Pest"),
                     "SO": ("Somogy", ["Somogy", "Kaposvár"], "Somogy"),
                     "SZ": ("Szabolcs-Szatmár-Bereg", ["Szabolcs-Szatmár-Bereg", "Nyíregyháza"],
                            "Szabolcs-Szatmár-Bereg"),
                     "TO": ("Tolna", ["Tolna", "Szekszárd"], "Tolna"),
                     "VA": ("Vas", ["Vas", "Szombathely"], "Vas"),
                     "VE": ("Veszprém", ["Veszprém"], "Veszprém"),
                     "ZA": ("Zala", ["Zala", "Zalaegerszeg", "Nagykanizsa"], "Zala")}},
    "GR": {"adm0": "GRC", "dir": "gr", "bbox": (19.3, 29.7, 34.7, 41.8),
           "page": "June 2023 Greek legislative election", "match": "by region",
           "alias": {"?ND": "?NEWDEMOCRACY", "?PASOK": "?PASOKMOVEMENTFORCHANGE",
                     "?KKE": "?COMMUNISTPARTYOFGREECE", "?EL": "?GREEKSOLUTION",
                     "?PE": "?COURSEOFFREEDOM"},
           "units": {"ATT": ("Attica", ["Attiki"], "Attiki"),
                     "STE": ("Central Greece", ["Stereá Elláda"], "Sterea Ellada"),
                     "KMA": ("Central Macedonia", ["Kentriki Makedonia"], "Kentriki Makedonia"),
                     "KRI": ("Crete", ["Kriti"], "Kriti"),
                     "AMT": ("Eastern Macedonia and Thrace", ["Anatoliki Makedonia kai Thraki"],
                             "Anatoliki Makedonia kai Thraki"),
                     "IPE": ("Epirus", ["Ipeiros"], "Ipeiros"),
                     "ION": ("Ionian Islands", ["Ionioi Nisoi"], "Ionioi Nisoi"),
                     "VAI": ("North Aegean", ["Voreio Aigaio"], "Voreio Aigaio"),
                     "PEL": ("Peloponnese", ["Peloponnisos"], "Peloponnisos"),
                     "NAI": ("South Aegean", ["Notio Aigaio"], "Notio Aigaio"),
                     "THE": ("Thessaly", ["Thessalia"], "Thessalia"),
                     "DEL": ("Western Greece", ["Dytiki Ellada"], "Dytiki Ellada"),
                     "DMA": ("Western Macedonia", ["Dytiki Makedonia"], "Dytiki Makedonia")}},
    "EE": {"adm0": "EST", "dir": "ee", "bbox": (21.7, 28.3, 57.5, 59.75),
           "page": "2023 Estonian parliamentary election", "match": "results by constituency",
           # 12 circumscripcions sobre 15 comtats. Harju (amb Tallinn) fa la mitjana
           # de les tres de Tallinn i la de la resta de Harju i Rapla; Tartu, la del
           # comtat i la de la ciutat.
           "units": {"HAR": (["No. 1", "No. 2", "No. 3", "No. 4"], ["Harju"], "Harjumaa"),
                     "RAP": ("No. 4", ["Rapla"], "Raplamaa"),
                     "LSH": ("No. 5", ["Hiiu", "Lääne", "Saare"], "Hiiu-, Lääne- ja Saaremaa"),
                     "LVI": ("No. 6", ["Lääne-Viru"], "Lääne-Virumaa"),
                     "IVI": ("No. 7", ["Ida-Viru"], "Ida-Virumaa"),
                     "JVI": ("No. 8", ["Järva", "Viljandi"], "Järva- ja Viljandimaa"),
                     "JOG": ("No. 9", ["Jõgeva"], "Jõgevamaa"),
                     "TAR": (["No. 9", "No. 10"], ["Tartu"], "Tartumaa"),
                     "VVP": ("No. 11", ["Võru", "Valga", "Põlva"], "Võru-, Valga- ja Põlvamaa"),
                     "PAR": ("No. 12", ["Pärnu"], "Pärnumaa")}},
    "IE": {"adm0": "IRL", "dir": "ie", "bbox": (-10.7, -5.9, 51.3, 55.5),
           "page": "2024 Irish general election",
           "match": "first preference votes by constituency",
           # Les enquestes no detallen els independents: van a OTHER, i com que
           # OTHER no te mitjana estatal es queden al seu resultat local del 2024
           # (Kerry, Tipperary...), que es el que val mes no moure a cegues.
           "alias": {"?INDEPENDENTPOLITICIAN": "OTHER"},
           # 43 circumscripcions agrupades en els comtats de Natural Earth.
           "units": {"CK": ("Carlow–Kilkenny", ["Carlow", "Kilkenny"], "Carlow–Kilkenny"),
                     "CM": ("Cavan–Monaghan", ["Cavan", "Monaghan"], "Cavan–Monaghan"),
                     "CE": ("Clare", ["Clare"], "Clare"),
                     "CO": (["Cork East", "Cork North-Central", "Cork North-West",
                             "Cork South-Central", "Cork South-West"], ["Cork"], "Cork"),
                     "DL": ("Donegal", ["Donegal"], "Donegal"),
                     "DC": (["Dublin Bay North", "Dublin Bay South", "Dublin Central",
                             "Dublin North-West", "Dublin South-Central"], ["Dublin"], "Dublin City"),
                     "FG": (["Dublin Fingal East", "Dublin Fingal West", "Dublin West"], ["Fingal"],
                            "Fingal"),
                     "SD": (["Dublin Mid-West", "Dublin South-West"], ["South Dublin"], "South Dublin"),
                     "DR": (["Dún Laoghaire", "Dublin Rathdown"], ["Dún Laoghaire–Rathdown"],
                            "Dún Laoghaire–Rathdown"),
                     "G": (["Galway East", "Galway West"], ["Galway"], "Galway"),
                     "KY": ("Kerry", ["Kerry"], "Kerry"),
                     "KE": (["Kildare North", "Kildare South"], ["Kildare"], "Kildare"),
                     "LS": ("Laois", ["Laoighis"], "Laois"),
                     "OY": ("Offaly", ["Offaly"], "Offaly"),
                     "L": (["Limerick City", "Limerick County"], ["Limerick"], "Limerick"),
                     "LW": ("Longford–Westmeath", ["Longford", "Westmeath"], "Longford–Westmeath"),
                     "LH": ("Louth", ["Louth"], "Louth"),
                     "MO": ("Mayo", ["Mayo"], "Mayo"),
                     "MH": (["Meath East", "Meath West"], ["Meath"], "Meath"),
                     "RN": ("Roscommon–Galway", ["Roscommon"], "Roscommon"),
                     "SL": ("Sligo–Leitrim", ["Sligo", "Leitrim"], "Sligo–Leitrim"),
                     "TN": ("Tipperary North", ["North Tipperary"], "Tipperary North"),
                     "TS": ("Tipperary South", ["South Tipperary"], "Tipperary South"),
                     "W": ("Waterford", ["Waterford"], "Waterford"),
                     "WX": (["Wexford", "Wicklow–Wexford"], ["Wexford"], "Wexford"),
                     "WW": (["Wicklow", "Wicklow–Wexford"], ["Wicklow"], "Wicklow")}},
}


def _wiki_spec(country):
    w = WIKI[country]
    codes = {ne: code for code, (_wn, nes, _dn) in w["units"].items() for ne in nes}
    names = {ne: w["units"][code][2] for ne, code in codes.items()}
    return {"adm0": w["adm0"], "group": "name", "dir": w["dir"], "unit_file": "units.json",
            "bbox": w["bbox"], "base_file": "base.json", "loader": "wiki", "codes": codes,
            "names": names, "wiki": w,
            "source": f"Wikipedia, «{w['page']}» (CC BY-SA 4.0)"}


def _clean(v):
    if not isinstance(v, str):
        return v
    v = v.replace("\0", "").strip()
    try:
        return v.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return v


def _projector(bbox):
    lon0, lon1, lat0, lat1 = bbox
    k = math.cos(math.radians((lat0 + lat1) / 2))
    scale = WIDTH / ((lon1 - lon0) * k)

    def xy(lon, lat):
        return (round((lon - lon0) * k * scale, 1), round((lat1 - lat) * scale, 1))
    return xy, round((lat1 - lat0) * scale, 1)


def _path(rings, xy):
    parts = []
    for ring in rings:
        pts = []
        for lon, lat in ring:
            p = xy(lon, lat)
            if not pts or p != pts[-1]:
                pts.append(p)
        if len(set(pts)) < 3:
            continue
        x0, y0 = pts[0]
        seg = [f"M{x0:g} {y0:g}l"]
        for x, y in pts[1:]:
            seg.append(f"{round(x - x0, 1):g} {round(y - y0, 1):g}")
            x0, y0 = x, y
        parts.append(seg[0] + " ".join(seg[1:]) + "z")
    return "".join(parts)


def geometry(spec, admin1: Path):
    rows = _dbf(Path(str(admin1) + ".dbf").read_bytes())
    shapes = _shp(Path(str(admin1) + ".shp").read_bytes())
    xy, height = _projector(spec["bbox"])
    lon0, lon1, lat0, lat1 = spec["bbox"]

    def inside(ring):
        # Illots fora del marc (Rockall, a 300 km d'Escocia) estiraven el mapa.
        return any(lon0 <= x <= lon1 and lat0 <= y <= lat1 for x, y in ring)

    rings = {}
    for row, shape in zip(rows, shapes):
        if _clean(row.get("adm0_a3")) != spec["adm0"]:
            continue
        if spec["group"] == "gb":
            # Escocia, Gal.les i Irlanda del Nord senceres; Anglaterra per regions.
            nation = _clean(row.get("geonunit"))
            key = _clean(row.get("region")) if nation == "England" else nation
        else:
            key = _clean(row.get(spec["group"]))
        code = spec["codes"].get(key)
        if code:
            rings.setdefault(code, {"n": spec.get("names", {}).get(key, key), "r": []})["r"] += [
                r for r in shape if inside(r)]
    out = {code: {"n": v["n"], "d": _path(v["r"], xy)} for code, v in rings.items()}
    return {"w": WIDTH, "h": height, "dep": out}


def _shares(votes):
    """{territori: {partit: vots}} -> ({territori: {partit: %}}, {territori: valids})."""
    valid = {u: sum(v.values()) for u, v in votes.items()}
    return ({u: {p: round(100 * n / valid[u], 3) for p, n in v.items()} for u, v in votes.items()},
            valid)


def _load_de(spec):
    import csv
    path = ROOT / "data" / "raw" / "de" / "btw25_kerg2.csv"
    rows = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines(), delimiter=";"))
    head = next(i for i, r in enumerate(rows) if r and r[0] == "Wahlart")
    cols = {name: i for i, name in enumerate(rows[head])}
    votes, national = {}, {}
    for r in rows[head + 1:]:
        if len(r) < len(cols) or r[cols["Gruppenart"]] != "Partei" or r[cols["Stimme"]] != "2":
            continue
        n = int(r[cols["Anzahl"]] or 0)
        party = spec["parties"].get(r[cols["Gruppenname"]], "OTHER")
        kind, num = r[cols["Gebietsart"]], r[cols["Gebietsnummer"]]
        if kind == "Land":
            votes.setdefault(num, {}).setdefault(party, 0)
            votes[num][party] += n
        elif kind == "Bund":
            national[party] = national.get(party, 0) + n
    deps, valid = _shares(votes)
    nat, _ = _shares({"all": national})
    return deps, valid, nat["all"]


def _load_gb(spec):
    import csv
    path = ROOT / "data" / "raw" / "gb" / "ge2024_candidacies.csv"
    votes, national = {}, {}
    nations = {"Scotland": "SCT", "Wales": "WLS", "Northern Ireland": "NIR"}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            unit = nations.get(row["Country name"]) or spec["csv_regions"].get(row["English region name"])
            if not unit:
                continue
            n = int(row["Candidate vote count"] or 0)
            party = spec["parties"].get(row["Main party abbreviation"], "OTHER")
            if unit != "NIR":
                votes.setdefault(unit, {}).setdefault(party, 0)
                votes[unit][party] += n
            national[party] = national.get(party, 0) + n
    deps, valid = _shares(votes)
    nat, _ = _shares({"all": national})
    return deps, valid, nat["all"]


def _load_nl(spec):
    import csv
    path = ROOT / "data" / "raw" / "nl" / "x" / "TK2025_uitslag.csv"
    votes, national = {}, {}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            if row["VeldType"] != "LijstAantalStemmen":
                continue
            code, n = row["RegioCode"], int(row["Waarde"] or 0)
            party = spec["parties"].get(row["LijstNaam"], "OTHER")
            if code.startswith("P") and code != "P99":
                votes.setdefault(code, {}).setdefault(party, 0)
                votes[code][party] += n
            elif code.startswith("L"):
                national[party] = national.get(party, 0) + n
    deps, valid = _shares(votes)
    nat, _ = _shares({"all": national})
    return deps, valid, nat["all"]


def _load_au(spec):
    import csv
    path = ROOT / "data" / "raw" / "au" / "HouseFirstPrefsByStateByPartyDownload-31496.csv"
    lines = path.read_text(encoding="utf-8-sig").splitlines()[1:]      # la 1a es un titol
    votes, national = {}, {}
    for row in csv.DictReader(lines):
        n = int(row["TotalVotes"] or 0)
        party = spec["parties"].get(row["PartyAb"], "OTHER")
        votes.setdefault(row["StateAb"], {}).setdefault(party, 0)
        votes[row["StateAb"]][party] += n
        national[party] = national.get(party, 0) + n
    deps, valid = _shares(votes)
    nat, _ = _shares({"all": national})
    return deps, valid, nat["all"]


def _load_wiki(spec):
    from .wikiresults import region_table
    w = spec["wiki"]
    rows, total, _title = region_table(w["page"], w["match"], w["cc"])
    alias = w.get("alias") or {}

    def rename(shares):
        out = {}
        for p, v in (shares or {}).items():
            out[alias.get(p, p)] = out.get(alias.get(p, p), 0) + v
        return out

    by_name = {}
    for k, v in rows.items():
        key = _ascii(k).lower()
        by_name[key] = v
        # Polonia numera les circumscripcions: "19 – Warsaw I".
        by_name.setdefault(re.sub(r"^\d+\s*[-–]\s*", "", key), v)
    deps = {}
    for code, (wiki_name, _nes, _dn) in w["units"].items():
        names = wiki_name if isinstance(wiki_name, (list, tuple)) else [wiki_name]
        got = [by_name[_ascii(n).lower()] for n in names if _ascii(n).lower() in by_name]
        if not got:
            continue
        # Territoris amb mes d'una circumscripcio (Escania, Varsovia...): la taula
        # nomes porta %, no vots, aixi que es fa la mitjana simple.
        parties = {p for g in got for p in g}
        deps[code] = rename({p: round(sum(g.get(p, 0) for g in got) / len(got), 2) for p in parties})
    return deps, {}, rename(total) if total else None


def baseline(spec, conn):
    """{territori: {partit: %}} i el total estatal de l'eleccio de base."""
    if spec.get("loader") == "wiki":
        deps, valid, national = _load_wiki(spec)
        return {"national": national, "dep": deps, "valid": valid, "source": spec["source"]}
    loaders = {"de": _load_de, "gb": _load_gb, "nl": _load_nl, "au": _load_au}
    if spec.get("loader") in loaders:
        deps, valid, national = loaders[spec["loader"]](spec)
        return {"national": national, "dep": deps, "valid": valid, "source": spec["source"]}
    deps, valid = {}, {}
    for code, party, v, val in conn.execute(
            """SELECT code, party, votes, valid_votes FROM election_result
               WHERE election = ? AND level = ?""", (spec["election"], spec["level"])):
        if not val:
            continue
        deps.setdefault(code, {})[party] = round(100 * (v or 0) / val, 3)
        valid[code] = val
    national = {r[0]: round(100 * r[1] / r[2], 3) for r in conn.execute(
        """SELECT party, votes, valid_votes FROM election_result
           WHERE election = ? AND level = 'national'""", (spec["election"],)) if r[2]}
    return {"election": spec["election"], "national": national, "dep": deps, "valid": valid,
            "source": spec["source"]}


def build(country: str, admin1: Path):
    if country in WIKI:
        WIKI[country]["cc"] = country
        spec = _wiki_spec(country)
    else:
        spec = SPECS[country]
    out = ROOT / "web" / spec["dir"]
    out.mkdir(parents=True, exist_ok=True)
    geo = geometry(spec, admin1)
    (out / spec["unit_file"]).write_text(json.dumps(geo, separators=(",", ":"), ensure_ascii=False),
                                         encoding="utf-8")
    base = baseline(spec, sqlite3.connect(ROOT / "data" / "politbureau.db"))
    (out / spec["base_file"]).write_text(json.dumps(base, separators=(",", ":"), ensure_ascii=False),
                                         encoding="utf-8")
    missing = sorted(set(geo["dep"]) - set(base["dep"]))
    return len(geo["dep"]), len(base["dep"]), missing


if __name__ == "__main__":
    print(build(sys.argv[1], Path(sys.argv[2])))
