# Changelog

Notable changes to the Whisper installer and API server are documented here.

Downloading or rerunning the installer does not upgrade an existing service.

## 2026-10-17

### Added

- Added `WHISPER_CONDITION_ON_PREVIOUS_TEXT` and `WHISPER_NO_REPEAT_NGRAM_SIZE`
  for tuning repetition-prone recordings. Defaults preserve previous decoding
  behavior; malformed settings prevent service startup.

## 2026-10-05

### Fixed

- Restored audio-decoding compatibility by excluding PyAV 19, which removed
  an option still used by faster-whisper.

## 2026-09-07

### Compatibility

- Raised the minimum Debian version from 11 to 12, including for
  management commands on existing installations.

## 2026-07-10

### Added

- Added a per-request `beam` override for transcription and translation,
  bounded by `WHISPER_MAX_REQUEST_BEAM` (default: 10).

## 2026-06-25

### Changed

- Transcription and translation now reject `temperature` values outside 0-1
  with HTTP 400.

## 2026-06-21

### Added

- Fresh installations now generate an API key by default. Retrieve it with
  `--showkey` or `--getkey`; authenticated requests use
  `Authorization: Bearer <key>`.

### Changed

- Unsupported OpenAI-only diarization and logprob options now return HTTP 400
  instead of being silently ignored.

## 2026-06-17

### Changed

- Limited uploaded audio to 1024 MB by default; configure
  `WHISPER_MAX_UPLOAD_MB` to change the limit or set it to `0` to disable it.

## 2026-06-16

### Fixed

- Corrected subtitle timestamp rounding for SRT and VTT output.

## Earlier notable changes

- Added systemd-based setup with a dedicated service user, persistent model
  caching, and configurable model, port, and listen address.
- Added OpenAI-compatible transcription and English-translation endpoints
  and word-level timestamps.
- Added OpenAI-compatible streaming with `transcript.text.delta` and
  `transcript.text.done` events.
