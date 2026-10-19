"""Vimar technical recipes. Prices and availability always come from the user's list.
No fuzzy code matching: exact SKU families, colour suffixes and explicit components.
See CATALOG_SOURCES.md for scope, technical references and exclusions.
"""
import hashlib
import json
import re
import sqlite3

SERIES = {
 'Vimar Plana': {'prefix':'14','colours':{'Bianco':'','Silver':'.SL'},'plates':['1465']},
 'Vimar Arké': {'prefix':'19','colours':{'Bianco':'.B','Grigio':'','Metal':'.M'},'plates':['1965','1968','1995']},
 'Vimar Linea': {'prefix':'30','colours':{'Bianco':'.B','Canapa':'.C','Nero':'.G'},'plates':['3065']},
}
COMPONENTS = {
 'presa':('Presa 10/16 A',1,['203']),
 'schuko':('Presa Schuko',2,['208']),
 'interruttore':('Interruttore',1,['000','001','002','100']),
 'deviatore':('Deviatore',1,['004','005','006','104']),
 'pulsante':('Pulsante',1,['008','108']),
 'invertitore':('Invertitore',1,['013','113']),
 'dati':('Presa dati',1,['337.6','339.11','339.13','339.14','339.15','339.16']),
 'tv':('Presa TV',1,['300.01','300.10','313']),
 'tapparella':('Comando tapparella',1,['060','061','062']),
 'ronzatore':('Ronzatore',1,['370.SR','373.SR']),
 'campanello':('Campanello 3 moduli',3,[]),
 'campanello2':('Suoneria elettronica 2 moduli',2,['380']),
 'presenza1':('Sensore di presenza 1 modulo',1,['181']),
 'presenza2':('Sensore di presenza 2 moduli',2,[]),
 'termostato2':('Termostato 2 moduli',2,[]),
 'termostato3':('Termostato 3 moduli',3,[]),
 'cieco':('Tappo cieco',1,['041']),
}
LINEA = {'interruttore':['000','000A','020'],'deviatore':['004','004A','024'],
         'pulsante':['008','008A'],'invertitore':['012','012A'],
         'dati':['339.13','339.16'],'ronzatore':['370','373'],'campanello2':[]}
NOTES = {
 'campanello':'Nessuna suoneria da 3 moduli verificata. Per Plana/Arké è disponibile la suoneria elettronica da 2 moduli: modifica la composizione se adatta al progetto.',
 'presenza2':'Nessun sensore tradizionale da 2 moduli verificato. Non vengono sostituiti dispositivi da 1 modulo o sensori bus.',
 'termostato3':'Nessun termostato tradizionale da 3 moduli verificato nel profilo. Disponibili alternative da 2 moduli.',
}


def active_products(c):
 c.row_factory=sqlite3.Row
 return {r['codice'][6:]:dict(r) for r in c.execute("SELECT v.* FROM voci v LEFT JOIN catalog_status s ON s.code=v.codice WHERE v.codice LIKE 'VIMAR:%' AND v.unita='cad' AND v.prezzo>0 AND COALESCE(s.active,1)=1")}


def plate_families(products, series):
 spec=SERIES[series];result={}
 # Only linear 3/4/7 module plates; 6M (3+3) or (2+2+2) must never match SCAT-6.
 for code,p in products.items():
  m=re.fullmatch(r'(1465|1965|1968|1995|3065)([347])(U?)\.(.+)',code)
  if not m or m[1] not in spec['plates'] or (m[3] and series!='Vimar Plana'):continue
  desc=p['descrizione']
  if not re.match(r'^Placca\b',desc) or not re.search(r'\b'+m[2]+r'M\b',desc) or '(' in desc or ' BS ' in desc:continue
  family=m[1]+'{m}'+m[3]+'.'+m[4]
  name=re.sub(r'\b[347]M\b','',desc).replace('Placca ','').strip()
  result.setdefault(family,{'id':family,'nome':name,'moduli':[]})['moduli'].append(int(m[2]))
 return sorted(result.values(),key=lambda p:p['nome'].casefold())


def options(c):
 products=active_products(c)
 return {'serie':[{'nome':name,'colori':list(spec['colours']), 'placche':plate_families(products,name)} for name,spec in SERIES.items()],
         'articoli_attivi':len(products),
         'note':'Profili Vimar Plana, Arké e Linea per impianti tradizionali. Altri produttori richiedono i relativi listini e dati tecnici. Quadri, protezioni e derivazioni generiche richiedono la scelta del codice completo; non vengono dimensionati automaticamente.'}


def option(products, codes, label=None):
 if any(code not in products for code in codes):return None
 parts=[{'codice':'VIMAR:'+code,'quantita':1,'descrizione':products[code]['descrizione'],'prezzo':products[code]['prezzo']} for code in codes]
 return {'id':'+'.join(codes),'articoli':parts,'nome':label or ' + '.join(p['descrizione'] for p in parts),
         'prezzo':sum(p['prezzo'] for p in parts)}


def analyse(c, data):
 series=data.get('serie');colour=data.get('colore');plate=data.get('placca');mount=data.get('posa')
 if series not in SERIES or colour not in SERIES[series]['colours'] or mount not in ('Muratura','Cartongesso'):
  raise ValueError('Scegli serie, colore dei frutti e posa')
 products=active_products(c);plates=plate_families(products,series)
 selected=next((p for p in plates if p['id']==plate),None)
 if not selected:raise ValueError('Scegli una placca presente nel listino attivo della serie')
 spec=SERIES[series];prefix=spec['prefix'];suffix=spec['colours'][colour]
 variant='Auto · '+colour+' · '+selected['nome']+' ('+plate.replace('{m}','3')+') · '+mount
 existing={r[0] for r in c.execute('SELECT component FROM catalog_associations WHERE series=? AND variant=?',(series,variant))}
 rows=[]
 def row(component,name,choices,note=''):
  choices=[o for o in choices if o]
  rows.append({'componente':component,'nome':name,'opzioni':choices,'selezione':choices[0]['id'] if len(choices)==1 and component not in ('FR-ronzatore','FR-termostato2','FR-dati','FR-tv','FR-tapparella','FR-campanello2') else '',
               'esistente':component in existing,'nota':note or ('Scegli la caratteristica richiesta.' if len(choices)>1 else '' if choices else 'Articolo non disponibile nel listino attivo.')})
 for n in (3,4,6,7):
  choices=[];note=''
  if n==6:
   note='Le combinazioni Vimar verificate usano supporto e placca da 7 moduli su scatola 6/7. Non equivale alla composizione da 6: modifica la scatola se opportuno.'
  else:
   box=('V713' if mount=='Muratura' else 'V717')+('06' if n==7 else '0'+str(n))
   support=('1991' if plate.startswith('1995') else prefix+'61')+str(n)
   plate_code=plate.replace('{m}',str(n))
   choices=[option(products,[box,support,plate_code])]
  row('SCAT-'+str(n),'Scatola, supporto e placca '+str(n)+' moduli',choices,note)
 for component,(name,modules,stems) in COMPONENTS.items():
  stems=LINEA.get(component,stems) if series=='Vimar Linea' else stems
  codes=[]
  for stem in stems:
   ending=suffix[1:] if series=='Vimar Linea' and '.' in stem else suffix
   codes.append(prefix+stem+ending)
  if component=='termostato2':
   if series=='Vimar Linea':codes=['30440'+suffix]
   else:
    common={'Bianco':'.B','Grigio':'','Metal':'.M'}.get(colour)
    codes=(['02970'+common] if common is not None else [])
    if series=='Vimar Plana':codes.append('14440'+suffix)
  choices=[]
  for code in codes:
   p=products.get(code)
   if not p:continue
   d=p['descrizione'].lower()
   # Extra protection against a price list containing accessories or different sizes at these SKUs.
   if any(t in d for t in ('meccanismo','adattatore','domotico','knx','iot')):continue
   size=re.search(r'\b(\d+)m\b',d)
   if size and int(size[1])!=modules:continue
   # Colour is part of both SKU and description, no cross-colour fallback.
   if colour.casefold() not in d:continue
   choices.append(option(products,[code]))
  row('FR-'+component,name,choices,NOTES.get(component,''))
 # The fingerprint covers current options, prices and profile. Saving a stale analysis is rejected.
 content=json.dumps([series,variant,rows],sort_keys=True,ensure_ascii=False)
 return {'serie':series,'variante':variant,'righe':rows,'impronta':hashlib.sha256(content.encode()).hexdigest(),
         'automatiche':sum(bool(r['selezione']) and not r['esistente'] for r in rows),
         'da_scegliere':sum(bool(r['opzioni']) and not r['selezione'] and not r['esistente'] for r in rows),
         'mancanti':sum(not r['opzioni'] for r in rows)}


def save(c,data):
 chosen=data.get('scelte')
 if not isinstance(chosen,dict):raise ValueError('Scelte non valide')
 with c:
  c.execute('BEGIN IMMEDIATE')
  report=analyse(c,data)
  if report['impronta']!=data.get('impronta'):raise ValueError('Listino o associazioni modificati: ripeti Analizza abbinamenti')
  inserts=[]
  for row in report['righe']:
   if row['esistente']:continue  # Never replace a user's saved associations.
   pick=chosen.get(row['componente'],row['selezione'])
   if not pick:continue
   found=next((o for o in row['opzioni'] if o['id']==pick),None)
   if not found:raise ValueError('Scelta non disponibile: '+row['nome'])
   parts=[{'codice':p['codice'],'quantita':p['quantita']} for p in found['articoli']]
   inserts.append((report['serie'],report['variante'],row['componente'],json.dumps(parts)))
  if not inserts:raise ValueError('Nessuna nuova associazione da salvare')
  c.executemany('INSERT INTO catalog_associations VALUES(?,?,?,?)',inserts)
 return {'salvate':len(inserts),'variante':report['variante']}
