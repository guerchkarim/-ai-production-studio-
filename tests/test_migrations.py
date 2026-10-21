import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

class MigrationTests(unittest.TestCase):
    def test_v1_upgrade_is_repeatable_and_keeps_original_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'studio.sqlite3'
            with sqlite3.connect(path) as c:
                c.executescript('''
                CREATE TABLE projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,language TEXT NOT NULL,resolution TEXT NOT NULL,fps INTEGER NOT NULL,budget REAL NOT NULL,created_at REAL NOT NULL);
                INSERT INTO projects VALUES('original-project','Mon film original','AR','1920 × 1080',24,10,123);
                CREATE TABLE characters(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id),name TEXT NOT NULL,description TEXT NOT NULL,voice TEXT NOT NULL,created_at REAL NOT NULL);
                INSERT INTO characters VALUES('original-character','original-project','نور','Description originale','Voix originale',124);
                CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                INSERT INTO settings VALUES('password','test-only-hash-fixture');
                CREATE TABLE sessions(token TEXT PRIMARY KEY,expires REAL NOT NULL);
                INSERT INTO sessions VALUES('test-session',9999999999);
                ''')
            code='from services.api import main; main.migrate_v2()'
            env={**os.environ,'STUDIO_DATA_DIR':tmp}
            for _ in range(2):
                result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
            with sqlite3.connect(path) as c:
                self.assertEqual(c.execute('SELECT name,version FROM projects').fetchone(),('Mon film original',1))
                self.assertEqual(c.execute('SELECT name,version FROM characters').fetchone(),('نور',1))
                self.assertEqual(c.execute('SELECT value FROM settings').fetchone()[0],'test-only-hash-fixture')
                self.assertEqual(c.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],1)
                self.assertEqual(c.execute('SELECT COUNT(*) FROM revisions').fetchone()[0],2)
                self.assertEqual(c.execute('SELECT MAX(version) FROM schema_version').fetchone()[0],4)
                snapshot=json.loads(c.execute("SELECT snapshot FROM revisions WHERE entity_type='characters'").fetchone()[0])
                self.assertEqual(snapshot['description'],'Description originale')
