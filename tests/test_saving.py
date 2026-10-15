"""Save/reopen tests against an isolated HTTP server and persistent temporary DB."""
import ast
import http.client
import json
import pathlib
import sys
import tempfile
import threading
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]/'ghiro_preventivi'
sys.path.insert(0,str(ROOT))


def load_app(folder,storage_roots=None):
    tree=ast.parse((ROOT/'app.py').read_text())
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('DATA','CONTROL') for t in node.targets):
            node.value=ast.Call(func=ast.Attribute(value=ast.Name(id='pathlib',ctx=ast.Load()),attr='Path',ctx=ast.Load()),args=[ast.Constant(str(folder))],keywords=[])
    if storage_roots is not None:
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DATA' for t in node.targets):
                node.value=ast.Call(func=ast.Name(id='activate_storage',ctx=ast.Load()),args=[ast.Name(id='CONTROL',ctx=ast.Load())],keywords=[ast.keyword(arg='allowed_roots',value=ast.List(elts=[ast.Constant(str(p)) for p in storage_roots],ctx=ast.Load()))])
    ast.fix_missing_locations(tree)
    scope={'__file__':str(ROOT/'app.py'),'__name__':'isolated_save_test'}
    exec(compile(tree,str(ROOT/'app.py'),'exec'),scope)
    return scope


class SavingTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.folder=pathlib.Path(self.temp.name)
        self.scope=load_app(self.folder)
        self.start_server()

    def start_server(self):
        production=self.scope['H']
        class TestHandler(production):
            # Only this isolated test subclass replaces the TCP-peer gate.
            def ingress_allowed(self):return True
            def log_message(self,*args):pass
        self.server=self.scope['ThreadingHTTPServer'](('127.0.0.1',0),TestHandler)
        self.host='127.0.0.1:'+str(self.server.server_port)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()

    def stop_server(self):
        self.server.shutdown();self.server.server_close();self.thread.join()

    def tearDown(self):
        self.stop_server();self.temp.cleanup()

    def request(self,path,data=None,origin=None):
        connection=http.client.HTTPConnection(self.host)
        headers={}
        if data is not None:
            headers={'Content-Type':'application/json','Origin':origin or 'http://'+self.host}
        connection.request('POST' if data is not None else 'GET',path,
                           json.dumps(data) if data is not None else None,headers)
        response=connection.getresponse();status=response.status;value=json.loads(response.read());connection.close()
        return status,value

    def test_config_description_rename_and_delete(self):
        rooms=[{'nome':'Cucina','scatole':[{'moduli':3,'frutti':['presa']}]}]
        status,saved=self.request('/api/configurazioni',{'titolo':'Impianto','descrizione':'Primo piano','stanze':rooms});self.assertEqual(status,200)
        ident=saved['id']
        status,client=self.request('/api/clienti',{'nome':'Cliente'})
        status,quote=self.request('/api/preventivi',{'cliente_id':client['id'],'cliente':'Cliente','titolo':'Preventivo indipendente','righe':[]});self.assertEqual(status,200)
        self.assertEqual(self.request('/api/configurazioni/rinomina',{'id':ident,'titolo':'Nuovo nome'})[0],200)
        rows=self.request('/api/configurazioni')[1];self.assertEqual(rows[0]['descrizione'],'Primo piano');self.assertEqual(json.loads(rows[0]['stanze_json']),rooms)
        self.assertEqual(self.request('/api/configurazioni',{'id':ident,'titolo':'Nuovo nome','stanze':rooms})[0],200)
        self.stop_server();self.scope=load_app(self.folder);self.start_server()
        self.assertEqual(self.request('/api/configurazioni')[1][0]['descrizione'],'Primo piano')
        self.assertEqual(self.request('/api/configurazioni/elimina',{'id':ident})[0],200)
        self.assertEqual(self.request('/api/configurazioni')[1],[])
        self.assertEqual(self.request('/api/preventivi/'+str(quote['id']))[0],200)
        self.assertEqual(self.request('/api/configurazioni',{'id':ident,'titolo':'Non ricreare','stanze':rooms})[0],404)

    def test_box_presets_persist_and_validate(self):
        data={'nome':'Termostato','serie':'Vimar Arké','scatola':{'moduli':3,'frutti':[None,'termostato2'],'note':'A lato letto'}}
        status,saved=self.request('/api/scatole-preimpostate',data);self.assertEqual(status,200)
        self.assertNotEqual(self.request('/api/scatole-preimpostate',data)[0],200)
        bad={**data,'nome':'Troppo piena','scatola':{'moduli':3,'frutti':['termostato3','presa']}}
        self.assertNotEqual(self.request('/api/scatole-preimpostate',bad)[0],200)
        self.stop_server();self.scope=load_app(self.folder);self.start_server()
        self.assertEqual(self.request('/api/scatole-preimpostate/rinomina',{'id':saved['id'],'nome':'Termostato camera'})[0],200)
        self.assertNotEqual(self.request('/api/scatole-preimpostate/rinomina',{'id':saved['id'],'nome':' '})[0],200)
        rows=self.request('/api/scatole-preimpostate')[1]
        self.assertEqual(rows[0]['nome'],'Termostato camera')
        self.assertNotIn('serie',rows[0]);self.assertEqual(json.loads(rows[0]['scatola_json']),data['scatola'])
        self.assertEqual(self.request('/api/scatole-preimpostate/elimina',{'id':saved['id']})[0],200)
        self.assertEqual(self.request('/api/scatole-preimpostate')[1],[])

    def test_projects_and_quotes_survive_restart_and_edits(self):
        status,client=self.request('/api/clienti',{'nome':'Cliente prova'})
        self.assertEqual(status,200)
        rooms=[{'id':'room1','name':'Camera','items':[{'id':'point1','type':'comando','x':20,'y':30,'series':'Vimar Arké','capacity':3,'fruits':['Interruttore','Presa']}],'planImage':'data:image/png;base64,iVBORw0KGgo='}]
        status,project=self.request('/api/configurazioni',{'cliente_id':client['id'],'titolo':'Progetto prova','stanze':rooms})
        self.assertEqual(status,200)
        rooms[0]['name']='Camera aggiornata'
        status,updated=self.request('/api/configurazioni',{'id':project['id'],'titolo':'Progetto aggiornato','stanze':rooms})
        self.assertEqual(status,200);self.assertEqual(updated['id'],project['id'])
        status,projects=self.request('/api/configurazioni')
        self.assertEqual(len(projects),1);self.assertEqual(projects[0]['cliente_id'],client['id'])
        self.assertEqual(json.loads(projects[0]['stanze_json']),rooms)
        quote={'cliente_id':client['id'],'cliente':'Cliente prova','titolo':'Preventivo prova','ricarico':5,'iva':22,'sconto_materiale':10,
               'righe':[{'codice':'VIMAR:00750','descrizione':'Interruttore','unita':'cad','quantita':10,'prezzo':1.367,'quota_materiale':100}]}
        status,saved=self.request('/api/preventivi',quote);self.assertEqual(status,200)
        quote['id']=saved['id'];quote['righe'][0]['quantita']=20
        status,edited=self.request('/api/preventivi',quote);self.assertEqual(status,200);self.assertEqual(edited['id'],saved['id'])
        self.stop_server();self.scope=load_app(self.folder);self.start_server()
        status,reopened=self.request('/api/preventivi/'+str(saved['id']));self.assertEqual(status,200)
        self.assertEqual(reopened['righe'][0]['prezzo'],1.367);self.assertEqual(reopened['righe'][0]['quantita'],20)
        self.assertEqual(len(self.request('/api/preventivi')[1]),1)
        self.assertEqual(json.loads(self.request('/api/configurazioni')[1][0]['stanze_json']),rooms)

    def test_multiple_apartments_common_areas_and_notes_survive_restart(self):
        apartments=[{'id':'a1','nome':'Appartamento 1'},{'id':'a2','nome':'Appartamento 2'},{'id':'common','nome':'Parti comuni'}]
        rooms=[{'nome':'Ingresso','appartamento_id':a['id'],'scatole':[{'note':'Nota '+a['nome'],'moduli':3,'frutti':['presa']}]} for a in apartments]
        status,project=self.request('/api/configurazioni',{'titolo':'Condominio','stanze':rooms,'appartamenti':apartments})
        self.assertEqual(status,200)
        # Older callers omitting the new field must not erase apartment metadata.
        status,_=self.request('/api/configurazioni',{'id':project['id'],'titolo':'Aggiornato','stanze':rooms})
        self.assertEqual(status,200)
        rows=[{'appartamento':a['nome'],'descrizione':'Ingresso - presa','quantita':2,'prezzo':12.50} for a in apartments]
        status,quote=self.request('/api/preventivi',{'titolo':'Tre zone','righe':rows})
        self.assertEqual(status,200)
        self.stop_server();self.scope=load_app(self.folder);self.start_server()
        project=self.request('/api/configurazioni')[1][0]
        self.assertEqual(json.loads(project['appartamenti_json']),apartments)
        self.assertEqual(json.loads(project['stanze_json']),rooms)
        result=self.request('/api/preventivi/'+str(quote['id']))[1]['righe']
        self.assertEqual([r['appartamento'] for r in result],[a['nome'] for a in apartments])
        self.assertEqual(sum(r['quantita']*r['prezzo'] for r in result),75)
        status,_=self.request('/api/configurazioni',{'appartamenti':apartments+[apartments[0]],'stanze':rooms})
        self.assertEqual(status,400)

    def test_data_folder_restart_keeps_live_records_and_document_downloads(self):
        _,client=self.request('/api/clienti',{'nome':'Cliente archivio'})
        _,project=self.request('/api/configurazioni',{'cliente_id':client['id'],'titolo':'Archivio','stanze':[{'nome':'Cucina','scatole':[{'note':'Frigorifero'}]}]})
        doc_folder=self.scope['DOCS']/str(client['id']);doc_folder.mkdir()
        (doc_folder/'prova.txt').write_text('allegato originale')
        with self.scope['conn']() as c:
            doc=c.execute('INSERT INTO documenti(cliente_id,nome,path) VALUES(?,?,?)',(client['id'],'prova.txt',str(client['id'])+'/prova.txt')).lastrowid
        # Keep the mock mount outside the old data directory, as in production.
        with tempfile.TemporaryDirectory() as mounted:
            target=pathlib.Path(mounted)/'archivio'
            self.scope['configure_storage'](self.folder,self.folder,str(target),(mounted,))
            self.stop_server();self.scope=load_app(self.folder,(mounted,));self.start_server()
            self.assertEqual(self.scope['DATA'],target)
            self.assertEqual(self.request('/api/clienti')[1][0]['nome'],'Cliente archivio')
            self.assertEqual(self.request('/api/configurazioni')[1][0]['id'],project['id'])
            self.assertEqual(self.request('/api/impostazioni/archivio')[1]['active'],str(target))
            connection=http.client.HTTPConnection(self.host);connection.request('GET','/api/download/'+str(doc));response=connection.getresponse()
            self.assertEqual(response.status,200);self.assertEqual(response.read(),b'allegato originale');connection.close()
            self.assertEqual(self.request('/api/configurazioni',{'id':project['id'],'titolo':'Dopo trasferimento','stanze':[]})[0],200)
            self.assertEqual(self.request('/api/configurazioni')[1][0]['titolo'],'Dopo trasferimento')
            self.assertTrue((self.folder/'prezzario.sqlite').exists())

    def test_origin_and_ingress_restrictions(self):
        self.assertEqual(self.request('/api/clienti',{'nome':'HTTP'})[0],200)
        self.assertEqual(self.request('/api/clienti',{'nome':'HTTPS'},origin='https://'+self.host)[0],200)
        self.assertEqual(self.request('/api/clienti',{'nome':'Rejected'},origin='https://foreign.invalid')[0],403)
        self.assertEqual(self.request('/api/clienti',{'nome':'Rejected'},origin='null')[0],403)
        self.assertEqual(len(self.request('/api/clienti')[1]),2)
        fake=type('Peer',(),{'client_address':('127.0.0.1',1)})()
        self.assertFalse(self.scope['H'].ingress_allowed(fake))

    def test_missing_project_is_not_reported_saved(self):
        status,result=self.request('/api/configurazioni',{'id':999,'titolo':'Missing','stanze':[]})
        self.assertEqual(status,404)
        self.assertIn('errore',result)
        self.assertEqual(self.request('/api/configurazioni')[1],[])

if __name__=='__main__':unittest.main()
