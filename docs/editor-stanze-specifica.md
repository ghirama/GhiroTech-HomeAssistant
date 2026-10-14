# Editor planimetria per stanze

Obiettivo: editor per PDF/JPG/PNG con planimetria fissa, simboli elettrici e stanze nominate.

## Modello dati
Ogni configurazione civile ha stanze con id, nome e una lista di punti. Ogni punto ha id, tipo, coordinate percentuali x/y e, se è una scatola, serie civile, capacità e frutti.

## Interazione
- Creare, rinominare e duplicare stanze.
- Posizionare e spostare simboli con mouse o touch.
- Aprire un compositore quando si seleziona una scatola.
- Scegliere Vimar Plana, Arké, Linea, BTicino Livinglight o Living Now.
- Controllare la capienza della scatola senza inventare compatibilità o codici articolo.
- Salvare nel database esistente tramite configurazioni_civili, senza sovrascrivere i preventivi.
- Conteggio dei simboli per stanza e per appartamento.

## Prima del rilascio
Implementare l'interfaccia, persistenza della planimetria in /data, validazione dei dati e test Ingress/iPad. I listini ufficiali verranno importati separatamente.
