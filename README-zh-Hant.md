[English](README.md) | [简体中文](README-zh.md) | [繁體中文](README-zh-Hant.md) | [Русский](README-ru.md)

# Whisper 語音轉文字自動安裝腳本

[![Build Status](https://github.com/hwdsl2/whisper-install/actions/workflows/main.yml/badge.svg)](https://github.com/hwdsl2/whisper-install/actions/workflows/main.yml) &nbsp;[![License: MIT](docs/images/license.svg)](https://opensource.org/licenses/MIT)

適用於 Ubuntu、Debian、AlmaLinux、Rocky Linux、CentOS、RHEL 和 Fedora 的 Whisper 語音轉文字伺服器安裝腳本。

本腳本安裝並設定由 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 驅動的自託管 [Whisper](https://github.com/openai/whisper) 語音轉文字 API 伺服器，提供相容 OpenAI 的 `/v1/audio/transcriptions` 和 `/v1/audio/translations` 介面。使用任何支援 OpenAI 音訊 API 的應用程式轉錄和翻譯音訊檔案。

**功能特性：**

- 全自動 Whisper 伺服器安裝，無需使用者輸入
- 支援使用自訂選項進行互動式安裝
- 支援預下載模型和管理伺服器
- 相容 OpenAI 的 `POST /v1/audio/transcriptions` 和 `POST /v1/audio/translations` 介面 —— 一行更改即可切換任意應用程式
- 串流轉錄 —— 透過 SSE 即時接收解碼片段，無需等待完整檔案
- 逐字時間戳記 —— `verbose_json` 輸出中包含每個字詞的開始/結束時間和信心分數
- 多種輸出格式：`json`、`text`、`verbose_json`、`srt`、`vtt`
- 離線/隔離網路模式 —— 使用預快取模型在無網路環境中執行（`WHISPER_LOCAL_ONLY`）
- 音訊保留在你的伺服器上 —— 不向第三方傳送資料
- 將 Whisper 安裝為具有專用系統使用者的 systemd 服務
- 模型從 HuggingFace 下載並快取至 `/var/lib/whisper`

**另提供：**

- AI 套件：[Self-Hosted AI Stack](https://github.com/hwdsl2/self-hosted-ai-stack/blob/main/README-zh-Hant.md)
- 基於 Docker 的 AI 服務：[Whisper (STT)](https://github.com/hwdsl2/docker-whisper/blob/main/README-zh-Hant.md)、[Kokoro (TTS)](https://github.com/hwdsl2/docker-kokoro/blob/main/README-zh-Hant.md)、[Embeddings](https://github.com/hwdsl2/docker-embeddings/blob/main/README-zh-Hant.md)、[LiteLLM](https://github.com/hwdsl2/docker-litellm/blob/main/README-zh-Hant.md)、[Ollama (LLM)](https://github.com/hwdsl2/docker-ollama/blob/main/README-zh-Hant.md)、[Docling](https://github.com/hwdsl2/docker-docling/blob/main/README-zh-Hant.md)、[MCP Gateway](https://github.com/hwdsl2/docker-mcp-gateway/blob/main/README-zh-Hant.md)

## 社群

- 📬 [訂閱專案更新](https://selfhostedstack.beehiiv.com/subscribe?utm_campaign=ai-zh-hant)（每月 1–2 封郵件）——獲取免費的 AI 和 VPN 部署指南（PDF，英文）
- 💬 加入 [r/selfhostedstack](https://www.reddit.com/r/selfhostedstack/) 社群，參與討論與專案展示
- ⭐ 如果你覺得本專案有用，請為儲存庫加星——這能幫助更多人發現它。

<details>
<summary>自託管 VPN 與網路專案</summary>

- [Setup IPsec VPN](https://github.com/hwdsl2/setup-ipsec-vpn/blob/master/README-zh-Hant.md)
- [Docker 上的 IPsec VPN](https://github.com/hwdsl2/docker-ipsec-vpn-server/blob/master/README-zh-Hant.md)
- [WireGuard](https://github.com/hwdsl2/docker-wireguard/blob/main/README-zh-Hant.md)
- [OpenVPN](https://github.com/hwdsl2/docker-openvpn/blob/main/README-zh-Hant.md)
- [Headscale](https://github.com/hwdsl2/docker-headscale/blob/main/README-zh-Hant.md)

</details>

## 系統需求

- 一台 Linux 伺服器（雲端伺服器、VPS、獨立伺服器或家用伺服器）
- Python 3.9 或更高版本（腳本會在支援的發行版上自動安裝）
- 預設 `base` 模型至少需要 **700 MB RAM**（參見[模型表](#可用模型)）
- 初次下載模型需要網際網路存取（模型下載後會快取到本機）。如果使用 `WHISPER_LOCAL_ONLY` 並已預快取模型，則不需要。

**注：** 對於面向網際網路的部署，強烈建議使用[反向代理](#使用反向代理)新增 HTTPS。使用反向代理時，請在 `/etc/whisper/whisper.conf` 中設定 `WHISPER_LISTEN_ADDR=127.0.0.1`，以防止未加密連接埠被直接存取。

## 安裝

在你的 Linux 伺服器上下載腳本：

```bash
wget -O whisper.sh https://github.com/hwdsl2/whisper-install/raw/main/whisper-install.sh
```

**選項 1：** 使用預設選項自動安裝。

```bash
sudo bash whisper.sh --auto
```

這將在連接埠 `9000` 上安裝 `base` 模型（約 145 MB）。模型將在首次啟動時從 HuggingFace 下載。

**選項 2：** 使用自訂選項自動安裝。

```bash
sudo bash whisper.sh --auto --model small --port 9000
```

**選項 3：** 使用自訂選項進行互動式安裝。

```bash
sudo bash whisper.sh
```

<details>
<summary>
如果無法下載，請點擊此處。
</summary>

也可使用 `curl` 下載：

```bash
curl -fL -o whisper.sh https://github.com/hwdsl2/whisper-install/raw/main/whisper-install.sh
```

如果仍無法下載，請開啟 [whisper-install.sh](whisper-install.sh)，然後點擊右側的 `Raw` 按鈕。按 `Ctrl/Cmd+A` 全選，`Ctrl/Cmd+C` 複製，然後貼上至你喜歡的編輯器中。
</details>

<details>
<summary>
查看腳本的使用說明。
</summary>

```
用法：bash whisper.sh [選項]

選項：

  --showinfo                           顯示伺服器資訊（模型、介面、API 文件）
  --showkey                            顯示 API 金鑰（如果已設定）
  --getkey                             輸出 API 金鑰（機器可讀，無額外文字）
  --listmodels                         列出可用的 Whisper 模型名稱和大小
  --downloadmodel <模型>               預下載模型到快取目錄
  --uninstall                          移除 Whisper 及所有設定
  -y, --yes                            對提示自動回答「是」
  -h, --help                           顯示此說明訊息並結束

安裝選項（選用）：

  --auto                               使用預設或自訂選項自動安裝
  --model      <名稱>                  要使用的 Whisper 模型（預設：base）
  --port       <數字>                  API 伺服器的 TCP 連接埠（預設：9000）
  --listenaddr [地址]                  監聽位址（預設：0.0.0.0，使用 127.0.0.1 僅限本機存取）

可用模型：tiny, tiny.en, base, base.en, small, small.en,
          medium, medium.en, large-v1, large-v2, large-v3,
          large-v3-turbo（或：turbo）
```
</details>

## 安裝後

首次執行時，腳本將：
1. 安裝系統套件：`python3`、`python3-venv`、`curl`
2. 建立 `whisper` 系統使用者和群組
3. 在 `/opt/whisper/venv` 建立 Python 虛擬環境
4. 安裝 `faster-whisper`、`fastapi`、`uvicorn` 和 `python-multipart`
5. 為全新安裝產生 API 金鑰
6. 將設定寫入 `/etc/whisper/whisper.conf`
7. 安裝並啟動 `whisper` systemd 服務

首次啟動將從 HuggingFace 下載所選模型。根據模型大小和網路速度，這可能需要幾分鐘。模型快取在 `/var/lib/whisper` 中，後續啟動時將重複使用。

查看服務狀態和日誌：

```bash
sudo systemctl status whisper
sudo journalctl -u whisper -n 50
```

看到「Whisper speech-to-text server is ready」後，轉錄你的第一個音訊檔案：

```bash
API_KEY=$(sudo bash whisper.sh --getkey)

curl http://<伺服器IP>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@audio.mp3 -F model=whisper-1
```

**回應：**
```json
{"text": "轉錄後的文字顯示在這裡。"}
```

**提示：** 需要範例音訊檔案進行測試？可以使用來自 [Azure Samples](https://github.com/Azure-Samples/cognitive-services-speech-sdk) 儲存庫的英語語音範例（WAV 格式，MIT 授權）：

```bash
curl -L -o sample_speech.wav \
    "https://github.com/Azure-Samples/cognitive-services-speech-sdk/raw/master/sampledata/audiofiles/katiesteve.wav"

curl http://<伺服器IP>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@sample_speech.wav \
  -F model=whisper-1
```

## API 參考

該 API 與 OpenAI 的[音訊轉錄](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)和[音訊翻譯](https://developers.openai.com/api/reference/resources/audio/subresources/translations/methods/create)介面相容。任何已呼叫 `https://api.openai.com/v1/audio/transcriptions` 的應用程式，只需設定以下內容即可切換至自託管：

OpenAI 專用的轉錄選項（如 `gpt-4o-transcribe-diarize`、`response_format=diarized_json`、`include=logprobs`、`chunking_strategy`、`known_speaker_names` 和 `known_speaker_references`）不受支援，並會回傳 `400`。

```
OPENAI_BASE_URL=http://<伺服器IP>:9000
```

### 轉錄音訊

```
POST /v1/audio/transcriptions
Content-Type: multipart/form-data
```

**參數：**

| 參數 | 類型 | 必填 | 描述 |
|---|---|---|---|
| `file` | 檔案 | ✅ | 音訊檔案。支援的格式：`mp3`、`mp4`、`m4a`、`wav`、`webm`、`ogg`、`flac` 及所有 ffmpeg 支援的格式。 |
| `model` | 字串 | ✅ | 傳入 `whisper-1`（值被接受，但始終使用目前活躍模型）。 |
| `language` | 字串 | — | BCP-47 語言代碼（例如 `en`、`fr`、`zh`）。覆寫本次請求的 `WHISPER_LANGUAGE` 設定。 |
| `prompt` | 字串 | — | 用於引導模型風格或延續前一片段的選用文字。 |
| `response_format` | 字串 | — | 輸出格式。預設：`json`。參見[回應格式](#回應格式)。當 `stream=true` 時忽略此參數。不支援 OpenAI 專用的 `diarized_json`。 |
| `temperature` | 浮點數 | — | 取樣溫度（0–1）。預設：`0`。 |
| `stream` | 布林值 | — | 啟用 SSE 串流傳輸。為 `true` 時，片段以 `text/event-stream` 事件的形式即時返回。預設：`false`。 |
| `timestamp_granularities[]` | 陣列 | — | 要填充的時間戳記粒度。值：`word`、`segment`。包含 `word` 時，`verbose_json` 輸出的頂層包含帶有逐字時間和信心度的 `words` 陣列。預設：`["segment"]`。 |

**本地 faster-whisper 擴充：** 可設定 `beam`，為單一轉錄或翻譯請求覆寫 `WHISPER_BEAM`。這不是 OpenAI API 架構的一部分，因此不要將其傳送到託管的 OpenAI API 或嚴格相容 OpenAI 的閘道。每請求預設上限為 `10`（`WHISPER_MAX_REQUEST_BEAM`）；將該變數設為 `0` 可停用上限。Beam 搜尋主要影響 `temperature=0` 時的確定性解碼。

**範例：**

```bash
API_KEY=$(sudo bash whisper.sh --getkey)

curl http://<伺服器IP>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@meeting.m4a \
  -F model=whisper-1 \
  -F language=zh
```

如果已停用 API 金鑰驗證，請省略 `Authorization` 請求標頭。

### 回應格式

| `response_format` | 描述 |
|---|---|
| `json` | `{"text": "..."}` —— 預設，與 OpenAI 的基本回應一致 |
| `text` | 純文字，無 JSON 封裝 |
| `verbose_json` | 包含語言、時長、逐片段時間戳記和對數機率的完整 JSON |
| `srt` | SubRip 字幕格式（`.srt`） |
| `vtt` | WebVTT 字幕格式（`.vtt`） |

**範例 —— 即時串流接收解碼片段：**

```bash
curl http://<伺服器IP>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@long-audio.mp3 \
  -F model=whisper-1 \
  -F stream=true
```

**SSE 回應**（使用 [OpenAI 串流轉錄協定](https://developers.openai.com/api/docs/guides/speech-to-text#streaming)）：

```
data: {"type":"transcript.text.delta","delta":"Hello, how are you?"}

data: {"type":"transcript.text.delta","delta":" I'm doing well, thank you."}

data: {"type":"transcript.text.done","text":"Hello, how are you? I'm doing well, thank you."}

data: [DONE]
```

上傳後第一個增量文字通常在 1–3 秒內到達。每個 `transcript.text.delta` 事件包含剛解碼的段落的增量文字。最後的 `transcript.text.done` 事件包含與標準 `json` 回應等效的完整轉錄文字。

<details>
<summary><strong>範例 —— 在瀏覽器中使用 <code>fetch</code> 進行串流傳輸</strong></summary>

```javascript
const form = new FormData();
form.append("file", audioBlob, "audio.webm");
form.append("model", "whisper-1");
form.append("stream", "true");

const res = await fetch("http://<伺服器IP>:9000/v1/audio/transcriptions", {
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
  // SSE 框架以 "\n\n" 分隔；拆分並處理完整框架
  const frames = buffer.split("\n\n");
  buffer = frames.pop(); // 保留未完成的尾部框架
  for (const frame of frames) {
    if (!frame.startsWith("data: ")) continue;
    const payload = frame.slice(6);
    if (payload.startsWith("[DONE]")) break;
    const event = JSON.parse(payload);
    if (event.type === "transcript.text.delta") console.log(event.delta);
    if (event.type === "transcript.text.done") console.log("完整文字：", event.text);
  }
}
```

</details>

**範例 —— 取得 SRT 字幕：**

```bash
curl http://<伺服器IP>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@video.mp4 \
  -F model=whisper-1 \
  -F response_format=srt
```

**範例 —— 取得帶時間戳記的詳細 JSON：**

```bash
curl http://<伺服器IP>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@audio.mp3 \
  -F model=whisper-1 \
  -F response_format=verbose_json
```

**範例 —— 逐字時間戳記：**

```bash
curl http://<伺服器IP>:9000/v1/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@audio.mp3 \
  -F model=whisper-1 \
  -F response_format=verbose_json \
  -F "timestamp_granularities[]=word"
```

`timestamp_granularities[]` 包含 `word` 時，`verbose_json` 回應的頂層包含 `words` 陣列：

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

### 翻譯音訊

```
POST /v1/audio/translations
Content-Type: multipart/form-data
```

將任意語言的音訊翻譯為英文文字。與 [OpenAI 音訊翻譯介面](https://developers.openai.com/api/reference/resources/audio/subresources/translations/methods/create)相容。接受常見的翻譯參數。輸出始終為英文。

> **注意：** 翻譯功能不支援僅限英語的（`.en`）模型。請使用多語言模型，如 `base`、`small` 或 `large-v3-turbo`。

**範例：**

```bash
curl http://<伺服器IP>:9000/v1/audio/translations \
  -H "Authorization: Bearer $API_KEY" \
  -F file=@french-audio.mp3 \
  -F model=whisper-1
```

### 列出模型

```
GET /v1/models
```

以相容 OpenAI 的格式返回目前活躍模型。

```bash
curl http://<伺服器IP>:9000/v1/models \
  -H "Authorization: Bearer $API_KEY"
```

### 互動式 API 文件

互動式 Swagger UI 可透過以下位址存取：

```
http://<伺服器IP>:9000/docs
```

## 可用模型

| 名稱 | 磁碟占用 | RAM（約） | 說明 |
|---|---|---|---|
| `tiny` | ~75 MB | ~250 MB | 最快；準確率較低 |
| `tiny.en` | ~75 MB | ~250 MB | 僅限英語 |
| `base` | ~145 MB | ~700 MB | 良好的平衡 —— **預設** |
| `base.en` | ~145 MB | ~700 MB | 僅限英語 |
| `small` | ~465 MB | ~1.5 GB | 更高準確率 |
| `small.en` | ~465 MB | ~1.5 GB | 僅限英語 |
| `medium` | ~1.5 GB | ~5 GB | 高準確率 |
| `medium.en` | ~1.5 GB | ~5 GB | 僅限英語 |
| `large-v1` | ~3 GB | ~10 GB | 較舊的大型模型 |
| `large-v2` | ~3 GB | ~10 GB | 非常高的準確率 |
| `large-v3` | ~3 GB | ~10 GB | 最高準確率 |
| `large-v3-turbo` | ~1.6 GB | ~6 GB | 速度快 + 高準確率 ⭐ |
| `turbo` | ~1.6 GB | ~6 GB | `large-v3-turbo` 的別名 |

> **提示：** `large-v3-turbo` 的準確率接近 `large-v3`，但資源消耗約為其一半。對於大多數部署場景，它是從 `base` 升級的建議選擇。

**說明：**
- 僅限英語（`.en`）的變體對英語音訊略快。
- INT8 量化（預設）可將 RAM 使用量減少約 50%。

## 管理 Whisper

安裝完成後，再次執行腳本即可管理你的伺服器。

**顯示伺服器資訊：**

```bash
sudo bash whisper.sh --showinfo
```

**顯示 API 金鑰：**

```bash
sudo bash whisper.sh --showkey
```

用於腳本時，只輸出原始金鑰：

```bash
sudo bash whisper.sh --getkey
```

**列出可用模型：**

```bash
sudo bash whisper.sh --listmodels
```

**預下載模型：**

```bash
sudo bash whisper.sh --downloadmodel large-v3-turbo
```

預下載模型可避免切換模型時的延遲。下載後，更新設定檔中的 `WHISPER_MODEL` 並重新啟動服務。

**解除安裝 Whisper：**

```bash
sudo bash whisper.sh --uninstall
```

`/var/lib/whisper` 中的模型檔案將被保留。如需同時刪除，請執行：

```bash
sudo rm -rf /var/lib/whisper
```

**顯示說明：**

```bash
sudo bash whisper.sh --help
```

也可不帶參數執行腳本以進入互動式管理選單。

## 設定

設定檔位於 `/etc/whisper/whisper.conf`。編輯此檔案更改設定，然後重新啟動服務：

```bash
sudo systemctl restart whisper
```

所有變數均為選用。如未設定，將自動使用預設值。

| 變數 | 描述 | 預設值 |
|---|---|---|
| `WHISPER_MODEL` | 要使用的 Whisper 模型。參見[模型表](#可用模型)了解選項。 | `base` |
| `WHISPER_PORT` | API 伺服器的 TCP 連接埠（1–65535）。 | `9000` |
| `WHISPER_LISTEN_ADDR` | API 伺服器的監聽位址。使用 `0.0.0.0` 監聽所有介面，或 `127.0.0.1` 僅限本機存取。 | `0.0.0.0` |
| `WHISPER_LANGUAGE` | 預設轉錄語言。BCP-47 代碼（例如 `en`、`fr`、`zh`）或 `auto` 自動偵測。 | `auto` |
| `WHISPER_DEVICE` | 運算裝置。 | `cpu` |
| `WHISPER_COMPUTE_TYPE` | 量化類型。建議 CPU 使用 `int8`。 | `int8` |
| `WHISPER_THREADS` | 推理使用的 CPU 執行緒數。設定為實體核心數可獲得最佳延遲。 | `2` |
| `WHISPER_BEAM` | 轉錄和翻譯解碼的 beam 大小。較大的值可能提高準確率，但會降低速度。使用 `1` 可獲得最快的（貪婪）解碼。 | `5` |
| `WHISPER_MAX_REQUEST_BEAM` | 每個請求的 `beam` 覆寫值允許的最大 beam 大小。設為 `0` 可停用此限制。 | `10` |
| `WHISPER_MAX_UPLOAD_MB` | 上傳音訊檔案的最大大小（MB）。超過此限制的請求會返回 HTTP 413。設為 `0` 可停用此限制。 | `1024` |
| `WHISPER_API_KEY` | 選用的 Bearer 權杖。全新安裝會自動產生。設定後，所有 API 請求必須包含 `Authorization: Bearer <key>`。明確設為空值可停用身分驗證。 | 全新安裝自動產生 |
| `WHISPER_LOG_LEVEL` | 日誌級別：`DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL`。 | `INFO` |
| `WHISPER_LOCAL_ONLY` | 設定為任意非空值時，停用所有 HuggingFace 模型下載。適用於使用預快取模型的離線或隔離網路部署。 | *（未設定）* |
| `WHISPER_WORD_TIMESTAMPS` | 設定為 `true` 時，為所有請求全域啟用逐字時間戳記。`verbose_json` 輸出將包含帶有逐字時間和信心度的頂層 `words` 陣列。也可透過 `timestamp_granularities[]=word` 按請求啟用。 | *（未設定）* |

## 切換模型

1. 預下載新模型（選用但建議）：
   ```bash
   sudo bash whisper.sh --downloadmodel small
   ```
2. 編輯設定檔：
   ```bash
   sudo nano /etc/whisper/whisper.conf
   # 設定：WHISPER_MODEL=small
   ```
3. 重新啟動服務：
   ```bash
   sudo systemctl restart whisper
   ```

## 保護你的伺服器

如果你的 Whisper 伺服器可從公用網際網路存取 —— 即使只是短暫可達 —— 也請至少採取以下保護措施。Whisper 對 CPU/GPU 資源消耗較大，未做身分驗證的介面可能被濫用，浪費你的運算資源。

**1. 使用 API 金鑰。** 全新安裝會自動產生 API 金鑰。可用 `sudo bash whisper.sh --showkey` 顯示，或在腳本中使用 `sudo bash whisper.sh --getkey`。既有設定檔不會被自動修改；如果既有安裝沒有金鑰，請在 `/etc/whisper/whisper.conf` 中設定 `WHISPER_API_KEY` 以手動啟用身分驗證。所有已啟用驗證的請求都必須包含 `Authorization: Bearer <key>`。

```bash
# 產生 32 位元組的隨機金鑰
openssl rand -hex 32
```

**2. 在反向代理後方時繫結到 localhost。** 在 `/etc/whisper/whisper.conf` 中設定 `WHISPER_LISTEN_ADDR=127.0.0.1`，使未加密連接埠無法從主機外部直接存取。使用 `sudo systemctl restart whisper` 重新啟動。

**3. 限制上傳大小。** 伺服器會拒絕超過 `WHISPER_MAX_UPLOAD_MB`（預設 `1024`）的上傳。對於面向網際網路的部署，還應設定反向代理在請求到達應用程式前拒絕過大的上傳（例如 nginx `client_max_body_size 100M;`）。

**4. 注意日誌等級。** `WHISPER_LOG_LEVEL=DEBUG` 可能會將轉錄文字寫入日誌。在共用系統上請保持 `INFO` 或更高等級。

**5. 瀏覽器呼叫時在代理處啟用 CORS。** 本伺服器預設不設定 `Access-Control-Allow-Origin` 回應標頭；若需在不同來源的網頁中直接呼叫本 API，請在反向代理處新增 CORS 標頭。

**6. 考慮限流。** 在伺服器前部署限流（如 nginx `limit_req_zone`、Caddy `rate_limit`），限制每個用戶端 IP 的並行轉錄請求數。

## 使用反向代理

對於面向網際網路的部署，在 Whisper 前放置反向代理以處理 HTTPS 終止。

**使用 [Caddy](https://caddyserver.com/docs/) 的範例**（透過 Let's Encrypt 自動申請 TLS）：

```
whisper.example.com {
  reverse_proxy localhost:9000
}
```

**使用 nginx 的範例：**

```nginx
server {
    listen 443 ssl;
    server_name whisper.example.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 音訊檔案可能較大 —— 根據需要增加上傳限制
    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;       # SSE 串流傳輸所需
        proxy_read_timeout 300s;
    }
}
```

## 與其他 AI 服務配合使用

Whisper 可作為更廣泛的自託管 AI 設定中的語音轉文字服務。

如需完整和輕量級 Docker Compose 技術堆疊、手動 `docker run` 範例，以及結合 Kokoro、Embeddings、LiteLLM、Ollama、Docling 和 MCP Gateway 的語音/RAG/MCP 流水線範例，請參閱 [Self-Hosted AI Stack](https://github.com/hwdsl2/self-hosted-ai-stack/blob/main/README-zh-Hant.md)。

## 使用自訂選項自動安裝

```bash
sudo bash whisper.sh --auto --model base --port 9000
```

使用 `--auto` 時，所有安裝選項均為選用。預設值：模型 `base`，連接埠 `9000`，監聽位址 `0.0.0.0`。

## 技術細節

- 作業系統支援：Ubuntu 22.04+、Debian 11+、AlmaLinux/Rocky/CentOS 9+、RHEL 9+、Fedora
- 執行時：Python 3.9+（虛擬環境位於 `/opt/whisper/venv`）
- STT 引擎：[faster-whisper](https://github.com/SYSTRAN/faster-whisper) with CTranslate2（預設 INT8）
- API 框架：[FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- API 伺服器：[`api_server.py`](api_server.py)（安裝至 `/opt/whisper/api_server.py`）
- 音訊解碼：[PyAV](https://github.com/PyAV-Org/PyAV)（內建 FFmpeg 函式庫 —— 無需系統安裝 `ffmpeg`）
- 資料目錄：`/var/lib/whisper`（模型快取，升級後保留）
- 設定檔：`/etc/whisper/whisper.conf`
- 服務：`whisper.service`（systemd，以專用 `whisper` 系統使用者執行）

## 授權條款

Copyright (C) 2026 Lin Song   
本作品依據 [MIT 授權條款](https://opensource.org/licenses/MIT)授權。

**faster-whisper** 版權歸 SYSTRAN 所有，遵循 [MIT 授權條款](https://github.com/SYSTRAN/faster-whisper/blob/master/LICENSE)。

本專案是 Whisper 的獨立安裝程式，與 OpenAI 或 SYSTRAN 無關聯，未獲其背書或贊助。
