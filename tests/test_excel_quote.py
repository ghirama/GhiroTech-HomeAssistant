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
            self.assertEqual(internal['D18'].findtext(tag('f')), "'Calcolo interno'!E11")
            self.assertEqual(internal['F20'].findtext(tag('f')), 'SUM(F17:F18)')
            self.assertAlmostEqual(float(internal['F22'].findtext(tag('v'))),322.08)
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
