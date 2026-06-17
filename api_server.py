#!/usr/bin/env python3
"""
Whisper Speech-to-Text API Server
Provides OpenAI-compatible /v1/audio/transcriptions and
/v1/audio/translations endpoints powered by faster-whisper.

https://github.com/hwdsl2/whisper-install

Copyright (C) 2026 Lin Song <linsongui@gmail.com>

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
from typing import List, Optional

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

_model = None       # WhisperModel instance
_model_name = None  # name as loaded (e.g. "base")
_beam_size = 5      # beam size used for transcription
_word_timestamps = False  # default for word-level timestamps
_max_upload_bytes = 1024 * 1024 * 1024  # 1 GiB by default; 0 disables the limit
_UPLOAD_CHUNK_SIZE = 1024 * 1024

# Serialise all inference calls (batch and streaming) so that CTranslate2 is
# never called concurrently from multiple threads.
_inference_lock = threading.Lock()

def _env_int(name: str, default: int) -> int:
    """Read an integer env var, falling back to ``default`` when unset or empty.

    ``os.environ.get(name, default)`` only applies the default when the variable
    is absent. systemd's ``EnvironmentFile=`` directive sets bare ``VAR=`` lines
    in /etc/whisper/whisper.conf as empty strings (not absent), so a user who
    clears a numeric option would otherwise hit ValueError in int(). Treat
    empty/whitespace values as "use the default".
    """
    val = os.environ.get(name, "").strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        logger.error(
            "Invalid value for %s: %r (expected an integer); using default %s",
            name, val, default,
        )
        return default

def _env_float(name: str, default: float) -> float:
    """Read a float env var, falling back to ``default`` when unset or empty."""
    val = os.environ.get(name, "").strip()
    if not val:
        return default
    try:
        return float(val)
    except ValueError:
        logger.error(
            "Invalid value for %s: %r (expected a number); using default %s",
            name, val, default,
        )
        return default

def _load_model() -> None:
    """Import and initialise the faster-whisper model from environment config."""
    global _model, _model_name, _beam_size, _word_timestamps, _max_upload_bytes

    from faster_whisper import WhisperModel  # deferred — keeps import fast

    model_name       = os.environ.get("WHISPER_MODEL",        "base").strip()
    device           = os.environ.get("WHISPER_DEVICE",       "cpu").strip()
    compute_type     = os.environ.get("WHISPER_COMPUTE_TYPE", "int8").strip()
    threads          = _env_int("WHISPER_THREADS", 2)
    cache_dir        = os.environ.get("HF_HOME", "/var/lib/whisper")
    local_files_only = bool(os.environ.get("WHISPER_LOCAL_ONLY", "").strip())
    _beam_size       = _env_int("WHISPER_BEAM", 5)
    _word_timestamps = os.environ.get("WHISPER_WORD_TIMESTAMPS", "").strip().lower() == "true"
    max_upload_mb    = _env_int("WHISPER_MAX_UPLOAD_MB", 1024)
    if max_upload_mb < 0:
        logger.error(
            "Invalid value for WHISPER_MAX_UPLOAD_MB: %d (expected 0 or greater); using default 1024",
            max_upload_mb,
        )
        max_upload_mb = 1024
    _max_upload_bytes = max_upload_mb * 1024 * 1024

    logger.info(
        "Loading model '%s' | device=%s compute_type=%s threads=%d beam=%d word_ts=%s max_upload_mb=%d local_only=%s cache=%s",
        model_name, device, compute_type, threads, _beam_size, _word_timestamps, max_upload_mb, local_files_only, cache_dir,
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
    """
    If WHISPER_API_KEY is set, require a matching Bearer token.
    If the env var is empty or unset the endpoint is open (no auth).
    """
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
    """Format a float second offset as an SRT or VTT timestamp string."""
    total_ms = max(0, int(round(seconds * 1000)))
    h, rem = divmod(total_ms, 3600 * 1000)
    m, rem = divmod(rem, 60 * 1000)
    s, ms = divmod(rem, 1000)
    sep = "," if fmt == "srt" else "."
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"

def _to_srt(segments) -> str:
    lines = []
    for i, seg in enumerate(segments, start=1):
        text = seg.text.strip() if hasattr(seg, "text") else seg.get("text", "").strip()
        start = seg.start if hasattr(seg, "start") else seg["start"]
        end = seg.end if hasattr(seg, "end") else seg["end"]
        lines.append(
            f"{i}\n"
            f"{_fmt_ts(start, 'srt')} --> {_fmt_ts(end, 'srt')}\n"
            f"{text}\n"
        )
    return "\n".join(lines)

def _to_vtt(segments) -> str:
    lines = ["WEBVTT\n"]
    for seg in segments:
        text = seg.text.strip() if hasattr(seg, "text") else seg.get("text", "").strip()
        start = seg.start if hasattr(seg, "start") else seg["start"]
        end = seg.end if hasattr(seg, "end") else seg["end"]
        lines.append(
            f"{_fmt_ts(start, 'vtt')} --> {_fmt_ts(end, 'vtt')}\n"
            f"{text}\n"
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
    task: str = "transcribe",
):
    """
    Async generator that yields Server-Sent Events (SSE) frames using the
    OpenAI streaming transcription protocol.

    Event types emitted (see https://developers.openai.com/api/docs/guides/speech-to-text):
      - transcript.text.delta  — incremental text as each segment is decoded
      - transcript.text.done   — final assembled transcript

    Inference runs in a thread-pool worker so the event loop stays responsive
    while the CPU-bound model decodes the audio.  _inference_lock ensures that
    only one transcription (batch or streaming) runs at a time.

    The temporary audio file is deleted when the generator finishes (or is
    abandoned by the client).
    """
    loop = asyncio.get_running_loop()
    seg_queue: asyncio.Queue = asyncio.Queue()

    def _run() -> None:
        with _inference_lock:
            try:
                segs_gen, _ = _model.transcribe(
                    tmp_path,
                    language=lang,
                    task=task,
                    initial_prompt=prompt or None,
                    temperature=temperature,
                    beam_size=_beam_size,
                    vad_filter=True,
                )
                for seg in segs_gen:
                    loop.call_soon_threadsafe(seg_queue.put_nowait, seg)
            except Exception as exc:  # noqa: BLE001
                loop.call_soon_threadsafe(seg_queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(seg_queue.put_nowait, None)  # sentinel

    loop.run_in_executor(None, _run)
    text_parts: list = []

    try:
        while True:
            item = await seg_queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                logger.error("Streaming transcription error: %s", item)
                err_payload = json.dumps({
                    "error": {
                        "type": "transcription_error",
                        "message": str(item),
                    }
                })
                yield f"data: {err_payload}\n\n"
                return
            seg_text = item.text.strip()
            if seg_text:
                # Prepend space to separate from previous segments
                delta = seg_text if not text_parts else " " + seg_text
                text_parts.append(seg_text)
                payload = json.dumps({
                    "type": "transcript.text.delta",
                    "delta": delta,
                })
                yield f"data: {payload}\n\n"
        # Final frame — complete transcript (OpenAI transcript.text.done event)
        full_text = " ".join(text_parts).strip()
        yield f'data: {json.dumps({"type": "transcript.text.done", "text": full_text})}\n\n'
        yield "data: [DONE]\n\n"
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
    """Container liveness probe — used by the server to detect startup completion."""
    return {"status": "ok", "model": _model_name}

@app.get("/v1/models")
async def list_models(_auth: None = Depends(_verify_api_key)):
    """
    List the active model in OpenAI-compatible format.
    Any app that queries /v1/models before sending requests will work correctly.
    """
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

async def _handle_audio(
    task: str,
    file: UploadFile,
    model: str,
    language: Optional[str],
    prompt: Optional[str],
    response_format: str,
    temperature: float,
    stream: Optional[str],
    timestamp_granularities: Optional[List[str]] = None,
):
    """
    Shared implementation for transcription and translation endpoints.
    ``task`` is either ``"transcribe"`` or ``"translate"``.
    """
    if _model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded yet. Please retry.")

    # Block translation on English-only models
    if task == "translate" and _model_name and _model_name.endswith(".en"):
        raise HTTPException(
            status_code=400,
            detail=f"Translation is not supported with English-only model '{_model_name}'. "
                   "Use a multilingual model (e.g. base, small, large-v3-turbo).",
        )

    # Normalise the stream form field: the string "true" (case-insensitive) enables streaming.
    # Using Optional[str] instead of bool avoids Pydantic version-dependent coercion differences.
    stream_flag: bool = stream is not None and stream.strip().lower() == "true"

    # Resolve word_timestamps:
    #   timestamp_granularities (spec-compliant) > WHISPER_WORD_TIMESTAMPS env var > False
    wt_flag: bool
    if timestamp_granularities and "word" in timestamp_granularities:
        wt_flag = True
    else:
        wt_flag = _word_timestamps

    # Validate response_format (only relevant for non-streaming responses)
    valid_formats = {"json", "text", "verbose_json", "srt", "vtt"}
    if not stream_flag and response_format not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid response_format '{response_format}'. "
                   f"Must be one of: {', '.join(sorted(valid_formats))}",
        )

    # Resolve language: per-request param > WHISPER_LANGUAGE env var > None (autodetect)
    env_lang = os.environ.get("WHISPER_LANGUAGE", "auto").strip()
    if language and language.lower() != "auto":
        lang = language
    elif env_lang and env_lang.lower() != "auto":
        lang = env_lang
    else:
        lang = None  # faster-whisper autodetects when None

    # Persist uploaded bytes to a temp file so faster-whisper can open it.
    original_name = file.filename or "audio"
    suffix = os.path.splitext(original_name)[1] or ".audio"
    tmp_path: Optional[str] = None
    upload_size = 0
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            while True:
                chunk = await file.read(_UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                upload_size += len(chunk)
                if _max_upload_bytes and upload_size > _max_upload_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "Uploaded audio is too large. "
                            f"Maximum allowed size is {_max_upload_bytes // (1024 * 1024)} MB."
                        ),
                    )
                tmp.write(chunk)
    except HTTPException:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise
    except Exception as exc:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        logger.exception("Failed to save upload: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {exc}") from exc

    logger.info(
        "%s '%s' (%d bytes) | lang=%s format=%s stream=%s word_ts=%s",
        "Translating" if task == "translate" else "Transcribing",
        original_name, upload_size, lang or "auto", response_format, stream_flag, wt_flag,
    )

    # ------------------------------------------------------------------
    # Streaming path — inference runs in a thread; temp file cleaned up
    # inside the generator when the stream ends or the client disconnects.
    # Word timestamps are silently ignored in streaming mode.
    # ------------------------------------------------------------------
    if stream_flag:
        return StreamingResponse(
            _stream_sse(tmp_path, lang, prompt, temperature, task),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",   # disable nginx proxy buffering
                "Cache-Control": "no-cache",
            },
        )

    # ------------------------------------------------------------------
    # Batch path
    # ------------------------------------------------------------------
    try:
        with _inference_lock:
            segments_gen, info = _model.transcribe(
                tmp_path,
                language=lang,
                task=task,
                initial_prompt=prompt or None,
                temperature=temperature,
                beam_size=_beam_size,
                word_timestamps=wt_flag,
                vad_filter=True,
            )
            segments = list(segments_gen)  # consume the generator before the temp file is removed

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
        seg_list = []
        all_words = []
        for idx, seg in enumerate(segments):
            seg_dict = {
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
            if wt_flag and seg.words:
                all_words.extend(
                    {
                        "word": w.word.strip(),
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                        "probability": round(w.probability, 4),
                    }
                    for w in seg.words
                )
            seg_list.append(seg_dict)
        resp = {
            "task": task,
            "language": info.language,
            "language_probability": round(info.language_probability, 4),
            "duration": round(info.duration, 3),
            "duration_after_vad": round(info.duration_after_vad, 3),
            "text": full_text,
            "segments": seg_list,
        }
        if wt_flag:
            resp["words"] = all_words
        return JSONResponse(resp)

    # Default: json — matches OpenAI's minimal response shape
    return JSONResponse({"text": full_text})

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
            "decoded segment — followed by a final 'done' frame. "
            "response_format is ignored when stream=true."
        ),
    ),
    timestamp_granularities: Optional[List[str]] = Form(
        default=None,
        alias="timestamp_granularities[]",
        description=(
            "The timestamp granularities to populate for this transcription. "
            "response_format must be verbose_json. Supported values: 'word', 'segment'. "
            "Default: ['segment']."
        ),
    ),
    _auth: None = Depends(_verify_api_key),
):
    """
    Transcribe an audio file.

    Drop-in replacement for OpenAI's POST /v1/audio/transcriptions endpoint.
    Accepts the same multipart/form-data parameters and returns the same
    response shapes.

    When stream=true the response is text/event-stream (SSE) using the OpenAI
    streaming transcription protocol.  Each event carries a JSON object:
      - delta frames: {"type":"transcript.text.delta","delta":"..."}
      - final frame:  {"type":"transcript.text.done","text":"full transcript"}
      - error frame:  {"error":{"type":"...","message":"..."}}

    Supported audio formats: mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg, flac
    (all formats supported by ffmpeg).
    """
    return await _handle_audio(
        task="transcribe",
        file=file,
        model=model,
        language=language,
        prompt=prompt,
        response_format=response_format,
        temperature=temperature,
        stream=stream,
        timestamp_granularities=timestamp_granularities,
    )

@app.post("/v1/audio/translations")
async def translate(
    file: UploadFile = File(..., description="Audio file to translate to English"),
    model: str = Form(
        default="whisper-1",
        description="Model identifier (ignored — active model is used)",
    ),
    language: Optional[str] = Form(
        default=None,
        description="BCP-47 language code of the source audio (e.g. 'fr'). Omit for autodetect.",
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
            "decoded segment — followed by a final 'done' frame. "
            "response_format is ignored when stream=true."
        ),
    ),
    _auth: None = Depends(_verify_api_key),
):
    """
    Translate audio to English text.

    Drop-in replacement for OpenAI's POST /v1/audio/translations endpoint.
    Accepts the same multipart/form-data parameters and returns the same
    response shapes. The output is always in English.

    Not supported with English-only (.en) models — use a multilingual model.

    Supported audio formats: mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg, flac
    (all formats supported by ffmpeg).
    """
    return await _handle_audio(
        task="translate",
        file=file,
        model=model,
        language=language,
        prompt=prompt,
        response_format=response_format,
        temperature=temperature,
        stream=stream,
    )

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = _env_int("WHISPER_PORT", 9000)
    # Fall back to 0.0.0.0 when WHISPER_LISTEN_ADDR is unset or empty
    host = os.environ.get("WHISPER_LISTEN_ADDR", "0.0.0.0").strip() or "0.0.0.0"
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        log_level=_log_level_str.lower(),
        workers=1,  # single worker — model is loaded into process memory
    )
