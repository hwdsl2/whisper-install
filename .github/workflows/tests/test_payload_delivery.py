"""Native fresh-install candidate payload regression tests."""
import ast
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

from prepare_candidate import prepare

ROOT = Path(__file__).resolve().parents[3]


class CandidateFixtureTests(unittest.TestCase):
    def test_only_url_and_hash_change_in_installer(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            digest = prepare(ROOT, output, "http://127.0.0.1:8765")
            source = (ROOT / "api_server.py").read_bytes()
            self.assertEqual((output / "api_server.py").read_bytes(), source)
            self.assertEqual(digest, hashlib.sha256(source).hexdigest())
            original = (ROOT / "whisper-install.sh").read_text().splitlines()
            for name, checksum in (("whisper.sh", digest), ("bad-checksum.sh", "0" * 64)):
                modified = (output / name).read_text().splitlines()
                # The production checksum may already match the candidate.
                # Assert exact output, not a fixed number of differing lines.
                expected = [
                    'WS_API_URL="http://127.0.0.1:8765/api_server.py"'
                    if line.startswith("WS_API_URL=")
                    else 'WS_API_SHA256="' + checksum + '"'
                    if line.startswith("WS_API_SHA256=")
                    else line
                    for line in original
                ]
                self.assertEqual(modified, expected)
                subprocess.run(["bash", "-n", str(output / name)], check=True)

    def test_anchor_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "api_server.py").write_text("pass\n")
            for installer in ('# missing anchors\n', (ROOT / "whisper-install.sh").read_text() * 2):
                (root / "whisper-install.sh").write_text(installer)
                with self.assertRaisesRegex(ValueError, "exactly one"):
                    prepare(root, root / "output", "http://127.0.0.1:8765")

    def test_unsafe_fixture_url_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for url in (
                "file:///etc/passwd", "https://example.com",
                "http://127.0.0.1:8765/a", "http://user@127.0.0.1:8765",
                'http://127.0.0.1:8765"$(id)', "http://127.0.0.1:8765\n",
            ):
                with self.subTest(url=url):
                    with self.assertRaises(ValueError):
                        prepare(ROOT, Path(directory), url)

    def test_runtime_remains_self_contained_and_python39_syntax(self):
        tree = ast.parse((ROOT / "api_server.py").read_text(), feature_version=(3, 9))
        imports = [
            item.module for item in ast.walk(tree) if isinstance(item, ast.ImportFrom)
        ]
        self.assertFalse(any(name and name.startswith(("diarizer", "decoding_options")) for name in imports))
        self.assertNotIn("sherpa_onnx", (ROOT / "api_server.py").read_text())


if __name__ == "__main__":
    unittest.main()
