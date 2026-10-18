"""Prepare checksum-enforced native installer fixtures; never used in production."""
import argparse
import hashlib
import ipaddress
from pathlib import Path
import re
from urllib.parse import urlsplit


def prepare(repo, output, base_url):
    parsed = urlsplit(base_url)
    if (parsed.scheme not in ("http", "https") or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/")
            or not ipaddress.ip_address(parsed.hostname).is_private):
        raise ValueError("Expected an explicit fixture HTTP(S) base URL")
    if (
        parsed.port is None or not 1 <= parsed.port <= 65535
        or parsed.netloc != parsed.hostname + ":" + str(parsed.port)
        or base_url.rstrip("/") != parsed.scheme + "://" + parsed.netloc
    ):
        raise ValueError("Expected a literal private-IP fixture URL with a port")
    source = (repo / "api_server.py").read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    installer = (repo / "whisper-install.sh").read_text()
    output.mkdir(parents=True, exist_ok=True)
    (output / "api_server.py").write_bytes(source)
    (output / "candidate.sha256").write_text(digest + "\n")
    for name, checksum in (("whisper.sh", digest), ("bad-checksum.sh", "0" * 64)):
        result, url_count = re.subn(
            r'^WS_API_URL="[^"\n]+"$',
            lambda _: 'WS_API_URL="' + base_url.rstrip("/") + '/api_server.py"',
            installer, flags=re.MULTILINE,
        )
        result, hash_count = re.subn(
            r'^WS_API_SHA256="[0-9a-f]{64}"$',
            lambda _: 'WS_API_SHA256="' + checksum + '"',
            result, flags=re.MULTILINE,
        )
        if (url_count, hash_count) != (1, 1):
            raise ValueError("Expected exactly one installer URL/hash pair")
        (output / name).write_text(result)
    return digest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    print(prepare(args.repo, args.output, args.base_url))
