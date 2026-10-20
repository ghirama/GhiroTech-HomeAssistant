"""Extract numeric facts from `pdftotext -layout` of the 2025/26 catalogue.

Only explicit table columns are used, never selection matrices or illustrations.
The source PDF and commercial prices are deliberately not distributed.
Usage: python tools/extract_gewiss_catalog.py layout.txt output.json
"""
import json
import re
import sys
from pathlib import Path

RANGES = [(197,200,'40 CD'),(207,215,'40 CDe'),(219,222,'42 RV'),
          (275,281,'40 CDi'),(282,282,'40 CDe'),(283,284,'40 CDi'),(285,285,'48 PTC'),(286,289,'40 CDi'),(302,302,'48 PTC'),(423,437,'90 MCB'),
          (447,467,'90 RCD'),(478,520,'90 AM')]


def extract(contents):
    result = {}
    for page, body in enumerate(contents.split('\f'), 1):
        series = next((name for start,end,name in RANGES if start <= page <= end), None)
        if not series:
            continue
        columns = None
        for line in body.splitlines():
            if re.search(r'\bCodice\b', line):
                columns = None
                mod = re.search(r'N\. mod\.', line)
                if mod and 'Conf.' in line and len(re.findall(r'N\. mod\.', line)) == 1:
                    columns = (line.index('Codice'), mod.start(), line.find('Dim. esterne BxHxP'))
                continue
            if columns is None:
                continue
            code_col, mod_col, dim_col = columns
            # Image captions sit to the left of the Codice column. Suffixes are
            # part of the first cell, separated from the next column by 2 spaces.
            cell = re.split(r'\s{2,}', line[code_col:].strip(), 1)[0]
            if not re.fullmatch(r'GW\s+(?:\d\d|D\d)\s+\d{3}(?:\s+[A-Z0-9]+)?', cell):
                continue
            code = re.sub(r'\s+', '', cell)
            match = re.match(r'\s*(\d+(?:[.,]\d+)?)(\s*(?:\+\d+)?\s*(?:\(\d+\s*[xX]\s*\d+\))?)\s{2,}', line[max(0,mod_col-3):])
            if not match:
                continue
            value = float(match[1].replace(',', '.'))
            if not 0 < value <= 1440:
                continue
            item = {'moduli':value, 'serie':series, 'pagina':page}
            arrangement = re.search(r'\((\d+)\s*[xX]\s*(\d+)\)', match[2])
            if arrangement and int(arrangement[1])*int(arrangement[2]) == value:
                item.update(perFila=int(arrangement[1]), file=int(arrangement[2]))
            if '+' in match[2]:
                item['capacita_catalogo'] = (match[1]+match[2]).strip()
            if dim_col >= 0:
                dims = re.match(r'\s*(\d+)\s*[xX]\s*(\d+)\s*[xX]\s*(\d+)\b', line[max(0,dim_col-1):])
                if dims:
                    item.update(zip(('larghezza','altezza','profondita'),map(int,dims.groups())))
            # Conflicting facts must be reviewed, not silently overwritten.
            if code in result:
                old = {k:v for k,v in result[code].items() if k not in ('pagina','serie')}
                new = {k:v for k,v in item.items() if k not in ('pagina','serie')}
                if old != new:
                    raise ValueError(f'Conflicting facts for {code}: {result[code]} / {item}')
                result[code]['serie'] = ' / '.join(sorted(set(result[code]['serie'].split(' / ') + [series])))
            else:
                result[code] = item
    return {'fonte':'Gewiss — Catalogo commerciale 2025/2026', 'articoli':dict(sorted(result.items()))}

if __name__ == '__main__':
    data = extract(Path(sys.argv[1]).read_text())
    Path(sys.argv[2]).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    print(f"{len(data['articoli'])} articoli")
