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


def _build_combined(data):
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

REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
DOCREL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'


def xml_bytes(root):
    # OPC parsers expect default namespaces on package metadata. Avoid changing
    # ElementTree's global namespace registry in a threaded HTTP handler.
    namespace = root.tag.split('}')[0].lstrip('{')
    if namespace in (REL, CT):
        root = copy.deepcopy(root)
        for node in root.iter():
            node.tag = node.tag.split('}')[-1]
        root.set('xmlns', namespace)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def sheet_name(value, used):
    name = re.sub(r'[\\/*?:\[\]]', '-', value).strip().strip("'")[:31].rstrip("'") or 'Generale'
    base, suffix = name, 2
    while name.casefold() in used:
        tail = f' ({suffix})'; name = base[:31-len(tail)] + tail; suffix += 1
    used.add(name.casefold())
    return name


def quoted(name):
    return "'" + name.replace("'", "''") + "'"



def build_quote(data):
    # Preserve the existing costs, formulas and columns; split only the client
    # view into apartment sheets. All views refer to the same internal inputs.
    combined = _build_combined(data)
    with zipfile.ZipFile(io.BytesIO(combined)) as z:
        original = {name: z.read(name) for name in z.namelist()}
    template = ET.fromstring(original['xl/worksheets/sheet1.xml'])
    internal = ET.fromstring(original['xl/worksheets/sheet2.xml'])
    template_rows = {int(r.get('r')): r for r in template.find(tag('sheetData'))}
    lines = data['righe']; groups = {}
    for i, line in enumerate(lines):
        groups.setdefault(label(line.get('appartamento')) or 'Generale', []).append(i)
    def clean_sheet():
        root = copy.deepcopy(template); rows = root.find(tag('sheetData'))
        for row in list(rows):
            if int(row.get('r')) >= 17:
                rows.remove(row)
        return root, rows
    # Reuse the established subtotal and total formatting from the template.
    subtotal_style = template_rows[18 + len(lines)]
    total_style = template_rows[max(template_rows)]
    summary, summary_rows = clean_sheet()
    sh = {int(r.get('r')): r for r in summary_rows}
    cell(sh[2], 'A', 'RIEPILOGO PREVENTIVO')
    for col, value in zip('ABCDEF', ['Appartamento / zona', '', '', 'Voci', 'Imponibile', 'Totale IVA inclusa']):
        cell(sh[16], col, value)
    used = {'riepilogo generale', 'calcolo interno', 'history'}
    sheets = [('Riepilogo generale', summary, 1, 'F')]
    grand = 0; vat = number(data.get('iva')) / 100
    def natural(name):
        return (name.casefold() == 'parti comuni', [(1, int(x)) if x.isdigit() else (0, x.casefold()) for x in re.split(r'(\d+)', name)])
    for apartment in sorted(groups, key=natural):
        name = sheet_name(apartment, used)
        root, rows = clean_sheet()
        header = next(r for r in rows if r.get('r') == '11')
        cell(header, 'A', apartment + ' — ' + label(data.get('titolo') or 'Preventivo'))
        net = 0
        for j, source_index in enumerate(groups[apartment], 17):
            # Preserve formulas pointing to the original internal row, not the
            # new apartment row number. Cell addresses alone move here.
            row = copy.deepcopy(template_rows[17 + source_index]); row.set('r', str(j))
            for c in row.findall(tag('c')):
                c.set('r', re.sub(r'\d+$', str(j), c.get('r')))
            rows.append(row)
            net += float(next(c for c in row if c.get('r') == f'F{j}').findtext(tag('v')))
        last = 16 + len(groups[apartment]); total_row = last + 4
        for r, title, value, formula, style in (
            (last+2, 'Imponibile', net, f'SUM(F17:F{last})', subtotal_style),
            (last+3, 'IVA', net*vat, f"F{last+2}*'Calcolo interno'!$B$6", subtotal_style),
            (total_row, 'TOTALE PREVENTIVO', net*(1+vat), f'F{last+2}+F{last+3}', total_style),
        ):
            row = clone(style, r); cell(row, 'B', title); cell(row, 'F', value, formula); rows.append(row)
        r = 16 + len(sheets); row = clone(template_rows[17], r)
        cell(row, 'A', apartment); cell(row, 'D', len(groups[apartment]))
        cell(row, 'E', net, f'{quoted(name)}!F{last+2}')
        cell(row, 'F', net*(1+vat), f'{quoted(name)}!F{total_row}')
        summary_rows.append(row); sheets.append((name, root, 1, 'F')); grand += net
    last = 16 + len(groups)
    row = clone(total_style, last+2); cell(row, 'B', 'TOTALE GENERALE')
    cell(row, 'D', len(lines), f'SUM(D17:D{last})')
    cell(row, 'E', grand, f'SUM(E17:E{last})'); cell(row, 'F', grand*(1+vat), f'SUM(F17:F{last})')
    summary_rows.append(row)
    row = clone(subtotal_style, last+3); cell(row, 'B', 'IVA complessiva')
    cell(row, 'F', grand*vat, f'F{last+2}-E{last+2}'); summary_rows.append(row)
    sheets.append(('Calcolo interno', internal, 2, 'J'))
    return package_workbook(original, sheets)


def package_workbook(original, sheets):
    # Clone both worksheet and drawing parts, so each apartment has its own
    # print area, header, logo relationship and independently editable cells.
    files = {k: v for k, v in original.items() if not k.startswith(('xl/worksheets/', 'xl/drawings/'))}
    book = ET.fromstring(files['xl/workbook.xml']); sheet_list = book.find(tag('sheets')); sheet_list.clear()
    names = book.find(tag('definedNames'))
    if names is not None:
        book.remove(names)
    names = ET.Element(tag('definedNames')); book.insert(list(book).index(sheet_list) + 1, names)
    calc = book.find(tag('calcPr'))
    if calc is None:
        calc = ET.SubElement(book, tag('calcPr'))
    calc.attrib.update(calcMode='auto', fullCalcOnLoad='1', forceFullCalc='1')
    relations = ET.fromstring(files['xl/_rels/workbook.xml.rels'])
    for rel in list(relations):
        if rel.get('Type', '').endswith('/worksheet'):
            relations.remove(rel)
    types = ET.fromstring(files['[Content_Types].xml'])
    for t in list(types):
        if t.get('PartName', '').startswith(('/xl/worksheets/', '/xl/drawings/')):
            types.remove(t)
    for i, (name, root, template, width) in enumerate(sheets, 1):
        last = max(int(r.get('r')) for r in root.find(tag('sheetData')))
        configure_print(root, last, width, width == 'J')
        ref = f'groupSheet{i}'
        ET.SubElement(sheet_list, tag('sheet'), {'name': name, 'sheetId': str(i), '{'+DOCREL+'}id': ref})
        ET.SubElement(relations, '{'+REL+'}Relationship', {'Id': ref, 'Type': DOCREL+'/worksheet', 'Target': f'/xl/worksheets/sheet{i}.xml'})
        for key, area in (('_xlnm.Print_Area', f'$A$1:${width}${last}'), ('_xlnm.Print_Titles', '$8:$8' if template == 2 else '$16:$16')):
            ET.SubElement(names, tag('definedName'), {'name': key, 'localSheetId': str(i-1)}).text = quoted(name) + '!' + area
        files[f'xl/worksheets/sheet{i}.xml'] = xml_bytes(root)
        parts = [(f'worksheets/sheet{i}.xml', 'spreadsheetml.worksheet')]
        rel_path = f'xl/worksheets/_rels/sheet{template}.xml.rels'
        if rel_path in original:
            rel = ET.fromstring(original[rel_path])
            for item in rel:
                if item.get('Type', '').endswith('/drawing'):
                    item.set('Target', f'/xl/drawings/drawing{i}.xml')
            files[f'xl/worksheets/_rels/sheet{i}.xml.rels'] = xml_bytes(rel)
            files[f'xl/drawings/drawing{i}.xml'] = original[f'xl/drawings/drawing{template}.xml']
            files[f'xl/drawings/_rels/drawing{i}.xml.rels'] = original[f'xl/drawings/_rels/drawing{template}.xml.rels']
            parts.append((f'drawings/drawing{i}.xml', 'drawing'))
        for path, content_type in parts:
            ET.SubElement(types, '{'+CT+'}Override', {'PartName': '/xl/'+path, 'ContentType': 'application/vnd.openxmlformats-officedocument.'+content_type+'+xml'})
    for path, root in (('xl/workbook.xml', book), ('xl/_rels/workbook.xml.rels', relations), ('[Content_Types].xml', types)):
        files[path] = xml_bytes(root)
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content)
    return output.getvalue()
