import base64
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ghiro_preventivi"))
from fv_workflow import get_plan, initialize, save_task


class WorkFlowTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.row_factory = sqlite3.Row
        initialize(self.db)

    def task(self, plant):
        return next(task for task in get_plan(self.db, plant) if task["task"] == "comune")

    def test_persists_status_and_attachment_per_plant(self):
        self.assertEqual(len(get_plan(self.db, 1)), 17)
        content = b"protocollo di prova"
        save_task(self.db, 1, {
            "task": "comune", "stato": "In attesa", "scadenza": "2026-12-01",
            "responsabile": "Tecnico", "note": "Protocollo 123",
            "file": {"nome": "ricevuta.pdf", "dati": base64.b64encode(content).decode()},
        })
        task = self.task(1)
        self.assertEqual((task["stato"], task["scadenza"], task["responsabile"], task["note"]),
                         ("In attesa", "2026-12-01", "Tecnico", "Protocollo 123"))
        self.assertEqual(task["file"][0]["nome"], "ricevuta.pdf")
        self.assertEqual(self.db.execute("SELECT dati FROM fv_workflow_files").fetchone()[0], content)
        self.assertEqual(self.task(2)["stato"], "Da fare")
        self.assertEqual(self.task(2)["file"], [])
        initialize(self.db)
        self.assertEqual(self.task(1), task)

    def test_invalid_task_date_and_attachment_are_rejected(self):
        for payload in (
            {"task": "sconosciuta"},
            {"task": "comune", "stato": "In corso", "scadenza": "2026-02-30"},
            {"task": "comune", "stato": "In corso", "file": {"nome": "a.pdf", "dati": "?"}},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                save_task(self.db, 1, payload)
        self.assertEqual(self.task(1)["stato"], "Da fare")
