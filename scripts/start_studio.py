"""Private local launcher. Installs locked dependencies, builds UI, and serves loopback only."""
import json
import hashlib
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    if sys.version_info<(3,12):raise RuntimeError('Python 3.12 ou plus récent est nécessaire.')
    npm=shutil.which('npm.cmd' if os.name=='nt' else 'npm');node=shutil.which('node')
    if not npm or not node:raise RuntimeError('Installez Node.js LTS 22+ depuis nodejs.org, puis relancez.')
    major=int(subprocess.check_output([node,'--version'],text=True).strip().lstrip('v').split('.')[0])
    if major<22:raise RuntimeError('Node.js 22 ou plus récent est nécessaire.')
    origin='http://127.0.0.1:8001/'
    def health():
        try:
            with urllib.request.urlopen(origin+'api/v1/health',timeout=2) as response:return json.load(response)
        except (urllib.error.URLError,ValueError):return None
    running=health()
    if running and running.get('status')=='ok':
        expected=json.loads((ROOT/'package.json').read_text())['version']
        if running.get('version')!=expected:
            raise RuntimeError('Une ancienne version du serveur est encore ouverte. Arrêtez sa fenêtre avant de relancer la mise à jour.')
        webbrowser.open(origin);print('Votre studio est déjà ouvert.');return
    python=ROOT/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    fresh_venv=not python.exists()
    if fresh_venv:subprocess.run([sys.executable,'-m','venv',str(ROOT/'.venv')],check=True)
    state_path=ROOT/'.studio-setup.json'
    try:state=json.loads(state_path.read_text())
    except (OSError,ValueError):state={}
    def digest(paths):
        sha=hashlib.sha256()
        for path in sorted(paths):sha.update(str(path.relative_to(ROOT)).encode());sha.update(path.read_bytes())
        return sha.hexdigest()
    deps=digest([ROOT/'package-lock.json',ROOT/'services/api/requirements.lock.txt'])
    if fresh_venv or state.get('dependencies')!=deps or not (ROOT/'node_modules').is_dir():
        subprocess.run([str(python),'-m','pip','install','--disable-pip-version-check','-r','services/api/requirements.lock.txt'],cwd=ROOT,check=True)
        subprocess.run([npm,'ci'],cwd=ROOT,check=True)
    frontend=digest([p for p in (ROOT/'apps/web').rglob('*') if p.is_file()]+[ROOT/'vite.config.js',ROOT/'package-lock.json'])
    if state.get('frontend')!=frontend or not (ROOT/'dist/index.html').is_file():
        subprocess.run([npm,'run','build'],cwd=ROOT,check=True)
    state_path.write_text(json.dumps({'dependencies':deps,'frontend':frontend}))
    # Back up the actual data location before any startup schema migration.
    data=Path(os.environ.get('STUDIO_DATA_DIR',ROOT/'.studio-data'))
    if (data/'studio.sqlite3').is_file():
        import sqlite3
        with sqlite3.connect(data/'studio.sqlite3') as conn:
            version=conn.execute('SELECT MAX(version) FROM schema_version').fetchone()[0]
        if version<5:
            destination=ROOT/'.studio-backups'/time.strftime('%Y%m%d-%H%M%S')
            subprocess.run([str(python),'scripts/backup.py','backup',str(destination),'--data',str(data)],cwd=ROOT,check=True)
    print('Démarrage du studio personnel. Aucun service payant ni clé API nécessaire.')
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):print('FFmpeg/FFprobe absents : organisation disponible, export vidéo désactivé.')
    server=subprocess.Popen([str(python),'-m','uvicorn','services.api.main:app','--host','127.0.0.1','--port','8001'],cwd=ROOT)
    try:
        for _ in range(100):
            if server.poll() is not None:raise RuntimeError('Le serveur a quitté avant son démarrage. Consultez son message ci-dessus.')
            ready=health()
            if ready and ready.get('status')=='ok':break
            time.sleep(.1)
        else:raise RuntimeError('Le serveur ne répond pas.')
        webbrowser.open(origin)
        print('Gardez cette fenêtre ouverte. Ctrl+C arrête le serveur sans effacer vos projets.')
        server.wait()
    finally:
        if server.poll() is None:
            server.terminate()
            try:server.wait(timeout=10)
            except subprocess.TimeoutExpired:server.kill();server.wait()

if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:print('\nStudio arrêté. Vos données sont conservées.')
    except (RuntimeError,subprocess.CalledProcessError) as error:print(str(error),file=sys.stderr);sys.exit(1)
