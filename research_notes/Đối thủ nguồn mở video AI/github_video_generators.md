# Open-source end-to-end AI short-form ("faceless / auto Shorts") video generators on GitHub — state as of 2026-11-04, mapped against ai-content-agent's 13 criteria

Method note: GitHub repo pages were read with WebFetch on 2026-11-04 (star/fork/issue counts are the rounded values GitHub displays, e.g. "29.8k"). READMEs and selected source/config files were pulled from raw.githubusercontent.com. The GitHub REST API, shields.io, ghtrends.pages.dev and aiindigo.com were NOT reachable from this session (403 / DNS failure), so exact last-commit timestamps were not available. Activity is inferred from dated changelog entries in READMEs and from Releases pages. Criteria numbering follows the brief: (1) storyboard LLM, (2) per-scene AI visuals, (3) TTS, (4) FFmpeg editing bundle, (5) thumbnail, (6) auto-publish YT/TikTok/FB, (7) scheduling + topic rotation/dedup, (8) web dashboard, (9) CapCut draft export, (10) pluggable providers/publishers, (11) Vietnamese, (12) Windows desktop and/or server mode, and (13) batch/mass production, added by the coordinator.

## Q1. Which projects exist, how big and active are they, and what are their license and stack?

### Takeaway
The category is led by one very large project, MoneyPrinterTurbo, which is MIT-licensed, Python-based and released v1.3.9 on 21 Oct (2026 implied). A second tier of Chinese-ecosystem projects is next: Pixelle-Video, MoneyPrinterV2 (AGPL), ViMax, NarratoAI, RedditVideoMakerBot, MoneyPrinter V1, ShortGPT, MoneyPrinterPlus and short-video-factory. Most of them can be self-hosted through a WebUI and/or Docker. Smaller 2026 repos (AbdullahNaveed/ai-shorts-generator, SaarD00 "AutoShorts AI") are architecturally the closest to ai-content-agent, but they have very little traction.

### Cited Findings
**Core "topic → finished short" generators**
- **MoneyPrinterTurbo** (harry0703): https://github.com/harry0703/MoneyPrinterTurbo. GitHub page shows **138.5k stars, 22.1k forks, 10 open issues, 58 open PRs, 1,233 commits**, MIT license, Python — [GitHub page](https://github.com/harry0703/MoneyPrinterTurbo); [LICENSE](https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/main/LICENSE). Star counts from other sources disagree: a 2026 search summary cites third-party figures of ~28k, 84,230 and 106K at unspecified dates — [search results incl. alternativeto/aitoolsatlas/opensourcealternatives](https://alternativeto.net/software/moneyprinterturbo/). Treat 138.5k as the GitHub-displayed figure on 2026-11-04. It could not be cross-checked through the API.
  - Latest releases: **v1.3.9 (21 Oct, "Latest"), v1.3.8 (03 Oct), v1.3.7 (13 Sep)**. The year is not shown. The README carries a sponsor promo "活动截至 2026 年 12 月 31 日", which suggests the releases are from 2026 — [Releases](https://github.com/harry0703/MoneyPrinterTurbo/releases); [README](https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/main/README.md).
  - v1.3.9 changes: an official `mpt` pip package; "static and slow-zoom image effects for local and AI-generated images, with slow zoom as the default"; **Muse Spark** and other providers added as LLM providers; diagnostic logging controls; and a fix to "kept completed videos when another video in the same batch fails" — [Releases](https://github.com/harry0703/MoneyPrinterTurbo/releases).
- **Pixelle-Video** (AIDC-AI, Alibaba International's AI team): https://github.com/AIDC-AI/Pixelle-Video. **29.8k stars, 4.3k forks, 151 issues, 24 PRs, 377 commits**, Apache-2.0 — [GitHub page](https://github.com/AIDC-AI/Pixelle-Video); [README](https://raw.githubusercontent.com/AIDC-AI/Pixelle-Video/main/README.md). Dated changelog runs from 2025-11-18 to **2026-06-01** ("新增直连 API 媒体模型配置") — [README](https://raw.githubusercontent.com/AIDC-AI/Pixelle-Video/main/README.md).
- **MoneyPrinterV2** (FujiwaraChoki): https://github.com/FujiwaraChoki/MoneyPrinterV2. **32.3k stars, 3.5k forks, 49 issues, 116 commits**, AGPL-3.0, Python 3.12 — [GitHub page](https://github.com/FujiwaraChoki/MoneyPrinterV2); [README](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinterV2/main/README.md). Its config references `gemini-3.1-flash-image-preview` ("nanobanana2"), which indicates recent updates — [config.example.json](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinterV2/main/config.example.json).
- **MoneyPrinter (V1)** (FujiwaraChoki): https://github.com/FujiwaraChoki/MoneyPrinter. **14.1k stars, 1.8k forks, 15 issues, 219 commits**, MIT — [GitHub page](https://github.com/FujiwaraChoki/MoneyPrinter). It has been re-architected as "Ollama-first" with "a DB-backed generation queue (API + worker + Postgres in Docker)". "Pull Requests will not be accepted for the time-being" — [README](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinter/main/README.md).
- **ShortGPT** (RayVentura): https://github.com/RayVentura/ShortGPT. **8.1k stars, 1.2k forks, 74 open issues, 12 PRs, 298 commits**, MIT, no releases. Last commit date not shown — [GitHub page](https://github.com/RayVentura/ShortGPT); [LICENSE](https://raw.githubusercontent.com/RayVentura/ShortGPT/master/LICENSE).
- **MoneyPrinterPlus** (ddean2009): https://github.com/ddean2009/MoneyPrinterPlus. **7.3k stars, 1.3k forks, 79 issues, 197 commits**, GPL-3.0, and "commercial use requires the author's explicit permission". The latest changelog entry is **20250208** — [GitHub page](https://github.com/ddean2009/MoneyPrinterPlus); [README](https://raw.githubusercontent.com/ddean2009/MoneyPrinterPlus/main/README.md).
- **short-video-maker** (gyoridavid): https://github.com/gyoridavid/short-video-maker. **1.5k stars, 442 forks, 25 issues, 122 commits**, MIT, TypeScript/Remotion. No release is shown — [GitHub page](https://github.com/gyoridavid/short-video-maker); [README](https://raw.githubusercontent.com/gyoridavid/short-video-maker/main/README.md).
- **short-video-factory / 短视频工厂** (YILS-LIN): https://github.com/YILS-LIN/short-video-factory. **6.0k stars, 830 forks, 18 issues, 151 commits**, AGPL-3.0. Its repo has an `electron` folder and `electron-builder.json5` (Electron + TypeScript/Vite) — [GitHub page](https://github.com/YILS-LIN/short-video-factory); [README](https://raw.githubusercontent.com/YILS-LIN/short-video-factory/main/README.md).
- **ViMax** (HKUDS, HKU Data Intelligence Lab): https://github.com/HKUDS/ViMax. **12.9k stars, 1.9k forks, 36 issues, 395 commits**, MIT. **v1.2.0 Web UI released 2026-07-20** — [GitHub page](https://github.com/HKUDS/ViMax); [README](https://raw.githubusercontent.com/HKUDS/ViMax/main/readme.md).
- **AI Shorts Generator** (AbdullahNaveed): https://github.com/AbdullahNaveed/ai-shorts-generator. **18 stars, 8 forks, 1 commit**, MIT. Example output path is dated `2026-06-24`. Self-described "A weekend project" — [GitHub page](https://github.com/AbdullahNaveed/ai-shorts-generator); [README](https://raw.githubusercontent.com/AbdullahNaveed/ai-shorts-generator/main/README.md).
- **AutoShorts AI** (SaarD00/AI-Youtube-Shorts-Generator): https://github.com/SaarD00/AI-Youtube-Shorts-Generator. **269 stars, 68 forks, 19 commits**, MIT — [GitHub page](https://github.com/SaarD00/AI-Youtube-Shorts-Generator).

**Adjacent projects (clip-from-long-video, story/commentary, or general agentic video)**
- **NarratoAI** (linyqh): an AI film/drama commentary + auto-editing tool. https://github.com/linyqh/NarratoAI. **11.7k stars, 1.6k forks, 3 open issues, 440 commits**, MIT. **v0.8.6 on 2026-07-16** — [GitHub page](https://github.com/linyqh/NarratoAI); [README](https://raw.githubusercontent.com/linyqh/NarratoAI/main/README.md).
- **RedditVideoMakerBot** (elebumm): turns Reddit threads into TTS videos. **12.6k stars, 2.9k forks, 19 issues, 1,286 commits**, GPL-3.0 — [GitHub page](https://github.com/elebumm/RedditVideoMakerBot).
- **AI-Youtube-Shorts-Generator** (SamurAIGPT): clips long YouTube videos into shorts, described as an "open-source alternative to Opus Clip". **5.8k stars, 1.0k forks, 10 issues, 32 commits**, MIT — [GitHub page](https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator); [README](https://raw.githubusercontent.com/SamurAIGPT/AI-Youtube-Shorts-Generator/main/README.md).
- **ViralCutter** (RafaelGodoyEbert): an Opus Clip alternative. **442 stars, 100 forks, 70 commits**, GPL-3.0, "0.8v Alpha" — [GitHub page](https://github.com/RafaelGodoyEbert/ViralCutter); [README](https://raw.githubusercontent.com/RafaelGodoyEbert/ViralCutter/main/README.md).
- **Text-To-Video-AI** (SamurAIGPT): the GitHub page currently shows only **5 stars, 5 commits**, MIT. The repo appears to have been reset or recreated, and the README now funnels users to a paid "Premium API" (vadoo.tv) — [GitHub page](https://github.com/SamurAIGPT/Text-To-Video-AI); [README](https://raw.githubusercontent.com/SamurAIGPT/Text-To-Video-AI/main/README.md).
- **AutoShorts** (alamshafil/auto-shorts): a JS/TS package with a Next.js web UI. **Discontinued**: "I have stopped working on auto-shorts since it was just a learning project" — [README](https://raw.githubusercontent.com/alamshafil/auto-shorts/main/README.md).
- **ViGen** (PhucHuwu): a PyQt6 desktop app (Windows .exe / macOS) using Gemini + Imagen 3 + **Veo 3.1**, MIT — [README](https://raw.githubusercontent.com/PhucHuwu/ViGen/main/README.md).
- **Content Factory** (jutsuhq/content-factory): a search snippet describes it as an "Open-source AI faceless video generator for TikTok, YouTube Shorts and Reels... MCP server for Claude". **The GitHub page returned HTTP 404 on 2026-11-04**, so it is unverified — [search listing](https://github.com/jutsuhq/content-factory).
- Other repos surfaced on topic pages (youtube-agentic-ai-studio, Mystery-CLI faceless-video-engine, BeyondtheUnkn generator) were not verified — [GitHub topic faceless-video](https://github.com/topics/faceless-video).

### Inferences
- By stars, MoneyPrinterTurbo is roughly 4x the next project, and its feature list has absorbed most competitor features: AI video providers, slow zoom, Muse Spark, batch, and publishing. It is the primary benchmark for ai-content-agent.
- Licenses differ in ways that matter for code reuse. MIT/Apache projects (MPT, Pixelle, ShortGPT, NarratoAI, ViMax, MoneyPrinter V1, short-video-maker) can be borrowed from freely. AGPL (MPV2, short-video-factory) and GPL-with-commercial-restriction (MoneyPrinterPlus) cannot be borrowed from freely.
- Three of the older projects look dormant or frozen: MoneyPrinterPlus (no changelog after Feb 2025), ShortGPT (no releases, 74 open issues) and alamshafil/auto-shorts (explicitly discontinued).

### Gaps
- Exact last-commit dates for each repo were unavailable because the GitHub API and shields.io were blocked. Activity is inferred only from README changelogs and Releases pages.
- The MoneyPrinterTurbo star count (138.5k) could not be independently verified. Third-party figures conflict.
- Star counts for alamshafil/auto-shorts and PhucHuwu/ViGen were not retrieved.
- Content Factory (jutsuhq) could not be verified because its page returned 404.

## Q2. Per-project feature mapping against the 13 criteria

### Takeaway
No single open-source project covers the full set of ai-content-agent features. MoneyPrinterTurbo comes closest: it covers (2), (3), (10), (11), (12) and (13) fully and (1), (4), (6) and (8) partially. It lacks thumbnails (5), scheduling with topic dedup (7) and a CapCut export (9). Its publishing goes through the third-party Upload-Post SaaS and does not cover Facebook. Across all projects, features (5) auto-thumbnail and (6) native publishing that includes a Facebook Page are essentially absent. Feature (9) exists only as JianYing/剪映 draft export (NarratoAI) and Premiere XML export (ViralCutter, beta). Vietnamese (11) is verifiably present only in MoneyPrinterTurbo, ShortGPT and NarratoAI.

### Cited Findings

**MoneyPrinterTurbo** (sources: [README](https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/main/README.md), [config.example.toml](https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/main/config.example.toml), [Releases](https://github.com/harry0703/MoneyPrinterTurbo/releases), [azure_voices.json](https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/main/app/services/data/azure_voices.json), [vi.json](https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/main/webui/i18n/vi.json))
- (1) **Partial**:
  - The LLM auto-generates or rewrites "多语言视频脚本" (multi-language scripts) from a topic.
  - Supported LLMs: Kimi, OpenAI, Anthropic Claude, Google Gemini, DeepSeek, Qwen, Azure OpenAI, Volcengine Ark, xAI Grok, MiniMax, Xiaomi MiMo, plus Ollama/OpenRouter/LiteLLM/Groq/OneAPI gateways. **Muse Spark** was added in v1.3.9.
  - No source describes a per-scene storyboard with separate visual prompt and on-screen text fields.
- (2) **Yes**:
  - Stock footage: Pexels/Pixabay/Coverr, plus local uploads.
  - AI video: MiniMax H3 (768P/2K, 4–15 s, 9:16/16:9/1:1), Volcengine Seedance, WaveSpeed, OFox (Seedance, Wan), MuAPI (3–12 s clips).
  - AI images: "OpenAI 兼容文生图...将生成图片转换为动态视频片段" (images turned into motion clips). v1.3.9 made "slow-zoom image effects" the default, which is equivalent to Ken Burns.
  - Adjustable clip duration and fit mode.
  - Veo and Imagen are not named.
- (3) **Yes**: Edge TTS (free, no key), Azure Speech V1/V2, SiliconFlow, Google Gemini TTS, Xiaomi MiMo, MiniMax, ElevenLabs, Chatterbox, Kokoro, Fish Audio, ModelBest VoxCPM (with voice cloning). OpenAI TTS is not named.
- (4) **Partial**:
  - Captions: auto subtitles in two modes, `edge` (TTS timestamps) or `whisper` (faster-whisper large-v3 / large-v3-turbo). Font, position, color, size, outline and background are adjustable.
  - Audio and output: BGM can be random, local or AI-generated, with independent volume. Output is 9:16 1080×1920, 16:9 or 1:1.
  - Not documented: a hook text overlay, a logo watermark (the only `watermark` key is `volcengine_seedance_watermark = false`, the provider's own watermark) and loudness normalization.
- (5) **No (not documented)**: there is no thumbnail feature for the core tool.
- (6) **Partial**:
  - It supports "一键跨平台发布...自动上传至 TikTok、Instagram 和 YouTube Shorts".
  - This goes through the third-party SaaS **Upload-Post** (`upload_post_enabled`, `upload_post_api_key`, `upload_post_platforms = ["tiktok","instagram"]`, `upload_post_auto_upload`, YouTube privacy and made-for-kids flags).
  - "Cross-post jobs run in the current process and are not resumed after restart".
  - There is no Facebook Page support and no native platform API.
- (7) **No (not documented)**: scheduling is not mentioned, and there is no topic rotation or dedup.
- (8) **Partial**: four interfaces, "AI Agent、WebUI、API 和 CLI". The WebUI has task history, settings and API key import/export, and v1.3.9 added diagnostic logging controls. The API docs are at `/docs`. A live job-progress dashboard is not explicitly described.
- (9) **No**: CapCut and JianYing are not mentioned.
- (10) **Partial**: there are many interchangeable LLM, TTS, footage and AI-video providers, configured through config.toml. Publishing has only the single Upload-Post integration, and no publisher plugin architecture is documented.
- (11) **Yes**: `azure_voices.json` (331 voices) includes `vi-VN-HoaiMyNeural` and `vi-VN-NamMinhNeural`, the WebUI ships a Vietnamese translation (`"Language": "Tiếng Việt"`), and scripts can be multi-language.
- (12) **Yes**:
  - Windows: a "Windows 一键启动包" (one-click portable package; a launcher plus browser WebUI, not a native desktop app).
  - Server/self-host: Docker via `ghcr.io/harry0703/moneyprinterturbo:latest`, the API server, and the v1.3.9 `mpt` pip package.
  - Other: Colab, Windows/macOS/Linux.
- (13) **Yes**:
  - WebUI "批量生成多条成片" (batch generation of multiple finished videos).
  - CLI `--batch-file` takes a UTF-8 JSON array or JSONL file. The WebFetch summary says up to 100 tasks.
  - `material_concurrency` (1–8) parallelizes stock downloads.
  - v1.3.9 keeps completed videos when another video in the batch fails.
  - An "AI Agent" Skill mode lets an external agent install and run it.

**Pixelle-Video** (sources: [README](https://raw.githubusercontent.com/AIDC-AI/Pixelle-Video/main/README.md), [README_EN](https://raw.githubusercontent.com/AIDC-AI/Pixelle-Video/main/README_EN.md), [GitHub page](https://github.com/AIDC-AI/Pixelle-Video))
- (1) **Partial**:
  - Pipeline: "文案生成 → 配图规划 → 逐帧处理 → 视频合成" (script, then per-frame image planning, then per-frame processing, then compose). Progress shows "分镜 3/5" (storyboard shots).
  - LLMs: GPT, Qwen, DeepSeek, Ollama (OpenAI-compatible). Claude and Gemini are not named as LLMs.
  - Per-scene on-screen text comes via HTML templates, but per-scene text fields are not documented.
- (2) **Yes**:
  - AI images: "每句话都配上精美的 AI 插图" (an AI illustration for every sentence).
  - AI video models: WAN 2.1, DashScope Wan, Kling, Seedance.
  - Image backends: Nano Banana, Seedream, OpenAI, via ComfyUI or RunningHub workflows.
  - "API 视频片段会尽量根据旁白音频时长生成" (clips are generated to match narration length).
  - Ken Burns is not documented.
- (3) **Yes**: Edge-TTS, Index-TTS, voice cloning from reference audio, and multi-language TTS voices (2026-01-14).
- (4) **Partial**: BGM, HTML video templates (static_/image_/video_*.html), and portrait/landscape/square sizes. Burned-in captions, watermark and loudness normalization are not explicitly documented in the README.
- (5) **Unknown**: not mentioned.
- (6) **No**: not mentioned.
- (7) **No**: not mentioned.
- (8) **Partial**: the Streamlit Web UI (localhost:8501) shows real-time step progress, and a history page was added 2025-11-18. An error log is not documented.
- (9) **No**.
- (10) **Partial**: "原子能力灵活组合" (image, video, TTS and VLM capabilities can be swapped via ComfyUI workflows or direct APIs), and users can drop custom HTML templates into `templates/`. There is no publisher layer.
- (11) **Partial (inferred)**: it uses Edge-TTS, which has vi-VN voices, and multi-language voices. No explicit Vietnamese mention was found.
- (12) **Yes**:
  - Windows: a one-click package (`start.bat` opens the web UI).
  - Server: an `api` folder, and "API 接口支持模板自定义参数" (the API takes template parameters). FastAPI is not named.
  - Other: source install on macOS/Linux.
- (13) **Yes (thinly documented)**: "支持批量创建视频任务" (batch creation of video tasks) and RunningHub parallel processing with configurable concurrency (2025-11-18, 2025-12-28).
- Extra features: digital human talking head, image-to-video and motion transfer pipelines (2026-01), "custom media" analysis, and the claim "本项目完全支持免费运行" (can run fully free).

**MoneyPrinterV2** (sources: [README](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinterV2/main/README.md), [docs/YouTube.md](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinterV2/main/docs/YouTube.md), [config.example.json](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinterV2/main/config.example.json), [Roadmap](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinterV2/main/docs/Roadmap.md))
- (1) **Partial**: an Ollama LLM generates the video idea "based on the account's niche", the script, the title/description and the image prompts. A custom-topic option exists. The only LLM is Ollama (gpt4free is acknowledged).
- (2) **Partial**: "V2 uses AI generated images as the visuals...instead of using stock footage". The image model is Gemini "nanobanana2" `gemini-3.1-flash-image-preview` at 9:16. Animation and AI video are not documented.
- (3) **Yes**: KittenTTS (`tts_voice: "Jasper"`).
- (4) **Partial**: "supports music right from the get-go". The config has `stt_provider: local_whisper` or AssemblyAI and a font setting, but the Roadmap still lists "Subtitles for Shorts" as unchecked, so the docs conflict. Watermark, hook text and loudness normalization are not documented.
- (5) **Unknown**.
- (6) **Partial**: YouTube Shorts upload via a logged-in **Firefox profile** (browser automation). TikTok and Instagram cross-posting go through third-party **Post Bridge** (`post_bridge.platforms: ["tiktok","instagram"]`, `auto_crosspost`). There is no Facebook Page.
- (7) **Partial**: "YouTube Shorts Automator (with CRON Jobs => scheduler)". Topics are LLM-generated from a niche. Dedup is not documented.
- (8) **No**: interactive CLI menu (`python src/main.py`).
- (9) **No**.
- (10) **Partial**: a "more modular architecture" is claimed. It also runs Twitter bots, affiliate marketing and cold outreach.
- (11) **Unknown**.
- (12) **Partial**: a Python CLI on Windows/Unix. There is no desktop app or web server.
- (13) **Partial**: unattended CRON-driven generation and upload per account. There is no list or batch import.

**MoneyPrinter (V1)** (sources: [README](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinter/main/README.md), [docs/configuration.md](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinter/main/docs/configuration.md), [docs/architecture.md](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinter/main/docs/architecture.md))
- (1) **Partial**: "script generation and metadata are fully powered by local Ollama models".
- (2) **No (stock only)**: `PEXELS_API_KEY` is "used to fetch stock video clips".
- (3) **Yes**: the TikTok TTS voice endpoint via a `TIKTOK_SESSION_ID` cookie.
- (4) **Partial**: subtitles via AssemblyAI or "local subtitle generation", rendered with ImageMagick. Music, watermark and loudness normalization are not documented in current docs.
- (5) **Unknown**.
- (6) **Unknown**: the current README says only "Automate the creation of YouTube Shorts". Upload is not described.
- (7) **No**.
- (8) **Partial**: the frontend "submits generation requests and polls job status/events". The API supports `/api/jobs/:id/events` and cancel, and job states are queued/running/completed/failed/cancelled.
- (9) **No**.
- (10) **Unknown**.
- (11) **Unknown**.
- (12) **Yes (server)**: Docker Compose with frontend, backend, worker and Postgres. There is no desktop app.
- (13) **Partial**: a "DB-backed generation queue...reliable, restart-safe processing". Bulk topic import is not documented.

**ShortGPT** (sources: [README](https://raw.githubusercontent.com/RayVentura/ShortGPT/master/README.md), [languages.py](https://raw.githubusercontent.com/RayVentura/ShortGPT/stable/shortGPT/config/languages.py))
- (1) **Partial**: OpenAI only, "generating scripts and prompts". The LLM-oriented "Editing Markup Language" breaks editing into blocks.
- (2) **No (sourced only)**: Pexels and Bing Image.
- (3) **Yes**: ElevenLabs and EdgeTTS, in "30+ more languages".
- (4) **Partial**: "Automates the generation of video captions", and customization "from language selection to watermark addition". Music, resolution and loudness normalization are not documented.
- (5) **Unknown**.
- (6) **No**: ContentShortEngine only handles "adding YouTube metadata".
- (7) **No**.
- (8) **Partial**: Gradio web UI on port 31415.
- (9) **No**.
- (10) **Partial**: an engine framework (ContentShortEngine, ContentVideoEngine, ContentTranslationEngine, EditingEngine).
- (11) **Yes**: `Language.VIETNAMESE` maps to `{'male': 'vi-VN-NamMinhNeural', 'female': 'vi-VN-HoaiMyNeural'}`. A translation/dubbing engine is also included.
- (12) **Partial**: a Docker-hosted Gradio server and Colab. There is no desktop app.
- (13) **No/Unknown**: no batch mode is documented.

**MoneyPrinterPlus** (source: [README](https://raw.githubusercontent.com/ddean2009/MoneyPrinterPlus/main/README.md))
- (1) **Partial**: LLM script generation via OpenAI, Azure, Kimi, Qianfan, Baichuan, Tongyi Qwen, DeepSeek or Ollama.
- (2) **No**: it uses local or online footage. "接入stable diffusion，AI生图" and "接入Sora等AI视频大模型" are listed as *not yet implemented*.
- (3) **Yes**: Azure, Alibaba Cloud and Tencent Cloud TTS, ChatTTS, GPT-SoVITS and CosyVoice, with "100+不同的语音种类" (100+ voice types).
- (4) **Partial**: 30+ transitions, BGM with volume control, custom subtitles (fasterwhisper/sensevoice recognition) and multiple resolutions.
- (5) **Unknown**.
- (6) **Partial**: "视频批量自动发布...抖音，快手，小红书，视频号" (batch auto-publish to Douyin, Kuaishou, Xiaohongshu and WeChat Channels). It does not support YouTube, TikTok or Facebook.
- (7) **Unknown**.
- (8) **Partial**: a web UI (界面概览). Details are not verified.
- (9) **No**.
- (10) **Unknown**.
- (11) **Unknown**.
- (12) **Yes**: a Windows "小白版" (beginner) package since V4.5 (`setup.bat`/`start.bat`), and a Dockerfile (2024-09-27).
- (13) **Yes**: "一键批量生成各类短视频", "批量产出大量不重复的短视频" (bulk unique videos), and a batch upload tool.

**short-video-maker** (source: [README](https://raw.githubusercontent.com/gyoridavid/short-video-maker/main/README.md))
- (1) **No (externalized)**: there is no built-in LLM. The client submits scenes of "Text: Narration" plus "Search terms". The LLM is an external agent such as n8n.
- (2) **No**: Pexels only. "you cannot supply your own video or images".
- (3) **Yes**: Kokoro TTS.
- (4) **Partial**: Whisper (whisper.cpp) captions with styling, "Background music with genre/mood selection", and portrait or landscape output. Watermark, hook text and loudness normalization are not documented.
- (5) **No**.
- (6) **No**.
- (7) **No (external n8n)**.
- (8) **Partial**: a third-party Web UI.
- (9) **No**.
- (10) **Partial**: "exposes an MCP and a REST server".
- (11) **No**: "only capable generating videos with English voiceover".
- (12) **Partial**: Docker images (tiny/normal/CUDA) and npx. "Windows is NOT supported".
- (13) **Partial**: the REST API can be driven in bulk by an external orchestrator. `CONCURRENCY=1` is advised "to overcome OOM errors coming from Remotion".

**short-video-factory / 短视频工厂** (sources: [README](https://raw.githubusercontent.com/YILS-LIN/short-video-factory/main/README.md), [GitHub page](https://github.com/YILS-LIN/short-video-factory))
- (1) **Partial**: LLM copywriting "兼容通用的 OpenAI 接口格式" (any OpenAI-compatible API).
- (2) **No**: users supply "视频分镜素材" (storyboard footage), which is auto-remixed.
- (3) **Yes**: EdgeTTS.
- (4) **Partial**: "自动添加字幕和特效" (auto subtitles and effects).
- (5) **Unknown**.
- (6) **No**.
- (7) **No**.
- (8) **N/A**: it is a desktop GUI.
- (9) **No**.
- (10) **Unknown**.
- (11) **Partial**: multi-language "中文、英文等", and EdgeTTS. Vietnamese is not stated.
- (12) **Yes (desktop)**: a cross-platform Electron desktop app for Windows, macOS and Linux, distributed via GitHub Releases.
- (13) **Yes**: "批量处理，支持一个批量任务，按预设自动持续合成视频" (a batch task that continuously synthesizes videos from a preset).

**ViMax** (sources: [README](https://raw.githubusercontent.com/HKUDS/ViMax/main/readme.md), [GitHub page](https://github.com/HKUDS/ViMax))
- (1) **Yes (richer)**: Idea2Video, Script2Video and Novel2Video produce "stories, characters, scripts, storyboards, shots". An agent loop and TUI support revision. LLMs are OpenAI-compatible (Gemini via OpenRouter) or MiniMax.
- (2) **Yes**: images via Nano Banana or OpenRouter GPT Image 2. Video via Veo (example config), Seedance 2.0 Fast or Google Omni.
- (3) **Unknown**: "character voice, and sound effects" is claimed, but no provider is named.
- (4) **Unknown**: captions and 9:16 output are not stated.
- (5)–(7) **No**: not mentioned.
- (8) **Yes**: the Web UI (v1.2.0) has projects, storyboard previews, render progress and checkpoints.
- (9) **No**.
- (10) **Partial**: "extensible workflow" with provider settings.
- (11) **Unknown**.
- (12) **Partial**: Web UI and TUI, self-hosted.
- (13) **Partial**: "Parallelized generation" of shots within a project. There is no multi-video batch.

**AI Shorts Generator (AbdullahNaveed)**: architecturally the closest analogue to ai-content-agent (source: [README](https://raw.githubusercontent.com/AbdullahNaveed/ai-shorts-generator/main/README.md), [GitHub page](https://github.com/AbdullahNaveed/ai-shorts-generator))
- (1) **Partial**: "script (OpenAI, structured JSON)" per scene. OpenAI only.
- (2) **Yes**: "cinematic images via Flux and motion clips via Wan on fal.ai", or Pexels/Pixabay stock. A "reusable semantic library" uses "match-then-generate". The assembler applies "Ken Burns / motion".
- (3) **Yes**: OpenAI `gpt-4o-mini-tts`.
- (4) **Partial (strong)**: "Word-by-word karaoke captions auto-aligned with faster-whisper", a "Music bed with automatic ducking", an "Optional watermark (your logo + disclaimer)", a branded outro and 1080×1920 output. There is no hook overlay: "the only on-screen text is the karaoke captions". Loudness normalization is not documented.
- (5) **Unknown**.
- (6) **No**: "No — you review and post manually... A publishing backend is a welcome PR". It produces per-platform titles and hashtags.
- (7) **Partial**: a topic backlog (`data/topics.txt`, `topics import`). Cron and dedup are not documented.
- (8) **Partial**: a local Flask "review dashboard" for previewing, swapping clips, picking music and downloading.
- (9) **No**.
- (10) **Unknown**.
- (11) **Unknown**.
- (12) **Partial**: local Python with Windows `start.bat`/`stop.bat`.
- (13) **Yes**: `python run.py batch 7` makes "a week's worth from data/topics.txt".

**AutoShorts AI (SaarD00)** (sources: [README](https://raw.githubusercontent.com/SaarD00/AI-Youtube-Shorts-Generator/master/README.md), [GitHub page](https://github.com/SaarD00/AI-Youtube-Shorts-Generator))
- (1) **Partial**: "Google Gemini 2.0 Flash" scripts with a "Hook → Context → Mechanism → Twist" structure. "The AI picks a trending topic".
- (2) **No (stock)**: "two distinct stock videos per scene from Pexels".
- (3) **Yes**: edge-tts.
- (4) **Partial**: FFmpeg smart trimming to audio, xfade transitions, silence removal, random avatar injection, and `yuv420p`/`faststart` flags. Captions are not confirmed in the excerpt read.
- (5) **Unknown**.
- (6) **Partial**: `--upload` publishes to YouTube via OAuth (private/unlisted/public). YouTube only.
- (7) **Partial**: a cron example `0 9 * * * ... main.py`, a GitHub Actions workflow and trending topic selection. Dedup is not documented.
- (8) **No**: CLI.
- (9) **No**.
- (10) **Unknown**.
- (11) **Unknown**.
- (12) **Partial**: CLI with Docker noted. The README says "a container is not where you want a scheduled run".
- (13) **Yes**: `--runs N` and `--fail-fast`.

**NarratoAI** (adjacent: commentary over existing footage) (sources: [README](https://raw.githubusercontent.com/linyqh/NarratoAI/main/README.md), [voice.py](https://raw.githubusercontent.com/linyqh/NarratoAI/main/app/services/voice.py))
- (1) **Partial**: LLM-written commentary from video understanding (Qwen2-VL, TwelveLabs Pegasus). It starts from a source video, not a topic.
- (2) **No**: it edits user-supplied film or drama footage.
- (3) **Yes**: Edge TTS, IndexTTS-1.5/2, OmniVoice, Tencent and Doubao TTS, and voice cloning.
- (4) **Partial**: subtitles via Fun-ASR (0.7.9) and optional Sonilo AI music (0.8.6).
- (5)–(7) **No/Unknown**.
- (8) **Partial**: Streamlit WebUI at 127.0.0.1:8501.
- (9) **Yes (JianYing)**: "支持导出剪映草稿" (export JianYing drafts; JianYing is the Chinese edition of CapCut).
- (10) **Partial**: LLM provider management. LiteLLM was removed in 0.7.7 "出于安全考虑" (for security reasons).
- (11) **Yes (TTS)**: `filter_locals = ["zh-CN", "en-US", "zh-HK", "zh-TW", "vi-VN"]` with `vi-VN-HoaiMyNeural` and `vi-VN-NamMinhNeural`.
- (12) **Yes**: Windows x64 and macOS arm64 integrated packages, plus Docker.
- (13) **No/Unknown**.

**Clippers and others (brief)**
- SamurAIGPT AI-Youtube-Shorts-Generator turns long YouTube videos into ranked 9:16 clips. It uses GPT/Gemini highlight scoring, Whisper, and OpenCV face-tracking crop, through either a CLI or a Python lib. Batch works by "`xargs` an entire URL list", and output is `--output-json`. Its default mode relies on the paid MuAPI — [README](https://raw.githubusercontent.com/SamurAIGPT/AI-Youtube-Shorts-Generator/main/README.md).
- ViralCutter uses Gemini, GPT-4 or local GGUF LLMs, WhisperX, "Hormozi"-style word-highlight captions, split screen and active speaker, subtitle translation to 10+ languages, "Exporta XML para Premiere Pro (Beta)" (the closest analogue to feature 9), and a Gradio WebUI with a project gallery — [README](https://raw.githubusercontent.com/RafaelGodoyEbert/ViralCutter/main/README.md).
- RedditVideoMakerBot: "this repository won't attempt to upload this content", so uploading is manual — [README](https://raw.githubusercontent.com/elebumm/RedditVideoMakerBot/master/README.md).
- Text-To-Video-AI:
  - LLMs: OpenAI, Groq or Gemini.
  - Voice and captions: EdgeTTS or ElevenLabs, Pexels B-roll, Whisper or Deepgram captions, and portrait or landscape output.
  - Sample videos used "Veo3 AI B-roll" and "Suno AI background music" with a React/Remotion engine.
  - Source: [README](https://raw.githubusercontent.com/SamurAIGPT/Text-To-Video-AI/main/README.md).
- ViGen: "Idea to Video" and "Script to Video", using Gemini 2.5 Flash Image, Imagen 3 and Veo 3.1. It has character consistency via reference images and ships ViGen_Windows.exe — [README](https://raw.githubusercontent.com/PhucHuwu/ViGen/main/README.md).
- alamshafil/auto-shorts uses Ollama by default and also supports OpenAI, Gemini and Claude. Video types include text-message stories, would-you-rather, ranking, quiz and news. It has a Next.js/Express web UI, and it is discontinued — [README](https://raw.githubusercontent.com/alamshafil/auto-shorts/main/README.md).

### Inferences
Summary matrix (Y = Yes, P = Partial, N = No, ? = Unknown; derived from the cited findings above):

| Project | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MoneyPrinterTurbo | P | Y | Y | P | N | P (Upload-Post; TT/IG/YT) | N | P | N | P | Y | Y | Y |
| Pixelle-Video | P | Y | Y | P | ? | N | N | P | N | P | P | Y | Y |
| MoneyPrinterV2 | P | P | Y | P | ? | P (YT via browser; TT/IG via Post Bridge) | P | N | N | P | ? | P | P |
| MoneyPrinter V1 | P | N | Y | P | ? | ? | N | P | N | ? | ? | Y | P |
| ShortGPT | P | N | Y | P | ? | N | N | P | N | P | Y | P | N |
| MoneyPrinterPlus | P | N | Y | P | ? | P (CN platforms only) | ? | P | N | ? | ? | Y | Y |
| short-video-maker | N | N | Y | P | N | N | N | P | N | P | N | P | P |
| short-video-factory | P | N | Y | P | ? | N | N | n/a | N | ? | P | Y (Electron) | Y |
| ViMax | Y | Y | ? | ? | N | N | N | Y | N | P | ? | P | P |
| AbdullahNaveed ai-shorts-generator | P | Y | Y | P | ? | N | P | P | N | ? | ? | P | Y |
| SaarD00 AutoShorts AI | P | N | Y | P | ? | P (YT only) | P | N | N | ? | ? | P | Y |
| NarratoAI (adjacent) | P | N | Y | P | ? | N | N | P | Y (JianYing) | P | Y | Y | ? |

- Features where ai-content-agent stands out among open-source projects:
  - (5) auto thumbnail: no project documents it.
  - (6) a Facebook Page publisher, and native (non-SaaS) multi-platform publishing.
  - (7) scheduling combined with topic rotation and dedup of posted topics: only CRON or trending-topic picking exists elsewhere, with no dedup.
  - (9) CapCut desktop draft export: only JianYing (NarratoAI) and Premiere XML (ViralCutter beta) exist.
  - Hook text overlay and loudness normalization within (4).
  - The specific Google stack (Imagen, Veo, Gemini TTS) in a shorts pipeline: only ViGen, ViMax and the Text-To-Video-AI samples use Veo, and none of those is a full shorts pipeline with publishing.
- Features where competitors are ahead or equal:
  - MoneyPrinterTurbo's provider breadth: 15+ LLMs including Muse Spark, 11 TTS engines, 5+ AI-video APIs, and Pexels/Pixabay/Coverr.
  - Its Vietnamese UI translation.
  - Pixelle-Video's ComfyUI workflow pluggability and digital-human/motion-transfer pipelines.
  - Whisper-based word-level caption alignment, which is standard in MPT, short-video-maker, ViralCutter and AbdullahNaveed.
  - MCP/REST server exposure (short-video-maker; MPT has a REST API and an agent Skill).
- MoneyPrinterTurbo's v1.3.9 additions (slow-zoom images and Muse Spark) show it converging on ai-content-agent's feature set.

### Gaps
- Pixelle-Video caption and subtitle behaviour, and any watermark option, were not documented in the README sections read.
- MoneyPrinter V1's current upload capability: older versions reportedly uploaded to YouTube, but no 2026 source confirms this.
- Loudness normalization (e.g. FFmpeg `loudnorm`) is not documented for any project. Answering this would require reading the source code.
- Whether MoneyPrinterTurbo's WebUI shows a live per-step progress bar was not confirmed.
- ViMax TTS, caption and 9:16 support were not stated on its page.
- Vietnamese for Pixelle-Video, MoneyPrinterPlus, short-video-factory and AbdullahNaveed is inferred at best, from Edge/Azure TTS supporting vi-VN, and has no explicit project evidence.

## Q3. Batch / mass production (criterion 13) and throughput or cost-per-video figures

### Takeaway
Bulk, unattended production is common but implemented unevenly:
- **True bulk-job features**: MoneyPrinterTurbo (JSON/JSONL batch manifest, WebUI batch, failure isolation), Pixelle-Video (batch task creation, parallel RunningHub), MoneyPrinterPlus (bulk generation, remix and upload), short-video-factory (continuous preset batch) and AbdullahNaveed (topic backlog batch).
- **Queue or cron driven**: MoneyPrinter V1 (Postgres job queue), MoneyPrinterV2 (CRON), SaarD00 (`--runs N` plus cron).
- **API-driven by external orchestrators**: short-video-maker (n8n via MCP/REST).

No project publishes a measured cost-per-video. Available figures are sponsor-price claims and platform quota limits.

### Cited Findings
- MoneyPrinterTurbo:
  - "如需顺序执行多个任务，可通过 `--batch-file` 提供 UTF-8 JSON 数组或 JSONL" (sequential multi-task execution via a batch file), e.g. `uv run python cli.py --batch-file ./tasks.json --stop-at video`. The WebUI supports "批量生成多条成片" — [README](https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/main/README.md).
  - The WebFetch summary of the repo page says the batch manifest takes "up to 100 tasks" — [GitHub page](https://github.com/harry0703/MoneyPrinterTurbo).
  - v1.3.9 "kept completed videos when another video in the same batch fails" — [Releases](https://github.com/harry0703/MoneyPrinterTurbo/releases).
  - Stock downloads can run with `material_concurrency` of 1, 2, 4, 6 or 8 ("the code caps values at 8"). Higher values "can trigger provider rate limits" — [config.example.toml](https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/main/config.example.toml).
  - Cross-post queue limit: `upload_post_max_pending_tasks = 10`. "When the limit is reached, video generation still succeeds and only cross-posting is rejected" — [config.example.toml](https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/main/config.example.toml).
  - Hardware: "如果你主要依赖云端 LLM、云端 TTS 和在线素材源，CPU 与内存比 GPU 更重要" (with cloud LLM, TTS and footage, CPU and RAM matter more than GPU). A GPU helps when using faster-whisper or batch generation — [README](https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/main/README.md).
  - Sponsor prices (vendor claims, not measured per-video costs): MiniMax H3 video "768P 仅 0.09 元/秒，2K 仅 0.15 元/秒" (CNY per second); APIMart "GPT-Image-2 低至 $0.006/张，1 美元可出图 160+ 张" (as low as $0.006 per image) — [README](https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/main/README.md).
- Pixelle-Video: "支持批量创建视频任务" and RunningHub parallel processing (2025-11-18). RunningHub concurrency limit is configurable (2025-12-28), and RunningHub 48G-VRAM machines are supported (2026-01-06). The README claims "本项目完全支持免费运行" (can run fully free) — [README](https://raw.githubusercontent.com/AIDC-AI/Pixelle-Video/main/README.md).
- MoneyPrinterPlus:
  - Claims "一键批量生成各类短视频" and "批量产出大量不重复的短视频" (bulk generation of unique videos), plus a "批量视频自动上传工具" (batch auto-upload tool).
  - A tutorial is titled "一天上万短视频不是梦" ("10,000+ short videos a day is not a dream"; a marketing claim) and another "一键万条短视频" — [README](https://raw.githubusercontent.com/ddean2009/MoneyPrinterPlus/main/README.md).
- short-video-factory: "批量处理，支持一个批量任务，按预设自动持续合成视频" — [README](https://raw.githubusercontent.com/YILS-LIN/short-video-factory/main/README.md).
- AbdullahNaveed ai-shorts-generator:
  - `python run.py batch 7`, "a week's worth from data/topics.txt", plus a topic backlog import.
  - The cost-control design reuses clips via a semantic library "instead of paying to regenerate it".
  - "Graceful degradation" covers a missing API key or GPU.
  - Source: [README](https://raw.githubusercontent.com/AbdullahNaveed/ai-shorts-generator/main/README.md).
- SaarD00 AutoShorts AI:
  - `--runs N` ("Generate N videos in one invocation") and `--fail-fast`.
  - YouTube limit: "An upload costs 1600 units against a default daily quota of 10,000", which works out to about **6 uploads/day per Google Cloud project**. "unverified projects have uploads forced to private".
  - Source: [GitHub page](https://github.com/SaarD00/AI-Youtube-Shorts-Generator).
- MoneyPrinter V1: Postgres-backed queue with worker claim. Job states are queued, running, completed, failed and cancelled. It is "designed for reliability, restart safety, and future scaling" — [architecture.md](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinter/main/docs/architecture.md).
- MoneyPrinterV2: "YouTube Shorts Automator (with CRON Jobs => scheduler)"; `threads` config — [README](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinterV2/main/README.md); [config.example.json](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinterV2/main/config.example.json).
- short-video-maker: the REST and MCP server can be driven by n8n workflows. `CONCURRENCY` is "how many browser tabs are opened in parallel during a render", and it is set to 1 in Docker images to avoid Remotion OOM. Requirements are ≥3 GB free RAM (4 GB recommended), ≥2 vCPU and ≥5 GB disk — [README](https://raw.githubusercontent.com/gyoridavid/short-video-maker/main/README.md).
- SamurAIGPT clipper: "Batch processing: `xargs` an entire URL list"; no per-clip credits — [README](https://raw.githubusercontent.com/SamurAIGPT/AI-Youtube-Shorts-Generator/main/README.md).
- NarratoAI sponsor claim: with SiliconFlow, "剪辑10分钟视频仅需0.1元" (editing a 10-minute video costs ¥0.1) — [README](https://raw.githubusercontent.com/linyqh/NarratoAI/main/README.md).
- A third-party review summary notes that MoneyPrinterTurbo "does not bundle any LLM inference, so you supply the API access and pay the token costs", and that "stock-footage output tends to look like stock footage". This is a secondary aggregator source — [aitoolsatlas review](https://aitoolsatlas.ai/tools/moneyprinterturbo/review).

### Inferences
- Scaling an unattended pipeline to many videos a day on YouTube is capped by the Data API quota (~6 uploads/day per default project) unless a quota increase is granted. Any mass-production claim for ai-content-agent must account for this, and so must competitors that upload natively (SaarD00) or through SaaS (MPT via Upload-Post, MPV2 via Post Bridge).
- MoneyPrinterTurbo's batch is a sequential manifest runner (JSON/JSONL), not a persistent scheduler. ai-content-agent's cron plus topic rotation plus dedup is a differentiator for "unattended for weeks" operation. MPT's per-task failure isolation and concurrency caps are worth matching.
- None of the projects publishes an end-to-end cost-per-video figure. Credible numbers would have to be computed from provider prices.

### Gaps
- No measured throughput figures (videos/hour on given hardware) were found for any project.
- No independent cost-per-video figures were found. Only vendor and sponsor unit prices were available.
- Whether Pixelle-Video batch tasks accept a topic list (CSV) or only repeated single tasks was not documented.

## Q4. Maturity signals and known problems

### Takeaway
MoneyPrinterTurbo shows the strongest maturity signals: frequent releases (v1.3.7 to v1.3.9 between September and October), only 10 open issues against 58 open PRs, Docker images on GHCR, and a pip package. Pixelle-Video and NarratoAI are actively maintained in 2026. ShortGPT, MoneyPrinterPlus and alamshafil/auto-shorts show stagnation or abandonment. Several projects have platform limits: short-video-maker has no Windows support and English only, and ViralCutter is alpha. Several also funnel users toward paid APIs (SamurAIGPT repos via MuAPI and vadoo.tv; MPT and NarratoAI through heavy sponsor sections).

### Cited Findings
- MoneyPrinterTurbo: 10 open issues and 58 open PRs; v1.3.9 "Fixed a range of rendering, audio, subtitle, and task-handling issues" — [GitHub page](https://github.com/harry0703/MoneyPrinterTurbo); [Releases](https://github.com/harry0703/MoneyPrinterTurbo/releases).
  - The README FAQ covers Whisper model download failures from Hugging Face, ImageMagick and ffmpeg detection, and advice to avoid project paths with Chinese characters or spaces on Windows. The bundled BGM "来自于 YouTube 视频，如有侵权，请删除" (taken from YouTube videos; delete if infringing), which is a copyright risk — [README](https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/main/README.md).
  - The README has a large sponsor block (Kimi, Volcengine, APIMart, MiniMax/Metaso, Infistar, OfoxAI, 胜算云, RunningHub) — [README](https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/main/README.md).
- Pixelle-Video: 151 issues on the tab, 24 PRs. Changelog fixes include "锁定 edge-tts 版本修复 TTS 服务不稳定问题" (pinning the edge-tts version to fix unstable TTS, 2025-12-10) — [GitHub page](https://github.com/AIDC-AI/Pixelle-Video); [README](https://raw.githubusercontent.com/AIDC-AI/Pixelle-Video/main/README.md).
- NarratoAI: 3 open issues, releases from 0.8.1 to 0.8.6 between June and July 2026. LiteLLM was removed "出于安全考虑" (0.7.7, 2026-03-27). The README warns about others reselling the free software under new names — [GitHub page](https://github.com/linyqh/NarratoAI); [README](https://raw.githubusercontent.com/linyqh/NarratoAI/main/README.md).
- ShortGPT: 74 open issues, no releases. "More documentation incomming, please be patient" — [GitHub page](https://github.com/RayVentura/ShortGPT); [README](https://raw.githubusercontent.com/RayVentura/ShortGPT/master/README.md).
- MoneyPrinterPlus: 79 issues, and the latest changelog is 2025-02-08 — [GitHub page](https://github.com/ddean2009/MoneyPrinterPlus).
- MoneyPrinter V1: "Pull Requests will not be accepted for the time-being" — [README](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinter/main/README.md).
- MoneyPrinterV2: Roadmap still lists "Subtitles for Shorts" as unimplemented. YouTube upload depends on a logged-in Firefox profile (browser automation, which can break) — [Roadmap](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinterV2/main/docs/Roadmap.md); [YouTube.md](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinterV2/main/docs/YouTube.md).
- short-video-maker: "Windows is NOT supported at the moment (whisper.cpp installation fails occasionally)"; English only — [README](https://raw.githubusercontent.com/gyoridavid/short-video-maker/main/README.md).
- alamshafil/auto-shorts: discontinued, "not meant to be used in production environments yet" — [README](https://raw.githubusercontent.com/alamshafil/auto-shorts/main/README.md).
- ViralCutter: "0.8v Alpha", and it needs NVIDIA GPU and C++ Build Tools for insightface — [GitHub page](https://github.com/RafaelGodoyEbert/ViralCutter); [README](https://raw.githubusercontent.com/RafaelGodoyEbert/ViralCutter/main/README.md).
- SamurAIGPT repos: the default `--mode api` relies on MuAPI. Text-To-Video-AI recommends a "Premium API" as "Option 1" — [AI-Youtube-Shorts-Generator README](https://raw.githubusercontent.com/SamurAIGPT/AI-Youtube-Shorts-Generator/main/README.md); [Text-To-Video-AI README](https://raw.githubusercontent.com/SamurAIGPT/Text-To-Video-AI/main/README.md).
- RedditVideoMakerBot deliberately does not upload, "for the sake of avoiding any sort of community guideline issues" — [README](https://raw.githubusercontent.com/elebumm/RedditVideoMakerBot/master/README.md).

### Inferences
- Chinese-ecosystem projects (MPT, Pixelle, NarratoAI, MoneyPrinterPlus, short-video-factory) dominate activity and stars. Their providers skew to Chinese clouds (Kimi, Qwen, Volcengine Seedance, MiniMax, RunningHub). That leaves room for a Google-stack plus Vietnamese-market positioning (Imagen, Veo, Gemini TTS, vi-VN, Facebook Page publishing).
- Platform policy risk (YouTube's stance on automated or "reused" content) shapes design choices. MPV2 justifies AI images over stock as "less likely to be flagged by YouTube", and RedditVideoMakerBot avoids uploading altogether — [YouTube.md](https://raw.githubusercontent.com/FujiwaraChoki/MoneyPrinterV2/main/docs/YouTube.md).

### Gaps
- Issue-tracker contents (top complaints, crash classes) were not read, because GitHub issue search via the API was blocked. Known problems are taken only from READMEs, FAQs and changelogs.
- Reddit and HN user reviews could not be retrieved. Third-party review sites (aiindigo.com, ghtrends.pages.dev) failed DNS resolution in this session and would need to be allowed in network settings.
