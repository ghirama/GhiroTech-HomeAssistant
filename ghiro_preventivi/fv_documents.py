"""Generate editable working documents from a saved PV installation."""
import io
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfWriter

from docx import Document
from docx.shared import Mm, Pt
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

COMPANY = (
    "GHIRARDELLI MARCO · Impresa individuale · P. IVA 02834310399",
    "C.F. GHRMRC99T05H199Q · REA TN-254793 · PEC mghirardelli@pec.perind.it",
    "Via Giacomo Bresadola 5, 38025 Dimaro Folgarida (TN)",
)
EXTRA = {
    "cf": "Codice fiscale del firmatario",
    "societa": "Società rappresentata",
    "qualifica": "Qualifica del rappresentante",
    "cf_societa": "Codice fiscale della società",
    "piva": "Partita IVA del delegante",
    "indirizzo_impianto": "Indirizzo impianto",
    "pod": "POD",
    "distributore": "Distributore",
}
BLANK = "________________________________"


def field(label, value=None):
    displayed = BLANK if value is None or value == "" else value
    return f"{label} — {displayed}"


def build_package(client, plant, extra):
    """Return a ZIP with matching PDF and Word drafts for one installation."""
    if not isinstance(extra, dict):
        raise ValueError("Dati documentali non validi.")
    if any(not isinstance(extra.get(key, ""), str) or len(extra.get(key, "")) > 240
           for key in EXTRA):
        raise ValueError("I campi documentali devono contenere al massimo 240 caratteri.")
    fields = {key: field(label, extra.get(key, "").strip()) for key, label in EXTRA.items()}
    customer = [
        field("Cliente / firmatario", client["nome"]), fields["cf"],
        fields["societa"], fields["qualifica"], fields["cf_societa"], fields["piva"],
        field("Residenza / sede", client["indirizzo"]),
        field("E-mail", client["email"]), field("Telefono", client["telefono"]),
    ]
    kwp = plant["pannelli"] * plant["watt_pannello"] / 1000 if plant["pannelli"] and plant["watt_pannello"] else None
    technical = [
        field("Impianto", plant["titolo"]), fields["indirizzo_impianto"], fields["pod"],
        field("Potenza nominale (kWp)", kwp), fields["distributore"],
    ]
    design = technical + [
        field("Numero moduli", plant["pannelli"]),
        field("Potenza modulo (Wp)", plant["watt_pannello"]),
        field("Potenza inverter (kW)", plant["inverter_kw"]),
        field("Capacità accumulo (kWh)", plant["batteria_kwh"]),
        field("Orientamento", plant["orientamento"]),
        field("Inclinazione (°)", plant["inclinazione"]),
    ]
    signature = [field("Luogo e data"), field("Firma")]
    delegation_title = "Delega generale gestione pratiche fotovoltaiche"
    delegation_values = {
        "nome": client["nome"], "cf": extra.get("cf"),
        "societa": extra.get("societa"), "qualifica": extra.get("qualifica"),
        "soc_cf": extra.get("cf_societa"), "piva": extra.get("piva"),
        "indirizzo": client["indirizzo"], "email": client["email"], "telefono": client["telefono"],
        "impianto": extra.get("indirizzo_impianto"), "pod": extra.get("pod"),
        "potenza": str(kwp).replace(".", ",") if kwp is not None else "",
        "distributore": extra.get("distributore"),
    }
    documents = [
        ("Scheda sopralluogo", customer + design + [
            field("Accessi e lavori in quota"), field("Copertura, misure e ostacoli"),
            field("Ombreggiamento"), field("Contatore, quadro e impianto di terra"),
            field("Percorsi cavi e posizione apparecchi"),
            field("Foto, planimetrie e verifiche da approfondire"), field("Tecnico"),
        ] + signature),
        ("Scheda raccolta dati", customer + technical + [
            field("Intestatario POD e produttore"), field("Titolo di disponibilità dell’immobile"),
            field("Consensi e autorizzazioni"), field("Consumi annui e potenza disponibile"),
            field("Documenti acquisiti"), field("Documenti mancanti"),
        ]),
        ("Scheda tecnica per il preventivo", customer + design + [
            field("Produzione annua stimata e fonte"), field("Componenti e prestazioni previste"),
            field("Opere incluse ed escluse"), field("Pratiche e costi di connessione"),
            "Per importi, condizioni e dettaglio delle voci allegare il preventivo esportato dal gestionale.",
        ]),
        ("Contratto di fornitura e installazione", customer + design + [
            field("Riferimento al preventivo e agli allegati"), field("Prestazioni incluse ed escluse"),
            field("Corrispettivo, IVA e pagamenti"), field("Tempi e condizioni di avvio"),
            field("Pratiche a carico delle parti"), field("Garanzie e assistenza"),
            field("Varianti e condizioni applicabili"), field("Informazioni sul recesso, se applicabile"),
            field("Luogo e data"), field("Firma committente"), field("Firma impresa"),
        ]),
        ("Informativa privacy", [
            "Traccia da completare e verificare prima della consegna all’interessato.",
            field("Titolare del trattamento e recapiti"), field("Finalità e basi giuridiche"),
            field("Dati trattati e natura del conferimento"), field("Destinatari e trasferimenti"),
            field("Conservazione"), field("Diritti dell’interessato e modalità di esercizio"),
            field("Reclamo all’autorità di controllo"), field("Versione e data"),
        ]),
        (delegation_title, [
            "Oggetto — Gestione documentale delle pratiche relative all’impianto indicato.",
            *customer,
            "Il sottoscritto, in proprio o per la società indicata, delega GHIRARDELLI MARCO.",
            *technical,
            "La delega comprende preparazione e trasmissione di domande, allegati e integrazioni, consultazione dello stato e gestione delle comunicazioni per connessione, GSE e GAUDÌ, nei limiti ammessi. Usare il mandato dell’ente quando richiesto.",
            "Sono esclusi impegni economici, accettazione di preventivi o contratti e firme riservate. La delega dura dalla sottoscrizione alla chiusura delle pratiche o alla revoca anticipata scritta.",
            "La visura del 10/10/2026 riporta l’impresa come inattiva. Eventuali abilitazioni richiedono una verifica separata.",
            "Allegare copia del documento di identità del firmatario. Per il trattamento dei dati si rinvia all’informativa separata.",
            *signature,
        ]),
        ("Rapporto verifiche e prove", technical + [
            field("Tecnico, data e strumenti utilizzati"), field("Esame a vista e riscontri"),
            field("Continuità dei conduttori di protezione"), field("Isolamento e condizioni di prova"),
            field("Prove funzionali e protezioni"), field("Prove di interfaccia, se previste"),
            field("Misure, unità, esiti e allegati"), field("Anomalie e azioni correttive"),
        ] + signature),
        ("Verbale di consegna", customer + technical + [
            field("Documenti consegnati"), field("Configurazione e istruzioni consegnate"),
            field("Stato attivazione, GSE ed ENEA"), field("Pratiche aperte e responsabili"),
            field("Osservazioni del cliente"), field("Luogo e data"),
            field("Firma committente"), field("Firma impresa"),
        ]),
        ("Checklist pratiche e allegati", technical + [
            field("Comune — regime, eventuale pratica, protocollo e ricevuta"),
            field("Distributore — iter, domanda e accettazione"),
            field("Terna — modalità di censimento e codice CENSIMP"),
            field("Cantiere — sicurezza, incarichi e documenti"),
            field("Fine lavori — prove, schema definitivo, DiCo e relativi allegati"),
            field("Distributore — fine lavori, regolamento e attivazione"),
            field("GSE — regime, istanza e convenzione"),
            field("ENEA e altre pratiche eventuali — scadenza e ricevuta"),
            "Usare i portali e i moduli previsti dai singoli enti. La DiCo è rilasciata dall’impresa installatrice abilitata dopo le verifiche previste.",
        ]),
    ]
    result = io.BytesIO()
    styles = getSampleStyleSheet()
    meta_style = ParagraphStyle("Module", parent=styles["Normal"], alignment=TA_RIGHT)
    with zipfile.ZipFile(result, "w", zipfile.ZIP_DEFLATED) as archive:
        for title, lines in documents:
            doc = Document()
            section = doc.sections[0]
            section.page_width, section.page_height = Mm(210), Mm(297)
            section.top_margin = section.bottom_margin = Mm(16)
            normal = doc.styles["Normal"]
            normal.font.name = "Arial"
            normal.font.size = Pt(10)
            normal.paragraph_format.space_after = Pt(4)
            doc.add_paragraph(title).alignment = 2
            doc.add_paragraph("Da verificare prima della firma o dell’invio")
            for line in (*COMPANY, *lines):
                doc.add_paragraph(line)
            word = io.BytesIO()
            doc.save(word)
            if title == delegation_title:
                pdf = io.BytesIO()
                writer = PdfWriter(clone_from=Path(__file__).with_name("fv_delega.pdf"))
                values = {
                    name: str(value or "").strip() for name, value in delegation_values.items()
                }
                writer.update_page_form_field_values(writer.pages[0], values, auto_regenerate=False)
                writer.write(pdf)
                archive.writestr(title+".docx", word.getvalue())
                archive.writestr(title+".pdf", pdf.getvalue())
                continue
            pdf = io.BytesIO()
            flow = [Paragraph(escape(title), meta_style), Spacer(1, 12),
                    Paragraph("Da verificare prima della firma o dell’invio", styles["Heading3"])]
            for line in (*COMPANY, *lines):
                flow.extend((Paragraph(escape(line), styles["Normal"]), Spacer(1, 5)))
            SimpleDocTemplate(pdf, pagesize=(595.28, 841.89), topMargin=37,
                              bottomMargin=37, leftMargin=42, rightMargin=42,
                              title=title, author=COMPANY[0].split(" · ")[0]).build(flow)
            archive.writestr(title+".docx", word.getvalue())
            archive.writestr(title+".pdf", pdf.getvalue())
    return result.getvalue()
