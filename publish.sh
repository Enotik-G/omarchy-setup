#!/usr/bin/env bash
set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
repo=Enotik-G/omarchy-setup
command -v gh >/dev/null || { echo 'Нужен gh (GitHub CLI).'; exit 1; }
gh auth status >/dev/null 2>&1 || gh auth login -h github.com -p https -w
# Encrypted payloads can be large, so use release assets instead of Git blobs.
latest=$(cat private/LATEST)
python3 - "$latest/status.json" <<'PY'
import json,sys
if not json.load(open(sys.argv[1]))['system_complete']:
    raise SystemExit('Публикация остановлена: сначала export-system.py, затем export-private.py --system-data ПУТЬ. Системные БД и Docker ещё не сохранены.')
PY
if gh repo view "$repo" >/dev/null 2>&1; then
  [[ $(gh repo view "$repo" --json isPrivate --jq .isPrivate) == true ]] || { echo 'Репозиторий должен быть приватным.'; exit 1; }
else
  gh repo create "$repo" --private --description 'Personal Omarchy development setup and encrypted migration backup'
fi
# Only explicitly named, reviewed setup files enter Git. Never git add .
git add .gitignore README.md packages.txt bootstrap.sh install-apps.py export-private.py export-system.py restore.sh restore-private.py publish.sh flash-usb.py check.sh prepare.sh restore-system.py
if ! git diff --cached --quiet; then git commit -m 'Add Omarchy setup and encrypted migration workflow'; fi
if ! git remote get-url origin >/dev/null 2>&1; then git remote add origin "https://github.com/$repo.git"; fi
[[ $(git remote get-url origin) == "https://github.com/$repo.git" ]] || { echo 'Неожиданный origin'; exit 1; }
gh auth setup-git
git push -u origin main
if gh release view migration-v1 --repo "$repo" >/dev/null 2>&1; then
  echo 'Release migration-v1 уже существует. Для обновления создай новый release вручную; старую копию не заменяю.'; exit 1
fi
gh release create migration-v1 "$latest"/payload.gpg.part-* "$latest/SHA256SUMS" --repo "$repo" --title 'Encrypted migration backup' --notes 'Encrypted personal migration data. Decryption key is stored separately.'
echo 'Опубликовано. Обязательно сохрани private/migration.key вне системного SSD и НЕ на установочной флешке.'
echo "На Omarchy: git clone https://github.com/$repo.git && cd omarchy-setup && bash bootstrap.sh --restore"
