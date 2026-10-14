# Changelog

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
