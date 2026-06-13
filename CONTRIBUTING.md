# Contributing

Thanks for helping improve this project. This repository maintains the bare-metal Whisper install script; Docker image changes belong in [docker-whisper](https://github.com/hwdsl2/docker-whisper), and multi-service stack changes belong in [docker-ai-stack](https://github.com/hwdsl2/docker-ai-stack).

## Before You Start

- Search existing issues and pull requests.
- Keep changes focused and easy to review.
- For upstream `faster-whisper`, CTranslate2, or Whisper behavior, check the upstream project first.
- Do not include API keys, private audio, model files, logs with secrets, or provider credentials.

## Pull Requests

- Update `README.md` or docs when install behavior, options, service names, paths, or defaults change.
- Include the tested Linux distribution, version, architecture, and install/manage command.
- For upstream version changes, link the upstream release, tag, or commit.

## Testing

Test the smallest relevant path before opening a PR, for example:

- Run ShellCheck when editing shell scripts.
- Test install, management, or uninstall paths touched by the change.
- Check `systemctl status whisper` and relevant `journalctl` output for service changes.
- Verify model download/cache behavior when changing model defaults.
