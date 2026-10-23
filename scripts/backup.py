"""Offline backup/restore. Stop the API first. Never overwrites an existing destination."""
import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('action',choices=['backup','restore'])
parser.add_argument('destination',type=Path)
parser.add_argument('--data',type=Path,default=Path(__file__).resolve().parents[1]/'.studio-data')
args=parser.parse_args()
source,target=(args.data,args.destination) if args.action=='backup' else (args.destination,args.data)
if source.resolve() == target.resolve() or source.resolve() in target.resolve().parents:
    parser.error('La destination doit être hors du dossier source.')
if target.exists():
    parser.error('La destination existe déjà : aucune donnée ne sera écrasée.')
if not (source/'studio.sqlite3').is_file():
    parser.error('Base SQLite source absente.')
with sqlite3.connect(source/'studio.sqlite3') as conn:
    if conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
        parser.error('Base SQLite corrompue.')
    assets=conn.execute('SELECT DISTINCT checksum FROM assets').fetchall()
for (checksum,) in assets:
    path=source/'media'/checksum
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=checksum:
        parser.error('Média absent ou checksum invalide.')
with sqlite3.connect(source/'studio.sqlite3') as conn:
    voice_table=conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='voice_clips'").fetchone()
    if voice_table:
        for (checksum,) in conn.execute('SELECT DISTINCT checksum FROM voice_clips'):
            path=source/'voice-media'/checksum
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=checksum:
                parser.error('Audio de casting absent ou checksum invalide.')
shutil.copytree(source,target)
if args.action=='restore':
    with sqlite3.connect(target/'studio.sqlite3') as conn:
        conn.execute('DELETE FROM sessions')
        conn.commit()
print('Sauvegarde vérifiée.' if args.action=='backup' else 'Restauration vérifiée. Reconnectez-vous avec votre mot de passe.')
