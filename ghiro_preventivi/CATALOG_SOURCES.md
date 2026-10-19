# Associazioni automatiche Vimar (0.9.37)

## Utilizzo

Caricare il file in Listini prezzi. In Configura impianto civile, scegliere l’appartamento e usare Materiali dell’appartamento:
1. Scegliere marca, serie, colore frutti, modello/finitura placca e posa.
2. Analizza abbinamenti, completare le scelte tecniche richieste.
3. Applica all’appartamento: le scatole esistenti ricevono i materiali scelti, anche le nuove li ereditano. Le impostazioni si salvano con la configurazione.
4. Porta nel preventivo: codici e prezzi vengono risolti dal listino corrente secondo le scelte del progetto.

Ogni appartamento mantiene le proprie impostazioni, comprese le parti comuni. Duplicare crea copie indipendenti. Le scatole preimpostate continuano a salvare solo composizione e note: ereditano i materiali dell’appartamento in cui vengono inserite. Le associazioni manuali precedenti restano compatibili. Un cambio manuale della serie/finitura della singola scatola disattiva il suo profilo automatico. Applica all’appartamento sostituisce queste eccezioni.

Prezzi e codici sono verificati nuovamente all’importazione nel preventivo; scelte non più disponibili vengono segnalate senza sostituzioni. I preventivi archiviati mantengono i prezzi salvati. Le scelte del progetto non modificano le associazioni globali né altri progetti.

## Perimetro e limiti

Impianti tradizionali Plana (bianco/silver), Arké (bianco/grigio/metal), Linea (bianco/canapa/nero). Sono coperti prese, comandi, dati, TV, tapparelle, ronzatori, suonerie elettroniche 2M, presenza 1M, termostati 2M, tappi e distinte scatola/supporto/placca 3/4/7M. Disponibilità effettiva dipendente dal listino attivo: prodotti annullati e combinazioni incomplete sono esclusi.

Nessuna equivalenza inventata fra 6M lineari, 3+3 e 7M. Nessuna sostituzione fra campanello 3M e suoneria 2M, sensori 2M e 1M o termostati 3M e 2M. Esclusi meccanismi incompleti e prodotti bus/KNX/IoT. Alimentazione, categoria dati, attenuazione TV e tipo comando richiedono una scelta esplicita. Non sono dimensionamenti elettrici automatici.

Quadri, protezioni e derivazioni generiche non identificano da soli un articolo: occorre scegliere il codice completo dal listino. BTicino e altri produttori richiedono i relativi listini e dati tecnici; rimangono disponibili le associazioni manuali. Nuove famiglie tecniche non sono dedotte dal solo prezzo o da somiglianze testuali.

## Provenienza delle regole

Consultazione 19 ottobre 2026. Prezzi non incorporati nel codice. Verifica di disponibilità sul listino pubblico Vimar 28 del 01/06/2026 fornito dall'utente; file e prezzi integrali non redistribuiti.

- [Catalogo comandi e regolatori Vimar](https://www.vimar.com/irj/go/km/docs/z_catalogo/DOCUMENT/Apparecchidicomandoeregolatori.53917.pdf): famiglie comandi Arké, 19062, 19181, supporti 19613/19614/19617.
- [Catalogo Linea B.C24013](https://www.vimar.com/en/int/catalog/document/download/code/B.C24013): supporti 30613/30614/30617, placche 30653/30654/30657, scatole V71303/04/06 e V71703/04/06.
- [Plana 14000](https://www.vimar.com/it/it/catalog/product/index/code/14000), [14004](https://www.vimar.com/it/it/catalog/product/index/code/14004): interruttore e deviatore 1M.
- [Plana Up 14653U.01](https://www.vimar.com/it/it/catalog/product/index/code/14653U.01): supporto ordinario 14613.
- [Arké Fit 19953.01](https://www.vimar.com/it/it/catalog/product/index/code/19953.01): supporto dedicato 19913.
- [Arké 19203](https://www.vimar.com/it/it/catalog/product/index/code/19203), [19208](https://www.vimar.com/it/it/catalog/product/index/code/19208): bipasso 1M, Schuko 2M.
- [19300.01](https://www.vimar.com/it/it/catalog/product/index/code/19300.01), [19339.13](https://www.vimar.com/it/it/catalog/product/index/code/19339.13): TV diretta, RJ45 Cat6 UTP.
- [19380](https://www.vimar.com/it/it/catalog/product/index/code/19380): suoneria elettronica 12V SELV 2M, non 3M.
- [19181](https://www.vimar.com/it/it/catalog/product/index/code/19181), [30181.B](https://www.vimar.com/it/it/catalog/product/index/code/30181.B): sensori IR tradizionali 1M.
- [02970](https://www.vimar.com/it/it/catalog/product/index/code/02970), [14440](https://www.vimar.com/it/it/catalog/product/index/code/14440): termostati 2M; 02970 compatibile Arké/Plana.
- [30000.B](https://www.vimar.com/it/it/catalog/product/index/code/30000.B): comando completo, distinto dal solo meccanismo 30000.
- [30370.B](https://www.vimar.com/it/it/catalog/product/index/code/30370.B): ronzatore 12V 1M.

Le famiglie SKU sono vincolate a suffisso colore e presenza nel listino; non basta una corrispondenza approssimata della descrizione. Eventuali cambi di significato dei codici richiedono una revisione delle regole.
