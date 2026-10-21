import base64
import importlib
import io
import json
import os
import sqlite3
import tempfile
import unittest
import zipfile

ROOT = tempfile.TemporaryDirectory()
os.environ['STUDIO_DATA_DIR'] = ROOT.name
from fastapi.testclient import TestClient
from services.api import main

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jF9sAAAAASUVORK5CYII=')

class StudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(main.app)
        response = cls.client.post('/api/v1/auth/login',json={'password':'test-only-password-123'})
        assert response.status_code == 200

    def project(self, budget=0):
        r = self.client.post('/api/v1/projects',json={'name':'Film éducatif العربية','budget':budget})
        self.assertEqual(r.status_code,201)
        return r.json()

    def test_private_data_requires_session(self):
        guest = TestClient(main.app)
        for endpoint in ('/api/v1/studio','/api/v1/assets/missing/content','/api/v1/projects/missing/export'):
            self.assertEqual(guest.get(endpoint).status_code,401)
        self.assertEqual(guest.post('/api/v1/auth/login',json={'password':'incorrect-password'}).status_code,401)

    def test_cross_origin_mutation_rejected(self):
        r = self.client.post('/api/v1/projects',json={'name':'No'},headers={'origin':'https://other.example'})
        self.assertEqual(r.status_code,403)
        self.assertEqual(self.client.post('/api/v1/auth/login',json={'password':'test-only-password-123'},headers={'origin':'https://other.example'}).status_code,403)

    def test_project_character_survive_new_connection(self):
        p = self.project()
        r = self.client.post('/api/v1/characters',json={'project_id':p['id'],'name':'نور','description':'شخصية أصلية','voice':'العربية'})
        self.assertEqual(r.status_code,201)
        # Reopening the SQLite database emulates a fresh persistence connection.
        with sqlite3.connect(main.DB) as conn:
            name = conn.execute('SELECT name FROM projects WHERE id=?',(p['id'],)).fetchone()[0]
        self.assertEqual(name,'Film éducatif العربية')
        snapshot = self.client.get('/api/v1/studio').json()
        self.assertTrue(any(c['id']==r.json()['id'] for c in snapshot['characters']))

    def test_budget_blocked_job_and_cancel(self):
        p=self.project(2)
        body={'project_id':p['id'],'type':'image','prompt':'Une forêt','max_cost':3}
        self.assertEqual(self.client.post('/api/v1/jobs',json=body).status_code,409)
        body['max_cost']=1
        r=self.client.post('/api/v1/jobs',json=body)
        self.assertEqual(r.status_code,201)
        self.assertEqual(r.json()['status'],'blocked')
        self.assertEqual(r.json()['actual_cost'],0)
        self.assertEqual(self.client.post('/api/v1/jobs/'+r.json()['id']+'/cancel').json()['status'],'canceled')

    def test_upload_deduplicated_and_export_complete(self):
        p=self.project()
        ids=[]
        for _ in range(2):
            r=self.client.post('/api/v1/assets/upload',params={'project_id':p['id']},files={'file':('../../image.png',PNG,'image/png')})
            self.assertEqual(r.status_code,201)
            self.assertEqual(r.json()['name'],'image.png')
            ids.append(r.json()['id'])
        self.assertEqual(self.client.get('/api/v1/assets/'+ids[0]+'/content').content,PNG)
        exported=self.client.get('/api/v1/projects/'+p['id']+'/export')
        self.assertEqual(exported.status_code,200)
        with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
            manifest=json.loads(archive.read('manifest.json'))
            self.assertEqual(len(manifest['assets']),2)
            self.assertEqual(len([n for n in archive.namelist() if n.startswith('media/')]),1)
            asset=manifest['assets'][0]
            self.assertEqual(archive.read('media/'+asset['checksum']),PNG)

    def test_upload_rejects_active_or_disguised_content(self):
        p=self.project()
        for mime in ('text/html','image/svg+xml','image/png'):
            r=self.client.post('/api/v1/assets/upload',params={'project_id':p['id']},files={'file':('bad.png',b'<script>alert(1)</script>',mime)})
            self.assertEqual(r.status_code,415)
        r=self.client.post('/api/v1/characters',json={'project_id':'unknown','name':'Nour'})
        self.assertEqual(r.status_code,404)

    def test_invalid_budget(self):
        self.assertEqual(self.client.post('/api/v1/projects',json={'name':'Bad','budget':-1}).status_code,422)
        self.assertEqual(self.client.post('/api/v1/projects',json={'name':'   '}).status_code,422)

if __name__=='__main__': unittest.main()
