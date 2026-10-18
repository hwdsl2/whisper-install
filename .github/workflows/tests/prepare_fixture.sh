#!/bin/bash
# Run on the disposable runner, before starting the private HTTP fixture server.
set -euo pipefail
fixture_dir=$1
base_url=$2
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
repo=$(cd "$script_dir/../../.." && pwd)
python3 "$script_dir/prepare_candidate.py" --repo "$repo" --output "$fixture_dir" --base-url "$base_url"
cp "$script_dir/check_bad_checksum.sh" "$script_dir/check_systemd_decoding.sh" "$fixture_dir/"
curl --proto '=https' --proto-redir '=https' -fsSL --retry 2 --max-time 60 \
  https://raw.githubusercontent.com/openai/whisper/6e3be77e1a105e59086e3e21ff5f609fd6fa89a5/tests/jfk.flac \
  -o "$fixture_dir/jfk.flac"
printf '%s  %s\n' 63a4b1e4c1dc655ac70961ffbf518acd249df237e5a0152faae9a4a836949715 \
  "$fixture_dir/jfk.flac" | sha256sum -c -
