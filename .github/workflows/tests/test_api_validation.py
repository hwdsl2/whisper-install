import importlib
import pathlib
import sys
import types
import unittest


class _HTTPException(Exception):
    def __init__(self, status_code, detail=None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class _FastAPI:
    def __init__(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
        return lambda func: func

    def post(self, *args, **kwargs):
        return lambda func: func


def _install_stubs():
    fastapi = types.ModuleType("fastapi")
    fastapi.Depends = lambda *args, **kwargs: None
    fastapi.FastAPI = _FastAPI
    fastapi.File = lambda default=..., **kwargs: default
    fastapi.Form = lambda default=..., **kwargs: default
    fastapi.Header = lambda *args, **kwargs: None
    fastapi.HTTPException = _HTTPException
    fastapi.UploadFile = object
    sys.modules["fastapi"] = fastapi

    responses = types.ModuleType("fastapi.responses")
    responses.JSONResponse = object
    responses.PlainTextResponse = object
    responses.StreamingResponse = object
    sys.modules["fastapi.responses"] = responses

    sys.modules["uvicorn"] = types.ModuleType("uvicorn")


_install_stubs()
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
api_server = importlib.import_module("api_server")


class OpenAITranscriptionCompatTests(unittest.TestCase):
    def _assert_rejected(self, **kwargs):
        params = {
            "model": "whisper-1",
            "response_format": "json",
            "include": None,
            "chunking_strategy": None,
            "known_speaker_names": None,
            "known_speaker_references": None,
        }
        params.update(kwargs)
        with self.assertRaises(api_server.HTTPException) as ctx:
            api_server._validate_openai_transcription_compat(**params)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_standard_request_passes(self):
        api_server._validate_openai_transcription_compat(
            model="whisper-1",
            response_format="json",
            include=None,
            chunking_strategy=None,
            known_speaker_names=None,
            known_speaker_references=None,
        )

    def test_rejects_diarize_model(self):
        self._assert_rejected(model="gpt-4o-transcribe-diarize")

    def test_rejects_diarize_model_case_insensitive(self):
        self._assert_rejected(model=" GPT-4O-TRANSCRIBE-DIARIZE ")

    def test_rejects_diarized_json(self):
        self._assert_rejected(response_format="diarized_json")

    def test_rejects_diarized_json_case_insensitive(self):
        self._assert_rejected(response_format=" DIARIZED_JSON ")

    def test_rejects_include_logprobs(self):
        self._assert_rejected(include=["logprobs"])

    def test_rejects_chunking_strategy(self):
        self._assert_rejected(chunking_strategy="auto")

    def test_rejects_known_speaker_names(self):
        self._assert_rejected(known_speaker_names=["agent"])

    def test_rejects_known_speaker_references(self):
        self._assert_rejected(known_speaker_references=["data:audio/wav;base64,AAAA"])

    def test_empty_optional_unsupported_fields_pass(self):
        api_server._validate_openai_transcription_compat(
            model="whisper-1",
            response_format="json",
            include=[],
            chunking_strategy="   ",
            known_speaker_names=[],
            known_speaker_references=[],
        )

    def test_merge_form_lists(self):
        self.assertEqual(api_server._merge_form_lists(["logprobs"], None), ["logprobs"])
        self.assertEqual(api_server._merge_form_lists(None, ["logprobs"]), ["logprobs"])
        self.assertIsNone(api_server._merge_form_lists(None, []))


if __name__ == "__main__":
    unittest.main()
