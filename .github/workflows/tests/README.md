# Regression checks

## Running the checks

Run the dependency-free unit suite from the repository root with Python 3.9+:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/workflows/tests
```

The [build workflow](../main.yml) runs on relevant pull requests and pushes to
`main`. Its [first](../test_set_1.yml) and [second](../test_set_2.yml) test sets
cover fresh installs on Linux distributions, checksum rejection and systemd
configuration. Run installer checks only in disposable Linux environments with
systemd. The second test set also checks unit/HTTP compatibility on Python 3.9
and 3.12.

## Coverage and helpers

- Unit tests cover API compatibility, decoding and beam controls, startup
  parsing, authentication, SSE cleanup, translation-model validation and
  candidate-payload delivery. Docker-only shell bridge tests are skipped.
- [HTTP checks](check_api_http.py) exercise real FastAPI routing with stubbed
  inference, including translation errors before SSE starts. Run
  `python3 .github/workflows/tests/check_api_http.py api_server.py` with isolated
  test-only `fastapi`, `python-multipart`, `uvicorn` and `httpx` dependencies.
- [Audio decoding](check_audio_decoding.py) is an additional real CPU inference
  helper for comparing default and opt-in settings with short and long audio.
  Supply `--api`, `--audio`, `--cache` and `--output`; optional `--baseline`
  compares a reviewed older API. Use isolated inference dependencies and
  disposable caches/output directories. The helper may download models.

## Public audio fixture

The fixture is OpenAI Whisper's [jfk.flac](https://github.com/openai/whisper/blob/6e3be77e1a105e59086e3e21ff5f609fd6fa89a5/tests/jfk.flac), under its [MIT license, Copyright (c) 2022 OpenAI](https://github.com/openai/whisper/blob/6e3be77e1a105e59086e3e21ff5f609fd6fa89a5/LICENSE).
[Fixture preparation](prepare_fixture.sh) pins the revision and verifies its
checksum. No audio binary is committed here; preserve upstream attribution and
the license when redistributing it. The long decoding fixture adds repeated
speech and synthetic noise rather than reproducing a private recording.

HTTP checks use stubbed inference. Real CPU checks record versions, transcripts
and timing, but do not establish CUDA quality or guarantee that a setting
eliminates every hallucination.
