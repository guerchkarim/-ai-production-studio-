"""Private casting library and bounded, restartable import of Colab voice packages."""
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import threading
import time
import uuid
import wave
import zipfile

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

MAX_PACKAGE = 64 * 1024**2


class InboxIn(BaseModel):
    path: str = Field(min_length=1, max_length=2048)
    enabled: bool = True


class ApprovalIn(BaseModel):
    approved: bool


class UseClipIn(BaseModel):
    project_id: str


def wav_info(blob):
    if len(blob) > 16 * 1024**2:
        raise ValueError('WAV : 16 Mo maximum')
    try:
        with wave.open(io.BytesIO(blob), 'rb') as w:
            rate, channels, width, frames = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
    except (wave.Error, EOFError) as e:
        raise ValueError('WAV invalide') from e
    if not 8000 <= rate <= 192000 or channels not in (1, 2) or not frames or frames*channels*width > len(blob):
        raise ValueError('Format ou durée WAV invalide')
    if frames / rate > 180:
        raise ValueError('Une réplique de casting ne doit pas dépasser 3 minutes')
    return {'duration_sec': frames / rate, 'sample_rate': rate, 'channels': channels}


def parse_package(raw):
    if len(raw) > MAX_PACKAGE:
        raise ValueError('Archive : 64 Mo maximum')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        entries = z.infolist()
        if not entries or len(entries) > 256 or len({e.filename for e in entries}) != len(entries):
            raise ValueError('Archive vide, doublons ou trop de fichiers')
        if sum(e.file_size for e in entries) > 128 * 1024**2:
            raise ValueError('Archive décompressée trop volumineuse')
        files = {}
        for e in entries:
            p = PurePosixPath(e.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in e.filename or ':' in e.filename or len(p.parts) > 2:
                raise ValueError('Chemin d’archive refusé')
            if (e.external_attr >> 16) & 0o170000 == 0o120000 or e.flag_bits & 1:
                raise ValueError('Liens et fichiers chiffrés refusés')
            if e.is_dir():
                continue
            if p.suffix.lower() not in ('.wav', '.json', '.zip'):
                raise ValueError('Le paquet doit contenir seulement les WAV, JSON et ZIP de référence')
            if e.file_size > (100000 if p.suffix.lower() == '.json' else 16*1024**2):
                raise ValueError('Un fichier du paquet est trop volumineux')
            files[e.filename] = e
        manifests = [n for n in files if n.endswith('_reference.json') or n == 'voix.json']
        if len(manifests) != 1:
            raise ValueError('Un seul dossier de voix avec sa fiche de référence est attendu')
        manifest_name = manifests[0]
        metadata = json.loads(z.read(manifest_name))
        if not isinstance(metadata, dict):
            raise ValueError('Fiche de voix invalide')
        profile, variant = metadata.get('profile_id'), metadata.get('variant')
        if not isinstance(profile, str) or not re.fullmatch(r'[FM]-(?:petit|enfant|ado|20|30|40|50|senior)', profile):
            raise ValueError('Profil de voix invalide')
        if isinstance(variant, bool) or not isinstance(variant, int) or not 1 <= variant <= 99:
            raise ValueError('Variante invalide')
        reference_name = manifest_name[:-5]+'.wav' if manifest_name != 'voix.json' else 'reference.wav'
        if reference_name not in files:
            raise ValueError('WAV de référence absent')
        reference = z.read(reference_name)
        ref_sha = hashlib.sha256(reference).hexdigest()
        if ref_sha != metadata.get('reference_sha256'):
            raise ValueError('Empreinte de référence incorrecte')
        ref_info = wav_info(reference)
        if not 3 <= ref_info['duration_sec'] <= 20:
            raise ValueError('Référence vocale : 3 à 20 secondes')
        clips = [{'checksum': ref_sha, 'blob': reference, 'kind': 'reference', 'language': metadata.get('reference_language', 'fr'),
                  'filename': PurePosixPath(reference_name).name, 'metadata': metadata, **ref_info}]
        for name in files:
            if not name.endswith('.wav') or name == reference_name:
                continue
            json_name = name[:-4]+'.json'
            if json_name not in files:
                raise ValueError('Chaque réplique doit avoir son JSON')
            report = json.loads(z.read(json_name))
            if not isinstance(report, dict):
                raise ValueError('Fiche de réplique invalide')
            blob = z.read(name)
            checksum = hashlib.sha256(blob).hexdigest()
            if report.get('reference_sha256') != ref_sha or report.get('audio_sha256') != checksum or report.get('language') not in ('fr', 'ar'):
                raise ValueError('Réplique ou langue incompatible avec la référence')
            clips.append({'checksum': checksum, 'blob': blob, 'kind': 'audition', 'language': report['language'],
                          'filename': PurePosixPath(name).name, 'metadata': report, **wav_info(blob)})
    return profile, variant, ref_sha, metadata, clips


def register(app, db, data, auth, audit, project_exists):
    media = data / 'voice-media'
    packages = data / 'voice-packages'
    inbox = data / 'Voix-a-importer'
    for folder in (media, packages, inbox):
        folder.mkdir(exist_ok=True)
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS voice_profiles(id TEXT PRIMARY KEY,profile TEXT NOT NULL,variant INTEGER NOT NULL,metadata TEXT NOT NULL,approved INTEGER NOT NULL DEFAULT 0,created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS voice_clips(id TEXT PRIMARY KEY,voice_id TEXT NOT NULL REFERENCES voice_profiles(id),checksum TEXT NOT NULL,kind TEXT NOT NULL,language TEXT NOT NULL,filename TEXT NOT NULL,metadata TEXT NOT NULL,duration REAL NOT NULL,created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS voice_imports(checksum TEXT PRIMARY KEY,filename TEXT NOT NULL,status TEXT NOT NULL,error TEXT NOT NULL,created_at REAL NOT NULL);
        INSERT OR IGNORE INTO schema_version VALUES(5);
        ''')
    lock = threading.Lock()
    stop = threading.Event()
    worker = [None]
    seen = {}
    processed = {}

    def config():
        with db() as c:
            row = c.execute("SELECT value FROM settings WHERE key='voice_inbox'").fetchone()
        return json.loads(row['value']) if row else {'path': str(inbox.resolve()), 'enabled': True}

    def import_package(raw, filename):
        package_sha = hashlib.sha256(raw).hexdigest()
        profile, variant, ref, metadata, clips = parse_package(raw)
        with lock, db() as c:
            c.execute('BEGIN IMMEDIATE')
            previous = c.execute('SELECT profile,variant FROM voice_profiles WHERE id=?', (ref,)).fetchone()
            if previous and (previous['profile'] != profile or previous['variant'] != variant):
                raise ValueError('Cette référence appartient déjà à un autre profil ou numéro de variante')
            c.execute('INSERT OR IGNORE INTO voice_profiles VALUES(?,?,?,?,0,?)', (ref, profile, variant, json.dumps(metadata, ensure_ascii=False), time.time()))
            added = 0
            for clip in clips:
                target = media / clip['checksum']
                if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != clip['checksum']:
                    raise ValueError('Un fichier de bibliothèque est corrompu')
                if not target.exists():
                    target.write_bytes(clip['blob'])
                ident = hashlib.sha256((ref+':'+clip['checksum']+':'+clip['kind']+':'+str(clip['language'])).encode()).hexdigest()
                cursor = c.execute('INSERT OR IGNORE INTO voice_clips VALUES(?,?,?,?,?,?,?,?,?)',
                    (ident, ref, clip['checksum'], clip['kind'], str(clip['language']), clip['filename'], json.dumps(clip['metadata'], ensure_ascii=False), clip['duration_sec'], time.time()))
                added += cursor.rowcount
            (packages / (package_sha+'.zip')).write_bytes(raw)
            c.execute('INSERT OR REPLACE INTO voice_imports VALUES(?,?,?,?,?)', (package_sha, Path(filename).name, 'imported', '', time.time()))
            audit(c, 'voice.imported', ref)
        return {'voice_id': ref, 'added_clips': added}

    def scan(force=False):
        cfg = config()
        with db() as c:
            if not c.execute("SELECT 1 FROM settings WHERE key='password'").fetchone():
                return
        if not cfg['enabled']:
            return
        directory = Path(cfg['path'])
        if not directory.is_dir():
            return
        for path in sorted(directory.glob('Studio-Voix-*.zip'))[:2000]:
            if path.is_symlink() or not path.is_file():
                continue
            stat = path.stat()
            stamp = (stat.st_size, stat.st_mtime_ns)
            if processed.get(str(path)) == stamp:
                continue
            if not force and seen.get(str(path)) != stamp:
                seen[str(path)] = stamp
                continue
            if stat.st_size > MAX_PACKAGE:
                continue
            raw = path.read_bytes()
            sha = hashlib.sha256(raw).hexdigest()
            with db() as c:
                done = c.execute('SELECT 1 FROM voice_imports WHERE checksum=?', (sha,)).fetchone()
            if done:
                processed[str(path)] = stamp
                continue
            try:
                import_package(raw, path.name)
            except (ValueError, KeyError, TypeError, zipfile.BadZipFile, EOFError) as e:
                with db() as c:
                    c.execute('INSERT OR REPLACE INTO voice_imports VALUES(?,?,?,?,?)', (sha, path.name, 'failed', str(e)[:250], time.time()))
            processed[str(path)] = stamp

    @app.get('/api/v1/voices', dependencies=[Depends(auth)])
    def list_voices():
        with db() as c:
            voices = [dict(r) for r in c.execute('SELECT * FROM voice_profiles ORDER BY profile,variant,created_at')]
            for v in voices:
                v['metadata'] = json.loads(v['metadata'])
                v['clips'] = [dict(r) for r in c.execute('SELECT id,kind,language,filename,duration FROM voice_clips WHERE voice_id=? ORDER BY kind,created_at', (v['id'],))]
            recent = [dict(r) for r in c.execute('SELECT filename,status,error,created_at FROM voice_imports ORDER BY created_at DESC LIMIT 10')]
        return {'voices': voices, 'inbox': config(), 'recent': recent, 'can_open_folder': os.name == 'nt'}

    @app.post('/api/v1/voices/import', dependencies=[Depends(auth)])
    async def upload(file: UploadFile = File(...)):
        raw = bytearray()
        while chunk := await file.read(1024*1024):
            raw.extend(chunk)
            if len(raw) > MAX_PACKAGE:
                raise HTTPException(413, 'Archive : 64 Mo maximum')
        await file.close()
        try:
            return import_package(bytes(raw), file.filename or 'voix.zip')
        except (ValueError, KeyError, TypeError, zipfile.BadZipFile, EOFError) as e:
            raise HTTPException(422, 'Paquet de voix refusé : '+str(e)[:180]) from e

    @app.get('/api/v1/voices/notebook', dependencies=[Depends(auth)])
    def casting_notebook():
        path = Path(__file__).resolve().parents[2] / 'notebooks/AI_Production_Studio_Casting_Voix_FR_AR.ipynb'
        return FileResponse(path, filename=path.name, media_type='application/x-ipynb+json', headers={'Cache-Control': 'private, no-store'})

    @app.put('/api/v1/voices/inbox', dependencies=[Depends(auth)])
    def set_inbox(body: InboxIn):
        path = Path(body.path).expanduser().resolve()
        if not path.is_dir():
            raise HTTPException(422, 'Choisissez un dossier existant sur le PC du studio')
        document = {'path': str(path), 'enabled': body.enabled}
        with db() as c:
            c.execute("INSERT OR REPLACE INTO settings VALUES('voice_inbox',?)", (json.dumps(document),))
        return document

    @app.post('/api/v1/voices/inbox/scan', dependencies=[Depends(auth)])
    def scan_now():
        scan(force=True)
        return {'status': 'scanned'}

    @app.post('/api/v1/voices/inbox/open', dependencies=[Depends(auth)])
    def open_folder():
        if os.name != 'nt':
            raise HTTPException(409, 'Ouverture de dossier disponible sur Windows uniquement')
        path = Path(config()['path'])
        if not path.is_dir():
            raise HTTPException(409, 'Dossier introuvable')
        os.startfile(str(path))
        return {'status': 'opened'}

    @app.put('/api/v1/voices/{voice_id}/approval', dependencies=[Depends(auth)])
    def approve(voice_id: str, body: ApprovalIn):
        with db() as c:
            if not c.execute('UPDATE voice_profiles SET approved=? WHERE id=?', (int(body.approved), voice_id)).rowcount:
                raise HTTPException(404, 'Voix introuvable')
            audit(c, 'voice.approval_changed', voice_id)
        return {'approved': body.approved}

    @app.get('/api/v1/voices/clips/{clip_id}/content', dependencies=[Depends(auth)])
    def clip_content(clip_id: str):
        with db() as c:
            clip = c.execute('SELECT * FROM voice_clips WHERE id=?', (clip_id,)).fetchone()
        if not clip or not (media / clip['checksum']).is_file():
            raise HTTPException(404, 'Audio introuvable')
        return FileResponse(media / clip['checksum'], media_type='audio/wav', headers={'Cache-Control': 'private, no-store'})

    @app.get('/api/v1/voices/clips/{clip_id}/metadata', dependencies=[Depends(auth)])
    def clip_metadata(clip_id: str):
        with db() as c:
            clip = c.execute('SELECT * FROM voice_clips WHERE id=?', (clip_id,)).fetchone()
        if not clip:
            raise HTTPException(404, 'Fiche audio introuvable')
        return Response(clip['metadata'], media_type='application/json', headers={'Cache-Control': 'private, no-store', 'Content-Disposition': 'attachment; filename="voix-'+clip_id[:12]+'.json"'})

    @app.post('/api/v1/voices/clips/{clip_id}/use', dependencies=[Depends(auth)])
    def use_clip(clip_id: str, body: UseClipIn):
        with db() as c:
            project_exists(c, body.project_id)
            clip = c.execute('SELECT * FROM voice_clips WHERE id=?', (clip_id,)).fetchone()
            if not clip:
                raise HTTPException(404, 'Audio introuvable')
            blob = (media / clip['checksum']).read_bytes()
            if hashlib.sha256(blob).hexdigest() != clip['checksum']:
                raise HTTPException(409, 'Audio de bibliothèque corrompu')
            path = data / 'media' / clip['checksum']
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != clip['checksum']:
                raise HTTPException(409, 'Un média du projet portant cette empreinte est corrompu')
            if not path.exists():
                path.write_bytes(blob)
            existing = c.execute('SELECT id FROM assets WHERE project_id=? AND checksum=?', (body.project_id, clip['checksum'])).fetchone()
            aid = existing['id'] if existing else str(uuid.uuid4())
            if not existing:
                c.execute('INSERT INTO assets VALUES(?,?,?,?,?,?,?,?)', (aid, body.project_id, clip['filename'], 'audio', 'audio/wav', clip['checksum'], len(blob), time.time()))
            audit(c, 'voice.used_in_project', aid)
        return {'asset_id': aid}

    def run():
        while not stop.wait(3):
            try:
                scan()
            except Exception:
                # A folder being moved/disconnected cannot bring down the studio.
                continue

    def startup():
        stop.clear()
        worker[0] = threading.Thread(target=run, daemon=True, name='voice-inbox')
        worker[0].start()

    def shutdown():
        stop.set()
        if worker[0]:
            worker[0].join(timeout=5)

    app.add_event_handler('startup', startup)
    app.add_event_handler('shutdown', shutdown)
    return {'scan': scan, 'import_package': import_package}
