"""Persistent, per-installation job and filing checklist."""
import base64
import binascii
import datetime
import re

SET = "https://www.setdistribuzione.it/per-i-clienti/produttori/modalita-connessione-impianti.html"
SET_END = "https://www.setdistribuzione.it/per-i-clienti/produttori/regole--soluzioni-e-documentazione-per-la-connessione.html"
COMUNE = "https://www.provincia.tn.it/News/Approfondimenti/Modulistica-UNICA-e-standardizzata-per-attivita-edilizia-e-tutela-del-paesaggio"
TASKS = (
    ("cliente", "1. Preparazione", "Anagrafica, bolletta e disponibilità dell’immobile", "Tecnico e cliente", "", "Identifica cliente, produttore, intestatario POD e raccogli i consensi applicabili."),
    ("sopralluogo", "1. Preparazione", "Sopralluogo e verifica del sito", "Tecnico", "", "Archivia rilievi, foto, accessi, verifica preliminare della copertura e posizione dei componenti."),
    ("contratto", "1. Preparazione", "Preventivo, contratto, privacy e deleghe", "Cliente e impresa", "", "Archivia preventivo e contratto firmati, informativa e mandato richiesto per la pratica."),
    ("comune", "2. Progetto e pratiche iniziali", "Comune: regime edilizio, vincoli e protocollo", "Proprietario o tecnico incaricato", COMUNE, "Verifica il regime con il Comune. Conserva il modulo trasmesso, gli allegati e il protocollo, ove richiesti."),
    ("progetto", "2. Progetto e pratiche iniziali", "Progetto elettrico e verifiche specialistiche", "Progettista o responsabile tecnico", "", "Archivia schema, layout, relazioni e eventuali elaborati strutturali o antincendio."),
    ("connessione", "2. Progetto e pratiche iniziali", "Distributore: domanda di connessione", "Produttore o mandatario", SET, "Parte I del Modello Unico o domanda ordinaria. Verifica POD, mandati, preventivo di connessione ed eventuale accettazione."),
    ("gaudi", "2. Progetto e pratiche iniziali", "Terna: censimento GAUDÌ e CENSIMP", "Produttore, mandatario o distributore", "https://my.terna.it/it-IT/support/", "Verifica chi registra l’impianto in base all’iter. Con Modello Unico il flusso è gestito dal distributore."),
    ("sicurezza", "3. Cantiere", "Sicurezza e documenti delle imprese", "Committente e imprese", "", "Verifica lavori in quota, idoneità, DURC, POS, coordinamento e notifiche applicabili prima dell’avvio."),
    ("installazione", "3. Cantiere", "Installazione, materiali, matricole e varianti", "Impresa installatrice", "", "Registra componenti, matricole, fotografie e modifiche rispetto al progetto."),
    ("prove", "4. Fine lavori e messa in servizio", "Prove elettriche e protezioni", "Tecnico incaricato", "", "Inserisci misure effettive, esito delle verifiche e, se prevista, prova dell’interfaccia."),
    ("dico", "4. Fine lavori e messa in servizio", "Dichiarazione di conformità e allegati", "Impresa installatrice abilitata", "https://www.normattiva.it/atto/caricaDettaglioAtto?atto.articolo.numero=7&atto.codiceRedazionale=008G0060&atto.dataPubblicazioneGazzetta=2008-03-12", "Archivia DiCo firmata, progetto/schema definitivo, relazione materiali e altri allegati applicabili."),
    ("fine", "4. Fine lavori e messa in servizio", "Distributore: fine lavori e regolamento di esercizio", "Produttore e tecnico", SET_END, "Parte II del Modello Unico o fine lavori ordinario. Verifica elenco allegati, regolamento e conferma di invio."),
    ("attivazione", "4. Fine lavori e messa in servizio", "Attivazione della connessione", "Distributore", SET_END, "Registra la data di attivazione e allega il verbale o altra evidenza del gestore."),
    ("gse", "5. Incentivi e consegna", "GSE: regime energia e convenzione", "Produttore o referente", "https://www.gse.it/servizi-per-te/fotovoltaico/ritiro-dedicato", "Verifica se il servizio è richiesto. Conserva istanza o flusso Modello Unico, esito e convenzione."),
    ("enea", "5. Incentivi e consegna", "ENEA: comunicazione per detrazione", "Beneficiario o incaricato", "https://bonusfiscali.enea.it/", "Verifica applicabilità, anno del portale e termine. Archivia scheda e ricevuta."),
    ("adm", "5. Incentivi e consegna", "ADM, CER e altri adempimenti specifici", "Produttore o soggetto incaricato", "https://www.adm.gov.it/portale/energia-elettrica-rilascio-licenza-di-officina-elettrica-art.-53-del-tua-", "Verifica l’applicabilità già prima dei lavori. Archivia gli atti pertinenti al caso."),
    ("consegna", "5. Incentivi e consegna", "Fascicolo finale e verbale di consegna", "Impresa e cliente", "", "Consegna DiCo, schemi, manuali, garanzie, ricevute disponibili e istruzioni. Indica eventuali pratiche ancora aperte."),
)
STATUSES = ("Da fare", "In corso", "In attesa", "Completata", "Non applicabile")
KEYS = {row[0] for row in TASKS}
MAX_FILE = 8 * 1024 * 1024


def initialize(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS fv_workflow (
        plant_id INTEGER NOT NULL, task TEXT NOT NULL, stato TEXT NOT NULL,
        scadenza TEXT NOT NULL, responsabile TEXT NOT NULL, note TEXT NOT NULL,
        PRIMARY KEY (plant_id, task)
    );
    CREATE TABLE IF NOT EXISTS fv_workflow_files (
        id INTEGER PRIMARY KEY, plant_id INTEGER NOT NULL, task TEXT NOT NULL,
        nome TEXT NOT NULL, dati BLOB NOT NULL
    );
    CREATE INDEX IF NOT EXISTS fv_workflow_files_plant ON fv_workflow_files(plant_id, task);
    """)


def get_plan(db, plant_id):
    saved = {row["task"]: dict(row) for row in db.execute(
        "SELECT task,stato,scadenza,responsabile,note FROM fv_workflow WHERE plant_id=?", (plant_id,)
    )}
    files = {}
    for row in db.execute("SELECT id,task,nome FROM fv_workflow_files WHERE plant_id=? ORDER BY id", (plant_id,)):
        files.setdefault(row["task"], []).append({"id": row["id"], "nome": row["nome"]})
    return [
        {"task": key, "fase": phase, "titolo": title, "guida": guide, "fonte": url,
         "stato": STATUSES[0], "scadenza": "", "responsabile": role, "note": "",
         **saved.get(key, {}), "file": files.get(key, [])}
        for key, phase, title, role, url, guide in TASKS
    ]


def save_task(db, plant_id, payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("task"), str) or payload["task"] not in KEYS:
        raise ValueError("Attività non valida.")
    key = payload["task"]
    if payload.get("file") is not None:
        file = payload["file"]
        if not isinstance(file, dict):
            raise ValueError("Allegato non valido.")
        name, encoded = file.get("nome"), file.get("dati")
        if not isinstance(name, str) or not isinstance(encoded, str):
            raise ValueError("Allegato non valido.")
        name = re.sub(r"[\\/\x00-\x1f\x7f]", "_", name.strip())[:180]
        if len(encoded) > ((MAX_FILE + 2) // 3) * 4:
            raise ValueError("Allegato massimo 8 MB.")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error):
            raise ValueError("Allegato non valido.") from None
        if not name or not 0 < len(data) <= MAX_FILE:
            raise ValueError("Allegato vuoto o troppo grande.")
        db.execute("INSERT INTO fv_workflow_files(plant_id,task,nome,dati) VALUES(?,?,?,?)",
                   (plant_id, key, name, data))
    status, deadline, owner, notes = (payload.get(k, "") for k in ("stato", "scadenza", "responsabile", "note"))
    if status not in STATUSES or not all(isinstance(x, str) for x in (deadline, owner, notes)):
        raise ValueError("Stato o dati dell’attività non validi.")
    if deadline:
        try:
            if datetime.date.fromisoformat(deadline).isoformat() != deadline:
                raise ValueError
        except ValueError:
            raise ValueError("Scadenza non valida.") from None
    if len(owner) > 180 or len(notes) > 4000:
        raise ValueError("Responsabile o note troppo lunghi.")
    db.execute("""INSERT INTO fv_workflow(plant_id,task,stato,scadenza,responsabile,note)
               VALUES(?,?,?,?,?,?) ON CONFLICT(plant_id,task) DO UPDATE SET
               stato=excluded.stato,scadenza=excluded.scadenza,
               responsabile=excluded.responsabile,note=excluded.note""",
               (plant_id, key, status, deadline, owner, notes))
    db.commit()
