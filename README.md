# Polit Bureau

Web pública de resultats electorals i estimació de vot per als **8.131 municipis
d'Espanya**. Llegeix cada dia les enquestes publicades, en calcula la mitjana
ponderada i les projecta sobre cada territori.

Es genera com a **lloc estàtic** (16.455 fitxers) i es publica sol cada matí amb
GitHub Actions. Cost d'allotjament: zero. Vegeu [DESPLEGAMENT.md](DESPLEGAMENT.md)
per posar-lo en línia.

---

## Què fa i què no fa

**Ho fa.** Recull totes les enquestes publicades, en calcula una mitjana que dona
més pes a les recents i a les de mostra gran, i pinta dos mapes que es poden
comparar amb un interruptor:

| Capa | Què és | Fiabilitat |
| --- | --- | --- |
| **Resultat real** | L'escrutini oficial del Ministeri de l'Interior, municipi a municipi | Dada verificada |
| **Estimació d'avui** | El resultat real de cada territori desplaçat segons el que diuen les enquestes | Model, no mesura |

El mapa mostra **tota la intenció de vot**, no només qui guanya: en passar-hi el
cursor surt el repartiment sencer del territori, i el desplegable de dalt permet
acolorir el mapa pel vot d'un partit concret en comptes de pel guanyador.
Hi ha un **cercador**: escriu el nom d'un municipi i el mapa s'hi acosta i n'obre
la fitxa. Indexa els 8.213 municipis espanyols, els 7.861 comuni italians, les
províncies, les comunitats i els estats.

La pestanya **Escons** dibuixa l'hemicicle de cada cambra. I clicant una
**província espanyola** surten tres coses:

- **quants diputats envia al Congrés** i de quin partit;
- **els escons en joc**: la taula de divisors de la llei d'Hondt, amb l'últim escó
  repartit marcat i, a sota de la ratlla, qui ve al darrere i **quants vots li
  falten**. A Múrcia el desè escó se l'endú el PP amb un quocient de 7,61 i Vox es
  queda a 7,46: **4.525 vots**;
- **els diputats amb nom i cognoms** que va elegir el 2023, i quins entrarien o
  sortirien amb l'estimació d'avui.

**No ho fa.** *No existeixen enquestes municipals.* Ningú no enquesta Cabra de
Mora (Terol, 68 habitants) ni ho farà mai. La capa "Estimació d'avui" **no és una
enquesta d'aquell municipi**: és una projecció. Si el PP puja quatre punts a
Espanya, el model el fa pujar proporcionalment allà on ja era fort. És la tècnica
que fan servir el *Financial Times* o *The Economist*, i és defensable, però
segueix sent un model. El mapa ho diu en cada pantalla, i és important que hi
segueixi sortint.

---

## Posar-lo en marxa

```powershell
.\pb.ps1 init
```

```powershell
.\pb.ps1 geo
```

```powershell
.\pb.ps1 ingest
```

```powershell
.\pb.ps1 build
```

```powershell
.\pb.ps1 site
```

Genera el lloc públic a `dist/`. Per provar-lo abans de publicar:

```powershell
.\pb.ps1 serve
```

que arrenca el mapa a <http://127.0.0.1:8730> amb l'API en viu.

Per actualitzar-ho tot de cop cada dia:

```powershell
.\refresh.ps1
```

---

## D'on surten les dades

| Què | Font | Com |
| --- | --- | --- |
| Enquestes | [Wikipedia](https://en.wikipedia.org/wiki/Opinion_polling_for_the_next_Spanish_general_election), articles *Opinion polling for…* | API de MediaWiki |
| Resultats reals | [Ministeri de l'Interior](https://infoelectoral.interior.gob.es/) | Microdades: vots, escons per circumscripció i els 350 diputats electes |
| Fronteres d'Espanya | Institut Geogràfic Nacional, via [es-atlas](https://www.npmjs.com/package/es-atlas) | 8.213 municipis, 53 províncies, 20 comunitats |

**Per què Wikipedia i no X (Twitter).** Els articles *Opinion polling for…* són
l'agregador més complet i ràpid que existeix, i citen la fitxa tècnica de cada
enquesta. L'API de X costa uns 200 $/mes i les "enquestes" que hi circulen no són
científiques: qui hi vota no és una mostra de res. X serveix per **assabentar-se**
que s'ha publicat una enquesta, no com a font de dades.

**Per què no FiveThirtyEight.** ABC el va tancar el març de 2025 i amb ell la seva
base de dades pública.

---

## Com es calcula la mitjana

El pes d'una enquesta és `recència × mostra`:

- **recència** = `0,5 ^ (dies_enrere / 14)` — una enquesta perd la meitat del pes cada catorze dies
- **mostra** = `√(n / 1000)`, amb un límit perquè una macroenquesta no domini la resta

Es descarten les de fa més de 90 dies i les de menys de 300 entrevistes.
Tots aquests números són a `config/sources.yaml` i es poden canviar.

La banda clara de cada barra al panell és la **dispersió entre cases
enquestadores**, no un interval de confiança estadístic: mesura fins a quin punt
els instituts discrepen entre ells.

### Limitacions conegudes

1. **Sense correcció de biaix per casa.** Cada institut té una tendència
   sistemàtica coneguda. Corregir-la bé demana un model bayesià; fer-ho malament
   és pitjor que no fer-ho.
2. **El swing és proporcional i uniforme.** Assumeix que el moviment nacional es
   reparteix arreu segons la força prèvia. La realitat és més local.
3. **Els partits territorials només existeixen al seu territori.** L'àmbit de
   cadascun surt de `config/parties.yaml → _scope` i està derivat de les dades:
   són les regions que acumulen el 99% dels seus vots reals. Els partits sense
   àmbit declarat es donen per estatals.
4. **No totes les cases pregunten pels partits petits.** El panell marca amb
   «`n enq.`» les xifres que se sostenen en poques enquestes: Aliança.cat surt a
   3 de les 41 recents i Podem a 41. Una mitjana de tres no val el mateix.
5. **Els escons d'Espanya es calculen amb la llei d'Hondt de veritat**, a
   cadascuna de les 52 circumscripcions, amb la seva magnitud real i el llindar
   del 3%. Aplicat als vots reals de 2023, el mateix càlcul reprodueix **348 dels
   350 escons**. Els d'Itàlia són un repartiment proporcional simple i **no**
   modelen la quota uninominal del Rosatellum; el gràfic ho adverteix.
6. **Els noms dels diputats «amb l'estimació d'avui» no són una predicció.**
   Suposen que els partits repetirien exactament les llistes del 2023, i no ho
   faran. Serveixen per veure quants escons canvien i en quin ordre.

---

## Estructura

```
polit bureau/
├── config/
│   ├── sources.yaml      Quines pàgines es llegeixen i com es pondera
│   └── parties.yaml      Partits, colors, àlies i candidats
├── data/
│   ├── politbureau.db    SQLite amb tot
│   ├── geo/              Geometries dels mapes
│   └── raw/              ZIPs del Ministeri, tal com arriben
├── src/politbureau/
│   ├── ingest/           Lectura de Wikipedia i d'infoelectoral
│   ├── model/            Mitjana ponderada, swing, llei d'Hondt
│   ├── build.py          Recalcula mitjanes i projeccions
│   ├── site/             Generador del lloc públic estàtic
│   └── server.py         API i servidor local (per provar)
├── web/                  Plantilles, CSS i JavaScript
└── dist/                 El lloc generat (no es guarda al repositori)
```

## Afegir una elecció nova

Una línia a `config/sources.yaml`. No cal tocar codi:

```yaml
  - id: es-cat-2027
    country: ES
    label: "Catalunya — Parlament"
    scope: region
    page: "Opinion_polling_for_the_next_Catalan_regional_election"
    optional: true
```

Si surten partits nous, `ingest` els llista al final amb un codi provisional
`?XXX` i s'afegeixen a `config/parties.yaml`. Cap dada es perd mentre no ho facis.

---

## Nota tècnica: els certificats de l'Administració

Els servidors `*.gob.es` no envien el certificat intermedi de la FNMT, i per això
Python els rebutja amb `CERTIFICATE_VERIFY_FAILED`. `ingest/gobtls.py` ho resol
**sense desactivar la verificació**: llegeix l'extensió AIA del certificat del
servidor, baixa l'intermedi que falta i construeix un magatzem propi.
Serveix per a qualsevol web de l'Administració espanyola.


---

## Llicència de les dades

Els resultats electorals surten d'Infoelectoral. Les seves condicions generals
diuen literalment que **permeten la reutilització amb finalitats comercials**, amb
dues obligacions: citar la font i no desnaturalitzar la informació. Totes dues es
compleixen a cada pàgina.

La cartografia és de l'Institut Geogràfic Nacional, amb llicència CC BY 4.0
(comercial permès amb atribució). Les dades d'enquestes es recullen de Wikipedia,
CC BY-SA 4.0; les xifres són fets i cada fitxa tècnica se cita.
