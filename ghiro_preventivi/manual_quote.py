"""Additive manual quote fields; old documents keep their original calculation."""
import math
FIELDS=('note','condizioni','validita','pagamenti','riferimento')
def numeric(value):
    n=float(value or 0)
    if not math.isfinite(n) or n<0 or n>1e12:raise ValueError('Valore numerico non valido')
    return n
def validate_line(row):
    if not isinstance(row,dict):raise ValueError('Voce non valida')
    for k in ('quantita','prezzo','quota_materiale','sconto','ricarico_voce'):
        n=numeric(row.get(k))
        if k in ('sconto','quota_materiale') and n>100:raise ValueError('Percentuale oltre 100%')
    if len(str(row.get('sezione','')))>200:raise ValueError('Sezione troppo lunga')
def details(data):
    result={k:str(data.get(k,'') or '') for k in FIELDS}
    if any(len(v)>10000 for v in result.values()):raise ValueError('Testo troppo lungo')
    return result
def adjusted_cost(row):
    validate_line(row)
    return numeric(row.get('prezzo'))*(1-numeric(row.get('sconto'))/100)*(1+numeric(row.get('ricarico_voce'))/100)
