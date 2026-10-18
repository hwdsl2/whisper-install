#!/bin/bash
# Disposable Linux CI only. Run before the first installation.
set -euo pipefail
export LC_ALL=C
fixture_dir=$1
[ "$(id -u)" = 0 ]
for target in /etc/whisper/whisper.conf /opt/whisper/api_server.py /etc/systemd/system/whisper.service; do
  [ ! -e "$target" ]
done
if getent passwd whisper >/dev/null; then
  echo "Fresh checksum test requires no pre-existing whisper account"; exit 1
fi
package_state() {
  if command -v dpkg-query >/dev/null 2>&1; then
    dpkg-query -W -f='${Package}=${Version}\n' | LC_ALL=C sort | sha256sum
  else
    rpm -qa | LC_ALL=C sort | sha256sum
  fi
}
before_packages=$(package_state)
umask 077
if bash "$fixture_dir/bad-checksum.sh" --auto --model tiny >"$fixture_dir/bad-checksum.log" 2>&1; then
  echo "Bad checksum unexpectedly installed"; exit 1
fi
grep -q 'checksum verification failed' "$fixture_dir/bad-checksum.log"
[ "$(package_state)" = "$before_packages" ]
if getent passwd whisper >/dev/null; then
  echo "Checksum failure created a service account"; exit 1
fi
for target in /etc/whisper/whisper.conf /opt/whisper/api_server.py /etc/systemd/system/whisper.service; do
  [ ! -e "$target" ]
done
echo "Fresh checksum failure leaves packages, account and installed files unchanged"
