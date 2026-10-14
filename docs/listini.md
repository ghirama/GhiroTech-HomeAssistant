# Listini: verifica e importazione

La proposta mantiene la versione 0.9.11 e la configurazione Ingress. Non è un aggiornamento già installato su Home Assistant.

## Inventario al 14 ottobre 2026

- Database iniziale: 3.831 voci; il repository le descrive come EPPAT 2026. Non sono presenti file originali o impronte che consentano di verificare completezza ed edizione. Non sovrascrivere questa base senza confronto con l'originale.
- Trentino: fonte ufficiale https://contrattipubblici.provincia.tn.it/Servizi/Elenco-Prezzi-P.A.T/ e portale https://www.elencoprezzi2026.provincia.tn.it/ . Il portale 2026 non ha risposto durante la verifica. Serve l'Excel originale per verificare copertura e prezzi, inclusi lavori compiuti, materiali e impianti.
- Vimar / Elvox: listino 28.00, 1 giugno 2026; Excel e Metel richiedono registrazione. https://www.vimar.com/it/it/listino-e-catalogo-26-00-del-01-06-2025-4100122.html
- BTicino: listino 1 aprile 2026; Excel e Metel da MyBTicino. https://professionisti.bticino.it/novita/listino-prezzi-1-aprile-2026
- Fotovoltaico: mancano listini verificati di moduli, inverter, accumuli, strutture, protezioni e accessori; chiedere marchi, fornitore, data e prezzi netti o pubblici.
- Materiali e domotica: richiedere listini dei grossisti e condizioni commerciali. La presenza di Vimar e BTicino non prova la copertura di ogni famiglia.

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
