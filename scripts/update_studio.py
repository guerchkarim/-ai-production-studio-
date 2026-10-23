"""Appliquer les sources téléchargées à un Studio existant, sans remplacer ses données."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CODE_DIRS = ('apps', 'services', 'scripts', 'notebooks', 'docs', 'tests', '.github')
ROOT_FILES = ('package.json', 'package-lock.json', 'tsconfig.json', 'vite.config.js', 'README.md', '.gitignore', 'Lancer-Studio.cmd', 'Mettre-a-jour-Studio.cmd')
IGNORED = {'.git', '.venv', '.studio-data', '.studio-backups', 'node_modules', '__pycache__', 'dist', '.env'}


def is_studio(path):
    try:
        return json.loads((Path(path)/'package.json').read_text(encoding='utf-8')).get('name') == 'ai-production-studio'
    except (OSError, ValueError):
        return False


def apply_update(source, target, check_running=True):
    source, target = Path(source).resolve(), Path(target).resolve()
    if not is_studio(source) or not is_studio(target):
        raise ValueError('Ce dossier n’est pas AI Production Studio. Aucune modification effectuée.')
    if source == target:
        return None
    if source in target.parents or target in source.parents:
        raise ValueError('Utilisez deux dossiers indépendants pour la mise à jour.')
    if check_running:
        try:
            with urllib.request.urlopen('http://127.0.0.1:8001/api/v1/health', timeout=2):
                raise ValueError('Fermez la fenêtre du Studio en cours avec Ctrl+C, puis relancez la mise à jour.')
        except (OSError, TimeoutError):
            pass
    backup = target/'.studio-backups'/('mise-a-jour-'+time.strftime('%Y%m%d-%H%M%S'))
    if backup.exists():
        raise ValueError('Une sauvegarde porte déjà ce nom. Réessayez dans quelques secondes.')
    backup.mkdir(parents=True)
    data = target/'.studio-data'
    if (data/'studio.sqlite3').is_file():
        subprocess.run([sys.executable, str(source/'scripts/backup.py'), 'backup', str(backup/'donnees'), '--data', str(data)], check=True)
    files = [source/name for name in ROOT_FILES if (source/name).is_file()]
    for directory in CODE_DIRS:
        if (source/directory).is_dir():
            files += [p for p in (source/directory).rglob('*') if p.is_file() and not p.is_symlink() and not (set(p.relative_to(source).parts) & IGNORED)]
    replaced, created = [], []
    try:
        for path in files:
            relative = path.relative_to(source)
            destination = target/relative
            if not destination.resolve().is_relative_to(target):
                raise ValueError('Un chemin de destination sort du dossier du Studio.')
            if destination.exists():
                saved = backup/'code'/relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, saved)
                replaced.append((saved, destination))
            else:
                created.append(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
    except Exception:
        for saved, destination in reversed(replaced):
            shutil.copy2(saved, destination)
        for destination in created:
            destination.unlink(missing_ok=True)
        raise
    return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path)
    args = parser.parse_args()
    target = args.target
    if target is None:
        import tkinter
        from tkinter import filedialog
        window = tkinter.Tk()
        window.withdraw()
        chosen = filedialog.askdirectory(title='Choisissez le dossier actuel de votre AI Production Studio')
        window.destroy()
        if not chosen:
            print('Mise à jour annulée. Aucun fichier modifié.')
            return
        target = Path(chosen)
    saved = apply_update(ROOT, target)
    print('Studio mis à jour. Projets, mot de passe et créations conservés.')
    if saved:
        print('Sauvegarde :', saved)
    print('Dans le dossier habituel, ouvrez Lancer-Studio.cmd pour démarrer la nouvelle version.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
