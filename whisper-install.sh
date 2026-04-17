#!/bin/bash
#
# https://github.com/hwdsl2/whisper-install
#
# Copyright (C) 2026 Lin Song <linsongui@gmail.com>
#
# This work is licensed under the MIT License
# See: https://opensource.org/licenses/MIT

exiterr()  { echo "Error: $1" >&2; exit 1; }
exiterr2() { exiterr "Package installation failed. Check your package manager."; }

WHISPER_DATA="/var/lib/whisper"
WHISPER_CONF="/etc/whisper/whisper.conf"
WHISPER_CONF_DIR="/etc/whisper"
WHISPER_API_SERVER="/opt/whisper/api_server.py"
WHISPER_VENV="/opt/whisper/venv"
WHISPER_SVC="/etc/systemd/system/whisper.service"
WHISPER_TMPDIR="/run/whisper-temp"

check_ip() {
  IP_REGEX='^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$'
  printf '%s' "$1" | tr -d '\n' | grep -Eq "$IP_REGEX"
}

check_port() {
  printf '%s' "$1" | tr -d '\n' | grep -Eq '^[0-9]+$' &&
    [ "$1" -ge 1 ] && [ "$1" -le 65535 ]
}

check_root() {
  if [ "$(id -u)" != 0 ]; then
    exiterr "This installer must be run as root. Try 'sudo bash $0'"
  fi
}

check_shell() {
  if readlink /proc/$$/exe 2>/dev/null | grep -q "dash"; then
    exiterr 'This installer needs to be run with "bash", not "sh".'
  fi
}

check_os() {
  if grep -qs "ubuntu" /etc/os-release; then
    os="ubuntu"
    os_version=$(grep 'VERSION_ID' /etc/os-release | cut -d '"' -f 2 | tr -d '.')
    if [[ -z "$os_version" || ! "$os_version" =~ ^[0-9]+$ || "$os_version" -lt 2004 ]]; then
      ubuntu_codename=$(grep 'UBUNTU_CODENAME' /etc/os-release | cut -d '=' -f 2 | tr -d '"')
      case "$ubuntu_codename" in
      focal)  os_version=2004 ;;
      jammy)  os_version=2204 ;;
      noble)  os_version=2404 ;;
      esac
    fi
  elif [[ -e /etc/debian_version ]]; then
    os="debian"
    os_version=$(grep -oE '[0-9]+' /etc/debian_version | head -1)
    if [[ -z "$os_version" ]]; then
      debian_codename=$(grep '^DEBIAN_CODENAME' /etc/os-release 2>/dev/null | cut -d '=' -f 2)
      case "$debian_codename" in
      buster)   os_version=10 ;;
      bullseye) os_version=11 ;;
      bookworm) os_version=12 ;;
      trixie)   os_version=13 ;;
      esac
    fi
  elif grep -qs "Alibaba Cloud Linux" /etc/system-release 2>/dev/null; then
    os="centos"
    al_ver=$(grep -oE '[0-9]+' /etc/system-release | head -1)
    if [[ "$al_ver" -ge 3 ]]; then
      os_version=9
    else
      os_version=7
    fi
  elif [[ -e /etc/almalinux-release || -e /etc/rocky-release || -e /etc/centos-release ]]; then
    os="centos"
    os_version=$(grep -shoE '[0-9]+' /etc/almalinux-release /etc/rocky-release /etc/centos-release | head -1)
  elif [[ -e /etc/fedora-release ]]; then
    os="fedora"
    os_version=$(grep -oE '[0-9]+' /etc/fedora-release | head -1)
  elif [[ -e /etc/redhat-release ]]; then
    os="rhel"
    os_version=$(grep -oE '[0-9]+' /etc/redhat-release | head -1)
  else
    exiterr "This installer seems to be running on an unsupported distribution.
Supported distros are Ubuntu, Debian, AlmaLinux, Rocky Linux, CentOS, RHEL and Fedora."
  fi
}

check_os_ver() {
  if [[ "$os" == "ubuntu" && "$os_version" -lt 2204 ]]; then
    exiterr "Ubuntu 22.04 or higher is required to use this installer."
  fi
  if [[ "$os" == "debian" && "$os_version" -lt 11 ]]; then
    exiterr "Debian 11 or higher is required to use this installer."
  fi
  if [[ "$os" == "centos" && "$os_version" -lt 9 ]]; then
    exiterr "CentOS 9 or higher is required to use this installer."
  fi
  if [[ "$os" == "rhel" && "$os_version" -lt 9 ]]; then
    exiterr "RHEL 9 or higher is required to use this installer."
  fi
}

check_systemd() {
  if ! command -v systemctl >/dev/null 2>&1; then
    exiterr "This installer requires systemd.
To run Whisper in Docker instead, see: https://github.com/hwdsl2/docker-whisper"
  fi
}

check_python() {
  # Require Python 3.9+ (faster-whisper minimum)
  local py_cmd
  for py_cmd in python3 python3.12 python3.11 python3.10 python3.9; do
    if command -v "$py_cmd" >/dev/null 2>&1; then
      local ver
      ver=$("$py_cmd" -c 'import sys; print(sys.version_info.major * 100 + sys.version_info.minor)' 2>/dev/null)
      if [[ -n "$ver" && "$ver" -ge 309 ]]; then
        PYTHON_CMD="$py_cmd"
        return 0
      fi
    fi
  done
  return 1
}

parse_args() {
  while [ "$#" -gt 0 ]; do
    case $1 in
    --auto)
      auto=1
      shift
      ;;
    --model)
      [ -z "${2:-}" ] && show_usage "Missing value for --model."
      model_arg="$2"
      shift; shift
      ;;
    --port)
      [ -z "${2:-}" ] && show_usage "Missing value for --port."
      port_arg="$2"
      shift; shift
      ;;
    --listenaddr)
      [ -z "${2:-}" ] && show_usage "Missing value for --listenaddr."
      listen_addr_arg="$2"
      shift; shift
      ;;
    --showinfo)
      show_info=1
      shift
      ;;
    --listmodels)
      list_models=1
      shift
      ;;
    --downloadmodel)
      download_model=1
      model_to_download="${2:-}"
      shift
      [ "$#" -gt 0 ] && shift
      ;;
    --uninstall)
      remove_whisper=1
      shift
      ;;
    -y | --yes)
      assume_yes=1
      shift
      ;;
    -h | --help)
      show_usage
      ;;
    *)
      show_usage "Unknown parameter: $1"
      ;;
    esac
  done
}

check_args() {
  local mgmt_count
  mgmt_count=$((show_info + list_models + download_model))

  if [ "$auto" != 0 ] && [ -f "$WHISPER_CONF" ]; then
    show_usage "Invalid parameter '--auto'. Whisper is already set up on this server."
  fi
  if [ "$remove_whisper" = 1 ]; then
    if [ "$((mgmt_count + auto))" -gt 0 ]; then
      show_usage "Invalid parameters. '--uninstall' cannot be specified with other parameters."
    fi
    if [ ! -f "$WHISPER_CONF" ]; then
      exiterr "Cannot remove Whisper because it has not been set up on this server."
    fi
  fi
  if [ ! -f "$WHISPER_CONF" ]; then
    [ "$show_info" = 1 ]      && exiterr "You must first set up Whisper before showing info."
    [ "$download_model" = 1 ] && exiterr "You must first set up Whisper before downloading a model."
  fi
  if [ "$mgmt_count" -gt 1 ]; then
    show_usage "Invalid parameters. Specify only one management action at a time."
  fi
  if [ "$download_model" = 1 ] && [ -z "$model_to_download" ]; then
    exiterr "Missing model name. Usage: --downloadmodel <model>"
  fi
  if [ -n "$model_arg" ] || [ -n "$port_arg" ] || [ -n "$listen_addr_arg" ]; then
    if [ -f "$WHISPER_CONF" ]; then
      show_usage "Invalid parameters. Whisper is already set up on this server."
    elif [ "$auto" = 0 ]; then
      show_usage "Invalid parameters. You must specify '--auto' when using these parameters."
    fi
  fi
  if [ -n "$model_arg" ]; then
    validate_model_name "$model_arg" || exiterr "Invalid model '$model_arg'. Run '--listmodels' to see valid names."
  fi
  if [ -n "$port_arg" ] && ! check_port "$port_arg"; then
    exiterr "Invalid port. Must be an integer between 1 and 65535."
  fi
  if [ -n "$listen_addr_arg" ] && ! check_ip "$listen_addr_arg"; then
    exiterr "Invalid listen address '$listen_addr_arg'. Must be a valid IPv4 address (e.g. 127.0.0.1 or 0.0.0.0)."
  fi
  if [ "$download_model" = 1 ]; then
    validate_model_name "$model_to_download" || exiterr "Unknown model '$model_to_download'. Run '--listmodels' to see valid names."
  fi
}

validate_model_name() {
  case "$1" in
    tiny|tiny.en|base|base.en|small|small.en|medium|medium.en|\
    large-v1|large-v2|large-v3|large-v3-turbo|turbo) return 0 ;;
    *) return 1 ;;
  esac
}

show_header() {
  cat <<'EOF'

Whisper Script
https://github.com/hwdsl2/whisper-install
EOF
}

show_header2() {
  cat <<'EOF'

Welcome to this Whisper speech-to-text installer!
GitHub: https://github.com/hwdsl2/whisper-install

EOF
}

show_header3() {
  cat <<'EOF'

Copyright (C) 2026 Lin Song
EOF
}

show_usage() {
  if [ -n "$1" ]; then
    echo "Error: $1" >&2
  fi
  show_header
  show_header3
  cat 1>&2 <<EOF

Usage: bash $0 [options]

Options:

  --showinfo                           show server info (model, endpoint, API docs)
  --listmodels                         list available Whisper model names and sizes
  --downloadmodel <model>              pre-download a model to the cache directory
  --uninstall                          remove Whisper and delete all configuration
  -y, --yes                            assume "yes" as answer to prompts
  -h, --help                           show this help message and exit

Install options (optional):

  --auto                               auto install using default or custom options
  --model      <name>                  Whisper model to use (default: base)
  --port       <number>                TCP port for the API server (default: 9000)
  --listenaddr [address]               listen address (default: 0.0.0.0, use 127.0.0.1 for local only)

Available models: tiny, tiny.en, base, base.en, small, small.en,
                  medium, medium.en, large-v1, large-v2, large-v3,
                  large-v3-turbo (or: turbo)

To customize options, you may also run this script without arguments.
EOF
  exit 1
}

find_public_ip() {
  ip_url1="http://ipv4.icanhazip.com"
  ip_url2="http://ip1.dynupdate.no-ip.com"
  get_public_ip=$(grep -m 1 -oE '^[0-9]{1,3}(\.[0-9]{1,3}){3}$' \
    <<<"$(wget -T 10 -t 1 -4qO- "$ip_url1" 2>/dev/null || curl -m 10 -4Ls "$ip_url1" 2>/dev/null)")
  if ! check_ip "$get_public_ip"; then
    get_public_ip=$(grep -m 1 -oE '^[0-9]{1,3}(\.[0-9]{1,3}){3}$' \
      <<<"$(wget -T 10 -t 1 -4qO- "$ip_url2" 2>/dev/null || curl -m 10 -4Ls "$ip_url2" 2>/dev/null)")
  fi
}

detect_server_ip() {
  find_public_ip
  if check_ip "$get_public_ip"; then
    server_ip="$get_public_ip"
  else
    server_ip=$(ip -4 route get 1 2>/dev/null | sed 's/ uid .*//' | awk '{print $NF;exit}')
    check_ip "$server_ip" || server_ip="<server ip>"
  fi
}

show_welcome() {
  if [ "$auto" = 0 ]; then
    show_header2
    echo 'I need to ask you a few questions before starting setup.'
    echo 'You can use the default options and just press enter if you are OK with them.'
  else
    show_header
    op_text=default
    if [ -n "$model_arg" ] || [ -n "$port_arg" ] || [ -n "$listen_addr_arg" ]; then
      op_text=custom
    fi
    echo
    echo "Starting Whisper setup using $op_text options."
  fi
}

select_model() {
  if [ "$auto" = 0 ]; then
    echo
    echo "Which Whisper model would you like to use?"
    echo "  tiny (~75 MB) · base (~145 MB, default) · small (~465 MB)"
    echo "  medium (~1.5 GB) · large-v3 (~3 GB) · large-v3-turbo (~1.6 GB)"
    read -rp "Model [base]: " model_input
    if [ -z "$model_input" ]; then
      whisper_model="base"
    elif validate_model_name "$model_input"; then
      whisper_model="$model_input"
    else
      echo "Unrecognized model '$model_input', using default: base"
      whisper_model="base"
    fi
  else
    [ -n "$model_arg" ] && whisper_model="$model_arg" || whisper_model="base"
  fi
}

select_port() {
  if [ "$auto" = 0 ]; then
    echo
    echo "Which TCP port should the Whisper API server listen on?"
    read -rp "Port [9000]: " port_input
    until [[ -z "$port_input" || "$port_input" =~ ^[0-9]+$ && "$port_input" -le 65535 ]]; do
      echo "$port_input: invalid port."
      read -rp "Port [9000]: " port_input
    done
    [[ -z "$port_input" ]] && whisper_port=9000 || whisper_port="$port_input"
  else
    [ -n "$port_arg" ] && whisper_port="$port_arg" || whisper_port=9000
  fi
}

show_config() {
  if [ "$auto" != 0 ]; then
    echo
    echo "Model:        $whisper_model"
    echo "Listen addr:  $whisper_listen_addr"
    echo "Port:         TCP/$whisper_port"
  fi
}

show_setup_ready() {
  if [ "$auto" = 0 ]; then
    echo
    echo "Whisper installation is ready to begin."
  fi
}

abort_and_exit() {
  echo "Abort. No changes were made." >&2
  exit 1
}

confirm_setup() {
  if [ "$auto" = 0 ]; then
    printf "Do you want to continue? [Y/n] "
    read -r response
    case $response in
    [yY][eE][sS] | [yY] | '')
      :
      ;;
    *)
      abort_and_exit
      ;;
    esac
  fi
}

show_start_setup() {
  echo
  echo "Installing Whisper, please wait..."
}

install_packages() {
  echo "  Installing system packages..."
  if [ "$os" = "ubuntu" ] || [ "$os" = "debian" ]; then
    export DEBIAN_FRONTEND=noninteractive
    (
      set -x
      apt-get -yqq update || apt-get -yqq update
      apt-get -yqq install --no-install-recommends curl python3 python3-venv >/dev/null
    ) || exiterr2
  else
    (
      set -x
      yum -y -q install curl python3 >/dev/null
    ) || exiterr "Package installation failed. Check your package manager."
  fi
}

create_whisper_user() {
  if ! getent group whisper >/dev/null 2>&1; then
    groupadd --system whisper
  fi
  if ! id whisper >/dev/null 2>&1; then
    useradd --system --shell /usr/sbin/nologin \
      --gid whisper --home-dir "$WHISPER_DATA" \
      --comment "Whisper speech-to-text daemon" whisper
  fi
}

create_directories() {
  mkdir -p "$WHISPER_CONF_DIR" /opt/whisper "$WHISPER_DATA" "$WHISPER_TMPDIR"
  chown root:whisper "$WHISPER_CONF_DIR"
  chmod 750 "$WHISPER_CONF_DIR"
  chown whisper:whisper "$WHISPER_DATA" "$WHISPER_TMPDIR"
  chmod 750 "$WHISPER_DATA"
  chmod 1777 "$WHISPER_TMPDIR"
}

create_venv() {
  echo "  Creating Python virtual environment..."
  if ! check_python; then
    exiterr "Python 3.9 or higher is required but was not found.
Install Python 3.9+ and re-run this script."
  fi
  (
    set -x
    "$PYTHON_CMD" -m venv "$WHISPER_VENV"
  ) || exiterr "Failed to create Python virtual environment."
  echo "  Installing Python packages (this may take a few minutes)..."
  (
    set -x
    "$WHISPER_VENV/bin/pip" install --quiet --no-cache-dir --upgrade pip
    "$WHISPER_VENV/bin/pip" install --quiet --no-cache-dir \
      faster-whisper \
      fastapi \
      "uvicorn[standard]" \
      python-multipart
  ) || exiterr "Failed to install Python packages. Check your internet connection."
  chown -R whisper:whisper /opt/whisper
}

install_api_server() {
  echo "  Installing API server..."
  cat >"$WHISPER_API_SERVER" <<'PYEOF'
#!/usr/bin/env python3
"""
Whisper Speech-to-Text API Server
Provides an OpenAI-compatible /v1/audio/transcriptions endpoint
powered by faster-whisper.

https://github.com/hwdsl2/whisper-install

Copyright (C) 2026 Lin Song

This work is licensed under the MIT License
See: https://opensource.org/licenses/MIT
"""

import asyncio
import json
import logging
import os
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_log_level_str = os.environ.get("WHISPER_LOG_LEVEL", "INFO").upper()
_log_level = getattr(logging, _log_level_str, logging.INFO)
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("whisper_server")

# ---------------------------------------------------------------------------
# Model — loaded once at startup via the FastAPI lifespan hook
# ---------------------------------------------------------------------------

_model = None
_model_name = None
_beam_size = 5

_inference_lock = threading.Lock()


def _load_model() -> None:
    """Import and initialise the faster-whisper model from environment config."""
    global _model, _model_name, _beam_size

    from faster_whisper import WhisperModel

    model_name       = os.environ.get("WHISPER_MODEL",        "base").strip()
    device           = os.environ.get("WHISPER_DEVICE",       "cpu").strip()
    compute_type     = os.environ.get("WHISPER_COMPUTE_TYPE", "int8").strip()
    threads          = int(os.environ.get("WHISPER_THREADS",  "2"))
    cache_dir        = os.environ.get("HF_HOME", "/var/lib/whisper")
    local_files_only = bool(os.environ.get("WHISPER_LOCAL_ONLY", "").strip())
    _beam_size       = int(os.environ.get("WHISPER_BEAM", "5"))

    logger.info(
        "Loading model '%s' | device=%s compute_type=%s threads=%d beam=%d local_only=%s cache=%s",
        model_name, device, compute_type, threads, _beam_size, local_files_only, cache_dir,
    )
    t0 = time.monotonic()
    _model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
        cpu_threads=threads,
        download_root=cache_dir,
        local_files_only=local_files_only,
    )
    _model_name = model_name
    logger.info("Model '%s' ready in %.1fs", model_name, time.monotonic() - t0)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    _load_model()
    yield


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Whisper Speech-to-Text",
    description=(
        "OpenAI-compatible speech-to-text API powered by faster-whisper.\n\n"
        "https://github.com/hwdsl2/whisper-install"
    ),
    version="1.0.0",
    lifespan=_lifespan,
)

# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


def _verify_api_key(authorization: Optional[str] = Header(default=None)) -> None:
    required = os.environ.get("WHISPER_API_KEY", "").strip()
    if not required:
        return
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    parts = authorization.split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header. Expected: Bearer <key>",
        )
    if parts[1] != required:
        raise HTTPException(status_code=401, detail="Invalid API key.")


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------


def _fmt_ts(seconds: float, fmt: str) -> str:
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    sep = "," if fmt == "srt" else "."
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def _to_srt(segments) -> str:
    lines = []
    for i, seg in enumerate(segments, start=1):
        lines.append(
            f"{i}\n"
            f"{_fmt_ts(seg.start, 'srt')} --> {_fmt_ts(seg.end, 'srt')}\n"
            f"{seg.text.strip()}\n"
        )
    return "\n".join(lines)


def _to_vtt(segments) -> str:
    lines = ["WEBVTT\n"]
    for seg in segments:
        lines.append(
            f"{_fmt_ts(seg.start, 'vtt')} --> {_fmt_ts(seg.end, 'vtt')}\n"
            f"{seg.text.strip()}\n"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# SSE streaming helper
# ---------------------------------------------------------------------------


async def _stream_sse(
    tmp_path: str,
    lang: Optional[str],
    prompt: Optional[str],
    temperature: float,
):
    loop = asyncio.get_running_loop()
    seg_queue: asyncio.Queue = asyncio.Queue()

    def _run() -> None:
        with _inference_lock:
            try:
                segs_gen, _ = _model.transcribe(
                    tmp_path,
                    language=lang,
                    initial_prompt=prompt or None,
                    temperature=temperature,
                    beam_size=_beam_size,
                    vad_filter=True,
                )
                for seg in segs_gen:
                    loop.call_soon_threadsafe(seg_queue.put_nowait, seg)
            except Exception as exc:
                loop.call_soon_threadsafe(seg_queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(seg_queue.put_nowait, None)

    loop.run_in_executor(None, _run)
    text_parts: list = []

    try:
        while True:
            item = await seg_queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                logger.error("Streaming transcription error: %s", item)
                yield f'data: {json.dumps({"type": "error", "detail": str(item)})}\n\n'
                return
            text_parts.append(item.text.strip())
            payload = json.dumps({
                "type": "segment",
                "start": round(item.start, 3),
                "end":   round(item.end, 3),
                "text":  item.text.strip(),
            })
            yield f"data: {payload}\n\n"
        yield f'data: {json.dumps({"type": "done", "text": " ".join(text_parts).strip()})}\n\n'
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok", "model": _model_name}


@app.get("/v1/models")
async def list_models(_auth: None = Depends(_verify_api_key)):
    return {
        "object": "list",
        "data": [
            {
                "id": _model_name or "whisper-1",
                "object": "model",
                "created": 0,
                "owned_by": "faster-whisper",
            }
        ],
    }


@app.post("/v1/audio/transcriptions")
async def transcribe(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    model: str = Form(
        default="whisper-1",
        description="Model identifier (ignored — active model is used)",
    ),
    language: Optional[str] = Form(
        default=None,
        description="BCP-47 language code (e.g. 'en'). Omit or set to 'auto' for autodetect.",
    ),
    prompt: Optional[str] = Form(
        default=None,
        description="Optional text to guide the model's style or continue a previous segment.",
    ),
    response_format: str = Form(
        default="json",
        description="Output format: json, text, verbose_json, srt, vtt",
    ),
    temperature: float = Form(
        default=0.0,
        description="Sampling temperature between 0 and 1.",
    ),
    stream: Optional[str] = Form(
        default=None,
        description=(
            "Stream segments as Server-Sent Events (text/event-stream). "
            "When true, the response is a series of 'data:' frames — one per "
            "decoded segment — followed by a final 'done' frame."
        ),
    ),
    _auth: None = Depends(_verify_api_key),
):
    """
    Transcribe an audio file.

    Drop-in replacement for OpenAI's POST /v1/audio/transcriptions endpoint.
    Accepts the same multipart/form-data parameters and returns the same
    response shapes.

    Supported audio formats: mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg, flac.
    """
    if _model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded yet. Please retry.")

    # Normalise the stream form field: the string "true" (case-insensitive) enables streaming.
    # Using Optional[str] instead of bool avoids Pydantic version-dependent coercion differences.
    stream_flag: bool = stream is not None and stream.strip().lower() == "true"

    valid_formats = {"json", "text", "verbose_json", "srt", "vtt"}
    if not stream_flag and response_format not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid response_format '{response_format}'. "
                   f"Must be one of: {', '.join(sorted(valid_formats))}",
        )

    env_lang = os.environ.get("WHISPER_LANGUAGE", "auto").strip()
    if language and language.lower() != "auto":
        lang = language
    elif env_lang and env_lang.lower() != "auto":
        lang = env_lang
    else:
        lang = None

    original_name = file.filename or "audio"
    suffix = os.path.splitext(original_name)[1] or ".audio"
    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            content = await file.read()
            tmp.write(content)
    except Exception as exc:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        logger.exception("Failed to save upload: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {exc}") from exc

    logger.info(
        "Transcribing '%s' (%d bytes) | lang=%s format=%s stream=%s",
        original_name, len(content), lang or "auto", response_format, stream_flag,
    )

    if stream_flag:
        return StreamingResponse(
            _stream_sse(tmp_path, lang, prompt, temperature),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
            },
        )

    try:
        with _inference_lock:
            segments_gen, info = _model.transcribe(
                tmp_path,
                language=lang,
                initial_prompt=prompt or None,
                temperature=temperature,
                beam_size=_beam_size,
                vad_filter=True,
            )
            segments = list(segments_gen)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Transcription failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    full_text = " ".join(seg.text.strip() for seg in segments).strip()

    if response_format == "text":
        return PlainTextResponse(full_text)
    if response_format == "srt":
        return PlainTextResponse(_to_srt(segments), media_type="text/plain")
    if response_format == "vtt":
        return PlainTextResponse(_to_vtt(segments), media_type="text/plain")
    if response_format == "verbose_json":
        return JSONResponse({
            "task": "transcribe",
            "language": info.language,
            "language_probability": round(info.language_probability, 4),
            "duration": round(info.duration, 3),
            "duration_after_vad": round(info.duration_after_vad, 3),
            "text": full_text,
            "segments": [
                {
                    "id": idx,
                    "seek": seg.seek,
                    "start": round(seg.start, 3),
                    "end": round(seg.end, 3),
                    "text": seg.text.strip(),
                    "tokens": seg.tokens,
                    "temperature": round(seg.temperature, 3) if seg.temperature is not None else temperature,
                    "avg_logprob": round(seg.avg_logprob, 4),
                    "compression_ratio": round(seg.compression_ratio, 4),
                    "no_speech_prob": round(seg.no_speech_prob, 4),
                }
                for idx, seg in enumerate(segments)
            ],
        })

    return JSONResponse({"text": full_text})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("WHISPER_PORT", "9000"))
    host = os.environ.get("WHISPER_LISTEN_ADDR", "0.0.0.0").strip()
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        log_level=_log_level_str.lower(),
        workers=1,
    )
PYEOF
  chmod 644 "$WHISPER_API_SERVER"
  chown root:whisper "$WHISPER_API_SERVER"
}

create_config() {
  cat >"$WHISPER_CONF" <<EOF
# Whisper speech-to-text server configuration
# Generated by whisper-install — edit this file to change settings.
# https://github.com/hwdsl2/whisper-install
#
# After editing, restart the service: sudo systemctl restart whisper

# Whisper model to use.
# Options: tiny, tiny.en, base, base.en, small, small.en, medium, medium.en,
#          large-v1, large-v2, large-v3, large-v3-turbo, turbo
WHISPER_MODEL=${whisper_model}

# TCP port for the API server (1-65535)
WHISPER_PORT=${whisper_port}

# Listen address for the API server.
# Use 0.0.0.0 to listen on all interfaces, or 127.0.0.1 for local access only.
WHISPER_LISTEN_ADDR=${whisper_listen_addr}

# Default language for transcription.
# Set to a BCP-47 code (e.g. en, fr, de) to skip auto-detection.
# Leave as 'auto' to let the model detect the language automatically.
WHISPER_LANGUAGE=auto

# Inference device. Only 'cpu' is supported for bare-metal CPU installs.
WHISPER_DEVICE=cpu

# Quantization type. int8 gives the best balance of speed and accuracy on CPU.
# Options: int8, int8_float16, int8_float32, int8_bfloat16, int16, float32, bfloat16
WHISPER_COMPUTE_TYPE=int8

# Number of CPU threads to use for inference (positive integer).
WHISPER_THREADS=2

# Beam size for decoding (positive integer, higher = more accurate but slower).
WHISPER_BEAM=5

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
WHISPER_LOG_LEVEL=INFO

# Optional API key for bearer token authentication.
# Leave blank to allow unauthenticated access.
WHISPER_API_KEY=

# Set to any non-empty value to disable model downloads (air-gap / offline mode).
# The model must already be present in ${WHISPER_DATA}.
WHISPER_LOCAL_ONLY=
EOF
  chmod 640 "$WHISPER_CONF"
  chown root:whisper "$WHISPER_CONF"
}

install_service() {
  # RuntimeDirectory creates and owns /run/whisper-temp at service start.
  cat >"$WHISPER_SVC" <<EOF
[Unit]
Description=Whisper speech-to-text API server
After=network.target

[Service]
Type=simple
User=whisper
Group=whisper
EnvironmentFile=${WHISPER_CONF}
Environment=HF_HOME=${WHISPER_DATA}
Environment=TMPDIR=${WHISPER_TMPDIR}
ExecStart=${WHISPER_VENV}/bin/python3 ${WHISPER_API_SERVER}
Restart=on-failure
RestartSec=5
WorkingDirectory=${WHISPER_DATA}
RuntimeDirectory=whisper-temp
RuntimeDirectoryMode=1777

NoNewPrivileges=true
PrivateTmp=false
ProtectHome=true
ProtectSystem=full
ReadWritePaths=${WHISPER_DATA} ${WHISPER_TMPDIR} /opt/whisper

[Install]
WantedBy=multi-user.target
EOF
  (
    set -x
    systemctl daemon-reload
  )
}

start_whisper_service() {
  (
    set -x
    systemctl enable --now whisper.service >/dev/null 2>&1
  )
}

wait_for_server() {
  local i=0
  local port="${whisper_port:-9000}"
  echo
  printf 'Waiting for Whisper server to start'
  while [ "$i" -lt 60 ]; do
    if curl -sf "http://127.0.0.1:${port}/health" >/dev/null 2>&1; then
      echo ""
      return 0
    fi
    printf '.'
    sleep 2
    i=$((i + 1))
  done
  echo ""
  return 1
}

finish_setup() {
  detect_server_ip
  local port="${whisper_port:-9000}"
  echo
  echo "Finished!"
  echo
  echo "==========================================================="
  echo " Whisper speech-to-text server is ready"
  echo "==========================================================="
  echo " Model:    $whisper_model"
  echo " Endpoint: http://${server_ip}:${port}"
  echo "==========================================================="
  echo
  echo "Transcribe an audio file:"
  echo "  curl http://${server_ip}:${port}/v1/audio/transcriptions \\"
  echo "    -F file=@audio.mp3 -F model=whisper-1"
  echo
  echo "Interactive API docs: http://${server_ip}:${port}/docs"
  echo
  echo "Manage this server by running this script again."
  echo
  echo "Configuration file: $WHISPER_CONF"
  echo
}

# ---------------------------------------------------------------------------
# Management actions
# ---------------------------------------------------------------------------

load_config_from_file() {
  if [ -f "$WHISPER_CONF" ]; then
    # shellcheck disable=SC1090
    . <(grep -E '^(WHISPER_MODEL|WHISPER_PORT)=' "$WHISPER_CONF" | sed 's/[[:space:]]*#.*$//')
  fi
  WHISPER_MODEL="${WHISPER_MODEL:-base}"
  WHISPER_PORT="${WHISPER_PORT:-9000}"
}

do_show_info() {
  load_config_from_file
  detect_server_ip
  echo
  echo "==========================================================="
  echo " Whisper Speech-to-Text Server"
  echo "==========================================================="
  echo " Active model: $WHISPER_MODEL"
  echo " Endpoint:     http://${server_ip}:${WHISPER_PORT}"
  echo "==========================================================="
  echo
  echo "API endpoints:"
  echo "  POST http://${server_ip}:${WHISPER_PORT}/v1/audio/transcriptions"
  echo "  GET  http://${server_ip}:${WHISPER_PORT}/v1/models"
  echo "  GET  http://${server_ip}:${WHISPER_PORT}/docs     (interactive docs)"
  echo
  echo "Example transcription:"
  echo "  curl http://${server_ip}:${WHISPER_PORT}/v1/audio/transcriptions \\"
  echo "    -F file=@audio.mp3 -F model=whisper-1"
  echo
  echo "Service status:"
  echo "  sudo systemctl status whisper"
  echo
  echo "Configuration file: $WHISPER_CONF"
  echo
}

do_list_models() {
  cat <<'EOF'

Available Whisper models:

  Name              Disk     RAM (approx)   Notes
  ----              ----     ------------   -----
  tiny              ~75 MB   ~250 MB        Fastest; lower accuracy
  tiny.en           ~75 MB   ~250 MB        English-only variant
  base              ~145 MB  ~500 MB        Good balance — default
  base.en           ~145 MB  ~500 MB        English-only variant
  small             ~465 MB  ~1.5 GB        Better accuracy
  small.en          ~465 MB  ~1.5 GB        English-only variant
  medium            ~1.5 GB  ~5 GB          High accuracy
  medium.en         ~1.5 GB  ~5 GB          English-only variant
  large-v1          ~3 GB    ~10 GB         Older large model
  large-v2          ~3 GB    ~10 GB         Very high accuracy
  large-v3          ~3 GB    ~10 GB         Best accuracy (recommended for quality)
  large-v3-turbo    ~1.6 GB  ~6 GB          Fast + high accuracy (best overall upgrade)
  turbo             ~1.6 GB  ~6 GB          Alias for large-v3-turbo

Notes:
  - English-only (.en) variants are slightly faster for English audio.
  - large-v3-turbo (or: turbo) is recommended over large-v3 for most use
    cases: comparable accuracy with significantly lower resource usage.
  - Models are downloaded from HuggingFace on first use and cached in
    /var/lib/whisper.
  - INT8 quantization (default) reduces RAM usage by approximately 50%.

Use '--downloadmodel <name>' to pre-download a model before switching.

EOF
}

do_download_model() {
  load_config_from_file
  echo
  echo "Downloading model '${model_to_download}' to ${WHISPER_DATA}..."
  echo "This may take several minutes depending on model size and network speed."
  echo
  HF_HOME="$WHISPER_DATA" \
  _MODEL="$model_to_download" \
  "$WHISPER_VENV/bin/python3" - <<'PYEOF'
import os, sys
model_name = os.environ["_MODEL"]
cache_dir  = os.environ.get("HF_HOME", "/var/lib/whisper")
try:
    from faster_whisper import WhisperModel
    print(f"  Downloading '{model_name}' (compute_type=int8) ...")
    sys.stdout.flush()
    WhisperModel(
        model_name,
        device="cpu",
        compute_type="int8",
        download_root=cache_dir,
    )
    print(f"  Model '{model_name}' downloaded successfully.")
    print(f"  Cache location: {cache_dir}")
except Exception as exc:
    print(f"Error: {exc}", file=sys.stderr)
    sys.exit(1)
PYEOF
  echo
  echo "To activate this model, set WHISPER_MODEL=${model_to_download} in"
  echo "$WHISPER_CONF and restart the service:"
  echo "  sudo systemctl restart whisper"
  echo
}

remove_whisper() {
  if [ "$assume_yes" = 0 ]; then
    echo
    echo "This will stop and remove Whisper, including:"
    echo "  - systemd service"
    echo "  - configuration at $WHISPER_CONF_DIR"
    echo "  - Python venv at /opt/whisper"
    echo "  - API server at $WHISPER_API_SERVER"
    echo
    echo "Model cache at $WHISPER_DATA will NOT be deleted."
    printf "Are you sure you want to remove Whisper? [y/N] "
    read -r response
    case $response in
    [yY][eE][sS] | [yY])
      :
      ;;
    *)
      abort_and_exit
      ;;
    esac
  fi
  echo
  echo "Removing Whisper..."
  systemctl disable --now whisper.service 2>/dev/null || true
  rm -f "$WHISPER_SVC"
  systemctl daemon-reload 2>/dev/null || true
  rm -rf "$WHISPER_CONF_DIR"
  rm -rf /opt/whisper
  # Remove the dedicated system user and group if they exist
  if id whisper >/dev/null 2>&1; then userdel whisper 2>/dev/null || true; fi
  if getent group whisper >/dev/null 2>&1; then groupdel whisper 2>/dev/null || true; fi
  echo
  echo "Whisper has been removed."
  echo "Model cache at $WHISPER_DATA was preserved."
  echo "To also remove model files: sudo rm -rf $WHISPER_DATA"
  echo
}

select_menu_option() {
  echo
  echo "Whisper is already installed."
  echo
  echo "Select an option:"
  echo "   1) Show server info"
  echo "   2) List available models"
  echo "   3) Pre-download a model"
  echo "   4) Remove Whisper"
  echo "   5) Exit"
  read -rp "Option: " opt
  until [[ "$opt" =~ ^[1-5]$ ]]; do
    echo "$opt: invalid selection."
    read -rp "Option: " opt
  done
  case "$opt" in
  1)
    do_show_info
    ;;
  2)
    do_list_models
    ;;
  3)
    echo
    read -rp "Model name to download: " model_to_download
    if validate_model_name "$model_to_download"; then
      do_download_model
    else
      exiterr "Unknown model '$model_to_download'. Run '--listmodels' to see valid names."
    fi
    ;;
  4)
    remove_whisper
    ;;
  5)
    exit 0
    ;;
  esac
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

auto=0
show_info=0
list_models=0
download_model=0
remove_whisper=0
assume_yes=0
model_arg=""
port_arg=""
listen_addr_arg=""
model_to_download=""

check_shell
check_root
check_os
check_os_ver
check_systemd
parse_args "$@"
check_args

# Management actions (post-install and pre-install --listmodels)
if [ "$list_models" = 1 ]; then
  do_list_models
  exit 0
fi

if [ -f "$WHISPER_CONF" ]; then
  if [ "$show_info" = 1 ]; then
    do_show_info
    exit 0
  fi
  if [ "$download_model" = 1 ]; then
    do_download_model
    exit 0
  fi
  if [ "$remove_whisper" = 1 ]; then
    remove_whisper
    exit 0
  fi
  # Interactive menu if no flags
  if [ "$auto" = 0 ]; then
    select_menu_option
    exit 0
  fi
fi

# Installation
show_welcome
select_model
select_port
[ -n "$listen_addr_arg" ] && whisper_listen_addr="$listen_addr_arg" || whisper_listen_addr="0.0.0.0"
show_config
show_setup_ready
confirm_setup
show_start_setup
install_packages
create_whisper_user
create_directories
create_venv
install_api_server
create_config
install_service
start_whisper_service
if ! wait_for_server; then
  echo
  echo "Warning: The Whisper server did not become ready within 120 seconds."
  echo "The model may still be downloading. Check logs with:"
  echo "  sudo journalctl -u whisper -n 50"
  echo
else
  finish_setup
fi
