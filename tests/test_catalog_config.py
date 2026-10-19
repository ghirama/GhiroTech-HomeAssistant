import base64
import io
import pathlib
import sqlite3
import sys
import tempfile
import unittest
import openpyxl
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'ghiro_preventivi'))
from catalog_config import initialize, read_excel, save_association, resolve, associations
from price_import import initialize_catalog, import_catalog

class AssociationsTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.c=sqlite3.connect(pathlib.Path(self.temp.name)/'test.sqlite')
  self.c.executescript('CREATE TABLE voci(codice TEXT PRIMARY KEY,descrizione,dettagli,unita,categoria,prezzo,manodopera);CREATE TABLE listini(id INTEGER PRIMARY KEY,etichetta,caricato,numero_voci);CREATE TABLE righe(prezzo);INSERT INTO righe VALUES(42);')
  initialize_catalog(self.c);initialize(self.c);self.c.commit()
  self.payload={'fonte':'VIMAR','edizione':'1','voci':[{'codice':'001.01','descrizione':'Presa','unita':'cad','prezzo':10},{'codice':'002','descrizione':'Supporto','unita':'cad','prezzo':2}]}
  self.identity={'serie':'Vimar Plana','variante':'Bianco / placca A','componente':'SCAT-3'}
 def tearDown(self):
  self.c.close();self.temp.cleanup()
 def put(self,d=None):return import_catalog(self.c,d or self.payload,self.temp.name)
 def test_prices_update_by_code_and_quotes_remain_unchanged(self):
  self.put();save_association(self.c,{**self.identity,'articoli':[{'codice':'VIMAR:001.01','quantita':1},{'codice':'VIMAR:002','quantita':2}]})
  request={'righe':[{'associazione':self.identity},{'associazione':{**self.identity,'variante':'Altro colore'}}]}
  result=resolve(self.c,request)['righe'];self.assertEqual(sum(p['prezzo']*p['quantita'] for p in result[0]['articoli']),14);self.assertIn('errore',result[1])
  self.payload['voci'][0]['prezzo']=15;self.payload['edizione']='2';self.put()
  result=resolve(self.c,request)['righe'];self.assertEqual(result[0]['articoli'][0]['prezzo'],15);self.assertEqual(self.c.execute('SELECT prezzo FROM righe').fetchone()[0],42)
  self.assertEqual(len(associations(self.c)),1)
  self.c.close();self.c=sqlite3.connect(pathlib.Path(self.temp.name)/'test.sqlite');self.assertEqual(len(associations(self.c)),1)
 def test_missing_cancelled_and_partial_catalogs(self):
  self.put();save_association(self.c,{**self.identity,'articoli':[{'codice':'VIMAR:001.01'}]})
  self.payload['voci']=self.payload['voci'][1:];self.payload['edizione']='2';self.put()
  request={'righe':[{'associazione':self.identity}]}
  self.assertIn('articoli',resolve(self.c,request)['righe'][0])
  self.payload['completo']=True;self.put();self.assertIn('errore',resolve(self.c,request)['righe'][0])
  self.payload['inattivi']=['002'];self.put();self.assertIn('errore',resolve(self.c,{'righe':[{'codice':'VIMAR:002'}]})['righe'][0])
  with self.assertRaises(ValueError):save_association(self.c,{**self.identity,'articoli':[{'codice':'VIMAR:002'}]})
 def test_invalid_mapping_and_delete(self):
  self.put()
  for qty in [0,-1,1.5,101,True]:
   with self.assertRaises(ValueError):save_association(self.c,{**self.identity,'articoli':[{'codice':'VIMAR:001.01','quantita':qty}]})
  save_association(self.c,{**self.identity,'articoli':[{'codice':'VIMAR:001.01'}]});save_association(self.c,{**self.identity,'elimina':True});self.assertEqual(associations(self.c),[])
 def excel(self,rows):
  w=openpyxl.Workbook();s=w.active
  for r in rows:s.append(r)
  b=io.BytesIO();w.save(b);w.close();return {**self.payload,'xlsx':base64.b64encode(b.getvalue()).decode()}
 def test_excel_metel_multiplier_cancelled_and_text_codes(self):
  headers=['Sigla Marchio','Codice Prodotto Azienda','EAN','Descrizione prodotto','','','','','','','Prezzo al Pubblico','Moltiplic. prezzo','Codice valuta','Unità misura','','SP']
  row=['VIW','001.01',None,'Presa',None,None,None,None,None,None,123,100,'EUR','PCE',None,3]
  data=self.excel([headers,row,row[:1]+['002']+row[2:15]+[9]])
  result=read_excel(data);self.assertEqual(result['voci'][0]['codice'],'001.01');self.assertEqual(result['voci'][0]['prezzo'],'1.23');self.assertEqual(result['inattivi'],['002'])
  self.assertEqual(import_catalog(self.c,data,self.temp.name,True)['inattive'],1)
  self.assertEqual(self.c.execute('SELECT COUNT(*) FROM voci').fetchone()[0],0)
  self.put(data);self.assertIn('errore',resolve(self.c,{'righe':[{'codice':'VIMAR:002'}]})['righe'][0])
  row[1]=1
  with self.assertRaises(ValueError):read_excel(self.excel([headers,row]))
 def test_generic_excel_and_formulas_rejected(self):
  data=self.excel([['codice','descrizione','unita','prezzo'],['001','Supporto','cad',3.4]])
  self.assertEqual(read_excel(data)['voci'][0]['codice'],'001')
  with self.assertRaises(ValueError):read_excel(self.excel([['codice','descrizione','unita','prezzo'],['001','Supporto','cad','=1+2']]))

if __name__=='__main__':unittest.main()
