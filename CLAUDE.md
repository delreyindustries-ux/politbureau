# CLAUDE.md — Polit Bureau

Instruccions per a Claude Code quan treballa en aquesta carpeta.

## Què és això

Una **web pública** de resultats electorals i estimació de vot per als 8.131
municipis d'Espanya, que es finança amb publicitat. Es genera com a lloc estàtic
i es publica amb GitHub Actions.

Només Espanya: Itàlia, França i els Estats Units es van eliminar el 23/08/2026 a
petició de l'Alfonso, en convertir el projecte en web pública.

Llegeix [DESPLEGAMENT.md](DESPLEGAMENT.md) abans de tocar res que afecti la
publicació.

Llegeix el `README.md` abans de tocar res: hi ha les fonts, el mètode de càlcul i
les limitacions conegudes.

## Idioma

- **Conversa i documentació:** català.
- **Codi i comentaris:** català sense accents (els fitxers `.py` i `.js` viuen
  millor en ASCII i evita problemes de codificació a la consola de Windows).
- **Interfície del mapa:** català.

## La regla que no es pot trencar

**Cap número sense font, i cap estimació disfressada de dada.**

El projecte barreja dues coses molt diferents:

| | Què és | Com s'ha d'etiquetar |
| --- | --- | --- |
| `election_result` | Escrutini oficial | «Resultat real», amb el procés i l'organisme |
| `projection` | Model de swing | «Estimació», dient sempre que **ningú no ha enquestat aquell municipi** |

Si algun canvi fa que aquesta distinció s'esborri de la interfície, el canvi està
malament. El cartell del mapa (`#mapnote`) i el peu de la fitxa de territori no
són decoració: són la part honesta del producte.

Quan es publiqui un número nou (una mitjana, una projecció, un escó), ha de
poder-se resseguir fins a la font. La pestanya «Enquestes» existeix per això.

## Ordres

```powershell
.\pb.ps1 ingest    # baixa enquestes noves (idempotent)
.\pb.ps1 build     # recalcula mitjanes i projeccions
.\pb.ps1 serve     # mapa a http://127.0.0.1:8730
.\pb.ps1 status    # què hi ha a la base de dades
.\refresh.ps1      # ingest + build, per a la tasca programada
```

Python és a `%LOCALAPPDATA%\Programs\Python\Python312\python.exe` i **no és al
PATH**: cal invocar-lo per ruta completa o fer servir `pb.ps1`.

## Coses que ja s'han après i no cal tornar a descobrir

1. **Wikipedia posa els partits com a logotips.** El text de la cel·la de
   capçalera és buit; el nom viu a `a[title]` o `img[alt]`. `pandas.read_html`
   els perd tots. Per això el parser va amb BeautifulSoup.
2. **Cal expandir `rowspan`/`colspan` a una graella.** El CIS agrupa quatre files
   sota una sola cel·la de data; sense `grid()` els índexs de columna es desplacen.
3. **Els fitxers 05 i 06 d'infoelectoral tenen estructures diferents**: el 05
   porta el codi de comunitat davant del de província i el 06 no. Es va validar
   comprovant que els codis donen 8.131 municipis coincidents al 100% amb l'INE.
4. **El `FICHEROS.rtf` del Ministeri és un `.doc` binari** amb l'extensió
   canviada. No es pot llegir com a text; les posicions s'han deduït i validat.
5. **Els servidors `.gob.es` no envien el certificat intermedi.** `ingest/gobtls.py`
   el baixa via AIA. **Mai** posar `verify=False`.
6. **Wikipedia talla amb 429** si es demanen 35 pàgines seguides. Hi ha un
   limitador a `wikipedia._throttled_get`; no el treguis.
7. **Les seccions «Hypothetical scenarios», «Voting preferences» i
   «aggregations» estan excloses a posta.** Mesuren coses diferents o són
   mitjanes d'altri: incloure-les falsejaria el càlcul.
8. **El codi de comunitat autònoma del Ministeri NO és el de l'INE.** El
   Ministeri intercanvia les dues Castelles i canvia Valencia de lloc. Donar-los
   per equivalents fa que Navarra es dibuixi damunt de Múrcia. La pertinença es
   dedueix de la geometria de l'IGN a `geo/regions.py`; no la substitueixis per
   cap taula copiada a mà. Els codis de **província** sí que són INE i són fiables.
9. **Esborrar abans d'inserir, mai `INSERT OR REPLACE`** a `projection`,
   `election_result`, `constituency*` i `seat_projection`. La clau primària inclou
   el partit, així que un partit que deixa de sortir en un territori no
   l'sobreescriu ningú i sobreviu al recàlcul contaminant el mapa.
10. **`HAVING SUM(x)`, mai `HAVING x`** quan l'àlies té el mateix nom que una
    columna: SQLite dona prioritat a la columna i el filtre s'aplica a una fila
    arbitrària del grup. Això feia desaparèixer Vox i Sumar de l'hemicicle.
11. **El swing divideix, i dividir per números petits explota.** Adelante
    Andalucía tenia el 0,037% estatal el 2023: el factor sortia 26,8 i el model
    li donava Cadis. Hi ha dos guardians a `model/seats.py` (`MIN_BASE` i el
    límit del factor) i `build` avisa per pantalla de quins partits ha frenat.
13. **El numerador i el denominador han de cobrir el mateix territori.** A França
    l'ultramar té resultats però no polígon: sumar-lo al total nacional i no als
    partits feia que tots els candidats sortissin un punt per sota. Ara el total
    nacional es calcula sobre TOT i només els nivells territorials descarten el
    que no es pot dibuixar.
14. **Els codis del ministeri italià no són els de l'ISTAT** (una altra vegada).
    El creuament amb el mapa va pel `minint_elettorale` de la geometria
    d'openpolis: els seus set últims dígits són província + comune.
15. **Quantitzar, no simplificar.** Si cada polígon s'aprimés pel seu compte,
    els veïns deixarien de compartir la frontera i sortirien escletxes.
    Encaixar-los tots a la mateixa graella manté les fronteres tancades.
12. **Els escons surten del fitxer 08 d'infoelectoral**, que porta les mateixes
    dades a tres nivells barrejats; els agregats es marquen amb `99`. Sense
    filtrar-los la suma dona 1.050 en comptes de 350.
16. **El canvas d'identificació no es pinta mentre s'arrossega** el mapa. Sense
    això, 35.000 polígons van a 813 ms per fotograma; amb això, a 119.
17. **Els 350 diputats surten del fitxer 04**, posició 119 (`S`/`N`). Validat:
    n'hi ha exactament 350 i cada província en té tants com escons reparteix.
19. **Un partit nou sense base estatal no es presenta a tot arreu.** Quan un
    partit surt a les enquestes però no va concórrer el 2023, el model li donava
    la seva quota nacional a TOTS els territoris, i Aliança Catalana acabava
    sortint a Ceuta i Melilla. Els partits territorials tenen l'àmbit declarat a
    `config/parties.yaml → _scope`, **derivat de les dades**: són les regions que
    acumulen el 99% dels seus vots reals. Si n'afegeixes un, deriva'l igual; el
    filtre només esborra, i un àmbit mal posat faria desaparèixer dades bones.
18. **Arribar al llindar del 3% no dona cap escó.** Per a un partit que hi és per
    sota, el que li falta és el MÀXIM entre el llindar i el quocient de l'últim
    escó. Comptar només el llindar posava un partit del 0,9% per davant de
    Soria ¡Ya!, que hi va pel 18,8%.

## Quan surtin partits nous

`ingest` acaba llistant les etiquetes que no ha sabut classificar. Es guarden amb
un codi provisional `?XXX` — la dada no es perd. Afegir-les a
`config/parties.yaml` i tornar a fer `build`.

## Regles de la web pública

1. **Res de rastrejadors sense consentiment.** Els scripts de Google només es
   carreguen des de `loadThirdParty()` a `web/site.js`, i només després que
   l'usuari accepti. Si `adsense_client` és buit no es carrega res i el banner
   ni tan sols surt. **No moguis això**: carregar-los abans del consentiment és
   il·legal a la UE, no una qüestió d'estil.
2. **Cada pàgina ha de dir alguna cosa verdadera i diferent.** El text d'entrada
   es construeix amb els números reals d'aquell territori (`lede_for`). Si això
   es converteix en una plantilla igual per a tothom, són 16.000 pàgines de
   contingut buit i Google les penalitza.
3. **El guanyador real no és la primera fila de la taula.** Les files van
   ordenades per l'estimació d'avui. Confondre-ho feia dir que va guanyar el PP
   a llocs on va guanyar el PSOE.
4. **Coma decimal**, no punt: `pct()` a `site/build.py` i el filtre `pct` a les
   plantilles.
5. **Les adreces del lloc són relatives** (`root`), perquè GitHub Pages pot
   servir des d'un subdirectori. Cap enllaç intern ha de començar amb barra.
6. **`politbureau check` abans de donar res per bo.** Revisa enllaços, títols
   duplicats, `h1`, JSON-LD i sitemap sobre les 16.417 pàgines. Va trobar que el
   text deia que havia guanyat un partit que havia quedat segon, que 120 títols
   es repetien i que el sitemap llistava 168 adreces inexistents. El workflow
   l'executa i **no publica si falla**.
7. **Només s'enllaça el que s'ha escrit.** `territory_pages()` retorna el conjunt
   de territoris amb pàgina i `run()` filtra `urls` amb ell. es-atlas inclou
   Gibraltar i codis amb prefix 53/54 que no tenen resultats: sense el filtre,
   el sitemap i la portada els enllacen.
8. **Aturar el servidor abans de regenerar.** Si té `dist/` oberta, l'esborrat
   falla a mitges; el generador ho detecta i s'atura amb un avís.

## Estat pendent

- [ ] Correcció de biaix per casa enquestadora (cal model bayesià)
- [x] Llei d'Hondt pròpia amb les magnituds reals (backtest: 348/350 escons de 2023)
- [x] Mapes d'Itàlia (regions i comuni) i França (régions i comunes)
- [x] Escons per circumscripció i marge de vots per canviar el repartiment
- [x] Cercador de territoris (16.223 indexats)
- [x] Escons en joc: taula de divisors amb els vots que falten
- [x] Diputats electes per província, amb nom
- [ ] Autonòmiques per comunitat (les pàgines existeixen però no estan a `sources.yaml`)
- [ ] Itàlia: la Camera es reparteix amb el Rosatellum, no proporcionalment
- [ ] Europees: verificar que la pàgina de Wikipedia existeix
- [x] Lloc públic estàtic bilingüe amb 16.455 pàgines
- [x] Titular i contacte a `config/site.yaml` (Alfonso del Rey Vega)
- [x] Domini comprat: politbureau.es (Hostinger)
- [ ] Repositori a GitHub, DNS i Search Console (vegeu DESPLEGAMENT.md)
- [ ] Alta a AdSense, quan el lloc porti setmanes en linia
- [x] Rutes legals en català (`/ca/avis-legal/`, `/ca/privadesa/`, `/ca/galetes/`)
