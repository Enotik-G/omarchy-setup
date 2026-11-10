#!/usr/bin/env bash
set -Eeuo pipefail
[[ $# == 2 ]] || { echo 'restore.sh КАТАЛОГ_С_ЧАСТЯМИ ФАЙЛ_КЛЮЧА'; exit 1; }
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
parts=$(realpath -- "$1"); key=$(realpath -- "$2")
(cd "$parts" && sha256sum -c SHA256SUMS)
umask 077
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
cat "$parts"/payload.gpg.part-* | gpg --no-symkey-cache --batch --pinentry-mode loopback --passphrase-file "$key" --decrypt > "$stage/payload.tar.gz"
python3 restore-private.py "$stage/payload.tar.gz"
