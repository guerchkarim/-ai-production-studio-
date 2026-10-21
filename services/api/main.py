"""Local control plane. No model download, paid call or GPU provisioning."""
import hashlib
import hmac
import io
import json
import mimetypes
import os
import secrets
import sqlite3
import time
import uuid
import zipfile
from contextlib import contextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

DATA = Path(os.environ.get('STUDIO_DATA_DIR', Path(__file__).resolve().parents[2] / '.studio-data'))
DATA.mkdir(parents=True, exist_ok=True)
(DATA / 'media').mkdir(exist_ok=True)
DB = DATA / 'studio.sqlite3'
MAX_UPLOAD = 50 * 1024 * 1024
TRUSTED_ORIGINS = set(os.environ.get('STUDIO_TRUSTED_ORIGINS', 'http://127.0.0.1:5174,http://localhost:5174').split(','))

@contextmanager
def db():
    conn = sqlite3.connect(DB, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

with db() as c:
    c.executescript('''
    CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
    INSERT OR IGNORE INTO schema_version VALUES (1);
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, expires REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, name TEXT NOT NULL, language TEXT NOT NULL, resolution TEXT NOT NULL, fps INTEGER NOT NULL, budget REAL NOT NULL, created_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS characters(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), name TEXT NOT NULL, description TEXT NOT NULL, voice TEXT NOT NULL, created_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), name TEXT NOT NULL, type TEXT NOT NULL, mime TEXT NOT NULL, checksum TEXT NOT NULL, size INTEGER NOT NULL, created_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), type TEXT NOT NULL, prompt TEXT NOT NULL, status TEXT NOT NULL, reason TEXT NOT NULL, max_cost REAL NOT NULL, actual_cost REAL NOT NULL DEFAULT 0, created_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL, entity_id TEXT NOT NULL, created_at REAL NOT NULL);
    ''')

def migrate_v2():
    """Add versioned records without discarding a v1 database or its media."""
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        for table in ('projects', 'characters'):
            if 'version' not in {row['name'] for row in c.execute(f'PRAGMA table_info({table})')}:
                c.execute(f'ALTER TABLE {table} ADD COLUMN version INTEGER NOT NULL DEFAULT 1')
        c.execute('''CREATE TABLE IF NOT EXISTS revisions(
            entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, version INTEGER NOT NULL,
            snapshot TEXT NOT NULL, created_at REAL NOT NULL,
            PRIMARY KEY(entity_type, entity_id, version))''')
        c.execute('''CREATE TABLE IF NOT EXISTS character_references(
            id TEXT PRIMARY KEY, character_id TEXT NOT NULL REFERENCES characters(id),
            asset_id TEXT NOT NULL REFERENCES assets(id), label TEXT NOT NULL,
            approved INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL,
            UNIQUE(character_id, asset_id, label))''')
        for table in ('projects', 'characters'):
            for row in c.execute(f'SELECT * FROM {table}').fetchall():
                save_revision(c, table, dict(row))
        c.execute('INSERT OR IGNORE INTO schema_version VALUES(2)')


def save_revision(c, entity_type, item):
    c.execute('INSERT OR IGNORE INTO revisions VALUES(?,?,?,?,?)',
              (entity_type, item['id'], item['version'], json.dumps(item, ensure_ascii=False), time.time()))


migrate_v2()
app = FastAPI(title='AI Production Studio', version='0.3.0')

class Password(BaseModel):
    password: str = Field(min_length=10, max_length=256)

class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    language: str = Field(default='FR', pattern='^(FR|AR|FR / AR)$')
    resolution: str = Field(default='1920 × 1080', max_length=40)
    fps: int = Field(default=24, ge=1, le=120)
    budget: float = Field(default=0, ge=0, le=100000, allow_inf_nan=False)

class CharacterIn(BaseModel):
    project_id: str
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=6000)
    voice: str = Field(default='', max_length=120)

class ProjectUpdate(ProjectIn):
    version: int = Field(ge=1)

class CharacterUpdate(CharacterIn):
    version: int = Field(ge=1)

class ReferenceIn(BaseModel):
    asset_id: str
    label: str = Field(default='face', pattern='^(face|profile|three-quarter|full-body|outfit|expression|other)$')
    approved: bool = False

class JobIn(BaseModel):
    project_id: str
    type: str = Field(pattern='^(image|video|voice)$')
    prompt: str = Field(min_length=1, max_length=6000)
    max_cost: float = Field(default=0, ge=0, le=100000, allow_inf_nan=False)


def require_auth(request: Request):
    # Mutating browser requests must be same-origin, including login/bootstrap.
    origin = request.headers.get('origin')
    if request.method not in ('GET', 'HEAD') and origin:
        if origin not in TRUSTED_ORIGINS and origin != str(request.base_url).rstrip('/'):
            raise HTTPException(403, 'Origine refusée')
    token = request.cookies.get('studio_session', '')
    with db() as c:
        found = c.execute('SELECT 1 FROM sessions WHERE token=? AND expires>?', (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
    if not found:
        raise HTTPException(401, 'Connexion requise')


def audit(c, action, entity):
    c.execute('INSERT INTO audit(action,entity_id,created_at) VALUES(?,?,?)', (action, entity, time.time()))


def project_exists(c, project_id):
    if not c.execute('SELECT 1 FROM projects WHERE id=?', (project_id,)).fetchone():
        raise HTTPException(404, 'Projet introuvable')


def as_list(c, table):
    return [dict(r) for r in c.execute(f'SELECT * FROM {table} ORDER BY created_at DESC')]


@app.get('/api/v1/health')
def health():
    return {'status': 'ok', 'version': '0.3.0'}


@app.get('/api/v1/auth/status')
def auth_status(request: Request):
    with db() as c:
        configured = bool(c.execute("SELECT 1 FROM settings WHERE key='password'").fetchone())
    try:
        require_auth(request)
        authenticated = True
    except HTTPException:
        authenticated = False
    return {'configured': configured, 'authenticated': authenticated}


@app.post('/api/v1/auth/login')
def login(body: Password, request: Request, response: Response):
    origin = request.headers.get('origin')
    if origin:
        if origin not in TRUSTED_ORIGINS and origin != str(request.base_url).rstrip('/'):
            raise HTTPException(403, 'Origine refusée')
    # Binding to loopback is mandatory until TLS / remote access is configured.
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        row = c.execute("SELECT value FROM settings WHERE key='password'").fetchone()
        if row:
            salt, expected = row['value'].split(':')
            digest = hashlib.scrypt(body.password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
            if not hmac.compare_digest(digest, expected):
                raise HTTPException(401, 'Mot de passe incorrect')
        else:
            salt = secrets.token_bytes(16)
            digest = hashlib.scrypt(body.password.encode(), salt=salt, n=16384, r=8, p=1).hex()
            c.execute("INSERT INTO settings VALUES('password',?)", (salt.hex() + ':' + digest,))
        token = secrets.token_urlsafe(32)
        c.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
        c.execute('INSERT INTO sessions VALUES(?,?)', (hashlib.sha256(token.encode()).hexdigest(), time.time()+43200))
    response.set_cookie('studio_session', token, httponly=True, samesite='strict', secure=request.url.scheme == 'https', max_age=43200)
    return {'authenticated': True}


@app.post('/api/v1/auth/logout', dependencies=[Depends(require_auth)])
def logout(request: Request, response: Response):
    with db() as c:
        c.execute('DELETE FROM sessions WHERE token=?', (hashlib.sha256(request.cookies.get('studio_session', '').encode()).hexdigest(),))
    response.delete_cookie('studio_session')
    return {'ok': True}


@app.get('/api/v1/studio', dependencies=[Depends(require_auth)])
def studio():
    with db() as c:
        return {key: as_list(c, key) for key in ('projects', 'characters', 'assets', 'jobs', 'character_references')}


@app.post('/api/v1/projects', dependencies=[Depends(require_auth)], status_code=201)
def create_project(body: ProjectIn):
    name = body.name.strip()
    if not name:
        raise HTTPException(422, 'Nom requis')
    item = {'id': str(uuid.uuid4()), **body.model_dump(), 'name': name, 'created_at': time.time(), 'version': 1}
    with db() as c:
        c.execute('INSERT INTO projects(id,name,language,resolution,fps,budget,created_at,version) VALUES(:id,:name,:language,:resolution,:fps,:budget,:created_at,:version)', item)
        save_revision(c, 'projects', item)
        audit(c, 'project.created', item['id'])
    return item


@app.post('/api/v1/characters', dependencies=[Depends(require_auth)], status_code=201)
def create_character(body: CharacterIn):
    if not body.name.strip():
        raise HTTPException(422, 'Nom requis')
    item = {'id': str(uuid.uuid4()), **body.model_dump(), 'name': body.name.strip(), 'created_at': time.time(), 'version': 1}
    with db() as c:
        project_exists(c, body.project_id)
        c.execute('INSERT INTO characters(id,project_id,name,description,voice,created_at,version) VALUES(:id,:project_id,:name,:description,:voice,:created_at,:version)', item)
        save_revision(c, 'characters', item)
        audit(c, 'character.created', item['id'])
    return item


@app.put('/api/v1/projects/{project_id}', dependencies=[Depends(require_auth)])
def update_project(project_id: str, body: ProjectUpdate):
    if not body.name.strip():
        raise HTTPException(422, 'Nom requis')
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        project_exists(c, project_id)
        old = dict(c.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone())
        if old['version'] != body.version:
            raise HTTPException(409, 'Cette fiche a changé. Fermez la fenêtre et rechargez les données avant de réessayer.')
        largest = c.execute("SELECT COALESCE(MAX(max_cost),0) FROM jobs WHERE project_id=? AND status NOT IN ('canceled','completed')", (project_id,)).fetchone()[0]
        spent = c.execute('SELECT COALESCE(SUM(actual_cost),0) FROM jobs WHERE project_id=?', (project_id,)).fetchone()[0]
        if body.budget < max(largest, spent):
            raise HTTPException(409, 'Le budget ne peut pas être inférieur aux dépenses ou aux plafonds des demandes actives. Annulez les demandes concernées avant de le réduire.')
        item = {**old, **body.model_dump(), 'name':body.name.strip(), 'version':old['version']+1}
        c.execute('UPDATE projects SET name=:name,language=:language,resolution=:resolution,fps=:fps,budget=:budget,version=:version WHERE id=:id', item)
        save_revision(c, 'projects', item)
        audit(c, 'project.updated', project_id)
    return item


@app.put('/api/v1/characters/{character_id}', dependencies=[Depends(require_auth)])
def update_character(character_id: str, body: CharacterUpdate):
    if not body.name.strip():
        raise HTTPException(422, 'Nom requis')
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        row = c.execute('SELECT * FROM characters WHERE id=?', (character_id,)).fetchone()
        if not row:
            raise HTTPException(404, 'Personnage introuvable')
        old = dict(row)
        if old['version'] != body.version:
            raise HTTPException(409, 'Cette fiche a changé. Fermez la fenêtre et rechargez les données avant de réessayer.')
        if body.project_id != old['project_id']:
            raise HTTPException(409, 'Un personnage ne peut pas être déplacé dans un autre projet.')
        item = {**old, **body.model_dump(), 'name':body.name.strip(), 'version':old['version']+1}
        c.execute('UPDATE characters SET name=:name,description=:description,voice=:voice,version=:version WHERE id=:id', item)
        save_revision(c, 'characters', item)
        audit(c, 'character.updated', character_id)
    return item


@app.get('/api/v1/{entity_type}/{entity_id}/history', dependencies=[Depends(require_auth)])
def history(entity_type: str, entity_id: str):
    if entity_type not in ('projects', 'characters'):
        raise HTTPException(404, 'Historique introuvable')
    with db() as c:
        if not c.execute(f'SELECT 1 FROM {entity_type} WHERE id=?', (entity_id,)).fetchone():
            raise HTTPException(404, 'Fiche introuvable')
        rows = c.execute('SELECT version,snapshot,created_at FROM revisions WHERE entity_type=? AND entity_id=? ORDER BY version DESC', (entity_type, entity_id)).fetchall()
        return [{'version':r['version'], 'snapshot':json.loads(r['snapshot']), 'created_at':r['created_at']} for r in rows]


@app.post('/api/v1/characters/{character_id}/references', dependencies=[Depends(require_auth)], status_code=201)
def add_reference(character_id: str, body: ReferenceIn):
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        character = c.execute('SELECT project_id FROM characters WHERE id=?', (character_id,)).fetchone()
        asset = c.execute('SELECT project_id,type FROM assets WHERE id=?', (body.asset_id,)).fetchone()
        if not character or not asset:
            raise HTTPException(404, 'Personnage ou image introuvable')
        if asset['project_id'] != character['project_id'] or asset['type'] != 'image':
            raise HTTPException(422, 'Choisissez une image appartenant au même projet que le personnage.')
        existing = c.execute('SELECT * FROM character_references WHERE character_id=? AND asset_id=? AND label=?', (character_id, body.asset_id, body.label)).fetchone()
        if existing:
            if bool(existing['approved']) != body.approved:
                raise HTTPException(409, 'Cette référence existe déjà avec une autre approbation. Sa modification n’est pas disponible dans cette version.')
            return dict(existing)
        item = {'id':str(uuid.uuid4()), 'character_id':character_id, **body.model_dump(), 'created_at':time.time()}
        c.execute('INSERT INTO character_references VALUES(:id,:character_id,:asset_id,:label,:approved,:created_at)', item)
        audit(c, 'character.reference_added', character_id)
    return item


@app.post('/api/v1/assets/upload', dependencies=[Depends(require_auth)], status_code=201)
async def upload(project_id: str, file: UploadFile = File(...)):
    with db() as c:
        project_exists(c, project_id)
    # Only passive media; SVG/HTML and arbitrary executables are not accepted.
    allowed = {'image/png':'image','image/jpeg':'image','image/webp':'image','video/mp4':'video','video/webm':'video','audio/wav':'audio','audio/x-wav':'audio','audio/mpeg':'audio','audio/ogg':'audio'}
    mime = file.content_type or ''
    if mime not in allowed:
        raise HTTPException(415, 'Formats acceptés : PNG, JPEG, WebP, MP4, WebM, WAV, MP3, OGG')
    temp = DATA / 'media' / (str(uuid.uuid4()) + '.part')
    size = 0
    sha = hashlib.sha256()
    try:
        with temp.open('wb') as out:
            while chunk := await file.read(1024*1024):
                size += len(chunk)
                if size > MAX_UPLOAD:
                    raise HTTPException(413, 'Fichier trop volumineux (50 Mo maximum)')
                sha.update(chunk)
                out.write(chunk)
        if not size:
            raise HTTPException(422, 'Fichier vide')
        # Verify signatures independently of the client-provided MIME type.
        with temp.open('rb') as raw:
            head = raw.read(32)
        valid = {'image/png':head.startswith(b'\x89PNG\r\n\x1a\n'), 'image/jpeg':head.startswith(b'\xff\xd8\xff'), 'image/webp':head.startswith(b'RIFF') and head[8:12]==b'WEBP', 'video/mp4':head[4:8]==b'ftyp', 'video/webm':head.startswith(b'\x1aE\xdf\xa3'), 'audio/wav':head.startswith(b'RIFF') and head[8:12]==b'WAVE', 'audio/x-wav':head.startswith(b'RIFF') and head[8:12]==b'WAVE', 'audio/mpeg':head.startswith(b'ID3') or (len(head)>1 and head[0]==255 and head[1]&224==224), 'audio/ogg':head.startswith(b'OggS')}
        if not valid[mime]:
            raise HTTPException(415, 'Signature du média incompatible avec son format')
        checksum = sha.hexdigest()
        target = DATA / 'media' / checksum
        if not target.exists():
            temp.replace(target)
        item = {'id':str(uuid.uuid4()),'project_id':project_id,'name':Path((file.filename or 'media').replace('\\','/')).name[:200], 'type':allowed[mime], 'mime':mime,'checksum':checksum,'size':size,'created_at':time.time()}
        with db() as c:
            c.execute('INSERT INTO assets VALUES(:id,:project_id,:name,:type,:mime,:checksum,:size,:created_at)', item)
            audit(c, 'asset.uploaded', item['id'])
        return item
    finally:
        temp.unlink(missing_ok=True)
        await file.close()


@app.get('/api/v1/assets/{asset_id}/content', dependencies=[Depends(require_auth)])
def media(asset_id: str):
    with db() as c:
        item = c.execute('SELECT * FROM assets WHERE id=?', (asset_id,)).fetchone()
    if not item:
        raise HTTPException(404, 'Média introuvable')
    path = DATA / 'media' / item['checksum']
    if not path.is_file():
        raise HTTPException(404, 'Fichier manquant')
    return FileResponse(path, media_type=item['mime'], headers={'X-Content-Type-Options':'nosniff','Cache-Control':'private, no-store'})


@app.post('/api/v1/jobs', dependencies=[Depends(require_auth)], status_code=201)
def create_job(body: JobIn):
    with db() as c:
        project_exists(c, body.project_id)
        budget = c.execute('SELECT budget FROM projects WHERE id=?', (body.project_id,)).fetchone()['budget']
        if body.max_cost > budget:
            raise HTTPException(409, 'Le plafond de la tâche dépasse le budget du projet')
        item = {'id':str(uuid.uuid4()),**body.model_dump(),'status':'blocked','reason':'Aucun moteur compatible connecté. Aucune génération ni dépense engagée.','actual_cost':0,'created_at':time.time()}
        c.execute('INSERT INTO jobs(id,project_id,type,prompt,status,reason,max_cost,actual_cost,created_at) VALUES(:id,:project_id,:type,:prompt,:status,:reason,:max_cost,:actual_cost,:created_at)',item)
        audit(c, 'job.blocked', item['id'])
    return item


@app.post('/api/v1/jobs/{job_id}/cancel', dependencies=[Depends(require_auth)])
def cancel_job(job_id: str):
    with db() as c:
        row = c.execute('SELECT status FROM jobs WHERE id=?', (job_id,)).fetchone()
        if not row:
            raise HTTPException(404, 'Tâche introuvable')
        if row['status'] == 'completed':
            raise HTTPException(409, 'Tâche déjà terminée')
        c.execute("UPDATE jobs SET status='canceled',reason='Annulée par le propriétaire' WHERE id=?", (job_id,))
        audit(c, 'job.canceled', job_id)
    return {'status':'canceled'}


@app.get('/api/v1/projects/{project_id}/export', dependencies=[Depends(require_auth)])
def export_project(project_id: str):
    with db() as c:
        project_exists(c, project_id)
        project = dict(c.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone())
        manifest = {'schema_version':3,'project':project}
        for table in ('assets','characters','jobs'):
            manifest[table] = [dict(r) for r in c.execute(f'SELECT * FROM {table} WHERE project_id=?',(project_id,))]
        manifest['character_references'] = [dict(r) for r in c.execute('SELECT r.* FROM character_references r JOIN characters ch ON ch.id=r.character_id WHERE ch.project_id=?', (project_id,))]
        manifest['revisions'] = [dict(r) for r in c.execute("SELECT * FROM revisions WHERE (entity_type='projects' AND entity_id=?) OR (entity_type='characters' AND entity_id IN (SELECT id FROM characters WHERE project_id=?)) ORDER BY created_at", (project_id, project_id))]
        for revision in manifest['revisions']:
            revision['snapshot'] = json.loads(revision['snapshot'])
    manifest['production'] = production_snapshot(project_id)
    with db() as c:
        manifest['remote_generations'] = [{'job_id':r['job_id'],'request':json.loads(r['request']),'result':json.loads(r['result']) if r['result'] else None} for r in c.execute('SELECT rr.* FROM remote_runs rr JOIN jobs j ON j.id=rr.job_id WHERE j.project_id=?',(project_id,))]
    archive = io.BytesIO()
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        for checksum in {a['checksum'] for a in manifest['assets']}:
            path = DATA / 'media' / checksum
            if not path.is_file():
                raise HTTPException(409,'Export impossible : un fichier média manque')
            z.write(path,'media/'+checksum)
    archive.seek(0)
    return StreamingResponse(archive, media_type='application/zip', headers={'Content-Disposition':f'attachment; filename="studio-{project_id}.zip"'})

# Registered after core endpoints to keep the control and CPU render modules separate.
from .production import register as register_production
production_snapshot = register_production(app, db, DATA, require_auth, audit, project_exists)
from .restore import register as register_restore
register_restore(app, db, DATA, require_auth, audit, ProjectIn, CharacterIn)

from .colab import register as register_colab
register_colab(app, db, DATA, require_auth, audit)

# A local production build can be served by the same authenticated API origin.
# The static shell contains no user data; all private content remains behind /api.
from fastapi.staticfiles import StaticFiles
_frontend = Path(__file__).resolve().parents[2] / 'dist'
if _frontend.is_dir():
    app.mount('/', StaticFiles(directory=_frontend, html=True), name='studio-web')
