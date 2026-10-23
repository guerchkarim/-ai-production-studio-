"""Vrais paquets du moteur d'archivage ; aucun modèle vocal lancé."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import uuid
import wave
import zipfile

TEST_DATA = tempfile.TemporaryDirectory()
os.environ.setdefault('STUDIO_DATA_DIR', TEST_DATA.name)
from fastapi.testclient import TestClient
from services.api import main

spec = importlib.util.spec_from_file_location('voice_archive', Path(__file__).resolve().parents[1]/'scripts/colab/archiver_voix.py')
archiver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archiver)


def wav(seconds, value):
    b = io.BytesIO()
    with wave.open(b, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(bytes([value, 0])*int(24000*seconds))
    return b.getvalue()


class VoiceLibraryTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.client.post('/api/v1/auth/login', json={'password':'test-only-password-123'})
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def package(self):
        base = Path(self.tmp.name)
        ref = base / uuid.uuid4().hex
        ref.mkdir()
        blob = wav(4, uuid.uuid4().int % 240 + 1)
        (ref/'reference.wav').write_bytes(blob)
        sha = hashlib.sha256(blob).hexdigest()
        (ref/'voix.json').write_text(json.dumps({'schema_version':1,'source_type':'fictional_voice_design','profile_id':'M-petit','variant':2,'reference_sha256':sha,'reference_language':'fr'}))
        audition = ref / 'audition.wav'
        audition.write_bytes(wav(1, 42))
        audition.with_suffix('.json').write_text(json.dumps({'reference_sha256':sha,'language':'ar','audio_sha256':hashlib.sha256(audition.read_bytes()).hexdigest(),'model_revision':'a'*40}))
        _, archive, _ = archiver.save_voice(base/'output', ref, audition)
        return archive.read_bytes(), sha

    def upload(self, raw):
        return self.client.post('/api/v1/voices/import', files={'file':('Studio-Voix-test.zip',raw,'application/zip')})

    def test_import_deduplicate_preserve_approval_and_use_in_project(self):
        raw, sha = self.package()
        result = self.upload(raw)
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['added_clips'],2)
        self.assertEqual(self.upload(raw).json()['added_clips'],0)
        voices = self.client.get('/api/v1/voices').json()['voices']
        voice = next(v for v in voices if v['id']==sha)
        self.assertFalse(voice['approved'])
        self.assertEqual((voice['profile'],voice['variant']),('M-petit',2))
        self.client.put('/api/v1/voices/'+sha+'/approval',json={'approved':True})
        self.upload(raw)
        voice = next(v for v in self.client.get('/api/v1/voices').json()['voices'] if v['id']==sha)
        self.assertTrue(voice['approved'])
        clip = next(c for c in voice['clips'] if c['kind']=='audition')
        self.assertEqual(self.client.get('/api/v1/voices/clips/'+clip['id']+'/content').content,wav(1,42))
        self.assertEqual(self.client.get('/api/v1/voices/clips/'+clip['id']+'/metadata').json()['reference_sha256'],sha)
        project = self.client.post('/api/v1/projects',json={'name':'Casting fixture'}).json()
        use = self.client.post('/api/v1/voices/clips/'+clip['id']+'/use',json={'project_id':project['id']})
        self.assertEqual(use.status_code,200,use.text)
        again = self.client.post('/api/v1/voices/clips/'+clip['id']+'/use',json={'project_id':project['id']})
        self.assertEqual(use.json()['asset_id'],again.json()['asset_id'])
        self.assertEqual(self.client.get('/api/v1/assets/'+use.json()['asset_id']+'/content').content,wav(1,42))

    def test_inbox_waits_for_stable_file_and_imports_only_named_packages(self):
        original = self.client.get('/api/v1/voices').json()['inbox']
        folder = Path(self.tmp.name)/'incoming'
        folder.mkdir()
        raw, sha = self.package()
        (folder/'unrelated.zip').write_bytes(raw)
        self.assertEqual(self.client.put('/api/v1/voices/inbox',json={'path':str(folder),'enabled':True}).status_code,200)
        try:
            main.voice_library['scan'](force=True)
            self.assertFalse(any(v['id']==sha for v in self.client.get('/api/v1/voices').json()['voices']))
            (folder/'Studio-Voix-candidate.zip').write_bytes(raw)
            main.voice_library['scan']()
            self.assertFalse(any(v['id']==sha for v in self.client.get('/api/v1/voices').json()['voices']))
            main.voice_library['scan']()
            self.assertTrue(any(v['id']==sha for v in self.client.get('/api/v1/voices').json()['voices']))
            self.assertTrue((folder/'Studio-Voix-candidate.zip').exists())
        finally:
            self.client.put('/api/v1/voices/inbox',json=original)

    def test_private_and_hostile_archives(self):
        self.assertEqual(TestClient(main.app).get('/api/v1/voices').status_code,401)
        self.assertEqual(TestClient(main.app).get('/api/v1/voices/notebook').status_code,401)
        raw, sha = self.package()
        before = len(self.client.get('/api/v1/voices').json()['voices'])
        bad = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw)) as original, zipfile.ZipFile(bad,'w') as z:
            for name in original.namelist():
                data = original.read(name)
                if name.endswith('_reference.json'):
                    doc=json.loads(data);doc['reference_sha256']='0'*64;data=json.dumps(doc).encode()
                z.writestr(name,data)
            z.writestr('../escape.wav',b'no')
        self.assertEqual(self.upload(bad.getvalue()).status_code,422)
        self.assertEqual(len(self.client.get('/api/v1/voices').json()['voices']),before)
        self.assertFalse((main.DATA/'escape.wav').exists())
        self.assertEqual(self.client.put('/api/v1/voices/inbox',json={'path':str(Path(self.tmp.name)/'absent'),'enabled':True}).status_code,422)


if __name__=='__main__':
    unittest.main()
