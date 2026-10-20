# Catalogo Gewiss nel configuratore quadri

Dalla versione 0.9.43, i pulsanti **Scegli contenitore Gewiss** e **Scegli componente Gewiss** aprono la scelta guidata. Importare prima il listino METEL Gewiss nella sezione Listini.

1. Scegliere il tipo di componente nel quadro e aprire la scelta guidata.
2. Restringere per serie, moduli e caratteristiche disponibili. Nei contenitori si possono filtrare installazione e grado IP; negli interruttori poli, corrente, curva, potere di interruzione, tipo differenziale e sensibilità.
3. Verificare la descrizione completa e scegliere il codice esatto. Le caratteristiche vengono filtrate, non dimensionate automaticamente per l'impianto.
4. Posizionare il componente nella cella desiderata. Per i contenitori vengono applicate le dimensioni esterne e le file esplicite del catalogo, senza sovrapporre i componenti già presenti.
5. Salvare il progetto o un modello di quadro. L'importazione nel preventivo usa il codice scelto e il prezzo del listino attivo.

**Azzera filtri** permette di cercare anche articoli di un altro tipo. Sono mostrati al massimo 100 risultati, con il numero totale e filtri calcolati sull'intero elenco. Gli articoli non attivi, senza prezzo positivo o con unità diversa da cad non vengono proposti.

## Fonti e copertura

`gewiss_catalog.json` contiene 1.446 schede di dati numerici estratti dalle tabelle del catalogo commerciale Gewiss 2025/2026 fornito, con riferimento alla pagina PDF (non alla numerazione stampata). Le famiglie comprendono centralini 40 CD/CDe/CDi, 42 RV, 48 PTC e apparecchi modulari 90 MCB, 90 RCD e 90 AM. Non è una riproduzione del catalogo e non contiene prezzi né immagini.

Il codice esatto collega questi dati al listino importato. La serie viene dal catalogo; le caratteristiche elettriche e il grado IP sono letti solo quando espliciti nella descrizione METEL. Il potere di interruzione visualizzato è quello descritto dal listino: la scheda tecnica del produttore resta il riferimento per norma e tensione di applicazione. AFDD e blocchi differenziali componibili non sono classificati come normali magnetotermici o differenziali completi.

Gli articoli nuovi restano ricercabili dal listino anche se privi di scheda integrata. Aggiornare i prezzi tramite METEL non richiede una nuova versione e conserva i codici salvati. L'estensione dei metadati tecnici del catalogo integrato richiede invece un aggiornamento delle schede dell'applicazione.

Le capacità aggiuntive, ad esempio 24+2, sono indicate nella scheda: la griglia usa i 24 moduli della disposizione principale. La geometria di contenitori senza disposizione esplicita deve essere impostata manualmente. Gli ingombri frazionari restano esclusi dalla griglia. Se catalogo e listino indicano larghezze diverse, la scelta è bloccata; se manca l'ingombro, occorre confermare quello verificato sul catalogo.

## Manutenzione

L'estrazione è riproducibile con `pdftotext -layout` seguito da `tools/extract_gewiss_catalog.py`. Lo script considera colonne esplicite delle sole sezioni previste, ignora matrici di selezione e didascalie e rifiuta dati numerici discordanti per lo stesso codice. Tabelle con più colonne di capacità sono escluse. Il PDF originale e il listino commerciale non vanno committati.
