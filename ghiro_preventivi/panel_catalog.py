"""Reusable panels and explicit selection from the imported Gewiss list."""
import json
import re
import sqlite3
from functools import lru_cache
from pathlib import Path


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
    widths = re.findall(r'(?<!\w)(?<!\d[.,])(\d+(?:[.,]\d+)?)\s*M(?:ODULI)?\b', s)
    modules = float(widths[-1].replace(',', '.')) if widths else None
    arrangement = re.search(r'\(\s*(\d+)\s*[X×]\s*(\d+)\s*\)', s)
    result = {'moduli': modules}
    if arrangement and modules == int(arrangement[1]) * int(arrangement[2]):
        result.update(perFila=int(arrangement[1]), file=int(arrangement[2]))
    return result


def search(c, query):
    if query.get('guidata', [''])[0] == '1':
        return guided_search(c, query)
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


# Catalogue metadata has no prices: every result is joined to the current list.

FACETS = ('categoria', 'serie', 'montaggio', 'ip', 'moduli', 'poli',
          'corrente', 'curva', 'potere', 'differenziale', 'sensibilita')


@lru_cache(maxsize=1)
def catalogue():
    return json.loads(Path(__file__).with_name('gewiss_catalog.json').read_text())


def characteristics(description):
    """Read explicit METEL attributes; never choose an electrical rating."""
    s = description.upper().replace('È', 'E').replace('É', 'E')
    compact = re.sub(r'\s+', '', s)
    kind = 'Altro'
    if re.match(r'^(CENTRALINO|QUADRO)\b', s):
        kind = 'Contenitore'
    elif 'AFDD' in s or 'BLOCCO' in s or 'COMPONIB' in s:
        pass  # A separate block/AFDD is not an ordinary MCB or complete RCD.
    elif re.match(r'INT\.?MAG\.?DIF', compact):
        kind = 'Magnetotermico differenziale'
    elif re.match(r'INT\.?MAGNET', compact):
        kind = 'Magnetotermico'
    elif re.match(r'INT\.?DIFF\.?PURO', compact):
        kind = 'Differenziale'
    elif 'SEZIONATORE' in s:
        kind = 'Sezionatore'
    elif 'SCARICATORE' in s:
        kind = 'Scaricatore di sovratensione'
    elif compact.startswith('CONTATTORE'):
        kind = 'Contattore'
    elif compact.startswith(('RELE', 'RELÈ')):
        kind = 'Relè'
    elif compact.startswith('TEMPORIZZATORE'):
        kind = 'Temporizzatore'
    elif compact.startswith('ALIMENTATORE'):
        kind = 'Alimentatore'
    elif compact.startswith('MORSETTIERA'):
        kind = 'Morsettiera'
    elif compact.startswith(('COPRIFORO', 'COPRIMODUL')):
        kind = 'Copriforo'
    out = {'categoria':kind}
    if kind == 'Contenitore':
        mount = 'Incasso' if re.search(r'\bINC\.|INCASSO', s) else 'Parete' if re.search(r'\bPAR\.|PARETE', s) else None
        if mount:
            out['montaggio'] = mount
        ip = re.search(r'\bIP\s*(\d{2})\b', s)
        if ip:
            out['ip'] = 'IP'+ip[1]
    if kind in ('Magnetotermico', 'Magnetotermico differenziale', 'Differenziale', 'Sezionatore'):
        poles = re.search(r'(?<!\d)([1-4]P(?:\+N)?)', compact)
        if poles:
            out['poli'] = poles[1]
        curve = re.search(r'(?<![A-Z])([BCD])\s*(\d+(?:[.,]\d+)?)', s)
        if kind.startswith('Magnetotermico') and curve:
            out.update(curva=curve[1], corrente=float(curve[2].replace(',', '.')))
        elif kind in ('Differenziale', 'Sezionatore'):
            amps = re.search(r'(?:P(?:\+N)?)[. ]*(\d+(?:[.,]\d+)?)A', compact)
            if amps:
                out['corrente'] = float(amps[1].replace(',', '.'))
        if kind.startswith('Magnetotermico'):
            ka = re.search(r'(?<![\d.,])(\d+(?:[.,]\d+)?)\s*KA', s)
            if ka:
                out['potere'] = float(ka[1].replace(',', '.'))
        if kind in ('Differenziale', 'Magnetotermico differenziale'):
            diff = re.search(r'(?<![A-Z])(AC|A(?:\[?IR\]?)?|F|B\+?)/(\d+(?:[.,]\d+)?)', s)
            if diff:
                out.update(differenziale=diff[1], sensibilita=round(float(diff[2].replace(',', '.'))*1000, 3))
    return out


def enriched(item):
    item = dict(item)
    item.update(specs(item['descrizione']))
    item.update(characteristics(item['descrizione']))
    fact = catalogue()['articoli'].get(item['codice'].removeprefix('GEWISS:'))
    if fact:
        # Both references describe the same SKU. A disagreement is exposed,
        # never resolved by silently applying an unverified footprint.
        if item['moduli'] is not None and item['moduli'] != fact['moduli']:
            item['avviso'] = 'Ingombro discordante tra listino e catalogo: verifica la scheda tecnica.'
            item['moduli'] = None
        else:
            item.update(fact)
            item['fonte'] = catalogue()['fonte']
    return item


def guided_search(c, query):
    """Facets are computed before pagination; legacy search retains its API."""
    container = query.get('tipo', [''])[0] == 'contenitore'
    q = str(query.get('q', [''])[0]).upper().strip()[:200]
    filters = {key:str(query.get(key, [''])[0])[:100] for key in FACETS}
    sql = "SELECT v.codice,v.descrizione,v.prezzo,v.unita FROM voci v WHERE v.codice LIKE 'GEWISS:%' AND v.prezzo>0 AND lower(v.unita)='cad' AND NOT EXISTS(SELECT 1 FROM catalog_status s WHERE s.code=v.codice AND s.active=0) ORDER BY v.codice"
    pool = []
    for row in c.execute(sql):
        item = enriched(row)
        if container:
            if item['categoria'] != 'Contenitore' or item['moduli'] is None:
                continue
        elif item['categoria'] == 'Contenitore':
            continue
        haystack = item['codice']+' '+item['descrizione'].upper()
        if all(token in haystack for token in q.split()):
            pool.append(item)

    def formatted(value):
        return format(value, 'g') if isinstance(value, (int,float)) else str(value)

    def matches(item, exclude=None):
        return all(not value or key == exclude or formatted(item.get(key,'')) == value for key,value in filters.items())

    facets = {key:sorted({formatted(item[key]) for item in pool if key in item and item[key] is not None and matches(item,key)}, key=lambda x:(0,float(x)) if re.fullmatch(r'\d+(?:\.\d+)?',x) else (1,x)) for key in FACETS}
    found = [item for item in pool if matches(item)]
    return {'articoli':found[:100], 'totale':len(found), 'filtri':facets}
