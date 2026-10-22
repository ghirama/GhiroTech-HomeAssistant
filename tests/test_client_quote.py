"""Customer output must conserve sale totals without exposing component detail."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]/'ghiro_preventivi'
sys.path.insert(0,str(ROOT))
from pdf_client_quote import build_client_quote, summarize_quote, customer_group


def row(**changes):
    return dict({'appartamento':'Appartamento 1','stanza':'Cucina','codice':'VIMAR:SECRET',
        'descrizione':'COMPONENTE RISERVATO','quantita':2,'prezzo':18.91,'quota_materiale':100,
        'gruppo_cliente':{'id':'box1','tipo':'scatola','nome':'Scatola piano lavoro','descrizione':'Vimar Arké · 3 moduli'}},**changes)


def text_pages(data):
    with tempfile.TemporaryDirectory() as folder:
        pdf=Path(folder)/'client.pdf';pdf.write_bytes(build_client_quote(data,ROOT/'logo.jpg'))
        return subprocess.check_output(['pdftotext','-layout',str(pdf),'-']).decode().split('\f')[:-1]


class ClientQuoteTest(unittest.TestCase):
    def test_sale_totals_and_group_identity(self):
        rows=[row(),row(prezzo=12.37,quantita=1),row(prezzo=30,quantita=10,quota_materiale=0,codice='LIBERA',gruppo_cliente=None,descrizione='Manodopera'),row(quantita=0)]
        apartments,vat=summarize_quote({'righe':rows,'iva':22,'ricarico':20,'sconto_materiale':10})
        self.assertAlmostEqual(apartments[0]['totale'],414.2052)
        self.assertAlmostEqual(next(iter(apartments[0]['voci'].values()))['totale'],54.2052)
        self.assertEqual(len(apartments[0]['voci']),2);self.assertEqual(vat,.22)
        copies=[row(),row(stanza='Camera'),row(appartamento='Appartamento 2'),row(gruppo_cliente={**row()['gruppo_cliente'],'id':'box2'})]
        apartments,_=summarize_quote({'righe':copies})
        self.assertEqual([len(a['voci']) for a in apartments],[3,1])
        self.assertAlmostEqual(sum(a['totale'] for a in apartments),4*37.82)

    def test_saved_metadata_and_legacy_recovery(self):
        self.assertEqual(customer_group(row()),customer_group(row(gruppo_cliente=json.dumps(row()['gruppo_cliente']))))
        legacy=row(gruppo_cliente=None,codice='FR-presa',associazione={'contesto':'Cucina — Piano lavoro — Vimar Arké / Bianco'})
        self.assertEqual(customer_group(legacy)['nome'],'Piano lavoro')
        self.assertEqual(customer_group(row(gruppo_cliente=None,descrizione='Cucina — Piano lavoro — Vimar Arké / Bianco — Presa'))['nome'],'Piano lavoro')
        with self.assertRaisesRegex(ValueError,'reimporta'):
            customer_group(row(gruppo_cliente=None,codice='FR-presa'))

    def test_pdf_privacy_and_totals(self):
        pages=text_pages({'righe':[row(),row(prezzo=12.37,quantita=1)],'iva':22,'ricarico':20,'sconto_materiale':10,'cliente':{'nome':'Cliente prova'}})
        self.assertEqual(len(pages),2)
        all_text='\n'.join(pages)
        self.assertIn('Scatola piano lavoro',pages[1]);self.assertIn('54,21',pages[1]);self.assertIn('66,13',pages[0])
        for hidden in ['COMPONENTE RISERVATO','SECRET','18,91','12,37','ricarico','sconto_materiale']:
            self.assertNotIn(hidden,all_text)

    def test_overview_can_use_two_pages_and_never_three(self):
        def data(count):
            return {'righe':[row(appartamento=f'Appartamento {i}') for i in range(1,count+1)],'iva':22}
        pages=text_pages(data(22))
        detail=next(i for i,p in enumerate(pages) if 'Dettaglio per stanza' in p)
        self.assertEqual(detail,2)
        self.assertIn('TOTALE PREVENTIVO',pages[1])
        with self.assertRaisesRegex(ValueError,'supera due pagine'):
            build_client_quote(data(70),ROOT/'logo.jpg')

if __name__=='__main__':unittest.main()
