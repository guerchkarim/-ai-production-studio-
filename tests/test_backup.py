import hashlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT=Path(__file__).resolve().parents[1]/'scripts'/'backup.py'

class BackupTests(unittest.TestCase):
    def fixture(self, root):
        source=root/'source'
        (source/'media').mkdir(parents=True)
        blob=b'fixture-media'
        digest=hashlib.sha256(blob).hexdigest()
        (source/'media'/digest).write_bytes(blob)
        with sqlite3.connect(source/'studio.sqlite3') as c:
            c.execute('CREATE TABLE assets(checksum TEXT)')
            c.execute('INSERT INTO assets VALUES(?)',(digest,))
            c.execute('CREATE TABLE sessions(token TEXT)')
            c.execute("INSERT INTO sessions VALUES('temporary-session')")
        return source,digest

    def command(self, *args):
        return subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],capture_output=True,text=True)

    def test_backup_restore_verifies_and_drops_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,digest=self.fixture(root)
            backup=root/'backup';restored=root/'restored'
            self.assertEqual(self.command('backup',backup,'--data',source).returncode,0)
            self.assertEqual(self.command('restore',backup,'--data',restored).returncode,0)
            self.assertEqual((restored/'media'/digest).read_bytes(),b'fixture-media')
            with sqlite3.connect(restored/'studio.sqlite3') as c:
                self.assertEqual(c.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],0)
            self.assertNotEqual(self.command('restore',backup,'--data',restored).returncode,0)

    def test_corrupted_media_blocks_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,digest=self.fixture(root)
            (source/'media'/digest).write_bytes(b'corrupted')
            self.assertNotEqual(self.command('backup',root/'backup','--data',source).returncode,0)
            self.assertFalse((root/'backup').exists())
