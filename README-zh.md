[English](README.md) | [简体中文](README-zh.md) | [繁體中文](README-zh-Hant.md) | [Русский](README-ru.md)

# Whisper 语音转文字自动安装脚本

[![Build Status](https://github.com/hwdsl2/whisper-install/actions/workflows/main.yml/badge.svg)](https://github.com/hwdsl2/whisper-install/actions/workflows/main.yml) &nbsp;[![License: MIT](docs/images/license.svg)](https://opensource.org/licenses/MIT)

适用于 Ubuntu、Debian、AlmaLinux、Rocky Linux、CentOS、RHEL 和 Fedora 的 Whisper 语音转文字服务器安装脚本。

本脚本安装并配置由 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 驱动的自托管 [Whisper](https://github.com/openai/whisper) 语音转文字 API 服务器，提供兼容 OpenAI 的 `/v1/audio/transcriptions` 和 `/v1/audio/translations` 接口。使用任何支持 OpenAI 音频 API 的应用程序转录和翻译音频文件。

**功能特性：**

- 全自动 Whisper 服务器安装，无需用户输入
- 支持使用自定义选项进行交互式安装
- 支持预下载模型和管理服务器
- 兼容 OpenAI 的 `POST /v1/audio/transcriptions` 和 `POST /v1/audio/translations` 接口 —— 一行更改即可切换任意应用
- 流式转录 —— 通过 SSE 实时接收解码片段，无需等待完整文件
- 逐词时间戳 —— `verbose_json` 输出中包含每个词的开始/结束时间和置信度分数
- 多种输出格式：`json`、`text`、`verbose_json`、`srt`、`vtt`
- 离线/隔离网络模式 —— 使用预缓存模型在无网络环境中运行（`WHISPER_LOCAL_ONLY`）
- 音频保留在你的服务器上 —— 不向第三方发送数据
- 将 Whisper 安装为具有专用系统用户的 systemd 服务
- 模型从 HuggingFace 下载并缓存至 `/var/lib/whisper`

**另提供：**

- AI 套件：[Self-Hosted AI Stack](https://github.com/hwdsl2/self-hosted-ai-stack/blob/main/README-zh.md)
- 基于 Docker 的 AI 服务：[Whisper (STT)](https://github.com/hwdsl2/docker-whisper/blob/main/README-zh.md)、[Kokoro (TTS)](https://github.com/hwdsl2/docker-kokoro/blob/main/README-zh.md)、[Embeddings](https://github.com/hwdsl2/docker-embeddings/blob/main/README-zh.md)、[LiteLLM](https://github.com/hwdsl2/docker-litellm/blob/main/README-zh.md)、[Ollama (LLM)](https://github.com/hwdsl2/docker-ollama/blob/main/README-zh.md)、[Docling](https://github.com/hwdsl2/docker-docling/blob/main/README-zh.md)、[MCP Gateway](https://github.com/hwdsl2/docker-mcp-gateway/blob/main/README-zh.md)

## 社区

- 📬 [订阅项目更新](https://selfhostedstack.beehiiv.com/subscribe?utm_campaign=ai-zh)（每月 1–2 封邮件）——获取免费的 AI 和 VPN 部署指南（PDF，英文）
- 💬 加入 [r/selfhostedstack](https://www.reddit.com/r/selfhostedstack/) 社区，参与讨论和项目展示
- ⭐ 如果你觉得本项目有用，请为仓库加星——这有助于让更多人发现它。

<details>
<summary>自托管 VPN 和网络项目</summary>

- [Setup IPsec VPN](https://github.com/hwdsl2/setup-ipsec-vpn/blob/master/README-zh.md)
- [Docker 上的 IPsec VPN](https://github.com/hwdsl2/docker-ipsec-vpn-server/blob/master/README-zh.md)
- [WireGuard](https://github.com/hwdsl2/docker-wireguard/blob/main/README-zh.md)
- [OpenVPN](https://github.com/hwdsl2/docker-openvpn/blob/main/README-zh.md)
- [Headscale](https://github.com/hwdsl2/docker-headscale/blob/main/README-zh.md)

</details>

## 系统要求

- 一台 Linux 服务器（云服务器、VPS、独立服务器或家用服务器）
- Python 3.9 或更高版本（脚本会在支持的发行版上自动安装）
- 默认 `base` 模型至少需要 **700 MB RAM**（参见[模型表](#可用模型)）
- 初次下载模型需要互联网访问（模型下载后会缓存到本地）。如果使用 `WHISPER_LOCAL_ONLY` 并已预缓存模型，则不需要。

**注：** 对于面向互联网的部署，强烈建议使用[反向代理](#使用反向代理)添加 HTTPS。使用反向代理时，请在 `/etc/whisper/whisper.conf` 中设置 `WHISPER_LISTEN_ADDR=127.0.0.1`，以防止未加密端口被直接访问。

## 安装

在你的 Linux 服务器上下载脚本：

```bash
wget -O whisper.sh https://github.com/hwdsl2/whisper-install/raw/main/whisper-install.sh
```

**选项 1：** 使用默认选项自动安装。

```bash
sudo bash whisper.sh --auto
```

这将在端口 `9000` 上安装 `base` 模型（约 145 MB）。模型将在首次启动时从 HuggingFace 下载。

**选项 2：** 使用自定义选项自动安装。

```bash
sudo bash whisper.sh --auto --model small --port 9000
```

**选项 3：** 使用自定义选项进行交互式安装。

```bash
sudo bash whisper.sh
```

<details>
<summary>
如果无法下载，请点击此处。
</summary>

也可使用 `curl` 下载：

```bash
curl -fL -o whisper.sh https://github.com/hwdsl2/whisper-install/raw/main/whisper-install.sh
```

如果仍无法下载，请打开 [whisper-install.sh](whisper-install.sh)，然后点击右侧的 `Raw` 按钮。按 `Ctrl/Cmd+A` 全选，`Ctrl/Cmd+C` 复制，然后粘贴到你喜欢的编辑器中。
</details>

<details>
<summary>
查看脚本的使用说明。
</summary>

```
用法：bash whisper.sh [选项]

选项：

  --showinfo                           显示服务器信息（模型、接口、API 文档）
  --showkey                            显示 API 密钥（如果已配置）
  --getkey                             输出 API 密钥（机器可读，无额外文本）
  --listmodels                         列出可用的 Whisper 模型名称和大小
  --downloadmodel <模型>               预下载模型到缓存目录
  --uninstall                          删除 Whisper 及所有配置
  -y, --yes                            对提示自动回答"是"
  -h, --help                           显示此帮助信息并退出

安装选项（可选）：

  --auto                               使用默认或自定义选项自动安装
  --model      <名称>                  要使用的 Whisper 模型（默认：base）
  --port       <数字>                  API 服务器的 TCP 端口（默认：9000）
  --listenaddr [地址]                  监听地址（默认：0.0.0.0，使用 127.0.0.1 仅本地访问）

可用模型：tiny, tiny.en, base, base.en, small, small.en,
          medium, medium.en, large-v1, large-v2, large-v3,
          large-v3-turbo（或：turbo）
```
</details>

## 安装后

首次运行时，脚本将：
1. 安装系统软件包：`python3`、`python3-venv`、`curl`
2. 创建 `whisper` 系统用户和组
3. 在 `/opt/whisper/venv` 创建 Python 虚拟环境
4. 安装 `faster-whisper`、`fastapi`、`uvicorn` 和 `python-multipart`
5. 为全新安装生成 API 密钥
6. 将配置写入 `/etc/whisper/whisper.conf`
7. 安装并启动 `whisper` systemd 服务

首次启动将从 HuggingFace 下载所选模型。根据模型大小和网络速度，这可能需要几分钟。模型缓存在 `/var/lib/whisper` 中，后续启动时将复用。

查看服务状态和日志：

```bash
sudo systemctl status whisper
sudo journalctl -u whisper -n 50
```

看到"Whisper speech-to-text server is ready"后，转录你的第一个音频文件：

```bash
API_KEY=$(sudo bash whisper.sh --getkey)

curl http://<服务器IP>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@audio.mp3 -F model=whisper-1
```

**响应：**
```json
{"text": "转录后的文字显示在这里。"}
```

**提示：** 需要示例音频文件进行测试？可以使用来自 [Azure Samples](https://github.com/Azure-Samples/cognitive-services-speech-sdk) 仓库的英语语音示例（WAV 格式，MIT 许可证）：

```bash
curl -L -o sample_speech.wav \
    "https://github.com/Azure-Samples/cognitive-services-speech-sdk/raw/master/sampledata/audiofiles/katiesteve.wav"

curl http://<服务器IP>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@sample_speech.wav \
  -F model=whisper-1
```

## API 参考

该 API 与 OpenAI 的[音频转录](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)和[音频翻译](https://developers.openai.com/api/reference/resources/audio/subresources/translations/methods/create)接口兼容。任何已调用 `https://api.openai.com/v1/audio/transcriptions` 的应用程序，只需设置以下内容即可切换到自托管：

OpenAI 专用的转录选项（如 `gpt-4o-transcribe-diarize`、`response_format=diarized_json`、`include=logprobs`、`chunking_strategy`、`known_speaker_names` 和 `known_speaker_references`）不受支持，并会返回 `400`。

```
OPENAI_BASE_URL=http://<服务器IP>:9000
```

### 转录音频

```
POST /v1/audio/transcriptions
Content-Type: multipart/form-data
```

**参数：**

| 参数 | 类型 | 必填 | 描述 |
|---|---|---|---|
| `file` | 文件 | ✅ | 音频文件。支持的格式：`mp3`、`mp4`、`m4a`、`wav`、`webm`、`ogg`、`flac` 及所有 ffmpeg 支持的格式。 |
| `model` | 字符串 | ✅ | 传入 `whisper-1`（值被接受，但始终使用当前活跃模型）。 |
| `language` | 字符串 | — | BCP-47 语言代码（例如 `en`、`fr`、`zh`）。覆盖本次请求的 `WHISPER_LANGUAGE` 设置。 |
| `prompt` | 字符串 | — | 用于引导模型风格或延续前一片段的可选文本。 |
| `response_format` | 字符串 | — | 输出格式。默认：`json`。参见[响应格式](#响应格式)。当 `stream=true` 时忽略此参数。不支持 OpenAI 专用的 `diarized_json`。 |
| `temperature` | 浮点数 | — | 采样温度（0–1）。默认：`0`。 |
| `stream` | 布尔值 | — | 启用 SSE 流式传输。为 `true` 时，片段以 `text/event-stream` 事件的形式实时返回。默认：`false`。 |
| `timestamp_granularities[]` | 数组 | — | 要填充的时间戳粒度。值：`word`、`segment`。包含 `word` 时，`verbose_json` 输出的顶层包含带有逐词时间和置信度的 `words` 数组。默认：`["segment"]`。 |

**本地 faster-whisper 扩展：** 可设置 `beam`，为单个转录或翻译请求覆盖 `WHISPER_BEAM`。这不是 OpenAI API 架构的一部分，因此不要将其发送到托管的 OpenAI API 或严格兼容 OpenAI 的网关。每请求默认上限为 `10`（`WHISPER_MAX_REQUEST_BEAM`）；将该变量设为 `0` 可禁用上限。Beam 搜索主要影响 `temperature=0` 时的确定性解码。

**示例：**

```bash
API_KEY=$(sudo bash whisper.sh --getkey)

curl http://<服务器IP>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@meeting.m4a \
  -F model=whisper-1 \
  -F language=zh
```

如果已禁用 API 密钥认证，请省略 `Authorization` 请求头。

### 响应格式

| `response_format` | 描述 |
|---|---|
| `json` | `{"text": "..."}` —— 默认，与 OpenAI 的基本响应一致 |
| `text` | 纯文本，无 JSON 封装 |
| `verbose_json` | 包含语言、时长、逐片段时间戳和对数概率的完整 JSON |
| `srt` | SubRip 字幕格式（`.srt`） |
| `vtt` | WebVTT 字幕格式（`.vtt`） |

**示例 —— 实时流式接收解码片段：**

```bash
curl http://<服务器IP>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@long-audio.mp3 \
  -F model=whisper-1 \
  -F stream=true
```

**SSE 响应**（使用 [OpenAI 流式转录协议](https://developers.openai.com/api/docs/guides/speech-to-text#streaming)）：

```
data: {"type":"transcript.text.delta","delta":"Hello, how are you?"}

data: {"type":"transcript.text.delta","delta":" I'm doing well, thank you."}

data: {"type":"transcript.text.done","text":"Hello, how are you? I'm doing well, thank you."}

data: [DONE]
```

上传后第一个增量文本通常在 1–3 秒内到达。每个 `transcript.text.delta` 事件包含刚解码的段落的增量文本。最后的 `transcript.text.done` 事件包含与标准 `json` 响应等效的完整转录文本。

<details>
<summary><strong>示例 —— 在浏览器中使用 <code>fetch</code> 进行流式传输</strong></summary>

```javascript
const form = new FormData();
form.append("file", audioBlob, "audio.webm");
form.append("model", "whisper-1");
form.append("stream", "true");

const res = await fetch("http://<服务器IP>:9000/v1/audio/transcriptions", {
  method: "POST",
  headers: { Authorization: `Bearer ${apiKey}` },
  body: form,
});

const reader = res.body.getReader();
const decoder = new TextDecoder();
let buffer = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  // SSE 帧以 "\n\n" 分隔；拆分并处理完整帧
  const frames = buffer.split("\n\n");
  buffer = frames.pop(); // 保留未完成的尾部帧
  for (const frame of frames) {
    if (!frame.startsWith("data: ")) continue;
    const payload = frame.slice(6);
    if (payload.startsWith("[DONE]")) break;
    const event = JSON.parse(payload);
    if (event.type === "transcript.text.delta") console.log(event.delta);
    if (event.type === "transcript.text.done") console.log("完整文本：", event.text);
  }
}
```

</details>

**示例 —— 获取 SRT 字幕：**

```bash
curl http://<服务器IP>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@video.mp4 \
  -F model=whisper-1 \
  -F response_format=srt
```

**示例 —— 获取带时间戳的详细 JSON：**

```bash
curl http://<服务器IP>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@audio.mp3 \
  -F model=whisper-1 \
  -F response_format=verbose_json
```

**示例 —— 逐词时间戳：**

```bash
curl http://<服务器IP>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@audio.mp3 \
  -F model=whisper-1 \
  -F response_format=verbose_json \
  -F "timestamp_granularities[]=word"
```

`timestamp_granularities[]` 包含 `word` 时，`verbose_json` 响应的顶层包含 `words` 数组：

```json
{
  "text": "Hello world.",
  "words": [
    {"word": "Hello", "start": 0.0, "end": 0.42, "probability": 0.98},
    {"word": "world.", "start": 0.42, "end": 0.88, "probability": 0.97}
  ],
  "segments": [...]
}
```

### 翻译音频

```
POST /v1/audio/translations
Content-Type: multipart/form-data
```

将任意语言的音频翻译为英文文本。与 [OpenAI 音频翻译接口](https://developers.openai.com/api/reference/resources/audio/subresources/translations/methods/create)兼容。接受常见的翻译参数。输出始终为英文。

> **注意：** 翻译功能不支持仅限英语的（`.en`）模型。请使用多语言模型，如 `base`、`small` 或 `large-v3-turbo`。

**示例：**

```bash
curl http://<服务器IP>:9000/v1/audio/translations \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@french-audio.mp3 \
  -F model=whisper-1
```

### 列出模型

```
GET /v1/models
```

以兼容 OpenAI 的格式返回当前活跃模型。

```bash
curl http://<服务器IP>:9000/v1/models \
  -H "Authorization: Bearer $API_KEY"
```

### 交互式 API 文档

交互式 Swagger UI 可通过以下地址访问：

```
http://<服务器IP>:9000/docs
```

## 可用模型

| 名称 | 磁盘占用 | RAM（约） | 说明 |
|---|---|---|---|
| `tiny` | ~75 MB | ~250 MB | 最快；准确率较低 |
| `tiny.en` | ~75 MB | ~250 MB | 仅限英语 |
| `base` | ~145 MB | ~700 MB | 良好的平衡 —— **默认** |
| `base.en` | ~145 MB | ~700 MB | 仅限英语 |
| `small` | ~465 MB | ~1.5 GB | 更高准确率 |
| `small.en` | ~465 MB | ~1.5 GB | 仅限英语 |
| `medium` | ~1.5 GB | ~5 GB | 高准确率 |
| `medium.en` | ~1.5 GB | ~5 GB | 仅限英语 |
| `large-v1` | ~3 GB | ~10 GB | 较旧的大模型 |
| `large-v2` | ~3 GB | ~10 GB | 非常高的准确率 |
| `large-v3` | ~3 GB | ~10 GB | 最高准确率 |
| `large-v3-turbo` | ~1.6 GB | ~6 GB | 速度快 + 高准确率 ⭐ |
| `turbo` | ~1.6 GB | ~6 GB | `large-v3-turbo` 的别名 |

> **提示：** `large-v3-turbo` 的准确率接近 `large-v3`，但资源消耗约为其一半。对于大多数部署场景，它是从 `base` 升级的推荐选择。

**说明：**
- 仅限英语（`.en`）的变体对英语音频略快。
- INT8 量化（默认）可将 RAM 使用量减少约 50%。

## 管理 Whisper

安装完成后，再次运行脚本即可管理你的服务器。

**显示服务器信息：**

```bash
sudo bash whisper.sh --showinfo
```

**显示 API 密钥：**

```bash
sudo bash whisper.sh --showkey
```

用于脚本时，只输出原始密钥：

```bash
sudo bash whisper.sh --getkey
```

**列出可用模型：**

```bash
sudo bash whisper.sh --listmodels
```

**预下载模型：**

```bash
sudo bash whisper.sh --downloadmodel large-v3-turbo
```

预下载模型可避免切换模型时的延迟。下载后，更新配置文件中的 `WHISPER_MODEL` 并重启服务。

**卸载 Whisper：**

```bash
sudo bash whisper.sh --uninstall
```

`/var/lib/whisper` 中的模型文件将被保留。如需同时删除，请运行：

```bash
sudo rm -rf /var/lib/whisper
```

**显示帮助信息：**

```bash
sudo bash whisper.sh --help
```

也可不带参数运行脚本以进入交互式管理菜单。

## 配置

配置文件位于 `/etc/whisper/whisper.conf`。编辑此文件更改设置，然后重启服务：

```bash
sudo systemctl restart whisper
```

所有变量均为可选。如未设置，将自动使用默认值。

| 变量 | 描述 | 默认值 |
|---|---|---|
| `WHISPER_MODEL` | 要使用的 Whisper 模型。参见[模型表](#可用模型)了解选项。 | `base` |
| `WHISPER_PORT` | API 服务器的 TCP 端口（1–65535）。 | `9000` |
| `WHISPER_LISTEN_ADDR` | API 服务器的监听地址。使用 `0.0.0.0` 监听所有接口，或 `127.0.0.1` 仅本地访问。 | `0.0.0.0` |
| `WHISPER_LANGUAGE` | 默认转录语言。BCP-47 代码（例如 `en`、`fr`、`zh`）或 `auto` 自动检测。 | `auto` |
| `WHISPER_DEVICE` | 计算设备。 | `cpu` |
| `WHISPER_COMPUTE_TYPE` | 量化类型。推荐 CPU 使用 `int8`。 | `int8` |
| `WHISPER_THREADS` | 推理使用的 CPU 线程数。设置为物理核心数可获得最佳延迟。 | `2` |
| `WHISPER_BEAM` | 转录和翻译解码的 beam 大小。较大的值可能提高准确率，但会降低速度。使用 `1` 可获得最快的（贪婪）解码。 | `5` |
| `WHISPER_MAX_REQUEST_BEAM` | 每个请求的 `beam` 覆盖值允许的最大 beam 大小。设为 `0` 可禁用此限制。 | `10` |
| `WHISPER_MAX_UPLOAD_MB` | 上传音频文件的最大大小（MB）。超过此限制的请求会返回 HTTP 413。设为 `0` 可禁用此限制。 | `1024` |
| `WHISPER_API_KEY` | 可选的 Bearer 令牌。全新安装会自动生成。设置后，所有 API 请求必须包含 `Authorization: Bearer <key>`。显式设为空可禁用身份验证。 | 全新安装自动生成 |
| `WHISPER_LOG_LEVEL` | 日志级别：`DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL`。 | `INFO` |
| `WHISPER_LOCAL_ONLY` | 设置为任意非空值时，禁用所有 HuggingFace 模型下载。适用于使用预缓存模型的离线或隔离网络部署。 | *（未设置）* |
| `WHISPER_WORD_TIMESTAMPS` | 设置为 `true` 时，为所有请求全局启用逐词时间戳。`verbose_json` 输出将包含带有逐词时间和置信度的顶层 `words` 数组。也可通过 `timestamp_granularities[]=word` 按请求启用。 | *（未设置）* |

## 切换模型

1. 预下载新模型（可选但推荐）：
   ```bash
   sudo bash whisper.sh --downloadmodel small
   ```
2. 编辑配置文件：
   ```bash
   sudo nano /etc/whisper/whisper.conf
   # 设置：WHISPER_MODEL=small
   ```
3. 重启服务：
   ```bash
   sudo systemctl restart whisper
   ```

## 保护你的服务器

如果你的 Whisper 服务器可从公网访问 —— 即使只是短暂可达 —— 也请至少采取以下保护措施。Whisper 对 CPU/GPU 资源消耗较大，未做身份验证的接口可能被滥用，浪费你的计算资源。

**1. 使用 API 密钥。** 全新安装会自动生成 API 密钥。可用 `sudo bash whisper.sh --showkey` 显示，或在脚本中使用 `sudo bash whisper.sh --getkey`。既有配置文件不会被自动修改；如果既有安装没有密钥，请在 `/etc/whisper/whisper.conf` 中设置 `WHISPER_API_KEY` 以手动启用身份验证。所有已启用认证的请求都必须包含 `Authorization: Bearer <key>`。

```bash
# 生成 32 字节的随机密钥
openssl rand -hex 32
```

**2. 在反向代理后面时绑定到 localhost。** 在 `/etc/whisper/whisper.conf` 中设置 `WHISPER_LISTEN_ADDR=127.0.0.1`，使未加密端口无法从主机外部直接访问。使用 `sudo systemctl restart whisper` 重启。

**3. 限制上传大小。** 服务器会拒绝超过 `WHISPER_MAX_UPLOAD_MB`（默认 `1024`）的上传。对于面向互联网的部署，还应配置反向代理在请求到达应用前拒绝超大上传（例如 nginx `client_max_body_size 100M;`）。

**4. 注意日志级别。** `WHISPER_LOG_LEVEL=DEBUG` 可能会将转录文本写入日志。在共享系统上请保持 `INFO` 或更高级别。

**5. 浏览器调用时在代理处启用 CORS。** 本服务器默认不设置 `Access-Control-Allow-Origin` 响应头；若需在不同源的网页中直接调用本 API，请在反向代理处添加 CORS 头。

**6. 考虑限流。** 在服务器前部署限流（如 nginx `limit_req_zone`、Caddy `rate_limit`），限制每个客户端 IP 的并发转录请求数。

## 使用反向代理

对于面向互联网的部署，在 Whisper 前放置反向代理以处理 HTTPS 终止。

**使用 [Caddy](https://caddyserver.com/docs/) 的示例**（通过 Let's Encrypt 自动申请 TLS）：

```
whisper.example.com {
  reverse_proxy localhost:9000
}
```

**使用 nginx 的示例：**

```nginx
server {
    listen 443 ssl;
    server_name whisper.example.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 音频文件可能较大 —— 根据需要增加上传限制
    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;       # SSE 流式传输所需
        proxy_read_timeout 300s;
    }
}
```

## 与其他 AI 服务配合使用

Whisper 可作为更广泛的自托管 AI 设置中的语音转文字服务。

如需完整和轻量级 Docker Compose 技术栈、手动 `docker run` 示例，以及结合 Kokoro、Embeddings、LiteLLM、Ollama、Docling 和 MCP Gateway 的语音/RAG/MCP 流水线示例，请参阅 [Self-Hosted AI Stack](https://github.com/hwdsl2/self-hosted-ai-stack/blob/main/README-zh.md)。

## 使用自定义选项自动安装

```bash
sudo bash whisper.sh --auto --model base --port 9000
```

使用 `--auto` 时，所有安装选项均为可选。默认值：模型 `base`，端口 `9000`，监听地址 `0.0.0.0`。

## 技术细节

- 操作系统支持：Ubuntu 22.04+、Debian 11+、AlmaLinux/Rocky/CentOS 9+、RHEL 9+、Fedora
- 运行时：Python 3.9+（虚拟环境位于 `/opt/whisper/venv`）
- STT 引擎：[faster-whisper](https://github.com/SYSTRAN/faster-whisper) with CTranslate2（默认 INT8）
- API 框架：[FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- API 服务器：[`api_server.py`](api_server.py)（安装到 `/opt/whisper/api_server.py`）
- 音频解码：[PyAV](https://github.com/PyAV-Org/PyAV)（内置 FFmpeg 库 —— 无需系统安装 `ffmpeg`）
- 数据目录：`/var/lib/whisper`（模型缓存，升级后保留）
- 配置文件：`/etc/whisper/whisper.conf`
- 服务：`whisper.service`（systemd，以专用 `whisper` 系统用户运行）

## 授权协议

Copyright (C) 2026 Lin Song   
本作品依据 [MIT 许可证](https://opensource.org/licenses/MIT)授权。

**faster-whisper** 版权归 SYSTRAN 所有，遵循 [MIT 许可证](https://github.com/SYSTRAN/faster-whisper/blob/master/LICENSE)。

本项目是 Whisper 的独立安装程序，与 OpenAI 或 SYSTRAN 无关联，未获其背书或赞助。
