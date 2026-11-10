#!/usr/bin/env python3
"""Install official JetBrains binary, isolated pgAdmin, optional Throne."""
import hashlib, json, os, pathlib, subprocess, tarfile, tempfile, urllib.request
H=pathlib.Path.home()
def run(*args): subprocess.run(args,check=True)
def fetch(url):
    if not url.startswith('https://'): raise ValueError('HTTPS required')
    return urllib.request.urlopen(url,timeout=120)
def desktop(name, title, executable):
    p=H/'.local/share/applications'/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(f'[Desktop Entry]\nType=Application\nName={title}\nExec={executable}\nTerminal=false\nCategories=Development;\n')
(H/'.local/bin').mkdir(parents=True,exist_ok=True)
with fetch('https://data.services.jetbrains.com/products/releases?code=IIU&latest=true&type=release') as f:
    release=json.load(f)['IIU'][0]
item=release['downloads']['linux']; version=release['version']
app=H/'.local/opt'/f'idea-{version}'
if not app.exists():
    with tempfile.TemporaryDirectory() as tmp:
        tmp=pathlib.Path(tmp); archive=tmp/'idea.tar.gz'
        with fetch(item['link']) as src,archive.open('wb') as dst:
            import shutil;shutil.copyfileobj(src,dst)
        with fetch(item['checksumLink']) as f: expected=f.read().decode().split()[0]
        with archive.open('rb') as f: actual=hashlib.file_digest(f,'sha256').hexdigest()
        if actual!=expected: raise RuntimeError('JetBrains SHA256 mismatch')
        with tarfile.open(archive) as t: t.extractall(tmp/'unpacked',filter='data')
        roots=list((tmp/'unpacked').iterdir())
        if len(roots)!=1: raise RuntimeError('Unexpected JetBrains archive')
        app.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(roots[0]),app)
launcher=H/'.local/bin/idea'
launcher.write_text('#!/bin/sh\nexec "'+str(app/'bin/idea.sh')+'" "$@"\n');launcher.chmod(0o755)
desktop('enotik-idea.desktop','IntelliJ IDEA',str(launcher))
# Use supported Python in an isolated environment, even when Arch Python is newer.
venv=H/'.local/share/enotik-setup/pgadmin-venv'
if not (venv/'bin/python').exists(): run('uv','venv','--python','3.12',str(venv))
run('uv','pip','install','--python',str(venv/'bin/python'),'pgadmin4','instaloader')
# pgAdmin reads Python config_local.py, not generic shell SERVER_MODE variables.
config=venv/'lib/python3.12/site-packages/pgadmin4/config_local.py'
config.write_text('import os\nSERVER_MODE = False\nDATA_DIR = os.path.expanduser("~/.pgadmin")\nLOG_FILE = os.path.join(DATA_DIR, "pgadmin4.log")\nSQLITE_PATH = os.path.join(DATA_DIR, "pgadmin4.db")\nSESSION_DB_PATH = os.path.join(DATA_DIR, "sessions")\nSTORAGE_DIR = os.path.join(DATA_DIR, "storage")\n')
pg=H/'.local/bin/pgadmin4'
pg.write_text('#!/bin/sh\nexport SERVER_MODE=False\nexport DATA_DIR="$HOME/.pgadmin"\nexec "'+str(venv/'bin/pgadmin4')+'" "$@"\n');pg.chmod(0o755)
desktop('enotik-pgadmin.desktop','pgAdmin 4',str(pg))
insta=H/'.local/bin/instaloader'
if not insta.exists(): insta.symlink_to(venv/'bin/instaloader')
# Arch packages cover Blender/Godot. Throne is an optional AUR application.
import shutil
if shutil.which('yay'): run('yay','-S','--needed','throne-bin')
else: print('Throne: установи throne-bin через AUR; настройки входят в личный архив.')
