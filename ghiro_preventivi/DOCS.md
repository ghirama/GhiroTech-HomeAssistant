# Ghiro Tech Preventivi 0.9.13

## Aggiornamento da Home Assistant

1. Crea un backup completo dell’add-on da Home Assistant.
2. Nel negozio delle app verifica gli aggiornamenti del repository GhiroTech-HomeAssistant.
3. Aggiorna Ghiro Tech Preventivi alla versione 0.9.13 e riavvia l’add-on.
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
