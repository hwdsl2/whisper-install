"""Lightweight decoding configuration and propagation regressions (no models)."""
import asyncio
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from test_api_validation import api_server, _FakeModel, _FakeUpload

CONDITION = "WHISPER_CONDITION_ON_PREVIOUS_TEXT"
NGRAM = "WHISPER_NO_REPEAT_NGRAM_SIZE"
VALID = [
    ("", "", True, 0),
    ("true", "0", True, 0),
    ("FALSE", "3", False, 3),
    ("TrUe", "2147483647", True, 2147483647),
    (" \t\r\n\v\f' false '\t", ' " 6 " ', False, 6),
    ('""', "''", True, 0),
    ('" \t "', "'\r\n'", True, 0),
]
BAD_CONDITION = [
    "yes", "1", "0", "true\nfalse", "tr ue", "truE\u00a0", "\u00a0true",
    "fal\u017fe", "'\"false\"'", "'false", 'false"', "$(true)", "T" * 10000,
]
BAD_NGRAM = [
    "-1", "+1", "01", "00", "1.5", "1_000", "2147483648", "9" * 10000,
    "\u0663", "\uff13", "3\u00a0", "\u00a03", "3\n4", "3\ninvalid",
    "3 4", "'\"3\"'", "'3", '3"', "NaN", "$(id)",
]


class DecodingOptionTests(unittest.TestCase):
    def setUp(self):
        self.saved = (
            api_server._condition_on_previous_text, api_server._no_repeat_ngram_size
        )
        self.env = mock.patch.dict(os.environ, {CONDITION: "", NGRAM: ""})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        (api_server._condition_on_previous_text,
         api_server._no_repeat_ngram_size) = self.saved

    def test_valid_values_and_normalization(self):
        for condition, ngram, expected_condition, expected_ngram in VALID:
            with self.subTest(condition=condition, ngram=ngram):
                os.environ.update({CONDITION: condition, NGRAM: ngram})
                api_server._load_decoding_options()
                self.assertIs(api_server._condition_on_previous_text, expected_condition)
                self.assertEqual(api_server._no_repeat_ngram_size, expected_ngram)

    def test_absent_values_restore_defaults(self):
        os.environ.pop(CONDITION, None)
        os.environ.pop(NGRAM, None)
        api_server._condition_on_previous_text = False
        api_server._no_repeat_ngram_size = 3
        api_server._load_decoding_options()
        self.assertIs(api_server._condition_on_previous_text, True)
        self.assertEqual(api_server._no_repeat_ngram_size, 0)

    def test_invalid_values_fail_without_changing_resolved_settings(self):
        for name, values in ((CONDITION, BAD_CONDITION), (NGRAM, BAD_NGRAM)):
            for value in values:
                with self.subTest(name=name, value=value[:80]):
                    os.environ.update({CONDITION: "false", NGRAM: "3"})
                    api_server._load_decoding_options()
                    os.environ[name] = value
                    with self.assertRaisesRegex(ValueError, name):
                        api_server._load_decoding_options()
                    self.assertIs(api_server._condition_on_previous_text, False)
                    self.assertEqual(api_server._no_repeat_ngram_size, 3)

    def test_invalid_startup_never_loads_models(self):
        async def start():
            async with api_server._lifespan(api_server.app):
                self.fail("Invalid configuration must not begin serving")
        for name, value in ((CONDITION, "yes"), (NGRAM, "2147483648")):
            with self.subTest(name=name):
                os.environ.update({CONDITION: "", NGRAM: "", name: value})
                with mock.patch.object(api_server, "_load_model") as load_model:
                    with mock.patch.object(api_server, "_load_diarizer", create=True) as diarizer:
                        with self.assertRaisesRegex(ValueError, name):
                            asyncio.run(start())
                        load_model.assert_not_called()
                        diarizer.assert_not_called()

    def test_startup_resolves_before_model_loading(self):
        os.environ.update({CONDITION: "false", NGRAM: "3"})
        async def start():
            async with api_server._lifespan(api_server.app):
                self.assertIs(api_server._condition_on_previous_text, False)
                self.assertEqual(api_server._no_repeat_ngram_size, 3)
        def check_options():
            self.assertIs(api_server._condition_on_previous_text, False)
            self.assertEqual(api_server._no_repeat_ngram_size, 3)
        with mock.patch.object(api_server, "_load_model", side_effect=check_options):
            with mock.patch.object(api_server, "_load_diarizer", create=True):
                asyncio.run(start())


class DecodingPropagationTests(unittest.TestCase):
    def setUp(self):
        self.patches = []
        for name, value in (
            ("_model", _FakeModel()), ("_model_name", "base"),
            ("_beam_size", 5), ("_max_request_beam", 10), ("_max_upload_bytes", 0),
            ("_condition_on_previous_text", True), ("_no_repeat_ngram_size", 0),
        ):
            patch = mock.patch.object(api_server, name, value)
            patch.start()
            self.patches.append(patch)
        if hasattr(api_server, "_diarization_enabled"):
            patch = mock.patch.object(api_server, "_diarization_enabled", False)
            patch.start()
            self.patches.append(patch)

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()

    def test_batch_sse_by_task_defaults_and_overrides(self):
        async def request(task, stream):
            response = await api_server._handle_audio(
                task=task, file=_FakeUpload(), model="whisper-1", language=None,
                prompt=None, response_format="json", temperature=0,
                stream="true" if stream else None, beam=None,
            )
            if stream:
                frames = [frame async for frame in response.body_iterator]
                self.assertTrue(any("transcript.text.done" in frame for frame in frames))
                self.assertIn("data: [DONE]\n\n", frames)
            else:
                self.assertEqual(response.content, {"text": "hello"})
        for condition, ngram in ((True, 0), (False, 3)):
            api_server._condition_on_previous_text = condition
            api_server._no_repeat_ngram_size = ngram
            for task in ("transcribe", "translate"):
                for stream in (False, True):
                    with self.subTest(condition=condition, ngram=ngram, task=task, stream=stream):
                        asyncio.run(request(task, stream))
                        call = api_server._model.calls[-1]
                        self.assertIs(call["condition_on_previous_text"], condition)
                        self.assertEqual(call["no_repeat_ngram_size"], ngram)
                        self.assertEqual(call["task"], task)
                        self.assertIs(call["vad_filter"], True)
                        self.assertEqual(call["beam_size"], 5)

    def test_sse_error_and_temp_cleanup(self):
        async def collect(path):
            return [frame async for frame in api_server._stream_sse(
                path, None, None, 0, 5, task="translate"
            )]
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "audio.wav"
            path.touch()
            with mock.patch.object(api_server._model, "transcribe", side_effect=RuntimeError("fixture")):
                frames = asyncio.run(collect(str(path)))
            self.assertTrue(any("transcription_error" in frame for frame in frames))
            self.assertFalse(path.exists())

    def test_authentication_is_unchanged(self):
        with mock.patch.dict(os.environ, {"WHISPER_API_KEY": "synthetic-test-key"}):
            api_server._verify_api_key("Bearer synthetic-test-key")
            for credential in (None, "Bearer wrong"):
                with self.assertRaises(api_server.HTTPException) as ctx:
                    api_server._verify_api_key(credential)
                self.assertEqual(ctx.exception.status_code, 401)
        with mock.patch.dict(os.environ, {"WHISPER_API_KEY": ""}):
            api_server._verify_api_key(None)

    def test_sse_close_cleans_temporary_upload(self):
        async def close_stream(path):
            stream = api_server._stream_sse(path, None, None, 0, 5)
            self.assertIn("transcript.text.delta", await stream.__anext__())
            await stream.aclose()
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "cancelled.wav"
            path.touch()
            asyncio.run(close_stream(str(path)))
            self.assertFalse(path.exists())


class ShellDecodingOptionTests(unittest.TestCase):
    def test_shell_matches_python_and_exports_plain_assignments(self):
        run_sh = pathlib.Path(__file__).resolve().parents[3] / "run.sh"
        if not run_sh.is_file():
            self.skipTest("Native startup uses systemd, not the Docker shell bridge")
        source = run_sh.read_text()
        helpers = source.split("normalize_decoding_option() {", 1)[1]
        helpers = "normalize_decoding_option() {" + helpers.split(
            "# End strict decoding option helpers.", 1
        )[0]
        # Source a plain assignment file into an initially unexported shell.
        # Do not execute run.sh on the host or interpolate tested values as code.
        script = (
            'exiterr() { echo "$1" >&2; exit 1; }\n' + helpers +
            '\nunset WHISPER_CONDITION_ON_PREVIOUS_TEXT WHISPER_NO_REPEAT_NGRAM_SIZE\n'
            '. "$1"\nconfigure_decoding_options\n'
            'exec "$2" -c \'import os; print(os.environ["' + CONDITION +
            '"]); print(os.environ["' + NGRAM + '"])\'\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            config = pathlib.Path(directory) / "whisper.env"
            # The file grammar differs from environment values: use a safe
            # quoting function, without evaluating expressions in the parser.
            def quote(value):
                return "'" + value.replace("'", "'\"'\"'") + "'"
            cases = [(c, n, True) for c, n, _, _ in VALID]
            cases += [(v, "0", False) for v in BAD_CONDITION]
            cases += [("true", v, False) for v in BAD_NGRAM]
            for condition, ngram, valid in cases:
                config.write_text(
                    CONDITION + "=" + quote(condition) + "\n" +
                    NGRAM + "=" + quote(ngram) + "\n"
                )
                result = subprocess.run(
                    ["bash", "-c", script, "decoding-test", str(config), sys.executable],
                    capture_output=True, text=True, timeout=10,
                )
                with self.subTest(condition=condition[:80], ngram=ngram[:80]):
                    self.assertEqual(result.returncode == 0, valid, result.stderr)
                    if valid:
                        with mock.patch.dict(os.environ, {CONDITION: condition, NGRAM: ngram}):
                            api_server._load_decoding_options()
                            self.assertEqual(
                                result.stdout.splitlines(),
                                [str(api_server._condition_on_previous_text).lower(),
                                 str(api_server._no_repeat_ngram_size)],
                            )
                    else:
                        self.assertIn("WHISPER_", result.stderr)


if __name__ == "__main__":
    unittest.main()
