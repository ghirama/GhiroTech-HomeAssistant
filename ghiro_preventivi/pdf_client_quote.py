"""Customer quote: bounded overview and room detail, with box-level sale totals."""
import datetime
import io
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle, PageBreak, Flowable, KeepTogether, CondPageBreak
from excel_quote import label, number, room_name, section
from pdf_summary import AQUA, NAVY, PALE


def object_value(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            raise ValueError('Raggruppamento scatole non valido: reimporta la configurazione nel preventivo.') from None
    if value is not None and not isinstance(value, dict):
        raise ValueError('Raggruppamento scatole non valido')
    return value


def customer_group(line):
    group = object_value(line.get('gruppo_cliente'))
    if group:
        if not all(isinstance(group.get(k), str) and group[k].strip() for k in ('id', 'nome', 'tipo')) or group['tipo'] not in ('scatola', 'quadro'):
            raise ValueError('Nome o identificativo della scatola non valido')
        return {k:label(group.get(k, '')).strip() for k in ('id','nome','tipo','descrizione')}
    # Recovery is restricted to recognizable, named configurator records.
    code = label(line.get('codice')).upper()
    desc = label(line.get('descrizione'))
    association = object_value(line.get('associazione'))
    context = label(association.get('contesto')) if association else ''
    parts = (context or desc).split(' — ')
    if len(parts) >= 3 and ((context and code.startswith(('SCAT-', 'FR-'))) or (len(parts) >= 4 and code.startswith(('VIMAR:', 'BTICINO:')) and re.match(r'^(VIMAR|BTICINO)\b', parts[2], re.I))):
        return {'id':'legacy-box:'+parts[1], 'nome':parts[1], 'tipo':'scatola', 'descrizione':parts[2]}
    if ' — Contenitore ' in desc or ' — Fila ' in desc:
        return {'id':'legacy-panel:'+parts[0], 'nome':parts[0], 'tipo':'quadro', 'descrizione':''}
    if code.startswith(('SCAT-', 'FR-')) or (code.startswith(('VIMAR:', 'BTICINO:')) and room_name(line)):
        raise ValueError('Alcune voci precedenti non identificano la scatola: reimporta la configurazione nel preventivo e verifica i prezzi prima di scaricare il PDF cliente.')
    return None


def summarize_quote(data):
    if not isinstance(data, dict) or not isinstance(data.get('righe'), list) or not 1 <= len(data['righe']) <= 5000:
        raise ValueError('Inserisci da 1 a 5000 voci nel preventivo')
    discount = max(0, min(100, number(data.get('sconto_materiale'))))/100
    markup = number(data.get('ricarico'))/100
    vat = number(data.get('iva'))/100
    if vat < 0 or markup < 0:
        raise ValueError('IVA e ricarico non validi')
    apartments = {}
    for index,line in enumerate(data['righe']):
        if not isinstance(line, dict):
            raise ValueError('Voce non valida')
        qty,cost = number(line.get('quantita')),number(line.get('prezzo'))
        if qty < 0 or cost < 0:
            raise ValueError('Quantità e prezzo non validi')
        if qty == 0:
            continue
        amount = number(qty*cost*(1-max(0,min(100,number(line.get('quota_materiale'))))/100*discount)*(1+markup))
        apartment = label(line.get('appartamento')).strip() or 'Generale'
        room = room_name(line)
        group = customer_group(line)
        a = apartments.setdefault(apartment, {'nome':apartment, 'voci':{}, 'totale':0})
        if group:
            key = (room,group['tipo'],group['id'])
            title = group['nome']
            description = group['descrizione']
        else:
            key = (room,'voce',str(index))
            title = label(line.get('descrizione')) or 'Fornitura / lavorazione'
            description = f"{qty:g} {label(line.get('unita'))}".strip()
        item = a['voci'].setdefault(key, {'stanza':room,'nome':title,'descrizione':description,'totale':0, 'sezione':('Quadri elettrici' if group and group['tipo']=='quadro' else section(line))})
        if group and (item['nome'] != title or item['descrizione'] != description):
            raise ValueError('La stessa scatola ha descrizioni discordanti: reimporta la configurazione.')
        item['totale'] += amount
        a['totale'] += amount
    if not apartments:
        raise ValueError('Il preventivo non contiene quantità maggiori di zero')
    def natural(name):
        return (name.casefold()=='parti comuni',[(1,int(x)) if x.isdigit() else (0,x.casefold()) for x in re.split(r'(\d+)',name)])
    result=[apartments[name] for name in sorted(apartments,key=natural)]
    return result,vat


def money(value):
    return f'{value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')+' €'


class SummaryEnd(Flowable):
    width=0
    height=0
    def draw(self):
        pass


class QuoteDoc(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, SummaryEnd) and self.page > 2:
            raise ValueError('Il riepilogo supera due pagine. Riduci il numero di appartamenti o la lunghezza delle intestazioni.')


def build_client_quote(data, logo):
    apartments,vat=summarize_quote(data)
    client=data.get('cliente') or {}
    if not isinstance(client,dict):
        raise ValueError('Cliente non valido')
    font='Helvetica'
    for folder in ['/usr/share/fonts/truetype/dejavu','/usr/share/fonts/ttf-dejavu','/usr/share/fonts/dejavu']:
        path=Path(folder)/'DejaVuSans.ttf'
        if path.exists():
            if 'GhiroClient' not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('GhiroClient',str(path)))
            font='GhiroClient';break
    body=ParagraphStyle('ClientBody',fontName=font,fontSize=9,leading=12,textColor=NAVY,spaceAfter=0)
    small=ParagraphStyle('ClientSmall',parent=body,fontSize=8,leading=10)
    heading=ParagraphStyle('ClientHeading',parent=body,fontSize=18,leading=22,spaceAfter=9,keepWithNext=True)
    sub=ParagraphStyle('ClientSub',parent=body,fontSize=11,leading=15,textColor=AQUA,spaceBefore=12,spaceAfter=6,keepWithNext=False)
    white=ParagraphStyle('ClientWhite',parent=body,textColor=colors.white,fontSize=8,leading=11)
    right=ParagraphStyle('ClientRight',parent=body,alignment=2)
    def p(value,style=body):
        return Paragraph(escape(label(value)).replace('\n','<br/>'),style)
    def table(headers, rows, widths, total=False, compact=False):
        cells=[[p(v,white) for v in headers]]+[[p(v,right if j else body) for j,v in enumerate(row)] for row in rows]
        t=LongTable(cells,colWidths=[v*mm for v in widths],repeatRows=1,hAlign='LEFT',splitInRow=1)
        styles=[('BACKGROUND',(0,0),(-1,0),AQUA),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),4 if compact else 7),('BOTTOMPADDING',(0,0),(-1,-1),4 if compact else 7)]
        if total:
            styles += [('LINEABOVE',(0,-1),(-1,-1),1,AQUA)]
        t.setStyle(TableStyle(styles));return t
    logo=Path(logo)
    def page(canvas, doc):
        canvas.saveState()
        if logo.exists():
            canvas.drawImage(str(logo),17*mm,267*mm,width=68*mm,height=24*mm,preserveAspectRatio=True,anchor='c',mask='auto')
        canvas.setFillColor(NAVY);canvas.setFont(font,7)
        for n,text in enumerate(['GHIRARDELLI MARCO - Ghiro Tech and Light','Via Giacomo Bresadola 5, 38025 Dimaro Folgarida (TN)','P. IVA 02834310399 - REA TN-254793','mghirardelli@pec.perind.it']):
            canvas.drawRightString(193*mm,(286-n*4)*mm,text)
        canvas.setStrokeColor(AQUA);canvas.line(17*mm,262*mm,193*mm,262*mm)
        canvas.line(17*mm,17*mm,193*mm,17*mm)
        canvas.setFont(font,7);canvas.drawString(17*mm,12*mm,'Ghiro Tech and Light - Preventivo cliente')
        canvas.drawRightString(193*mm,12*mm,f'Pagina {doc.page}');canvas.restoreState()
    net=sum(a['totale'] for a in apartments)
    story=[p('PREVENTIVO',heading),p(data.get('titolo') or 'Impianto elettrico'),Spacer(1,4*mm),p((f"Preventivo #{label(data['id'])} - " if data.get('id') else '')+datetime.date.today().strftime('%d/%m/%Y'),small),Spacer(1,5*mm)]
    story += [p('CLIENTE / COMMITTENTE',sub),p(client.get('nome') or 'Cliente'),p(client.get('indirizzo') or '',small),p(' - '.join(label(client[k]) for k in ('email','telefono') if client.get(k)),small)]
    story += [CondPageBreak(90),p('Riepilogo appartamenti',sub),table(['Appartamento / zona','Imponibile','IVA inclusa'],[[a['nome'],money(a['totale']),money(a['totale']*(1+vat))] for a in apartments],[100,38,38])]
    totals=table(['Riepilogo economico','Importo'],[['Imponibile',money(net)],[f'IVA {vat*100:g}%',money(net*vat)],['TOTALE PREVENTIVO',money(net*(1+vat))]],[126,50],True)
    story += [Spacer(1,6*mm),KeepTogether([totals]),Spacer(1,3*mm),p('Il dettaglio per stanza e scatola segue nelle pagine successive. Importi del dettaglio al netto di IVA.',small),SummaryEnd()]
    for a in apartments:
        story += [PageBreak(),p(a['nome'],heading),p('Dettaglio per stanza - importi al netto di IVA',small)]
        groups={}
        for item in a['voci'].values():
            key=(bool(item['stanza']),item['stanza'] or item['sezione'])
            groups.setdefault(key,[]).append(item)
        for (is_room,name),items in sorted(groups.items(),key=lambda x:not x[0][0]):
            story += [CondPageBreak(90),p(('Stanza: ' if is_room else '')+name,sub)]
            detail=[[item['nome']+(' · '+item['descrizione'] if item['descrizione'] else ''),money(item['totale'])] for item in items]
            detail.append(['Subtotale '+name,money(sum(item['totale'] for item in items))])
            story.append(table(['Scatola / fornitura','Totale'],detail,[138,38],True,compact=True))
        story += [Spacer(1,6*mm),KeepTogether([table(['Totale '+a['nome'],'Importo'],[['Imponibile',money(a['totale'])],[f'IVA {vat*100:g}%',money(a['totale']*vat)],['TOTALE IVA INCLUSA',money(a['totale']*(1+vat))]],[126,50],True)])]
    out=io.BytesIO()
    doc=QuoteDoc(out,pagesize=A4,leftMargin=17*mm,rightMargin=17*mm,topMargin=40*mm,bottomMargin=24*mm,title='Preventivo cliente',author='Ghiro Tech and Light')
    doc.build(story,onFirstPage=page,onLaterPages=page)
    return out.getvalue()
