# Ghiro Tech & Light — Home Assistant

Repository per gli aggiornamenti dell'add-on.

## Installazione
1. Caricare nella cartella `ghiro_preventivi/` i file dell'add-on (`config.yaml`, `Dockerfile`, `app.py`, `index.html`, `prezzario.sqlite`).
2. In Home Assistant aprire **Impostazioni → Componenti aggiuntivi → Negozio → ⋮ → Repository**.
3. Aggiungere `https://github.com/ghirama/GhiroTech-HomeAssistant`.
4. Installare l'add-on dal negozio.

## Sicurezza
Non pubblicare database in uso, documenti dei clienti, credenziali o backup. Il `prezzario.sqlite` del pacchetto iniziale contiene il listino, non i dati operativi. I dati operativi restano nella cartella persistente `/data` di Home Assistant.

Eseguire un backup prima di ogni aggiornamento. La pubblicazione di una nuova versione su GitHub non la installa automaticamente: Home Assistant deve rilevare e applicare l'aggiornamento.
