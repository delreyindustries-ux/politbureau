# Cens electoral per eleccio

Un CSV per eleccio (`<id de sources.yaml>.csv`), amb una fila per territori:

| columna | que es |
| --- | --- |
| `level` | `national`, `region`, `province` o `municipality` |
| `code` | codi INE del territori (el mateix de la resta del projecte) |
| `cer` | electors residents a Espanya (CER) |
| `cera` | electors residents a l'estranger (CERA), assignats al seu municipi d'inscripcio |
| `total` | cens total de l'eleccio (CER + CERA) |

## es-general.csv — generals del 29/11/2026

- Font: Oficina del Censo Electoral (INE), «Elecciones a Cortes Generales 2026. Censo de consulta»,
  publicat el 09/10/2026:
  - municipis: <https://www.ine.es/oficina_censo/elecgen2026/Elecgral_2026_cc_tab4.xlsx>
  - provincies: <https://www.ine.es/oficina_censo/elecgen2026/Elecgral_2026_cc_tab3.xlsx>
  - comunitats (nomes per comprovar): <https://www.ine.es/oficina_censo/elecgen2026/Elecgral_2026_cc_tab2.xlsx>
- Total: 38.728.356 electors (35.958.711 a Espanya, 2.769.645 a l'estranger).
- Les comunitats son la suma de les seves provincies; quadren amb la taula de l'INE.
- A la taula de municipis, la fila de **48915 Ziortza-Bolibar** no porta el codi de provincia ni el
  total: s'ha completat amb el codi de Bizkaia i CER + CERA (315 + 18 = 333). Amb aquesta fila, la
  suma de municipis quadra amb la de provincies i amb el total estatal.
- Convertit el 17/10/2026.
