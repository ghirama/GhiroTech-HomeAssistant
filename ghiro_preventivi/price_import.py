"""Validated, atomic catalog imports. Never writes quote tables."""
import csv
import datetime
import hashlib
import io
import json
import pathlib
import re
import sqlite3
import uuid
from decimal import Decimal, InvalidOperation


def initialize_catalog(c):
    c.execute('''CREATE TABLE IF NOT EXISTS catalog_imports (
        id INTEGER PRIMARY KEY, source TEXT NOT NULL, edition TEXT NOT NULL,
        digest TEXT NOT NULL UNIQUE, created TEXT NOT NULL, rows_json TEXT NOT NULL)''')


def number(value):
    if isinstance(value, bool) or value is None:
        raise ValueError('Prezzo mancante o non valido')
    text = str(value).strip()
    if ',' in text:
        if not re.fullmatch(r'(?:\d+|\d{1,3}(?:\.\d{3})+),\d+', text):
            raise ValueError('Formato numerico ambiguo: ' + text)
        text = text.replace('.', '').replace(',', '.')
    elif not re.fullmatch(r'\d+(?:\.\d+)?', text):
        raise ValueError('Numero non valido: ' + text)
    try:
        n = Decimal(text)
    except InvalidOperation:
        raise ValueError('Numero non valido')
    if not n.is_finite() or n < 0 or n > Decimal('1000000000'):
        raise ValueError('Numero fuori intervallo')
    return float(n)


def validate(data):
    source = str(data.get('fonte', '')).strip().upper()
    edition = str(data.get('edizione', '')).strip()
    if not re.fullmatch(r'[A-Z0-9_-]{1,40}', source) or not edition or len(edition) > 80:
        raise ValueError('Indicare fonte (es. VIMAR, BTICINO, EPPAT) ed edizione')
    rows = data.get('voci')
    if 'csv' in data:
        text = data['csv'].lstrip('\ufeff')
        delimiter = data.get('separatore', ';')
        if delimiter not in (';', ',', '\t'):
            raise ValueError('Separatore non valido')
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter, strict=True)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError('Intestazioni mancanti o duplicate')
        if not {'codice', 'descrizione', 'unita', 'prezzo'} <= set(reader.fieldnames):
            raise ValueError('Colonne richieste: codice,descrizione,unita,prezzo')
        rows = []
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError('Numero colonne incoerente')
            if any(v.strip() for v in row.values()):
                rows.append(row)
            if len(rows) > 100000:
                raise ValueError('Troppe righe')
    if not isinstance(rows, list) or not rows or len(rows) > 100000:
        raise ValueError('Elenco voci non valido')
    clean, seen = [], set()
    for i, row in enumerate(rows, 2):
        try:
            if not isinstance(row, dict):
                raise ValueError('Voce non valida')
            code = str(row.get('codice', '')).strip()
            description = str(row.get('descrizione', '')).strip()
            unit = str(row.get('unita', '')).strip()
            if not code or ':' in code or len(code) > 100 or not description or not unit:
                raise ValueError('Codice, descrizione e unità obbligatori; codice senza due punti')
            if code in seen:
                raise ValueError('Codice duplicato: ' + code)
            seen.add(code)
            labour = number(row.get('manodopera') or 0)
            if labour > 100:
                raise ValueError('Manodopera deve essere una percentuale 0–100')
            clean.append((source + ':' + code, description, str(row.get('dettagli', '')),
                          unit, str(row.get('categoria', '')), number(row.get('prezzo')), labour))
        except ValueError as e:
            raise ValueError('Riga %s: %s' % (i, e))
    return source, edition, sorted(clean)


def import_catalog(c, data, backup_dir, preview=False):
    source, edition, rows = validate(data)
    content = json.dumps([source, edition, rows], ensure_ascii=False, separators=(',', ':'))
    digest = hashlib.sha256(content.encode()).hexdigest()
    existing = c.execute('SELECT id FROM catalog_imports WHERE digest=?', (digest,)).fetchone()
    updates = sum(c.execute('SELECT 1 FROM voci WHERE codice=?', (r[0],)).fetchone() is not None for r in rows)
    report = {'voci': len(rows), 'nuove': len(rows)-updates, 'aggiornate': updates,
              'gia_importato': bool(existing), 'impronta': digest,
              'campione': [dict(zip(('codice','descrizione','dettagli','unita','categoria','prezzo','manodopera'), r)) for r in rows[:5]]}
    if preview or existing:
        return dict(report, importate=0)
    # SQLite backup API captures a consistent snapshot, including any WAL content.
    folder = pathlib.Path(backup_dir)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / ('pre-import-' + uuid.uuid4().hex + '.sqlite')
    with sqlite3.connect(target) as backup:
        c.backup(backup)
    with c:
        c.executemany('''INSERT INTO voci(codice,descrizione,dettagli,unita,categoria,prezzo,manodopera)
            VALUES(?,?,?,?,?,?,?) ON CONFLICT(codice) DO UPDATE SET
            descrizione=excluded.descrizione,dettagli=excluded.dettagli,unita=excluded.unita,
            categoria=excluded.categoria,prezzo=excluded.prezzo,manodopera=excluded.manodopera''', rows)
        c.execute('INSERT INTO catalog_imports(source,edition,digest,created,rows_json) VALUES(?,?,?,?,?)',
                  (source, edition, digest, datetime.datetime.now(datetime.timezone.utc).isoformat(), content))
        c.execute('INSERT INTO listini(etichetta,caricato,numero_voci) VALUES(?,?,?)',
                  (source + ' — ' + edition, datetime.date.today().isoformat(), len(rows)))
    return dict(report, importate=len(rows))
