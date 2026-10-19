"""Reusable panels and explicit selection from the imported Gewiss list."""
import json
import re
import sqlite3


def initialize(c):
    c.execute('CREATE TABLE IF NOT EXISTS quadri_preimpostati(id INTEGER PRIMARY KEY,nome TEXT NOT NULL UNIQUE COLLATE NOCASE,quadro_json TEXT NOT NULL)')


def integer(value, maximum):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError('Dimensioni o posizioni del quadro non valide')
    return value


def text(value, maximum=5000):
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError('Testo del modello non valido')
    return value.strip()


def normalize(p):
    if not isinstance(p, dict):
        raise ValueError('Quadro non valido')
    out = {k: text(p.get(k, '')) for k in ('nome', 'note', 'codice', 'articolo')}
    out.update(file=integer(p.get('file'), 20), perFila=integer(p.get('perFila'), 72))
    for k in ('larghezza', 'altezza', 'profondita'):
        out[k] = '' if p.get(k, '') == '' else integer(p[k], 10000)
    components = p.get('componenti')
    if not isinstance(components, list) or len(components) > 1440:
        raise ValueError('Componenti del quadro non validi')
    occupied = set()
    out['componenti'] = []
    for item in components:
        if not isinstance(item, dict):
            raise ValueError('Componente non valido')
        comp = {k: text(item.get(k, '')) for k in ('tipo', 'descrizione', 'codice', 'articolo')}
        comp.update(fila=integer(item.get('fila'), out['file']), posizione=integer(item.get('posizione'), out['perFila']), moduli=integer(item.get('moduli'), 72))
        if comp['posizione'] + comp['moduli'] - 1 > out['perFila']:
            raise ValueError('Un componente supera la capienza della fila')
        cells = {(comp['fila'], n) for n in range(comp['posizione'], comp['posizione'] + comp['moduli'])}
        if occupied & cells:
            raise ValueError('I componenti del quadro si sovrappongono')
        occupied |= cells
        out['componenti'].append(comp)
    return out


def models(c):
    return [dict(row) for row in c.execute('SELECT * FROM quadri_preimpostati ORDER BY id DESC')]


def mutate(c, action, data):
    if not isinstance(data, dict):
        raise ValueError('Richiesta non valida')
    ident = int(data.get('id') or 0)
    if action in ('rinomina', 'elimina') and not c.execute('SELECT 1 FROM quadri_preimpostati WHERE id=?', (ident,)).fetchone():
        raise ValueError('Modello non trovato')
    if action == 'elimina':
        c.execute('DELETE FROM quadri_preimpostati WHERE id=?', (ident,))
    else:
        name = text(data.get('nome', ''), 100)
        if not name:
            raise ValueError('Inserisci il nome del modello')
        try:
            if action == 'rinomina':
                c.execute('UPDATE quadri_preimpostati SET nome=? WHERE id=?', (name, ident))
            elif action == 'salva':
                panel = normalize(data.get('quadro'))
                ident = c.execute('INSERT INTO quadri_preimpostati(nome,quadro_json) VALUES(?,?)', (name, json.dumps(panel, ensure_ascii=False))).lastrowid
            else:
                raise ValueError('Operazione non valida')
        except sqlite3.IntegrityError:
            raise ValueError('Nome già presente: scegli un altro nome') from None
    c.commit()
    return {'ok': True, 'id': ident}


def specs(description):
    s = description.upper()
    width = re.search(r'(?<!\w)(?<!\d[.,])(\d+(?:[.,]\d+)?)\s*M(?:ODULI)?\b', s)
    modules = float(width[1].replace(',', '.')) if width else None
    arrangement = re.search(r'\(\s*(\d+)\s*[X×]\s*(\d+)\s*\)', s)
    result = {'moduli': modules}
    if arrangement and modules == int(arrangement[1]) * int(arrangement[2]):
        result.update(perFila=int(arrangement[1]), file=int(arrangement[2]))
    return result


def search(c, query):
    q = str(query.get('q', [''])[0]).strip()[:200]
    container = query.get('tipo', [''])[0] == 'contenitore'
    sql = "SELECT v.codice,v.descrizione,v.prezzo,v.unita FROM voci v WHERE v.codice LIKE 'GEWISS:%' AND v.prezzo>0 AND lower(v.unita)='cad' AND NOT EXISTS(SELECT 1 FROM catalog_status s WHERE s.code=v.codice AND s.active=0)"
    args = []
    for token in q.split():
        sql += " AND (v.codice LIKE ? ESCAPE '\\' OR v.descrizione LIKE ? ESCAPE '\\')"
        pattern = '%' + token.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        args.extend((pattern, pattern))
    rows = []
    for row in c.execute(sql + ' ORDER BY v.codice', args):
        item = dict(row)
        item.update(specs(item['descrizione']))
        if container and (not re.match(r'^(CENTRALINO|QUADRO)\b', item['descrizione'], re.I) or item['moduli'] is None):
            continue
        rows.append(item)
        if len(rows) == 100:
            break
    return rows
