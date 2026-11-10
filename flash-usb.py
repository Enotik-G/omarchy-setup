#!/usr/bin/env python3
"""Writes ONLY the previously identified 16 GB UDisk; never selects by /dev/sda name."""
import argparse,hashlib,json,pathlib,re,subprocess,os,sys
SERIAL='2601241108580572837513'
def run(*args,**kw):return subprocess.run(args,check=True,**kw)
def target():
    disks=json.loads(run('lsblk','-J','-b','-o','PATH,SIZE,TRAN,RM,MODEL,SERIAL,MOUNTPOINTS',capture_output=True,text=True).stdout)['blockdevices']
    found=[d for d in disks if d.get('serial')==SERIAL]
    if len(found)!=1:raise SystemExit('Не найдена именно твоя UDisk 16 ГБ. Запись отменена.')
    d=found[0]
    if d.get('tran')!='usb' or not d.get('rm') or not 14_000_000_000<int(d['size'])<17_000_000_000:
        raise SystemExit('Параметры флешки изменились; запись отменена.')
    def walk(node):
        yield node
        for child in node.get('children',[]):yield from walk(child)
    nodes=list(walk(d))
    if any(m in ['/','/home','/home/enotik','/boot','/boot/efi'] for n in nodes for m in (n.get('mountpoints') or [])):
        raise SystemExit('На устройстве обнаружена системная точка монтирования. Запись запрещена.')
    return d,nodes

CURL=['curl','--fail','--location','--retry','2','--connect-timeout','20',
      '--proto','=https','--proto-redir','=https',
      '--user-agent','Mozilla/5.0 (X11; Linux x86_64) OmarchyInstaller/1.0']
def fetch_text(url):
    return run(*CURL,'--silent','--show-error','--max-time','90',url,
               capture_output=True,text=True).stdout

def iso_urls(text):
    urls=re.findall(r'https://iso\.omarchy\.org/omarchy-[^"\s<>\\]+\.iso',text)
    return [u for u in dict.fromkeys(urls)
            if re.fullmatch(r'omarchy-\d+(?:\.\d+)+(?:-\d+)?(?:-x86_64)?\.iso',u.rsplit('/',1)[1])]

def resolve_iso():
    try:
        urls=iso_urls(fetch_text('https://omarchy.org/'))
        if urls:return urls[0]
    except (OSError,subprocess.CalledProcessError) as e:
        print('Сайт Omarchy недоступен; проверяю официальный GitHub release.',flush=True)
    release=json.loads(fetch_text('https://api.github.com/repos/omacom/omarchy/releases/latest'))
    if release.get('prerelease') or release.get('draft'):
        raise ValueError('GitHub вернул предварительный релиз вместо стабильного.')
    urls=iso_urls(release.get('body',''))
    if not urls:raise ValueError('В официальном релизе не найдена ссылка на стабильный x86 ISO.')
    return urls[0]

def main():
    p=argparse.ArgumentParser();p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    d,nodes=target();print('Только это устройство:',d['path'],d['model'],d['serial'],flush=True)
    if a.dry_run:
        print('Проверка завершена; ничего не скачано и не записано.');return
    folder=pathlib.Path.home()/'Downloads/omarchy-installer';folder.mkdir(parents=True,exist_ok=True)
    # Use curl consistently, preserving proxy environment and handling HTTP failures.
    url=resolve_iso();filename=url.rsplit('/',1)[1]
    checksum=fetch_text(url+'.sha256')
    match=re.search(r'\b[0-9a-fA-F]{64}\b',checksum)
    if not match:raise SystemExit('Официальный SHA256 не найден; запись отменена.')
    expected=match.group().lower();iso=folder/filename
    valid=False
    if iso.exists():
        with iso.open('rb') as f:valid=hashlib.file_digest(f,'sha256').hexdigest()==expected
    if not valid:
        part=iso.with_suffix('.iso.download')
        print('Скачивание:',url,flush=True)
        run(*CURL,'--output',str(part),url)
        with part.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
        if actual!=expected:raise SystemExit('SHA256 не совпадает; запись отменена.')
        part.replace(iso)
    (folder/(filename+'.sha256')).write_text(expected+'  '+filename+'\n')
    d,nodes=target()
    if iso.stat().st_size>=int(d['size']):raise SystemExit('ISO больше флешки.')
    run('sudo','-v')
    # Unmount partitions only after successful download and checksum verification.
    for n in reversed(nodes):
        if any(n.get('mountpoints') or []):run('sudo','umount',n['path'])
    d,_=target()
    print('Стираю Debian и записываю Omarchy на',d['path'],flush=True)
    run('sudo','dd','if='+str(iso),'of='+d['path'],'bs=4M','status=progress','conv=fsync')
    run('sync')
    run('sudo','cmp','--bytes='+str(iso.stat().st_size),str(iso),d['path'])
    print('ГОТОВО: запись флешки проверена побайтно. ISO:',iso)
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        detail=e.stderr.strip() if isinstance(e,subprocess.CalledProcessError) and e.stderr else str(e)
        print('Ошибка: '+detail+'\nОперация остановлена. Если ошибка возникла при скачивании или проверке ISO, запись флешки ещё не начиналась.',file=sys.stderr)
        sys.exit(1)
