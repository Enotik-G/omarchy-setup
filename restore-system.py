#!/usr/bin/env python3
"""Restore saved Docker volumes and one PostgreSQL cluster on a fresh Arch install."""
import json,os,pathlib,subprocess,sys,tempfile
root=pathlib.Path(sys.argv[1]);state=root/'restored.json'
if state.exists():print('Системные данные уже восстановлены:',state);sys.exit(0)
def run(*args,**kw):return subprocess.run(args,check=True,**kw)
volumes=json.loads((root/'docker-volumes.json').read_text())
# Preflight before changing anything: existing volumes are never overwritten.
for v in volumes:
    if subprocess.run(['sudo','docker','volume','inspect',v['name']],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
        raise SystemExit('Том уже существует; для предотвращения перезаписи нужен ручной разбор: '+v['name'])
dumps=list(root.glob('postgres-*.sql'))
pgdata=pathlib.Path('/var/lib/postgres/data')
if len(dumps)>1:raise SystemExit('Несколько PostgreSQL-кластеров: нужен отдельный импорт по README.')
if dumps and subprocess.run(['sudo','test','-f',str(pgdata/'PG_VERSION')]).returncode==0:
    raise SystemExit('PostgreSQL уже инициализирован: автоматический импорт пропущен, дамп сохранён.')
if json.loads((root/'docker-bind-paths.json').read_text()):
    print('Дополнительные bind mounts сохранены отдельным архивом; пути проверь по README.')
for v in volumes:
    run('sudo','docker','volume','create',v['name'],stdout=subprocess.DEVNULL)
    info=json.loads(run('sudo','docker','volume','inspect',v['name'],capture_output=True,text=True).stdout)[0]
    with (root/v['archive']).open('rb') as f:
        run('sudo','tar','--acls','--xattrs','-xzf','-','-C',info['Mountpoint'],stdin=f)
if dumps:
    run('sudo','install','-d','-m','700','-o','postgres','-g','postgres',str(pgdata))
    run('sudo','-u','postgres','initdb','-D',str(pgdata),'--auth-local=peer','--auth-host=scram-sha-256')
    run('sudo','systemctl','enable','--now','postgresql')
    # initdb already creates the bootstrap postgres role. Keep all its ALTER ROLE
    # statements, passwords and privileges; skip only the duplicate CREATE ROLE.
    with tempfile.TemporaryFile() as sql:
        with dumps[0].open('rb') as f:
            for line in f:
                if line.strip() not in [b'CREATE ROLE postgres;',b'CREATE ROLE "postgres";']:sql.write(line)
        sql.seek(0)
        with (root/'postgres-restore.log').open('wb') as log:
            run('sudo','-u','postgres','psql','-X','--set','ON_ERROR_STOP=on','-d','postgres',stdin=sql,stdout=log,stderr=log)
state.write_text(json.dumps({'postgres':len(dumps),'volumes':len(volumes)}))
print('Системные данные восстановлены. Compose-проекты запускай из своих каталогов.')
