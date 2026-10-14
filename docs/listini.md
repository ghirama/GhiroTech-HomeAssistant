# Listini: verifica e importazione

La versione 0.9.12 mantiene la configurazione Ingress. Il rilascio nel repository non aggiorna automaticamente l’installazione Home Assistant.

## Fonti disponibili al 14 ottobre 2026

Sono disponibili gli Excel originali EPPAT 2026, Vimar 28.00 e BTicino 2126 RR forniti dall'utente. L'inventario verificato e i conteggi sono riportati sotto. Le fonti ufficiali sono https://contrattipubblici.provincia.tn.it/Servizi/Elenco-Prezzi-P.A.T. , https://www.vimar.com/it/it/listino-e-catalogo-26-00-del-01-06-2025-4100122.html e https://professionisti.bticino.it/novita/listino-prezzi-1-aprile-2026 . L'Excel BTicino fornito contiene una variazione successiva, documentata nella TESTATA.

Mancano i listini dei fornitori per fotovoltaico, le condizioni di acquisto e gli sconti effettivi. La presenza di prezzi provinciali e di cataloghi produttori non prova la copertura di tutti i componenti installati dall'azienda.

## Procedura verificabile

1. Fare un backup completo dell'add-on da Home Assistant prima di un aggiornamento. Il backup automatico dell'importatore riguarda solo SQLite, non documenti o impostazioni Home Assistant.
2. Conservare l'originale. Per questo primo passo sono supportati CSV UTF-8 e righe JSON normalizzate; Excel va esportato, PDF e Metel non sono interpretati automaticamente. Nessun prezzo viene stimato.
3. Normalizzare le colonne `codice,descrizione,unita,prezzo`; opzionali `dettagli,categoria,manodopera`. Codici come testo, preservando gli zeri. Euro, IVA esclusa. `manodopera` è una percentuale 0–100, non un costo. Prezzo obbligatorio; zero è accettato solo se esplicito nel file.
4. Specificare fonte e edizione/data. Per grossisti diversi usare identificativi diversi, ad esempio FORNITORE_A. Non mescolare prezzi netti di acquisto e listino pubblico nella stessa fonte.
5. Scegliere il separatore effettivo. Prezzi ammessi: `1234.56`, `1234,56`, `1.234,56`. Non usare simboli valuta o separatori ambigui.
6. Verificare anteprima, conteggi e campione confrontandoli con l'originale. Confermare soltanto dopo la verifica. Errori e duplicati bloccano l'intero file.
7. Gli articoli nuovi sono distinti per fonte (`VIMAR:codice`). Le importazioni successive aggiornano soltanto i codici della stessa fonte; articoli assenti dal nuovo file restano disponibili. Nessuna disattivazione automatica degli articoli fuori catalogo.
8. Ogni importazione conserva righe normalizzate, fonte, edizione e SHA-256 in `catalog_imports`. Le righe dei preventivi restano copie indipendenti. Reimportare gli stessi dati della stessa edizione non produce duplicati.
9. Prima delle scritture, SQLite viene copiato con la backup API in `/data/backup_listini`. Importazione articoli e registro sono una transazione unica. Per ripristinare un backup fermare l'add-on e ripristinare il database completo: il ripristino torna indietro anche per eventuali preventivi creati successivamente.

Non è stata verificata l'installazione reale sul Raspberry. Prima del rilascio provare su copia dei dati: apertura tramite Ingress, ricerca, anteprima, importazione, preventivo precedente invariato e riavvio con dati persistenti. Non pubblicare database operativi, originali riservati o backup su GitHub.

## File forniti e verifica completata

Gli originali forniti il 14 ottobre 2026 sono stati letti senza modificarli. Le colonne prezzo contengono valori, non formule con risultati memorizzati.

| Fonte | Righe con prezzo / articoli | Importabili | Separate per verifica |
| --- | ---: | ---: | ---: |
| EPPAT Excel 2026 | 17.087, inclusi 120 duplicati identici | 16.581 | 386 |
| Vimar 28.00, 01/06/2026 | 8.033 | 7.751 | 282 prodotti annullati |
| BTicino 2126 RR, variazione 01/07/2026 | 24.676 | 24.442 | 234 prodotti annullati |

BTicino ha decorrenza 01/04/2026 e ultima variazione 01/07/2026 nella TESTATA. Sono presenti sigle BTI, LEG, IMS, ZUC, CAB e NTM. La chiave conserva il marchio: `BTICINO_BTI:010`, ad esempio. Nessun prezzo netto negoziato è stato dedotto: nelle righe fornite i prezzi al pubblico e al rivenditore coincidono.

Il prezzo unitario METEL è prezzo esposto diviso moltiplicatore, indipendentemente dalla confezione. Fonte tecnica: manuale METEL 020/021 rev.20, sezioni 4.3.12, 4.3.14 e 4.3.16, https://www.metel.it/assets/fbd46ec847d0420b8a5dfec26dd5078d.pdf . La precisione dei prezzi unitari è conservata (es. CAB 000011: 1643,72 / 100 = 16,4372 €/m). Gli stati 2 e 7 restano visibili come in esaurimento; lo stato 6 è su commessa, non annullato. Lo stato 9 è separato dai pacchetti importabili.

EPPAT: 367 prezzi zero richiedono analisi/verifica, 19 altre righe hanno dati essenziali mancanti. I duplicati identici vengono unificati, i duplicati discordanti bloccano la preparazione. 701 descrizioni sono ricavate dai titoli presenti nella gerarchia originale quando la variante non ha una propria descrizione. I dettagli includono contesto, righe originali e incidenze; nessun prezzo o unità mancante è stato inventato. Nessuna riga separata interessa i capitoli B.62, B.64, A.01.15 o S.50.

Tutti i 3.831 codici e prezzi del database iniziale coincidono con l'Excel originale, e appartengono ai capitoli B.62 e B.64. Il nuovo pacchetto EPPAT include anche gli altri capitoli utilizzabili; la ricerca permette di filtrare per fonte. Le voci iniziali restano nel database, ma i duplicati EPPAT sono nascosti nella ricerca combinata quando è presente la versione con fonte esplicita.

### Preparazione e caricamento

`tools/prepare_catalogs.py` legge EPPAT e i due formati Excel METEL osservati. Richiede `tools/requirements.txt` sul computer di preparazione, non nell'add-on. Esempio:

```
python tools/prepare_catalogs.py originale.xlsx --source VIMAR --edition "28.00 — 01/06/2026" --output cartella-pacchetti
```

Produce JSON caricabili dall'interfaccia, CSV alternativi e riepiloghi con SHA-256 degli originali. I file sono divisi in parti inferiori ai limiti di caricamento, per un totale di 26 pacchetti. Caricare i JSON con `voci`, non i file `riepilogo` o `da_verificare`; i metadati fonte/edizione vengono compilati dal pacchetto. Gli originali, gli archivi generati e i dati non vanno pubblicati nel repository.

La prova completa su database temporaneo ha importato 48.774 voci, verificato reimportazione senza duplicati, conservazione delle righe di un preventivo esistente e delle 3.831 voci iniziali, integrità SQLite, ricerca per fonte e blocco HTTP 403 fuori Ingress. Il test non sostituisce la verifica sul Raspberry.

Restano da fornire listini di acquisto e sconti effettivi dei grossisti, e i marchi/listini FV di moduli, inverter, accumuli e strutture specificamente utilizzati. Non sono stati associati automaticamente articoli a punti dell'impianto: la compatibilità di serie, supporti e placche richiede una distinta verificata.
