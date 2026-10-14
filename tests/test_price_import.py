import pathlib, sqlite3, sys, tempfile, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'ghiro_preventivi'))
from price_import import initialize_catalog, import_catalog

class CatalogTest(unittest.TestCase):
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
