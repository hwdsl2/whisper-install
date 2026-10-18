"""Regressions for native CI helpers without running Linux services."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]


class CIHelperTests(unittest.TestCase):
    def test_settings_log_check_drains_large_stream(self):
        source = (ROOT / ".github/workflows/tests/check_systemd_decoding.sh").read_text()
        body = source.split("assert_settings() {", 1)[1].split("\n}\n", 1)[0]
        helper = "assert_settings() {" + body + "\n}\n"
        script = (
            "set -euo pipefail\n"
            "ci_test_python=$1\n"
            "ci_test_match=$2\n"
            'systemctl() { printf "12345\\n"; }\n'
            'journalctl() { "$ci_test_python" -c \'import sys; '
            'marker = "Decoding options: condition_on_previous_text=True no_repeat_ngram_size=0" '
            'if sys.argv[1] == "yes" else "unrelated startup line"; '
            'sys.stdout.write(marker + "\\n" + "fixture log line\\n" * 100000)\' "$ci_test_match"; }\n'
            + helper + "assert_settings True 0\n"
        )
        for marker, expected in (("yes", 0), ("no", 1)):
            with self.subTest(marker=marker):
                result = subprocess.run(
                    ["bash", "-c", script, "ci-helper-test", sys.executable, marker],
                    capture_output=True, text=True, timeout=10,
                    env=dict(os.environ, LC_ALL="C"),
                )
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
