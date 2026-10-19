# Ghiro Tech & Light — Home Assistant

Repository ufficiale dell'add-on gestionale Ghiro Tech & Light.

## Struttura
- `repository.yaml`: metadati del repository add-on
- `ghiro_preventivi/`: codice dell'add-on e listino EPPAT iniziale
- `.github/workflows/import-addon.yml`: importazione dei futuri pacchetti ZIP

## Installazione
In Home Assistant apri **Impostazioni → Componenti aggiuntivi → Negozio → ⋮ → Repository** e aggiungi:

`https://github.com/ghirama/GhiroTech-HomeAssistant`

Aggiorna il negozio e verifica la presenza dell'add-on. Prima di sostituire un'installazione locale già in uso, esegui un backup e verifica la migrazione dei dati.

## Nuove versioni
Nel preventivo aperto, **Esporta Excel** scarica le voci correnti (anche non salvate) in un unico file `.xlsx` con logo e colori aziendali. Il file contiene **Riepilogo generale**, un foglio per ogni appartamento e **Parti comuni** se presenti. Le colonne e i calcoli restano quelli del preventivo. Il foglio **Calcolo interno** mantiene quantità, costi, quote materiale, sconto, ricarico e IVA modificabili: le formule aggiornano tutti i fogli cliente e il riepilogo. I fogli cliente sono impostati per stampa A4. Le modifiche in Excel non vengono sincronizzate con il gestionale.

Carica nella cartella principale un file `GhiroTech_HA_Addon_vX.Y.zip` contenente `ghiro_preventivi/`: GitHub Actions lo estrarrà nella cartella corretta. Una volta importato, il file ZIP può essere eliminato per mantenere pulito il repository.

**Importante:** non pubblicare database operativi, documenti clienti, credenziali o backup. I dati dell'applicazione devono restare nella cartella persistente `/data` di Home Assistant. Gli aggiornamenti di Home Assistant non vengono installati automaticamente soltanto perché è cambiato il repository: serve incrementare la versione dell'add-on e configurare l'aggiornamento in Home Assistant.
