# Ghiro Tech Preventivi 0.9.16

## Aggiornamento da Home Assistant

1. Crea un backup completo dell’add-on da Home Assistant.
2. Nel negozio delle app verifica gli aggiornamenti del repository GhiroTech-HomeAssistant.
3. Aggiorna Ghiro Tech Preventivi alla versione 0.9.16 e riavvia l’add-on.
4. Aprilo dalla barra laterale di Home Assistant e controlla un preventivo già salvato.

Il database persistente e i documenti restano in `/data`. Non disinstallare l’add-on per aggiornarlo. Non sostituire manualmente il database operativo con quello incluso nel pacchetto.

## Caricamento listini

Nella sezione Prezzario seleziona un JSON normalizzato, premi Verifica anteprima, controlla i prezzi e conferma l’importazione. Fonte ed edizione vengono lette dal pacchetto. Ripeti per le altre parti elencate nel manifest del pacchetto listini.

Sono supportati anche CSV UTF-8 con codice,descrizione,unita,prezzo e le colonne facoltative dettagli,categoria,manodopera. Seleziona il separatore effettivo. Manodopera è una percentuale, non un importo.

Gli articoli sono distinti per fonte e marchio. Ogni importazione crea un backup SQLite nella cartella `backup_listini`; questo backup non sostituisce il backup completo Home Assistant. I prezzi dei preventivi già salvati non vengono aggiornati dall’importazione dei listini.

I listini Excel originali devono essere prima normalizzati: non caricarli direttamente in questa versione. Nel pacchetto listini sono separati gli articoli annullati e le righe prive di dati essenziali. Non caricare manifest, riepiloghi o file da_verificare come listini.

I prezzi dei produttori non comprendono automaticamente gli sconti dei tuoi fornitori. Verifica prezzi di acquisto, disponibilità e compatibilità degli articoli prima di associare la distinta al preventivo.

## Verifica del salvataggio dopo l’aggiornamento

Crea un progetto di prova nell’editor, aggiungi una stanza e un punto, premi Salva e verifica il messaggio Progetto salvato. Ricarica la pagina e scegli la stanza: il titolo, le stanze e i punti devono essere presenti. Le configurazioni civili senza planimetria si aprono dal configuratore impianto civile.

Crea un preventivo di prova selezionando un cliente e una voce, premi Salva preventivo, ricarica e aprilo da Preventivi archiviati. Verifica cliente, quantità e prezzo. Un errore viene mostrato nella pagina; se il salvataggio riesce ma l’elenco non si aggiorna, il messaggio distingue i due casi.

## PDF come sfondo della planimetria

Nell’editor scegli un PDF da Planimetria JPG/PNG o PDF e attendi l’anteprima. Il file può avere fino a 100 pagine e pesare al massimo 10 MB. Se contiene più pagine, seleziona quella desiderata e premi Usa pagina scelta. La pagina scelta è lo sfondo dell’appartamento selezionato; gli altri appartamenti conservano la propria planimetria.

Aggiungi prese, punti luce e altri simboli come sulle immagini, quindi premi Salva. Dopo aver ricaricato la pagina, il progetto mantiene il PDF, la pagina scelta e i punti. Il PDF originale resta disponibile tramite Scarica PDF originale.

Il PDF viene conservato nella cartella persistente `/data/planimetrie`; le anteprime vengono generate localmente con Poppler. Nessun documento viene inviato a servizi esterni. Per conservare anche gli originali PDF usa il backup completo Home Assistant: il solo backup SQLite non contiene questi file.

Cambiare pagina o sfondo conserva i punti già inseriti; verifica che corrispondano alla nuova planimetria. Il gestionale non modifica il PDF originale e non esegue un riconoscimento automatico delle stanze o degli impianti.

PDF danneggiati o protetti da password mostrano un errore senza sostituire lo sfondo precedente. Esporta una copia leggibile dal programma che ha generato il documento. Il formato DWG è escluso da questa versione.

## Appartamenti e parti comuni nello stesso preventivo

Nel configuratore usa `+ Appartamento` e assegna un nome a ciascuna unità. `+ Parti comuni` crea un’altra unità identica, chiamata Parti comuni. Seleziona l’unità prima di aggiungere stanze e scatole. `Duplica appartamento` crea una copia indipendente, comprese le note delle scatole. Le configurazioni precedenti si aprono come Appartamento 1.

Il trasferimento al preventivo comprende tutte le unità. Ogni voce conserva l’appartamento; i subtotali sono riepilogati separatamente e confluiscono nel totale generale. Le note delle scatole restano nella configurazione e non vengono stampate automaticamente sul preventivo cliente.

Anche l’editor planimetria gestisce più unità, ciascuna con il proprio sfondo e i propri punti. La stampa cliente usa l’intestazione Ghiro Tech and Light e i colori ispirati al Digital Aqua Blue.

## Salvataggio e conteggi delle scatole

Usa Salva configurazione in alto o nella barra in fondo al configuratore. Puoi salvare una bozza senza cliente; per salvare il preventivo economico il cliente rimane necessario. Nell’editor planimetria la barra superiore con Salva configurazione rimane visibile durante lo scorrimento.

Le nuove stanze partono da zero. Inserimento, rimozione e duplicazione di frutti o scatole aggiornano i conteggi della stanza. La Schuko occupa due moduli ma conta come un solo punto presa. Puoi aumentare i totali manualmente per includere punti non composti nelle scatole; non puoi scendere sotto i componenti effettivamente inseriti. I punti luce si impostano separatamente: il numero di pulsanti, deviatori e interruttori non determina il numero delle lampade. Alla prima apertura delle configurazioni precedenti, i totali già presenti sono conservati se almeno pari ai componenti; non si sommano due volte i frutti già conteggiati.

## Scelta della cartella dati

Apri Impostazioni → Salvataggio dati. La cartella attuale predefinita è `/data`. Per cambiare, scegli una nuova sottocartella vuota in `/share` o `/media`, per esempio `/share/ghiro-tech`, e premi Verifica e salva percorso. Il percorso riguarda il server Home Assistant, non il PC o iPad. Un archivio di rete deve essere già montato e disponibile a Home Assistant.

Fino al riavvio tutti i salvataggi continuano nella cartella attuale. Riavviando l’add-on vengono copiati il database aggiornato, i documenti, le planimetrie e i backup dei listini. La cartella originale viene conservata. Il database contiene anche clienti, preventivi, configurazioni, lavori e pratiche. I PDF creati dalla stampa del browser continuano a usare la destinazione scelta nella finestra di stampa.

La destinazione deve essere vuota e scrivibile: i dati esistenti non vengono sovrascritti. Se il trasferimento fallisce, il gestionale continua a utilizzare l’originale e mostra il problema nelle impostazioni. Puoi annullare il cambio in attesa. Se un archivio esterno già attivo diventa indisponibile, il gestionale interrompe l’avvio senza crearne uno vuoto: ripristina il montaggio della cartella.

Includi `/share` o `/media` nel backup di Home Assistant quando vi sposti l’archivio: il solo backup dell’add-on non include queste cartelle. Non eliminare la copia originale prima di aver verificato l’archivio nuovo e un backup completo.


### Scatole e derivazioni (0.9.24)
Le preimpostazioni conservano componenti, posizioni e note senza serie civile. La serie predefinita della stanza vale per le nuove scatole; ogni scatola può avere una serie diversa. Cliccare il titolo per richiudere una scatola o la composizione della stanza.

Derivazioni: 28 formati iniziali da catalogo (11 GEWISS da incasso, 9 BTicino da incasso, 8 GEWISS da parete), più dimensioni personalizzate. Le dimensioni sono L × H × P in mm: esterne per GEWISS incasso, interne per GEWISS parete, dimensioni dichiarate dal catalogo per BTicino. Non sono misure universali intercambiabili. Quantità e note sono incluse nella distinta; i prezzi restano da associare.

Fonti dei formati, consultate il 15 ottobre 2026:
- https://www.gewiss.com/it/it/series/serie.1000000.1000057.48-range-flush-mounting-junction-and-modular-boxes-range
- https://www.gewiss.com/it/it/prodotti/product.1000000.1000057.GW48011
- https://www.gewiss.com/it/it/prodotti/product.1000002.1000088.GW44008
- https://www.bticino.com/products/switches-sockets-and-wiring-devices/installation-boxes-and-protected-enclosures/junction-boxes-and-accessories
- https://catalogo.bticino.it/prodotto/soluzioni-per-edifici-residenziali-e-nel-terziario/scatole-idrobox-e-multibox/scatole-di-derivazione-multibox-ed-accessori/BTI-16204-IT
- https://catalogo.bticino.it/prodotto/soluzioni-per-edifici-residenziali-e-nel-terziario/scatole-idrobox-e-multibox/scatole-di-derivazione-multibox-ed-accessori/BTI-16205-IT
- https://catalogo.bticino.it/prodotto/soluzioni-per-edifici-residenziali-e-nel-terziario/scatole-idrobox-e-multibox/scatole-di-derivazione-multibox-ed-accessori/BTI-16206-IT
- https://catalogo.bticino.it/prodotto/soluzioni-per-edifici-residenziali-e-nel-terziario/scatole-idrobox-e-multibox/scatole-di-derivazione-multibox-ed-accessori/BTI-16207-IT


### Quadri elettrici
Nella configurazione civile, ogni appartamento e le parti comuni possono contenere più quadri. Impostare le dimensioni L × H × P in mm, numero di file e moduli per fila. Scegliere il componente e il suo ingombro, poi cliccare sullo spazio di partenza: il componente deve entrare interamente nella fila senza sovrapposizioni. Le caratteristiche e il codice articolo sono compilabili per ciascun componente. La riduzione della capienza non può tagliare componenti presenti.
I quadri si possono richiudere, duplicare ed eliminare. Salva configurazione conserva tutto il progetto. Il riepilogo e i pulsanti di trasferimento al preventivo includono contenitori e componenti, con prezzi da compilare. Dimensioni e ingombri vanno inseriti secondo il prodotto scelto; non vengono calcolate automaticamente le protezioni.
