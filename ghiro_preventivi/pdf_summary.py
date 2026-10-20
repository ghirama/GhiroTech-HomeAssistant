"""Printable configuration summary, with no economic calculations."""
import io
import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image

AQUA=colors.HexColor('#2C829B')
NAVY=colors.HexColor('#193B4B')
PALE=colors.HexColor('#EDF6F8')

def build_summary(data, logo):
    out=io.BytesIO()
    font='Helvetica'
    for folder in ['/usr/share/fonts/truetype/dejavu','/usr/share/fonts/ttf-dejavu','/usr/share/fonts/dejavu']:
        path=Path(folder)/'DejaVuSans.ttf'
        if path.exists():
            if 'GhiroSans' not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont('GhiroSans',str(path)))
            font='GhiroSans';break
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyG',fontName=font,fontSize=9,leading=13,textColor=NAVY,spaceAfter=5))
    styles.add(ParagraphStyle(name='SmallG',parent=styles['BodyG'],fontSize=8,leading=11))
    styles.add(ParagraphStyle(name='TitleG',parent=styles['BodyG'],fontSize=25,leading=29,spaceAfter=14))
    styles.add(ParagraphStyle(name='HeadG',parent=styles['BodyG'],fontSize=16,leading=20,spaceBefore=12,spaceAfter=8,keepWithNext=True))
    styles.add(ParagraphStyle(name='SubG',parent=styles['BodyG'],fontSize=11,leading=15,textColor=AQUA,spaceBefore=10,keepWithNext=True))
    styles.add(ParagraphStyle(name='WhiteG',parent=styles['SmallG'],textColor=colors.white))
    def p(value, style='BodyG'):
        return Paragraph(escape(str('' if value is None else value)).replace('\n','<br/>'),styles[style])
    def table(headers, rows, widths):
        cells=[[p(x,'WhiteG') for x in headers]]+[[p(x,'SmallG') for x in row] for row in rows]
        t=Table(cells,colWidths=[x*mm for x in widths],repeatRows=1,hAlign='LEFT',splitInRow=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),AQUA),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.5,AQUA)]))
        return t
    def footer(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(AQUA);canvas.line(17*mm,17*mm,193*mm,17*mm)
        canvas.setFont(font,8);canvas.setFillColor(NAVY);canvas.drawString(17*mm,12*mm,'Ghiro Tech & Light | Riepilogo impianto')
        canvas.drawRightString(193*mm,12*mm,'Pagina '+str(doc.page));canvas.restoreState()
    story=[]
    logo=Path(logo)
    if logo.exists():story.extend([Image(str(logo),width=77*mm,height=28*mm,hAlign='LEFT'),Spacer(1,10*mm)])
    story+=[p('RIEPILOGO IMPIANTO','TitleG'),p(data.get('titolo'),'HeadG'),p(data.get('descrizione')),p('Configurazione #'+str(data.get('id') or '-')+' | '+datetime.date.today().strftime('%d/%m/%Y'),'SmallG'),Spacer(1,5*mm)]
    story.append(table(['CLIENTE / COMMITTENTE','FORNITORE / INSTALLATORE'],[[data.get('cliente') or 'Cliente non associato','GHIRARDELLI MARCO\nGhiro Tech and Light\nVia Giacomo Bresadola 5\n38025 Dimaro Folgarida (TN)\nP. IVA 02834310399 | REA TN-254793\nmghirardelli@pec.perind.it']],[88,88]))
    story.extend([p('Panoramica','HeadG'),table(['Appartamento / zona','Stanze','Portafrutti','Derivazioni','Quadri'],[[a['nome'],len(a['stanze']),sum(len(r['scatole']) for r in a['stanze']),sum(b['quantita'] for r in a['stanze'] for b in r['derivazioni']),len(a['quadri'])] for a in data['appartamenti']],[72,22,28,29,25])])
    for a in data['appartamenti']:
        if a['stanze'] or a['quadri']:story.append(PageBreak())
        story.append(p(a['nome'],'HeadG'))
        if a.get('costi_impianto'):
            story.extend([p('Cavi, tubazioni e manodopera','SubG'),table(['Voce','Quantità','Unità'],[[r['descrizione'],r['quantita'],r['unita']] for r in a['costi_impianto']],[125,28,23])])
        for r in a['stanze']:
            story.append(p(r['nome'],'HeadG'))
            story.append(table(['Riepilogo punti','Quantità'],r['punti'],[143,33]))
            for b in r['scatole']:
                story.extend([p(b['nome']+' | Scatola portafrutti','SubG'),p(b['serie']+' | '+str(b['occupati'])+' / '+str(b['moduli'])+' moduli occupati','SmallG')])
                story.append(table(['Posizione','Componente','Moduli'],b['componenti'],[28,120,28]))
                if b.get('note'):story.append(p('Note: '+b['note']))
            if r['derivazioni']:
                story.extend([p('Scatole di derivazione','SubG'),table(['Nome / quantità','Formato e dimensioni','Note'],[[b['nome']+'\nQuantità: '+str(b['quantita']),b['dettagli'],b.get('note','')] for b in r['derivazioni']],[43,85,48])])
        for q in a['quadri']:
            story.extend([p(q['nome']+' | Quadro elettrico','HeadG'),p(q['dettagli'])])
            story.append(table(['Fila / posizione','Componente','Moduli','Circuito e caratteristiche / codice'],[[str(c['fila'])+' / '+str(c['posizione']),c['tipo'],c['moduli'],'\n'.join(filter(None,[c.get('descrizione'),c.get('codice'),c.get('articolo')]))] for c in q['componenti']] or [['-','Nessun componente','-','']],[27,51,20,78]))
            if q.get('note'):story.append(p('Note: '+q['note']))
        if not a['stanze'] and not a['quadri'] and not a.get('costi_impianto'):story.append(p('Nessuna stanza o quadro inserito.'))
    doc=SimpleDocTemplate(out,pagesize=A4,rightMargin=17*mm,leftMargin=17*mm,topMargin=16*mm,bottomMargin=24*mm,title=str(data.get('titolo') or 'Riepilogo impianto'),author='Ghiro Tech & Light')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()
