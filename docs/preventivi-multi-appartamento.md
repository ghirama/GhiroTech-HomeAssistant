# Preventivi con più appartamenti

Una configurazione può contenere più appartamenti. `Parti comuni` è un normale appartamento con quel nome: stanze, scatole, note e operazioni sono identici.

Nel configuratore usare `+ Appartamento`, `+ Parti comuni` o `Duplica appartamento`. La copia è indipendente. Il selettore mostra le stanze e le scatole dell'appartamento attivo; il trasferimento al preventivo include tutti gli appartamenti. Le voci conservano il nome dell'appartamento anche dopo salvataggio, riapertura ed esportazione JSON. Il riepilogo mostra i subtotali imponibili e il totale generale, applicando gli stessi sconti, ricarichi e IVA del preventivo.

Nell'editor planimetria ogni appartamento mantiene il proprio sfondo JPG/PNG/PDF e i propri punti. La duplicazione copia anche la planimetria e assegna nuovi identificativi ai punti. Le configurazioni precedenti sono ricondotte ad Appartamento 1.

Le note delle scatole sono persistenti in entrambi gli editor. Restano interne alla configurazione; l'eventuale allegato tecnico stampabile con selezione delle note non è incluso in questa modifica.

La stampa cliente riprende logo, intestazione e palette Digital Aqua Blue della bozza approvata, aggiungendo il riepilogo per appartamento. I prezzi di listino devono essere associati alle voci come già previsto dal gestionale.

## Verifica

- `node tools/check_frontend.mjs`
- `node tools/check_apartments.mjs`
- `python3 -m unittest discover -s tests -p test_saving.py`

Versione add-on: 0.9.15. Il test JavaScript usa un adattatore DOM; `tools/check_browser.cjs` verifica anche le interazioni in Chromium, la stampa multipagina e il layout tablet, usando un database temporaneo e il server di prova isolato `tools/browser_test_server.py`. Gli artefatti di GitHub Actions permettono di controllare le schermate e i PDF prodotti. L’installazione Home Assistant reale non è accessibile da questa procedura: l’aggiornamento si installa dal negozio add-on.
