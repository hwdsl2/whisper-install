[English](README.md) | [简体中文](README-zh.md) | [繁體中文](README-zh-Hant.md) | [Русский](README-ru.md)

# Whisper Speech-to-Text Auto Setup Script

[![Build Status](https://github.com/hwdsl2/whisper-install/actions/workflows/main.yml/badge.svg)](https://github.com/hwdsl2/whisper-install/actions/workflows/main.yml) &nbsp;[![License: MIT](docs/images/license.svg)](https://opensource.org/licenses/MIT)

Whisper speech-to-text server installer for Ubuntu, Debian, AlmaLinux, Rocky Linux, CentOS, RHEL and Fedora.

This script installs and configures a self-hosted [Whisper](https://github.com/openai/whisper) speech-to-text API server powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper), providing OpenAI-compatible `/v1/audio/transcriptions` and `/v1/audio/translations` endpoints. Transcribe and translate audio files using any app that supports the OpenAI audio API.

**Features:**

- Fully automated Whisper server setup, no user input needed
- Supports interactive install using custom options
- Supports pre-downloading models and managing the server
- OpenAI-compatible `POST /v1/audio/transcriptions` and `POST /v1/audio/translations` endpoints — switch any app with a one-line change
- Streaming transcription — receive segments via SSE as they are decoded, with no waiting for the full file
- Word-level timestamps — per-word start/end times and confidence scores in `verbose_json` output
- Multiple output formats: `json`, `text`, `verbose_json`, `srt`, `vtt`
- Offline/air-gapped mode — run without internet access using pre-cached models (`WHISPER_LOCAL_ONLY`)
- Audio stays on your server — no data sent to third parties
- Installs Whisper as a systemd service with a dedicated system user
- Models downloaded from HuggingFace and cached in `/var/lib/whisper`

**Also available:**

- AI stack: [Self-Hosted AI Stack](https://github.com/hwdsl2/self-hosted-ai-stack)
- Docker-based AI services: [Whisper](https://github.com/hwdsl2/docker-whisper), [Kokoro](https://github.com/hwdsl2/docker-kokoro), [Embeddings](https://github.com/hwdsl2/docker-embeddings), [LiteLLM](https://github.com/hwdsl2/docker-litellm), [Ollama](https://github.com/hwdsl2/docker-ollama), [Docling](https://github.com/hwdsl2/docker-docling), [MCP Gateway](https://github.com/hwdsl2/docker-mcp-gateway)
- Book: [The Self-Hosted AI Builder’s Guide](https://books2read.com/aiguide?store=amazon) — use this service in a complete private AI stack

## Community

- 📬 [Subscribe for project updates](https://selfhostedstack.beehiiv.com/subscribe?utm_campaign=ai) (1–2 emails/month) — get free AI and VPN deployment guides (PDF)
- 💬 Join the [r/selfhostedstack](https://www.reddit.com/r/selfhostedstack/) community for discussions and showcases
- ⭐ Star the repository if you find it useful — it helps others discover it

<details>
<summary>Self-hosted VPN & networking projects</summary>

- [Setup IPsec VPN](https://github.com/hwdsl2/setup-ipsec-vpn)
- [IPsec VPN on Docker](https://github.com/hwdsl2/docker-ipsec-vpn-server)
- [WireGuard](https://github.com/hwdsl2/docker-wireguard)
- [OpenVPN](https://github.com/hwdsl2/docker-openvpn)
- [Headscale](https://github.com/hwdsl2/docker-headscale)

</details>

## Requirements

- A Linux server (cloud server, VPS, dedicated server or home server)
- Python 3.9 or higher (the script installs it automatically on supported distros)
- At least **700 MB RAM** for the default `base` model (see [model table](#available-models))
- Internet access for the initial model download (the model is cached locally afterwards). Not required if using `WHISPER_LOCAL_ONLY` with pre-cached models.

**Note:** For internet-facing deployments, using a [reverse proxy](#using-a-reverse-proxy) to add HTTPS is **strongly recommended**. When using a reverse proxy, set `WHISPER_LISTEN_ADDR=127.0.0.1` in `/etc/whisper/whisper.conf` to prevent direct access to the unencrypted port.

## Installation

Download the script on your Linux server:

```bash
wget -O whisper.sh https://github.com/hwdsl2/whisper-install/raw/main/whisper-install.sh
```

**Option 1:** Auto install with default options.

```bash
sudo bash whisper.sh --auto
```

This installs the `base` model (~145 MB) on port `9000`. The model is downloaded from HuggingFace on first start.

**Option 2:** Auto install with custom options.

```bash
sudo bash whisper.sh --auto --model small --port 9000
```

**Option 3:** Interactive install using custom options.

```bash
sudo bash whisper.sh
```

<details>
<summary>
Click here if you are unable to download.
</summary>

You may also use `curl` to download:

```bash
curl -fL -o whisper.sh https://github.com/hwdsl2/whisper-install/raw/main/whisper-install.sh
```

If you are unable to download, open [whisper-install.sh](whisper-install.sh), then click the `Raw` button on the right. Press `Ctrl/Cmd+A` to select all, `Ctrl/Cmd+C` to copy, then paste into your favorite editor.
</details>

<details>
<summary>
View usage information for the script.
</summary>

```
Usage: bash whisper.sh [options]

Options:

  --showinfo                           show server info (model, endpoint, API docs)
  --showkey                            show the API key, if configured
  --getkey                             output the API key (machine-readable, no decoration)
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
```
</details>

## After installation

On first run, the script:
1. Installs system packages: `python3`, `python3-venv`, `curl`
2. Creates a `whisper` system user and group
3. Creates a Python virtual environment at `/opt/whisper/venv`
4. Installs `faster-whisper`, `fastapi`, `uvicorn`, and `python-multipart`
5. Generates an API key for fresh installs
6. Writes the configuration to `/etc/whisper/whisper.conf`
7. Installs and starts the `whisper` systemd service

The first start will download the selected model from HuggingFace. This can take several minutes depending on the model size and network speed. The model is cached in `/var/lib/whisper` and reused on subsequent starts.

Check service status and logs:

```bash
sudo systemctl status whisper
sudo journalctl -u whisper -n 50
```

Once you see "Whisper speech-to-text server is ready", transcribe your first audio file:

```bash
API_KEY=$(sudo bash whisper.sh --getkey)

curl http://<server-ip>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@audio.mp3 -F model=whisper-1
```

**Response:**
```json
{"text": "Your transcribed text appears here."}
```

**Tip:** Need a sample audio file to test? Download this English speech sample (WAV, MIT License) from the [Azure Samples](https://github.com/Azure-Samples/cognitive-services-speech-sdk) repository:

```bash
curl -L -o sample_speech.wav \
    "https://github.com/Azure-Samples/cognitive-services-speech-sdk/raw/master/sampledata/audiofiles/katiesteve.wav"

curl http://<server-ip>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@sample_speech.wav \
  -F model=whisper-1
```

## API reference

The API is compatible with OpenAI's [audio transcription](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create) and [audio translation](https://developers.openai.com/api/reference/resources/audio/subresources/translations/methods/create) endpoints. Any application already calling `https://api.openai.com/v1/audio/transcriptions` can switch to self-hosted by setting:

OpenAI-only transcription options such as `gpt-4o-transcribe-diarize`, `response_format=diarized_json`, `include=logprobs`, `chunking_strategy`, `known_speaker_names`, and `known_speaker_references` are not supported and return `400`.

```
OPENAI_BASE_URL=http://<server-ip>:9000
```

### Transcribe audio

```
POST /v1/audio/transcriptions
Content-Type: multipart/form-data
```

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `file` | file | ✅ | Audio file. Supported formats: `mp3`, `mp4`, `m4a`, `wav`, `webm`, `ogg`, `flac`, and all other formats supported by ffmpeg. |
| `model` | string | ✅ | Pass `whisper-1` (value is accepted but the active model is always used). |
| `language` | string | — | BCP-47 language code (e.g. `en`, `fr`, `zh`). Overrides `WHISPER_LANGUAGE` for this request. |
| `prompt` | string | — | Optional text to guide the model's style or continue a previous segment. |
| `response_format` | string | — | Output format. Default: `json`. See [response formats](#response-formats). Ignored when `stream=true`. OpenAI-only `diarized_json` is not supported. |
| `temperature` | float | — | Sampling temperature (0–1). Default: `0`. |
| `stream` | boolean | — | Enable SSE streaming. When `true`, segments are returned as `text/event-stream` events as they are decoded. Default: `false`. |
| `timestamp_granularities[]` | array | — | Timestamp granularities to populate. Values: `word`, `segment`. When `word` is included, `verbose_json` output includes a top-level `words` array with per-word timing and confidence. Default: `["segment"]`. |

**Local faster-whisper extension:** You can set `beam` to override `WHISPER_BEAM` for a single transcription or translation request. This is not part of the OpenAI API schema, so do not send it to the hosted OpenAI API or strict OpenAI-compatible gateways. The default per-request cap is `10` (`WHISPER_MAX_REQUEST_BEAM`); set that variable to `0` to disable the cap. Beam search mainly affects deterministic decoding when `temperature=0`.

**Example:**

```bash
API_KEY=$(sudo bash whisper.sh --getkey)

curl http://<server-ip>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@meeting.m4a \
  -F model=whisper-1 \
  -F language=en
```

If API key authentication is disabled, omit the `Authorization` header.

### Response formats

| `response_format` | Description |
|---|---|
| `json` | `{"text": "..."}` — default, matches OpenAI's basic response |
| `text` | Plain text, no JSON wrapper |
| `verbose_json` | Full JSON with language, duration, per-segment timestamps, log-probabilities |
| `srt` | SubRip subtitle format (`.srt`) |
| `vtt` | WebVTT subtitle format (`.vtt`) |

**Example — stream segments as they are decoded:**

```bash
curl http://<server-ip>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@long-audio.mp3 \
  -F model=whisper-1 \
  -F stream=true
```

**SSE response** (uses the [OpenAI streaming transcription protocol](https://developers.openai.com/api/docs/guides/speech-to-text#streaming)):

```
data: {"type":"transcript.text.delta","delta":"Hello, how are you?"}

data: {"type":"transcript.text.delta","delta":" I'm doing well, thank you."}

data: {"type":"transcript.text.done","text":"Hello, how are you? I'm doing well, thank you."}

data: [DONE]
```

The first delta typically arrives within 1–3 seconds of upload. Each `transcript.text.delta` event contains the incremental text for the segment just decoded. The final `transcript.text.done` event contains the full assembled transcript, equivalent to the standard `json` response.

<details>
<summary><strong>Example — stream from a browser using <code>fetch</code></strong></summary>

```javascript
const form = new FormData();
form.append("file", audioBlob, "audio.webm");
form.append("model", "whisper-1");
form.append("stream", "true");

const res = await fetch("http://<server-ip>:9000/v1/audio/transcriptions", {
  method: "POST",
  headers: { Authorization: `Bearer ${apiKey}` },
  body: form,
});

const reader = res.body.getReader();
const decoder = new TextDecoder();
let buffer = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  // SSE frames are separated by "\n\n"; split and process complete frames
  const frames = buffer.split("\n\n");
  buffer = frames.pop(); // keep any incomplete trailing frame
  for (const frame of frames) {
    if (!frame.startsWith("data: ")) continue;
    const payload = frame.slice(6);
    if (payload.startsWith("[DONE]")) break;
    const event = JSON.parse(payload);
    if (event.type === "transcript.text.delta") console.log(event.delta);
    if (event.type === "transcript.text.done") console.log("Full text:", event.text);
  }
}
```

</details>

**Example — get SRT subtitles:**

```bash
curl http://<server-ip>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@video.mp4 \
  -F model=whisper-1 \
  -F response_format=srt
```

**Example — verbose JSON with timestamps:**

```bash
curl http://<server-ip>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@audio.mp3 \
  -F model=whisper-1 \
  -F response_format=verbose_json
```

**Example — word-level timestamps:**

```bash
curl http://<server-ip>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@audio.mp3 \
  -F model=whisper-1 \
  -F response_format=verbose_json \
  -F "timestamp_granularities[]=word"
```

When `timestamp_granularities[]` includes `word`, the `verbose_json` response includes a top-level `words` array:

```json
{
  "text": "Hello world.",
  "words": [
    {"word": "Hello", "start": 0.0, "end": 0.42, "probability": 0.98},
    {"word": "world.", "start": 0.42, "end": 0.88, "probability": 0.97}
  ],
  "segments": [...]
}
```

### Translate audio

```
POST /v1/audio/translations
Content-Type: multipart/form-data
```

Translates audio in any language to English text. Compatible with [OpenAI's audio translation endpoint](https://developers.openai.com/api/reference/resources/audio/subresources/translations/methods/create). Accepts the common translation parameters. The output is always in English.

> **Note:** Translation is not supported with English-only (`.en`) models. Use a multilingual model such as `base`, `small`, or `large-v3-turbo`.

**Example:**

```bash
curl http://<server-ip>:9000/v1/audio/translations \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@french-audio.mp3 \
  -F model=whisper-1
```

### List models

```
GET /v1/models
```

Returns the active model in OpenAI-compatible format.

```bash
curl http://<server-ip>:9000/v1/models \
  -H "Authorization: Bearer $API_KEY"
```

### Interactive API docs

An interactive Swagger UI is available at:

```
http://<server-ip>:9000/docs
```

## Available models

| Name | Disk | RAM (approx) | Notes |
|---|---|---|---|
| `tiny` | ~75 MB | ~250 MB | Fastest; lower accuracy |
| `tiny.en` | ~75 MB | ~250 MB | English-only variant |
| `base` | ~145 MB | ~700 MB | Good balance — **default** |
| `base.en` | ~145 MB | ~700 MB | English-only variant |
| `small` | ~465 MB | ~1.5 GB | Better accuracy |
| `small.en` | ~465 MB | ~1.5 GB | English-only variant |
| `medium` | ~1.5 GB | ~5 GB | High accuracy |
| `medium.en` | ~1.5 GB | ~5 GB | English-only variant |
| `large-v1` | ~3 GB | ~10 GB | Older large model |
| `large-v2` | ~3 GB | ~10 GB | Very high accuracy |
| `large-v3` | ~3 GB | ~10 GB | Best accuracy |
| `large-v3-turbo` | ~1.6 GB | ~6 GB | Fast + high accuracy ⭐ |
| `turbo` | ~1.6 GB | ~6 GB | Alias for `large-v3-turbo` |

> **Tip:** `large-v3-turbo` offers accuracy close to `large-v3` at roughly half the resource cost. It is the recommended upgrade path from `base` for most deployments.

**Notes:**
- English-only (`.en`) variants are slightly faster for English audio.
- INT8 quantization (default) reduces RAM usage by approximately 50%.

## Managing Whisper

After setup, run the script again to manage your server.

**Show server info:**

```bash
sudo bash whisper.sh --showinfo
```

**Show API key:**

```bash
sudo bash whisper.sh --showkey
```

For scripts, output only the raw key:

```bash
sudo bash whisper.sh --getkey
```

**List available models:**

```bash
sudo bash whisper.sh --listmodels
```

**Pre-download a model:**

```bash
sudo bash whisper.sh --downloadmodel large-v3-turbo
```

Pre-downloading a model avoids a delay when switching models. After downloading, update `WHISPER_MODEL` in the configuration file and restart the service.

**Remove Whisper:**

```bash
sudo bash whisper.sh --uninstall
```

Model files in `/var/lib/whisper` are preserved. To also remove them:

```bash
sudo rm -rf /var/lib/whisper
```

**Show help:**

```bash
sudo bash whisper.sh --help
```

You may also run the script without arguments for an interactive management menu.

## Configuration

The configuration file is at `/etc/whisper/whisper.conf`. Edit this file to change settings, then restart the service:

```bash
sudo systemctl restart whisper
```

All variables are optional. If not set, defaults are used automatically.

| Variable | Description | Default |
|---|---|---|
| `WHISPER_MODEL` | Whisper model to use. See [model table](#available-models) for options. | `base` |
| `WHISPER_PORT` | TCP port for the API server (1–65535). | `9000` |
| `WHISPER_LISTEN_ADDR` | Listen address for the API server. Use `0.0.0.0` to listen on all interfaces, or `127.0.0.1` for local access only. | `0.0.0.0` |
| `WHISPER_LANGUAGE` | Default transcription language. BCP-47 code (e.g. `en`, `fr`, `zh`) or `auto` to autodetect. | `auto` |
| `WHISPER_DEVICE` | Compute device. | `cpu` |
| `WHISPER_COMPUTE_TYPE` | Quantization type. `int8` is recommended for CPU. | `int8` |
| `WHISPER_THREADS` | CPU threads for inference. Set to the number of physical cores for best latency. | `2` |
| `WHISPER_BEAM` | Beam size for transcription and translation decoding. Higher values may improve accuracy at the cost of speed. Use `1` for fastest (greedy) decoding. | `5` |
| `WHISPER_MAX_REQUEST_BEAM` | Maximum beam size allowed for the per-request `beam` override. Set to `0` to disable this limit. | `10` |
| `WHISPER_MAX_UPLOAD_MB` | Maximum uploaded audio file size in MB. Requests above this limit return HTTP 413. Set to `0` to disable the limit. | `1024` |
| `WHISPER_API_KEY` | Optional Bearer token. Fresh installs auto-generate one. If set, all API requests must include `Authorization: Bearer <key>`. Set explicitly empty to disable authentication. | Auto-generated for fresh installs |
| `WHISPER_LOG_LEVEL` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. | `INFO` |
| `WHISPER_LOCAL_ONLY` | When set to any non-empty value, disables all HuggingFace model downloads. For offline or air-gapped deployments with pre-cached models. | *(not set)* |
| `WHISPER_WORD_TIMESTAMPS` | When set to `true`, enables word-level timestamps globally for all requests. The `verbose_json` output will include a top-level `words` array with per-word timing and confidence. Can also be enabled per-request via `timestamp_granularities[]=word`. | *(not set)* |

## Switching models

1. Pre-download the new model (optional but recommended):
   ```bash
   sudo bash whisper.sh --downloadmodel small
   ```
2. Edit the configuration file:
   ```bash
   sudo nano /etc/whisper/whisper.conf
   # Set: WHISPER_MODEL=small
   ```
3. Restart the service:
   ```bash
   sudo systemctl restart whisper
   ```

## Securing your server

If your Whisper server is reachable from the public internet — even briefly — apply at minimum these protections. Whisper is CPU/GPU-intensive, so an unauthenticated endpoint can be abused to burn your compute resources.

**1. Use an API key.** Fresh installs auto-generate an API key. Display it with `sudo bash whisper.sh --showkey`, or use `sudo bash whisper.sh --getkey` in scripts. Existing configuration files are not modified; if an existing install has no key, set `WHISPER_API_KEY` in `/etc/whisper/whisper.conf` to enable authentication manually. All authenticated requests must include `Authorization: Bearer <key>`.

```bash
# Generate a 32-byte random key
openssl rand -hex 32
```

**2. Bind to localhost when fronted by a reverse proxy.** Set `WHISPER_LISTEN_ADDR=127.0.0.1` in `/etc/whisper/whisper.conf` so the unencrypted port is not reachable directly from outside the host. Restart with `sudo systemctl restart whisper`.

**3. Limit upload size.** The server rejects uploads above `WHISPER_MAX_UPLOAD_MB` (default `1024`). For internet-facing deployments, also configure your reverse proxy to reject oversized uploads (e.g. nginx `client_max_body_size 100M;`) before they reach the app.

**4. Mind the log level.** `WHISPER_LOG_LEVEL=DEBUG` may write transcript text to logs. Keep it at `INFO` or higher on shared systems.

**5. Enable CORS at the proxy if calling from a browser.** The server does not set `Access-Control-Allow-Origin` headers by default; add them at your reverse proxy if you intend to call the API directly from a web page on a different origin.

**6. Consider rate limiting.** Place a rate-limit (e.g. nginx `limit_req_zone`, Caddy `rate_limit`) in front of the server to cap concurrent transcriptions per client IP.

## Using a reverse proxy

For internet-facing deployments, place a reverse proxy in front of Whisper to handle HTTPS termination.

**Example with [Caddy](https://caddyserver.com/docs/)** (automatic TLS via Let's Encrypt):

```
whisper.example.com {
  reverse_proxy localhost:9000
}
```

**Example with nginx:**

```nginx
server {
    listen 443 ssl;
    server_name whisper.example.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Audio files can be large — increase the upload limit as needed
    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;       # required for chunked streaming (SSE)
        proxy_read_timeout 300s;
    }
}
```

## Using with other AI services

Whisper can be used as the speech-to-text service in a broader self-hosted AI setup.

For full and lightweight Docker Compose stacks, manual `docker run` examples, and voice/RAG/MCP pipeline examples with Kokoro, Embeddings, LiteLLM, Ollama, Docling, and MCP Gateway, see [Self-Hosted AI Stack](https://github.com/hwdsl2/self-hosted-ai-stack).

## Auto install using custom options

```bash
sudo bash whisper.sh --auto --model base --port 9000
```

All install options are optional when using `--auto`. Defaults: model `base`, port `9000`, listen address `0.0.0.0`.

## Technical details

- OS support: Ubuntu 22.04+, Debian 11+, AlmaLinux/Rocky/CentOS 9+, RHEL 9+, Fedora
- Runtime: Python 3.9+ (virtual environment at `/opt/whisper/venv`)
- STT engine: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) with CTranslate2 (INT8 by default)
- API framework: [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- API server: [`api_server.py`](api_server.py) (installed to `/opt/whisper/api_server.py`)
- Audio decoding: [PyAV](https://github.com/PyAV-Org/PyAV) (bundled FFmpeg libraries — no system `ffmpeg` required)
- Data directory: `/var/lib/whisper` (model cache, persistent across upgrades)
- Config file: `/etc/whisper/whisper.conf`
- Service: `whisper.service` (systemd, runs as dedicated `whisper` system user)

## License

Copyright (C) 2026 Lin Song   
This work is licensed under the [MIT License](https://opensource.org/licenses/MIT).

**faster-whisper** is Copyright (C) SYSTRAN, and is distributed under the [MIT License](https://github.com/SYSTRAN/faster-whisper/blob/master/LICENSE).

This project is an independent setup for Whisper and is not affiliated with, endorsed by, or sponsored by OpenAI or SYSTRAN.
