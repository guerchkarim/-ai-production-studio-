import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('studio_updater', ROOT/'scripts/update_studio.py')
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class UpdateStudioTests(unittest.TestCase):
    def prepare(self, base):
        source, target = base/'new', base/'installed'
        for path, version in [(source,'0.4.0'),(target,'0.3.0')]:
            path.mkdir()
            (path/'package.json').write_text(json.dumps({'name':'ai-production-studio','version':version}))
            (path/'services').mkdir()
        (source/'services/main.py').write_text('new code')
        (target/'services/main.py').write_text('old code')
        (source/'scripts').mkdir()
        shutil.copy2(ROOT/'scripts/backup.py',source/'scripts/backup.py')
        data = target/'.studio-data'
        data.mkdir()
        with sqlite3.connect(data/'studio.sqlite3') as c:
            c.executescript("CREATE TABLE assets(checksum TEXT);CREATE TABLE settings(key TEXT,value TEXT);INSERT INTO settings VALUES('password','preserve-this-hash');")
        (data/'original.wav').write_bytes(b'original audio')
        (target/'.env').write_text('personal configuration')
        return source,target

    def test_update_preserves_data_and_backs_up_old_code(self):
        with tempfile.TemporaryDirectory() as d:
            source,target=self.prepare(Path(d))
            before=hashlib.sha256((target/'.studio-data/studio.sqlite3').read_bytes()).hexdigest()
            saved=updater.apply_update(source,target,check_running=False)
            self.assertEqual((target/'services/main.py').read_text(),'new code')
            self.assertEqual((saved/'code/services/main.py').read_text(),'old code')
            self.assertEqual((target/'.env').read_text(),'personal configuration')
            self.assertEqual(hashlib.sha256((target/'.studio-data/studio.sqlite3').read_bytes()).hexdigest(),before)
            self.assertEqual((saved/'donnees/original.wav').read_bytes(),b'original audio')

    def test_refuses_other_project_and_running_server(self):
        with tempfile.TemporaryDirectory() as d:
            source,target=self.prepare(Path(d))
            arabic=Path(d)/'arabic';arabic.mkdir()
            (arabic/'package.json').write_text(json.dumps({'name':'arabic-placement-test-generator'}))
            with self.assertRaises(ValueError):
                updater.apply_update(source,arabic,check_running=False)
            self.assertEqual(len(list(arabic.iterdir())),1)
            with patch.object(updater.urllib.request,'urlopen') as opening:
                opening.return_value.__enter__.return_value=object()
                with self.assertRaises(ValueError):
                    updater.apply_update(source,target)
            self.assertEqual((target/'services/main.py').read_text(),'old code')


if __name__=='__main__':
    unittest.main()
