#!/usr/bin/env python3
import datetime,json,os,pathlib,shutil,sys,tarfile,tempfile
H=pathlib.Path.home()
def merge(src,dst,conflict,rel):
    if dst.is_symlink() or (dst.exists() and not (src.is_dir() and dst.is_dir() and not src.is_symlink())):
        # Existing files are preserved; archive versions remain available for review.
        target=conflict/rel;target.parent.mkdir(parents=True,exist_ok=True)
        if src.is_dir() and not src.is_symlink():shutil.copytree(src,target,symlinks=True)
        else:shutil.copy2(src,target,follow_symlinks=False)
        return
    if src.is_dir() and not src.is_symlink():
        dst.mkdir(parents=True,exist_ok=True)
        for p in src.iterdir():merge(p,dst/p.name,conflict,rel/p.name)
        os.chmod(dst,src.stat().st_mode & 0o777)
    else:
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst,follow_symlinks=False)
def main():
    os.umask(0o077)
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    saved=H/'.local/share/enotik-setup'/stamp;saved.mkdir(parents=True,mode=0o700)
    with tempfile.TemporaryDirectory() as tmp:
        root=pathlib.Path(tmp)
        skipped=[]
        def safe_filter(member,destination):
            try:return tarfile.data_filter(member,destination)
            except (tarfile.AbsoluteLinkError,tarfile.LinkOutsideDestinationError):
                skipped.append(member.name);return None
        with tarfile.open(sys.argv[1],'r:gz') as t:t.extractall(root,filter=safe_filter)
        if skipped:(saved/'skipped-external-symlinks.json').write_text(json.dumps(skipped,indent=2))
        report=json.loads((root/'manifest.json').read_text())
        for p in (root/'home').iterdir():merge(p,H/p.name,saved/'conflicts',pathlib.Path(p.name))
        for name in ['system','reference','manifest.json']:
            p=root/name
            if p.exists():shutil.move(str(p),saved/name)
    # Add saved IDEA settings to the newly installed IDEA release, without overwrites.
    configs=H/'.config/JetBrains';old=configs/'IntelliJIdea2026.2'
    for app in (H/'.local/opt').glob('idea-*'):
        version=app.name.removeprefix('idea-').split('.')
        dest=configs/('IntelliJIdea'+'.'.join(version[:2]))
        if old.exists() and not dest.exists():shutil.copytree(old,dest,symlinks=True)
    # Recreate app launchers with the current user's home, avoiding old absolute paths.
    for name,program in [('moss','Apps/moss-pomodoro/moss.py'),('granat','Apps/moss-pomodoro/moss.py')]:
        if (H/program).exists():
            p=H/'.local/bin'/name;p.parent.mkdir(parents=True,exist_ok=True)
            if not p.is_symlink():p.write_text('#!/bin/sh\nexec /usr/bin/python3 "'+str(H/program)+'" "$@"\n');p.chmod(0o755)
    ase=H/'.local/share/Steam/steamapps/common/Aseprite/aseprite'
    if ase.exists():
        p=H/'.local/share/applications/aseprite-migrated.desktop';p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text('[Desktop Entry]\nType=Application\nName=Aseprite\nExec="'+str(ase)+'"\nTerminal=false\n')
    print('Личные файлы восстановлены. Существующие файлы не перезаписаны.')
    print('Системные дампы, исходные shell-настройки и конфликты:',saved)
    if not report['system_complete']:print('В этой копии НЕТ системных баз и Docker volumes.')
    else:
        import subprocess
        subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('restore-system.py')),str(saved/'system')],check=True)
    print('Открой Firefox через firefox -P и выбери перенесённый профиль. Возможен повторный вход на сайты.')
if __name__=='__main__':main()
