import base64
import json
import pathlib
import tempfile
import unittest
from unittest import mock
import test_saving
from pdf_plan import import_pdf, preview, directory, jpeg_size, MAX_PDF

FIXTURE=pathlib.Path(__file__).parent/'fixtures'/'planimetria.pdf'


class PDFPlanTest(unittest.TestCase):
    def test_real_pdf_page_preview_and_validation(self):
        content=FIXTURE.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            first=import_pdf(folder,'piano.pdf',base64.b64encode(content).decode())
            self.assertEqual(first['pagine'],2);self.assertEqual(first['pagina'],1)
            second=preview(folder,first['id'],2)
            self.assertEqual(second['pagina'],2);self.assertGreater(second['width'],second['height'])
            self.assertLessEqual(max(second['width'],second['height']),2200)
            root=directory(folder,first['id'])
            self.assertEqual((root/'originale.pdf').read_bytes(),content)
            one=(root/'pagina-1.jpg').read_bytes();two=(root/'pagina-2.jpg').read_bytes()
            self.assertNotEqual(one,two)
            self.assertEqual(jpeg_size(two),(second['width'],second['height']))
            with mock.patch('pdf_plan.run',side_effect=AssertionError('cached page was rerendered')):
                self.assertEqual(preview(folder,first['id'],2),second)
            for page in (0,3,True,'1'):
                with self.assertRaises(ValueError):preview(folder,first['id'],page)
            with self.assertRaises(ValueError):directory(folder,'../originale.pdf')
            self.assertEqual(len(list(pathlib.Path(folder).iterdir())),1)

    def test_invalid_and_oversized_pdf_preserve_existing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            for name,data in [('file.dwg',b'AC1027'),('bad.pdf',b'not a PDF'),('broken.pdf',b'%PDF-1.7\ncorrupt')]:
                with self.assertRaises(ValueError):import_pdf(folder,name,base64.b64encode(data).decode())
            with self.assertRaises(ValueError):import_pdf(folder,'large.pdf','A'*(MAX_PDF*2))
            self.assertEqual(list(pathlib.Path(folder).iterdir()),[])


class PDFSavingTest(test_saving.SavingTest):
    # Inherit the isolated server fixture, not the parent test methods.
    test_projects_and_quotes_survive_restart_and_edits=None
    test_origin_and_ingress_restrictions=None
    test_missing_project_is_not_reported_saved=None

    def test_import_page_and_project_persist_after_restart(self):
        status,doc=self.request('/api/planimetrie/import',{'nome':'piano.pdf','contenuto':base64.b64encode(FIXTURE.read_bytes()).decode()})
        self.assertEqual(status,200);self.assertEqual(doc['pagine'],2)
        status,doc=self.request('/api/planimetrie/pagina',{'id':doc['id'],'pagina':2})
        self.assertEqual(status,200)
        rooms=[{'id':'r','name':'Camera','items':[{'id':'p','type':'presa','x':25,'y':35}],
                'planImage':doc['url'],'planDoc':doc}]
        status,result=self.request('/api/configurazioni',{'titolo':'PDF prova','stanze':rooms})
        self.assertEqual(status,200)
        self.stop_server();self.scope=__import__('test_saving').load_app(self.folder);self.start_server()
        reopened=self.request('/api/configurazioni')[1][0]
        self.assertEqual(json.loads(reopened['stanze_json']),rooms)
        import http.client
        connection=http.client.HTTPConnection(self.host)
        connection.request('GET','/'+doc['url']);response=connection.getresponse()
        self.assertEqual(response.status,200);self.assertEqual(response.getheader('Content-Type'),'image/jpeg')
        self.assertTrue(response.read().startswith(b'\xff\xd8'));connection.close()
        self.assertEqual((self.folder/'planimetrie'/doc['id']/'originale.pdf').read_bytes(),FIXTURE.read_bytes())
        self.assertEqual(self.request('/api/planimetrie/pagina',{'id':doc['id'],'pagina':3})[0],400)

if __name__=='__main__':unittest.main()
