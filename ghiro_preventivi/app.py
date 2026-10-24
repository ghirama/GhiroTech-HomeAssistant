import sqlite3,json,pathlib,shutil,os,uuid,datetime,html,cgi,io,csv,secrets,hashlib,hmac,time
from price_import import initialize_catalog, import_catalog
import catalog_config
import catalog_auto
import panel_catalog
from storage import activate as activate_storage, configure as configure_storage, read_state as storage_state
from pdf_plan import import_pdf, preview as pdf_preview, directory as pdf_directory
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from threading import Thread
import base64
from urllib.parse import urlparse,parse_qs
BASE=pathlib.Path(__file__).parent
CONTROL=pathlib.Path('/data') if pathlib.Path('/data').is_dir() else BASE
DATA=activate_storage(CONTROL)
DB=DATA/'prezzario.sqlite'
if not DB.exists():shutil.copy2(BASE/'prezzario.sqlite',DB)
DOCS=DATA/'documenti';DOCS.mkdir(exist_ok=True)
PLANS=DATA/'planimetrie'
def conn():
 c=sqlite3.connect(DB.resolve().as_uri()+'?mode=rw',uri=True);c.row_factory=sqlite3.Row;return c
def init():
 c=conn()
 c.executescript('''CREATE TABLE IF NOT EXISTS clienti(id INTEGER PRIMARY KEY,nome TEXT NOT NULL,telefono TEXT DEFAULT '',email TEXT DEFAULT '',indirizzo TEXT DEFAULT '',note TEXT DEFAULT '');
 CREATE TABLE IF NOT EXISTS lavori(id INTEGER PRIMARY KEY,cliente_id INTEGER,titolo TEXT,tipo TEXT,stato TEXT DEFAULT 'Da iniziare',note TEXT DEFAULT '');
 CREATE TABLE IF NOT EXISTS pratiche(id INTEGER PRIMARY KEY,cliente_id INTEGER,lavoro_id INTEGER,titolo TEXT,stato TEXT DEFAULT 'Da preparare',scadenza TEXT DEFAULT '',note TEXT DEFAULT '');
 CREATE TABLE IF NOT EXISTS documenti(id INTEGER PRIMARY KEY,cliente_id INTEGER,nome TEXT,path TEXT,caricato TEXT);
 CREATE TABLE IF NOT EXISTS configurazioni_civili(id INTEGER PRIMARY KEY,cliente_id INTEGER,titolo TEXT,stanze_json TEXT,aggiornato TEXT);
 CREATE TABLE IF NOT EXISTS scatole_preimpostate(id INTEGER PRIMARY KEY,nome TEXT NOT NULL UNIQUE COLLATE NOCASE,serie TEXT NOT NULL,scatola_json TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS listini(id INTEGER PRIMARY KEY,etichetta TEXT,caricato TEXT,numero_voci INTEGER);
 CREATE TABLE IF NOT EXISTS impianti_fv(id INTEGER PRIMARY KEY,cliente_id INTEGER,titolo TEXT,pannelli INTEGER DEFAULT 0,watt_pannello REAL DEFAULT 0,inverter_kw REAL DEFAULT 0,batteria_kwh REAL DEFAULT 0,orientamento TEXT DEFAULT '',inclinazione REAL DEFAULT 0,materiali_json TEXT DEFAULT '[]',note TEXT DEFAULT '',aggiornato TEXT);
 CREATE TABLE IF NOT EXISTS checklist_pratiche(id INTEGER PRIMARY KEY,lavoro_id INTEGER,cliente_id INTEGER,tipo TEXT,titolo TEXT,stato TEXT DEFAULT 'Da preparare',scadenza TEXT DEFAULT '',responsabile TEXT DEFAULT '',note TEXT DEFAULT '',creata TEXT);
 CREATE TABLE IF NOT EXISTS checklist_voci(id INTEGER PRIMARY KEY,pratica_id INTEGER,titolo TEXT,completata INTEGER DEFAULT 0);
 CREATE TABLE IF NOT EXISTS admin_login(id INTEGER PRIMARY KEY CHECK(id=1),username TEXT NOT NULL,password_hash TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS auth_sessions(token_hash TEXT PRIMARY KEY,expires INTEGER NOT NULL);
 ''')
 for tab,col,typ in [('preventivi','cliente_id','INTEGER'),('preventivi','sconto_materiale','REAL DEFAULT 0'),('righe','quota_materiale','REAL DEFAULT 0'),('righe','appartamento',"TEXT DEFAULT ''"),('righe','associazione',"TEXT DEFAULT ''"),('righe','stanza','TEXT DEFAULT NULL'),('righe','gruppo_cliente','TEXT DEFAULT NULL'),('configurazioni_civili','materiali_json',"TEXT DEFAULT 'null'"),('configurazioni_civili','descrizione',"TEXT DEFAULT ''"),('configurazioni_civili','appartamenti_json',"TEXT DEFAULT '[]'")]:
  if col not in [x[1] for x in c.execute('PRAGMA table_info('+tab+')')]:c.execute('ALTER TABLE '+tab+' ADD COLUMN '+col+' '+typ)
 c.execute("UPDATE scatole_preimpostate SET serie='' WHERE serie<>''")
 initialize_catalog(c)
 catalog_config.initialize(c)
 panel_catalog.initialize(c)
 c.commit();c.close()
init()
class H(BaseHTTPRequestHandler):
 def ingress_allowed(self):
  # Trust the TCP peer, never a client-supplied forwarding header.
  return self.client_address[0]=='172.30.32.2'
 def same_origin(self):
  origin=self.headers.get('Origin','')
  host=self.headers.get('Host','')
  if not origin:return True
  from urllib.parse import urlsplit
  u=urlsplit(origin)
  return u.scheme in ('http','https') and u.netloc.lower()==host.lower() and not u.username and not u.password and not u.path and not u.query and not u.fragment

 def send(self,obj,status=200):
  b=json.dumps(obj,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def body(self):return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
 def do_GET(self):
  if not self.ingress_allowed():return self.send({'errore':'Apri il gestionale da Home Assistant'},403)
  u=urlparse(self.path);path=u.path.rstrip('/');c=conn()
  try:
   if path.startswith('/api/auth/'):return self.send({'errore':'non trovato'},404)
   if path=='/editor':
    b=(BASE/'editor.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
   if path=='/logo.jpg':
    b=(BASE/'logo.jpg').read_bytes();self.send_response(200);self.send_header('Content-Type','image/jpeg');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
   if path in ('/manifest.webmanifest','/icon.svg'):
    name='manifest.webmanifest' if path.endswith('webmanifest') else 'icon.svg';b=(BASE/name).read_bytes();self.send_response(200);self.send_header('Content-Type','application/manifest+json' if name.endswith('webmanifest') else 'image/svg+xml');self.send_header('Cache-Control','public, max-age=3600');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
   if path in ('','/'):b=(BASE/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(b);return
   if path.startswith('/api/planimetrie/'):
    parts=path.split('/')
    if len(parts)==6 and parts[4]=='pagina':
     meta=pdf_preview(PLANS,parts[3],int(parts[5]));file=pdf_directory(PLANS,parts[3])/('pagina-%d.jpg'%meta['pagina']);content_type='image/jpeg'
    elif len(parts)==5 and parts[4]=='originale':
     file=pdf_directory(PLANS,parts[3])/'originale.pdf';content_type='application/pdf'
    else:return self.send({'errore':'non trovato'},404)
    b=file.read_bytes();self.send_response(200);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','private, max-age=86400');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(b);return
   if path=='/api/fotovoltaico':self.send([dict(x) for x in c.execute('SELECT * FROM impianti_fv ORDER BY id DESC')]);return
   if path=='/api/checklist':self.send([dict(x) for x in c.execute('SELECT * FROM checklist_pratiche ORDER BY id DESC')]);return
   if path.startswith('/api/checklist-voci/'):
    pid=int(path.split('/')[-1]);self.send([dict(x) for x in c.execute('SELECT * FROM checklist_voci WHERE pratica_id=? ORDER BY id',(pid,))]);return
   if path=='/api/impostazioni/archivio':self.send(storage_state(CONTROL));return
   if path=='/api/modelli-quadro':return self.send(panel_catalog.models(c))
   if path=='/api/listino/quadri':return self.send(panel_catalog.search(c,parse_qs(u.query)))
   if path=='/api/scatole-preimpostate':self.send([dict(x) for x in c.execute('SELECT id,nome,scatola_json FROM scatole_preimpostate ORDER BY id DESC')]);return
   if path=='/api/configurazioni':self.send([dict(x) for x in c.execute('SELECT * FROM configurazioni_civili ORDER BY id DESC')]);return
   if path=='/api/listino/automatico':return self.send(catalog_auto.options(c))
   if path=='/api/listino/associazioni':return self.send(catalog_config.associations(c))
   if path=='/api/listino/fonti':
    self.send([r[0] for r in c.execute("SELECT DISTINCT CASE WHEN instr(codice,':')>0 THEN substr(codice,1,instr(codice,':')-1) ELSE 'BASE_EPPAT' END FROM voci ORDER BY 1")]);return
   if path=='/api/voci':
    query=parse_qs(u.query);q=query.get('q',[''])[0];source=query.get('fonte',[''])[0]
    sql="SELECT * FROM voci v WHERE NOT EXISTS(SELECT 1 FROM catalog_status s WHERE s.code=v.codice AND s.active=0) AND (codice LIKE ? OR descrizione LIKE ? OR dettagli LIKE ?)"
    args=['%'+q+'%']*3
    if source:
     sql+=" AND CASE WHEN instr(codice,':')>0 THEN substr(codice,1,instr(codice,':')-1) ELSE 'BASE_EPPAT' END = ?";args.append(source)
    else:
     # Keep legacy rows, but hide matching canonical EPPAT rows from combined search.
     sql+=" AND NOT (instr(v.codice,':')=0 AND EXISTS (SELECT 1 FROM voci n WHERE n.codice='EPPAT:'||v.codice))"
    self.send([dict(x) for x in c.execute(sql+' ORDER BY codice LIMIT 100',args)]);return
   for t in ('clienti','lavori','pratiche','preventivi','listini'):
    if path=='/api/'+t:self.send([dict(x) for x in c.execute('SELECT * FROM '+t+' ORDER BY id DESC')]);return
   if path.startswith('/api/preventivi/'):
    pid=int(path.split('/')[-1]);p=c.execute('SELECT * FROM preventivi WHERE id=?',(pid,)).fetchone();self.send({'preventivo':dict(p),'righe':[dict(x) for x in c.execute('SELECT * FROM righe WHERE preventivo_id=?',(pid,))]} if p else {},200 if p else 404);return
   if path.startswith('/api/documenti/'):
    cid=int(path.split('/')[-1]);self.send([dict(x) for x in c.execute('SELECT id,cliente_id,nome,caricato FROM documenti WHERE cliente_id=?',(cid,))]);return
   if path.startswith('/api/download/'):
    id=int(path.split('/')[-1]);r=c.execute('SELECT * FROM documenti WHERE id=?',(id,)).fetchone()
    if not r:return self.send({'errore':'non trovato'},404)
    f=DOCS/r['path'];b=f.read_bytes();self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+__import__('urllib.parse',fromlist=['quote']).quote(r['nome']));self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
   self.send({'errore':'non trovato'},404)
  except Exception as e:self.send({'errore':str(e)},400)
  finally:c.close()
 def do_POST(self):
  if not self.ingress_allowed():return self.send({'errore':'Apri il gestionale da Home Assistant'},403)
  c=conn();path=urlparse(self.path).path.rstrip('/')
  try:
   if path.startswith('/api/auth/'):return self.send({'errore':'non trovato'},404)
   if not self.same_origin():return self.send({'errore':'Origine non valida'},403)
   if path=='/api/preventivi/cliente-pdf':
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=5*1024*1024:return self.send({'errore':'Preventivo troppo grande'},413)
    from pdf_client_quote import build_client_quote
    b=build_client_quote(self.body(),BASE/'logo.jpg');self.send_response(200);self.send_header('Content-Type','application/pdf');self.send_header('Content-Disposition','attachment; filename="Preventivo_cliente_GhiroTech.pdf"');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
   if path=='/api/preventivi/excel':
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=5*1024*1024:return self.send({'errore':'Preventivo troppo grande'},413)
    from excel_quote import build_quote
    b=build_quote(self.body());self.send_response(200);self.send_header('Content-Type','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');self.send_header('Content-Disposition','attachment; filename="Preventivo_GhiroTech.xlsx"');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
   if path=='/api/configurazioni/riepilogo-pdf':
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=5*1024*1024:return self.send({'errore':'Riepilogo troppo grande'},413)
    from pdf_summary import build_summary
    b=build_summary(self.body(),BASE/'logo.jpg');self.send_response(200);self.send_header('Content-Type','application/pdf');self.send_header('Content-Disposition','attachment; filename="Riepilogo_impianto.pdf"');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
   if path=='/api/impostazioni/archivio':
    payload=self.body();return self.send(configure_storage(CONTROL,DATA,payload.get('percorso')))
   if path in ('/api/planimetrie/import','/api/planimetrie/pagina'):
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=15*1024*1024:return self.send({'errore':'PDF massimo 10 MB'},413)
    payload=self.body()
    if path.endswith('/import'):
     return self.send(import_pdf(PLANS,payload.get('nome'),payload.get('contenuto')))
    return self.send(pdf_preview(PLANS,payload.get('id'),payload.get('pagina')))
   if path.startswith('/api/upload/'):
    cid=int(path.split('/')[-1]);length=int(self.headers.get('Content-Length','0'))
    if length>25*1024*1024:return self.send({'errore':'File massimo 25 MB'},413)
    # Multipart parser compatible with Python 3.12
    import email
    raw=self.rfile.read(length);msg=email.parser.BytesParser().parsebytes(b'Content-Type: '+self.headers['Content-Type'].encode()+b'\r\nMIME-Version: 1.0\r\n\r\n'+raw)
    parts=[x for x in msg.walk() if x.get_filename()]
    if not parts:return self.send({'errore':'File mancante'},400)
    part=parts[0];name=pathlib.Path(part.get_filename()).name;data=part.get_payload(decode=True);folder=DOCS/str(cid);folder.mkdir(exist_ok=True);stored=uuid.uuid4().hex+'_'+name;(folder/stored).write_bytes(data)
    c.execute('INSERT INTO documenti(cliente_id,nome,path,caricato) VALUES(?,?,?,?)',(cid,name,str(cid)+'/'+stored,datetime.date.today().isoformat()));c.commit();return self.send({'ok':True})
   if path in ('/api/listino/import','/api/listino/preview'):
    length=int(self.headers.get('Content-Length','0'))
    if length<=0 or length>20*1024*1024:return self.send({'errore':'File massimo 20 MB'},413)
    data=self.body()
    return self.send(import_catalog(c,data,DATA/'backup_listini',preview=path.endswith('/preview')))
   if path in ('/api/listino/automatico/analizza','/api/listino/automatico/salva'):
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=100000:return self.send({'errore':'Richiesta troppo grande'},413)
    payload=self.body()
    return self.send(catalog_auto.save(c,payload) if path.endswith('/salva') else catalog_auto.analyse(c,payload))
   if path in ('/api/listino/associazioni','/api/listino/risolvi'):
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=5*1024*1024:return self.send({'errore':'Richiesta troppo grande'},413)
    payload=self.body()
    return self.send(catalog_config.resolve(c,payload) if path.endswith('/risolvi') else catalog_config.save_association(c,payload))
   if path in ('/api/modelli-quadro','/api/modelli-quadro/rinomina','/api/modelli-quadro/elimina'):
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=1024*1024:return self.send({'errore':'Richiesta troppo grande'},413)
    return self.send(panel_catalog.mutate(c,'salva' if path=='/api/modelli-quadro' else path.rsplit('/',1)[1],self.body()))
   d=self.body()
   if path=='/api/fotovoltaico':
    cid=int(d.get('id') or 0);args=(d.get('cliente_id') or None,str(d.get('titolo','Impianto fotovoltaico')),max(0,int(d.get('pannelli') or 0)),max(0,float(d.get('watt_pannello') or 0)),max(0,float(d.get('inverter_kw') or 0)),max(0,float(d.get('batteria_kwh') or 0)),str(d.get('orientamento','')),float(d.get('inclinazione') or 0),json.dumps(d.get('materiali',[]),ensure_ascii=False),str(d.get('note','')),datetime.date.today().isoformat())
    if cid:
     c.execute('UPDATE impianti_fv SET cliente_id=?,titolo=?,pannelli=?,watt_pannello=?,inverter_kw=?,batteria_kwh=?,orientamento=?,inclinazione=?,materiali_json=?,note=?,aggiornato=? WHERE id=?',args+(cid,));cur=c.execute('SELECT id FROM impianti_fv WHERE id=?',(cid,))
    else:cur=c.execute('INSERT INTO impianti_fv(cliente_id,titolo,pannelli,watt_pannello,inverter_kw,batteria_kwh,orientamento,inclinazione,materiali_json,note,aggiornato) VALUES(?,?,?,?,?,?,?,?,?,?,?)',args)
   elif path=='/api/checklist':
    template={'Fotovoltaico':['Verificare progetto e documentazione tecnica','Pratica connessione distributore (se applicabile)','Regolamento di esercizio (se richiesto)','Adempimenti GSE (se applicabili)','Dichiarazione di conformita e allegati','Verifiche e collaudo','Consegna documenti al cliente'],'Elettrico':['Verificare obbligo di progetto','Dichiarazione di conformita e allegati','Verifiche finali','Consegna documenti al cliente']}
    tipo=str(d.get('tipo','Elettrico'));cur=c.execute('INSERT INTO checklist_pratiche(lavoro_id,cliente_id,tipo,titolo,stato,scadenza,responsabile,note,creata) VALUES(?,?,?,?,?,?,?,?,?)',(d.get('lavoro_id') or None,d.get('cliente_id') or None,tipo,str(d.get('titolo','Nuova pratica')),str(d.get('stato','Da preparare')),str(d.get('scadenza','')),str(d.get('responsabile','')),str(d.get('note','')),datetime.date.today().isoformat()))
    for voce in template.get(tipo,[]):c.execute('INSERT INTO checklist_voci(pratica_id,titolo) VALUES(?,?)',(cur.lastrowid,voce))
   elif path=='/api/checklist/update':
    pid=int(d.get('id') or 0);allowed=['titolo','stato','scadenza','responsabile','note','lavoro_id','cliente_id'];fields=[k for k in allowed if k in d];
    if not fields:return self.send({'errore':'Nessuna modifica'},400)
    c.execute('UPDATE checklist_pratiche SET '+','.join(k+'=?' for k in fields)+' WHERE id=?',[d[k] for k in fields]+[pid]);c.commit();return self.send({'ok':True})
   elif path=='/api/checklist/voce':
    vid=int(d.get('id') or 0);c.execute('UPDATE checklist_voci SET completata=? WHERE id=?',(1 if d.get('completata') else 0,vid));c.commit();return self.send({'ok':True})
   elif path=='/api/scatole-preimpostate/rinomina':
    ident=int(d.get('id') or 0);name=str(d.get('nome','')).strip()
    if not name or len(name)>100:raise ValueError('Nome obbligatorio, massimo 100 caratteri')
    if not c.execute('SELECT id FROM scatole_preimpostate WHERE id=?',(ident,)).fetchone():return self.send({'errore':'Scatola preimpostata non trovata'},404)
    if c.execute('SELECT id FROM scatole_preimpostate WHERE nome=? AND id<>?',(name,ident)).fetchone():raise ValueError('Nome già presente: scegli un altro nome')
    c.execute('UPDATE scatole_preimpostate SET nome=? WHERE id=?',(name,ident));c.commit();return self.send({'ok':True})
   elif path=='/api/scatole-preimpostate/elimina':
    c.execute('DELETE FROM scatole_preimpostate WHERE id=?',(int(d['id']),));c.commit();return self.send({'ok':True})
   elif path=='/api/scatole-preimpostate':
    name=str(d.get('nome','')).strip();series='';box=d.get('scatola')
    sizes={'presa':1,'schuko':2,'interruttore':1,'deviatore':1,'pulsante':1,'invertitore':1,'dati':1,'tv':1,'tapparella':1,'cieco':1,'ronzatore':1,'campanello':3,'campanello2':2,'presenza1':1,'presenza2':2,'termostato2':2,'termostato3':3}
    if not name or len(name)>100:raise ValueError('Nome obbligatorio, massimo 100 caratteri')
    if not isinstance(box,dict) or box.get('moduli') not in [3,4,6,7]:raise ValueError('Scatola non valida')
    fruits=box.get('frutti');note=box.get('note','')
    if not isinstance(fruits,list) or any(f is not None and (not isinstance(f,str) or f not in sizes) for f in fruits) or sum(1 if f is None else sizes[f] for f in fruits)>box['moduli']:raise ValueError('Componenti non validi o scatola piena')
    if not isinstance(note,str) or len(note)>5000:raise ValueError('Note non valide')
    if c.execute('SELECT id FROM scatole_preimpostate WHERE nome=?',(name,)).fetchone():raise ValueError('Nome già presente: scegli un altro nome')
    cur=c.execute('INSERT INTO scatole_preimpostate(nome,serie,scatola_json) VALUES(?,?,?)',(name,series,json.dumps({'moduli':box['moduli'],'frutti':fruits,'note':note},ensure_ascii=False)))
   elif path in ('/api/configurazioni/rinomina','/api/configurazioni/elimina'):
    ident=int(d.get('id') or 0)
    if not c.execute('SELECT id FROM configurazioni_civili WHERE id=?',(ident,)).fetchone():return self.send({'errore':'Configurazione non trovata'},404)
    if path.endswith('/rinomina'):
     title=str(d.get('titolo','')).strip()
     if not title or len(title)>200:raise ValueError('Nome obbligatorio, massimo 200 caratteri')
     c.execute('UPDATE configurazioni_civili SET titolo=?,aggiornato=? WHERE id=?',(title,datetime.date.today().isoformat(),ident))
    else:c.execute('DELETE FROM configurazioni_civili WHERE id=?',(ident,))
    c.commit();return self.send({'ok':True})
   elif path=='/api/configurazioni':
    cid=d.get('id');existing=None
    if cid:
     existing=c.execute('SELECT cliente_id,appartamenti_json,descrizione,materiali_json FROM configurazioni_civili WHERE id=?',(int(cid),)).fetchone()
     if not existing:return self.send({'errore':'Progetto non trovato: salva come nuovo progetto'},404)
    client=d.get('cliente_id') if 'cliente_id' in d else (existing['cliente_id'] if existing else None)
    apartments=d.get('appartamenti',json.loads(existing['appartamenti_json'] or '[]') if existing else [])
    if not isinstance(apartments,list) or len(apartments)>200:raise ValueError('Appartamenti non validi')
    if any(not isinstance(a,dict) or not isinstance(a.get('id'),str) or not isinstance(a.get('nome'),str) or not a['nome'].strip() for a in apartments):raise ValueError('Nome e identificativo appartamento obbligatori')
    if len({a['id'] for a in apartments})!=len(apartments) or len({a['nome'].strip().casefold() for a in apartments})!=len(apartments):raise ValueError('Appartamenti duplicati')
    description=d.get('descrizione',existing['descrizione'] if existing else '')
    if not isinstance(description,str) or len(description)>5000:raise ValueError('Descrizione troppo lunga (massimo 5000 caratteri)')
    materials=d.get('materiali',json.loads(existing['materiali_json'] or 'null') if existing else None)
    if materials is not None and (not isinstance(materials,dict) or len(json.dumps(materials))>20000):raise ValueError('Materiali impianto non validi')
    args=(client or None,str(d.get('titolo','')),json.dumps(d.get('stanze',[]),ensure_ascii=False),datetime.date.today().isoformat(),json.dumps(apartments,ensure_ascii=False),description,json.dumps(materials,ensure_ascii=False))
    if cid:
     c.execute('UPDATE configurazioni_civili SET cliente_id=?,titolo=?,stanze_json=?,aggiornato=?,appartamenti_json=?,descrizione=?,materiali_json=? WHERE id=?',args+(int(cid),));cur=c.execute('SELECT id FROM configurazioni_civili WHERE id=?',(int(cid),))
    else:cur=c.execute('INSERT INTO configurazioni_civili(cliente_id,titolo,stanze_json,aggiornato,appartamenti_json,descrizione,materiali_json) VALUES(?,?,?,?,?,?,?)',args)
   elif path=='/api/preventivi':
    import math
    def number(v):
     x=float(v)
     if not math.isfinite(x) or x<0:raise ValueError('Valore numerico non valido')
     return x
    rows=d.get('righe',[])
    if not isinstance(rows,list) or len(rows)>5000:raise ValueError('Righe non valide')
    vals=[]
    for r in rows:
     material=number(r.get('quota_materiale',0))
     if material>100:raise ValueError('Quota materiale oltre 100%')
     vals.append((str(r.get('codice','')),str(r.get('descrizione','')),str(r.get('unita','')),number(r.get('quantita',1)),number(r.get('prezzo',0)),material,str(r.get('appartamento','')),json.dumps(r.get('associazione') or None,ensure_ascii=False),None if r.get('stanza') is None else str(r['stanza']),json.dumps(r.get('gruppo_cliente'),ensure_ascii=False) if not isinstance(r.get('gruppo_cliente'),str) else r['gruppo_cliente']))
    discount=number(d.get('sconto_materiale',0))
    if discount>100:raise ValueError('Sconto oltre 100%')
    args=(str(d.get('cliente','')),str(d.get('titolo','')),number(d.get('ricarico',0)),number(d.get('iva',22)),d.get('cliente_id') or None,discount)
    pid=int(d.get('id') or 0)
    if pid:
     if not c.execute('SELECT id FROM preventivi WHERE id=?',(pid,)).fetchone():return self.send({'errore':'Preventivo non trovato'},404)
     c.execute('UPDATE preventivi SET cliente=?,titolo=?,ricarico=?,iva=?,cliente_id=?,sconto_materiale=? WHERE id=?',args+(pid,))
     c.execute('DELETE FROM righe WHERE preventivo_id=?',(pid,))
    else:pid=c.execute('INSERT INTO preventivi(cliente,titolo,ricarico,iva,cliente_id,sconto_materiale) VALUES(?,?,?,?,?,?)',args).lastrowid
    c.executemany('INSERT INTO righe(preventivo_id,codice,descrizione,unita,quantita,prezzo,quota_materiale,appartamento,associazione,stanza,gruppo_cliente) VALUES(?,?,?,?,?,?,?,?,?,?,?)',[(pid,)+r for r in vals])
    c.commit();return self.send({'id':pid})
   elif path in ('/api/clienti','/api/lavori','/api/pratiche'):
    t=path.split('/')[-1];cols={'clienti':['nome','telefono','email','indirizzo','note'],'lavori':['cliente_id','titolo','tipo','stato','note'],'pratiche':['cliente_id','lavoro_id','titolo','stato','scadenza','note']}[t]
    cur=c.execute('INSERT INTO '+t+'('+','.join(cols)+') VALUES('+','.join('?' for _ in cols)+')',tuple(d.get(k) or None for k in cols))
   else:return self.send({'errore':'non trovato'},404)
   c.commit();self.send({'id':int(cid) if path=='/api/configurazioni' and cid else cur.lastrowid})
  except Exception as e:self.send({'errore':str(e)},400)
  finally:c.close()
class ExternalH(H):
 def ingress_allowed(self):
  # Separate web endpoint: never rely on proxy headers for authentication.
  options_path=pathlib.Path('/data/options.json')
  try:
   options=json.loads(options_path.read_text())
   password=options.get('web_password','')
  except (OSError,ValueError,TypeError):
   password=''
  if not isinstance(password,str) or len(password)<8:
   return False
  authorization=self.headers.get('Authorization','')
  if not authorization.startswith('Basic '):
   return False
  try:
   raw=base64.b64decode(authorization[6:],validate=True).decode('utf-8')
   username,provided=raw.split(':',1)
  except (ValueError,UnicodeDecodeError):
   return False
  return hmac.compare_digest(username,'ghirotech') and hmac.compare_digest(provided,password)
 def unauthorized(self):
  self.send_response(401)
  self.send_header('WWW-Authenticate','Basic realm="GhiroTech Gestionale", charset="UTF-8"')
  self.send_header('Cache-Control','no-store')
  self.send_header('Content-Length','0')
  self.end_headers()
 def do_GET(self):
  if not self.ingress_allowed():return self.unauthorized()
  return super().do_GET_external()
 def do_POST(self):
  if not self.ingress_allowed():return self.unauthorized()
  return super().do_POST_external()

# Reuse the existing handlers without changing Ingress access rules.
H.do_GET_external=H.do_GET
H.do_POST_external=H.do_POST
# External handler's authentication is performed before invoking existing routes.
# The original handlers call ingress_allowed again; ExternalH supplies its own check.
if __name__=='__main__':
 Thread(target=lambda:ThreadingHTTPServer(('0.0.0.0',8766),ExternalH).serve_forever(),daemon=True).start()
 ThreadingHTTPServer(('0.0.0.0',8765),H).serve_forever()

