# Posar politbureau.es en línia

Vuit passos. El domini ja el tens; `config/site.yaml` ja apunta a
`https://politbureau.es`, o sigui que aquesta part no s'ha de tocar.

Els passos 1 a 6 es fan en una tarda, tret de l'espera del DNS. El 7 i el 8
depenen de Google i triguen setmanes.

---

## 1. El teu nom i un correu — ~~fet~~

`config/site.yaml` ja porta **Alfonso del Rey Vega** i
**delreyindustries@gmail.com** com a titular i contacte, i surten a l'avís legal
en tots dos idiomes, tal com exigeix l'article 10 de la Llei 34/2002.

> Aquestes dues dades seran **visibles a internet** i els robots de correu brossa
> les recolliran. És inevitable: la llei obliga a publicar-les. Si més endavant
> vols un correu específic per a això (`contacto@politbureau.es`, que Hostinger
> et deixa crear amb el domini), canvia'l al mateix fitxer i republica.

## 2. Crear el repositori a GitHub

Si encara no hi tens compte, fes-te'l a [github.com](https://github.com).
Després crea un repositori **buit** (sense README, sense .gitignore) que es digui
`politbureau`. Pot ser públic o privat: GitHub Pages funciona amb tots dos si el
compte és gratuït i el repositori és públic; amb repositori privat calen Pages
de pagament. **Fes-lo públic.**

Que sigui públic vol dir que qualsevol pot veure el codi. Les dades no hi són
(`data/` i `dist/` estan al `.gitignore`), i no hi ha cap contrasenya enlloc.

## 3. Pujar el projecte

Des de la carpeta del projecte:

```bash
git add -A && git commit -m "Polit Bureau"
```

```bash
git branch -M main && git remote add origin https://github.com/EL-TEU-USUARI/politbureau.git && git push -u origin main
```

Canvia `EL-TEU-USUARI` pel teu nom d'usuari de GitHub.

## 4. Activar GitHub Pages

Al repositori: **Settings → Pages → Build and deployment → Source**, tria
**GitHub Actions**.

Ves a la pestanya **Actions** i comprova que el workflow «Actualitza i publica»
s'executa. La primera vegada triga uns 10-15 minuts, perquè baixa els ZIP del
Ministeri. Quan acabi, el lloc ja serà a `EL-TEU-USUARI.github.io/politbureau`.

**Comprova que funciona abans de tocar el DNS.** Si el workflow falla, el
problema és al codi i el DNS no hi té res a veure.

## 5. Dir a GitHub quin és el domini

**Settings → Pages → Custom domain**: escriu `politbureau.es` i desa.

> No cal cap fitxer `CNAME` al repositori. Amb un workflow propi de GitHub
> Actions, GitHub **ignora** qualsevol fitxer `CNAME`; el domini només val si
> està posat aquí.

## 6. El DNS a Hostinger

A l'hPanel: **Dominis → politbureau.es → DNS / Nameservers → Gestionar registres DNS**.

Primer **esborra els registres A i CNAME que Hostinger hi hagi posat per defecte**
apuntant a la seva pàgina d'aparcament. Si els deixes, competiran amb els nous.

Després afegeix aquests **quatre registres A**, tots amb el nom `@`:

| Tipus | Nom | Apunta a | TTL |
| --- | --- | --- | --- |
| A | @ | `185.199.108.153` | 3600 |
| A | @ | `185.199.109.153` | 3600 |
| A | @ | `185.199.110.153` | 3600 |
| A | @ | `185.199.111.153` | 3600 |

I aquests **quatre AAAA** (IPv6), també amb nom `@`:

| Tipus | Nom | Apunta a |
| --- | --- | --- |
| AAAA | @ | `2606:50c0:8000::153` |
| AAAA | @ | `2606:50c0:8001::153` |
| AAAA | @ | `2606:50c0:8002::153` |
| AAAA | @ | `2606:50c0:8003::153` |

I un **CNAME** perquè `www` també funcioni:

| Tipus | Nom | Apunta a |
| --- | --- | --- |
| CNAME | www | `EL-TEU-USUARI.github.io` |

El punt final de `github.io.` el posa Hostinger sol; si el panell te'l demana,
posa-l'hi.

**Espera.** El DNS triga d'una hora a 24. Mentrestant, a Settings → Pages de
GitHub veuràs un avís de verificació pendent: és normal.

Quan GitHub digui que el domini està verificat, marca la casella
**Enforce HTTPS**. El certificat el genera GitHub gratis i triga uns minuts més.

## 7. Google Search Console

Aquest pas és el que decideix si el lloc rep visites o no.

1. Entra a [search.google.com/search-console](https://search.google.com/search-console).
2. Afegeix una propietat de tipus **Domini** amb `politbureau.es`.
3. Et demanarà verificar-ho amb un registre **TXT** al DNS: torna a Hostinger i
   afegeix-lo igual que els anteriors.
4. Un cop verificat, ves a **Sitemaps** i envia: `sitemap.xml`

A partir d'aquí Google comença a rastrejar. **Indexar 16.400 pàgines pot trigar
mesos**, i no les indexarà totes. És normal i no es pot accelerar pagant.

## 8. AdSense

Només quan els passos anteriors funcionin i el lloc porti unes setmanes en línia.

1. Demana el compte a [adsense.google.com](https://adsense.google.com).
2. Google revisa el lloc **a mà**. Triga de dies a setmanes.
3. Quan t'aprovin, crea tres blocs d'anunci i posa'ls a `config/site.yaml`:

```yaml
publicidad:
  adsense_client: "ca-pub-XXXXXXXXXXXXXXXX"
  slots:
    territory_top: "1234567890"
    territory_bottom: "0987654321"
    map_side: "1122334455"
```

4. Torna a fer `git commit` i `git push`. El workflow republica sol.

Fins que aquests camps estiguin buits **no es carrega cap script de Google i el
banner de galetes ni surt**. És a posta: demanar permís per a res és enganyar
l'usuari, i carregar rastrejadors abans del consentiment és il·legal a la UE.

---

## Què esperar, sense endolcir-ho

- **Google pot rebutjar el lloc.** La seva política de *scaled content abuse*
  apunta a llocs amb milers de pàgines generades. Aquí cada pàgina té dades
  reals i diferents i un text propi, que és el que ho separa del contingut buit,
  però la decisió és seva.
- **Els primers mesos no guanyaràs pràcticament res.** AdSense paga a Espanya
  entre 1 i 5 € per cada 1.000 pàgines vistes. Sense trànsit no hi ha ingressos,
  i el trànsit de cerca triga.
- **El pic serà en campanya electoral.** Aquest tipus de web multiplica les
  visites els dies previs i el dia d'unes eleccions. Val la pena tenir-ho
  indexat molt abans que arribin.

## Manteniment

Cap, si tot va bé: el workflow s'executa cada dia a les 8:15.

L'únic que has de mirar de tant en tant és la sortida d'`ingest` a la pestanya
Actions: al final llista els partits que no ha sabut classificar. Quan n'aparegui
un de nou, afegeix-lo a `config/parties.yaml`; si no, surt al mapa com a `?XXXX`.

## Provar-ho a casa abans de pujar res

```bash
python -m politbureau site
```

```bash
python -m politbureau check
```

`check` revisa les 16.417 pàgines: que els 604.000 enllaços interns apuntin a un
fitxer que existeix, que cap títol ni cap descripció es repeteixi, que cada
pàgina tingui un sol `h1` i que el sitemap no llisti adreces mortes. **El
desplegament automàtic també l'executa i no publica si troba res.**

Per veure-ho al navegador:

```bash
cd dist && python -m http.server 8000
```

I obrir <http://localhost:8000>. Atura el servidor abans de tornar a generar: si
té la carpeta oberta, l'esborrat falla i el generador s'atura amb un avís.
