#!/usr/bin/env bash
set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
echo 'Перед финальным снимком закрой Firefox, IDEA, Throne, pgAdmin и останови контейнеры.'
if pgrep -u "$(id -u)" -f '^(/[^ ]*/)?(firefox|firefox-esr|idea|Throne|pgadmin4)( |$)' >/dev/null; then
  echo 'Сначала закрой Firefox, IDEA, Throne и pgAdmin, затем повтори команду.'; exit 1
fi
python3 export-system.py
system_data=$(cat private/SYSTEM_LATEST)
python3 export-private.py --system-data "$system_data"
bash publish.sh
