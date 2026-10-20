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

class GuidedCatalogueTest(unittest.TestCase):
    def setUp(self):
        self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
        self.c.executescript('CREATE TABLE voci(codice,descrizione,prezzo,unita);CREATE TABLE catalog_status(code,active);')
        self.c.executemany('INSERT INTO voci VALUES(?,?,?,?)',[
            ('GEWISS:GW40007','CENTRALINO PAR.24M.(12X2) IP55',100,'cad'),
            ('GEWISS:GW90007','INT.MAGNET.COMPATTO 1P C16 4,5KA 1M',12,'cad'),
            ('GEWISS:GW90008','INT.MAGNET.COMPATTO 1P C20 4,5KA 1M',14,'cad'),
            ('GEWISS:GWD4002','INT.DIFF.PURO 2P 25A AC/0,03 2M',20,'cad'),
            ('GEWISS:GW96104','INTER.MANOVRA-SEZIONATORE 1P 32A',10,'cad'),
            ('GEWISS:GWD6401','LST - SCARICATORE 1P+N 12,5KA T1+2',10,'cad'),
            ('GEWISS:GWD6002','CONTATTO AUX POSIZ.IDP/SEZ ACC.0,5M',5,'cad'),
            ('VIMAR:GW90007','INT.MAGNET.1P C16 4,5KA 1M',1,'cad'),
            ('GEWISS:OLD','INT.MAGNET.1P C16 4,5KA 1M',1,'cad')])
        self.c.execute("INSERT INTO catalog_status VALUES('GEWISS:OLD',0)")
    def tearDown(self):self.c.close()
    def search(self,**kw):return pc.search(self.c,{k:[v] for k,v in dict(guidata='1',tipo='componente',**kw).items()})
    def test_filters_join_exact_skus_and_current_prices(self):
        data=self.search(categoria='Magnetotermico',poli='1P',corrente='16',curva='C',potere='4.5')
        self.assertEqual([x['codice'] for x in data['articoli']],['GEWISS:GW90007'])
        self.assertEqual(data['filtri']['corrente'],['16','20'])
        item=data['articoli'][0];self.assertEqual(item['moduli'],1);self.assertEqual(item['pagina'],423)
        self.c.execute("UPDATE voci SET prezzo=17 WHERE codice='GEWISS:GW90007'")
        self.assertEqual(self.search(q='GW90007')['articoli'][0]['prezzo'],17)
        self.assertEqual(self.search(corrente='99')['totale'],0)
    def test_catalogue_completes_missing_widths_and_dimensions(self):
        for code,width,page in [('GW96104',1,491),('GWD6401',2,488),('GWD6002',0.5,480)]:
            item=self.search(q=code)['articoli'][0]
            self.assertEqual((item['moduli'],item['pagina']),(width,page))
        item=pc.search(self.c,{'guidata':['1'],'tipo':['contenitore']})['articoli'][0]
        self.assertEqual([item[k] for k in ('file','perFila','larghezza','altezza','profondita')],[2,12,250,375,135])
        self.assertEqual(item['montaggio'],'Parete');self.assertEqual(item['ip'],'IP55')
    def test_conflicting_or_unknown_metadata_never_silently_assigns_width(self):
        self.c.execute("UPDATE voci SET descrizione='INT.MAGNET.1P C16 4,5KA 2M' WHERE codice='GEWISS:GW90007'")
        item=self.search(q='GW90007')['articoli'][0]
        self.assertIsNone(item['moduli']);self.assertIn('avviso',item)
        self.assertIsNone(pc.enriched({'codice':'GEWISS:UNKNOWN','descrizione':'INT.MAGNET.2P C16 6KA'})['moduli'])
    def test_attributes_do_not_confuse_current_sensitivity_and_breaking_capacity(self):
        d=pc.characteristics('INT.MAG.DIF.COM.3P C 6 4,5KA A/0,3 3M')
        self.assertEqual((d['corrente'],d['potere'],d['sensibilita']),(6,4.5,300))
        self.assertEqual(pc.characteristics('INT.DIFF.PURO 4P.25A ISTANT.AC/0,03 3M')['corrente'],25)
        self.assertEqual(pc.specs('CONTATTO AUX POSIZ.IDP 4P (3M) 0,5M')['moduli'],0.5)
        self.assertEqual(pc.characteristics('AFDD INT.MAGNETOTERMICO 1P+N C6 6KA 2M')['categoria'],'Altro')
        self.assertEqual(pc.characteristics('BLOCCO DIFFERENZIALE COMPONIBILE 2P')['categoria'],'Altro')
    def test_pagination_does_not_hide_filter_values(self):
        self.c.executemany('INSERT INTO voci VALUES(?,?,?,?)',[(f'GEWISS:X{i:03}','INT.MAGNET. 1P C10 6KA 1M',10,'cad') for i in range(110)])
        self.c.execute("INSERT INTO voci VALUES('GEWISS:ZZZ','INT.MAGNET. 2P C63 10KA 2M',10,'cad')")
        data=self.search(categoria='Magnetotermico')
        self.assertEqual(len(data['articoli']),100);self.assertEqual(data['totale'],113)
        self.assertIn('63',data['filtri']['corrente'])
        self.assertEqual(self.search(corrente='63')['articoli'][0]['codice'],'GEWISS:ZZZ')
