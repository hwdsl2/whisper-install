# Decoding regression checks

The dependency-free suite retains the API compatibility/beam tests and adds strict
startup parsing, default preservation, propagation, authentication and SSE cleanup:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/workflows/tests
```

Run each repository's suite in a separate process. Both APIs are independently
maintained; the native API remains a self-contained file supporting Python 3.9+.
The native suite intentionally skips the Docker-only shell bridge test.

`check_api_http.py api_server.py` exercises the real FastAPI stack with a
deterministic inference spy. It requires isolated test-only `fastapi`,
`python-multipart`, `uvicorn` and `httpx` dependencies. Do not install them globally.

`check_audio_decoding.py` runs real CPU inference with `tiny`, int8, two threads,
beam 5 and fixed dependencies/model cache. It compares unset/default/opt-in options,
all short-audio task/transport combinations and a generated long recording. Its
optional `--baseline` accepts a reviewed old API for same-runtime comparisons.
Supply `--api`, `--audio`, `--cache` and `--output` paths. Keep the model/cache
and output in disposable scratch space; the helper may download the model.

## Public audio fixture

- Source: OpenAI Whisper [tests/jfk.flac](https://github.com/openai/whisper/blob/6e3be77e1a105e59086e3e21ff5f609fd6fa89a5/tests/jfk.flac).
- Immutable revision: `6e3be77e1a105e59086e3e21ff5f609fd6fa89a5`.
- SHA-256: `63a4b1e4c1dc655ac70961ffbf518acd249df237e5a0152faae9a4a836949715`.
- Repository license: [MIT, Copyright (c) 2022 OpenAI](https://github.com/openai/whisper/blob/6e3be77e1a105e59086e3e21ff5f609fd6fa89a5/LICENSE).
- The recording is public speech, not a user's private audio. No audio binary is
  committed here. Preserve the upstream attribution/license when redistributing.
- The long fixture repeats the speech twice, adds 600 seconds of seeded Gaussian
  noise plus 60 Hz hum at low amplitude, then appends the speech again. It contains
  legitimate repetition and later speech. VAD can remove the noise; it is not a
  reproduction of issue #11's private recording.

The helper records resolved inference dependency versions, fixture hashes,
transcripts and timing. CPU checks do not establish CUDA inference quality, and
these tests do not prove that any setting eliminates every hallucination.
