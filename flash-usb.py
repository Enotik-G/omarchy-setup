#!/usr/bin/env python3
"""Writes ONLY the previously identified 16 GB UDisk; never selects by /dev/sda name."""
import argparse,hashlib,json,pathlib,re,subprocess,urllib.request,os
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

def main():
    p=argparse.ArgumentParser();p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    d,nodes=target();print('Только это устройство:',d['path'],d['model'],d['serial'],flush=True)
    if a.dry_run:
        print('Проверка завершена; ничего не скачано и не записано.');return
    folder=pathlib.Path.home()/'Downloads/omarchy-installer';folder.mkdir(parents=True,exist_ok=True)
    # Read current x86 ISO URL from the official website, never a third-party mirror.
    with urllib.request.urlopen('https://omarchy.org/',timeout=60) as f:html=f.read().decode()
    urls=re.findall(r'https://iso\.omarchy\.org/omarchy-[^"\s<>]+\.iso',html)
    urls=[u for u in dict.fromkeys(urls) if not re.search(r'(?i)(aarch64|arm64|rc|beta|alpha)',u)]
    if not urls:raise SystemExit('Не удалось найти стабильный x86 ISO на официальном сайте.')
    url=urls[0];filename=url.rsplit('/',1)[1]
    with urllib.request.urlopen(url+'.sha256',timeout=60) as f:checksum=f.read().decode()
    match=re.search(r'\b[0-9a-fA-F]{64}\b',checksum)
    if not match:raise SystemExit('Официальный SHA256 не найден; запись отменена.')
    expected=match.group().lower();iso=folder/filename
    valid=False
    if iso.exists():
        with iso.open('rb') as f:valid=hashlib.file_digest(f,'sha256').hexdigest()==expected
    if not valid:
        part=iso.with_suffix('.iso.download')
        print('Скачивание:',url,flush=True)
        run('curl','--fail','--location','--retry','3','--output',str(part),url)
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
if __name__=='__main__':main()
