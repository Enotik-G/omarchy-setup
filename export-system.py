#!/usr/bin/env python3
"""Run from normal host terminal; sudo is requested there, never store passwords."""
import json, os, pathlib, subprocess, datetime
ROOT=pathlib.Path(__file__).resolve().parent
os.umask(0o077)
out=ROOT/'private'/('system-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
out.mkdir(parents=True,mode=0o700)
def run(*args,**kw):return subprocess.run(args,check=True,**kw)
run('sudo','-v')
# PostgreSQL: logical backup per Debian cluster. Temporarily start down clusters.
clusters=json.loads(run('pg_lsclusters','--json',capture_output=True,text=True).stdout)
for c in clusters:
    ver=str(c['version']); name=c['cluster'];port=str(c['port']);started=c['status']=='down'
    if started:run('sudo','pg_ctlcluster',ver,name,'start')
    try:
        with (out/f'postgres-{ver}-{name}.sql').open('wb') as f:
            run('sudo','-u','postgres','pg_dumpall','-p',port,stdout=f)
    finally:
        if started:run('sudo','pg_ctlcluster',ver,name,'stop')
# Require quiescent containers; never silently stop the user's applications.
running=run('sudo','docker','ps','-q',capture_output=True,text=True).stdout.strip()
if running:raise SystemExit('Есть работающие контейнеры. Останови их штатно, затем повтори экспорт. PostgreSQL уже выгружен в '+str(out))
containers=[]
ids=run('sudo','docker','ps','-aq',capture_output=True,text=True).stdout.split()
if ids:containers=json.loads(run('sudo','docker','inspect',*ids,capture_output=True,text=True).stdout)
(out/'docker-containers.json').write_text(json.dumps(containers,indent=2))
volumes=run('sudo','docker','volume','ls','-q',capture_output=True,text=True).stdout.split()
metadata=[]
for i,name in enumerate(volumes):
    info=json.loads(run('sudo','docker','volume','inspect',name,capture_output=True,text=True).stdout)[0]
    if info.get('Driver')!='local' or info.get('Options'):raise SystemExit('Нужен отдельный экспорт нестандартного volume: '+name)
    archive=f'docker-volume-{i:03d}.tar.gz'
    with (out/archive).open('wb') as f:
        run('sudo','tar','--acls','--xattrs','-C',info['Mountpoint'],'-czf','-','.',stdout=f)
    metadata.append({'name':name,'archive':archive,'labels':info.get('Labels')})
(out/'docker-volumes.json').write_text(json.dumps(metadata,indent=2))
binds=sorted({m['Source'] for c in containers for m in c.get('Mounts',[]) if m['Type']=='bind'})
# Bind mounts already inside exported projects are included in home. Save others.
home=pathlib.Path.home();project_roots=[home/x for x in ['IdeaProjects','project','esp','handGOD','hwSkypro']]
external=[]
for source in binds:
    path=pathlib.Path(source)
    if not any(path==p or p in path.parents for p in project_roots):external.append(source)
if external:
    with (out/'docker-bind-mounts.tar.gz').open('wb') as f:
        run('sudo','tar','--acls','--xattrs','-czf','-','--',*external,stdout=f)
(out/'docker-bind-paths.json').write_text(json.dumps(external,indent=2))
(out/'status.json').write_text(json.dumps({'complete':True,'postgres_clusters':len(clusters),'docker_volumes':len(volumes)}))
(ROOT/'private/SYSTEM_LATEST').write_text(str(out)+'\n')
print('Экспорт завершён:',out)
print('Следующая команда: python3 export-private.py --system-data '+str(out))
