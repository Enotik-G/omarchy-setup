#!/usr/bin/env python3
"""Snapshot selected user data; encrypt before any upload. No game/AI app data."""
import argparse, datetime, hashlib, json, os, pathlib, secrets, shutil, sqlite3, subprocess, tarfile
H=pathlib.Path.home(); ROOT=pathlib.Path(__file__).resolve().parent
SELECTED=['IdeaProjects','project','hwSkypro','handGOD','esp','Documents','Pictures',
 'Downloads/site','vibe','https:',
 '.testcontainers.properties','.npmrc','.m2/settings-security.xml','.gradle/gradle.properties',
 '.docker','.aws','.ssh','.gnupg','.gitconfig','.mozilla','.pgadmin','.pki','.m2/settings.xml',
 '.config/JetBrains','.config/nvim','.config/git','.config/gh','.config/pgadmin4',
 '.config/Throne','.config/aseprite','.config/blender','.config/instaloader',
 '.config/instadl','.local/share/keyrings','.local/share/nvim',
 '.local/share/godot','Apps/moss-pomodoro','.local/bin/moss','.local/bin/granat',
 '.local/share/Steam/steamapps/common/Aseprite','.jdks']
def copy_path(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    if src.is_dir() and not src.is_symlink():
        shutil.copytree(src,dst,symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.sock','SingletonSocket'))
    elif src.is_file() or src.is_symlink(): shutil.copy2(src,dst,follow_symlinks=False)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--system-data',type=pathlib.Path)
    parser.add_argument('--list',action='store_true');a=parser.parse_args()
    if a.list:
        print('\n'.join(SELECTED));return
    os.umask(0o077)
    private=ROOT/'private';private.mkdir(exist_ok=True,mode=0o700)
    key=private/'migration.key'
    if not key.exists():key.write_text(secrets.token_urlsafe(48)+'\n')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    out=private/stamp;out.mkdir(mode=0o700);stage=out/'stage';home=stage/'home';home.mkdir(parents=True)
    copied=[]
    for rel in SELECTED:
        src=H/rel
        if src.exists() or src.is_symlink():
            print('Копирование:',rel,flush=True);copy_path(src,home/rel);copied.append(rel)
    # Shell files contain tokens and Debian-specific paths: preserve for reference,
    # do not replace the Omarchy shell automatically.
    for name in ['.bashrc','.profile','.zshrc']:
        if (H/name).exists():copy_path(H/name,stage/'reference'/name)
    # Stabilize copied SQLite databases using SQLite's online backup API.
    sqlite_count=0
    for p in home.rglob('*'):
        if not p.is_file() or p.is_symlink(): continue
        source=H/p.relative_to(home)
        try:
            with p.open('rb') as f: header=f.read(16)
            if header!=b'SQLite format 3\x00':continue
            uri=p.as_uri()+'?mode=ro'
            tmp=p.with_name(p.name+'.consistent')
            print('SQLite:',p.relative_to(home),flush=True)
            import time
            deadline=time.monotonic()+30
            def progress(status,remaining,total):
                if time.monotonic()>deadline:raise TimeoutError('SQLite backup timed out; close the application and retry')
            with sqlite3.connect(uri,uri=True,timeout=10) as src,sqlite3.connect(tmp) as dst:
                src.backup(dst,pages=256,progress=progress)
                if dst.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise RuntimeError('SQLite integrity check failed')
            os.replace(tmp,p)
            for suffix in ['-wal','-shm']:
                side=p.with_name(p.name+suffix)
                if side.exists():side.unlink()
            sqlite_count+=1
        except (sqlite3.Error,OSError) as e:
            raise RuntimeError(f'Не удалось сохранить SQLite: {p.relative_to(home)}') from e
    system_complete=False
    if a.system_data:
        s=a.system_data.resolve()
        report=json.loads((s/'status.json').read_text())
        if not report.get('complete'):raise RuntimeError('Системный экспорт не завершён')
        copy_path(s,stage/'system');system_complete=True
    report={'created':stamp,'source_home':str(H),'copied':copied,'sqlite_backups':sqlite_count,
            'system_complete':system_complete,'excluded':['games','Codex','Claude'],
            'note':'Close browser and IDE and run export again immediately before migration.'}
    (stage/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    archive=out/'payload.tar.gz'
    print('Архивация…',flush=True)
    with tarfile.open(archive,'w:gz',compresslevel=1) as t:
        for p in stage.iterdir(): t.add(p,arcname=p.name)
    gpg_home=private/'gpg';gpg_home.mkdir(mode=0o700,exist_ok=True)
    encrypted=out/'payload.gpg'
    base=['gpg','--no-symkey-cache','--homedir',str(gpg_home),'--batch','--pinentry-mode','loopback','--passphrase-file',str(key)]
    subprocess.run(base+['--symmetric','--cipher-algo','AES256','--output',str(encrypted),str(archive)],check=True)
    # Verify decryption against the original before deleting intermediate files.
    with archive.open('rb') as f:expected=hashlib.file_digest(f,'sha256').hexdigest()
    p=subprocess.Popen(base+['--decrypt',str(encrypted)],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    actual=hashlib.file_digest(p.stdout,'sha256').hexdigest();p.stdout.close()
    if p.wait()!=0 or actual!=expected:raise RuntimeError('Проверка расшифровки не пройдена')
    subprocess.run(['split','-b','1900M','-d','-a','3',str(encrypted),str(out/'payload.gpg.part-')],check=True)
    sums=[]
    for part in sorted(out.glob('payload.gpg.part-*')):
        with part.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        sums.append(f'{digest}  {part.name}\n')
    (out/'SHA256SUMS').write_text(''.join(sums));(out/'status.json').write_text(json.dumps(report,indent=2))
    encrypted.unlink();archive.unlink();shutil.rmtree(stage)
    (private/'LATEST').write_text(str(out)+'\n')
    print('Готово:',out,'\nКлюч (не загружать в GitHub!):',key)
    if not system_complete:print('ВНИМАНИЕ: PostgreSQL и Docker ещё НЕ сохранены.')
if __name__=='__main__':main()
