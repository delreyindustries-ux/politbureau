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

20. **El servidor del Ministeri no respon des dels runners de GitHub.** La
    primera publicació automàtica va fallar amb `TimeoutError` als 30 s en les
    quatre càrregues: `infoelectoral.interior.gob.es` no arriba ni a acceptar la
    connexió TCP des d'un runner, i des d'una connexió espanyola sí. Els ZIP són
    de 2023 i no canviaran mai, així que ara **viuen al repositori**
    (`data/raw/*.zip`, 6,2 MB) i `download()` no toca la xarxa. No els tornis a
    treure del control de versions.
21. **Una càrrega real que falla ha d'aturar el `build`.** El `try/except` de
    `load_real_results` convertia la fallada en una línia de text i el `build`
    acabava amb «Fet.» i codi 0. Amb quatre errors i zero resultats reals hauria
    publicat 16.000 pàgines buides si el generador no hagués petat per una altra
    banda. `run()` ara aixeca `RuntimeError` amb la llista del que ha fallat.

22. **Un partit d'àmbit no té el seu percentatge estatal al seu territori.**
    Aliança Catalana amb el 0,97% estatal té el 6,8% a Catalunya, perquè tots
    aquests vots són a dins i Catalunya és 3,5 de 24,3 milions. Congelar-los al
    resultat anterior (o donar-los la quota estatal tal qual) els deixava amb
    **zero escons mentre totes les cases d'enquestes els en donaven entre 1 i
    5**. Ho resol `build.scope_concentration()`, amb dos comportaments:
    conservar la geografia anterior escalada (`factor`) quan el partit ja hi
    tenia vots, o repartir la quota uniformement (`share`) quan no n'hi tenia o
    quan el factor passa de `MAX_FACTOR`. Aquest segon cas no és opcional:
    Adelante Andalucía només tenia vots a Cadis el 2023 i conservar-li aquella
    geografia li donava el 38% de Cadis, el mateix disbarat d'abans.
23. **La quota d'àmbit s'ha de donar a TOT l'àmbit.** `proportional_swing`
    recorre els partits del `baseline` del territori, així que un partit amb
    quota però sense resultat anterior allà no hi apareixia mai. Adelante
    Andalucía sortia només a Cadis i a les altres set províncies andaluses
    quedava a zero.
24. **Cap formació s'amaga.** `area_rows` retorna totes les candidatures amb
    vots i marca amb `minor` les que no arriben al 0,3%, que van a un bloc
    desplegable. A la província hi ha a més el bloc de les que no van treure cap
    escó, amb els vots i el pes conjunt. Filtrar-les d'entrada era publicar
    mitja graella electoral.

25. **El repartiment d'escons es calcula a dos llocs, i han de coincidir.**
    `web/coalition.js` refà la llei d'Hondt al navegador per al simulador de
    coalicions, amb el mateix desempat que `model/seats.py` (primer el quocient,
    després els vots). Si canvia la regla en un lloc, ha de canviar a l'altre:
    dues implementacions divergents publiquen dues xifres que no quadren.
    Verificat que el JavaScript reprodueix el repartiment **oficial** de
    Barcelona del 2023 (PSOE 13, PP 5, Sumar 5, ERC 4, Junts 3, Vox 2) i que
    coincideix amb Python en les cinc coalicions de prova.
26. **Anar junts no resta escons.** Comprovat sobre les 52 circumscripcions i
    les dues capes, 6.316 parelles: en 437 la coalició en guanya i en cap no en
    perd. És la propietat coneguda del mètode d'Hondt; si algun dia el
    simulador diu el contrari, l'error és al simulador.

27. **El canvas d'identificació del mapa suavitza les vores, i una barreja
    de dos colors descodifica a un tercer territori.** La forma 255 és
    `rgb(0,0,255)` i la 256 és `rgb(0,1,0)`; a mig camí surt `rgb(0,0,127)`, que
    és la forma 127, a l'altra punta d'Espanya. Per això clicar prop d'una
    frontera obria un municipi sense cap relació. Canvas 2D no deixa desactivar
    el suavitzat, així que `at()` **valida** el resultat: l'índex només val si el
    punt cau dins de la capsa d'aquella forma, i si no, es busca el píxel vàlid
    més proper del veïnat prioritzant els opacs. No treguis la validació.
28. **La comunitat i l'Estat no són circumscripcions.** El Congrés s'escull per
    província: per a qualsevol territori més gran cal repartir a cada província i
    després sumar (`constituencies_of()`). Repartir els 350 escons d'un sol cop a
    escala estatal donaria una cambra que no s'assembla a la real.
29. **Un botó que diu «tot» ha de voler dir tot.** El selector de partits
    amagava les formacions per sota del 0,5%, i el bloc «tot a l'esquerra del
    PSOE» en deixava fora Frente Obrero **sense dir-ho**: dos escons de
    diferència en dos dels quatre escenaris. Ara hi són totes les classificades
    (`position < 999`); el filtre del 0,5% només s'aplica a les que encara tenen
    codi provisional `?XXXX`.
30. **Una coalició no és una suma de vots.** El simulador dona quatre escenaris
    (transferència total, +5%, −10%, −20%) i cap no és una predicció. El vot que
    no segueix la llista conjunta va a l'abstenció, no es reparteix entre
    rivals: repartir-lo seria inventar-se un transvasament que cap dada no
    sustenta. Si algú converteix això en una xifra única, el producte torna a
    mentir.

31. **L'eix esquerra-dreta de `_order` és una afirmació política, no un
    detall tècnic.** L'Alfonso el va corregir el 29/08/2026: Frente Obrero **no
    és d'esquerres** i surt del bloc; Nueva Canarias, Geroa Bai i Chunta
    Aragonesista **sí que ho són** i hi entren. Aquest ordre no decideix només
    com s'asseu l'hemicicle: decideix qui entra al botó «tot a l'esquerra del
    PSOE», i per tant quins escons surten al simulador. No el toquis a ull.
    FO s'ha col·locat entre SALF i PACMA; és una ubicació provisional, no una
    afirmació sobre on cau exactament.

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
- [ ] Classificar els set partits que surten com a `?XXXX` al selector estatal
- [ ] `actions/deploy-pages@v4` va amb Node 20, en desús: pujar-ne la versió
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
- [x] Repositori a GitHub: delreyindustries-ux/politbureau, Pages amb workflow i domini politbureau.es
- [x] DNS a Hostinger verificat (4 A, 4 AAAA, CNAME de www)
- [x] **El lloc és en línia a https://politbureau.es** des del 29/08/2026, amb HTTPS
- [ ] Google Search Console: propietat de domini i enviar sitemap.xml (pas 7 de DESPLEGAMENT.md)
- [ ] Alta a AdSense, quan el lloc porti setmanes en linia
- [x] Rutes legals en català (`/ca/avis-legal/`, `/ca/privadesa/`, `/ca/galetes/`)
