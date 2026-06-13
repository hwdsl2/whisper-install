---
name: 错误报告
about: 请使用这个模板来提交 bug
title: ''
labels: ''
assignees: ''

---
**任务列表**

- [ ] 我已阅读[自述文件](https://github.com/hwdsl2/whisper-install/blob/main/README-zh.md)或相关章节
- [ ] 我搜索了已有的 [Issues](https://github.com/hwdsl2/whisper-install/issues?q=is%3Aissue)
- [ ] 这个问题是关于 Whisper 安装脚本/配置/API，而不只是 faster-whisper 本身

<!---
如果你确认问题属于上游项目本身，请考虑在相应上游项目提交 issue：[faster-whisper](https://github.com/SYSTRAN/faster-whisper)。
--->

**问题描述**
使用清楚简明的语言描述这个问题。

**重现步骤**
重现该问题的步骤：

1. ...
2. ...

**期待的正确结果**
简要描述你期望发生的结果。

**服务器环境**
- 操作系统和版本: [例如 Ubuntu 24.04, Debian 12]
- 服务提供商（如果适用）: [例如 AWS, GCP, 家用服务器]
- CPU 架构: [例如 amd64, arm64]
- 使用的安装或管理命令: [例如 `sudo bash whisper.sh --auto ...`]

**配置**
发布前请删除 secrets、密钥、tokens 和私有 URL。

- 模型和端口/监听地址：
- API 接口和请求参数（如果相关）：
- 音频格式/大小（如果相关）：
- 去除敏感信息后的 `/etc/whisper/whisper.conf` 相关片段：

**API 请求细节**
如果问题涉及 API 请求，请包含接口、参数、音频格式/大小和响应格式。发布前请删除敏感信息。

**日志**
请添加相关日志，并删除敏感信息。

```bash
sudo systemctl status whisper
sudo journalctl -u whisper -n 50
```

**其它信息**
添加关于该问题的其它信息。
