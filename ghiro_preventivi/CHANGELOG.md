# Changelog

## 0.9.12

- Importazione listini CSV e JSON con anteprima e conferma.
- Controllo dei prezzi, dei campi obbligatori e dei codici duplicati.
- Separazione dei codici per fonte e marchio, ricerca per fonte e visualizzazione della provenienza.
- Backup SQLite prima di ogni importazione e registrazione di edizione e impronta del file originale.
- Reimportazione degli stessi dati senza duplicati; prezzi dei preventivi salvati conservati.
- Supporto ai pacchetti normalizzati da EPPAT 2026, Vimar 28.00 e BTicino 2126 RR.

L’accesso resta tramite Home Assistant Ingress, porta interna 8765. Il database esistente in `/data` viene mantenuto. I listini nuovi si caricano dalla sezione Prezzario dopo l’aggiornamento; non vengono importati automaticamente.

Verificati cinque test automatici e il caricamento completo di 48.774 voci su una copia temporanea del database. La prova sull’installazione reale Home Assistant resta da effettuare.
