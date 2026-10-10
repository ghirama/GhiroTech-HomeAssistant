import sqlite3,json,pathlib,shutil,os,uuid,datetime,html,cgi,io,csv,secrets,hashlib,hmac,time
from http.cookies import SimpleCookie
from auth import password_hash,verify_password
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
 CREATE TABLE IF NOT EXISTS impianti_fv(id INTEGER PRIMARY KEY,cliente_id INTEGER,titolo TEXT,pannelli INTEGER DEFAULT 0,watt_pannello REAL DEFAULT 0,inverter_kw REAL DEFAULT 0,batteria_kwh REAL DEFAULT 0,orientamento TEXT DEFAULT '',inclinazione REAL DEFAULT 0,materiali_json TEXT DEFAULT '[]',note TEXT DEFAULT '',aggiornato TEXT);
 CREATE TABLE IF NOT EXISTS checklist_pratiche(id INTEGER PRIMARY KEY,lavoro_id INTEGER,cliente_id INTEGER,tipo TEXT,titolo TEXT,stato TEXT DEFAULT 'Da preparare',scadenza TEXT DEFAULT '',responsabile TEXT DEFAULT '',note TEXT DEFAULT '',creata TEXT);
 CREATE TABLE IF NOT EXISTS checklist_voci(id INTEGER PRIMARY KEY,pratica_id INTEGER,titolo TEXT,completata INTEGER DEFAULT 0);
 CREATE TABLE IF NOT EXISTS admin_login(id INTEGER PRIMARY KEY CHECK(id=1),username TEXT NOT NULL,password_hash TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS auth_sessions(token_hash TEXT PRIMARY KEY,expires INTEGER NOT NULL);
 ''')
 for tab,col,typ in [('preventivi','cliente_id','INTEGER'),('preventivi','sconto_materiale','REAL DEFAULT 0'),('righe','quota_materiale','REAL DEFAULT 0')]:
  if col not in [x[1] for x in c.execute('PRAGMA table_info('+tab+')')]:c.execute('ALTER TABLE '+tab+' ADD COLUMN '+col+' '+typ)
 c.commit();c.close()
init()
LOGIN_FAILURES={}
def login_allowed(ip):
 now=time.time();attempts=[t for t in LOGIN_FAILURES.get(ip,[]) if now-t<900];LOGIN_FAILURES[ip]=attempts
 return len(attempts)<8
def login_failed(ip):
 LOGIN_FAILURES.setdefault(ip,[]).append(time.time())
def admin_exists(c):
 return c.execute('SELECT 1 FROM admin_login WHERE id=1').fetchone() is not None
def token_digest(token):
 return hashlib.sha256(token.encode('utf-8')).hexdigest()
class H(BaseHTTPRequestHandler):
 def authenticated(self,c):
  supplied=self.headers.get('X-Ghiro-Session','')
  if len(supplied)==64 and c.execute('SELECT 1 FROM auth_sessions WHERE token_hash=? AND expires>?',(token_digest(supplied),int(time.time()))).fetchone():return True
  raw=self.headers.get('Cookie','')
  cookie=SimpleCookie()
  try:cookie.load(raw)
  except Exception:return False
  item=cookie.get('ghiro_session')
  if not item:return False
  token=item.value
  if len(token)!=64:return False
  return c.execute('SELECT 1 FROM auth_sessions WHERE token_hash=? AND expires>?',(token_digest(token),int(time.time()))).fetchone() is not None
 def set_session(self,c):
  token=secrets.token_hex(32)
  c.execute('DELETE FROM auth_sessions WHERE expires<=?',(int(time.time()),))
  c.execute('INSERT INTO auth_sessions(token_hash,expires) VALUES(?,?)',(token_digest(token),int(time.time())+30*86400))
  c.commit()
  self.send_response(200)
  self.send_header('Content-Type','application/json; charset=utf-8')
  self.send_header('Set-Cookie','ghiro_session='+token+'; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=2592000')
  self.send_header('Cache-Control','no-store')
  self.end_headers()
  self.wfile.write(json.dumps({'ok':True,'session_token':token}).encode('utf-8'))
 def same_origin(self):
  origin=self.headers.get('Origin','')
  host=self.headers.get('Host','')
  if not origin:return True
  from urllib.parse import urlsplit
  u=urlsplit(origin)
  return u.scheme=='https' and u.netloc==host

 def send(self,obj,status=200):
  b=json.dumps(obj,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def body(self):return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
 def do_GET(self):
  u=urlparse(self.path);path=u.path.rstrip('/');c=conn()
  try:
   if path=='/api/auth/status':self.send({'configured':admin_exists(c),'authenticated':self.authenticated(c)});return
   if path not in ('','/','/manifest.webmanifest','/icon.svg') and not self.authenticated(c):return self.send({'errore':'Accesso richiesto'},401)
   if path in ('/manifest.webmanifest','/icon.svg'):
    name='manifest.webmanifest' if path.endswith('webmanifest') else 'icon.svg';b=(BASE/name).read_bytes();self.send_response(200);self.send_header('Content-Type','application/manifest+json' if name.endswith('webmanifest') else 'image/svg+xml');self.send_header('Cache-Control','public, max-age=3600');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
   if path in ('','/'):b=(BASE/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(b);return
   if path=='/api/fotovoltaico':self.send([dict(x) for x in c.execute('SELECT * FROM impianti_fv ORDER BY id DESC')]);return
   if path=='/api/checklist':self.send([dict(x) for x in c.execute('SELECT * FROM checklist_pratiche ORDER BY id DESC')]);return
   if path.startswith('/api/checklist-voci/'):
    pid=int(path.split('/')[-1]);self.send([dict(x) for x in c.execute('SELECT * FROM checklist_voci WHERE pratica_id=? ORDER BY id',(pid,))]);return
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
   if path=='/api/auth/setup':
    if admin_exists(c):return self.send({'errore':'Account gia configurato'},403)
    d=self.body();user=str(d.get('username','')).strip();password=str(d.get('password',''))
    if len(user)<3 or len(password)<10 or len(password)>256:return self.send({'errore':'Utente minimo 3 caratteri e password minimo 10'},400)
    c.execute('INSERT INTO admin_login(id,username,password_hash) VALUES(1,?,?)',(user,password_hash(password)));c.commit();return self.set_session(c)
   if path=='/api/auth/login':
    ip=self.client_address[0]
    if not login_allowed(ip):return self.send({'errore':'Troppi tentativi: riprova tra 15 minuti'},429)
    d=self.body();r=c.execute('SELECT username,password_hash FROM admin_login WHERE id=1').fetchone()
    if not r or not hmac.compare_digest(str(d.get('username','')),r['username']) or not verify_password(str(d.get('password','')),r['password_hash']):
     login_failed(ip);return self.send({'errore':'Credenziali non valide'},401)
    LOGIN_FAILURES.pop(ip,None)
    return self.set_session(c)
   if not self.authenticated(c):return self.send({'errore':'Accesso richiesto'},401)
   if not self.same_origin():return self.send({'errore':'Origine non valida'},403)
   if path=='/api/auth/logout':
    cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''));item=cookie.get('ghiro_session')
    if item:c.execute('DELETE FROM auth_sessions WHERE token_hash=?',(token_digest(item.value),));c.commit()
    self.send_response(200);self.send_header('Set-Cookie','ghiro_session=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0');self.end_headers();return
   if path=='/api/auth/username':
    d=self.body();new=str(d.get('new_username','')).strip()
    if len(new)<3 or len(new)>100:return self.send({'errore':'Nome utente da 3 a 100 caratteri'},400)
    row=c.execute('SELECT password_hash FROM admin_login WHERE id=1').fetchone()
    if not row or not verify_password(str(d.get('current_password','')),row['password_hash']):return self.send({'errore':'Password attuale errata'},403)
    c.execute('UPDATE admin_login SET username=? WHERE id=1',(new,));c.execute('DELETE FROM auth_sessions');c.commit();return self.send({'ok':True})
   if path=='/api/auth/password':
    d=self.body();r=c.execute('SELECT password_hash FROM admin_login WHERE id=1').fetchone()
    if not verify_password(str(d.get('old_password','')),r['password_hash']):return self.send({'errore':'Password attuale errata'},403)
    new=str(d.get('new_password',''))
    if len(new)<10 or len(new)>256:return self.send({'errore':'Nuova password minimo 10 caratteri'},400)
    c.execute('UPDATE admin_login SET password_hash=? WHERE id=1',(password_hash(new),));c.execute('DELETE FROM auth_sessions');c.commit();return self.send({'ok':True})
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
   elif path=='/api/configurazioni':
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
