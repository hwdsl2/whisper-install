---
name: Bug report
about: Tell us about a problem you are experiencing
title: ''
labels: ''
assignees: ''

---
**Checklist**

- [ ] I read the [README](https://github.com/hwdsl2/whisper-install/blob/main/README.md) or the relevant section
- [ ] I searched existing [Issues](https://github.com/hwdsl2/whisper-install/issues?q=is%3Aissue)
- [ ] This issue is about the Whisper install script/config/API, not only faster-whisper itself

<!---
If this is a reproducible bug in the transcription engine itself, it may belong in faster-whisper: https://github.com/SYSTRAN/faster-whisper. This project uses faster-whisper as its runtime engine; OpenAI compatibility refers to the API shape and Whisper model family.
--->

**Describe the issue**
A clear and concise description of the problem.

**To Reproduce**
Steps to reproduce the behavior:

1. ...
2. ...

**Expected behavior**
A clear and concise description of what you expected to happen.

**Server environment**
- OS and version: [e.g. Ubuntu 24.04, Debian 12]
- Hosting provider (if applicable): [e.g. AWS, GCP, home server]
- CPU architecture: [e.g. amd64, arm64]
- Install or management command used: [e.g. `sudo bash whisper.sh --auto ...`]

**Configuration**
Remove secrets, keys, tokens and private URLs before posting.

- Model and port/listen address:
- API endpoint and request parameters, if relevant:
- Audio format/size, if relevant:
- Relevant `/etc/whisper/whisper.conf` snippets with secrets removed:

**API request details**
If the issue involves an API request, include endpoint, parameters, audio format/size and response format. Remove secrets before posting.

**Logs**
Add relevant logs with secrets removed.

```bash
sudo systemctl status whisper
sudo journalctl -u whisper -n 50
```

**Additional context**
Add any other context about the problem here.
