#!/usr/bin/env bash
set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
[[ $EUID != 0 ]] || { echo 'Запускай от обычного пользователя, без sudo.' >&2; exit 1; }
command -v pacman >/dev/null || { echo 'Этот установщик предназначен для Omarchy / Arch Linux.' >&2; exit 1; }
[[ $(uname -m) == x86_64 ]] || { echo 'Подготовлено для x86_64.' >&2; exit 1; }
# Dry run never installs or restores anything.
if [[ ${1:-} == --dry-run ]]; then
  echo 'Пакеты Arch:'; cat packages.txt
  echo 'IDEA: официальный архив JetBrains; pgAdmin: изолированное Python-окружение.'
  echo 'Личные данные: зашифрованный архив, отдельный ключ, восстановление без перезаписи.'
  exit 0
fi
sudo -v
# Full upgrade avoids unsupported partial upgrades on Arch.
sudo pacman -Syu --needed --noconfirm
packages=(); missing=()
while IFS= read -r package; do
  [[ -n $package && $package != \#* ]] || continue
  if pacman -Si "$package" >/dev/null 2>&1; then packages+=("$package"); else missing+=("$package"); fi
done < packages.txt
if ((${#missing[@]})); then
  printf 'Пакеты не найдены; исправь packages.txt и повтори: %s\n' "${missing[*]}" >&2
  exit 1
fi
sudo pacman -S --needed --noconfirm "${packages[@]}"
sudo systemctl enable --now docker
sudo archlinux-java set java-25-openjdk
# Keep current Omarchy shell configuration, add a small separate fragment.
mkdir -p "$HOME/.config/enotik" "$HOME/.local/share/enotik-setup"
cat > "$HOME/.config/enotik/dev.bash" <<'SHELL'
export JAVA_HOME=/usr/lib/jvm/java-25-openjdk
export PATH="$HOME/.local/bin:$JAVA_HOME/bin:$PATH"
SHELL
line='[ -f "$HOME/.config/enotik/dev.bash" ] && . "$HOME/.config/enotik/dev.bash"'
grep -Fqx "$line" "$HOME/.bashrc" 2>/dev/null || printf '\n%s\n' "$line" >> "$HOME/.bashrc"
python3 install-apps.py
npm install --global --prefix "$HOME/.local" prettier tree-sitter-cli corepack
# Optional private data, downloaded from a private GitHub release after gh login.
if [[ ${1:-} == --restore ]]; then
  repo=${2:-Enotik-G/omarchy-setup}
  archive=${3:-"$HOME/.local/share/enotik-setup/download"}
  mkdir -p "$archive"
  if [[ ! -f "$archive/SHA256SUMS" ]]; then
    gh auth status >/dev/null 2>&1 || gh auth login -h github.com -p https -w
    gh release download migration-v1 --repo "$repo" --dir "$archive" --pattern 'payload.gpg.part-*' --pattern SHA256SUMS
  fi
  read -r -p 'Путь к файлу migration.key (хранится отдельно от GitHub): ' key
  ./restore.sh "$archive" "$key"
fi
printf '\nУстановка завершена. Docker доступен через sudo docker.\n'
printf 'Для личных данных: bash bootstrap.sh --restore\n'
printf 'Дамп PostgreSQL восстанавливается отдельно по README, чтобы не затереть базы.\n'
