import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from prepare_catalogs import metel_rows,eppat_rows

class PreparationTest(unittest.TestCase):
 def test_metel_multiplier_brands_and_cancelled(self):
  def row(brand,code,status):
   r=[None]*23;r[0]=brand;r[1]=code;r[3]='Cavo';r[10]=1643.72;r[11]=100;r[12]='EUR';r[13]='LM';r[15]=status;return tuple(r)
  rows=[(2,row('CAB','000011',3)),(3,row('BTI','000011',6)),(4,row('CAB','gone',9))]
  catalogs,rejected,stats=metel_rows(rows,[str(i) for i in range(23)],'test','BTICINO')
  self.assertEqual(catalogs['BTICINO_CAB'][0]['prezzo'],'16.4372')
  self.assertEqual(catalogs['BTICINO_CAB'][0]['codice'],'000011')
  self.assertEqual(catalogs['BTICINO_BTI'][0]['unita'],'m')
  self.assertEqual(len(rejected),1)
  with self.assertRaises(ValueError):metel_rows(rows+[rows[0]],[str(i) for i in range(23)],'test','BTICINO')
 def test_eppat_hierarchy_duplicates_and_missing(self):
  parent=('B.62.01','Cavi','Posa inclusa',None,'Lavori',None,None,None,None,None)
  child=('B.62.01.0001',None,None,'m','Lavori',12.34,79,0,0,None)
  missing=('B.62.01.0002','Voce',None,None,'Lavori',5,0,0,0,None)
  zero=('B.62.01.0003','Da analizzare',None,'cad','Lavori',0,0,0,0,None)
  catalogs,rejected,stats=eppat_rows([(3,parent),(4,child),(5,child),(6,missing),(7,zero)])
  self.assertEqual(len(catalogs['EPPAT']),1)
  self.assertEqual(catalogs['EPPAT'][0]['descrizione'],'Cavi')
  self.assertIn('Posa inclusa',catalogs['EPPAT'][0]['dettagli'])
  self.assertEqual(len(rejected),2)
  self.assertEqual(stats['duplicati_identici_unificati'],1)
  conflict=list(child);conflict[5]=99
  with self.assertRaises(ValueError):eppat_rows([(4,child),(5,tuple(conflict))])

if __name__=='__main__':unittest.main()
