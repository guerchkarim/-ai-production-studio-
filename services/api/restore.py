"""Portable project restore: validate before inserting, clone IDs, never overwrite a project."""
import hashlib
import io
import json
import stat
import sqlite3
import time
import uuid
import zipfile

from fastapi import Depends, File, HTTPException, UploadFile


def register(app,db,data,auth,audit,ProjectIn,CharacterIn):
    @app.post('/api/v1/projects/import',dependencies=[Depends(auth)],status_code=201)
    async def restore(file:UploadFile=File(...)):
        raw=bytearray()
        while chunk:=await file.read(1024*1024):
            raw.extend(chunk)
            if len(raw)>100*1024*1024:raise HTTPException(413,'Archive ZIP : 100 Mo maximum')
        await file.close()
        try:
            archive=zipfile.ZipFile(io.BytesIO(raw))
            entries=archive.infolist()
            if len(entries)>3000 or sum(e.file_size for e in entries)>500*1024*1024:raise ValueError('Archive trop volumineuse après décompression')
            if len({e.filename for e in entries})!=len(entries):raise ValueError('Noms dupliqués dans le ZIP')
            for entry in entries:
                name=entry.filename
                if name.startswith('/') or '..' in name.split('/') or '\\' in name or stat.S_ISLNK(entry.external_attr>>16):raise ValueError('Chemin ou lien interdit dans le ZIP')
            info=archive.getinfo('manifest.json')
            if info.file_size>5*1024*1024:raise ValueError('Manifeste trop volumineux')
            manifest=json.loads(archive.read('manifest.json'))
            if manifest.get('schema_version') not in (1,2,3):raise ValueError('Version de manifeste non prise en charge')
            project=ProjectIn(**manifest['project']).model_dump()
            project['name']=(project['name']+' · restauré')[:120]
            if not project['name'].strip():raise ValueError('Nom du projet manquant')
            assets=manifest.get('assets',[]);characters=manifest.get('characters',[]);refs=manifest.get('character_references',[])
            if not all(isinstance(group,list) for group in (assets,characters,refs)) or len(assets)>2000 or len(characters)>500:raise ValueError('Manifeste invalide')
            identities=[a['id'] for a in assets]+[c['id'] for c in characters]
            if len(set(identities))!=len(identities):raise ValueError('Identifiants dupliqués')
            aid={a['id']:str(uuid.uuid4()) for a in assets};cid={c['id']:str(uuid.uuid4()) for c in characters}
            blobs={}
            allowed={'image/png':'image','image/jpeg':'image','image/webp':'image','video/mp4':'video','video/webm':'video','audio/wav':'audio','audio/x-wav':'audio','audio/mpeg':'audio','audio/ogg':'audio'}
            for asset in assets:
                checksum=asset['checksum']
                if not isinstance(checksum,str) or len(checksum)!=64 or any(ch not in '0123456789abcdef' for ch in checksum):raise ValueError('Checksum invalide')
                if allowed.get(asset['mime'])!=asset['type']:raise ValueError('Type média invalide')
                entry=archive.getinfo('media/'+checksum)
                if entry.file_size>200*1024*1024:raise ValueError('Média trop volumineux')
                blob=archive.read(entry)
                if hashlib.sha256(blob).hexdigest()!=checksum:raise ValueError('Un média est corrompu')
                if not isinstance(asset['name'],str) or len(asset['name'])>200:raise ValueError('Nom de média invalide')
                blobs[checksum]=blob
            valid_names={'manifest.json',*('media/'+checksum for checksum in blobs)}
            if set(e.filename for e in entries)!=valid_names:raise ValueError('Fichiers inattendus dans le ZIP')
            pid=str(uuid.uuid4());now=time.time()
            prepared=[]
            for character in characters:
                item=CharacterIn(**{**character,'project_id':pid}).model_dump()
                if not item['name'].strip():raise ValueError('Nom du personnage vide')
                prepared.append({'id':cid[character['id']],**item,'created_at':now,'version':1})
            for ref in refs:
                if ref['character_id'] not in cid or ref['asset_id'] not in aid or ref['label'] not in ('face','profile','three-quarter','full-body','outfit','expression','other'):raise ValueError('Référence personnage invalide')
                if next(a for a in assets if a['id']==ref['asset_id'])['type']!='image':raise ValueError('Référence non visuelle')
            # Validate production data before entering the write transaction.
            production=manifest.get('production',{})
            script=production.get('script',{}).get('text','')
            if not isinstance(script,str) or len(script)>200000:raise ValueError('Scénario invalide')
            from .production import ShotIn,TimelineIn
            shots=[]
            for i,shot in enumerate(production.get('shots',[])):
                model=ShotIn(**{**shot,'asset_id':aid[shot['asset_id']] if shot.get('asset_id') else None,'version':1})
                shots.append({'id':str(uuid.uuid4()),'project_id':pid,**model.model_dump(),'position':i,'created_at':now})
            timeline=production.get('timeline',{}).get('document',{})
            clips=[{**clip,'asset_id':aid[clip['asset_id']]} for clip in timeline.get('clips',[])]
            audio=aid[timeline['audio_asset_id']] if timeline.get('audio_asset_id') else None
            timeline_doc=TimelineIn(clips=clips,audio_asset_id=audio,version=1).model_dump()
            if sum(c['duration'] for c in clips)>1800:raise ValueError('Montage trop long')
            remapped_types={aid[a['id']]:a['type'] for a in assets}
            if any(remapped_types[s['asset_id']] not in ('image','video') for s in shots if s['asset_id']):raise ValueError('Média de storyboard invalide')
            if any(remapped_types[c['asset_id']] not in ('image','video') for c in clips) or (audio and remapped_types[audio]!='audio'):raise ValueError('Média de montage invalide')
            with db() as c:
                c.execute('BEGIN IMMEDIATE')
                item={'id':pid,**project,'created_at':now,'version':1}
                c.execute('INSERT INTO projects(id,name,language,resolution,fps,budget,created_at,version) VALUES(:id,:name,:language,:resolution,:fps,:budget,:created_at,:version)',item)
                c.execute('INSERT INTO revisions VALUES(?,?,?,?,?)',('projects',pid,1,json.dumps(item,ensure_ascii=False),now))
                for checksum,blob in blobs.items():
                    target=data/'media'/checksum
                    if not target.exists():target.write_bytes(blob)
                for asset in assets:
                    c.execute('INSERT INTO assets(id,project_id,name,type,mime,checksum,size,created_at) VALUES(?,?,?,?,?,?,?,?)',(aid[asset['id']],pid,asset['name'],asset['type'],asset['mime'],asset['checksum'],len(blobs[asset['checksum']]),now))
                for char in prepared:
                    c.execute('INSERT INTO characters(id,project_id,name,description,voice,created_at,version) VALUES(:id,:project_id,:name,:description,:voice,:created_at,:version)',char)
                    c.execute('INSERT INTO revisions VALUES(?,?,?,?,?)',('characters',char['id'],1,json.dumps(char,ensure_ascii=False),now))
                for ref in refs:c.execute('INSERT INTO character_references VALUES(?,?,?,?,?,?)',(str(uuid.uuid4()),cid[ref['character_id']],aid[ref['asset_id']],ref['label'],bool(ref['approved']),now))
                if script:c.execute('INSERT INTO scripts VALUES(?,?,?,?)',(pid,script,1,now))
                for shot in shots:c.execute('INSERT INTO shots VALUES(:id,:project_id,:title,:text,:duration,:asset_id,:approved,:position,:version,:created_at)',shot)
                if clips:c.execute('INSERT INTO timelines VALUES(?,?,?,?)',(pid,json.dumps(timeline_doc),1,now))
                # Preserve the original manifest as read-only provenance, not executable queue state.
                c.execute('INSERT INTO production_history VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),pid,'import',pid,1,json.dumps(manifest,ensure_ascii=False),now))
                audit(c,'project.restored',pid)
            return item
        except (ValueError,KeyError,TypeError,zipfile.BadZipFile,RuntimeError,sqlite3.IntegrityError) as error:
            raise HTTPException(422,'Archive invalide : '+str(error)[:160]) from error
