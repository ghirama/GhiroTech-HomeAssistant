import pathlib,sys,tempfile,subprocess,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]/'ghiro_preventivi'
sys.path.insert(0,str(ROOT))
from pdf_summary import build_summary

def sample():
    return {'id':42,'titolo':'Impianto elettrico - Residenza Ossana','descrizione':'Riepilogo della configurazione per appartamenti e parti comuni.','cliente':'Cliente dimostrativo\nVia di prova 12 - Ossana','appartamenti':[{'nome':'Appartamento 1','stanze':[{'nome':'Cucina','punti':[['Punti luce','2'],['Comandi','3'],['Prese','6']],'scatole':[{'nome':'Piano di lavoro','serie':'Vimar Arké','moduli':3,'occupati':2,'componenti':[['1','Libero','1'],['2','Presa Schuko','2']],'note':'Presa dedicata agli elettrodomestici.'}],'derivazioni':[{'nome':'Derivazione cucina','quantita':2,'dettagli':'GEWISS GW48004\nIncasso | 152 × 98 × 70 mm\nMisure: Esterne','note':'Sopra la porta.'}]}],'quadri':[{'nome':'Quadro appartamento','dettagli':'400 × 600 × 120 mm | 2 file × 12 moduli | 2 occupati / 22 liberi','componenti':[{'fila':1,'posizione':3,'tipo':'Magnetotermico','moduli':2,'descrizione':'Circuito cucina','codice':'ART-001'}],'note':'Riserva disponibile per ampliamenti.'}]},{'nome':'Parti comuni','stanze':[],'quadri':[]}]}

class SummaryPDFTest(unittest.TestCase):
    def test_full_summary_and_long_rows(self):
        data=sample();data['appartamenti'][0]['stanze'][0]['scatole'][0]['note']='Nota estesa. '*1800+'FINE NOTA'
        with tempfile.TemporaryDirectory() as folder:
            file=pathlib.Path(folder)/'report.pdf';file.write_bytes(build_summary(data,ROOT/'logo.jpg'))
            text=subprocess.check_output(['pdftotext',str(file),'-'],text=True)
            for expected in ['Appartamento 1','Parti comuni','Presa Schuko','ART-001','FINE NOTA','GHIRARDELLI MARCO','Pagina']:
                self.assertIn(expected,text)
            self.assertGreater(text.count('\f'),3)
if __name__=='__main__':unittest.main()
