"""CPU production tools: script, storyboard, versioned timelines and restartable renders."""
import hashlib
import json
import shutil
import subprocess
import threading
import time
import sys
import uuid
from pathlib import Path

from fastapi import Depends, HTTPException, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

class ScriptIn(BaseModel):
    text: str = Field(max_length=200000)
    version: int = Field(default=0, ge=0)

class ShotIn(BaseModel):
    title: str = Field(min_length=1,max_length=160)
    text: str = Field(default='',max_length=10000)
    duration: float = Field(default=5,ge=0.25,le=120,allow_inf_nan=False)
    asset_id: str | None = None
    approved: bool = False
    version: int = Field(default=0,ge=0)

class Clip(BaseModel):
    asset_id: str
    duration: float = Field(default=5,ge=0.25,le=120,allow_inf_nan=False)
    start: float = Field(default=0,ge=0,le=86400,allow_inf_nan=False)

class TimelineIn(BaseModel):
    clips: list[Clip] = Field(default_factory=list,max_length=200)
    audio_asset_id: str | None = None
    version: int = Field(default=0,ge=0)


def register(app,db,data,auth,audit,project_exists):
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS scripts(project_id TEXT PRIMARY KEY REFERENCES projects(id),text TEXT NOT NULL,version INTEGER NOT NULL,created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS shots(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id),title TEXT NOT NULL,text TEXT NOT NULL,duration REAL NOT NULL,asset_id TEXT REFERENCES assets(id),approved INTEGER NOT NULL,position INTEGER NOT NULL,version INTEGER NOT NULL,created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS timelines(project_id TEXT PRIMARY KEY REFERENCES projects(id),document TEXT NOT NULL,version INTEGER NOT NULL,created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS production_history(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,kind TEXT NOT NULL,entity_id TEXT NOT NULL,version INTEGER NOT NULL,document TEXT NOT NULL,created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS renders(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id),document TEXT NOT NULL,status TEXT NOT NULL,progress REAL NOT NULL DEFAULT 0,error TEXT NOT NULL DEFAULT '',asset_id TEXT REFERENCES assets(id),created_at REAL NOT NULL);
        INSERT OR IGNORE INTO schema_version VALUES(3);
        ''')
    stop=threading.Event()
    signal=threading.Event()
    worker=[None]
    ffmpeg=shutil.which('ffmpeg')
    ffprobe=shutil.which('ffprobe')
    if ffmpeg:
        try:
            encoders=subprocess.check_output([ffmpeg,'-hide_banner','-encoders'],stderr=subprocess.DEVNULL,timeout=10).decode()
            if 'libx264' not in encoders or ' aac ' not in encoders:ffmpeg=None
        except (OSError,subprocess.SubprocessError):ffmpeg=None
    def snapshot(c,pid,kind,eid,version,document):
        c.execute('INSERT INTO production_history VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),pid,kind,eid,version,json.dumps(document,ensure_ascii=False),time.time()))
    def media(c,pid,aid,types):
        a=c.execute('SELECT * FROM assets WHERE id=? AND project_id=?',(aid,pid)).fetchone()
        if not a or a['type'] not in types:
            raise HTTPException(422,'Média incompatible ou appartenant à un autre projet')
        return dict(a)
    def timeline_document(c,pid,body):
        if not body.clips:
            raise HTTPException(422,'Ajoutez au moins un plan au montage')
        if sum(clip.duration for clip in body.clips)>1800:
            raise HTTPException(422,'Durée maximale de cet export CPU : 30 minutes')
        for clip in body.clips:
            media(c,pid,clip.asset_id,('image','video'))
        if body.audio_asset_id:
            media(c,pid,body.audio_asset_id,('audio',))
        return body.model_dump()
    @app.get('/api/v1/production/capabilities',dependencies=[Depends(auth)])
    def capabilities():
        return {'ffmpeg':bool(ffmpeg and ffprobe),'render_resolution':'1280 × 720','max_duration':1800,'ai_generation':False}
    @app.get('/api/v1/projects/{pid}/production',dependencies=[Depends(auth)])
    def get_production(pid:str):
        with db() as c:
            project_exists(c,pid)
            script=c.execute('SELECT * FROM scripts WHERE project_id=?',(pid,)).fetchone()
            timeline=c.execute('SELECT * FROM timelines WHERE project_id=?',(pid,)).fetchone()
            return {'script':dict(script) if script else {'text':'','version':0},'shots':[dict(r) for r in c.execute('SELECT * FROM shots WHERE project_id=? ORDER BY position',(pid,))], 'timeline':{'document':json.loads(timeline['document']),'version':timeline['version']} if timeline else {'document':{'clips':[],'audio_asset_id':None},'version':0},'renders':[dict(r) for r in c.execute('SELECT id,project_id,status,progress,error,asset_id,created_at FROM renders WHERE project_id=? ORDER BY created_at DESC',(pid,))]}
    @app.post('/api/v1/projects/{pid}/script/extract',dependencies=[Depends(auth)])
    async def extract(pid:str,file:UploadFile=File(...)):
        with db() as c:project_exists(c,pid)
        suffix=Path(file.filename or '').suffix.lower()
        if suffix not in ('.pdf','.docx'):raise HTTPException(415,'Choisissez un fichier PDF ou DOCX')
        folder=data/'imports';folder.mkdir(exist_ok=True)
        path=folder/(str(uuid.uuid4())+suffix)
        try:
            size=0
            with path.open('wb') as out:
                while chunk:=await file.read(1024*1024):
                    size+=len(chunk)
                    if size>10*1024*1024:raise HTTPException(413,'Document : 10 Mo maximum')
                    out.write(chunk)
            try:
                result=subprocess.run([sys.executable,str(Path(__file__).with_name('extract_text.py')),str(path)],capture_output=True,timeout=30)
            except subprocess.TimeoutExpired:raise HTTPException(422,'Extraction interrompue après 30 secondes')
            if result.returncode:raise HTTPException(422,'Texte non extractible, PDF chiffré/scanné ou document invalide. Essayez un export texte.')
            return {'text':result.stdout.decode('utf-8'),'method':'Extraction locale, sans IA ni OCR. Vérifiez les retours à la ligne avant sauvegarde.'}
        finally:
            path.unlink(missing_ok=True);await file.close()
    @app.put('/api/v1/projects/{pid}/script',dependencies=[Depends(auth)])
    def save_script(pid:str,body:ScriptIn):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');project_exists(c,pid)
            old=c.execute('SELECT version FROM scripts WHERE project_id=?',(pid,)).fetchone()
            version=old['version'] if old else 0
            if version!=body.version:raise HTTPException(409,'Scénario modifié ailleurs. Rechargez avant de réessayer.')
            item={'text':body.text,'version':version+1}
            c.execute('INSERT INTO scripts VALUES(?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET text=excluded.text,version=excluded.version,created_at=excluded.created_at',(pid,body.text,version+1,time.time()))
            snapshot(c,pid,'script',pid,version+1,item);audit(c,'script.saved',pid)
        return item
    def add_shot(c,pid,body):
        if body.asset_id:media(c,pid,body.asset_id,('image','video'))
        if not body.title.strip():raise HTTPException(422,'Titre requis')
        pos=c.execute('SELECT COALESCE(MAX(position),-1)+1 FROM shots WHERE project_id=?',(pid,)).fetchone()[0]
        item={'id':str(uuid.uuid4()),'project_id':pid,**body.model_dump(),'title':body.title.strip(),'position':pos,'version':1,'created_at':time.time()}
        c.execute('INSERT INTO shots VALUES(:id,:project_id,:title,:text,:duration,:asset_id,:approved,:position,:version,:created_at)',item)
        snapshot(c,pid,'shot',item['id'],1,item)
        return item
    @app.post('/api/v1/projects/{pid}/shots',dependencies=[Depends(auth)],status_code=201)
    def create_shot(pid:str,body:ShotIn):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');project_exists(c,pid)
            item=add_shot(c,pid,body);audit(c,'shot.created',item['id'])
        return item
    @app.post('/api/v1/projects/{pid}/script/split',dependencies=[Depends(auth)])
    def split_script(pid:str):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');project_exists(c,pid)
            script=c.execute('SELECT text FROM scripts WHERE project_id=?',(pid,)).fetchone()
            if not script or not script['text'].strip():raise HTTPException(422,'Enregistrez un scénario avant le découpage')
            if c.execute('SELECT 1 FROM shots WHERE project_id=?',(pid,)).fetchone():raise HTTPException(409,'Un storyboard existe déjà. Le découpage ne remplace pas les plans existants.')
            paragraphs=[p.strip() for p in script['text'].split('\n\n') if p.strip()]
            if len(paragraphs)>200:raise HTTPException(422,'200 paragraphes maximum pour le découpage')
            items=[add_shot(c,pid,ShotIn(title=f'Plan {i+1}',text=p,duration=min(120,max(3,len(p.split())/2.3)))) for i,p in enumerate(paragraphs)]
            audit(c,'storyboard.split',pid)
        return {'shots':items,'method':'Découpage déterministe par paragraphes, sans IA. Durées indicatives à valider.'}
    @app.put('/api/v1/projects/{pid}/shots/{sid}',dependencies=[Depends(auth)])
    def update_shot(pid:str,sid:str,body:ShotIn):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');project_exists(c,pid)
            old=c.execute('SELECT * FROM shots WHERE id=? AND project_id=?',(sid,pid)).fetchone()
            if not old:raise HTTPException(404,'Plan introuvable')
            if old['version']!=body.version:raise HTTPException(409,'Plan modifié ailleurs. Rechargez avant de réessayer.')
            if body.asset_id:media(c,pid,body.asset_id,('image','video'))
            if not body.title.strip():raise HTTPException(422,'Titre requis')
            item={**dict(old),**body.model_dump(),'title':body.title.strip(),'version':old['version']+1}
            c.execute('UPDATE shots SET title=:title,text=:text,duration=:duration,asset_id=:asset_id,approved=:approved,version=:version WHERE id=:id',item)
            snapshot(c,pid,'shot',sid,item['version'],item);audit(c,'shot.updated',sid)
        return item
    @app.put('/api/v1/projects/{pid}/timeline',dependencies=[Depends(auth)])
    def save_timeline(pid:str,body:TimelineIn):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');project_exists(c,pid)
            doc=timeline_document(c,pid,body)
            old=c.execute('SELECT version FROM timelines WHERE project_id=?',(pid,)).fetchone()
            version=old['version'] if old else 0
            if version!=body.version:raise HTTPException(409,'Montage modifié ailleurs. Rechargez avant de réessayer.')
            doc['version']=version+1
            c.execute('INSERT INTO timelines VALUES(?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET document=excluded.document,version=excluded.version,created_at=excluded.created_at',(pid,json.dumps(doc),version+1,time.time()))
            snapshot(c,pid,'timeline',pid,version+1,doc);audit(c,'timeline.saved',pid)
        return {'document':doc,'version':version+1}
    @app.get('/api/v1/projects/{pid}/production/history',dependencies=[Depends(auth)])
    def history(pid:str):
        with db() as c:
            project_exists(c,pid)
            return [{**dict(r),'document':json.loads(r['document'])} for r in c.execute('SELECT * FROM production_history WHERE project_id=? ORDER BY created_at DESC',(pid,))]
    @app.post('/api/v1/projects/{pid}/renders',dependencies=[Depends(auth)],status_code=202)
    def create_render(pid:str):
        if not ffmpeg or not ffprobe:raise HTTPException(503,'FFmpeg et FFprobe sont nécessaires pour exporter une vidéo')
        with db() as c:
            c.execute('BEGIN IMMEDIATE');project_exists(c,pid)
            row=c.execute('SELECT * FROM timelines WHERE project_id=?',(pid,)).fetchone()
            if not row:raise HTTPException(422,'Enregistrez le montage avant export')
            if c.execute("SELECT 1 FROM renders WHERE project_id=? AND status IN ('queued','running')",(pid,)).fetchone():raise HTTPException(409,'Un export de ce projet est déjà en cours')
            doc=timeline_document(c,pid,TimelineIn(**json.loads(row['document'])))
            # Freeze asset checksums and MIME into the render snapshot, never client file paths.
            for clip in doc['clips']:clip['asset']=media(c,pid,clip['asset_id'],('image','video'))
            if doc['audio_asset_id']:doc['audio']=media(c,pid,doc['audio_asset_id'],('audio',))
            item={'id':str(uuid.uuid4()),'project_id':pid,'document':json.dumps(doc),'status':'queued','created_at':time.time()}
            c.execute('INSERT INTO renders(id,project_id,document,status,created_at) VALUES(:id,:project_id,:document,:status,:created_at)',item)
            audit(c,'render.queued',item['id'])
        signal.set()
        return {'id':item['id'],'status':'queued'}
    @app.post('/api/v1/renders/{rid}/cancel',dependencies=[Depends(auth)])
    def cancel(rid:str):
        with db() as c:
            row=c.execute('SELECT status FROM renders WHERE id=?',(rid,)).fetchone()
            if not row:raise HTTPException(404,'Export introuvable')
            if row['status']=='completed':raise HTTPException(409,'Cet export est déjà terminé')
            c.execute("UPDATE renders SET status='canceled' WHERE id=?",(rid,));audit(c,'render.canceled',rid)
        return {'status':'canceled'}
    @app.post('/api/v1/renders/{rid}/retry',dependencies=[Depends(auth)])
    def retry(rid:str):
        if not ffmpeg or not ffprobe:raise HTTPException(503,'FFmpeg indisponible')
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM renders WHERE id=?',(rid,)).fetchone()
            if not row:raise HTTPException(404,'Export introuvable')
            if row['status'] not in ('failed','canceled'):raise HTTPException(409,'Seul un export échoué ou annulé peut être repris')
            if c.execute("SELECT 1 FROM renders WHERE project_id=? AND status IN ('queued','running')",(row['project_id'],)).fetchone():raise HTTPException(409,'Un export est déjà en cours pour ce projet')
            c.execute("UPDATE renders SET status='queued',error='' WHERE id=?",(rid,));audit(c,'render.retried',rid)
        signal.set()
        return {'status':'queued'}
    def active(rid):
        with db() as c:
            row=c.execute('SELECT status FROM renders WHERE id=?',(rid,)).fetchone()
        return row and row['status']=='running' and not stop.is_set()
    def run_command(cmd,rid,timeout=1800):
        # No shell, remote protocols, user-supplied flags or arbitrary output paths.
        logfile=data/'renders'/rid/'ffmpeg.log'
        with logfile.open('wb') as log:
            p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
            start=time.monotonic()
            try:
                while p.poll() is None:
                    if not active(rid):raise InterruptedError('Export interrompu')
                    if time.monotonic()-start>timeout:raise RuntimeError('Limite de temps de rendu atteinte')
                    stop.wait(.1)
                if p.returncode:raise RuntimeError('FFmpeg ne peut pas décoder ou assembler ces médias. Vérifiez leur format et leur durée.')
            finally:
                if p.poll() is None:
                    p.terminate()
                    try:p.wait(timeout=5)
                    except subprocess.TimeoutExpired:p.kill();p.wait()
    def valid_video(path,duration):
        if not path.is_file():return False
        try:
            info=json.loads(subprocess.check_output([ffprobe,'-v','error','-show_format','-show_streams','-of','json',str(path)],timeout=20))
            return any(s['codec_type']=='video' for s in info['streams']) and abs(float(info['format']['duration'])-duration)<.15
        except (subprocess.SubprocessError,ValueError,KeyError):return False
    def execute(row):
        rid=row['id'];doc=json.loads(row['document']);folder=data/'renders'/rid;folder.mkdir(parents=True,exist_ok=True)
        parts=[];duration=0
        for i,clip in enumerate(doc['clips']):
            if not active(rid):raise InterruptedError('Export interrompu')
            asset=clip['asset'];source=data/'media'/asset['checksum']
            if not source.is_file():raise RuntimeError('Un fichier source est manquant')
            duration+=clip['duration']
            digest=hashlib.sha256(json.dumps(clip,sort_keys=True).encode()).hexdigest()[:20]
            part=folder/f'{i:04d}-{digest}.mp4'
            if not valid_video(part,clip['duration']):
                temp=part.with_suffix('.part.mp4')
                cmd=[ffmpeg,'-hide_banner','-loglevel','error','-y','-threads','1','-protocol_whitelist','file,pipe']
                cmd+=['-loop','1','-framerate','24'] if asset['type']=='image' else ['-ss',str(clip['start'])]
                cmd+=['-i',str(source),'-t',str(clip['duration']),'-an','-vf','scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24','-c:v','libx264','-preset','veryfast','-threads','1','-filter_threads','1','-pix_fmt','yuv420p',str(temp)]
                run_command(cmd,rid)
                if not valid_video(temp,clip['duration']):raise RuntimeError('Un clip est trop court ou invalide pour la durée demandée')
                temp.replace(part)
            parts.append(part)
            with db() as c:c.execute("UPDATE renders SET progress=? WHERE id=? AND status='running'",((i+1)/(len(doc['clips'])+1),rid))
        concat=folder/'concat.txt';concat.write_text(''.join("file '"+p.name+"'\n" for p in parts))
        output=folder/'final.mp4'
        cmd=[ffmpeg,'-hide_banner','-loglevel','error','-y','-protocol_whitelist','file,pipe','-f','concat','-safe','1','-i',str(concat)]
        if doc.get('audio'):
            source=data/'media'/doc['audio']['checksum']
            cmd+=['-i',str(source),'-map','0:v:0','-map','1:a:0','-af','apad','-c:a','aac','-b:a','192k']
        cmd+=['-c:v','copy','-t',str(duration),'-movflags','+faststart',str(output)]
        run_command(cmd,rid)
        if not valid_video(output,duration):raise RuntimeError('La validation du MP4 final a échoué')
        digest=hashlib.sha256(output.read_bytes()).hexdigest();target=data/'media'/digest
        if not target.exists():shutil.copyfile(output,target)
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT status FROM renders WHERE id=?',(rid,)).fetchone()['status']!='running':return
            aid=str(uuid.uuid4())
            c.execute('INSERT INTO assets(id,project_id,name,type,mime,checksum,size,created_at) VALUES(?,?,?,?,?,?,?,?)',(aid,row['project_id'],'Montage-'+rid[:8]+'.mp4','video','video/mp4',digest,target.stat().st_size,time.time()))
            c.execute("UPDATE renders SET status='completed',progress=1,asset_id=? WHERE id=?",(aid,rid));audit(c,'render.completed',rid)
    def loop():
        while not stop.is_set():
            row=None
            with db() as c:
                c.execute('BEGIN IMMEDIATE')
                found=c.execute("SELECT * FROM renders WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
                if found:
                    row=dict(found);c.execute("UPDATE renders SET status='running',error='' WHERE id=?",(row['id'],))
            if not row:signal.wait(1);signal.clear();continue
            try:execute(row)
            except InterruptedError:
                with db() as c:c.execute("UPDATE renders SET status='queued' WHERE id=? AND status='running'",(row['id'],))
            except Exception as error:
                with db() as c:c.execute("UPDATE renders SET status='failed',error=? WHERE id=? AND status='running'",(str(error)[:500],row['id']))
    def startup():
        with db() as c:c.execute("UPDATE renders SET status='queued' WHERE status='running'")
        if ffmpeg and ffprobe:
            stop.clear();worker[0]=threading.Thread(target=loop,daemon=True);worker[0].start()
    def shutdown():
        stop.set();signal.set()
        if worker[0]:worker[0].join(timeout=10)
    app.add_event_handler('startup',startup);app.add_event_handler('shutdown',shutdown)
    return get_production
