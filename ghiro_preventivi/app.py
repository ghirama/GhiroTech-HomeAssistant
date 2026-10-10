import sqlite3,json,pathlib,shutil,os,uuid,datetime,html,cgi,io,csv
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
BASE=pathlib.Path(__file__).parent
DATA=pathlib.Path('/data') if pathlib.Path('/data').is_dir() else BASE
DB=DATA/'prezzario.sqlite'
if not DB.exists():shutil.copy2(BASE/'prezzario.sqlite',DB)
DOCS=DATA/'documenti';DOCS.mkdir(exist_ok=True)
def conn():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def init():
 c=conn()
 c.executescript('''CREATE TABLE IF NOT EXISTS clienti(id INTEGER PRIMARY KEY,nome TEXT NOT NULL,telefono TEXT DEFAULT '',email TEXT DEFAULT '',indirizzo TEXT DEFAULT '',note TEXT DEFAULT '');
 CREATE TABLE IF NOT EXISTS lavori(id INTEGER PRIMARY KEY,cliente_id INTEGER,titolo TEXT,tipo TEXT,stato TEXT DEFAULT 'Da iniziare',note TEXT DEFAULT '');
 CREATE TABLE IF NOT EXISTS pratiche(id INTEGER PRIMARY KEY,cliente_id INTEGER,lavoro_id INTEGER,titolo TEXT,stato TEXT DEFAULT 'Da preparare',scadenza TEXT DEFAULT '',note TEXT DEFAULT '');
 CREATE TABLE IF NOT EXISTS documenti(id INTEGER PRIMARY KEY,cliente_id INTEGER,nome TEXT,path TEXT,caricato TEXT);
 CREATE TABLE IF NOT EXISTS configurazioni_civili(id INTEGER PRIMARY KEY,cliente_id INTEGER,titolo TEXT,stanze_json TEXT,aggiornato TEXT);
 CREATE TABLE IF NOT EXISTS listini(id INTEGER PRIMARY KEY,etichetta TEXT,caricato TEXT,numero_voci INTEGER);
 ''')
 for tab,col,typ in [('preventivi','cliente_id','INTEGER'),('preventivi','sconto_materiale','REAL DEFAULT 0'),('righe','quota_materiale','REAL DEFAULT 0')]:
  if col not in [x[1] for x in c.execute('PRAGMA table_info('+tab+')')]:c.execute('ALTER TABLE '+tab+' ADD COLUMN '+col+' '+typ)
 c.commit();c.close()
init()
class H(BaseHTTPRequestHandler):
 def send(self,obj,status=200):
  b=json.dumps(obj,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def body(self):return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
 def do_GET(self):
  u=urlparse(self.path);path=u.path.rstrip('/');c=conn()
  try:
   if path in ('','/'):b=(BASE/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(b);return
   if path=='/api/configurazioni':self.send([dict(x) for x in c.execute('SELECT * FROM configurazioni_civili ORDER BY id DESC')]);return
   if path=='/api/voci':
    q=parse_qs(u.query).get('q',[''])[0];self.send([dict(x) for x in c.execute('SELECT * FROM voci WHERE codice LIKE ? OR descrizione LIKE ? OR dettagli LIKE ? LIMIT 100',('%'+q+'%',)*3)]);return
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
  c=conn();path=urlparse(self.path).path.rstrip('/')
  try:
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
   if path=='/api/listino/import':
    # Accept JSON array exported as CSV rows; keeps historic quote prices unchanged.
    data=self.body();rows=data.get('voci',[])
    if not rows or len(rows)>100000:return self.send({'errore':'Elenco voci non valido'},400)
    valid=[]
    for r in rows:
     code=str(r.get('codice','')).strip();price=float(str(r.get('prezzo',0)).replace(',','.'))
     if code and price>=0:valid.append((code,str(r.get('descrizione','')),str(r.get('dettagli','')),str(r.get('unita','')),str(r.get('categoria','')),price,float(r.get('manodopera',0) or 0)))
    c.executemany('INSERT OR REPLACE INTO voci VALUES(?,?,?,?,?,?,?)',valid);c.execute('INSERT INTO listini(etichetta,caricato,numero_voci) VALUES(?,?,?)',(str(data.get('etichetta','Aggiornamento')),datetime.date.today().isoformat(),len(valid)));c.commit();return self.send({'importate':len(valid)})
   d=self.body()
   if path=='/api/configurazioni':
    cid=d.get('id'); args=(d.get('cliente_id') or None,str(d.get('titolo','')),json.dumps(d.get('stanze',[]),ensure_ascii=False),datetime.date.today().isoformat())
    if cid:
     c.execute('UPDATE configurazioni_civili SET cliente_id=?,titolo=?,stanze_json=?,aggiornato=? WHERE id=?',args+(int(cid),));cur=c.execute('SELECT id FROM configurazioni_civili WHERE id=?',(int(cid),))
    else:cur=c.execute('INSERT INTO configurazioni_civili(cliente_id,titolo,stanze_json,aggiornato) VALUES(?,?,?,?)',args)
   elif path=='/api/preventivi':
    cur=c.execute('INSERT INTO preventivi(cliente,titolo,ricarico,iva,cliente_id,sconto_materiale) VALUES(?,?,?,?,?,?)',(d.get('cliente',''),d.get('titolo',''),float(d.get('ricarico',0)),float(d.get('iva',22)),d.get('cliente_id') or None,float(d.get('sconto_materiale',0))))
    for r in d.get('righe',[]):c.execute('INSERT INTO righe(preventivo_id,codice,descrizione,unita,quantita,prezzo,quota_materiale) VALUES(?,?,?,?,?,?,?)',(cur.lastrowid,r.get('codice',''),r.get('descrizione',''),r.get('unita',''),float(r.get('quantita',1)),float(r.get('prezzo',0)),float(r.get('quota_materiale',0))))
   elif path in ('/api/clienti','/api/lavori','/api/pratiche'):
    t=path.split('/')[-1];cols={'clienti':['nome','telefono','email','indirizzo','note'],'lavori':['cliente_id','titolo','tipo','stato','note'],'pratiche':['cliente_id','lavoro_id','titolo','stato','scadenza','note']}[t]
    cur=c.execute('INSERT INTO '+t+'('+','.join(cols)+') VALUES('+','.join('?' for _ in cols)+')',tuple(d.get(k) or None for k in cols))
   else:return self.send({'errore':'non trovato'},404)
   c.commit();self.send({'id':cur.lastrowid})
  except Exception as e:self.send({'errore':str(e)},400)
  finally:c.close()
if __name__=='__main__':ThreadingHTTPServer(('0.0.0.0',8765),H).serve_forever()
