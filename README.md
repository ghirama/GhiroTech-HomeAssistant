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
Carica nella cartella principale un file `GhiroTech_HA_Addon_vX.Y.zip` contenente `ghiro_preventivi/`: GitHub Actions lo estrarrà nella cartella corretta. Una volta importato, il file ZIP può essere eliminato per mantenere pulito il repository.

**Importante:** non pubblicare database operativi, documenti clienti, credenziali o backup. I dati dell'applicazione devono restare nella cartella persistente `/data` di Home Assistant. Gli aggiornamenti di Home Assistant non vengono installati automaticamente soltanto perché è cambiato il repository: serve incrementare la versione dell'add-on e configurare l'aggiornamento in Home Assistant.
