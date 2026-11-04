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
    "DK": {
        "adm0": "DNK", "group": "name", "dir": "dk", "unit_file": "units.json",
        "bbox": (7.9, 15.3, 54.5, 57.8),
        "base_file": "base.json", "loader": "dk",
        "source": "Danmarks Statistik, taula FVKOM (CC BY 4.0)",
        "codes": {"Hovedstaden": "84", "Sjaælland": "85", "Syddanmark": "83", "Midtjylland": "82",
                  "Nordjylland": "81"},
        "names": {"Sjaælland": "Sjælland"},
        # Lletra de llista -> codi de les enquestes. La resta (D, E, K, P, Q i
        # independents) va a OTHER.
        "parties": {"A": "?SOCIALDEMOCRATS", "B": "?DANISHSOCIALLIBERALPARTY",
                    "C": "?CONSERVATIVEPEOPLESPARTY", "F": "?GREENLEFT", "H": "?CITIZENSPARTY",
                    "I": "?LIBERALALLIANCE", "M": "?MODERATES", "O": "?DANISHPEOPLESPARTY",
                    "V": "?VENSTRE", "Æ": "?DENMARKDEMOCRATS", "Ø": "?REDGREENALLIANCE",
                    "Å": "?THEALTERNATIVE"},
    },
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

_TH = ['Amnat Charoen', 'Ang Thong', 'Bangkok Metropolis', 'Bueng Kan', 'Buri Ram',
       'Chachoengsao', 'Chai Nat', 'Chaiyaphum', 'Chanthaburi', 'Chiang Mai', 'Chiang Rai',
       'Chon Buri', 'Chumphon', 'Kalasin', 'Kamphaeng Phet', 'Kanchanaburi', 'Khon Kaen',
       'Krabi', 'Lampang', 'Lamphun', 'Loei', 'Lop Buri', 'Mae Hong Son', 'Maha Sarakham',
       'Mukdahan', 'Nakhon Nayok', 'Nakhon Pathom', 'Nakhon Phanom', 'Nakhon Ratchasima',
       'Nakhon Sawan', 'Nakhon Si Thammarat', 'Nan', 'Narathiwat', 'Nong Bua Lam Phu',
       'Nong Khai', 'Nonthaburi', 'Pathum Thani', 'Pattani', 'Phangnga', 'Phatthalung', 'Phayao',
       'Phetchabun', 'Phetchaburi', 'Phichit', 'Phitsanulok', 'Phra Nakhon Si Ayutthaya',
       'Phrae', 'Phuket', 'Prachin Buri', 'Prachuap Khiri Khan', 'Ranong', 'Ratchaburi',
       'Rayong', 'Roi Et', 'Sa Kaeo', 'Sakon Nakhon', 'Samut Prakan', 'Samut Sakhon',
       'Samut Songkhram', 'Saraburi', 'Satun', 'Si Sa Ket', 'Sing Buri', 'Songkhla', 'Sukhothai',
       'Suphan Buri', 'Surat Thani', 'Surin', 'Tak', 'Trang', 'Trat', 'Ubon Ratchathani',
       'Udon Thani', 'Uthai Thani', 'Uttaradit', 'Yala', 'Yasothon']
# Natural Earth -> taula de Wikipedia, on la grafia no coincideix.
_TH_WIKI = {"Bangkok Metropolis": "Bangkok", "Buri Ram": "Buriram", "Chon Buri": "Chonburi",
            "Lop Buri": "Lopburi", "Nong Bua Lam Phu": "Nong Bua Lamphu", "Phangnga": "Phang Nga",
            "Prachin Buri": "Prachinburi", "Si Sa Ket": "Sisaket"}
_MD = ['Briceni', 'Edineţ', 'Rîşcani', 'Glodeni', 'Făleşti', 'Ungheni', 'Nisporeni', 'Hîncesti',
       'Leova', 'Cantemir', 'Cahul', 'Ocniţa', 'Donduseni', 'Soroca', 'Rezina', 'Ștefan Vodă',
       'Causeni', 'Cimişlia', 'Basarabeasca', 'Taraclia', 'Criuleni', 'Străşeni', 'Anenii Noi',
       'Orhei', 'Teleneşti', 'Şoldăneşti', 'Floreşti', 'Ialoveni', 'Călărași', 'Drochia',
       'Sîngerei']
# Grafia romanesa amb coma a sota per als noms que es mostren.
_MD_SHOW = str.maketrans("şţŞŢ", "șțȘȚ")
# Municipis de Natural Earth per circumscripcio (articles «... (National Assembly
# constituency)» de Wikipedia). Ljubljana i Ivancna Gorica en tenen dues.
_SI = {
    "KR": ['Bled', 'Bohinj', 'Cerklje na Gorenjskem', 'Cerkno', 'Gorenja vas-Poljane', 'Idrija',
           'Jesenice', 'Jezersko', 'Kamnik', 'Komenda', 'Kranj', 'Kranjska Gora', 'Naklo',
           'Preddvor', 'Radovljica', 'Tržič', 'Šenčur', 'Škofja Loka', 'Železniki', 'Žiri',
           'Žirovnica'],
    "PO": ['Ajdovščina', 'Bovec', 'Brda', 'Divaca', 'Hrpelje-Kozina', 'Ilirska Bistrica',
           'Izola', 'Kanal', 'Kobarid', 'Komen', 'Koper', 'Miren-Kostanjevica', 'Nova Goriška',
           'Piran', 'Pivka', 'Postojna', 'Sežana', 'Tolmin', 'Vipava', 'Šempeter-Vrtojba'],
    "LC": ['Bloke', 'Borovnica', 'Brezovica', 'Cerknica', 'Dobrova-Polhov Gradec', 'Horjul',
           'Ig', 'Logatec', 'Loška dolina', 'Medvode', 'Velike Lašče', 'Vodice', 'Vrhnika',
           'Škofljica'],
    "LB": ['Dobrepolje', 'Dol pri Ljubljani', 'Domžale', 'Grosuplje', 'Kocevje', 'Kostel',
           'Loški Potok', 'Lukovica', 'Mengeš', 'Moravce', 'Ribnica', 'Sodražica', 'Trzin'],
    "CE": ['Braslovce', 'Celje', 'Dobje', 'Dobrna', 'Dravograd', 'Gornji Grad', 'Ljubno', 'Luce',
           'Mežica', 'Mislinja', 'Mozirje', 'Muta', 'Nazarje', 'Podvelka', 'Polzela', 'Prebold',
           'Prevalje', 'Radlje ob Dravi', 'Ravne na Koroškem', 'Ribnica na Pohorju',
           'Slovenj Gradec', 'Solcava', 'Tabor', 'Velenje', 'Vojnik', 'Vransko', 'Vuzenica',
           'Črna na Koroškem', 'Šentjur pri Celju', 'Šmartno ob Paki', 'Šoštanj', 'Štore',
           'Žalec'],
    "NM": ['Brežice', 'Crnomelj', 'Dolenjske Toplice', 'Hrastnik', 'Krsko', 'Krško', 'Laško',
           'Litija', 'Metlika', 'Mirna Pec', 'Novo Mesto', 'Radece', 'Semic', 'Sevnica',
           'Trbovlje', 'Trebnje', 'Zasavska', 'Šentjernej', 'Škocjan', 'Šmartno in Litiji',
           'Žužemberk'],
    "MB": ['Bistrica ob Sotli', 'Duplek', 'Hoce-Slivnica', 'Kozje', 'Lovrenc na Pohorju',
           'Maribor', 'Miklavž na Dravskem polju', 'Oplotnica', 'Podcetrtek', 'Race-Fram',
           'Rogatec', 'Rogaška Slatina', 'Ruše', 'Selnica ob Dravi', 'Slovenska Bistrica',
           'Slovenske Konjice', 'Starše', 'Vitanje', 'Zrece', 'Šmarje pri Jelšah'],
    "PT": ['Apace', 'Beltinci', 'Benedikt', 'Cankova', 'Cerkvenjak', 'Destrnik', 'Dobrovnik',
           'Dornava', 'Gorišnica', 'Gornja Radgona', 'Gornji Petrovci', 'Grad', 'Hajdina',
           'Hodoš', 'Juršinci', 'Kidricevo', 'Kobilje', 'Križevci', 'Kungota', 'Kuzma', 'Lenart',
           'Lendava', 'Ljutomer', 'Majšperk', 'Markovci', 'Moravske Toplice', 'Murska Sobota',
           'Odranci', 'Ormož', 'Pesnica', 'Podlehnik', 'Ptuj', 'Puconci', 'Radenci', 'Razkrižje',
           'Rogašovci', 'Sveta Ana', 'Sveti Andraž v Slovenskih Goricah', 'Sveti Jurij',
           'Trnovska vas', 'Turnišče', 'Velika Polana', 'Veržej', 'Videm', 'Zavrc', 'Črenšovci',
           'Šalovci', 'Šentilj', 'Žetale'],
}

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
    "TH": {"adm0": "THA", "dir": "th", "bbox": (97.3, 105.7, 5.6, 20.5),
           "page": "2026 Thai general election", "match": "party-list vote by province",
           # El vot de llista (el que es comparable amb les enquestes), no el de districte.
           "units": {_ascii(n).upper().replace(" ", "")[:4] + str(i):
                     (_TH_WIKI.get(n, n), [n], _TH_WIKI.get(n, n)) for i, n in enumerate(_TH)}},
    "IS": {"adm0": "ISL", "dir": "is", "bbox": (-24.6, -13.4, 63.2, 66.6),
           "page": "2024 Icelandic parliamentary election", "match": "by constituency",
           # La taula per circumscripcio no porta total: el de la taula de resultats.
           "national": {"?SOCIALDEMOCRATICALLIANCE": 20.75, "?INDEPENDENCEPARTY": 19.36,
                        "?VIREISN": 15.82, "?PEOPLESPARTY": 13.78, "?CENTREPARTY": 12.10,
                        "?PROGRESSIVEPARTY": 7.80, "?SOCIALISTPARTYOFICELAND": 3.96,
                        "?PIRATEPARTY": 3.02, "?LEFTGREENMOVEMENT": 2.34},
           # 6 circumscripcions sobre 9 regions: Reykjavik fa la mitjana de les dues
           # seves, i la resta de l'area de la capital es la circumscripcio Sud-oest.
           "units": {"RVK": (["Reykjavík North", "Reykjavík South"], ["Reykjavík"], "Reykjavík"),
                     "SV": ("Southwest", ["Höfuðborgarsvæði"], "Suðvestur"),
                     "SU": ("South", ["Suðurnes", "Suðurland"], "Suður"),
                     "NV": ("Northwest", ["Vesturland", "Vestfirðir", "Norðurland vestra"],
                            "Norðvestur"),
                     "NA": ("Northeast", ["Norðurland eystra", "Austurland"], "Norðaustur")}},
    "MD": {"adm0": "MDA", "dir": "md", "bbox": (26.6, 30.2, 45.4, 48.5),
           "page": "2025 Moldovan parliamentary election",
           "match": "results by administrative-territorial units",
           "units": {**{_ascii(n).upper().replace(" ", "")[:4] + str(i): (n, [n], n.translate(_MD_SHOW))
                        for i, n in enumerate(_MD)},
                     "CHI": ("Chișinău Municipality", ["Chişinău"], "Chișinău"),
                     "BAL": ("Bălți Municipality", ["Bălţi"], "Bălți"),
                     "GAG": ("UTA Gagauzia", ["Comrat"], "Găgăuzia"),
                     # Els vots de Transnistria (a col.legis de la riba dreta) en una sola unitat.
                     "TRN": ("Left Bank of the Dniester",
                             ["Transnistria", "Stîngă Nistrului", "Camenca", "Grigoriopol", "Bender"],
                             "Transnistria")}},
    "LU": {"adm0": "LUX", "dir": "lu", "bbox": (5.7, 6.55, 49.4, 50.2),
           "page": "2023 Luxembourg general election", "match": "votes by constituency",
           "pick": "last",
           # Total ponderat (un elector, un vot): el que es comparable amb les enquestes.
           # Dins d'una circumscripcio el % brut i el ponderat son el mateix.
           "national": {"?CHRISTIANSOCIALPEOPLESPARTY": 29.80, "?LUXEMBOURGSOCIALISTWORKERSPARTY": 18.18,
                        "?DEMOCRATICPARTY": 19.13, "?ALTERNATIVEDEMOCRATICREFORMPARTY": 9.54,
                        "?THEGREENS": 8.32, "?PIRATEPARTYLUXEMBOURG": 6.66, "?THELEFT": 3.64,
                        "?FOKUS": 2.57, "?LIBERTEFRAIHEET": 1.23, "?COMMUNISTPARTYOFLUXEMBOURG": 0.54,
                        "?THECONSERVATIVES": 0.21, "?VOLTLUXEMBOURG": 0.17},
           # 3 districtes de Natural Earth: Diekirch es la circumscripcio Nord,
           # Grevenmacher l'Est, i el districte de Luxemburg aplega Centre i Sud.
           "units": {"LUX": (["Centre", "South"], ["Luxembourg"], "Zentrum a Süden"),
                     "DIE": ("North", ["Diekirch"], "Norden"),
                     "GRE": ("East", ["Grevenmacher"], "Osten")}},
    "HR": {"adm0": "HRV", "dir": "hr", "bbox": (13.4, 19.5, 42.35, 46.6),
           "page": "2024 Croatian parliamentary election", "match": "results by constituency",
           # Les circumscripcions (llei del 2023) creuen comtats: cada comtat va a la
           # circumscripcio que en te la major part; Zagreb, el seu comtat, Split i
           # Koprivnica, que se les reparteixen, fan la mitjana.
           "units": {"ZG": (["I", "II", "VI"], ["Grad Zagreb"], "Grad Zagreb"),
                     "ZGZ": (["I", "II", "VI"], ["Zagrebacka"], "Zagrebačka"),
                     "KZ": ("III", ["Krapinsko-Zagorska"], "Krapinsko-zagorska"),
                     "VZ": ("III", ["Varaždinska"], "Varaždinska"),
                     "ME": ("III", ["Medimurska"], "Međimurska"),
                     "BB": ("II", ["Bjelovarsko-bilogorska"], "Bjelovarsko-bilogorska"),
                     "KK": (["II", "IV"], ["Koprivničko-Križevačka"], "Koprivničko-križevačka"),
                     "OB": ("IV", ["Osjecko-Baranjska"], "Osječko-baranjska"),
                     "VP": ("IV", ["Viroviticko-Podravska"], "Virovitičko-podravska"),
                     "VS": ("V", ["Vukovarsko-Srijemska"], "Vukovarsko-srijemska"),
                     # Natural Earth hi te dos poligons amb aquest nom (l'altre es Pozega).
                     "BP": ("V", ["Brodsko-Posavska"], "Brodsko-posavska i Požeško-slavonska"),
                     "SM": ("VII", ["Sisacko-Moslavacka"], "Sisačko-moslavačka"),
                     "KA": ("VII", ["Karlovacka"], "Karlovačka"),
                     "LS": ("VII", ["Licko-Senjska"], "Ličko-senjska"),
                     "PG": ("VIII", ["Primorsko-Goranska"], "Primorsko-goranska"),
                     "IS": ("VIII", ["Istarska"], "Istarska"),
                     "ZD": ("IX", ["Zadarska"], "Zadarska"),
                     "SK": ("IX", ["Šibensko-Kninska"], "Šibensko-kninska"),
                     "SD": (["IX", "X"], ["Splitsko-Dalmatinska"], "Splitsko-dalmatinska"),
                     "DN": ("X", ["Dubrovacko-Neretvanska"], "Dubrovačko-neretvanska")}},
    "SI": {"adm0": "SVN", "dir": "si", "bbox": (13.35, 16.65, 45.4, 46.9),
           "page": "2026 Slovenian parliamentary election", "match": "constituency results",
           "pick": "last",
           "alias": {"?SLOVENSKADEMOKRATSKASTRANKA": "?SLOVENIANDEMOCRATICPARTY"},
           "units": {**{code: (name, _SI[code], name.replace("Mesto", "mesto"))
                        for code, name in (("KR", "Kranj"), ("PO", "Postojna"),
                                           ("LC", "Ljubljana Center"), ("LB", "Ljubljana Bežigrad"),
                                           ("CE", "Celje"), ("NM", "Novo Mesto"),
                                           ("MB", "Maribor"), ("PT", "Ptuj"))},
                     "LJ": (["Ljubljana Center", "Ljubljana Bežigrad"], ["Ljubljana"], "Ljubljana"),
                     "IG": (["Ljubljana Bežigrad", "Novo Mesto"], ["Ivancna Gorica"], "Ivančna Gorica")}},
    "CA": {"adm0": "CAN", "dir": "can", "bbox": (-141.0, -52.6, 41.7, 70.0),
           "page": "2025 Canadian federal election", "match": "results by province",
           "transposed": True, "simplify": 1.5,
           "units": {"BC": ("BC", ["British Columbia"], "British Columbia"),
                     "AB": ("AB", ["Alberta"], "Alberta"),
                     "SK": ("SK", ["Saskatchewan"], "Saskatchewan"),
                     "MB": ("MB", ["Manitoba"], "Manitoba"),
                     "ON": ("ON", ["Ontario"], "Ontario"),
                     "QC": ("QC", ["Québec"], "Québec"),
                     "NB": ("NB", ["New Brunswick"], "New Brunswick"),
                     "NS": ("NS", ["Nova Scotia"], "Nova Scotia"),
                     "PE": ("PE", ["Prince Edward Island"], "Prince Edward Island"),
                     "NL": ("NL", ["Newfoundland and Labrador"], "Newfoundland and Labrador"),
                     "YT": ("YT", ["Yukon"], "Yukon"),
                     "NT": ("NT", ["Northwest Territories"], "Northwest Territories"),
                     "NU": ("NU", ["Nunavut"], "Nunavut")}},
    "KR": {"adm0": "KOR", "dir": "kr", "bbox": (124.6, 131.0, 33.1, 38.7),
           "page": "2025 South Korean presidential election", "match": "by province and city",
           "pick": "last",
           "units": {
                     "SSEO": ("Seoul", ["Seoul"], "Seoul"),
                     "BBUS": ("Busan", ["Busan"], "Busan"),
                     "DDAE": ("Daegu", ["Daegu"], "Daegu"),
                     "IINC": ("Incheon", ["Incheon"], "Incheon"),
                     "GGWA": ("Gwangju", ["Gwangju"], "Gwangju"),
                     "DDJE": ("Daejeon", ["Daejeon"], "Daejeon"),
                     "UULS": ("Ulsan", ["Ulsan"], "Ulsan"),
                     "SSEJ": ("Sejong", ["Sejong"], "Sejong"),
                     "GGYE": ("Gyeonggi", ["Gyeonggi"], "Gyeonggi"),
                     "GGAN": ("Gangwon", ["Gangwon"], "Gangwon"),
                     "NCCHU": ("North Chungcheong", ["North Chungcheong"], "North Chungcheong"),
                     "SCCHU": ("South Chungcheong", ["South Chungcheong"], "South Chungcheong"),
                     "NJJEO": ("North Jeolla", ["North Jeolla"], "North Jeolla"),
                     "SJJEO": ("South Jeolla", ["South Jeolla"], "South Jeolla"),
                     "NGGYE": ("North Gyeongsang", ["North Gyeongsang"], "North Gyeongsang"),
                     "SGGYE": ("South Gyeongsang", ["South Gyeongsang"], "South Gyeongsang"),
                     "JJEJ": ("Jeju", ["Jeju"], "Jeju")}},
    "ID": {"adm0": "IDN", "dir": "id", "bbox": (95.0, 141.1, -11.1, 6.1),
           "page": "2024 Indonesian presidential election", "match": "by province", "pick": "last",
           "name_col": 1,
           "alias": {"?ANIESBASWEDANINDEPENDENT": "?ANIESBASWEDAN",
                     "?PRABOWOSUBIANTOGERINDRA": "?PRABOWOSUBIANTO",
                     "?GANJARPRANOWOPDIP": "?GANJARPRANOWO"},
           # Natural Earth porta les 33 provincies d'abans del 2022: Papua, Papua Barat
           # i Kalimantan Timur fan la mitjana de les provincies que en van sortir.
           "units": {
                     "A0": ("Aceh", ["Aceh"], "Aceh"),
                     "SU1": ("North Sumatra", ["Sumatera Utara"], "Sumatera Utara"),
                     "SB2": ("West Sumatra", ["Sumatera Barat"], "Sumatera Barat"),
                     "R3": ("Riau", ["Riau"], "Riau"),
                     "J4": ("Jambi", ["Jambi"], "Jambi"),
                     "SS5": ("South Sumatra", ["Sumatera Selatan"], "Sumatera Selatan"),
                     "B6": ("Bengkulu", ["Bengkulu"], "Bengkulu"),
                     "L7": ("Lampung", ["Lampung"], "Lampung"),
                     "BB8": ("Bangka Belitung", ["Bangka-Belitung"], "Bangka Belitung"),
                     "KR9": ("Riau Islands", ["Kepulauan Riau"], "Kepulauan Riau"),
                     "B10": ("Banten", ["Banten"], "Banten"),
                     "JR11": ("Jakarta", ["Jakarta Raya"], "Jakarta"),
                     "JB12": ("West Java", ["Jawa Barat"], "Jawa Barat"),
                     "JT13": ("Central Java", ["Jawa Tengah"], "Jawa Tengah"),
                     "Y14": ("Yogyakarta", ["Yogyakarta"], "Yogyakarta"),
                     "JT15": ("East Java", ["Jawa Timur"], "Jawa Timur"),
                     "KB16": ("West Kalimantan", ["Kalimantan Barat"], "Kalimantan Barat"),
                     "KT17": ("Central Kalimantan", ["Kalimantan Tengah"], "Kalimantan Tengah"),
                     "KS18": ("South Kalimantan", ["Kalimantan Selatan"], "Kalimantan Selatan"),
                     "KT19": (["East Kalimantan", "North Kalimantan"], ["Kalimantan Timur"], "Kalimantan Timur"),
                     "B20": ("Bali", ["Bali"], "Bali"),
                     "NTB21": ("West Nusa Tenggara", ["Nusa Tenggara Barat"], "Nusa Tenggara Barat"),
                     "NTT22": ("East Nusa Tenggara", ["Nusa Tenggara Timur"], "Nusa Tenggara Timur"),
                     "SU23": ("North Sulawesi", ["Sulawesi Utara"], "Sulawesi Utara"),
                     "G24": ("Gorontalo", ["Gorontalo"], "Gorontalo"),
                     "ST25": ("Central Sulawesi", ["Sulawesi Tengah"], "Sulawesi Tengah"),
                     "ST26": ("Southeast Sulawesi", ["Sulawesi Tenggara"], "Sulawesi Tenggara"),
                     "SB27": ("West Sulawesi", ["Sulawesi Barat"], "Sulawesi Barat"),
                     "SS28": ("South Sulawesi", ["Sulawesi Selatan"], "Sulawesi Selatan"),
                     "M29": ("Maluku", ["Maluku"], "Maluku"),
                     "MU30": ("North Maluku", ["Maluku Utara"], "Maluku Utara"),
                     "P31": (["Papua", "Central Papua", "Highland Papua", "South Papua"], ["Papua"], "Papua"),
                     "PB32": (["West Papua", "Southwest Papua"], ["Papua Barat"], "Papua Barat")}},
    "PH": {"adm0": "PHL", "dir": "ph", "bbox": (116.9, 126.7, 4.5, 21.2),
           "page": "2022 Philippine presidential election",
           "match": "result by island group and region", "nth": 1, "pick": "last",
           # Les provincies de Natural Earth s'agrupen per la seva regio (17).
           "group": "region",
           "units": {
                     "I": ("I", ["Ilocos (Region I)"], "Ilocos"),
                     "CAR": ("CAR", ["Cordillera Administrative Region (CAR)"], "Cordillera"),
                     "II": ("II", ["Cagayan Valley (Region II)"], "Cagayan Valley"),
                     "III": ("III", ["Central Luzon (Region III)"], "Central Luzon"),
                     "NCR": ("NCR", ["National Capital Region"], "Metro Manila"),
                     "IVA": ("IV-A", ["CALABARZON (Region IV-A)"], "Calabarzon"),
                     "IVB": ("IV-B", ["MIMAROPA (Region IV-B)"], "Mimaropa"),
                     "V": ("V", ["Bicol (Region V)"], "Bicol"),
                     "VI": ("VI", ["Western Visayas (Region VI)"], "Western Visayas"),
                     "VII": ("VII", ["Central Visayas (Region VII)"], "Central Visayas"),
                     "VIII": ("VIII", ["Eastern Visayas (Region VIII)"], "Eastern Visayas"),
                     "IX": ("IX", ["Zamboanga Peninsula (Region IX)"], "Zamboanga Peninsula"),
                     "X": ("X", ["Northern Mindanao (Region X)"], "Northern Mindanao"),
                     "XI": ("XI", ["Davao (Region XI)"], "Davao"),
                     "XII": ("XII", ["SOCCSKSARGEN (Region XII)"], "Soccsksargen"),
                     "XIII": ("XIII", ["Dinagat Islands (Region XIII)"], "Caraga"),
                     "BARMM": ("BARMM", ["Autonomous Region in Muslim Mindanao (ARMM)"], "Bangsamoro")}},
    "GT": {"adm0": "GTM", "dir": "gt", "bbox": (-92.3, -88.2, 13.7, 17.85),
           "page": "Elecciones generales de Guatemala de 2023", "lang": "es",
           "match": "resultados por departamento", "columns": True,
           # Primera volta, % sobre el vot valid (taula de resultats de l'article angles).
           # Els departaments van sobre els vots emesos: el swing es reescala dins de
           # cada departament, aixi que la base diferent no hi pesa.
           "national": {"?SANDRATORRES": 21.10, "?BERNARDOAREVALO": 15.51,
                        "?MANUELCONDEORELLANA": 10.37, "?ARMANDOCASTILLO": 9.44,
                        "?EDMONDMULET": 8.78, "?ZURYRIOS": 8.70, "?MANUELVILLACORTA": 5.62,
                        "?GIOVANNIREYES": 3.37, "?HUGOPENA": 0.94},
           "units": {
                     "JUT0": ("Jutiapa", ["Jutiapa"], "Jutiapa"),
                     "CHI1": ("Chiquimula", ["Chiquimula"], "Chiquimula"),
                     "PET2": ("Petén", ["Petén"], "Petén"),
                     "SAN3": ("San Marcos", ["San Marcos"], "San Marcos"),
                     "HUE4": ("Huehuetenango", ["Huehuetenango"], "Huehuetenango"),
                     "QUI5": ("Quiché", ["Quiché"], "Quiché"),
                     "ALT6": ("Alta Verapaz", ["Alta Verapaz"], "Alta Verapaz"),
                     "IZA7": ("Izabal", ["Izabal"], "Izabal"),
                     "ZAC8": ("Zacapa", ["Zacapa"], "Zacapa"),
                     "RET9": ("Retalhuleu", ["Retalhuleu"], "Retalhuleu"),
                     "SUC10": ("Suchitepéquez", ["Suchitepéquez"], "Suchitepéquez"),
                     "ESC11": ("Escuintla", ["Escuintla"], "Escuintla"),
                     "SAN12": ("Santa Rosa", ["Santa Rosa"], "Santa Rosa"),
                     "CHI13": ("Chimaltenango", ["Chimaltenango"], "Chimaltenango"),
                     "SAC14": ("Sacatepéquez", ["Sacatepéquez"], "Sacatepéquez"),
                     "JAL15": ("Jalapa", ["Jalapa"], "Jalapa"),
                     "EL 16": ("El Progreso", ["El Progreso"], "El Progreso"),
                     "SOL17": ("Sololá", ["Sololá"], "Sololá"),
                     "BAJ18": ("Baja Verapaz", ["Baja Verapaz"], "Baja Verapaz"),
                     "TOT19": ("Totonicapán", ["Totonicapán"], "Totonicapán"),
                     "QUE": ("Quetzaltenango", ["Quezaltenango"], "Quetzaltenango"),
                     # La capital (Distrito Central) i la resta del departament.
                     "GUA": (["Distrito Central", "Guatemala"], ["Guatemala"], "Guatemala")}},
    # Generals 2027: la base es la primera volta presidencial del 2023; cada
    # partit d'avui es projecta sobre el candidat del seu espai (parties.yaml).
    "AR": {"adm0": "ARG", "dir": "ar", "bbox": (-73.6, -53.6, -55.1, -21.7),
           "page": "2023 Argentine general election", "match": "results by province, first round",
           "pick": "last",
           "units": {
                     "A00": ("Buenos Aires", ["Buenos Aires"], "Buenos Aires"),
                     "A01": ("Catamarca", ["Catamarca"], "Catamarca"),
                     "A02": ("Chaco", ["Chaco"], "Chaco"),
                     "A03": ("Chubut", ["Chubut"], "Chubut"),
                     "A04": ("Córdoba", ["Córdoba"], "Córdoba"),
                     "A05": ("Corrientes", ["Corrientes"], "Corrientes"),
                     "A06": ("Entre Ríos", ["Entre Ríos"], "Entre Ríos"),
                     "A07": ("Formosa", ["Formosa"], "Formosa"),
                     "A08": ("Jujuy", ["Jujuy"], "Jujuy"),
                     "A09": ("La Pampa", ["La Pampa"], "La Pampa"),
                     "A10": ("La Rioja", ["La Rioja"], "La Rioja"),
                     "A11": ("Mendoza", ["Mendoza"], "Mendoza"),
                     "A12": ("Misiones", ["Misiones"], "Misiones"),
                     "A13": ("Neuquén", ["Neuquén"], "Neuquén"),
                     "A14": ("Río Negro", ["Río Negro"], "Río Negro"),
                     "A15": ("Salta", ["Salta"], "Salta"),
                     "A16": ("San Juan", ["San Juan"], "San Juan"),
                     "A17": ("San Luis", ["San Luis"], "San Luis"),
                     "A18": ("Santa Cruz", ["Santa Cruz"], "Santa Cruz"),
                     "A19": ("Santa Fe", ["Santa Fe"], "Santa Fe"),
                     "A20": ("Santiago del Estero", ["Santiago del Estero"], "Santiago del Estero"),
                     "A21": ("Tierra del Fuego", ["Tierra del Fuego"], "Tierra del Fuego"),
                     "A22": ("Tucumán", ["Tucumán"], "Tucumán"),
                     "CABA": ("Buenos Aires City", ["Ciudad de Buenos Aires"], "Ciudad de Buenos Aires")}},
    # Les enquestes son de la Cambra 2027, pero no hi ha taula per estat dels
    # diputats del 2024: la base son les presidencials del mateix dia (Viquipedia
    # castellana), amb cada partit sobre la candidata de la seva coalicio.
    "MX": {"adm0": "MEX", "dir": "mx", "bbox": (-118.5, -86.6, 14.5, 32.8),
           "page": "Elecciones federales de México de 2024", "lang": "es", "match": "por estado",
           "pick": "last",
           "units": {
                     "M00": ("Aguascalientes", ["Aguascalientes"], "Aguascalientes"),
                     "M01": ("Baja California", ["Baja California"], "Baja California"),
                     "M02": ("Baja California Sur", ["Baja California Sur"], "Baja California Sur"),
                     "M03": ("Campeche", ["Campeche"], "Campeche"),
                     "M04": ("Coahuila", ["Coahuila"], "Coahuila"),
                     "M05": ("Colima", ["Colima"], "Colima"),
                     "M06": ("Chiapas", ["Chiapas"], "Chiapas"),
                     "M07": ("Chihuahua", ["Chihuahua"], "Chihuahua"),
                     "M08": ("Durango", ["Durango"], "Durango"),
                     "M09": ("Guanajuato", ["Guanajuato"], "Guanajuato"),
                     "M10": ("Guerrero", ["Guerrero"], "Guerrero"),
                     "M11": ("Hidalgo", ["Hidalgo"], "Hidalgo"),
                     "M12": ("Jalisco", ["Jalisco"], "Jalisco"),
                     "M13": ("Michoacán", ["Michoacán"], "Michoacán"),
                     "M14": ("Morelos", ["Morelos"], "Morelos"),
                     "M15": ("Nayarit", ["Nayarit"], "Nayarit"),
                     "M16": ("Nuevo León", ["Nuevo León"], "Nuevo León"),
                     "M17": ("Oaxaca", ["Oaxaca"], "Oaxaca"),
                     "M18": ("Puebla", ["Puebla"], "Puebla"),
                     "M19": ("Querétaro", ["Querétaro"], "Querétaro"),
                     "M20": ("Quintana Roo", ["Quintana Roo"], "Quintana Roo"),
                     "M21": ("San Luis Potosí", ["San Luis Potosí"], "San Luis Potosí"),
                     "M22": ("Sinaloa", ["Sinaloa"], "Sinaloa"),
                     "M23": ("Sonora", ["Sonora"], "Sonora"),
                     "M24": ("Tabasco", ["Tabasco"], "Tabasco"),
                     "M25": ("Tamaulipas", ["Tamaulipas"], "Tamaulipas"),
                     "M26": ("Tlaxcala", ["Tlaxcala"], "Tlaxcala"),
                     "M27": ("Veracruz", ["Veracruz"], "Veracruz"),
                     "M28": ("Yucatán", ["Yucatán"], "Yucatán"),
                     "M29": ("Zacatecas", ["Zacatecas"], "Zacatecas"),
                     "CDMX": ("Ciudad de México", ["Distrito Federal"], "Ciudad de México"),
                     "MEX": ("Estado de México", ["México"], "Estado de México")}},
    # Belgica: les 11 circumscripcions de la Cambra son les 10 provincies i
    # Brussel.les. Viquipedia francesa, taula resum per circumscripcio.
    "BE": {"adm0": "BEL", "dir": "be", "bbox": (2.5, 6.45, 49.45, 51.55),
           "page": "Élections législatives fédérales belges de 2024", "lang": "fr",
           "match": "résumé", "columns": True,
           "alias": {"?NIEUWVLAAMSEALLIANTIE": "?NEWFLEMISHALLIANCE",
                     "?MOUVEMENTREFORMATEUR": "?REFORMISTMOVEMENT",
                     "?PARTIDUTRAVAILDEBELGIQUE": "?WORKERSPARTYOFBELGIUM",
                     "?PARTISOCIALISTE": "?SOCIALISTPARTY",
                     "?CHRISTENDEMOCRATISCHENVLAAMS": "?CHRISTIANDEMOCRATICANDFLEMISH",
                     # Open VLD es diu Anders des del 2025.
                     "?OPENVLAAMSELIBERALENENDEMOCRATEN": "?ANDERS",
                     "?DEMOCRATEFEDERALISTEINDEPENDANT": "?DEFI", "?AUTRES": "OTHER"},
           # Resultat del 2024 a cada regio (taules «Flandre» i «Wallonie» de l'article).
           "regions": {"VLG": {"?NIEUWVLAAMSEALLIANTIE": 25.56, "?VLAAMSBELANG": 21.81,
                               "?VOORUIT": 13.02, "?CHRISTENDEMOCRATISCHENVLAAMS": 12.81,
                               "?OPENVLAAMSELIBERALENENDEMOCRATEN": 8.75,
                               "?PARTIDUTRAVAILDEBELGIQUE": 8.16, "?GROEN": 7.46},
                       "WAL": {"?MOUVEMENTREFORMATEUR": 28.21, "?PARTISOCIALISTE": 21.98,
                               "?LESENGAGES": 20.01, "?PARTIDUTRAVAILDEBELGIQUE": 11.64,
                               "?ECOLO": 6.89, "?DEMOCRATEFEDERALISTEINDEPENDANT": 2.36,
                               "?NIEUWVLAAMSEALLIANTIE": 1.93}},
           "by_region": {"ANT": "VLG", "VBR": "VLG", "WVL": "VLG", "OVL": "VLG", "LIM": "VLG",
                         "WBR": "WAL", "HAI": "WAL", "LIE": "WAL", "LUX": "WAL", "NAM": "WAL"},
           # Brussel.les te enquestes propies (regio BRU): es mostren tal qual.
           "units": {"BRU": ("Bruxelles", ["Brussels"], "Bruxelles / Brussel"),
                     "ANT": ("Anvers", ["Antwerp"], "Antwerpen"),
                     "VBR": ("Brabant fl.", ["Flemish Brabant"], "Vlaams-Brabant"),
                     "WVL": ("Flandre occ.", ["West Flanders"], "West-Vlaanderen"),
                     "OVL": ("Flandre or.", ["East Flanders"], "Oost-Vlaanderen"),
                     "LIM": ("Limbourg", ["Limburg"], "Limburg"),
                     "WBR": ("Brabant wa.", ["Walloon Brabant"], "Brabant wallon"),
                     "HAI": ("Hainaut", ["Hainaut"], "Hainaut"),
                     "LIE": ("Liège", ["Liege"], "Liège"),
                     "LUX": ("Luxembourg", ["Luxembourg"], "Luxembourg"),
                     "NAM": ("Namur", ["Namur"], "Namur")}},
    # Legislatives 2028: no hi ha taula per comtat de les legislatives del 2024 amb
    # llicencia clara; la base es la primera volta presidencial del 24/11/2024
    # (anul.lada despres, pero els vots per comtat son reals), amb un candidat per
    # partit gran. Cada partit es projecta sobre el seu candidat (parties.yaml).
    "RO": {"adm0": "ROU", "dir": "ro", "bbox": (20.2, 29.8, 43.6, 48.3),
           "page": "2024 Romanian presidential election", "match": "by county", "pick": "last",
           "units": {
                     "ALBA": ("Alba", ["Alba"], "Alba"),
                     "ARAD": ("Arad", ["Arad"], "Arad"),
                     "ARGES": ("Argeș", ["Arges"], "Argeș"),
                     "BACAU": ("Bacău", ["Bacau"], "Bacău"),
                     "BIHOR": ("Bihor", ["Bihor"], "Bihor"),
                     "BISTR": ("Bistrița-Năsăud", ["Bistrita-Nasaud"], "Bistrița-Năsăud"),
                     "BOTOS": ("Botoșani", ["Botosani"], "Botoșani"),
                     "BRAIL": ("Brăila", ["Braila"], "Brăila"),
                     "BRASO": ("Brașov", ["Brasov"], "Brașov"),
                     "BUCHA": ("Bucharest", ["Bucharest"], "Bucharest"),
                     "BUZAU": ("Buzău", ["Buzau"], "Buzău"),
                     "CALAR": ("Călărași", ["Calarasi"], "Călărași"),
                     "CARAS": ("Caraș-Severin", ["Caras-Severin"], "Caraș-Severin"),
                     "CLUJ": ("Cluj", ["Cluj"], "Cluj"),
                     "CONST": ("Constanța", ["Constanta"], "Constanța"),
                     "COVAS": ("Covasna", ["Covasna"], "Covasna"),
                     "DOLJ": ("Dolj", ["Dolj"], "Dolj"),
                     "DAMBO": ("Dâmbovița", ["Dâmbovita"], "Dâmbovița"),
                     "GALAT": ("Galați", ["Galati"], "Galați"),
                     "GIURG": ("Giurgiu", ["Giurgiu"], "Giurgiu"),
                     "GORJ": ("Gorj", ["Gorj"], "Gorj"),
                     "HARGH": ("Harghita", ["Harghita"], "Harghita"),
                     "HUNED": ("Hunedoara", ["Hunedoara"], "Hunedoara"),
                     "IALOM": ("Ialomița", ["Ialomita"], "Ialomița"),
                     "IASI": ("Iași", ["Iasi"], "Iași"),
                     "ILFOV": ("Ilfov", ["Ilfov"], "Ilfov"),
                     "MARAM": ("Maramureș", ["Maramures"], "Maramureș"),
                     "MEHED": ("Mehedinți", ["Mehedinti"], "Mehedinți"),
                     "MURES": ("Mureș", ["Mures"], "Mureș"),
                     "NEAMT": ("Neamț", ["Neamt"], "Neamț"),
                     "OLT": ("Olt", ["Olt"], "Olt"),
                     "PRAHO": ("Prahova", ["Prahova"], "Prahova"),
                     "SALAJ": ("Sălaj", ["Salaj"], "Sălaj"),
                     "SATUM": ("Satu Mare", ["Satu Mare"], "Satu Mare"),
                     "SIBIU": ("Sibiu", ["Sibiu"], "Sibiu"),
                     "SUCEA": ("Suceava", ["Suceava"], "Suceava"),
                     "TELEO": ("Teleorman", ["Teleorman"], "Teleorman"),
                     "TIMIS": ("Timiș", ["Timis"], "Timiș"),
                     "TULCE": ("Tulcea", ["Tulcea"], "Tulcea"),
                     "VASLU": ("Vaslui", ["Vaslui"], "Vaslui"),
                     "VRANC": ("Vrancea", ["Vrancea"], "Vrancea"),
                     "VALCE": ("Vâlcea", ["Vâlcea"], "Vâlcea")}},
    "CH": {"adm0": "CHE", "dir": "ch", "bbox": (5.9, 10.5, 45.8, 47.85),
           "page": "2023 Swiss federal election", "match": "by canton > national council",
           # Les enquestes son de la Viquipedia francesa: les sigles de la base (angles)
           # es passen a les seves.
           "alias": {"?SWISSPEOPLESPARTY": "?UNIONDEMOCRATIQUEDUCENTRE",
                     "?SOCIALDEMOCRATICPARTYOFSWITZERLAND": "?PARTISOCIALISTESUISSE",
                     "?THECENTRE": "?LECENTRE", "?THELIBERALS": "?PARTILIBERALRADICAL",
                     "?GREENPARTYOFSWITZERLAND": "?LESVERTS",
                     "?GREENLIBERALPARTYOFSWITZERLAND": "?VERTLIBERAUX"},
           "units": {
                     "C00": ("Aargau", ["Aargau"], "Aargau"),
                     "C01": ("Appenzell Ausserrhoden", ["Appenzell Ausserrhoden"], "Appenzell Ausserrhoden"),
                     "C02": ("Appenzell Innerrhoden", ["Appenzell Innerrhoden"], "Appenzell Innerrhoden"),
                     "C03": ("Basel-Landschaft", ["Basel-Landschaft"], "Basel-Landschaft"),
                     "C04": ("Basel-Stadt", ["Basel-Stadt"], "Basel-Stadt"),
                     "C05": ("Bern", ["Bern"], "Bern"),
                     "C06": ("Fribourg", ["Fribourg"], "Fribourg"),
                     "C07": ("Geneva", ["Genève"], "Genève"),
                     "C08": ("Glarus", ["Glarus"], "Glarus"),
                     "C09": ("Grisons", ["Graubünden"], "Graubünden"),
                     "C10": ("Jura", ["Jura"], "Jura"),
                     "C11": ("Lucerne", ["Lucerne"], "Luzern"),
                     "C12": ("Neuchâtel", ["Neuchâtel"], "Neuchâtel"),
                     "C13": ("Nidwalden", ["Nidwalden"], "Nidwalden"),
                     "C14": ("Obwalden", ["Obwalden"], "Obwalden"),
                     "C15": ("Schaffhausen", ["Schaffhausen"], "Schaffhausen"),
                     "C16": ("Schwyz", ["Schwyz"], "Schwyz"),
                     "C17": ("Solothurn", ["Solothurn"], "Solothurn"),
                     "C18": ("St. Gallen", ["Sankt Gallen"], "St. Gallen"),
                     "C19": ("Thurgau", ["Thurgau"], "Thurgau"),
                     "C20": ("Ticino", ["Ticino"], "Ticino"),
                     "C21": ("Uri", ["Uri"], "Uri"),
                     "C22": ("Valais", ["Valais"], "Valais"),
                     "C23": ("Vaud", ["Vaud"], "Vaud"),
                     "C24": ("Zug", ["Zug"], "Zug"),
                     "C25": ("Zürich", ["Zürich"], "Zürich")}},
    # Turquia: resultat per provincia de la Viquipedia turca ("vots | % | diputats").
    # Istanbul, Ankara, Esmirna i Bursa tenen diverses circumscripcions: el total.
    "TR": {"adm0": "TUR", "dir": "tr", "bbox": (25.6, 44.9, 35.8, 42.2),
           "page": "2023 Türkiye genel seçimleri", "lang": "tr", "match": "llere göre sonuçlar",
           "offset": 1,
           "units": {
                     "T00": ("Adana", ["Adana"], "Adana"),
                     "T01": ("Adıyaman", ["Adiyaman"], "Adıyaman"),
                     "T02": ("Afyonkarahisar", ["Afyonkarahisar"], "Afyonkarahisar"),
                     "T03": ("Ağrı", ["Agri"], "Ağrı"),
                     "T04": ("Aksaray", ["Aksaray"], "Aksaray"),
                     "T05": ("Amasya", ["Amasya"], "Amasya"),
                     "T06": ("Ankara (toplam)", ["Ankara"], "Ankara"),
                     "T07": ("Antalya", ["Antalya"], "Antalya"),
                     "T08": ("Ardahan", ["Ardahan"], "Ardahan"),
                     "T09": ("Artvin", ["Artvin"], "Artvin"),
                     "T10": ("Aydın", ["Aydin"], "Aydın"),
                     "T11": ("Balıkesir", ["Balikesir"], "Balıkesir"),
                     "T12": ("Bartın", ["Bartın"], "Bartın"),
                     "T13": ("Batman", ["Batman"], "Batman"),
                     "T14": ("Bayburt", ["Bayburt"], "Bayburt"),
                     "T15": ("Bilecik", ["Bilecik"], "Bilecik"),
                     "T16": ("Bingöl", ["Bingöl"], "Bingöl"),
                     "T17": ("Bitlis", ["Bitlis"], "Bitlis"),
                     "T18": ("Bolu", ["Bolu"], "Bolu"),
                     "T19": ("Burdur", ["Burdur"], "Burdur"),
                     "T20": ("Bursa (toplam)", ["Bursa"], "Bursa"),
                     "T21": ("Denizli", ["Denizli"], "Denizli"),
                     "T22": ("Diyarbakır", ["Diyarbakir"], "Diyarbakır"),
                     "T23": ("Düzce", ["Düzce"], "Düzce"),
                     "T24": ("Edirne", ["Edirne"], "Edirne"),
                     "T25": ("Elazığ", ["Elazig"], "Elazığ"),
                     "T26": ("Erzincan", ["Erzincan"], "Erzincan"),
                     "T27": ("Erzurum", ["Erzurum"], "Erzurum"),
                     "T28": ("Eskişehir", ["Eskisehir"], "Eskişehir"),
                     "T29": ("Gaziantep", ["Gaziantep"], "Gaziantep"),
                     "T30": ("Giresun", ["Giresun"], "Giresun"),
                     "T31": ("Gümüşhane", ["Gümüshane"], "Gümüşhane"),
                     "T32": ("Hakkâri", ["Hakkari"], "Hakkâri"),
                     "T33": ("Hatay", ["Hatay"], "Hatay"),
                     "T34": ("Isparta", ["Isparta"], "Isparta"),
                     "T35": ("İstanbul (toplam)", ["Istanbul"], "İstanbul"),
                     "T36": ("İzmir (toplam)", ["Izmir"], "İzmir"),
                     "T37": ("Iğdır", ["Iğdir"], "Iğdır"),
                     "T38": ("Kahramanmaraş", ["K. Maras"], "Kahramanmaraş"),
                     "T39": ("Karabük", ["Karabük"], "Karabük"),
                     "T40": ("Karaman", ["Karaman"], "Karaman"),
                     "T41": ("Kars", ["Kars"], "Kars"),
                     "T42": ("Kastamonu", ["Kastamonu"], "Kastamonu"),
                     "T43": ("Kayseri", ["Kayseri"], "Kayseri"),
                     "T44": ("Kilis", ["Kilis"], "Kilis"),
                     "T45": ("Kırıkkale", ["Kinkkale"], "Kırıkkale"),
                     "T46": ("Kırklareli", ["Kirklareli"], "Kırklareli"),
                     "T47": ("Kırşehir", ["Kirsehir"], "Kırşehir"),
                     "T48": ("Kocaeli", ["Kocaeli"], "Kocaeli"),
                     "T49": ("Konya", ["Konya"], "Konya"),
                     "T50": ("Kütahya", ["Kütahya"], "Kütahya"),
                     "T51": ("Malatya", ["Malatya"], "Malatya"),
                     "T52": ("Manisa", ["Manisa"], "Manisa"),
                     "T53": ("Mardin", ["Mardin"], "Mardin"),
                     "T54": ("Mersin", ["Mersin"], "Mersin"),
                     "T55": ("Muğla", ["Mugla"], "Muğla"),
                     "T56": ("Muş", ["Mus"], "Muş"),
                     "T57": ("Nevşehir", ["Nevsehir"], "Nevşehir"),
                     "T58": ("Niğde", ["Nigde"], "Niğde"),
                     "T59": ("Ordu", ["Ordu"], "Ordu"),
                     "T60": ("Osmaniye", ["Osmaniye"], "Osmaniye"),
                     "T61": ("Rize", ["Rize"], "Rize"),
                     "T62": ("Sakarya", ["Sakarya"], "Sakarya"),
                     "T63": ("Samsun", ["Samsun"], "Samsun"),
                     "T64": ("Şanlıurfa", ["Sanliurfa"], "Şanlıurfa"),
                     "T65": ("Siirt", ["Siirt"], "Siirt"),
                     "T66": ("Sinop", ["Sinop"], "Sinop"),
                     "T67": ("Şırnak", ["Sirnak"], "Şırnak"),
                     "T68": ("Sivas", ["Sivas"], "Sivas"),
                     "T69": ("Tekirdağ", ["Tekirdag"], "Tekirdağ"),
                     "T70": ("Tokat", ["Tokat"], "Tokat"),
                     "T71": ("Trabzon", ["Trabzon"], "Trabzon"),
                     "T72": ("Tunceli", ["Tunceli"], "Tunceli"),
                     "T73": ("Uşak", ["Usak"], "Uşak"),
                     "T74": ("Van", ["Van"], "Van"),
                     "T75": ("Yalova", ["Yalova"], "Yalova"),
                     "T76": ("Yozgat", ["Yozgat"], "Yozgat"),
                     "T77": ("Zonguldak", ["Zinguldak"], "Zonguldak"),
                     "T78": ("Çanakkale", ["Çanakkale"], "Çanakkale"),
                     "T79": ("Çankırı", ["Çankiri"], "Çankırı"),
                     "T80": ("Çorum", ["Çorum"], "Çorum")}},
    # Taiwan: vot de llista (el que mesuren les enquestes) per comtat i ciutat.
    # Lienchiang (Matsu) no es a Natural Earth.
    "TW": {"adm0": "TWN", "dir": "tw", "bbox": (118.1, 122.1, 21.85, 25.35),
           "page": "2024 Taiwanese legislative election", "match": "by national-at-large",
           "pick": "last",
           "national": {"?DEMOCRATICPROGRESSIVEPARTY": 36.16, "?KUOMINTANG": 34.58,
                        "?TAIWANPEOPLESPARTY": 22.07},
           "units": {
                     "W00": ("Taipei", ["Taipei City"], "Taipei"),
                     "W01": ("New Taipei City", ["New Taipei City"], "New Taipei City"),
                     "W02": ("Keelung", ["Keelung City"], "Keelung"),
                     "W03": ("Yilan County", ["Yilan"], "Yilan County"),
                     "W04": ("Taoyuan City", ["Taoyuan"], "Taoyuan City"),
                     "W05": ("Hsinchu County", ["Hsinchu"], "Hsinchu County"),
                     "W06": ("Hsinchu City", ["Hsinchu City"], "Hsinchu City"),
                     "W07": ("Miaoli County", ["Miaoli"], "Miaoli County"),
                     "W08": ("Taichung City", ["Taichung City"], "Taichung City"),
                     "W09": ("Changhua County", ["Changhua"], "Changhua County"),
                     "W10": ("Nantou County", ["Nantou"], "Nantou County"),
                     "W11": ("Yunlin County", ["Yunlin"], "Yunlin County"),
                     "W12": ("Chiayi County", ["Chiayi"], "Chiayi County"),
                     "W13": ("Chiayi City", ["Chiayi City"], "Chiayi City"),
                     "W14": ("Tainan City", ["Tainan City"], "Tainan City"),
                     "W15": ("Kaohsiung City", ["Kaohsiung City"], "Kaohsiung City"),
                     "W16": ("Pingtung County", ["Pingtung"], "Pingtung County"),
                     "W17": ("Taitung County", ["Taitung"], "Taitung County"),
                     "W18": ("Hualien County", ["Hualien"], "Hualien County"),
                     "W19": ("Penghu County", ["Penghu"], "Penghu County"),
                     "W20": ("Kinmen County", ["Kinmen"], "Kinmen County")}},
}


def _wiki_spec(country):
    w = WIKI[country]
    codes = {ne: code for code, (_wn, nes, _dn) in w["units"].items() for ne in nes}
    names = {ne: w["units"][code][2] for ne, code in codes.items()}
    # `group`: el camp de Natural Earth que s'agrupa (Filipines: "region").
    return {"adm0": w["adm0"], "group": w.get("group", "name"), "dir": w["dir"],
            "unit_file": "units.json",
            "bbox": w["bbox"], "base_file": "base.json", "loader": "wiki", "codes": codes,
            "simplify": w.get("simplify", 0.0),
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


def _path(rings, xy, tol=0.0):
    """`tol` (pixels): salta els punts massa a prop de l'anterior i els illots
    mes petits que aixo. Sense, l'arxipelag artic del Canada pesava 500 KB."""
    parts = []
    for ring in rings:
        pts = []
        for lon, lat in ring:
            p = xy(lon, lat)
            if not pts or (p != pts[-1] if not tol else
                           abs(p[0] - pts[-1][0]) + abs(p[1] - pts[-1][1]) >= tol):
                pts.append(p)
        if len(set(pts)) < 3:
            continue
        if tol and (max(x for x, _ in pts) - min(x for x, _ in pts) < 2 * tol
                    and max(y for _, y in pts) - min(y for _, y in pts) < 2 * tol):
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
    out = {code: {"n": v["n"], "d": _path(v["r"], xy, spec.get("simplify", 0.0))}
           for code, v in rings.items()}
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


def _load_dk(spec):
    """Vots per municipi del 2026 (FVKOM) sumats per regio. La regio de cada
    municipi surt de la llista de municipis de Wikipedia (codi LAU i regio)."""
    import csv
    from bs4 import BeautifulSoup
    from ..ingest import wikipedia as wk
    soup = BeautifulSoup(wk.fetch("List of municipalities of Denmark")["html"], "lxml")
    region_of = {}
    regions = {"Capital": "84", "Zealand": "85", "South": "83", "Central": "82", "North": "81"}
    for row in wk.grid(soup.select("table.wikitable")[0])[1:]:
        # "Bornholm (merged 2003)": fora el parentesi.
        name = re.sub(r"\s*\(.*\)", "", wk.cell_text(row[1]))
        reg = wk.cell_text(row[-1])
        code = next((c for k, c in regions.items() if reg.startswith(k)), None)
        if code:
            region_of[name] = code
    # Grafia de DST diferent de la de Wikipedia.
    region_of["Vesthimmerlands"] = region_of.get("Vesthimmerland")
    region_of["Nordfyns"] = region_of.get("Nordfyn")
    region_of["Christiansø"] = "84"           # no es municipi: l'administra l'Estat, a l'est de Bornholm
    path = ROOT / "data" / "raw" / "dk" / "fvkom_2026.csv"
    votes, national, missing = {}, {}, set()
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            label = row["VALRES"]
            m = re.match(r"^(\w)\. ", label)
            if not m and label != "Independent candidates":
                continue
            party = spec["parties"].get(m.group(1), "OTHER") if m else "OTHER"
            n = int(row["INDHOLD"] or 0) if row["INDHOLD"].strip().isdigit() else 0
            code = region_of.get(row["OMRÅDE"])
            if not code:
                missing.add(row["OMRÅDE"])
                continue
            votes.setdefault(code, {}).setdefault(party, 0)
            votes[code][party] += n
            national[party] = national.get(party, 0) + n
    if missing:
        raise RuntimeError(f"municipis sense regio: {sorted(missing)}")
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
    rows, total, _title = region_table(w["page"], w["match"], w["cc"], pick=w.get("pick", "first"),
                                       transposed=w.get("transposed", False),
                                       lang=w.get("lang", "en"), name_col=w.get("name_col", 0),
                                       columns=w.get("columns", False), nth=w.get("nth", 0),
                                       offset=w.get("offset", 0))
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
    if not total:
        total = w.get("national")
    return deps, {}, rename(total) if total else None


def baseline(spec, conn):
    """{territori: {partit: %}} i el total estatal de l'eleccio de base."""
    if spec.get("loader") == "wiki":
        deps, valid, national = _load_wiki(spec)
        out = {"national": national, "dep": deps, "valid": valid, "source": spec["source"]}
        w = spec["wiki"]
        if w.get("regions"):
            # Belgica: resultat de cada regio i regio de cada unitat (mode regional).
            alias = w.get("alias") or {}
            out["regions"] = {k: {alias.get(p, p): v for p, v in r.items()}
                              for k, r in w["regions"].items()}
            out["by_region"] = w["by_region"]
        return out
    loaders = {"de": _load_de, "gb": _load_gb, "nl": _load_nl, "au": _load_au, "dk": _load_dk}
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
