#!/bin/bash
# Disposable Linux CI only: fresh candidate install and decoding configuration.
set -euo pipefail
export LC_ALL=C
fixture_dir=$1
candidate_hash=$(cat "$fixture_dir/candidate.sha256")
conf=/etc/whisper/whisper.conf
api=/opt/whisper/api_server.py
health=http://127.0.0.1:9000/health
umask 077

wait_ready() {
  local attempts=0 pid port
  port="${health%/health}"
  port="${port##*:}"
  while [ "$attempts" -lt 300 ]; do
    pid=$(systemctl show -p MainPID --value whisper.service)
    if [[ "$pid" =~ ^[1-9][0-9]*$ ]] \
      && systemctl is-active --quiet whisper.service \
      && curl --max-time 2 -fsS "$health" >/dev/null; then
      ss -ltnp "sport = :$port" | grep -F "pid=$pid," >/dev/null && return 0
    fi
    sleep 1
    attempts=$((attempts + 1))
  done
  return 1
}
assert_hash() {
  printf '%s  %s\n' "$1" "$api" | sha256sum -c -
}
assert_settings() {
  local pid
  pid=$(systemctl show -p MainPID --value whisper.service)
  # Drain journalctl even after a match: grep -q can trigger an upstream
  # SIGPIPE and make a successful check fail under pipefail on larger logs.
  journalctl -u whisper.service "_PID=$pid" --no-pager \
    | grep -F "Decoding options: condition_on_previous_text=$1 no_repeat_ngram_size=$2" >/dev/null
}
assert_requests() {
  local endpoint output code
  local key
  key=$(bash "$fixture_dir/whisper.sh" --getkey)
  [ -n "$key" ]
  # Use a checksum-pinned public speech fixture, not private recordings.
  for endpoint in transcriptions translations; do
    curl --max-time 120 -fsS -H "Authorization: Bearer $key" \
      "${health%/health}/v1/audio/$endpoint" \
      -F "file=@$fixture_dir/jfk.flac" -F model=whisper-1 \
      | python3 -c 'import json,sys; assert json.load(sys.stdin)["text"].strip()'
    output=$(curl --max-time 120 -fsSN -H "Authorization: Bearer $key" \
      "${health%/health}/v1/audio/$endpoint" \
      -F "file=@$fixture_dir/jfk.flac" -F model=whisper-1 -F stream=true)
    grep -q 'transcript.text.done' <<<"$output"
    grep -q '\[DONE\]' <<<"$output"
  done
  for key in "" wrong; do
    local auth_args=()
    if [ -n "$key" ]; then
      auth_args=(-H "Authorization: Bearer $key")
    fi
    code=$(curl --max-time 10 -s -o /dev/null -w '%{http_code}' \
      "${auth_args[@]}" "${health%/health}/v1/models")
    [ "$code" = 401 ]
  done
}
restart_ready() {
  systemctl reset-failed whisper.service || true
  systemctl restart whisper.service
  wait_ready
}
assert_hash "$candidate_hash"
grep -qx WHISPER_CONDITION_ON_PREVIOUS_TEXT=true "$conf"
grep -qx WHISPER_NO_REPEAT_NGRAM_SIZE=0 "$conf"
wait_ready
assert_settings True 0
printf '%s  %s\n' 63a4b1e4c1dc655ac70961ffbf518acd249df237e5a0152faae9a4a836949715 \
  "$fixture_dir/jfk.flac" | sha256sum -c -
assert_requests

# The fresh-installed API must also accept unset options with unchanged defaults.
sed -i '/^WHISPER_CONDITION_ON_PREVIOUS_TEXT=/d; /^WHISPER_NO_REPEAT_NGRAM_SIZE=/d' "$conf"
restart_ready
assert_settings True 0
assert_requests

# Empty values use defaults; systemd quotes are launcher grammar, not shell code.
printf '\nWHISPER_CONDITION_ON_PREVIOUS_TEXT=\nWHISPER_NO_REPEAT_NGRAM_SIZE=""\n' >>"$conf"
restart_ready
assert_settings True 0
sed -i 's/^WHISPER_CONDITION_ON_PREVIOUS_TEXT=.*/WHISPER_CONDITION_ON_PREVIOUS_TEXT="FALSE"/; s/^WHISPER_NO_REPEAT_NGRAM_SIZE=.*/WHISPER_NO_REPEAT_NGRAM_SIZE=3/' "$conf"
restart_ready
assert_settings False 3
assert_requests

# Negative startup must fail before model loading despite Restart=on-failure.
systemctl stop whisper.service
sed -i 's/^WHISPER_NO_REPEAT_NGRAM_SIZE=.*/WHISPER_NO_REPEAT_NGRAM_SIZE=01/' "$conf"
systemctl reset-failed whisper.service || true
negative_cursor=$(journalctl -u whisper.service -n 1 --show-cursor --no-pager | sed -n 's/^-- cursor: //p')
[ -n "$negative_cursor" ]
systemctl start whisper.service
found=0
attempt=0
while [ "$attempt" -lt 20 ]; do
  if journalctl -u whisper.service --after-cursor="$negative_cursor" --no-pager \
    | grep -F 'WHISPER_NO_REPEAT_NGRAM_SIZE must be' >/dev/null; then
    found=1
    break
  fi
  sleep 1
  attempt=$((attempt + 1))
done
systemctl stop whisper.service
[ "$found" = 1 ]
if journalctl -u whisper.service --after-cursor="$negative_cursor" --no-pager | grep -F 'Loading model' >/dev/null; then
  echo "Invalid option loaded a model"; exit 1
fi
sed -i 's/^WHISPER_NO_REPEAT_NGRAM_SIZE=.*/WHISPER_NO_REPEAT_NGRAM_SIZE=3/' "$conf"
restart_ready
assert_settings False 3

assert_requests
assert_hash "$candidate_hash"
[ "$(stat -c '%a %U %G' "$conf")" = '640 root whisper' ]
[ "$(stat -c '%a %U %G' "$api")" = '644 root whisper' ]
echo "Fresh candidate install, decoding settings, authentication and recovery: OK"
