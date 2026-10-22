import io
import sys
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ghiro_preventivi'))
from excel_quote import build_quote, tag


class ExcelQuoteTests(unittest.TestCase):
    def sample(self):
        return {'titolo': 'Impianto elettrico', 'cliente': {'nome': 'Cliente prova'},
                'sconto_materiale': 10, 'ricarico': 20, 'iva': 22,
                'righe': [dict(appartamento=apt, codice='QE', descrizione=desc, unita='cad',
                               quantita=qty, prezzo=cost, quota_materiale=share)
                          for apt, desc, qty, cost, share in [
                              ('Appartamento 1', 'Quadro elettrico', 2, 100, 50),
                              ('Parti comuni *?', '=HYPERLINK("bad")', 1, 50, 100),
                              ('Appartamento 1', 'Presa', 3, 10, 0)]]}

    def test_layout_formulas_and_cached_totals(self):
        with zipfile.ZipFile(io.BytesIO(build_quote(self.sample()))) as z:
            p = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
            c = ET.fromstring(z.read('xl/worksheets/sheet2.xml'))
            cells = {x.get('r'): x for x in p.iter(tag('c'))}
            internal = {x.get('r'): x for x in c.iter(tag('c'))}
            self.assertAlmostEqual(float(cells['F20'].findtext(tag('v'))),387.96)
            self.assertEqual(internal['D19'].findtext(tag('f')), "'Calcolo interno'!E11")
            self.assertEqual(internal['F20'].findtext(tag('f')), 'SUM(F18:F19)')
            self.assertAlmostEqual(float(internal['F24'].findtext(tag('v'))),322.08)
            book=ET.fromstring(z.read('xl/workbook.xml'))
            self.assertEqual([s.get('name') for s in book.find(tag('sheets'))],['Riepilogo generale','Appartamento 1','Parti comuni --','Calcolo interno'])
            self.assertEqual(len(book.find(tag('definedNames'))),8)
            raw=ET.fromstring(z.read('xl/worksheets/sheet4.xml'))
            literal=next(x for x in raw.iter(tag('c')) if x.get('r')=='C10')
            self.assertEqual(literal.get('t'),'inlineStr');self.assertIsNone(literal.find(tag('f')))
            self.assertEqual(p.find(tag('pageSetup')).get('fitToHeight'),'0')
            for name in z.namelist():
                if name.endswith('.xml'):
                    ET.fromstring(z.read(name))

    def test_sections_sum_once_and_preserve_cost_inputs(self):
        data=self.sample();data['righe']=[dict(appartamento='Casa',codice=code,descrizione=desc,unita='cad',quantita=qty,prezzo=price,quota_materiale=share) for code,desc,qty,price,share in [('FR-presa','Presa',2,10,100),('QE','Quadro',1,100,100),('IMPIANTO-CAVI','Cavi',100,2,100),('IMPIANTO-TUBAZIONI','Tubazioni',50,1,100),('IMPIANTO-MANODOPERA','Manodopera',10,30,0),('LIBERA','Altra lavorazione',1,40,0)]]
        expected=sum(r['quantita']*r['prezzo']*(1-r['quota_materiale']/100*.1)*1.2 for r in data['righe'])
        with zipfile.ZipFile(io.BytesIO(build_quote(data))) as z:
            root=ET.fromstring(z.read('xl/worksheets/sheet2.xml'));rows=root.find(tag('sheetData'))
            labels=[''.join(c.itertext()) for c in root.iter(tag('c')) if c.get('t')=='inlineStr']
            for title in ['SCATOLE E COMPONENTI','QUADRI ELETTRICI','CAVI E TUBAZIONI','MANODOPERA','ALTRE FORNITURE E LAVORAZIONI']:
                self.assertIn(title,labels)
            netrow=next(r for r in rows if any(c.findtext('./'+tag('is')+'/'+tag('t'))=='Imponibile' for c in r))
            net=next(c for c in netrow if c.get('r').startswith('F'))
            self.assertAlmostEqual(float(net.findtext(tag('v'))),expected)
            self.assertEqual(net.findtext(tag('f')).count(','),4)
            raw=ET.fromstring(z.read('xl/worksheets/sheet3.xml'))
            self.assertEqual(raw.find(tag('autoFilter')).get('ref'),'A8:J14')
            self.assertEqual(len([c for c in raw.iter(tag('c')) if c.find(tag('f')) is not None]),18)

    def test_rooms_group_interleaved_rows_keep_apartments_and_totals_separate(self):
        data=self.sample();data.update(sconto_materiale=0,ricarico=0,iva=0)
        data['righe']=[dict(appartamento=apt,stanza=room,codice=code,descrizione=desc,unita='cad',quantita=1,prezzo=price,quota_materiale=100) for apt,room,code,desc,price in [
            ('Casa 1','Cucina','FR-presa','Presa cucina',10),
            ('Casa 1','Bagno','FR-presa','Presa bagno',20),
            ('Casa 2','Cucina','FR-presa','Presa altra casa',30),
            ('Casa 1','Cucina','DER-TEST','Derivazione cucina',40),
            ('Casa 1',None,'VIMAR:TEST','Ingresso — Scatola 1 — Presa',50),
            ('Casa 1','','QE','Quadro generale',100),
            ('Casa 1','','IMPIANTO-MANODOPERA','Manodopera',200)]]
        with zipfile.ZipFile(io.BytesIO(build_quote(data))) as z:
            root=ET.fromstring(z.read('xl/worksheets/sheet2.xml'));rows=root.find(tag('sheetData'))
            labels={r.get('r'):r.findtext('./'+tag('c')+'/'+tag('is')+'/'+tag('t')) for r in rows}
            self.assertEqual([v for v in labels.values() if v and v.startswith('STANZA')],['STANZA — Cucina','STANZA — Bagno','STANZA — Ingresso'])
            subtotals={labels[r.get('r')]:float(next(c for c in r if c.get('r').startswith('F')).findtext(tag('v'))) for r in rows if (labels[r.get('r')] or '').startswith('Subtotale')}
            self.assertEqual(subtotals,{'Subtotale stanza — Cucina':50,'Subtotale stanza — Bagno':20,'Subtotale stanza — Ingresso':50,'Subtotale quadri elettrici':100,'Subtotale manodopera':200})
            detail_refs=[c.findtext(tag('f')) for c in root.iter(tag('c')) if c.get('r').startswith('B') and c.find(tag('f')) is not None]
            self.assertEqual(detail_refs,["'Calcolo interno'!C9","'Calcolo interno'!C12","'Calcolo interno'!C10","'Calcolo interno'!C13","'Calcolo interno'!C14","'Calcolo interno'!C15"])
            summary=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
            values={c.get('r'):c.findtext(tag('v')) for c in summary.iter(tag('c'))}
            self.assertEqual(float(values['E17']),420);self.assertEqual(float(values['E18']),30)
            self.assertEqual(float(values['E20']),450)

    def test_room_override_and_legacy_recovery(self):
        from excel_quote import room_name
        old={'codice':'FR-presa','descrizione':'Cucina — Arké — Presa'}
        self.assertEqual(room_name(old),'Cucina')
        self.assertEqual(room_name({**old,'stanza':'Bagno'}),'Bagno')
        self.assertEqual(room_name({**old,'stanza':''}),'')
        self.assertEqual(room_name({'codice':'GEWISS:GW90007','descrizione':'Quadro — Magnetotermico'}),'')
        self.assertEqual(room_name({'codice':'LIBERA','descrizione':'Manodopera — impianto'}),'')

    def test_limits_and_invalid_numbers(self):
        for data in ({}, {'righe': [None]}, {'righe': [{}] * 5001}):
            with self.assertRaises(ValueError):
                build_quote(data)
        for value in ('nan', 'inf', 'invalid', 1e20):
            data = self.sample(); data['righe'][0]['prezzo'] = value
            with self.assertRaises(ValueError):
                build_quote(data)

    def test_multi_page_and_control_characters(self):
        data = self.sample(); data['cliente']['nome'] = 'A\x00B'
        data['righe'] *= 25
        with zipfile.ZipFile(io.BytesIO(build_quote(data))) as z:
            p = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
            self.assertEqual(p.find(tag('dimension')).get('ref'), 'A1:F21')
            self.assertNotIn(b'\x00', z.read('xl/worksheets/sheet1.xml'))


if __name__ == '__main__':
    unittest.main()
