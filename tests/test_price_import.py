import pathlib, sqlite3, sys, tempfile, unittest
import threading
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'ghiro_preventivi'))
from price_import import initialize_catalog, import_catalog, number, validate

class CatalogTest(unittest.TestCase):
 def test_simultaneous_identical_import_is_idempotent(self):
  with tempfile.TemporaryDirectory() as folder:
   db=pathlib.Path(folder)/'live.sqlite'
   with sqlite3.connect(db) as c:
    c.executescript('CREATE TABLE voci(codice TEXT PRIMARY KEY,descrizione,dettagli,unita,categoria,prezzo,manodopera); CREATE TABLE listini(id INTEGER PRIMARY KEY,etichetta,caricato,numero_voci); CREATE TABLE righe(prezzo); INSERT INTO righe VALUES(42);')
    initialize_catalog(c)
   barrier=threading.Barrier(2)
   class SynchronizedConnection(sqlite3.Connection):
    def backup(self,*args,**kwargs):
     super().backup(*args,**kwargs)
     barrier.wait(timeout=10)
   payload={'fonte':'VIMAR','edizione':'test','completo':True,'voci':[{'codice':'001','descrizione':'Presa','unita':'cad','prezzo':12}]}
   def run():
    c=sqlite3.connect(db,timeout=10,factory=SynchronizedConnection)
    try:return import_catalog(c,payload,pathlib.Path(folder)/'backup')
    finally:c.close()
   with ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(lambda _:run(),range(2)))
   self.assertEqual(sorted(r['importate'] for r in results),[0,1])
   self.assertEqual(sum(r['gia_importato'] for r in results),1)
   with sqlite3.connect(db) as c:
    self.assertEqual(c.execute('SELECT COUNT(*) FROM catalog_imports').fetchone()[0],1)
    self.assertEqual(c.execute('SELECT COUNT(*) FROM listini').fetchone()[0],1)
    self.assertEqual(c.execute('SELECT prezzo FROM voci').fetchone()[0],12)
    self.assertEqual(c.execute('SELECT prezzo FROM righe').fetchone()[0],42)

 def test_null_fields_and_subcent_precision(self):
  self.assertEqual(number(0.00001),0.00001)
  self.assertEqual(number('16.4372'),16.4372)
  with self.assertRaises(ValueError):number(True)
  with self.assertRaises(ValueError):validate({'fonte':'TEST','edizione':'test','voci':[{'codice':None,'descrizione':'Voce','unita':'cad','prezzo':1}]})
 def test_failed_registration_rolls_back_catalog(self):
  with tempfile.TemporaryDirectory() as folder:
   c=sqlite3.connect(pathlib.Path(folder)/'live.sqlite')
   c.executescript('CREATE TABLE voci(codice TEXT PRIMARY KEY,descrizione,dettagli,unita,categoria,prezzo,manodopera); CREATE TABLE listini(id INTEGER PRIMARY KEY,etichetta,caricato,numero_voci); CREATE TRIGGER reject_history BEFORE INSERT ON listini BEGIN SELECT RAISE(ABORT,"test failure"); END;')
   initialize_catalog(c);c.commit()
   d={'fonte':'TEST','edizione':'test','voci':[{'codice':'001','descrizione':'Voce','unita':'cad','prezzo':1}]}
   with self.assertRaises(sqlite3.IntegrityError):import_catalog(c,d,folder)
   self.assertEqual(c.execute('select count(*) from voci').fetchone()[0],0)
   self.assertEqual(c.execute('select count(*) from catalog_imports').fetchone()[0],0)
   c.close()

 def test_transaction_snapshot_and_validation(self):
  with tempfile.TemporaryDirectory() as folder:
   c=sqlite3.connect(pathlib.Path(folder)/'live.sqlite')
   c.executescript('CREATE TABLE voci(codice TEXT PRIMARY KEY,descrizione,dettagli,unita,categoria,prezzo,manodopera); CREATE TABLE listini(id INTEGER PRIMARY KEY,etichetta,caricato,numero_voci); CREATE TABLE righe(prezzo); INSERT INTO righe VALUES(42);')
   initialize_catalog(c);c.commit()
   d={'fonte':'VIMAR','edizione':'test','csv':'codice;descrizione;unita;prezzo\n001;"Presa; bianca";cad;1.234,56\n'}
   self.assertEqual(import_catalog(c,d,folder,True)['nuove'],1)
   self.assertEqual(c.execute('select count(*) from voci').fetchone()[0],0)
   self.assertEqual(import_catalog(c,d,folder)['importate'],1)
   self.assertEqual(import_catalog(c,d,folder)['importate'],0)
   d['fonte']='BTICINO';import_catalog(c,d,folder)
   self.assertEqual(c.execute('select count(*) from voci').fetchone()[0],2)
   self.assertEqual(c.execute('select prezzo from righe').fetchone()[0],42)
   for price in ('','NaN','inf','-1','1,2,3'):
    d['csv']='codice;descrizione;unita;prezzo\nBAD;Voce;cad;'+price+'\n'
    with self.assertRaises(ValueError):import_catalog(c,d,folder)
   self.assertEqual(c.execute('select count(*) from voci').fetchone()[0],2)
   backups=list(pathlib.Path(folder).glob('pre-import-*.sqlite'))
   self.assertEqual(len(backups),2)
   with sqlite3.connect(backups[0]) as b:self.assertEqual(b.execute('select prezzo from righe').fetchone()[0],42)
   d['csv']='codice;descrizione;unita;prezzo\nDUP;Voce;cad;1\nDUP;Voce;cad;2\n'
   with self.assertRaises(ValueError):import_catalog(c,d,folder)
   c.close()

if __name__=='__main__':unittest.main()
