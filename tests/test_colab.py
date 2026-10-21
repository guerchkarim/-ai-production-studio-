"""Exchange contract tests using synthetic fixtures; these do not validate AI models."""
import hashlib
import io
import json
import struct
import unittest
import zipfile
import zlib
from pathlib import Path
from fastapi.testclient import TestClient
import os
import tempfile
_TEST_DATA = tempfile.TemporaryDirectory()
os.environ['STUDIO_DATA_DIR'] = _TEST_DATA.name
from services.api import main


def fixture_png():
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',2,2,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\x70\x80\x90'*2)*2))+chunk(b'IEND',b'')

class ColabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client=TestClient(main.app)
        cls.client.post('/api/v1/auth/login',json={'password':'test-only-password-123'})
    def prepare(self):
        p=self.client.post('/api/v1/projects',json={'name':'Colab contract fixture'}).json()
        j=self.client.post('/api/v1/jobs',json={'project_id':p['id'],'type':'image','prompt':'Fixture, no AI call'}).json()
        package=self.client.post('/api/v1/jobs/'+j['id']+'/colab-package').json()
        return p,j,package
    def archive(self,packet,**changes):
        blob=fixture_png()
        result={k:packet[k] for k in ('job_id','run_id','result_token','model_id')}
        result.update({'filename':'output.png','checksum':hashlib.sha256(blob).hexdigest(),'model_revision':'a'*40,'runtime_sec':1.2,'parameters':{'fixture':True},**changes})
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as archive:
            archive.writestr('result.json',json.dumps(result));archive.writestr('output.png',blob)
        return out.getvalue()
    def upload(self,job,blob):return self.client.post('/api/v1/jobs/'+job['id']+'/colab-result',files={'file':('result.zip',blob,'application/zip')})
    def test_result_contract_and_duplicate_protection(self):
        p,j,packet=self.prepare();blob=self.archive(packet)
        result=self.upload(j,blob);self.assertEqual(result.status_code,200)
        duplicate=self.upload(j,blob);self.assertEqual(duplicate.status_code,200)
        self.assertEqual(result.json()['asset_id'],duplicate.json()['asset_id'])
        self.assertTrue(duplicate.json()['duplicate'])
        asset=self.client.get('/api/v1/assets/'+result.json()['asset_id']+'/content')
        self.assertEqual(asset.content,fixture_png())
        exported=zipfile.ZipFile(io.BytesIO(self.client.get('/api/v1/projects/'+p['id']+'/export').content))
        manifest=json.loads(exported.read('manifest.json'))
        self.assertEqual(manifest['remote_generations'][0]['result']['model_revision'],'a'*40)
        self.assertNotIn('result_token',json.dumps(manifest))
    def test_wrong_token_checksum_and_model_are_rejected(self):
        p,j,packet=self.prepare()
        for changes in ({'result_token':'wrong'},{'checksum':'0'*64},{'model_id':'unknown'},{'model_revision':'missing'}):
            self.assertEqual(self.upload(j,self.archive(packet,**changes)).status_code,422)
        self.assertEqual(len([a for a in self.client.get('/api/v1/studio').json()['assets'] if a['project_id']==p['id']]),0)
    def test_canceled_request_cannot_import(self):
        p,j,packet=self.prepare()
        self.client.post('/api/v1/jobs/'+j['id']+'/cancel')
        self.assertEqual(self.upload(j,self.archive(packet)).status_code,409)
    def test_notebook_is_private_and_all_code_cells_parse(self):
        self.assertEqual(TestClient(main.app).get('/api/v1/colab/notebook').status_code,401)
        response=self.client.get('/api/v1/colab/notebook');self.assertEqual(response.status_code,200)
        notebook=response.json();self.assertGreaterEqual(len(notebook['cells']),6)
        for cell in notebook['cells']:
            if cell['cell_type']=='code':compile(''.join(cell['source']),'<notebook>','exec')
