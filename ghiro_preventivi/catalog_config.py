"""Reusable, user-verified product associations and bounded Excel ingestion."""
import base64
import hashlib
import io
import json
import zipfile
from decimal import Decimal
from price_import import number


def initialize(c):
    c.executescript('''CREATE TABLE IF NOT EXISTS catalog_associations (
      series TEXT NOT NULL, variant TEXT NOT NULL, component TEXT NOT NULL,
      products TEXT NOT NULL, PRIMARY KEY(series,variant,component));
    CREATE TABLE IF NOT EXISTS catalog_status (
      code TEXT PRIMARY KEY, edition TEXT NOT NULL, active INTEGER NOT NULL);''')


def read_excel(data):
    """Vimar METEL or a worksheet using the same headers as normalized CSV."""
    import openpyxl
    try:
        raw = base64.b64decode(data['xlsx'], validate=True)
        if len(raw) > 10 * 1024 * 1024:
            raise ValueError('Excel massimo 10 MB')
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            if len(z.infolist()) > 2000 or sum(i.file_size for i in z.infolist()) > 80 * 1024 * 1024:
                raise ValueError('Excel espanso troppo grande')
        w = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=False, keep_links=False)
    except Exception as e:
        raise ValueError('Excel non leggibile: ' + str(e)) from e
    try:
        sheet = w.worksheets[0]
        sheet.reset_dimensions()
        rows = sheet.iter_rows(max_col=32, values_only=True)
        headers = [str(v or '').strip() for v in next(rows,())]
        if len(headers)<11:
            raise ValueError('Foglio vuoto o intestazioni mancanti')
        metel = headers[1] == 'Codice Prodotto Azienda' and headers[10] == 'Prezzo al Pubblico'
        if metel and any(headers[i] != h for i,h in {0:'Sigla Marchio',3:'Descrizione prodotto',11:'Moltiplic. prezzo',12:'Codice valuta',13:'Unità misura',15:'SP'}.items()):
            raise ValueError('Colonne METEL diverse dal formato Vimar atteso')
        if metel and data.get('fonte', '').upper() != 'VIMAR':
            raise ValueError('Questo formato METEL richiede la fonte VIMAR')
        if not metel and (len([h for h in headers if h]) != len(set(h for h in headers if h)) or not {'codice','descrizione','unita','prezzo'} <= set(headers)):
            raise ValueError('Primo foglio: formato Vimar METEL oppure colonne codice, descrizione, unita, prezzo')
        items, inactive = [], []
        for n, row in enumerate(rows, 2):
            if n > 100001:
                raise ValueError('Massimo 100.000 righe')
            if all(v is None for v in row):
                continue
            if any(isinstance(v, str) and v.startswith('=') for v in row):
                raise ValueError('Riga %d: esportare le formule come valori prima di importare' % n)
            if metel:
                if row[0] != 'VIW' or row[12] != 'EUR' or row[13] not in ('PCE','LM'):
                    raise ValueError('Riga %d: marchio, valuta o unità non supportati' % n)
                if row[11] not in (1,10,100,1000,10000,100000) or row[15] not in (1,2,3,6,7,9):
                    raise ValueError('Riga %d: moltiplicatore o stato non valido' % n)
                if not isinstance(row[1], str):
                    raise ValueError('Riga %d: il codice deve essere testo per conservare gli zeri iniziali' % n)
                if row[15] == 9:
                    inactive.append(row[1])
                details = {'foglio':sheet.title, 'riga':n, 'stato_metel':row[15],
                           'prezzo_pubblico_originale':row[10], 'moltiplicatore':row[11]}
                items.append(dict(codice=row[1], descrizione=row[3], unita='cad' if row[13]=='PCE' else 'm',
                    prezzo=str(Decimal(str(number(row[10]))) / Decimal(str(row[11]))),
                    categoria='Vimar — ' + {1:'Nuovo',2:'In esaurimento',3:'A magazzino',6:'Su commessa',7:'In esaurimento',9:'Annullato'}[row[15]],
                    dettagli=json.dumps(details, ensure_ascii=False)))
            else:
                items.append({h:v for h,v in zip(headers,row) if h})
        return {k:v for k,v in data.items() if k != 'xlsx'} | {
            'voci':items, 'inattivi':inactive, 'sha256_originale':hashlib.sha256(raw).hexdigest()}
    finally:
        w.close()


def key(data):
    values = tuple(data.get(k, '') for k in ('serie','variante','componente'))
    if any(not isinstance(v,str) or not v.strip() or len(v)>180 for v in values):
        raise ValueError('Serie, variante e componente obbligatori (massimo 180 caratteri)')
    return tuple(v.strip() for v in values)


def product(c, code):
    c.row_factory = __import__('sqlite3').Row
    r = c.execute('''SELECT v.*, s.edition, s.active FROM voci v
        LEFT JOIN catalog_status s ON s.code=v.codice WHERE v.codice=?''', (code,)).fetchone()
    if not r or r['active'] == 0 or r['prezzo'] <= 0:
        raise ValueError('Articolo assente, annullato o senza prezzo: '+code)
    return dict(r)


def associations(c):
    return [dict(serie=r[0], variante=r[1], componente=r[2], articoli=json.loads(r[3]))
            for r in c.execute('SELECT * FROM catalog_associations ORDER BY series,variant,component')]


def save_association(c, data):
    identity = key(data)
    if data.get('elimina') is True:
        with c:
            c.execute('DELETE FROM catalog_associations WHERE series=? AND variant=? AND component=?', identity)
        return {'ok':True}
    rows = data.get('articoli')
    if not isinstance(rows,list) or not 1 <= len(rows) <= 20:
        raise ValueError('Associare da 1 a 20 articoli')
    clean, seen = [], set()
    for row in rows:
        code = row.get('codice')
        if not isinstance(code,str) or ':' not in code or code in seen:
            raise ValueError('Usa codici univoci completi di fonte, es. VIMAR:001')
        p = product(c,code)
        if p['unita'] != 'cad':
            raise ValueError('Per scatole e frutti associare articoli a pezzo (cad)')
        qty = number(row.get('quantita',1))
        if qty <= 0 or qty > 100 or not qty.is_integer():
            raise ValueError('Quantità intera da 1 a 100')
        seen.add(code); clean.append({'codice':code,'quantita':qty})
    with c:
        c.execute('INSERT INTO catalog_associations VALUES(?,?,?,?) ON CONFLICT(series,variant,component) DO UPDATE SET products=excluded.products', identity+(json.dumps(clean),))
    return {'ok':True}


def resolve(c, data):
    rows = data.get('righe')
    if not isinstance(rows,list) or len(rows)>5000:
        raise ValueError('Massimo 5.000 righe')
    result = []
    project_cache = {}
    for line in rows:
        try:
            association = line.get('associazione')
            if isinstance(association,str):
                association = json.loads(association or 'null')
            if association and association.get('profilo'):
                from catalog_auto import project_parts
                parts = project_parts(c,association,project_cache)
            elif association:
                ident = key(association)
                found = c.execute('SELECT products FROM catalog_associations WHERE series=? AND variant=? AND component=?',ident).fetchone()
                if not found:
                    raise ValueError('Associazione da completare: ' + ' / '.join(ident))
                parts = json.loads(found[0])
            else:
                code = line.get('codice','')
                if ':' not in code:
                    raise ValueError('Codice articolo da associare: '+code)
                parts = [{'codice':code,'quantita':1}]
            priced = []
            for part in parts:
                p = product(c,part['codice'])
                priced.append(dict(codice=p['codice'],descrizione=p['descrizione'],unita=p['unita'],
                    prezzo=p['prezzo'],quantita=part['quantita'],edizione=p['edition'] or '',categoria=p['categoria']))
            result.append({'articoli':priced})
        except ValueError as e:
            result.append({'errore':str(e)})
    return {'righe':result}
