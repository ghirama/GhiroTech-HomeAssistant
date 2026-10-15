"""Ephemeral HTTP fixture for browser tests; never uses the live /data database."""
import pathlib
import sys
import tempfile

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tests'))
from test_saving import load_app

with tempfile.TemporaryDirectory(prefix='ghiro-browser-') as folder:
    scope=load_app(pathlib.Path(folder))
    class TestHandler(scope['H']):
        # Only the test server admits localhost; production keeps its Ingress gate.
        def ingress_allowed(self):return True
    scope['ThreadingHTTPServer'](('127.0.0.1',8866),TestHandler).serve_forever()
