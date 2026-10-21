"""Offline, user-mediated Colab exchange. Never provisions a GPU or exposes the API."""
import hashlib
import hmac
import io
import json
import secrets
import time
import uuid
import zipfile
from pathlib import Path

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import Response, FileResponse

CANDIDATES={
 'image':{'model_id':'stabilityai/stable-diffusion-xl-base-1.0','license_note':'CreativeML Open RAIL++-M : lire la fiche officielle et ses restrictions avant usage.','license_url':'https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0'},
 'video':{'model_id':'Wan-AI/Wan2.1-T2V-1.3B-Diffusers','license_note':'Vérifier la licence et les conditions des poids sur la fiche officielle. Compatibilité Colab à mesurer.','license_url':'https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B-Diffusers'},
 'voice':{'model_id':'facebook/mms-tts-fra','license_note':'MMS-TTS : CC-BY-NC 4.0, usage personnel non commercial seulement ; pas de clonage de voix.','license_url':'https://huggingface.co/facebook/mms-tts-fra'}}

def register(app,db,data,auth,audit):
    with db() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS remote_runs(id TEXT PRIMARY KEY,job_id TEXT NOT NULL REFERENCES jobs(id),token_hash TEXT NOT NULL,request TEXT NOT NULL,result TEXT,created_at REAL NOT NULL)''')
        c.execute('INSERT OR IGNORE INTO schema_version VALUES(4)')
    @app.get('/api/v1/colab/notebook',dependencies=[Depends(auth)])
    def notebook():
        path=Path(__file__).resolve().parents[2]/'notebooks'/'AI_Production_Studio_Worker.ipynb'
        return FileResponse(path,filename='AI_Production_Studio_Worker.ipynb',media_type='application/x-ipynb+json',headers={'Cache-Control':'private, no-store'})
    @app.get('/api/v1/colab/capabilities',dependencies=[Depends(auth)])
    def capabilities():return {'mode':'manual-private-files','models':CANDIDATES,'verified_gpu':False}
    @app.post('/api/v1/jobs/{jid}/colab-package',dependencies=[Depends(auth)])
    def package(jid:str):
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
            if not row:raise HTTPException(404,'Demande introuvable')
            if row['status'] in ('completed','canceled'):raise HTTPException(409,'Demande terminée ou annulée')
            candidate=CANDIDATES[row['type']]
            token=secrets.token_urlsafe(32);rid=str(uuid.uuid4())
            doc={'schema_version':1,'job_id':jid,'run_id':rid,'result_token':token,'task_type':row['type'],'prompt':row['prompt'],**candidate,'seed':42,'language':'fr','steps':20,'width':512,'height':512,'duration_sec':5,'max_cost':row['max_cost'],'notice':'Le studio ne loue aucun GPU. Exécution manuelle dans votre session Colab, après vérification de la licence et des ressources. Le coût propre à votre abonnement Colab éventuel n’est pas mesuré.'}
            if row['type']=='image':
                doc.update({'image_profile':'native_photo_1024','width':1024,'height':1024,'steps':35,'guidance_scale':5.5,'negative_prompt':'illustration, painting, drawing, cartoon, CGI, 3d render, plastic texture, wool, felt, knitted texture, blurry, oversaturated, text, watermark'})
            c.execute('INSERT INTO remote_runs(id,job_id,token_hash,request,created_at) VALUES(?,?,?,?,?)',(rid,jid,hashlib.sha256(token.encode()).hexdigest(),json.dumps({k:v for k,v in doc.items() if k!='result_token'},ensure_ascii=False),time.time()))
            c.execute("UPDATE jobs SET status='review',reason='Demande exportée pour Colab. Aucun calcul lancé automatiquement ; import du résultat nécessaire.' WHERE id=?",(jid,))
            audit(c,'colab.package_exported',jid)
        return Response(json.dumps(doc,ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="colab-{jid}.json"','Cache-Control':'no-store'})
    @app.post('/api/v1/jobs/{jid}/colab-result',dependencies=[Depends(auth)])
    async def result(jid:str,file:UploadFile=File(...)):
        raw=bytearray()
        while chunk:=await file.read(1024*1024):
            raw.extend(chunk)
            if len(raw)>100*1024*1024:raise HTTPException(413,'Résultat : 100 Mo maximum')
        await file.close()
        try:
            archive=zipfile.ZipFile(io.BytesIO(raw));entries=archive.infolist()
            if len(entries)!=2 or len({e.filename for e in entries})!=2 or sum(e.file_size for e in entries)>150*1024*1024:raise ValueError('Archive de résultat invalide')
            if archive.getinfo('result.json').file_size>100000:raise ValueError('Manifeste trop volumineux')
            doc=json.loads(archive.read('result.json'))
            filename=doc['filename']
            if filename not in ('output.png','output.mp4','output.wav') or set(archive.namelist())!={'result.json',filename}:raise ValueError('Fichier résultat non pris en charge')
            blob=archive.read(filename)
            checksum=hashlib.sha256(blob).hexdigest()
            if checksum!=doc['checksum']:raise ValueError('Checksum incorrect')
            signatures={'output.png':blob.startswith(b'\x89PNG\r\n\x1a\n'),'output.mp4':blob[4:8]==b'ftyp','output.wav':blob.startswith(b'RIFF') and blob[8:12]==b'WAVE'}
            if not signatures[filename]:raise ValueError('Signature média incorrecte')
            from math import isfinite
            runtime=float(doc.get('runtime_sec',0))
            if not isfinite(runtime) or not 0<=runtime<=86400:raise ValueError('Mesure de temps invalide')
            with db() as c:
                c.execute('BEGIN IMMEDIATE')
                job=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
                run=c.execute('SELECT * FROM remote_runs WHERE id=? AND job_id=?',(doc['run_id'],jid)).fetchone()
                if not job or not run:raise ValueError('Demande ou exécution inconnue')
                if doc['job_id']!=jid or not hmac.compare_digest(run['token_hash'],hashlib.sha256(str(doc['result_token']).encode()).hexdigest()):raise ValueError('Résultat non associé à cette demande')
                expected={'image':'output.png','video':'output.mp4','voice':'output.wav'}[job['type']]
                if filename!=expected:raise ValueError('Type de résultat incompatible')
                request=json.loads(run['request'])
                allowed_model={request['model_id']}
                if job['type']=='voice':allowed_model.add('facebook/mms-tts-ara')
                if doc.get('model_id') not in allowed_model:raise ValueError('Modèle inattendu')
                if not isinstance(doc.get('model_revision'),str) or len(doc['model_revision'])!=40 or any(ch not in '0123456789abcdef' for ch in doc['model_revision']):raise ValueError('Révision modèle manquante ou invalide')
                if run['result']:
                    existing=json.loads(run['result'])
                    if existing.get('checksum')!=checksum:raise HTTPException(409,'Un autre résultat a déjà été importé pour cette exécution')
                    return {'asset_id':existing['asset_id'],'status':'completed','duplicate':True}
                if job['status'] in ('completed','canceled'):raise HTTPException(409,'Demande déjà terminée ou annulée')
                path=data/'media'/checksum
                if not path.exists():path.write_bytes(blob)
                aid=str(uuid.uuid4());mime={'output.png':'image/png','output.mp4':'video/mp4','output.wav':'audio/wav'}[filename]
                media_type='audio' if job['type']=='voice' else job['type']
                c.execute('INSERT INTO assets(id,project_id,name,type,mime,checksum,size,created_at) VALUES(?,?,?,?,?,?,?,?)',(aid,job['project_id'],'Colab-'+jid[:8]+filename[6:],media_type,mime,checksum,len(blob),time.time()))
                saved={k:v for k,v in doc.items() if k!='result_token'};saved['asset_id']=aid
                c.execute('UPDATE remote_runs SET result=? WHERE id=?',(json.dumps(saved,ensure_ascii=False),doc['run_id']))
                c.execute("UPDATE jobs SET status='completed',reason='Résultat Colab importé. Revue humaine et mesure qualité nécessaires. Coût Colab éventuel non mesuré.' WHERE id=?",(jid,));audit(c,'colab.result_imported',jid)
            return {'asset_id':aid,'status':'completed','runtime_sec':runtime}
        except (ValueError,KeyError,TypeError,zipfile.BadZipFile) as error:raise HTTPException(422,'Résultat invalide : '+str(error)[:140]) from error
