# Changelog

## 0.9.20

- Riepilogo per appartamento e stanza con nomi scatole, serie, capienza, moduli occupati, componenti e note.

- Termostati da 2 e 3 moduli nel configuratore e nell’editor planimetria.

- Scatole preimpostate: salva nome, serie, moduli, componenti e note per riutilizzarli in tutti i preventivi e da tutti i dispositivi.
- Inserimento indipendente in cima alla stanza e aggiornamento dei conteggi.
- Eliminazione dei modelli senza alterare le scatole inserite; controllo della serie civile e della capienza.

## 0.9.19

- Duplicazione con numero progressivo al posto di “copia” per appartamenti, scatole, stanze nell’editor e preventivi fotovoltaici.
- Il numero segue il più alto già presente per lo stesso nome; le copie continuano a comparire in cima.

## 0.9.18

- Ronzatore da 1 modulo, campanello da 3 moduli e sensore di presenza da 1 o 2 moduli nelle scatole e nell’editor planimetria.
- Conteggio automatico in Altri punti: ogni dispositivo conta un punto, indipendentemente dai moduli occupati.
- Controllo della capienza anche per i sensori da 2 moduli nell’editor planimetria.

## 0.9.17

- Nuovi appartamenti, parti comuni, stanze e scatole inseriti in cima alla rispettiva lista, incluse le copie.
- Stesso ordine nell’editor planimetria e per i materiali aggiuntivi del fotovoltaico.
- Ordine conservato al salvataggio e alla riapertura; posizione dei frutti nelle scatole invariata.

## 0.9.16

- Salva configurazione disponibile anche in fondo alla pagina; salvataggio delle bozze senza cliente.
- Comando Salva configurazione sempre visibile nella barra dell’editor planimetria.
- I componenti delle scatole aggiornano i totali della stanza e del preventivo anche quando vengono rimossi o duplicati. Una Schuko da due moduli conta come una presa.
- I punti aggiunti manualmente si conservano; i punti luce restano distinti dai comandi. Le nuove stanze partono da zero.
- Impostazioni di salvataggio: cartella dati selezionabile in /share o /media, applicata al riavvio tramite copia verificata, senza eliminare l’originale.
- Destinazioni non vuote non sovrascritte; un archivio esterno non disponibile non viene rimpiazzato da un database vuoto.


## 0.9.15

- Più appartamenti nello stesso preventivo, con stanze e scatole separate.
- Parti comuni gestite come un normale appartamento, con le stesse funzioni.
- Duplicazione indipendente degli appartamenti e note per singola scatola.
- Planimetrie e punti distinti per appartamento nell’editor grafico.
- Subtotali per appartamento e parti comuni nella stampa e nel riepilogo generale.
- Stampa cliente con logo, intestazione e colori Digital Aqua Blue.
- Appartamenti conservati nel salvataggio e nell’import/export JSON dei preventivi; configurazioni esistenti ricondotte ad Appartamento 1.


## 0.9.14

- Planimetrie PDF come sfondo dell’editor, oltre alle immagini già supportate.
- Selezione della pagina per PDF multipagina; PDF originale conservato e scaricabile.
- Prese, luci e altri punti salvati separatamente dallo sfondo e ripristinati alla riapertura del progetto.
- Conversione locale con Poppler, senza inviare il PDF a servizi esterni. File massimo 10 MB e 100 pagine.
- Nuove anteprime con proporzioni della pagina, per mantenere l’allineamento dei punti. Le planimetrie JPG/PNG esistenti conservano il comportamento precedente.

La pagina scelta vale per tutto il progetto. Cambiando pagina o sfondo, i punti restano presenti e la loro posizione va verificata. I DWG non sono supportati in questa versione.

## 0.9.13

- Corretto un errore nello script che impediva l’avvio dell’editor e il salvataggio dei progetti.
- Collegati i pulsanti Nuovo progetto, Stanza, Inserisci punto ed Elimina alle rispettive azioni, indipendentemente dall’ordine nella pagina.
- Salvataggi consentiti anche quando Home Assistant è aperto in HTTP sullo stesso indirizzo; restano bloccati accessi diretti fuori Ingress e richieste di altre origini.
- Errori di salvataggio dei preventivi e delle configurazioni mostrati nella pagina, con protezione dai doppi invii.
- Progetto selezionato correttamente dopo la riapertura; configurazioni civili riconoscibili nel menu senza bloccare l’editor.
- Aggiornare una planimetria conserva il cliente collegato; un progetto inesistente non viene segnalato come salvato.

Verificati otto test automatici, salvataggio/riapertura da browser in HTTP e persistenza dopo riavvio su dati temporanei. Il database operativo resta in `/data`.

## 0.9.12

- Importazione listini CSV e JSON con anteprima e conferma.
- Controllo dei prezzi, dei campi obbligatori e dei codici duplicati.
- Separazione dei codici per fonte e marchio, ricerca per fonte e visualizzazione della provenienza.
- Backup SQLite prima di ogni importazione e registrazione di edizione e impronta del file originale.
- Reimportazione degli stessi dati senza duplicati; prezzi dei preventivi salvati conservati.
- Supporto ai pacchetti normalizzati da EPPAT 2026, Vimar 28.00 e BTicino 2126 RR.

L’accesso resta tramite Home Assistant Ingress, porta interna 8765. Il database esistente in `/data` viene mantenuto. I listini nuovi si caricano dalla sezione Prezzario dopo l’aggiornamento; non vengono importati automaticamente.

Verificati cinque test automatici e il caricamento completo di 48.774 voci su una copia temporanea del database. La prova sull’installazione reale Home Assistant resta da effettuare.
