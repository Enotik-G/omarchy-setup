#!/usr/bin/env bash
set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
for f in bootstrap.sh restore.sh publish.sh check.sh prepare.sh; do bash -n "$f"; done
python3 - <<'PY'
import ast,pathlib
for p in pathlib.Path('.').glob('*.py'):ast.parse(p.read_text(),filename=str(p))
print('Python и Bash: синтаксис OK')
PY
python3 flash-usb.py --dry-run
python3 export-private.py --list >/dev/null
# Archive traversal and existing user files must be protected on restoration.
python3 - <<'PY'
import importlib.util,pathlib,tempfile,tarfile,io
spec=importlib.util.spec_from_file_location('restore','restore-private.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
 r=pathlib.Path(tmp);(r/'src').mkdir();(r/'dst').mkdir();(r/'src/a').write_text('saved');(r/'dst/a').write_text('existing')
 m.merge(r/'src',r/'dst',r/'conflicts',pathlib.Path(''))
 assert (r/'dst/a').read_text()=='existing'
 assert (r/'conflicts/a').read_text()=='saved'
 (r/'src/b').write_text('new');m.merge(r/'src/b',r/'dst/b',r/'conflicts',pathlib.Path('b'))
 assert (r/'dst/b').read_text()=='new'
 with tarfile.open(r/'bad.tar','w') as t:
  i=tarfile.TarInfo('../escape');i.size=1;t.addfile(i,io.BytesIO(b'x'))
 try:
  with tarfile.open(r/'bad.tar') as t:t.extractall(r/'out',filter='data')
 except tarfile.FilterError:pass
 else:raise AssertionError('Unsafe archive accepted')
 print('Восстановление: существующие файлы сохранены, новые перенесены; traversal отклонён')
PY
