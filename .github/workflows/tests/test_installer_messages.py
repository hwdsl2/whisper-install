"""Installer download diagnostics without network access or root execution."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class InstallerMessageTests(unittest.TestCase):
    def run_download(self, matching):
        source = (ROOT / "whisper-install.sh").read_text()
        exiterr = next(line for line in source.splitlines() if line.startswith("exiterr()"))
        body = source.split("download_api_server() {", 1)[1].split("\n}\n", 1)[0]
        script = (
            'set -eu\n'
            'test_actual_sha256=$1\n'
            'WS_API_URL=https://example.invalid/api_server.py\n'
            'WS_API_SHA256=' + "a" * 64 + '\n'
            # Stub external downloads and checksum output to exercise both
            # branches of the real helper. mktemp and file cleanup remain real.
            'wget() { return 0; }\n'
            'curl() { return 1; }\n'
            'sha256sum() { printf "%s  %s\\n" "$test_actual_sha256" "$1"; }\n'
            + exiterr + '\ndownload_api_server() {' + body + '\n}\n'
            'download_api_server\n'
            'printf "verified:%s\\n" "$WS_API_TMP"\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                ["bash", "-c", script, "installer-message-test", ("a" if matching else "b") * 64],
                capture_output=True, text=True, timeout=10,
                env=dict(os.environ, TMPDIR=directory, LC_ALL="C"),
            )
            remaining = list(Path(directory).iterdir())
            if matching:
                self.assertEqual(len(remaining), 1)
                self.assertIn("verified:" + str(remaining[0]), result.stdout)
            else:
                self.assertEqual(remaining, [], "Unverified download was not removed")
            return result

    def test_checksum_mismatch_explains_safe_recovery(self):
        result = self.run_download(matching=False)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("verified:", result.stdout)
        self.assertEqual(
            result.stderr,
            "Error: Whisper API server checksum verification failed.\n"
            "Installation aborted. No installation changes were made.\n\n"
            "Download the latest installer from:\n"
            "https://github.com/hwdsl2/whisper-install\n\n"
            "If verification still fails with the latest installer, report the issue.\n"
            "Do not bypass checksum verification.\n",
        )

    def test_matching_checksum_continues_without_recovery_warning(self):
        result = self.run_download(matching=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
