"""Populate the branded Artifact Tool template using standard OOXML only.

No office suite or external service is needed on Home Assistant. Formulas have
cached values for previews and are recalculated by Excel when inputs change.
"""
import base64
import copy
import datetime
import io
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
ET.register_namespace('', NS)
ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')


def tag(name):
    return '{' + NS + '}' + name


def number(value):
    try:
        n = float(value or 0)
    except (TypeError, ValueError):
        raise ValueError('Valore numerico non valido') from None
    if not math.isfinite(n) or abs(n) > 1e15:
        raise ValueError('Valore numerico fuori limite')
    return n


def label(value):
    # XML 1.0 cannot represent control characters, even as character references.
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]', '', str(value or ''))[:32767]


def cell(row, column, value, formula=None):
    ref = column + row.attrib['r']
    c = next((x for x in row.findall(tag('c')) if x.get('r') == ref), None)
    if c is None:
        c = ET.SubElement(row, tag('c'), {'r': ref})
    for x in list(c):
        c.remove(x)
    c.attrib.pop('t', None)
    if formula is not None:
        ET.SubElement(c, tag('f')).text = formula
        if isinstance(value, str):
            c.set('t', 'str')
            ET.SubElement(c, tag('v')).text = label(value)
        else:
            ET.SubElement(c, tag('v')).text = str(number(value))
    elif isinstance(value, (float, int)):
        ET.SubElement(c, tag('v')).text = str(number(value))
    else:
        c.set('t', 'inlineStr')
        t = ET.SubElement(ET.SubElement(c, tag('is')), tag('t'))
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        t.text = label(value)
    return c


def clone(row, index):
    row = copy.deepcopy(row)
    row.set('r', str(index))
    for c in row.findall(tag('c')):
        c.set('r', re.sub(r'\d+$', str(index), c.get('r')))
        for child in list(c):
            c.remove(child)
        c.attrib.pop('t', None)
    return row


def configure_print(root, last, width, landscape=False):
    dimension = root.find(tag('dimension'))
    if dimension is None:
        dimension = ET.Element(tag('dimension'))
        root.insert(1 if root.find(tag('sheetPr')) is not None else 0, dimension)
    dimension.set('ref', f'A1:{width}{last}')
    props = root.find(tag('sheetPr'))
    if props is None:
        props = ET.Element(tag('sheetPr'))
        root.insert(0, props)
    fit = props.find(tag('pageSetUpPr'))
    if fit is None:
        fit = ET.SubElement(props, tag('pageSetUpPr'))
    fit.set('fitToPage', '1')
    # Keep schema order: print settings precede drawings.
    for name in ('pageMargins', 'pageSetup', 'headerFooter'):
        old = root.find(tag(name))
        if old is not None:
            root.remove(old)
    pos = next((i for i, x in enumerate(root) if x.tag in (tag('drawing'), tag('extLst'))), len(root))
    margins = ET.Element(tag('pageMargins'), dict(left='0.3', right='0.3', top='0.35', bottom='0.4', header='0.15', footer='0.2'))
    setup = ET.Element(tag('pageSetup'), dict(paperSize='9', orientation='landscape' if landscape else 'portrait', fitToWidth='1', fitToHeight='0'))
    footer = ET.Element(tag('headerFooter'))
    ET.SubElement(footer, tag('oddFooter')).text = '&LGhiro Tech and Light&RPagina &P di &N'
    for offset, item in enumerate((margins, setup, footer)):
        root.insert(pos + offset, item)


def build_quote(data):
    if not isinstance(data, dict):
        raise ValueError('Preventivo non valido')
    lines = data.get('righe', [])
    if not isinstance(lines, list) or not lines or len(lines) > 5000:
        raise ValueError('Inserisci da 1 a 5000 voci nel preventivo')
    if any(not isinstance(r, dict) for r in lines):
        raise ValueError('Voce non valida')
    discount = max(0, min(100, number(data.get('sconto_materiale')))) / 100
    markup, vat = number(data.get('ricarico')) / 100, number(data.get('iva')) / 100
    source = base64.b64decode(Path(__file__).with_name('quote_template.b64').read_text())
    with zipfile.ZipFile(io.BytesIO(source)) as z:
        files = {name: z.read(name) for name in z.namelist()}
    p, c = [ET.fromstring(files[f'xl/worksheets/sheet{i}.xml']) for i in (1, 2)]
    ps, cs = p.find(tag('sheetData')), c.find(tag('sheetData'))
    pr = {int(r.get('r')): r for r in ps}; cr = {int(r.get('r')): r for r in cs}
    detail, subtotal, totalstyle, internal = pr[17], pr[18], pr[19], cr[9]
    for r in list(ps):
        if int(r.get('r')) >= 17:
            ps.remove(r)
    for r in list(cs):
        if int(r.get('r')) >= 9:
            cs.remove(r)
    client = data.get('cliente') or {}
    if not isinstance(client, dict):
        raise ValueError('Cliente non valido')
    date = datetime.date.today().strftime('%d/%m/%Y')
    cell(pr[4], 'A', (f"Preventivo #{label(data['id'])} · " if data.get('id') else '') + 'Data: ' + date)
    cell(pr[7], 'D', client.get('nome', 'Cliente'))
    cell(pr[8], 'D', client.get('indirizzo', ''))
    cell(pr[9], 'D', ' · '.join(label(client[k]) for k in ('email', 'telefono') if client.get(k)))
    cell(pr[11], 'A', data.get('titolo', 'Preventivo'))
    for r, v in ((4, discount), (5, markup), (6, vat)):
        cell(cr[r], 'B', v)
    groups = {}
    net = 0
    for i, line in enumerate(lines):
        j, k = i + 9, i + 17
        ir, out = clone(internal, j), clone(detail, k)
        apartment = label(line.get('appartamento')) or 'Generale'
        qty, cost = number(line.get('quantita')), number(line.get('prezzo'))
        share = max(0, min(100, number(line.get('quota_materiale')))) / 100
        discounted = cost * (1 - share * discount)
        sell = discounted * (1 + markup)
        amount = number(sell * qty)
        values = [apartment, label(line.get('codice')), label(line.get('descrizione')), label(line.get('unita')), qty, cost, share]
        for col, v in zip('ABCDEFG', values):
            cell(ir, col, v)
        cell(ir, 'H', discounted, f'F{j}*(1-MAX(0,MIN(1,G{j}))*MAX(0,MIN(1,$B$4)))')
        cell(ir, 'I', sell, f'H{j}*(1+$B$5)')
        cell(ir, 'J', amount, f'I{j}*E{j}')
        for col, src, value in zip('ABCDEF', 'ACDEIJ', [apartment, values[2], values[3], qty, sell, amount]):
            cell(out, col, value, f"'Calcolo interno'!{src}{j}")
        # Allow long descriptions to wrap instead of clipping in print.
        height = min(409, max(42, 15 * math.ceil(len(values[2]) / 55)))
        out.set('ht', str(height)); ir.set('ht', str(height))
        ps.append(out); cs.append(ir)
        group = groups.setdefault(apartment, {'total': 0, 'rows': []})
        group['total'] += amount; group['rows'].append(k)
        net += amount
    last_line = 16 + len(lines)
    index = last_line + 2
    for apartment, group in groups.items():
        row = clone(subtotal, index)
        cell(row, 'B', 'Subtotale appartamento / zona')
        cell(row, 'A', apartment)
        formula = f'SUMPRODUCT((A17:A{last_line}=A{index})*F17:F{last_line})'
        cell(row, 'F', group['total'], formula)
        ps.append(row); index += 1
    for title, value, formula, style in (
        ('Imponibile', net, f'SUM(F17:F{last_line})', subtotal),
        ('IVA', net * vat, f"F{index}*'Calcolo interno'!$B$6", subtotal),
        ('TOTALE PREVENTIVO', net * (1 + vat), f'F{index}+F{index+1}', totalstyle),
    ):
        row = clone(style, index); cell(row, 'B', title); cell(row, 'F', value, formula)
        ps.append(row); index += 1
    configure_print(p, index - 1, 'F')
    configure_print(c, 8 + len(lines), 'J', True)
    book = ET.fromstring(files['xl/workbook.xml'])
    old = book.find(tag('definedNames'))
    if old is not None:
        book.remove(old)
    names = ET.Element(tag('definedNames'))
    calc = book.find(tag('calcPr'))
    if calc is None:
        calc = ET.SubElement(book, tag('calcPr'))
    book.insert(list(book).index(calc), names)
    for i, title, area, repeat in ((0, 'Preventivo', f'$A$1:$F${index-1}', '$16:$16'), (1, 'Calcolo interno', f'$A$1:$J${8+len(lines)}', '$8:$8')):
        for name, value in (('_xlnm.Print_Area', area), ('_xlnm.Print_Titles', repeat)):
            ET.SubElement(names, tag('definedName'), {'name': name, 'localSheetId': str(i)}).text = f"'{title}'!{value}"
    calc.attrib.update(calcMode='auto', fullCalcOnLoad='1', forceFullCalc='1')
    files['xl/workbook.xml'] = ET.tostring(book, encoding='utf-8', xml_declaration=True)
    for i, root in enumerate((p, c), 1):
        files[f'xl/worksheets/sheet{i}.xml'] = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content)
    return output.getvalue()
