"""Read supplied EPPAT/METEL Excel; write auditable import packages, never live DB.
Requires openpyxl in the workstation environment (not in the add-on).
"""
import argparse
import csv
import datetime
import hashlib
import io
import json
import pathlib
import sys
from collections import Counter, defaultdict
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ghiro_preventivi'))
from price_import import validate

STATES = {1: 'Nuovo', 2: 'In esaurimento', 3: 'A magazzino', 6: 'Su commessa',
          7: 'Su commessa in esaurimento', 9: 'Annullato'}
FIELDS = ['codice', 'descrizione', 'dettagli', 'unita', 'categoria', 'prezzo', 'manodopera']


def text(value):
    if value is None:
        return ''
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def metel_rows(rows, headers, edition, source):
    catalogs, rejected = defaultdict(list), []
    seen = set()
    stats = Counter()
    for rownum, r in rows:
        brand, code = text(r[0]), text(r[1])
        if source == 'VIMAR' and brand != 'VIW':
            raise ValueError('Marchio Vimar non riconosciuto: ' + brand)
        if not brand:
            raise ValueError('Marchio mancante alla riga ' + str(rownum))
        key = (brand, code, text(r[12]))
        # Include the brand in the namespace; article codes alone are not unique.
        namespace = 'VIMAR' if source == 'VIMAR' and brand == 'VIW' else 'BTICINO_' + brand
        reason = None
        if key in seen:
            raise ValueError('Duplicate METEL key at row %s: %s' % (rownum, key))
        seen.add(key)
        if text(r[12]) != 'EUR':
            reason = 'Valuta diversa da EUR'
        elif r[11] not in (1, 10, 100, 1000, 10000, 100000):
            reason = 'Moltiplicatore non valido'
        elif r[15] not in STATES:
            reason = 'Stato prodotto non riconosciuto'
        elif r[15] == 9:
            reason = 'Prodotto annullato (stato METEL 9)'
        elif text(r[13]) not in ('PCE', 'LM'):
            reason = 'Unità da verificare'
        elif not code or not text(r[3]) or not isinstance(r[10], (int, float)) or r[10] <= 0:
            reason = 'Codice, descrizione o prezzo non utilizzabile'
        if reason:
            rejected.append({'fonte': namespace, 'riga': rownum, 'codice': code,
                             'motivo': reason, 'originale': dict(zip(headers, map(text, r)))})
            continue
        price = Decimal(str(r[10])) / Decimal(str(r[11]))
        stats['moltiplicatore_' + text(r[11])] += 1
        details = {'file': source, 'foglio': 'LISTINO' if source != 'VIMAR' else 'VIWLSP021',
                   'riga': rownum, 'stato': STATES[r[15]], 'tipo_prezzo': 'pubblico',
                   'prezzo_originale': text(r[10]), 'moltiplicatore': r[11],
                   'originale': dict(zip(headers, map(text, r)))}
        catalogs[namespace].append(dict(codice=code, descrizione=text(r[3]),
            unita='cad' if r[13] == 'PCE' else 'm', prezzo=format(price, 'f'),
            manodopera='0', categoria=brand + ' — ' + STATES[r[15]],
            dettagli=json.dumps(details, ensure_ascii=False, separators=(',', ':'))))
    return catalogs, rejected, dict(stats)


def eppat_rows(rows):
    records = {text(r[0]): r for _, r in rows if r[0]}
    catalogs, rejected, stats = defaultdict(list), [], Counter()
    seen = {}
    row_numbers = defaultdict(list)
    for rownum, r in rows:
        row_numbers[text(r[0])].append(rownum)
    for rownum, r in rows:
        if not isinstance(r[5], (int, float)):
            stats['intestazioni_o_righe_senza_prezzo'] += 1
            continue
        code = text(r[0])
        if code in seen:
            if seen[code] != r:
                raise ValueError('Conflicting EPPAT duplicate: ' + code)
            stats['duplicati_identici_unificati'] += 1
            continue
        seen[code] = r
        ancestors = [records.get('.'.join(code.split('.')[:i])) for i in range(1, len(code.split('.')))]
        ancestors = [a for a in ancestors if a]
        description = text(r[1]) or text(r[2]) or next((text(a[1]) for a in reversed(ancestors) if a[1]), '')
        reason = 'Prezzo zero: richiede analisi o verifica' if r[5] == 0 else None
        if not code or not description or not text(r[3]):
            reason = reason or 'Codice, descrizione o unità mancante'
        if r[5] < 0:
            reason = 'Prezzo negativo'
        if reason:
            rejected.append({'fonte': 'EPPAT', 'riga': rownum, 'codice': code,
                             'motivo': reason, 'originale': list(map(text, r))})
            continue
        # Parent descriptions are part of EPPAT's definition of the priced variant.
        context = '\n'.join(dict.fromkeys(text(a[2]) or text(a[1]) for a in ancestors))
        details = json.dumps({'foglio': '2026', 'riga': rownum, 'righe_originali': row_numbers[code], 'contesto': context,
                             'descrizione_estesa': text(r[2]), 'originale': list(map(text, r))},
                            ensure_ascii=False, separators=(',', ':'))
        catalogs['EPPAT'].append(dict(codice=code, descrizione=description, unita=text(r[3]),
                categoria=text(r[4]), prezzo=text(r[5]), manodopera=text(r[6]), dettagli=details))
        stats['descrizioni_da_contesto'] += int(not r[1] and not r[2])
    return catalogs, rejected, dict(stats)


def prepare(input_path, source, edition, output):
    import openpyxl
    p = pathlib.Path(input_path)
    checksum = hashlib.sha256(p.read_bytes()).hexdigest()
    w = openpyxl.load_workbook(p, read_only=True, data_only=True)
    try:
        sheet = w.worksheets[0]
        sheet.reset_dimensions()  # EPPAT declares 1,048,576 rows, mostly formatting.
        width = 10 if source == 'EPPAT' else 23
        rows = [(i, r) for i, r in enumerate(sheet.iter_rows(max_col=width, values_only=True), 1) if any(v is not None for v in r)]
        if source == 'EPPAT':
            if text(rows[1][1][0]).replace('\n', ' ').strip() != 'CODICE  PRODOTTO':
                raise ValueError('Unexpected EPPAT headers')
            catalogs, rejected, stats = eppat_rows(rows[2:])
        else:
            headers = [text(v) for v in rows[0][1]]
            if headers[1] != 'Codice Prodotto Azienda' or headers[10] != 'Prezzo al Pubblico':
                raise ValueError('Unexpected METEL headers')
            catalogs, rejected, stats = metel_rows(rows[1:], headers, edition, source)
        folder = pathlib.Path(output)
        folder.mkdir(parents=True, exist_ok=True)
        packages = []
        for namespace, items in sorted(catalogs.items()):
            items.sort(key=lambda v: v['codice'])
            # Bounded packages fit the app's upload limits, retaining full context.
            chunks, chunk, size = [], [], 0
            for item in items:
                n = len(json.dumps(item, ensure_ascii=False).encode())
                if chunk and (len(chunk) >= 3000 or size + n > 4000000):
                    chunks.append(chunk); chunk, size = [], 0
                chunk.append(item); size += n
            if chunk:
                chunks.append(chunk)
            for part, chunk in enumerate(chunks, 1):
                name = '%s_%02d' % (namespace, part)
                payload = {'fonte': namespace, 'edizione': edition, 'originale': p.name,
                           'sha256_originale': checksum, 'voci': chunk}
                validate(payload)
                data = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
                (folder / (name + '.json')).write_text(data, encoding='utf-8')
                buf = io.StringIO(newline='')
                writer = csv.DictWriter(buf, fieldnames=FIELDS, delimiter=';')
                writer.writeheader(); writer.writerows(chunk)
                (folder / (name + '.csv')).write_text('\ufeff' + buf.getvalue(), encoding='utf-8')
                packages.append({'fonte': namespace, 'edizione': edition, 'file': name + '.json',
                                 'voci': len(chunk), 'sha256': hashlib.sha256(data.encode()).hexdigest()})
        (folder / (source + '_da_verificare.json')).write_text(json.dumps(rejected, ensure_ascii=False, indent=2), encoding='utf-8')
        report = {'originale': p.name, 'sha256_originale': checksum, 'edizione': edition,
                  'righe_dati': len(rows) - (2 if source == 'EPPAT' else 1),
                  'voci_importabili': sum(map(len, catalogs.values())),
                  'per_fonte': {k: len(v) for k, v in catalogs.items()},
                  'righe_da_verificare': len(rejected), 'motivi': dict(Counter(r['motivo'] for r in rejected)),
                  'statistiche': stats, 'pacchetti': packages}
        (folder / (source + '_riepilogo.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        return report
    finally:
        w.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input')
    parser.add_argument('--source', choices=['EPPAT', 'VIMAR', 'BTICINO'], required=True)
    parser.add_argument('--edition', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report = prepare(args.input, args.source, args.edition, args.output)
    print(json.dumps({k: v for k, v in report.items() if k != 'pacchetti'}, ensure_ascii=False))
