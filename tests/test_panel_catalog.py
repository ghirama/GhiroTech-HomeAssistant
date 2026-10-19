import copy
import json
import pathlib
import sqlite3
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'ghiro_preventivi'))
import panel_catalog as pc

PANEL={'nome':'Quadro tipo','file':2,'perFila':12,'larghezza':300,'altezza':400,'profondita':120,'codice':'GEWISS:TEST-C','note':'Modello','componenti':[{'tipo':'Magnetotermico','moduli':2,'fila':2,'posizione':4,'codice':'GEWISS:TEST-M','descrizione':'Cucina','articolo':'INT. TEST 2M'}]}

class PanelsTest(unittest.TestCase):
    def setUp(self):
        self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;pc.initialize(self.c)
    def tearDown(self):self.c.close()
    def test_models_preserve_geometry_not_prices_and_validate(self):
        p=copy.deepcopy(PANEL);p['prezzo']=123;p['selezioneArticolo']={'codice':'unused'};p['componenti'][0]['prezzo']=10
        ident=pc.mutate(self.c,'salva',{'nome':'Standard','quadro':p})['id']
        stored=json.loads(pc.models(self.c)[0]['quadro_json'])
        self.assertNotIn('prezzo',stored);self.assertNotIn('selezioneArticolo',stored);self.assertNotIn('prezzo',stored['componenti'][0]);self.assertEqual(stored['componenti'][0]['posizione'],4)
        with self.assertRaises(ValueError):pc.mutate(self.c,'salva',{'nome':'standard','quadro':p})
        pc.mutate(self.c,'rinomina',{'id':ident,'nome':'Nuovo'});self.assertEqual(pc.models(self.c)[0]['nome'],'Nuovo')
        pc.mutate(self.c,'elimina',{'id':ident});self.assertEqual(pc.models(self.c),[])
        self.assertEqual(stored['codice'],'GEWISS:TEST-C')
    def test_reject_overlap_outside_fractional_and_bad_shapes(self):
        for key,value in [('file',0),('perFila',True),('componenti',None)]:
            with self.subTest(key=key),self.assertRaises(ValueError):pc.normalize({**PANEL,key:value})
        for update in [{'fila':3},{'posizione':12},{'moduli':0.5}]:
            p=copy.deepcopy(PANEL);p['componenti'][0].update(update)
            with self.assertRaises(ValueError):pc.normalize(p)
        p=copy.deepcopy(PANEL);p['componenti'].append(dict(p['componenti'][0]))
        with self.assertRaises(ValueError):pc.normalize(p)
        self.assertEqual(pc.models(self.c),[])
    def test_specs_never_infer_modules_from_poles_or_fraction(self):
        self.assertEqual(pc.specs('CENTRALINO PAR.24M.(12X2) IP55'),{'moduli':24.0,'perFila':12,'file':2})
        self.assertEqual(pc.specs('CONTATTO AUX 0,5M')['moduli'],0.5)
        self.assertIsNone(pc.specs('INT 2P 25A 6KA')['moduli'])
        self.assertNotIn('file',pc.specs('CENTRALINO 24M.(18X2)'))
    def test_search_brand_active_positive_tokens_and_container_filter(self):
        self.c.executescript('CREATE TABLE voci(codice,descrizione,prezzo,unita);CREATE TABLE catalog_status(code,active);')
        rows=[('GEWISS:A','CENTRALINO 24M.(12X2)',100,'cad'),('GEWISS:B','INT.MAGNET. 1P C16 1M',10,'cad'),('VIMAR:B','INT.MAGNET. 1P C16 1M',10,'cad'),('GEWISS:C','QUADRO RACK 19 6U',100,'cad'),('GEWISS:D','CENTRALINO 12M',0,'cad'),('GEWISS:E','CENTRALINO 12M',100,'cad')]
        self.c.executemany('INSERT INTO voci VALUES(?,?,?,?)',rows);self.c.execute("INSERT INTO catalog_status VALUES('GEWISS:E',0)")
        self.assertEqual([x['codice'] for x in pc.search(self.c,{'tipo':['contenitore']})],['GEWISS:A'])
        self.assertEqual([x['codice'] for x in pc.search(self.c,{'q':['C16 1P']})],['GEWISS:B'])
        self.assertEqual(pc.search(self.c,{'q':['%']}),[])
