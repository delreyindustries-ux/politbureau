# D'on surten aquests fitxers

Els dos ZIP d'aquesta carpeta són **dades obertes del Ministeri de l'Interior**,
descarregades de:

<https://infoelectoral.interior.gob.es/estaticos/docxl/apliextr/>

| Fitxer | Procés |
| --- | --- |
| `02202307_MUNI.zip` | Eleccions al Congrés dels Diputats, 23 de juliol de 2023 |
| `04202305_MUNI.zip` | Eleccions municipals, 28 de maig de 2023 |

## Per què són al repositori i no es baixen cada dia

Perquè **el servidor del Ministeri no respon des dels servidors de GitHub**. La
primera publicació automàtica (29/08/2026) va fallar amb `TimeoutError` als 30
segons en cadascuna de les quatre càrregues: la connexió TCP amb
`infoelectoral.interior.gob.es` no s'arriba a establir. Des d'una connexió
espanyola sí que funciona.

Al marge d'això, tenir-los aquí és millor disseny: són resultats de **2023 i no
canviaran mai**. Baixar-los cada matí era una dependència diària d'un servidor
alié per a unes dades congelades. El que sí que s'actualitza cada dia són les
enquestes, que venen de Wikipedia.

## Llicència

L'avís legal d'infoelectoral autoritza expressament la reutilització de les
dades, **també amb finalitats comercials**, citant-ne l'origen. La citació surt
a la pàgina de metodologia del lloc i al peu de cada fitxa de territori.

`FICHEROS.txt` no és al repositori: és la documentació de format del Ministeri,
no la necessita el codi, i les posicions reals dels camps estan deduïdes i
documentades a `src/politbureau/ingest/infoelectoral.py`.
