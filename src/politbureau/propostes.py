"""Propostes concretes per tema i per grup (23/11/2026, demanat per l'Alfonso:
"unes propostes molt mes concretes i que parlin de molts mes temes").

Redaccio editorial de Polit Bureau: mesures que ja s'apliquen o es debaten a
Espanya o a altres paisos europeus, escrites de manera concreta. NO les ha
preguntat el CIS i no se'n sap el suport; les que si que ha preguntat el CIS
surten a part, amb el %.

Cada proposta te una orientacio:
  L  esquerra            C  centre / consens
  R  dreta               T  territorial (partits d'una comunitat)
i, si n'hi ha, etiquetes del grup a qui va mes adreçada (young, senior...).
La fitxa de cada partit nomes ensenya les orientacions que li corresponen
(FAMILY), en aquest ordre.
"""
from __future__ import annotations

# Orientacions de cada partit, per ordre de preferencia (raonament propi a
# partir dels seus programes i de la seva posicio a l'eix esquerra-dreta).
FAMILY = {
    "PSOE": "CL", "SUMAR": "LC", "PODEMOS": "L", "ERC": "LTC", "EHB": "LT", "BNG": "LT", "AA": "LT",
    "JUNTS": "TCR", "PNV": "TC", "CC": "TC", "PP": "CR", "UPN": "CR", "VOX": "R", "SALF": "R",
}

# Problema del CIS -> tema del cataleg.
TOPIC_OF = {
    "La vivienda": "housing",
    "La okupación de viviendas": "okupa",
    "La crisis económica, los problemas de índole económica": "economy",
    "Los problemas de índole económica": "economy",
    "La subida de precios. La inflación. Pérdida de poder adquisitivo": "prices",
    "El paro": "unemployment",
    "Los problemas relacionados con la calidad del empleo": "jobs",
    "Los problemas relacionados con la juventud. Falta de apoyo y oportunidades para los/as jóvenes": "youth",
    "La sanidad": "health",
    "La educación": "education",
    "Las pensiones": "pensions",
    "La inmigración": "immigration",
    "La inseguridad ciudadana": "security",
    "La corrupción y el fraude": "corruption",
    "El Gobierno y partidos o políticos/as concretos/as": "politics",
    "Los problemas políticos en general": "politics",
    "El mal comportamiento de los/as políticos/as": "politics",
    "Lo que hacen los partidos políticos": "politics",
    "La falta de confianza en los/las políticos/as y las instituciones": "politics",
    "La falta de acuerdos, unidad y capacidad de colaboración. Situación e inestabilidad política": "agreement",
    "Aumento de la crispación social, revueltas sociales": "agreement",
    "Los extremismos": "agreement",
    "Las desigualdades, incluida la de género, diferencias de clases, la pobreza": "inequality",
    "Los problemas de índole social": "inequality",
    "La violencia contra la mujer": "women",
    "Los problemas relacionados con la mujer": "women",
    "El cambio climático": "climate",
    "Los problemas de la agricultura, ganadería y pesca": "farming",
    "La dependencia": "care",
    "La Administración de Justicia": "justice",
    "Papel de los medios de comunicación y redes: desinformación, manipulación informativa, difusión de bulos": "media",
    "El nacionalismo, independencia de Cataluña": "territory",
    "La subida de los impuestos": "taxes",
    "El funcionamiento de los servicios públicos": "services",
    "El funcionamiento de la democracia": "democracy",
    "Las guerras en general": "world",
    "Crisis con Marruecos. Fronteras de Ceuta y Melilla": "borders",
    "La crisis de valores": "values",
}

TOPICS = {
    "housing": ("Habitatge", "Vivienda"), "okupa": ("Ocupació d'habitatges", "Okupación de viviendas"),
    "economy": ("Economia", "Economía"), "prices": ("Preus i inflació", "Precios e inflación"),
    "unemployment": ("Atur", "Paro"), "jobs": ("Qualitat de la feina", "Calidad del empleo"),
    "youth": ("Joventut i oportunitats", "Juventud y oportunidades"), "health": ("Sanitat", "Sanidad"),
    "education": ("Educació", "Educación"), "pensions": ("Pensions", "Pensiones"),
    "immigration": ("Immigració", "Inmigración"), "security": ("Seguretat", "Seguridad"),
    "corruption": ("Corrupció", "Corrupción"), "politics": ("Els polítics i les institucions", "Los políticos y las instituciones"),
    "agreement": ("Falta d'acords i crispació", "Falta de acuerdos y crispación"),
    "inequality": ("Desigualtat i pobresa", "Desigualdad y pobreza"),
    "women": ("Igualtat i violència masclista", "Igualdad y violencia machista"),
    "climate": ("Clima i emergències", "Clima y emergencias"), "farming": ("Camp i pesca", "Campo y pesca"),
    "care": ("Dependència i cures", "Dependencia y cuidados"), "justice": ("Justícia", "Justicia"),
    "media": ("Desinformació", "Desinformación"), "territory": ("Model territorial", "Modelo territorial"),
    "taxes": ("Impostos", "Impuestos"), "services": ("Serveis públics i tràmits", "Servicios públicos y trámites"),
    "democracy": ("Qualitat de la democràcia", "Calidad de la democracia"), "world": ("Guerres i defensa", "Guerras y defensa"),
    "borders": ("Marroc, Ceuta i Melilla", "Marruecos, Ceuta y Melilla"), "values": ("Família i valors", "Familia y valores"),
}

# (tema, orientacio, ca, es, etiquetes)
_P = [
    # ------------------------------------------------------------ habitatge
    ("housing", "L", "Construir 20.000 pisos públics de lloguer l'any en sòl públic, amb un lloguer que no passi del 30 % dels ingressos",
     "Construir 20.000 pisos públicos de alquiler al año en suelo público, con un alquiler que no pase del 30 % de los ingresos", ()),
    ("housing", "L", "Topall al preu del lloguer a les zones tensionades, amb multes als grans tenidors que no el compleixin",
     "Tope al precio del alquiler en las zonas tensionadas, con multas a los grandes tenedores que no lo cumplan", ("young",)),
    ("housing", "L", "Prohibir la compra d'habitatge per especular als fons i als no residents, com al Canadà",
     "Prohibir la compra de vivienda para especular a los fondos y a los no residentes, como en Canadá", ()),
    ("housing", "C", "Aval públic del 20 % de la hipoteca per als menors de 35 anys i les famílies amb fills",
     "Aval público del 20 % de la hipoteca para los menores de 35 años y las familias con hijos", ("young", "family")),
    ("housing", "C", "Convertir oficines i locals buits en habitatge amb una llicència exprés de tres mesos",
     "Convertir oficinas y locales vacíos en vivienda con una licencia exprés de tres meses", ()),
    ("housing", "C", "Assegurança pública gratuïta contra l'impagament per als propietaris que lloguin per sota del preu de referència",
     "Seguro público gratuito contra el impago para los propietarios que alquilen por debajo del precio de referencia", ("senior",)),
    ("housing", "R", "Alliberar sòl urbanitzable i que una llicència d'obra no trigui més de sis mesos",
     "Liberar suelo urbanizable y que una licencia de obra no tarde más de seis meses", ()),
    ("housing", "R", "Impost de transmissions del 4 % per a la primera casa i zero per als menors de 35 anys",
     "Impuesto de transmisiones del 4 % para la primera vivienda y cero para los menores de 35 años", ("young",)),
    ("housing", "R", "Deduir a l'IRPF tot el que cobra el propietari que lloga a un jove",
     "Deducir en el IRPF todo lo que cobra el propietario que alquila a un joven", ("young", "highinc")),
    ("housing", "T", "Competència plena d'habitatge amb un fons propi pagat amb la taxa turística",
     "Competencia plena de vivienda con un fondo propio pagado con la tasa turística", ()),
    ("housing", "T", "Registre autonòmic dels pisos buits i dels grans tenidors, amb recàrrec als que estiguin buits més de dos anys",
     "Registro autonómico de los pisos vacíos y de los grandes tenedores, con recargo a los vacíos más de dos años", ()),
    # ------------------------------------------------------------ okupacio
    ("okupa", "R", "Desallotjament en 48 hores quan qui ocupa el pis no pugui ensenyar cap contracte",
     "Desalojo en 48 horas cuando quien ocupa el piso no pueda enseñar ningún contrato", ("senior",)),
    ("okupa", "R", "Que les comunitats de veïns puguin denunciar l'ocupació i demanar el desallotjament",
     "Que las comunidades de vecinos puedan denunciar la okupación y pedir el desalojo", ()),
    ("okupa", "C", "Jutjats especialitzats perquè els casos d'ocupació es resolguin en menys d'un mes",
     "Juzgados especializados para que los casos de okupación se resuelvan en menos de un mes", ()),
    ("okupa", "L", "Separar l'ocupació delictiva de les famílies vulnerables, amb una alternativa d'habitatge obligatòria",
     "Separar la okupación delictiva de las familias vulnerables, con una alternativa de vivienda obligatoria", ()),
    ("okupa", "L", "Obligar bancs i fons a cedir els pisos buits a lloguer social",
     "Obligar a bancos y fondos a ceder los pisos vacíos a alquiler social", ()),
    # ------------------------------------------------------------ economia
    ("economy", "L", "Impost permanent a les grans fortunes i als beneficis extraordinaris de la banca i les energètiques",
     "Impuesto permanente a las grandes fortunas y a los beneficios extraordinarios de la banca y las energéticas", ()),
    ("economy", "L", "Pla industrial públic per fabricar a Espanya renovables, xips i cotxe elèctric",
     "Plan industrial público para fabricar en España renovables, chips y coche eléctrico", ("worker",)),
    ("economy", "C", "Pagar l'IVA només quan es cobra la factura i tarifa plana de 80 € durant dos anys per als nous autònoms",
     "Pagar el IVA solo cuando se cobra la factura y tarifa plana de 80 € durante dos años para los nuevos autónomos", ("selfemp",)),
    ("economy", "C", "Deduccions per a les pimes que inverteixin en tecnologia, en formació o a pujar sous",
     "Deducciones para las pymes que inviertan en tecnología, en formación o en subir sueldos", ("selfemp",)),
    ("economy", "R", "Abaixar l'IRPF a les rendes mitjanes i actualitzar-lo cada any amb la inflació",
     "Bajar el IRPF a las rentas medias y actualizarlo cada año con la inflación", ("family", "highinc")),
    ("economy", "R", "Retallar la despesa política (assessors, organismes duplicats) per abaixar el deute",
     "Recortar el gasto político (asesores, organismos duplicados) para bajar la deuda", ()),
    ("economy", "R", "Silenci positiu: obrir un negoci amb una declaració responsable, sense esperar el permís",
     "Silencio positivo: abrir un negocio con una declaración responsable, sin esperar el permiso", ("selfemp",)),
    ("economy", "T", "Un finançament just: que la comunitat recapti i gestioni els seus impostos",
     "Una financiación justa: que la comunidad recaude y gestione sus impuestos", ("indep",)),
    # ------------------------------------------------------------ preus
    ("prices", "L", "IVA zero als aliments bàsics i control dels marges de la gran distribució",
     "IVA cero en los alimentos básicos y control de los márgenes de la gran distribución", ("lowinc",)),
    ("prices", "L", "Salari mínim al 60 % del sou mitjà i salaris i pensions actualitzats amb l'IPC",
     "Salario mínimo al 60 % del sueldo medio y salarios y pensiones actualizados con el IPC", ("worker",)),
    ("prices", "C", "Xec de 200 € per a la compra de les llars de rendes baixes",
     "Cheque de 200 € para la compra de los hogares de rentas bajas", ("lowinc", "senior")),
    ("prices", "C", "Abonament únic de transport públic a 20 € al mes, i gratuït per als menors de 26 anys",
     "Abono único de transporte público a 20 € al mes, y gratuito para los menores de 26 años", ("young",)),
    ("prices", "R", "IVA del 5 % a la llum i el gas i menys impostos als carburants",
     "IVA del 5 % en la luz y el gas y menos impuestos a los carburantes", ("rural",)),
    ("prices", "R", "Deflactar l'IRPF perquè la inflació no faci pagar més impostos",
     "Deflactar el IRPF para que la inflación no haga pagar más impuestos", ()),
    # ------------------------------------------------------------ atur
    ("unemployment", "L", "Feina garantida per als aturats de llarga durada en serveis públics, cures i medi ambient",
     "Empleo garantizado para los parados de larga duración en servicios públicos, cuidados y medio ambiente", ("unemp",)),
    ("unemployment", "C", "FP dual a totes les comarques, amb una ajuda a les empreses que contractin els alumnes",
     "FP dual en todas las comarcas, con una ayuda a las empresas que contraten a los alumnos", ("young",)),
    ("unemployment", "C", "Bonificar la contractació indefinida dels majors de 52 anys",
     "Bonificar la contratación indefinida de los mayores de 52 años", ("unemp",)),
    ("unemployment", "R", "Rebaixar les cotitzacions socials a les empreses que contractin",
     "Rebajar las cotizaciones sociales a las empresas que contraten", ("selfemp",)),
    ("unemployment", "R", "Poder cobrar part del subsidi durant un temps mentre es treballa",
     "Poder cobrar parte del subsidio durante un tiempo mientras se trabaja", ("unemp",)),
    # ------------------------------------------------------------ feina
    ("jobs", "L", "Jornada de 37,5 hores sense rebaixar el sou i registre horari digital amb multes",
     "Jornada de 37,5 horas sin bajar el sueldo y registro horario digital con multas", ("worker",)),
    ("jobs", "L", "Encarir l'acomiadament sense causa",
     "Encarecer el despido sin causa", ("worker",)),
    ("jobs", "C", "Teletreball de fins a dos dies a la setmana on la feina ho permeti i horaris flexibles per a qui té fills",
     "Teletrabajo de hasta dos días a la semana donde el trabajo lo permita y horarios flexibles para quien tiene hijos",
     ("family", "women", "univ")),
    ("jobs", "C", "Que els convenis s'actualitzin cada any amb l'IPC",
     "Que los convenios se actualicen cada año con el IPC", ("worker",)),
    ("jobs", "R", "Motxilla austríaca: una indemnització que acumula cada treballador i s'emporta si canvia de feina",
     "Mochila austriaca: una indemnización que acumula cada trabajador y se lleva si cambia de empleo", ("young",)),
    ("jobs", "R", "Abaixar les cotitzacions perquè pugi el sou net",
     "Bajar las cotizaciones para que suba el sueldo neto", ("worker",)),
    # ------------------------------------------------------------ joventut
    ("youth", "L", "Renda d'emancipació de 300 € al mes per als menors de 30 anys amb sous baixos",
     "Renta de emancipación de 300 € al mes para los menores de 30 años con sueldos bajos", ("young",)),
    ("youth", "L", "Matrícula gratuïta a la universitat pública i a l'FP",
     "Matrícula gratuita en la universidad pública y en la FP", ("young", "univ")),
    ("youth", "C", "Bo de lloguer jove de 250 € al mes, cobrat automàticament amb la declaració",
     "Bono de alquiler joven de 250 € al mes, cobrado automáticamente con la declaración", ("young",)),
    ("youth", "C", "Pla de retorn del talent: cinc anys d'IRPF reduït per als joves que tornin de l'estranger",
     "Plan de retorno del talento: cinco años de IRPF reducido para los jóvenes que vuelvan del extranjero", ("young", "univ")),
    ("youth", "R", "IRPF zero per als menors de 30 anys fins a 30.000 € de sou",
     "IRPF cero para los menores de 30 años hasta 30.000 € de sueldo", ("young",)),
    ("youth", "T", "Emancipació jove a càrrec de la comunitat: habitatge i transport per als joves que es quedin al territori",
     "Emancipación joven a cargo de la comunidad: vivienda y transporte para los jóvenes que se queden en el territorio", ("young", "rural")),
    # ------------------------------------------------------------ sanitat
    ("health", "L", "Blindar la sanitat pública per llei: cap concert nou amb la privada i llistes d'espera publicades cada mes",
     "Blindar la sanidad pública por ley: ningún concierto nuevo con la privada y listas de espera publicadas cada mes", ()),
    ("health", "L", "Dentista, ulleres i audiòfons a la sanitat pública",
     "Dentista, gafas y audífonos en la sanidad pública", ("senior", "lowinc")),
    ("health", "C", "Temps màxim garantit: 48 hores per al metge de capçalera i 60 dies per operar-se; si no, la paga la sanitat pública en un altre centre",
     "Tiempo máximo garantizado: 48 horas para el médico de cabecera y 60 días para operarse; si no, lo paga la sanidad pública en otro centro",
     ("senior",)),
    ("health", "C", "Més places MIR i un plus per als metges que vagin a pobles",
     "Más plazas MIR y un plus para los médicos que vayan a pueblos", ("rural",)),
    ("health", "R", "Que el pacient pugui triar metge i hospital, també concertat, si passa del temps màxim d'espera",
     "Que el paciente pueda elegir médico y hospital, también concertado, si pasa del tiempo máximo de espera", ()),
    ("health", "R", "Deduir a l'IRPF les assegurances mèdiques privades",
     "Deducir en el IRPF los seguros médicos privados", ("highinc", "selfemp")),
    ("health", "T", "Més finançament per a la sanitat de la comunitat i places MIR decidides per cada comunitat",
     "Más financiación para la sanidad de la comunidad y plazas MIR decididas por cada comunidad", ()),
    # ------------------------------------------------------------ educacio
    ("education", "L", "Escola de 0 a 3 anys gratuïta i universal",
     "Escuela de 0 a 3 años gratuita y universal", ("family", "women")),
    ("education", "L", "Un màxim de 20 alumnes per aula i més professors de suport",
     "Un máximo de 20 alumnos por aula y más profesores de apoyo", ("family",)),
    ("education", "C", "Sense mòbil a l'escola fins als 16 anys i tutories individuals contra l'abandonament",
     "Sin móvil en la escuela hasta los 16 años y tutorías individuales contra el abandono", ("family",)),
    ("education", "C", "Beques que cobreixin la residència i els llibres per als estudiants que estudien fora de casa",
     "Becas que cubran la residencia y los libros para los estudiantes que estudian fuera de casa", ("young", "rural")),
    ("education", "R", "Llibertat per triar escola, també concertada, i un examen de selectivitat únic a tot Espanya",
     "Libertad para elegir colegio, también concertado, y una selectividad única en toda España", ("catholic", "family")),
    ("education", "R", "Garantir el castellà com a llengua vehicular a totes les comunitats",
     "Garantizar el castellano como lengua vehicular en todas las comunidades", ()),
    ("education", "T", "Blindar l'escola en la llengua pròpia i la competència plena d'educació",
     "Blindar la escuela en la lengua propia y la competencia plena de educación", ("indep",)),
    # ------------------------------------------------------------ pensions
    ("pensions", "L", "Que cap pensió mínima quedi per sota del salari mínim i revalorització sempre amb l'IPC",
     "Que ninguna pensión mínima quede por debajo del salario mínimo y revalorización siempre con el IPC", ("senior", "lowinc")),
    ("pensions", "L", "Treure el topall de cotització als sous alts perquè ajudin a pagar les pensions",
     "Quitar el tope de cotización a los sueldos altos para que ayuden a pagar las pensiones", ()),
    ("pensions", "C", "Poder cobrar el 100 % de la pensió i continuar treballant",
     "Poder cobrar el 100 % de la pensión y seguir trabajando", ("senior", "selfemp")),
    ("pensions", "C", "Pla de pensions d'empresa per a tots els treballadors, amb aportació de l'empresa",
     "Plan de pensiones de empresa para todos los trabajadores, con aportación de la empresa", ("worker",)),
    ("pensions", "R", "Pensions mínimes exemptes d'IRPF i deduccions per estalviar per a la jubilació",
     "Pensiones mínimas exentas de IRPF y deducciones por ahorrar para la jubilación", ("senior",)),
    ("pensions", "R", "Jubilació flexible: a partir dels 65 anys, cadascú tria quan es jubila sense penalització",
     "Jubilación flexible: a partir de los 65 años, cada uno elige cuándo se jubila sin penalización", ("senior",)),
    ("pensions", "T", "Que la comunitat gestioni les pensions no contributives i hi pugui afegir un complement",
     "Que la comunidad gestione las pensiones no contributivas y pueda añadir un complemento", ("senior",)),
    # ------------------------------------------------------------ immigracio
    ("immigration", "L", "Regularitzar els immigrants que ja hi viuen i treballen",
     "Regularizar a los inmigrantes que ya viven y trabajan aquí", ("immig",)),
    ("immigration", "L", "Classes d'idioma gratuïtes i mediadors als barris amb més immigració",
     "Clases de idioma gratuitas y mediadores en los barrios con más inmigración", ("immig",)),
    ("immigration", "C", "Contractació en origen per als sectors que no troben treballadors: camp, cures, hostaleria i construcció",
     "Contratación en origen para los sectores que no encuentran trabajadores: campo, cuidados, hostelería y construcción",
     ("rural", "selfemp")),
    ("immigration", "C", "Resoldre l'asil en sis mesos, i acords de retorn amb els països d'origen per a qui no en tingui dret",
     "Resolver el asilo en seis meses, y acuerdos de retorno con los países de origen para quien no tenga derecho", ()),
    ("immigration", "R", "Expulsar els estrangers condemnats per delictes greus",
     "Expulsar a los extranjeros condenados por delitos graves", ("security",)),
    ("immigration", "R", "Que l'arrelament exigeixi parlar l'idioma, tenir feina i no tenir antecedents",
     "Que el arraigo exija hablar el idioma, tener trabajo y no tener antecedentes", ()),
    ("immigration", "R", "Més agents i mitjans a les fronteres de Ceuta, Melilla i les Canàries",
     "Más agentes y medios en las fronteras de Ceuta, Melilla y Canarias", ("security",)),
    ("immigration", "T", "Que la comunitat decideixi els permisos de treball i la política d'acollida",
     "Que la comunidad decida los permisos de trabajo y la política de acogida", ("indep",)),
    # ------------------------------------------------------------ seguretat
    ("security", "L", "Policia de proximitat als barris, més enllumenat i serveis socials",
     "Policía de proximidad en los barrios, más alumbrado y servicios sociales", ()),
    ("security", "L", "Prevenció de la violència juvenil a les escoles i als barris",
     "Prevención de la violencia juvenil en las escuelas y en los barrios", ("young", "family")),
    ("security", "C", "Llei contra la multireincidència: més pena per a qui roba una vegada i una altra",
     "Ley contra la multirreincidencia: más pena para quien roba una y otra vez", ("senior",)),
    ("security", "C", "Judicis ràpids en una setmana per als furts i les baralles",
     "Juicios rápidos en una semana para los hurtos y las peleas", ()),
    ("security", "R", "Presó per als multireincidents i més policies al carrer",
     "Cárcel para los multirreincidentes y más policías en la calle", ("senior",)),
    ("security", "R", "Pistoles elèctriques, més mitjans i equiparació salarial per a policies i guàrdies civils",
     "Pistolas eléctricas, más medios y equiparación salarial para policías y guardias civiles", ("security",)),
    ("security", "T", "Que la policia de la comunitat tingui totes les competències",
     "Que la policía autonómica tenga todas las competencias", ("indep",)),
    # ------------------------------------------------------------ corrupcio
    ("corruption", "L", "Oficina anticorrupció independent i que les empreses condemnades no puguin contractar amb l'administració en deu anys",
     "Oficina anticorrupción independiente y que las empresas condenadas no puedan contratar con la administración en diez años", ()),
    ("corruption", "C", "Tots els contractes públics i les agendes dels ministres, publicats en obert",
     "Todos los contratos públicos y las agendas de los ministros, publicados en abierto", ("univ",)),
    ("corruption", "C", "Ningú amb un judici obert per corrupció a les llistes",
     "Nadie con un juicio abierto por corrupción en las listas", ()),
    ("corruption", "R", "Penes més dures per malversació i cap indult sense retornar el que s'ha robat",
     "Penas más duras por malversación y ningún indulto sin devolver lo robado", ()),
    ("corruption", "L", "Protecció i recompensa per als funcionaris que denunciïn la corrupció",
     "Protección y recompensa para los funcionarios que denuncien la corrupción", ()),
    # ------------------------------------------------------------ politica
    ("politics", "C", "Limitar a dos mandats (vuit anys) el president del Govern",
     "Limitar a dos mandatos (ocho años) al presidente del Gobierno", ()),
    ("politics", "C", "Llistes desbloquejades al Congrés: el votant pot marcar els candidats que prefereix",
     "Listas desbloqueadas en el Congreso: el votante puede marcar a los candidatos que prefiere", ("univ",)),
    ("politics", "L", "Comptes dels partits en obert i límit a les donacions privades",
     "Cuentas de los partidos en abierto y límite a las donaciones privadas", ()),
    ("politics", "R", "Menys assessors i càrrecs de confiança, i sous dels polítics lligats als dels funcionaris",
     "Menos asesores y cargos de confianza, y sueldos de los políticos ligados a los de los funcionarios", ()),
    ("politics", "R", "Que governi la llista més votada si ningú no té majoria",
     "Que gobierne la lista más votada si nadie tiene mayoría", ()),
    ("politics", "T", "Que les decisions es prenguin més a prop: més competències per als ajuntaments i la comunitat",
     "Que las decisiones se tomen más cerca: más competencias para los ayuntamientos y la comunidad", ()),
    # ------------------------------------------------------------ acords
    ("agreement", "C", "Pactes d'Estat de pensions, habitatge i educació que no es toquin en dues legislatures",
     "Pactos de Estado de pensiones, vivienda y educación que no se toquen en dos legislaturas", ()),
    ("agreement", "C", "Codi de conducta al Congrés amb sancions per als insults",
     "Código de conducta en el Congreso con sanciones por los insultos", ("senior",)),
    ("agreement", "L", "Llei contra els discursos d'odi a les xarxes",
     "Ley contra los discursos de odio en las redes", ()),
    ("agreement", "R", "Grans acords només amb els partits constitucionalistes",
     "Grandes acuerdos solo con los partidos constitucionalistas", ()),
    # ------------------------------------------------------------ desigualtat
    ("inequality", "L", "Ingrés mínim vital automàtic per a totes les llars que hi tenen dret",
     "Ingreso mínimo vital automático para todos los hogares que tienen derecho", ("lowinc",)),
    ("inequality", "L", "Prestació de 200 € al mes per fill, pagada amb un impost a les grans fortunes",
     "Prestación de 200 € al mes por hijo, pagada con un impuesto a las grandes fortunas", ("family", "lowinc")),
    ("inequality", "C", "Prestació de 100 € al mes per fill fins als 18 anys",
     "Prestación de 100 € al mes por hijo hasta los 18 años", ("family",)),
    ("inequality", "C", "Transparència salarial a les empreses per tancar la bretxa entre homes i dones",
     "Transparencia salarial en las empresas para cerrar la brecha entre hombres y mujeres", ("women",)),
    ("inequality", "R", "Que cap ajuda es perdi per treballar: cobrar sempre més treballant",
     "Que ninguna ayuda se pierda por trabajar: cobrar siempre más trabajando", ("lowinc",)),
    ("inequality", "R", "Pujar el mínim exempt de l'IRPF perquè els sous baixos no paguin",
     "Subir el mínimo exento del IRPF para que los sueldos bajos no paguen", ("worker", "lowinc")),
    # ------------------------------------------------------------ dones
    ("women", "L", "Jutjats de violència sobre la dona a totes les comarques i atenció les 24 hores",
     "Juzgados de violencia sobre la mujer en todas las comarcas y atención las 24 horas", ("women",)),
    ("women", "L", "Permís de cures pagat per atendre fills i familiars",
     "Permiso de cuidados pagado para atender a hijos y familiares", ("women", "family")),
    ("women", "C", "Polsera de control per a tots els agressors amb ordre d'allunyament",
     "Pulsera de control para todos los agresores con orden de alejamiento", ("women",)),
    ("women", "C", "Educació afectiva i sexual a totes les escoles",
     "Educación afectiva y sexual en todas las escuelas", ("young",)),
    ("women", "R", "Registre públic d'agressors sexuals i penes més dures",
     "Registro público de agresores sexuales y penas más duras", ("women", "family")),
    # ------------------------------------------------------------ clima
    ("climate", "L", "Renovables públiques i comunitats energètiques als barris perquè la llum sigui més barata",
     "Renovables públicas y comunidades energéticas en los barrios para que la luz sea más barata", ()),
    ("climate", "L", "Rodalies i trens regionals que funcionin, amb una inversió garantida per llei",
     "Cercanías y trenes regionales que funcionen, con una inversión garantizada por ley", ("young", "worker")),
    ("climate", "C", "Un pacte d'Estat per a les emergències (incendis, DANA, sequera) amb un fons estable",
     "Un pacto de Estado para las emergencias (incendios, DANA, sequía) con un fondo estable", ("rural",)),
    ("climate", "C", "Ajudes per aïllar les cases i posar plaques solars, retornades amb l'estalvi de la factura",
     "Ayudas para aislar las casas y poner placas solares, devueltas con el ahorro de la factura", ("family", "senior")),
    ("climate", "R", "Allargar la vida de les nuclears per abaratir la llum",
     "Alargar la vida de las nucleares para abaratar la luz", ()),
    ("climate", "R", "Neteja de boscos tot l'any i més embassaments contra la sequera i els incendis",
     "Limpieza de montes todo el año y más embalses contra la sequía y los incendios", ("rural",)),
    ("climate", "T", "Que la comunitat tingui els mitjans i els diners de les emergències",
     "Que la comunidad tenga los medios y el dinero de las emergencias", ()),
    # ------------------------------------------------------------ camp
    ("farming", "L", "Que ningú no pugui comprar la collita per sota del que costa produir-la, amb una agència que ho vigili",
     "Que nadie pueda comprar la cosecha por debajo de lo que cuesta producirla, con una agencia que lo vigile", ("rural",)),
    ("farming", "C", "Una sola declaració de la PAC l'any i menys paperassa",
     "Una sola declaración de la PAC al año y menos papeleo", ("rural",)),
    ("farming", "C", "Assegurances agràries més barates contra la sequera i la pedra",
     "Seguros agrarios más baratos contra la sequía y el granizo", ("rural",)),
    ("farming", "R", "Que els productes de fora compleixin les mateixes normes que els d'aquí",
     "Que los productos de fuera cumplan las mismas normas que los de aquí", ("rural",)),
    ("farming", "R", "Aigua per al camp: embassaments, regadius i transvasaments",
     "Agua para el campo: embalses, regadíos y trasvases", ("rural",)),
    # ------------------------------------------------------------ dependencia
    ("care", "L", "Ajuda de la dependència en un màxim de sis mesos i cuidadores professionals amb sous dignes",
     "Ayuda de la dependencia en un máximo de seis meses y cuidadoras profesionales con sueldos dignos", ("senior", "women")),
    ("care", "C", "Prestació per a les famílies que cuiden a casa i dies de descans per al cuidador",
     "Prestación para las familias que cuidan en casa y días de descanso para el cuidador", ("women", "family")),
    ("care", "C", "Pla contra la soledat no desitjada de la gent gran: visites, centres de dia i teleassistència",
     "Plan contra la soledad no deseada de los mayores: visitas, centros de día y teleasistencia", ("senior",)),
    ("care", "R", "Xec perquè cada família triï residència o ajuda a casa, pública o privada",
     "Cheque para que cada familia elija residencia o ayuda en casa, pública o privada", ("senior",)),
    # ------------------------------------------------------------ justicia
    ("justice", "C", "Més jutges, fins a la mitjana europea, perquè cap judici duri més d'un any",
     "Más jueces, hasta la media europea, para que ningún juicio dure más de un año", ()),
    ("justice", "R", "Que els jutges triïn els seus representants al Consell General del Poder Judicial",
     "Que los jueces elijan a sus representantes en el Consejo General del Poder Judicial", ()),
    ("justice", "L", "Justícia gratuïta més àmplia i un Consell del Poder Judicial renovat a temps",
     "Justicia gratuita más amplia y un Consejo del Poder Judicial renovado a tiempo", ()),
    ("justice", "T", "Que el tribunal superior de la comunitat sigui l'última instància",
     "Que el tribunal superior de la comunidad sea la última instancia", ()),
    # ------------------------------------------------------------ desinformacio
    ("media", "C", "Alfabetització mediàtica a l'escola i publicitat institucional repartida amb criteris públics",
     "Alfabetización mediática en la escuela y publicidad institucional repartida con criterios públicos", ("family",)),
    ("media", "L", "Que les plataformes retirin en 24 hores els bulos denunciats o paguin multes",
     "Que las plataformas retiren en 24 horas los bulos denunciados o paguen multas", ()),
    ("media", "R", "Llibertat d'expressió: només un jutge pot fer retirar un contingut",
     "Libertad de expresión: solo un juez puede hacer retirar un contenido", ()),
    # ------------------------------------------------------------ territori
    ("territory", "R", "Defensar la unitat d'Espanya i tornar a castigar la sedició",
     "Defender la unidad de España y volver a castigar la sedición", ()),
    ("territory", "R", "Cap referèndum d'independència i les mateixes competències per a totes les comunitats",
     "Ningún referéndum de independencia y las mismas competencias para todas las comunidades", ()),
    ("territory", "C", "Un finançament autonòmic nou i igual per a tothom, pactat entre totes les comunitats",
     "Una financiación autonómica nueva e igual para todos, pactada entre todas las comunidades", ()),
    ("territory", "C", "Un Senat que sigui de veritat la cambra de les comunitats",
     "Un Senado que sea de verdad la cámara de las comunidades", ()),
    ("territory", "L", "Una Espanya federal que reconegui que és plurinacional",
     "Una España federal que reconozca que es plurinacional", ("indep",)),
    ("territory", "T", "Un referèndum d'autodeterminació pactat amb l'Estat",
     "Un referéndum de autodeterminación pactado con el Estado", ("indep",)),
    ("territory", "T", "Hisenda pròpia que reculli tots els impostos i pagui una quota a l'Estat, com el concert basc",
     "Hacienda propia que recaude todos los impuestos y pague un cupo al Estado, como el concierto vasco", ("indep",)),
    ("territory", "T", "Oficialitat del català, el basc i el gallec a la Unió Europea",
     "Oficialidad del catalán, el vasco y el gallego en la Unión Europea", ("indep",)),
    # ------------------------------------------------------------ impostos
    ("taxes", "R", "Abaixar l'IRPF i suprimir l'impost de successions entre pares i fills",
     "Bajar el IRPF y suprimir el impuesto de sucesiones entre padres e hijos", ("family", "highinc", "senior")),
    ("taxes", "R", "Impost de societats del 15 % per a les pimes",
     "Impuesto de sociedades del 15 % para las pymes", ("selfemp",)),
    ("taxes", "C", "Que els autònoms cotitzin pel que guanyen de veritat i no paguin quota si no arriben al salari mínim",
     "Que los autónomos coticen por lo que ganan de verdad y no paguen cuota si no llegan al salario mínimo", ("selfemp",)),
    ("taxes", "L", "Un tipus mínim real del 15 % a les grans empreses perquè no pagui més qui guanya menys",
     "Un tipo mínimo real del 15 % a las grandes empresas para que no pague más quien gana menos", ()),
    ("taxes", "T", "Que els impostos que es paguen a la comunitat es quedin a la comunitat",
     "Que los impuestos que se pagan en la comunidad se queden en la comunidad", ("indep",)),
    # ------------------------------------------------------------ serveis
    ("services", "C", "Atenció presencial sense cita prèvia a la Seguretat Social, el SEPE i Hisenda",
     "Atención presencial sin cita previa en la Seguridad Social, el SEPE y Hacienda", ("senior", "immig")),
    ("services", "C", "Tots els tràmits en una sola web i un sol cop: l'administració no pot demanar un paper que ja té",
     "Todos los trámites en una sola web y una sola vez: la administración no puede pedir un papel que ya tiene", ("selfemp",)),
    ("services", "L", "Més treballadors a la sanitat, l'escola i la Seguretat Social",
     "Más trabajadores en la sanidad, la escuela y la Seguridad Social", ()),
    ("services", "R", "Avaluar cada servei públic i acabar amb les duplicitats entre administracions",
     "Evaluar cada servicio público y acabar con las duplicidades entre administraciones", ()),
    ("services", "T", "Rodalies i els trens regionals gestionats per la comunitat",
     "Cercanías y los trenes regionales gestionados por la comunidad", ("indep",)),
    # ------------------------------------------------------------ democracia
    ("democracy", "C", "Que el Congrés hagi de votar en sis mesos qualsevol iniciativa popular amb 250.000 signatures",
     "Que el Congreso tenga que votar en seis meses cualquier iniciativa popular con 250.000 firmas", ()),
    ("democracy", "R", "Fiscal general, CIS i RTVE elegits per tres cinquens del Congrés",
     "Fiscal general, CIS y RTVE elegidos por tres quintos del Congreso", ()),
    ("democracy", "L", "Consultes ciutadanes més fàcils als municipis i a les comunitats",
     "Consultas ciudadanas más fáciles en los municipios y las comunidades", ()),
    # ------------------------------------------------------------ mon
    ("world", "L", "Embargament d'armes a Israel i reconeixement ple de Palestina",
     "Embargo de armas a Israel y reconocimiento pleno de Palestina", ()),
    ("world", "L", "No pujar la despesa militar al 5 % del PIB",
     "No subir el gasto militar al 5 % del PIB", ()),
    ("world", "C", "Una defensa europea comuna i ajuda a Ucraïna fins a una pau justa",
     "Una defensa europea común y ayuda a Ucrania hasta una paz justa", ("univ",)),
    ("world", "R", "Arribar al 2 % del PIB en defensa i modernitzar l'exèrcit",
     "Llegar al 2 % del PIB en defensa y modernizar el ejército", ("security",)),
    # ------------------------------------------------------------ fronteres
    ("borders", "C", "Que la UE pagui una part de la vigilància de Ceuta i Melilla",
     "Que la UE pague una parte de la vigilancia de Ceuta y Melilla", ()),
    ("borders", "R", "Ceuta i Melilla, explícitament sota la protecció de l'OTAN",
     "Ceuta y Melilla, explícitamente bajo la protección de la OTAN", ("security",)),
    ("borders", "L", "Vies legals d'arribada i protecció dels menors que arriben sols",
     "Vías legales de llegada y protección de los menores que llegan solos", ()),
    # ------------------------------------------------------------ valors
    ("values", "R", "100 € al mes per fill i menys IRPF a les famílies nombroses",
     "100 € al mes por hijo y menos IRPF a las familias numerosas", ("family", "catholic")),
    ("values", "C", "Servei civil voluntari per als joves i educació en convivència",
     "Servicio civil voluntario para los jóvenes y educación en convivencia", ("young",)),
    ("values", "L", "Educació en igualtat i contra l'odi a totes les escoles",
     "Educación en igualdad y contra el odio en todas las escuelas", ()),
]

# Propostes per a un tipus de grup, encara que el tema no surti entre els
# seus problemes (etiqueta, orientacio, ca, es).
_G = [
    ("young", "C", "Primera feina amb formació i sense cotitzacions el primer any", "Primer empleo con formación y sin cotizaciones el primer año"),
    ("young", "L", "Lloguer jove topat: cap jove no ha de pagar més del 30 % del sou en lloguer", "Alquiler joven topado: ningún joven debe pagar más del 30 % del sueldo en alquiler"),
    ("young", "R", "IRPF zero per als menors de 30 anys fins a 30.000 € de sou", "IRPF cero para los menores de 30 años hasta 30.000 € de sueldo"),
    ("young", "T", "Pla de retorn per als joves que han marxat a fer feina fora", "Plan de retorno para los jóvenes que se han ido a trabajar fuera"),
    ("senior", "C", "Dentista i ulleres pagats per la sanitat pública als majors de 65 anys", "Dentista y gafas pagados por la sanidad pública a los mayores de 65 años"),
    ("senior", "L", "Pensions mínimes iguals al salari mínim", "Pensiones mínimas iguales al salario mínimo"),
    ("senior", "R", "Pensions sense IRPF fins a 20.000 € l'any", "Pensiones sin IRPF hasta 20.000 € al año"),
    ("senior", "T", "Atenció a la gent gran gestionada des de la comunitat i els ajuntaments", "Atención a los mayores gestionada desde la comunidad y los ayuntamientos"),
    ("selfemp", "C", "Quota d'autònoms zero per a qui no arribi al salari mínim", "Cuota de autónomos cero para quien no llegue al salario mínimo"),
    ("selfemp", "L", "Baixa pagada des del primer dia i atur per als autònoms que tanquen", "Baja pagada desde el primer día y paro para los autónomos que cierran"),
    ("selfemp", "R", "Menys normes per a les pimes: cada norma nova n'ha de treure dues de velles", "Menos normas para las pymes: cada norma nueva debe quitar dos viejas"),
    ("selfemp", "T", "Finestreta única de la comunitat per obrir un negoci en una setmana", "Ventanilla única de la comunidad para abrir un negocio en una semana"),
    ("unemp", "C", "Orientador personal per a cada aturat i formació pagada en les feines que falten", "Orientador personal para cada parado y formación pagada en los empleos que faltan"),
    ("unemp", "L", "Subsidi per als majors de 52 anys fins a la jubilació, amb cotització", "Subsidio para los mayores de 52 años hasta la jubilación, con cotización"),
    ("unemp", "R", "Rebaixa de cotitzacions a qui contracti un aturat de llarga durada", "Rebaja de cotizaciones a quien contrate a un parado de larga duración"),
    ("women", "C", "Escola bressol gratuïta i permisos iguals i intransferibles per als dos pares", "Escuela infantil gratuita y permisos iguales e intransferibles para los dos padres"),
    ("women", "L", "Transparència salarial obligatòria a totes les empreses", "Transparencia salarial obligatoria en todas las empresas"),
    ("women", "R", "Ajudes a la maternitat per a les mares treballadores i autònomes", "Ayudas a la maternidad para las madres trabajadoras y autónomas"),
    ("family", "C", "Permís de naixement de 20 setmanes per a cada pare", "Permiso de nacimiento de 20 semanas para cada padre"),
    ("family", "L", "Prestació universal de 200 € al mes per fill", "Prestación universal de 200 € al mes por hijo"),
    ("family", "R", "Deducció de 1.200 € a l'IRPF per cada fill", "Deducción de 1.200 € en el IRPF por cada hijo"),
    ("rural", "C", "Banda ampla, cobertura mòbil, metge i caixer a tots els pobles", "Banda ancha, cobertura móvil, médico y cajero en todos los pueblos"),
    ("rural", "R", "IRPF reduït per viure a les zones despoblades, com a Sòria, Conca i Terol", "IRPF reducido por vivir en las zonas despobladas, como en Soria, Cuenca y Teruel"),
    ("rural", "L", "Transport públic a la demanda per als pobles sense autobús", "Transporte público a demanda para los pueblos sin autobús"),
    ("rural", "T", "Que els pobles decideixin com es gasten els fons contra la despoblació", "Que los pueblos decidan cómo se gastan los fondos contra la despoblación"),
    ("immig", "C", "Homologar els títols estrangers en sis mesos, no en dos anys", "Homologar los títulos extranjeros en seis meses, no en dos años"),
    ("immig", "C", "Cita d'estrangeria nominal i per internet, sense revenda de cites", "Cita de extranjería nominal y por internet, sin reventa de citas"),
    ("immig", "L", "Vot a les eleccions municipals per a tots els residents de llarga durada", "Voto en las elecciones municipales para todos los residentes de larga duración"),
    ("immig", "L", "Nacionalitat als cinc anys de residència legal, i no als deu, per als que no són iberoamericans", "Nacionalidad a los cinco años de residencia legal, y no a los diez, para los que no son iberoamericanos"),
    ("immig", "R", "Immigració ordenada: contractes en origen i premiar qui treballa i s'integra", "Inmigración ordenada: contratos en origen y premiar a quien trabaja y se integra"),
    ("immig", "R", "Prioritat a la immigració iberoamericana, per llengua i cultura", "Prioridad a la inmigración iberoamericana, por lengua y cultura"),
    ("immig", "T", "Acollida i classes de la llengua pròpia gestionades per la comunitat", "Acogida y clases de la lengua propia gestionadas por la comunidad"),
    ("latam", "C", "Convenis de pensions i de carnet de conduir amb tots els països iberoamericans", "Convenios de pensiones y de carné de conducir con todos los países iberoamericanos"),
    ("exile", "R", "Una política exterior ferma amb els governs de Veneçuela, Cuba i Nicaragua", "Una política exterior firme con los gobiernos de Venezuela, Cuba y Nicaragua"),
    ("exile", "C", "Protecció humanitària ràpida per als veneçolans que arriben", "Protección humanitaria rápida para los venezolanos que llegan"),
    ("abroad_es", "C", "Que comptin per a la pensió tots els anys treballats a l'estranger", "Que cuenten para la pensión todos los años trabajados en el extranjero"),
    ("indep", "T", "Un referèndum d'autodeterminació pactat amb l'Estat", "Un referéndum de autodeterminación pactado con el Estado"),
    ("indep", "T", "Hisenda pròpia i un finançament com el concert basc", "Hacienda propia y una financiación como el concierto vasco"),
    ("indep", "L", "Desjudicialitzar el conflicte i una Espanya federal i plurinacional", "Desjudicializar el conflicto y una España federal y plurinacional"),
    ("indep", "C", "Traspassar Rodalies i el 100 % de l'IRPF, i oficialitat de la llengua a la UE", "Traspasar Cercanías y el 100 % del IRPF, y oficialidad de la lengua en la UE"),
    ("indep", "R", "Menys impostos i menys burocràcia per a les pimes catalanes, basques i gallegues", "Menos impuestos y menos burocracia para las pymes catalanas, vascas y gallegas"),
    ("state", "C", "Bilingüisme a l'escola i a l'administració: les dues llengües, amb els mateixos drets", "Bilingüismo en la escuela y en la administración: las dos lenguas, con los mismos derechos"),
    ("state", "R", "Garantir que a l'escola es pugui estudiar en castellà", "Garantizar que en la escuela se pueda estudiar en castellano"),
    ("state", "L", "Més inversió de l'Estat en trens i habitatge a la comunitat, pactada amb el govern autonòmic", "Más inversión del Estado en trenes y vivienda en la comunidad, pactada con el gobierno autonómico"),
    ("catholic", "R", "Llibertat d'educació i la religió com a assignatura optativa amb nota", "Libertad de educación y la religión como asignatura optativa con nota"),
    ("catholic", "C", "Més suport a les entitats socials de l'Església, com Càritas, a través de la casella del 0,7 %", "Más apoyo a las entidades sociales de la Iglesia, como Cáritas, a través de la casilla del 0,7 %"),
    ("catholic", "L", "Acollida digna dels migrants amb les entitats religioses i socials", "Acogida digna de los migrantes con las entidades religiosas y sociales"),
    ("secular", "L", "Estat laic: revisar els acords amb la Santa Seu", "Estado laico: revisar los acuerdos con la Santa Sede"),
    ("secular", "C", "Cures pal·liatives i eutanàsia garantides a tots els hospitals", "Cuidados paliativos y eutanasia garantizados en todos los hospitales"),
    ("univ", "C", "Sous de recerca europeus i contractes estables per als investigadors", "Sueldos de investigación europeos y contratos estables para los investigadores"),
    ("univ", "R", "Menys impostos al treball qualificat perquè el talent no marxi", "Menos impuestos al trabajo cualificado para que el talento no se vaya"),
    ("univ", "L", "Universitat pública gratuïta i més places als graus amb més demanda", "Universidad pública gratuita y más plazas en los grados con más demanda"),
    ("worker", "L", "Jornada de 37,5 hores i salari mínim al 60 % del sou mitjà", "Jornada de 37,5 horas y salario mínimo al 60 % del sueldo medio"),
    ("worker", "C", "Formació pagada durant la jornada per pujar de categoria", "Formación pagada durante la jornada para subir de categoría"),
    ("worker", "R", "Menys IRPF a les hores extres i als sous baixos", "Menos IRPF en las horas extra y en los sueldos bajos"),
    ("lowinc", "L", "Ingrés mínim vital automàtic i bo social de llum i gas per a tothom qui hi té dret", "Ingreso mínimo vital automático y bono social de luz y gas para todos los que tienen derecho"),
    ("lowinc", "C", "Xec de 200 € per a la compra", "Cheque de 200 € para la compra"),
    ("lowinc", "R", "Cap impost per als sous de menys de 18.000 € l'any", "Ningún impuesto para los sueldos de menos de 18.000 € al año"),
    ("highinc", "R", "Suprimir l'impost de patrimoni i el de successions entre pares i fills", "Suprimir el impuesto de patrimonio y el de sucesiones entre padres e hijos"),
    ("highinc", "C", "Deduccions per invertir en empreses noves i en habitatge de lloguer assequible", "Deducciones por invertir en empresas nuevas y en vivienda de alquiler asequible"),
    ("highinc", "L", "Que les rendes del capital tributin com les del treball", "Que las rentas del capital tributen como las del trabajo"),
    ("security", "R", "Equiparació salarial i més mitjans per a policies i guàrdies civils", "Equiparación salarial y más medios para policías y guardias civiles"),
    ("security", "C", "Professió de risc per a policies i guàrdies civils, amb jubilació anticipada", "Profesión de riesgo para policías y guardias civiles, con jubilación anticipada"),
    ("security", "L", "Més plantilla de policia de proximitat i millors condicions laborals", "Más plantilla de policía de proximidad y mejores condiciones laborales"),
    ("left", "L", "Habitatge, sanitat i escola públiques com a prioritat del pressupost", "Vivienda, sanidad y escuela públicas como prioridad del presupuesto"),
    ("right", "R", "Menys impostos, menys despesa política i més seguretat", "Menos impuestos, menos gasto político y más seguridad"),
    ("centre", "C", "Acords entre els grans partits en pensions, habitatge i finançament", "Acuerdos entre los grandes partidos en pensiones, vivienda y financiación"),
]

PROPOSALS = [{"topic": t, "o": o, "ca": ca, "es": es, "tags": set(tags)} for t, o, ca, es, tags in _P]
GROUP_PROPOSALS = [{"tag": t, "o": o, "ca": ca, "es": es} for t, o, ca, es in _G]


def tags_for(gid, persona_tags=None):
    """Etiquetes d'un grup de perfils.json a partir del seu id (dimensio:valor)."""
    key, _, val = gid.partition(":")
    t = set()
    if key == "persona":
        t |= set((persona_tags or {}).get(val, []))
    if key == "sexage":
        sex, _, age = val.partition(":")
        if sex == "Mujer":
            t.add("women")
        t |= {"18-29": {"young"}, "65+": {"senior"}, "30-44": {"family"}}.get(age, set())
    if key == "age":
        t |= {"18-29": {"young"}, "65+": {"senior"}, "30-44": {"family"}}.get(val, set())
    if key == "sex" and val == "Mujer":
        t.add("women")
    if key == "work":
        t |= {"Jubilado": {"senior"}, "Paro": {"unemp"}, "Estudiante": {"young", "univ"}, "Trabaja": {"worker"},
              "Trabajo doméstico no remunerado": {"family", "women"}}.get(val, set())
    if key == "employ":
        t |= {"selfemp"} if not val.startswith("Asalariado") else {"worker"}
    if key == "job":
        if val.startswith(("Agricultores",)):
            t.add("rural")
        elif val.startswith(("Ocupaciones militares",)):
            t.add("security")
        elif val.startswith(("Directores", "Profesionales")):
            t.add("univ")
        else:
            t.add("worker")
    if key == "studies" and val == "Superiores":
        t.add("univ")
    if key == "studies" and val in ("Primaria", "Secundaria 1ª etapa"):
        t.add("worker")
    if key == "class":
        t |= {"Clase alta y media alta": {"highinc"}, "Clase trabajadora/obrera/proletariado": {"worker"},
              "Clase baja/pobre": {"lowinc"}}.get(val, set())
    if key == "income":
        t |= {"Menos de 1.100 €": {"lowinc"}, "Más de 5.000 €": {"highinc"}, "De 3.901 a 5.000 €": {"highinc"}}.get(val, set())
    if key == "civil":
        t |= {"Casado/a": {"family"}, "Viudo/a": {"senior"}}.get(val, set())
    if key == "town" and val in ("<10k",):
        t.add("rural")
    if key == "origin" and val != "spain":
        t.add("immig")
        if val == "latam":
            t.add("latam")
    if key == "natio" and val.startswith("La ha adquirido"):
        t.add("immig")
    if key == "origin2":
        t.add("immig" if val != "west" else "abroad_es")
        if val in ("ven", "andes", "sud", "carib"):
            t.add("latam")
        if val in ("ven", "carib"):
            t.add("exile")
    if key == "migr":
        t.add("immig" if val == "acq" else "abroad_es")
    if key == "national":
        t.add("indep" if val in ("cat_ind", "eus_nat", "gal_bng", "ind_all") else "state")
    if key == "religion":
        if val == "Católico/a practicante":
            t.add("catholic")
        elif val in ("Ateo/a", "Agnóstico/a", "Indiferente, no creyente"):
            t.add("secular")
    if key == "ideology":
        t.add({"1-2": "left", "3-4": "left", "5-6": "centre", "7-8": "right", "9-10": "right"}[val])
    return t


def for_group(party, lang, topics, tags, n_topic=3, n_group=2):
    """Propostes per a un grup: per a cada tema que el preocupa (en ordre), la
    de l'orientacio del partit que millor li escau; despres, les del grup."""
    fam = FAMILY.get(party, "C")
    out, seen = [], set()
    for tp in topics:
        if tp not in TOPICS:
            continue
        cands = [p for p in PROPOSALS if p["topic"] == tp and p["o"] in fam and p[lang] not in seen]
        if not cands:
            continue
        # Primer les adreçades al grup; despres les generals; al final, les
        # adreçades a un altre tipus de grup.
        cands.sort(key=lambda p: (-len(p["tags"] & tags), bool(p["tags"]) and not (p["tags"] & tags), fam.index(p["o"])))
        p = cands[0]
        seen.add(p[lang])
        out.append({"topic": TOPICS[tp][0 if lang == "ca" else 1], "l": p[lang], "kind": "topic"})
        if len([x for x in out if x["kind"] == "topic"]) >= n_topic:
            break
    g = [p for p in GROUP_PROPOSALS if p["tag"] in tags and p["o"] in fam and p[lang] not in seen]
    g.sort(key=lambda p: fam.index(p["o"]))
    for p in g[:n_group]:
        seen.add(p[lang])
        out.append({"topic": None, "l": p[lang], "kind": "group"})
    return out


def catalog(party, lang):
    """{tema: [propostes del partit]} per a la fitxa."""
    fam = FAMILY.get(party, "C")
    out = {}
    for p in PROPOSALS:
        if p["o"] in fam:
            out.setdefault(p["topic"], []).append((fam.index(p["o"]), p[lang]))
    return {t: [x for _o, x in sorted(v, key=lambda z: z[0])] for t, v in out.items()}
