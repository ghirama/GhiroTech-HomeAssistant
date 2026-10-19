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
    """Known METEL Excel layouts or normalized CSV-style worksheets."""
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
        normalized = [' '.join(h.casefold().split()) for h in headers]
        metel = 'codice prodotto azienda' in normalized
        positions = {}
        if metel:
            aliases = {'brand':('sigla marchio',), 'code':('codice prodotto azienda',),
                'description':('descrizione prodotto',), 'price':('prezzo al pubblico',),
                'multiplier':('moltiplic. prezzo','moltiplicatore prezzo'),
                'currency':('codice valuta',), 'unit':('unità misura','unità di misura'),
                'status':('sp','stato del prodotto')}
            for field,names in aliases.items():
                matches=[i for i,h in enumerate(normalized) if h in names]
                if len(matches)!=1:
                    raise ValueError('Colonna METEL mancante o duplicata: '+names[0])
                positions[field]=matches[0]
        elif len([h for h in headers if h]) != len(set(h for h in headers if h)) or not {'codice','descrizione','unita','prezzo'} <= set(headers):
            raise ValueError('Primo foglio: Excel METEL oppure colonne codice, descrizione, unita, prezzo')
        source=str(data.get('fonte','')).strip().upper()
        brands={'VIW':('VIMAR','Vimar'),'GEW':('GEWISS','Gewiss')}
        items, inactive = [], []
        for n, row in enumerate(rows, 2):
            if n > 100001:
                raise ValueError('Massimo 100.000 righe')
            if all(v is None for v in row):
                continue
            if any(isinstance(v, str) and v.startswith('=') for v in row):
                raise ValueError('Riga %d: esportare le formule come valori prima di importare' % n)
            if metel:
                values={k:row[i] for k,i in positions.items()}
                brand=str(values['brand'] or '').strip().upper()
                if brand not in brands:
                    raise ValueError('Riga %d: marchio METEL %s non ancora supportato; occorre verificare il relativo listino' % (n,brand))
                expected,label=brands[brand]
                if source!=expected:
                    raise ValueError('Il file contiene marchio %s (%s), ma la fonte scelta è %s. Seleziona %s e ripeti la verifica.' % (brand,label,source or 'vuota',expected))
                currency=str(values['currency'] or '').strip().upper()
                unit=str(values['unit'] or '').strip().upper()
                if currency!='EUR' or unit not in ('PCE','LM'):
                    raise ValueError('Riga %d: valuta o unità non supportate' % n)
                multiplier=number(values['multiplier']);status=number(values['status'])
                if multiplier not in (1,10,100,1000,10000,100000) or status not in (1,2,3,6,7,9):
                    raise ValueError('Riga %d: moltiplicatore o stato non valido' % n)
                multiplier=int(multiplier);status=int(status);code=values['code']
                if not isinstance(code,str):
                    raise ValueError('Riga %d: il codice deve essere testo per conservare gli zeri iniziali' % n)
                code=code.strip()
                if status==9:inactive.append(code)
                details={'foglio':sheet.title,'riga':n,'stato_metel':status,
                         'prezzo_pubblico_originale':values['price'],'moltiplicatore':multiplier}
                items.append(dict(codice=code,descrizione=values['description'],unita='cad' if unit=='PCE' else 'm',
                    prezzo=str(Decimal(str(number(values['price']))) / Decimal(str(multiplier))),
                    categoria=label+' — '+{1:'Nuovo',2:'In esaurimento',3:'A magazzino',6:'Su commessa',7:'In esaurimento',9:'Annullato'}[status],
                    dettagli=json.dumps(details,ensure_ascii=False)))
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
