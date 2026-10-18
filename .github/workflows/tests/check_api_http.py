"""Exercise the real HTTP stack with a deterministic, lightweight inference spy."""
import argparse
import importlib.util
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest import mock

from fastapi.testclient import TestClient


def check(source, baseline=None):
    spec = importlib.util.spec_from_file_location("checked_api", source)
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    if baseline is not None:
        old_spec = importlib.util.spec_from_file_location("baseline_api", baseline)
        old_api = importlib.util.module_from_spec(old_spec)
        old_spec.loader.exec_module(old_api)
        assert api.app.openapi() == old_api.app.openapi(), "Public OpenAPI schema changed"
    calls = []
    segment = SimpleNamespace(
        id=0, seek=0, start=0.0, end=1.0, text=" hello ", tokens=[1],
        avg_logprob=-0.1, compression_ratio=1.0, no_speech_prob=0.1,
        temperature=0.0,
        words=[SimpleNamespace(start=0.0, end=1.0, word="hello", probability=1.0)],
    )
    info = SimpleNamespace(
        language="en", language_probability=1.0, duration=1.0, duration_after_vad=1.0,
    )

    class Model:
        def transcribe(self, path, **kwargs):
            assert api._inference_lock.locked(), "Inference escaped its lock"
            assert Path(path).is_file()
            calls.append(kwargs)
            def segments():
                assert api._inference_lock.locked(), "Lazy decoding escaped its lock"
                yield segment
            return segments(), info

    def load():
        api._model = Model()
        api._model_name = "tiny"

    with tempfile.TemporaryDirectory() as directory:
        with mock.patch.object(api.tempfile, "tempdir", directory):
            for condition, ngram in (("", ""), ("true", "0"), ("false", "3")):
                env = {
                    "WHISPER_API_KEY": "synthetic-http-test-key",
                    "WHISPER_CONDITION_ON_PREVIOUS_TEXT": condition,
                    "WHISPER_NO_REPEAT_NGRAM_SIZE": ngram,
                    "WHISPER_DIARIZATION": "",
                }
                with mock.patch.dict(os.environ, env):
                    with mock.patch.object(api, "_load_model", side_effect=load):
                        with TestClient(api.app) as client:
                            headers = {"Authorization": "Bearer synthetic-http-test-key"}
                            for auth in ({}, {"Authorization": "Bearer wrong"}):
                                assert client.get("/v1/models", headers=auth).status_code == 401
                            assert client.get("/health").status_code == 200
                            for endpoint, task in (
                                ("transcriptions", "transcribe"), ("translations", "translate")
                            ):
                                for stream in (False, True):
                                    response = client.post(
                                        "/v1/audio/" + endpoint, headers=headers,
                                        files={"file": ("audio.wav", b"fixture audio", "audio/wav")},
                                        data={"model": "whisper-1", "stream": str(stream).lower()},
                                    )
                                    assert response.status_code == 200, response.text
                                    call = calls[-1]
                                    assert call["condition_on_previous_text"] is (condition != "false")
                                    assert call["no_repeat_ngram_size"] == int(ngram or "0")
                                    assert call["task"] == task
                                    if stream:
                                        assert "transcript.text.done" in response.text
                                        assert "data: [DONE]" in response.text
                                    else:
                                        assert response.json() == {"text": "hello"}
                            for response_format in ("text", "verbose_json", "srt", "vtt"):
                                response = client.post(
                                    "/v1/audio/transcriptions", headers=headers,
                                    files={"file": ("audio.wav", b"fixture audio")},
                                    data={"model": "whisper-1", "response_format": response_format},
                                )
                                assert response.status_code == 200, response.text
                            previous_calls = len(calls)
                            with mock.patch.object(api, "_max_upload_bytes", 1):
                                response = client.post(
                                    "/v1/audio/transcriptions", headers=headers,
                                    files={"file": ("audio.wav", b"oversized")},
                                    data={"model": "whisper-1"},
                                )
                                assert response.status_code == 413
                                assert len(calls) == previous_calls
                            assert not list(Path(directory).iterdir()), "Upload files leaked"
            with mock.patch.dict(os.environ, {
                "WHISPER_API_KEY": "", "WHISPER_CONDITION_ON_PREVIOUS_TEXT": "",
                "WHISPER_NO_REPEAT_NGRAM_SIZE": "", "WHISPER_DIARIZATION": "",
            }):
                with mock.patch.object(api, "_load_model", side_effect=load):
                    with TestClient(api.app) as client:
                        assert client.get("/v1/models").status_code == 200
            with mock.patch.dict(os.environ, {"WHISPER_NO_REPEAT_NGRAM_SIZE": "01"}):
                with mock.patch.object(api, "_load_model") as load_model:
                    try:
                        with TestClient(api.app):
                            raise AssertionError("Invalid startup accepted")
                    except ValueError as error:
                        assert "WHISPER_NO_REPEAT_NGRAM_SIZE" in str(error)
                    load_model.assert_not_called()
    print("HTTP defaults, overrides, task/transport parity, formats, auth and locks: OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("api", type=Path)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    check(args.api.resolve(), args.baseline)
