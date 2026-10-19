import pathlib,sys,sqlite3,unittest,json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'ghiro_preventivi'))
import catalog_auto as auto
from catalog_config import initialize,resolve

class AutomaticCatalogTest(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:')
  self.c.executescript('CREATE TABLE voci(codice TEXT PRIMARY KEY,descrizione,dettagli,unita,categoria,prezzo,manodopera);')
  initialize(self.c)
  self.data={'serie':'Vimar Arké','colore':'Bianco','placca':'1965{m}.71','posa':'Muratura'}
  for code,desc in [('19653.71','Placca Classic 3M nero'),('19654.71','Placca Classic 4M nero'),('19657.71','Placca Classic 7M nero'),('19613','Supporto 3M + viti'),('19614','Supporto 4M + viti'),('19617','Supporto 7M + viti'),('V71303','Scatola incasso rettang. 3M azzurro'),('V71304','Scatola incasso rettang. 4M azzurro'),('V71306','Scatola incasso rettang. 6-7M azzurro'),('19203.B','Presa 2P+T 16A P17/11 bianco'),('19000.B','Interruttore 1P 10AX bianco'),('19001.B','Interruttore 1P 16AX bianco'),('19370.SR.B','Suoneria/ronzatore 12V 50-60Hz bianco'),('19380.B','Suoneria elettron. 3 sequenze 12V bianco'),('19339.13.B','Presa RJ45 Netsafe Cat6 UTP bianco')]:self.item(code,desc)
  self.c.commit()
 def tearDown(self):self.c.close()
 def item(self,code,desc):self.c.execute('INSERT INTO voci VALUES(?,?,?, ?,?,?,?)',('VIMAR:'+code,desc,'','cad','',10,0))
 def report(self):return auto.analyse(self.c,self.data)
 def test_known_codes_and_bom_no_6m_or_3m_bell_substitution(self):
  rows={r['componente']:r for r in self.report()['righe']}
  self.assertEqual(rows['FR-presa']['selezione'],'19203.B')
  self.assertEqual(rows['SCAT-7']['selezione'],'V71306+19617+19657.71')
  self.assertEqual(rows['SCAT-6']['opzioni'],[])
  self.assertEqual(rows['FR-campanello']['opzioni'],[])
  self.assertEqual(rows['FR-campanello2']['opzioni'][0]['id'],'19380.B')
  self.assertEqual(rows['FR-interruttore']['selezione'],'')
  self.assertEqual(rows['FR-ronzatore']['selezione'],'')  # voltage requires choice even if only one SKU
 def test_save_batch_preserves_existing_and_prices_follow_list(self):
  r=self.report();result=auto.save(self.c,{**self.data,'impronta':r['impronta'],'scelte':{'FR-interruttore':'19001.B'}})
  self.assertEqual(result['salvate'],5)
  identity={'serie':r['serie'],'variante':r['variante'],'componente':'FR-presa'}
  self.assertEqual(resolve(self.c,{'righe':[{'associazione':identity}]})['righe'][0]['articoli'][0]['codice'],'VIMAR:19203.B')
  self.c.execute("UPDATE voci SET prezzo=25 WHERE codice='VIMAR:19203.B'");self.c.commit()
  self.assertEqual(resolve(self.c,{'righe':[{'associazione':identity}]})['righe'][0]['articoli'][0]['prezzo'],25)
  new=self.report();self.assertTrue(next(x for x in new['righe'] if x['componente']=='FR-interruttore')['esistente'])
  auto.save(self.c,{**self.data,'impronta':new['impronta'],'scelte':{'FR-interruttore':'19000.B','FR-dati':'19339.13.B'}})
  p=self.c.execute("SELECT products FROM catalog_associations WHERE component='FR-interruttore'").fetchone()[0];self.assertEqual(json.loads(p)[0]['codice'],'VIMAR:19001.B')
 def test_stale_price_list_and_tampered_choices_do_not_write(self):
  r=self.report()
  with self.assertRaises(ValueError):auto.save(self.c,{**self.data,'impronta':r['impronta'],'scelte':{'FR-interruttore':'EVIL'}})
  self.assertEqual(len(list(self.c.execute('SELECT * FROM catalog_associations'))),0)
  self.c.execute("UPDATE voci SET prezzo=21 WHERE codice='VIMAR:19203.B'");self.c.commit()
  with self.assertRaises(ValueError):auto.save(self.c,{**self.data,'impronta':r['impronta'],'scelte':{}})
 def test_cancelled_missing_colour_and_incomplete_bom_excluded(self):
  self.c.execute('INSERT INTO catalog_status VALUES(?,?,0)',('VIMAR:19203.B','2'));self.c.execute("DELETE FROM voci WHERE codice='VIMAR:19613'");self.c.commit()
  rows={r['componente']:r for r in self.report()['righe']}
  self.assertEqual(rows['FR-presa']['opzioni'],[]);self.assertEqual(rows['SCAT-3']['opzioni'],[])
  self.data['colore']='Grigio';self.assertEqual(next(x for x in self.report()['righe'] if x['componente']=='FR-interruttore')['opzioni'],[])
 def test_fit_uses_dedicated_support_and_plana_up_regular_support(self):
  self.item('19953.01','Placca fit 3M grafite matt');self.item('19913','Supporto Arké fit 3M + viti')
  self.item('14653U.01','Placca Plana Up 3M bianco');self.item('14613','Supporto 3M + viti');self.c.commit()
  self.data['placca']='1995{m}.01';self.assertEqual(self.report()['righe'][0]['selezione'],'V71303+19913+19953.01')
  self.data.update(serie='Vimar Plana',placca='1465{m}U.01');self.assertEqual(self.report()['righe'][0]['selezione'],'V71303+14613+14653U.01')
 def test_linea_uses_complete_coloured_device_not_bare_mechanism(self):
  self.item('30653.00','Placca 3M bianco');self.item('30000','Meccanismo interruttore 1P 10AX');self.item('30000.B','Interruttore 1P 10AX allineato bianco');self.c.commit()
  self.data.update(serie='Vimar Linea',placca='3065{m}.00')
  row=next(x for x in self.report()['righe'] if x['componente']=='FR-interruttore')
  self.assertEqual([o['id'] for o in row['opzioni']],['30000.B'])

if __name__=='__main__':unittest.main()
