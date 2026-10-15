import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ghiro_preventivi'))
from storage import activate, configure, read_state

class StorageTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.control=self.root/'data';self.control.mkdir()
        self.share=self.root/'share';self.share.mkdir();self.allowed=(self.share,)
        with sqlite3.connect(self.control/'prezzario.sqlite') as c:
            c.execute('CREATE TABLE prova(valore TEXT)');c.execute("INSERT INTO prova VALUES('preventivo originale')")
        for folder in ('documenti','planimetrie','backup_listini'):
            (self.control/folder).mkdir();(self.control/folder/'prova.txt').write_text(folder)
    def tearDown(self):self.tmp.cleanup()
    def test_migration_preserves_all_data_source_and_future_startup(self):
        target=self.share/'archivio'
        configure(self.control,self.control,str(target),self.allowed)
        self.assertEqual(read_state(self.control)['active'],str(self.control))
        with sqlite3.connect(self.control/'prezzario.sqlite') as c:c.execute("INSERT INTO prova VALUES('salvato dopo impostazione')")
        self.assertEqual(activate(self.control,self.allowed),target)
        with sqlite3.connect(target/'prezzario.sqlite') as c:self.assertEqual(c.execute('SELECT count(*) FROM prova').fetchone()[0],2)
        for folder in ('documenti','planimetrie','backup_listini'):
            self.assertEqual((target/folder/'prova.txt').read_text(),folder)
            self.assertTrue((self.control/folder/'prova.txt').exists())
        self.assertTrue((self.control/'prezzario.sqlite').exists())
        self.assertEqual(activate(self.control,self.allowed),target)
        self.assertIsNone(read_state(self.control)['pending'])
    def test_nonempty_external_and_nested_paths_rejected(self):
        target=self.share/'existing';target.mkdir();(target/'keep.txt').write_text('keep')
        for value in (str(target),'/etc/ghiro',str(self.control/'nested'),'relative',str(self.share)):
            with self.assertRaises((ValueError,FileExistsError)):configure(self.control,self.control,value,self.allowed)
        self.assertEqual((target/'keep.txt').read_text(),'keep')
        self.assertFalse((self.control/'storage_settings.json').exists())
    def test_changed_destination_does_not_overwrite_and_keeps_old_archive(self):
        target=self.share/'new';configure(self.control,self.control,str(target),self.allowed)
        (target/'keep.txt').write_text('other file')
        self.assertEqual(activate(self.control,self.allowed),self.control)
        self.assertIn('non più vuota',read_state(self.control)['error'])
        self.assertEqual((target/'keep.txt').read_text(),'other file')
        configure(self.control,self.control,str(self.control),self.allowed)
        self.assertIsNone(read_state(self.control)['pending'])
    def test_missing_active_archive_does_not_initialize_empty_database(self):
        target=self.share/'new';configure(self.control,self.control,str(target),self.allowed);activate(self.control,self.allowed)
        (target/'prezzario.sqlite').unlink()
        with self.assertRaisesRegex(RuntimeError,'non disponibile'):activate(self.control,self.allowed)
        self.assertFalse((target/'prezzario.sqlite').exists())

if __name__=='__main__':unittest.main()
