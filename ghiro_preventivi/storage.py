"""Select a persistent data folder; migrate only at startup, retaining the source."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import threading

SETTINGS='storage_settings.json'
OWNED=('prezzario.sqlite','documenti','planimetrie','backup_listini')
_lock=threading.RLock()


def read_state(control):
    control=Path(control).resolve()
    file=control/SETTINGS
    if not file.exists():return {'active':str(control),'pending':None,'error':''}
    state=json.loads(file.read_text())
    if not isinstance(state,dict) or not isinstance(state.get('active'),str):raise ValueError('Impostazioni archivio non valide')
    return state


def write_state(control,state):
    control=Path(control)
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=control,prefix='.storage-',delete=False) as f:
        tmp=Path(f.name)
        try:
            json.dump(state,f,ensure_ascii=False);f.flush();os.fsync(f.fileno())
            os.replace(tmp,control/SETTINGS)
        finally:
            tmp.unlink(missing_ok=True)


def destination(value,control,allowed_roots):
    if not isinstance(value,str) or not value.strip():raise ValueError('Indica una cartella assoluta del server')
    raw=Path(value.strip())
    if not raw.is_absolute() or '..' in raw.parts:raise ValueError('Usa un percorso assoluto senza ..')
    target=raw.resolve()
    if target==Path(control).resolve():return target
    for root in map(Path,allowed_roots):
        if root.is_dir() and target!=root.resolve() and target.is_relative_to(root.resolve()):return target
    raise ValueError('Scegli una sottocartella di /share o /media disponibile in Home Assistant')


def configure(control,active,value,allowed_roots=('/share','/media')):
    with _lock:
        target=destination(value,control,allowed_roots)
        active=Path(active).resolve()
        if target==active:
            state={'active':str(active),'pending':None,'error':''};write_state(control,state);return state
        if target.is_relative_to(active) or active.is_relative_to(target):raise ValueError('La nuova cartella deve essere separata dall’archivio attuale')
        target.mkdir(parents=True,exist_ok=True)
        if any(target.iterdir()):raise ValueError('La cartella di destinazione deve essere vuota: i file esistenti non saranno sovrascritti')
        with tempfile.TemporaryFile(dir=target) as f:f.write(b'ghiro-write-check');f.flush();os.fsync(f.fileno())
        state={'active':str(active),'pending':str(target),'error':''};write_state(control,state);return state


def activate(control,allowed_roots=('/share','/media')):
    control=Path(control).resolve()
    state=read_state(control)
    active=destination(state['active'],control,allowed_roots)
    # Never silently initialize a fresh database when a previously selected mount is missing.
    if active!=control and not (active/'prezzario.sqlite').is_file():raise RuntimeError('Archivio dati non disponibile: ripristina la cartella '+str(active))
    if not state.get('pending'):return active
    stage=None
    try:
        target=destination(state['pending'],control,allowed_roots)
        if target.is_relative_to(active) or active.is_relative_to(target):raise ValueError('Destinazione non separata dalla sorgente')
        if not target.is_dir() or any(target.iterdir()):raise ValueError('Destinazione assente o non più vuota')
        if not (active/'prezzario.sqlite').is_file():raise ValueError('Archivio sorgente non trovato')
        stage=Path(tempfile.mkdtemp(prefix='.ghiro-migration-',dir=target.parent))
        with sqlite3.connect((active/'prezzario.sqlite').as_uri()+'?mode=ro',uri=True) as source:
            with sqlite3.connect(stage/'prezzario.sqlite') as output:
                source.backup(output)
                if output.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Copia del database non valida')
        for name in OWNED[1:]:
            folder=active/name
            if folder.exists():
                if folder.is_symlink() or any(p.is_symlink() for p in folder.rglob('*')):raise ValueError('L’archivio contiene collegamenti simbolici: trasferimento interrotto')
                shutil.copytree(folder,stage/name)
        # Empty target only: rmdir fails if another process added a file meanwhile.
        target.rmdir();os.replace(stage,target);stage=None
        write_state(control,{'active':str(target),'pending':None,'error':''})
        return target
    except Exception as exc:
        if stage and stage.exists():shutil.rmtree(stage)
        state['error']='Trasferimento non eseguito; archivio originale in uso. '+str(exc)
        write_state(control,state)
        return active
