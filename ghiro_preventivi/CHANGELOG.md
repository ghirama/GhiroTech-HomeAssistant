# Changelog

## 0.9.42

- Cavi, tubazioni e manodopera per ogni appartamento e per le Parti comuni: quantità, unità, costo unitario, descrizione e totale.
- Salvataggio automatico e duplicazione indipendente delle voci. Trasferimento nel preventivo, nella stampa e nei fogli Excel dell'appartamento; quantità anche nel riepilogo impianto PDF.
- Le quantità a zero sono escluse. I costi manuali restano invariati durante l'aggiornamento del listino; lo sconto materiali non si applica alla manodopera.

## 0.9.41

- Modelli di quadro: salvataggio persistente, rinomina, eliminazione e inserimento indipendente in qualsiasi progetto, conservando dimensioni, componenti, posizioni, codici e note.
- Scelta di contenitori e componenti dal listino Gewiss importato, con ricerca per codice e caratteristiche e prezzi aggiornati al trasferimento nel preventivo.
- Controlli di capienza e sovrapposizione; ingombro letto solo quando indicato nel listino. Gli ingombri frazionari non sono supportati dalla griglia.

## 0.9.40

- Lettore Excel METEL con riconoscimento delle intestazioni abbreviate/estese e delle colonne anche riordinate. Verificato sui listini Vimar e Gewiss forniti.
- Supporto a stato e moltiplicatore espressi come testo; mantenuti codici con zeri iniziali, prezzo al pubblico e conversione del moltiplicatore.
- Aggiunta fonte GEWISS. Controllo del marchio interno: un file GEW non viene importato come BTICINO o VIMAR. La verifica indica la fonte da selezionare.
- BTicino METEL resta da verificare con un file BTicino effettivo; nessuna modifica ad associazioni o prezzi dei preventivi salvati.

## 0.9.39

- Scatole di derivazione spostate nella sezione Quadri elettrici. Scelta della stanza e del tipo/formato prima dell’inserimento.
- Stanza modificabile anche sulle scatole già inserite, mantenendo dimensioni, quantità e note. Nessuna migrazione dei dati: riepilogo e preventivo continuano a usare la stanza assegnata.

## 0.9.38

- Materiali applicabili a tutto l’impianto oppure solo all’appartamento attivo. La scelta generale comprende le parti comuni e viene ereditata dai nuovi appartamenti.
- Impostazione generale salvata nella configurazione; modifiche locali indipendenti, senza cambiare gli altri appartamenti. Riapplicare a tutto l’impianto sostituisce tutte le scelte correnti.

## 0.9.37

- Scelta materiali spostata in Configurazione impianto, per appartamento: marca, serie, colore frutti, placca e posa.
- Le scelte tecniche sono salvate nella configurazione, applicate alle scatole esistenti e alle nuove, comprese quelle inserite da preimpostata. Copie degli appartamenti indipendenti.
- Importazione nel preventivo con codici e prezzi del listino usando le scelte del progetto, senza dover creare associazioni globali. Alternative mancanti o annullate restano segnalate.

## 0.9.36

- Associazioni guidate in blocco per Vimar Plana, Arké e Linea: serie, colore frutti, modello/finitura placca e posa. Codici esatti e prezzi dal listino attivo.
- Distinte scatola + supporto + placca da 3/4/7 moduli, inclusi supporti dedicati Arké Fit e placche Plana Up. Scelte esplicite per alternative tecniche.
- Le associazioni esistenti sono conservate; analisi obsolete vengono rifiutate. Le successive importazioni aggiornano i prezzi degli stessi codici, senza modificare preventivi archiviati.
- Aggiunta suoneria elettronica da 2 moduli; nessuna sostituzione automatica di campanelli da 3 moduli, sensori/termostati con ingombro diverso o scatole da 6 moduli.

## 0.9.35

- Corretto il conflitto `catalog_imports.digest` quando arrivano due importazioni contemporanee dello stesso listino. Il controllo duplicati è ora eseguito anche dentro la transazione di scrittura.
- Pulsanti Verifica/Conferma disabilitati durante la richiesta, con indicazione di avanzamento. Un listino già presente viene segnalato senza errori né modifiche ai preventivi.

## 0.9.34

- Caricamento diretto Excel Vimar METEL e Excel normalizzati, con anteprima, prezzo unitario e articoli annullati esclusi dalle scelte.
- Associazioni persistenti per serie, variante/finitura e componente; distinta scatola, supporto e placca con più codici.
- Scelta finitura nella scatola e valorizzazione automatica della distinta tramite le associazioni salvate.
- Aggiornamento esplicito dei prezzi nel preventivo aperto, senza modificare quelli archiviati; segnalazione delle voci mancanti.
- Importazione completa opzionale per disattivare i codici non più presenti. Backup automatico prima degli aggiornamenti.

## 0.9.33

- Esportazione Excel divisa in Riepilogo generale, un foglio per appartamento e Parti comuni se presenti.
- Mantenute colonne, costi e formule esistenti; Calcolo interno resta collegato ai fogli cliente, senza separazione aggiuntiva materiali/manodopera.
- Logo, intestazione aziendale e stampa A4 su ogni foglio cliente.

## 0.9.32

- Esportazione Excel del preventivo aperto con logo e colori aziendali, dati cliente, subtotali per appartamento, IVA e totale.
- Foglio Calcolo interno con costi, quote materiale, sconto e ricarico modificabili; formule collegate al foglio cliente e stampa A4.

## 0.9.31

- Porta nel preventivo importa la distinta completa di scatole, frutti, derivazioni, quadri e componenti, escludendo i riepiloghi punti.
- I due comandi di importazione usano la stessa distinta senza accodare duplicati. Conferma prima di sostituire voci e prezzi a schermo.

## 0.9.30

- PDF condivisi nel progetto: scelta del documento e assegnazione indipendente della pagina per ogni appartamento, senza ricaricare il file.

- Componenti da posizionare raggruppati per tutte le stanze dell’appartamento selezionato.
- Trascinamento dall’elenco alla planimetria con mouse o puntatore touch; rilascio fuori dal disegno senza modifiche.
- Visualizzazione contemporanea dei simboli di tutte le stanze dell’appartamento.

## 0.9.29

- Importazione dal configuratore civile alla planimetria come progetto separato, con appartamenti, stanze ed elementi da posizionare.
- Colori, simboli e legenda per luci, pulsanti, prese, TV, termostati e altri componenti.

## 0.9.28

- PDF del riepilogo completo con logo, colori aziendali, cliente e intestazione.
- Panoramica e dettagli per appartamento: punti, scatole, posizioni dei frutti, derivazioni, quadri e componenti, caratteristiche e note.

## 0.9.27

- Pulsante Aggiungi stanza spostato dentro Appartamenti del preventivo.

- Salvataggio automatico del configuratore dopo le modifiche, con stato visibile e salvataggio manuale disponibile.
- Salvataggi serializzati, protezione del cambio configurazione e avviso di uscita in caso di modifiche non salvate.

## 0.9.26

- Scatole di derivazione integrate nella sezione Scatole di ogni stanza, con pulsante accanto a quello delle scatole portafrutti. Rimossa la sezione separata.

## 0.9.25

- Quadri elettrici per appartamento e parti comuni, dimensioni in mm e file/moduli configurabili.
- Inserimento componenti nella posizione scelta, controllo ingombri e conteggio moduli liberi.
- Caratteristiche e codici articolo, note, duplicazione, cancellazione, salvataggio e distinta nel preventivo.

## 0.9.24

- Selettore Frutto da inserire dentro ogni stanza, con selezione indipendente.

- Composizione richiudibile al solo titolo per stanza e singola scatola.

- Scatole preimpostate senza serie civile, anche per i modelli esistenti. Serie selezionabile per ogni scatola inserita.
- Sezione Scatole di derivazione per stanza: formati da incasso e parete, misure personalizzate, quantità, note, duplicazione e cancellazione.
- Derivazioni conservate nel progetto e incluse nel riepilogo e nella distinta del preventivo.

## 0.9.23

- Scatole preimpostate: icone Rinomina e Cancella, con conferma per la cancellazione.
- Il nuovo nome viene aggiornato nelle scelte del configuratore; le scatole già inserite rimangono indipendenti.
- Nomi vuoti o già usati non accettati.

## 0.9.22

- Inserimento dei componenti nel quadratino selezionato; spazi vuoti conservati anche dopo rimozione, salvataggio, duplicazione e uso delle scatole preimpostate.
- Componenti da più moduli inseriti solo se lo spazio dal punto scelto è libero e contiguo.
- Griglia a moduli di uguale larghezza e conteggi senza includere gli spazi vuoti.

## 0.9.21

- Elenco configurazioni con nome e descrizione a sinistra e icone Rinomina, Apri e Cancella a destra.
- Descrizione modificabile in cima al configuratore e all’editor planimetria.
- Cancellazione con conferma, senza eliminare i preventivi già creati.
- Apertura diretta delle configurazioni su planimetria nell’editor.

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
