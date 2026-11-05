# Source-code deep dive and activity of the leading open-source AI short-video generators, plus missed projects (as of 2026-11-04/05)

Method note (applies to everything below):
- **Source access.** `api.github.com` was tried once more and is still blocked. `gh api` returned HTTP 403 ("GitHub access to this repository is not enabled for this session"), and a plain `curl` to the API also returned 403. `git clone` over HTTPS **did** work, so each target repo was cloned blobless (`--filter=blob:none`, full history) on 2026-11-04/05 and searched with `git grep`. Every code claim gives a file path, linked to its github.com blob URL on the default branch. Line numbers are from the clone on 2026-11-04/05 and may drift.
- **Activity metrics.** Commit and tag metrics come from `git log` / `git for-each-ref` on those clones (author dates; windows: 30d = since 2026-10-05, 90d = since 2026-08-06, 365d = since 2025-11-04). Issue counts come from github.com issue pages read with WebFetch on 2026-11-05. `curl` to github.com HTML returned 403, but WebFetch worked.
- **Blocked hosts.** `huggingface.co` and `gitee.com` failed DNS ("outside the session's allowed network domains"), so Hugging Face Spaces and Gitee were **not** searched. The pypi.org search page did not render (JS wall), but the PyPI JSON API worked.
- **Scoring.** Feature numbers follow the brief: (1) LLM storyboard, (2) per-scene AI visuals, (3) TTS, (4) FFmpeg edit bundle, (5) thumbnail, (6) publish YT+TikTok+FB Page, (7) scheduling + topic rotation/dedup, (8) dashboard with progress/history/error log, (9) CapCut draft, (10) pluggable providers/publishers, (11) Vietnamese, (12) Windows desktop/server, (13) batch. Y = Yes, P = Partial, N = No, U = Unknown.

## Q1. Source-level resolution of "?" cells for the top projects

### Takeaway
Source code overturns several README-based assumptions in the earlier report:
- **Loudness normalization is not unique to ai-content-agent.** AbdullahNaveed (`loudnorm=I=-14` plus sidechain ducking), short-video-factory (`loudnorm=I=-16`), NarratoAI (an `AudioNormalizer` with an LUFS target) and ArcReel (BGM normalized to −16 LUFS) all implement it, and so do several missed projects.
- **MoneyPrinterTurbo has no loudness normalization, thumbnail, logo or hook overlay.** It has word-level captions (Edge WordBoundary or faster-whisper `word_timestamps`), a WebUI task history with progress bar and diagnostic logging, and a hard cap of 100 batch tasks.
- **Pixelle-Video has a true per-scene storyboard data model** (`StoryboardFrame` with narration and image_prompt). Its "captions" are per-scene narration text rendered through HTML templates, with no word timing, no Ken Burns, no loudness normalization and no user watermark.
- **Hook-title overlays exist in leamsigc** (`burn_subtitles_and_hook`). **MoneyPrinterV2 does burn subtitles**, despite its outdated Roadmap.

### Cited Findings

**MoneyPrinterTurbo (harry0703, MIT, Python/MoviePy)**
- (4) Composition uses MoviePy (`from moviepy import ...`, `SubtitlesClip`) in `app/services/video.py`. The audio mix is only `afx.MultiplyVolume(voice_volume)` for the voice and `afx.MultiplyVolume(bgm_volume)` + `afx.AudioLoop` + `afx.AudioFadeOut(3)` for BGM, combined with `CompositeAudioClip` (lines ~1865–1946) — [video.py](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/app/services/video.py).
  - `git grep` across all `.py/.toml/.md/.json` files finds **zero hits** for `loudnorm`, `pyloudnorm`, `dynaudnorm` or `LUFS`.
  - The project's own docs say the BGM mix "does not normalize narration away" — [docs/video-projects.md](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/docs/video-projects.md).
- (4) Logo and watermark: the only `watermark` code is provider flags (Volcengine Seedance, LoomLoom prompt "No text, subtitles, captions, watermarks, logos") — [loomloom.py](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/app/services/loomloom.py). There is **no user logo overlay**.
- (4) Hook: the only "hook" hits are the social-metadata prompt (`"title": a catchy hook, at most … characters`, llm.py:1317, inside `generate_social_metadata`, llm.py:1378) and code comments. There is **no on-video hook-text overlay** — [llm.py](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/app/services/llm.py).
- (4) Caption timing:
  - `generate_subtitle()` in task.py:655–728 reads `subtitle_provider` (default `"edge"`).
  - `edge` uses TTS boundaries: `voice.create_subtitle(... word_level=is_word_level)`, `communicate_kwargs["boundary"] = "WordBoundary"` (voice.py:1356), and Azure `SpeechServiceResponse_RequestWordBoundary` (voice.py:1901).
  - `whisper` uses faster-whisper `WhisperModel(...)` with `word_timestamps=True` (subtitle.py:45, 81), plus a Levenshtein `correct()` against the script (subtitle.py:204–230).
  - The display modes are `sentence` and `word_by_word` (task.py, `subtitle_display_mode`).
  - Subtitles also have a "spring" pop animation (`_apply_subtitle_spring_animation`, video.py:188).
  - Sources: [task.py](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/app/services/task.py); [subtitle.py](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/app/services/subtitle.py); [voice.py](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/app/services/voice.py).
  - Open-tracker evidence that this is fragile: issue #1761 "Whisper sentence subtitles get zero timestamps", closed 2026-11-04 — [issues](https://github.com/harry0703/MoneyPrinterTurbo/issues?q=is%3Aissue).
- (2) Ken Burns: `render_image_zoom_video()` (video.py:1974) is a centre zoom of `1 + (clip_duration*0.03)*(t/duration)`, roughly 3%/s. It has no pan and no varied presets. "Static" is the alternative mode — [video.py](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/app/services/video.py).
- (5) Thumbnail: there is **no thumbnail code**. The only "thumbnail/封面" hits are the README sponsor text and an album-cover comment in bgm.py — [repo](https://github.com/harry0703/MoneyPrinterTurbo).
- (1) The LLM writes N script paragraphs (`build_script_prompt`, paragraph-number clamping) plus stock search terms (`generate_terms`). It does not write a per-scene storyboard with visual prompt and on-screen text — [llm.py](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/app/services/llm.py).
  - New (dated 2026-10-22 in git): an opt-in "editable local video projects" CLI with stable scene IDs and SHA-256 artifact reuse (`app/services/video_project.py`).
  - It "makes no API calls and does not publish videos", and "Word-aligned subtitles, transitions, overlays and provider generation are not implemented by this first local renderer" — [docs/video-projects.md](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/docs/video-projects.md).
- (6) Upload-Post module header: "cross-posting videos to TikTok, Instagram and YouTube Shorts" (upload_post.py:2). The default platforms are `["tiktok","instagram"]` (config.example.toml:649), and the WebUI multiselect offers `["tiktok","instagram","youtube"]` (webui/Main.py:4354).
  - task.py:75–80 maps `"facebook": "facebook_reels"` for LLM caption generation (added 2026-08-21, "use LLM captions for cross-posts"). A Facebook target may therefore work through manual config, but it is not exposed in the UI. Mark it **Unknown/Partial**.
  - Sources: [upload_post.py](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/app/services/upload_post.py); [task.py](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/app/services/task.py).
- (7) Scheduling: the only `cron` hit is a CI workflow (`.github/workflows/security.yml`). There is no scheduler and no topic dedup in code — [repo](https://github.com/harry0703/MoneyPrinterTurbo).
- (8) The WebUI has:
  - a "Task Status History" view (`_scan_history_tasks(limit=30/50)`, Main.py:986–1152);
  - a live `st.progress` bar (Main.py:2121), refreshed by a timed Streamlit fragment every ~2 s (Main.py:1396–1453);
  - failure messages via `st.error(f"{message}: {error}")` (Main.py:2140–2148);
  - a "Diagnostic Logging" expander with log level and request logging (Main.py:3327–3339; docs/diagnostic-logging.md).
  - REST: `/videos`, `/subtitle`, `/audio`, `GET /tasks`, plus stream and download routes (app/controllers/v1/video.py:214–583). `generation_progress.py` relays provider long-task states (queued/running/failed) into the shared task store.
  - Verdict: close to **Yes**. There is no persistent error-log page, but per-task errors and diagnostic logs are shown.
  - Source: [webui/Main.py](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/webui/Main.py).
- (13) Batch: `_BATCH_FILE_MAX_BYTES = 1024*1024` and `_BATCH_TASK_MAX_COUNT = 100` (cli.py:35–36); `--batch-file` takes a JSON array or JSONL — [cli.py](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/cli.py).
- (11) Vietnamese is present in `webui/i18n/vi.json`, `azure_voices.json` and `docs/voice-list.txt` (git grep) — [repo](https://github.com/harry0703/MoneyPrinterTurbo/tree/main/webui/i18n).
- PyPI: the official package `mpt` 1.3.9 was uploaded 2026-10-21 (MIT, "Official MoneyPrinterTurbo package … maintained by harry0703"). An unrelated `moneyprinterturbo` 1.4.5 (2024-06-01, home page yanjlee/MoneyPrinterTurbo) also exists, which matches MPT issue #1643 about a same-name package breaking `pip install` — [PyPI mpt](https://pypi.org/project/mpt/); [PyPI moneyprinterturbo](https://pypi.org/project/moneyprinterturbo/); [issues](https://github.com/harry0703/MoneyPrinterTurbo/issues?q=is%3Aissue).

**Pixelle-Video (AIDC-AI, Apache-2.0)**
- (1) It has a real per-scene storyboard model, defined in `pixelle_video/models/storyboard.py` — [storyboard.py](https://github.com/AIDC-AI/Pixelle-Video/blob/main/pixelle_video/models/storyboard.py).
  - `StoryboardConfig`: `n_storyboard: int = 5`, min/max narration words 5–20, image-prompt words 30–60, and `frame_template = "1080x1920/default.html"`.
  - `StoryboardFrame`: `narration`, `image_prompt`, `audio_path`, `media_type` (image/video), `composed_image_path` ("with subtitles"), `video_segment_path` and `duration` ("from audio or video").
  - LLMs are configured through `pixelle_video/llm_presets.py` (OpenAI-compatible).
- (4) Captions are the per-frame narration text composited by an HTML template ("Step 3: Compose frame with subtitle using HTML template", frame_processor.py:323). Template placeholders in `templates/1080x1920/image_default.html` are `{{title}}`, `{{text}}`, `{{image}}`, `{{author=@Pixelle.AI}}`, `{{brand=Pixelle-Video}}` and `{{describe=…}}`. That gives a persistent title and brand text (hook-like and logo-like text fields), but **sentence/scene-level only, no word timing**. There are no WordBoundary or whisper hits in `pixelle_video/` — [frame_processor.py](https://github.com/AIDC-AI/Pixelle-Video/blob/main/pixelle_video/services/frame_processor.py); [templates](https://github.com/AIDC-AI/Pixelle-Video/tree/main/templates/1080x1920).
- (4) Audio: BGM is mixed with ffmpeg `amix` (`inputs=2, duration='first'`) in services/video.py:677–760. The code comment admits that a fade-out "would need" more work. There is no loudnorm — [video.py](https://github.com/AIDC-AI/Pixelle-Video/blob/main/pixelle_video/services/video.py).
- (2) Images become static clips: `create_video_from_image` uses `ffmpeg.input(image, loop=1, framerate=fps)`. There is **no zoompan/Ken Burns**; the only "zoom" hit is a camera-motion word in the video-generation prompt (prompts/video_generation.py:51). AI video comes from API clients `video_dashscope.py`, `video_kling.py` and `video_seedance.py` — [api_services](https://github.com/AIDC-AI/Pixelle-Video/tree/main/pixelle_video/services/api_services).
- (4) Watermark: every hit is a provider parameter (DashScope/Seedream/Seedance `watermark`). There is no user logo overlay — [repo grep](https://github.com/AIDC-AI/Pixelle-Video).
- (5) Thumbnail: only `ContentMetadata.cover_url` ("Cover/thumbnail image URL", storyboard.py:91), which describes source content. No thumbnail is generated — [storyboard.py](https://github.com/AIDC-AI/Pixelle-Video/blob/main/pixelle_video/models/storyboard.py).
- (8) It has a Streamlit History page (`web/pages/2_📚_History.py`) with a failed-count metric and status icons (lines 97–177), and `models/progress.py` progress events with `extra_info` "e.g., batch progress" — [web/pages](https://github.com/AIDC-AI/Pixelle-Video/tree/main/web/pages).
- (13) Batch: a "Batch topics input" splits a textarea by newline (web/components/content_input.py:125–142). `SimpleBatchManager` "Only supports 'AI generate content' mode… Same config for all videos, only topics differ" (web/utils/batch_manager.py) — [batch_manager.py](https://github.com/AIDC-AI/Pixelle-Video/blob/main/web/utils/batch_manager.py).
- (11) UI locales are only `en_US.json` and `zh_CN.json` (web/i18n/locales/), and there are no `vi-VN` hits in the repo. **Vietnamese = No** (Edge voices might be selectable, but nothing in code references them) — [locales](https://github.com/AIDC-AI/Pixelle-Video/tree/main/web/i18n/locales).
- (12) There is a Windows build script `packaging/windows/build.py` with `templates/start.bat`, plus a FastAPI-style `api/` (routers: content, frame, image, llm, tasks, tts, video) — [packaging/windows](https://github.com/AIDC-AI/Pixelle-Video/tree/main/packaging/windows).
- (6) and (7) have no hits for YouTube upload, TikTok publish, cron or schedule. **N**.

**NarratoAI (linyqh, MIT)**
- (4) It has loudness normalization: `app/services/audio_normalizer.py` (`self.target_lufs = -23.0  # 目标响度 (LUFS)，符合广播标准`, `analyze_audio_lufs()`), used in `generate_video.py:34, 1512` (`AudioNormalizer()`, `calculate_volume_adjustment`). `app/config/audio_config.py:37–39` sets `'target_lufs': -20.0` and `'volume_analysis_method': 'lufs'` — [audio_normalizer.py](https://github.com/linyqh/NarratoAI/blob/main/app/services/audio_normalizer.py); [audio_config.py](https://github.com/linyqh/NarratoAI/blob/main/app/config/audio_config.py).
- (9) JianYing draft export is implemented in `app/services/jianying_draft_builder.py` and `jianying_task.py`, which have unit tests — [jianying_draft_builder.py](https://github.com/linyqh/NarratoAI/blob/main/app/services/jianying_draft_builder.py).
- (11) UI i18n has only `webui/i18n/en.json` and `zh.json`, so Vietnamese is TTS-only (vi-VN voices, per the earlier notes) — [webui/i18n](https://github.com/linyqh/NarratoAI/tree/main/webui/i18n).
- (13) Batch is absent: open issue #274 "【功能建议】支持批量视频生产，预定义工作流…" (opened 2026-07-19) confirms it — [issues](https://github.com/linyqh/NarratoAI/issues?q=is%3Aissue).

**ArcReel (AGPL-3.0, Python backend + React frontend, 4,338 files)**
- (4) BGM loudness: "响度按 EBU R128 积分响度在登记时实测一次" (integrated loudness is measured once when a track is registered), with `TARGET_LOUDNESS_LUFS = -16.0` (lib/bgm/library.py:7–53). It has a burned-subtitles render variant, `SubtitleMode = Literal["burned_subtitles","no_subtitles"]` (lib/final_cut/basis.py:39–64), with an ffmpeg render in `lib/final_cut/ffmpeg_render.py` — [library.py](https://github.com/ArcReel/ArcReel/blob/main/lib/bgm/library.py); [basis.py](https://github.com/ArcReel/ArcReel/blob/main/lib/final_cut/basis.py).
- (5) `lib/infra/thumbnail.py` "视频帧提取（首帧缩略图 / 尾帧）" (first-frame and last-frame extraction) produces UI thumbnails, not publish thumbnails. **N/P** — [thumbnail.py](https://github.com/ArcReel/ArcReel/blob/main/lib/infra/thumbnail.py).
- (9) It has a JianYing draft artifact kind `EPISODE_JIANYING_DRAFT` (lib/artifacts/artifact_manifest.py:82, 2102) and a `lib/jianying_draft/` package. CapCut International is not referenced in Python — [artifact_manifest.py](https://github.com/ArcReel/ArcReel/blob/main/lib/artifacts/artifact_manifest.py).
- (11) It has **Vietnamese UI locales**: `frontend/src/i18n/vi/*.ts` (assets, auth, common, dashboard, errors…) and backend `lib/i18n/vi/` (errors, providers, templates…). The earlier "?" becomes **P** (UI; no vi TTS evidence) — [frontend/src/i18n/vi](https://github.com/ArcReel/ArcReel/tree/main/frontend/src/i18n/vi).
- (3)/(10) Audio backends are `dashscope`, `gemini`, `minimax` and `openai` with a registry (lib/backends/audio_backends/). Text backends include Anthropic, Gemini, Grok, Ark and others (lib/backends/text_backends/) — [lib/backends](https://github.com/ArcReel/ArcReel/tree/main/lib/backends).
- (6) There are no youtube/tiktok/facebook hits in `*.py`. **N**.
- (12) Server mode is `deploy/docker-compose.yml` and `deploy/production/docker-compose.yml`, with no desktop installer — [deploy](https://github.com/ArcReel/ArcReel/tree/main/deploy).

**OpenDirector (seme-org, LGPL-3.0, TypeScript)**
- (4) The renderer is built on FFCreator (`FFScene`, `FFText`). `addWatermark()` draws a **hard-coded "OpenDirector" text** at 4% margin (apps/render/src/renderer.ts:243, 633–646). That is branding, not a user logo. `apps/render/src/effects.ts` registers `mini_zoom` and `ken_burns` effects (effects.test.ts:19–25) — [renderer.ts](https://github.com/seme-org/open-director/blob/main/apps/render/src/renderer.ts); [effects.ts](https://github.com/seme-org/open-director/blob/main/apps/render/src/effects.ts).
- (4) Caption timing: `subtitleTimings` are parsed from Edge TTS (apps/web/src/server/batch/edge-tts.ts:91–96) and passed into the batch pipeline (server/batch/pipeline.ts:62), i.e. TTS word boundaries — [edge-tts.ts](https://github.com/seme-org/open-director/blob/main/apps/web/src/server/batch/edge-tts.ts).
- (1) An agent graph has nodes `director`, `block-planner`, plus prompts for `script`, `storyboard`, `character`, `location`, `art-style`, `voice`, `bgm` and `media` (apps/web/src/server/agent/graph/nodes/) — [nodes](https://github.com/seme-org/open-director/tree/main/apps/web/src/server/agent/graph/nodes).
- (6) "Upload" hits are S3 object storage only (`@aws-sdk/lib-storage`, storage.ts). **N**.
- (11) Locales are only `en.json` and `zh-CN.json`. **N**.

**ShortGPT (RayVentura, MIT; default branch `stable`)**
- (4) The Gradio UI has an "Add watermark" checkbox with a "Watermark (your channel name)" textbox (gui/ui_tab_short_automation.py:49–51), so the watermark is text, not an image logo. Captions use `whisper_timestamped.transcribe_timestamped` (shortGPT/audio/audio_utils.py:73; setup.py `whisper-timestamped`) — [ui_tab_short_automation.py](https://github.com/RayVentura/ShortGPT/blob/stable/gui/ui_tab_short_automation.py); [audio_utils.py](https://github.com/RayVentura/ShortGPT/blob/stable/shortGPT/audio/audio_utils.py).

**MoneyPrinterV2 (FujiwaraChoki, AGPL-3.0)**
- (4) Subtitles **are** implemented in code: `generate_subtitles()` dispatches to local Whisper or AssemblyAI (src/classes/YouTube.py:444–460), and `SubtitlesClip(subtitles_path, generator)` burns them in (YouTube.py:624–626). The Roadmap's "Subtitles for Shorts [ ]" is stale — [YouTube.py](https://github.com/FujiwaraChoki/MoneyPrinterV2/blob/main/src/classes/YouTube.py).
- (7) Scheduling uses the `schedule` library: `schedule.every(1).day.do(job)` and `.at("10:00")` / `.at("16:00")` (src/main.py:1, 236–241), with menu options "Once a day / Twice a day / Thrice a day" (src/constants.py:38–43). A JSON cache of uploaded videos exists (YouTube.py:418–441), but there is no topic-dedup logic — [main.py](https://github.com/FujiwaraChoki/MoneyPrinterV2/blob/main/src/main.py); [constants.py](https://github.com/FujiwaraChoki/MoneyPrinterV2/blob/main/src/constants.py).
- (6) It uses Selenium and Firefox (`selenium_firefox`, `webdriver.firefox`) for browser-automated upload — [src/classes](https://github.com/FujiwaraChoki/MoneyPrinterV2/tree/main/src/classes).

**leamsigc/ShortsGenerator (MIT, Nuxt + Flask)**
- (4) `burn_subtitles_and_hook(..., hook_title: str, ...)`: "Burn word-synced subtitles and hook title into a clip using ffmpeg" (Backend/classes/Clipper.py:342–353). This is the **only hook-title overlay found among the original 12**, and it sits on the clipper path. Transcription uses local faster-whisper (Clipper.py:847–852) — [Clipper.py](https://github.com/leamsigc/ShortsGenerator/blob/main/Backend/classes/Clipper.py).
- (5) `generate_thumbnail()` "Extract a thumbnail frame from a video at `timestamp` fraction" (Clipper.py:472–477), i.e. frame extraction only — [Clipper.py](https://github.com/leamsigc/ShortsGenerator/blob/main/Backend/classes/Clipper.py).
- (6) YouTube upload goes direct through the Data API: `youtube.videos().insert(` (Backend/youtube.py:115), triggered by `automateYoutubeUpload` (Backend/main.py:171–254). Scheduling and other platforms go through **MagicSync** (`MAGICSYNC_BASE_URL`, `MAGICSYNC_API_TOKEN`; Backend/clipper_routes.py:910–995) — [youtube.py](https://github.com/leamsigc/ShortsGenerator/blob/main/Backend/youtube.py); [clipper_routes.py](https://github.com/leamsigc/ShortsGenerator/blob/main/Backend/clipper_routes.py).

**AbdullahNaveed/ai-shorts-generator (MIT)**
- (4) It has **loudness normalization and ducking**: `[m][s1]sidechaincompress=threshold=0.05:ratio=8:attack=20:release=350[duck];[duck][s2]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]`, or `loudnorm=I=-14:TP=-1.5:LRA=11` without music (pipeline/assemble.py:129–133). Ken Burns presets are "zoom/pan expressions over a 2x-prescaled still" (assemble.py:21–36) — [assemble.py](https://github.com/AbdullahNaveed/ai-shorts-generator/blob/main/pipeline/assemble.py).
- (4) Captions: "word-level captions via faster-whisper -> brand ASS subtitles. Karaoke style" (pipeline/captions.py:1–3). Watermark comes from `templates/watermark.html` and the `assets/logo/` folder. The pipeline code has no "hook" hits — [captions.py](https://github.com/AbdullahNaveed/ai-shorts-generator/blob/main/pipeline/captions.py).
- (8) It has a Flask dashboard (`dashboard/app.py`; templates index/create/library/video) and persisted drafts so work can be resumed ("closing the tab never loses work", pipeline/drafts.py) — [drafts.py](https://github.com/AbdullahNaveed/ai-shorts-generator/blob/main/pipeline/drafts.py).

**SaarD00 AutoShorts AI (MIT; branch `Main`)**
- (8) It now has a Flask web app with login: routes `/login`, `/`, `/generate`, `/stop`, `/api/status`, `/videos/<name>`, `/download/<name>` (webapp.py:163–245, last changed 2026-08-13). The earlier "N (CLI)" becomes **P** — [webapp.py](https://github.com/SaarD00/AI-Youtube-Shorts-Generator/blob/Main/webapp.py).
- (6) The YouTube Data API publisher uses `googleapiclient`, `MediaFileUpload` and the narrow scope `youtube.upload` (modules/publisher.py:1–15). It also has `upload_history.json` (upload.py:23–30), `upload_scheduled.py`, `daily_pipeline.py` and `.github/workflows/generate-short.yml` — [publisher.py](https://github.com/SaarD00/AI-Youtube-Shorts-Generator/blob/Main/modules/publisher.py); [upload.py](https://github.com/SaarD00/AI-Youtube-Shorts-Generator/blob/Main/upload.py).

**short-video-factory (YILS-LIN, AGPL-3.0, Electron)**
- (4) "音频处理：使用响度归一化(loudnorm)确保音量均衡" (audio processing uses loudnorm to balance volume), with `loudnorm=I=-16:TP=-1.5:LRA=11` on the voice (electron/ffmpeg/index.ts:179–185). Edge TTS `WordBoundary` interface and `getWordList()` (electron/lib/edge-tts.ts:95–145) feed a subtitle render service (electron/effect-engine/subtitle-render-service.ts) — [ffmpeg/index.ts](https://github.com/YILS-LIN/short-video-factory/blob/main/electron/ffmpeg/index.ts); [edge-tts.ts](https://github.com/YILS-LIN/short-video-factory/blob/main/electron/lib/edge-tts.ts).
- (11) Locales are only `locales/en` and `locales/zh-CN`. **N** — [locales](https://github.com/YILS-LIN/short-video-factory/tree/main/locales).

**Toonflow (HBAI-Ltd/Toonflow-app, MIT, Bun; branch `master`)**
- (11) It ships a Vietnamese UI locale at `packages/i18n/src/locales/vi.json`, and Element Plus `vi.json`, among 20+ languages — [locales](https://github.com/HBAI-Ltd/Toonflow-app/tree/master/packages/i18n/src/locales).
- (12) It has a Windows desktop installer with WebView2 checks (`apps/desktop/installer/checkWebView2.cs`, `checkRunning.cs`) — [apps/desktop](https://github.com/HBAI-Ltd/Toonflow-app/tree/master/apps/desktop).
- (3) Audio and media generation lives in `apps/server/src/routes/ai/media/generate.ts`. The server uses ffmpeg. There are no publish hits; the only "facebook" hits are zstd license lines. **(6) = N** — [server](https://github.com/HBAI-Ltd/Toonflow-app/tree/master/apps/server).

### Inferences
Revised matrix (source-verified where noted, otherwise carried over from the earlier README notes):

| Project | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MoneyPrinterTurbo | P | Y | Y | P (word captions; no loudnorm/logo/hook) | **N** | P (Upload-Post TT/IG/YT; FB mapping only) | **N** | **Y−** (history+progress+errors+diag logs) | N | P | Y | Y | Y (≤100) |
| Pixelle-Video | **Y** (StoryboardFrame) | P (AI images static, AI video API) | Y | P (scene-level text, amix, no loudnorm) | **N** | N | N | P | N | P | **N** | Y | Y (topics per line) |
| NarratoAI | P | N | Y | P (**LUFS normalizer**) | N | N | N | P | P (JianYing) | P | P (TTS only) | Y | **N** (#274) |
| ArcReel | Y | Y | Y | P (BGM −16 LUFS, burned subs) | N (UI thumbs only) | N | U | P | P (JianYing) | Y | **P (vi UI)** | Y (Docker) | P |
| OpenDirector | Y | P | Y | P (Ken Burns, Edge word timings, fixed brand watermark) | N | **N** | U | P | **N** | Y | N | P | Y |
| ShortGPT | P | N | Y | P (whisper-timestamped, text watermark) | U | N | N | P | N | P | Y | P | N |
| MoneyPrinterV2 | P | P | Y | P (**subtitles exist**) | U | P (Selenium) | P (schedule 1–3×/day, no dedup) | N | N | P | U | P | P |
| leamsigc | P | P | Y | P (**hook title + word subs**) | P (frame) | P (YT direct; rest via MagicSync) | P | P | N | P | U | P | U |
| AbdullahNaveed | P | Y | Y | **Y−** (loudnorm −14, ducking, karaoke, logo; no hook) | U | N | P | P | N | U | U | P | Y |
| SaarD00 | P | N | Y | P | U | P (YT API only) | P | **P (webapp)** | N | U | U | P | Y |
| short-video-factory | P | N | Y | P (**loudnorm −16**, WordBoundary subs) | U | N | N | n/a | N | U | **N** | Y | Y |
| Toonflow | Y | Y | U→P | P | U | N | U | P | U | Y | **P (vi UI)** | Y | P (#362 batch complaint) |

- Loudness normalization is not a differentiator. At least 4 of the 12 originals implement it, and so do 4 of the missed projects (below). ai-content-agent's real differentiators in (4) narrow down to a **hook overlay combined with a logo on a topic-to-Shorts pipeline**. Even that has been matched by purffle-shorts (missed project), and leamsigc has it on its clipper path.
- MPT's (8) is stronger than the "P" in the earlier report. Its (5) and (7) are confirmed absent in code, not just undocumented.
- Pixelle's (1) deserves **Y** (explicit storyboard frames), but its (11) should go from "P (inferred)" to **N**.

### Gaps
- ArcReel caption timing (Whisper vs TTS alignment) was not resolved. No `whisper`/`word_timestamps` hits were found in `lib/`, and the subtitle source in `lib/edit_timeline/sources.py` was not read in depth.
- ArcReel and Toonflow topic rotation/dedup (7) were not checked in depth. These are drama studios, so (7) is likely N.
- Whether MPT's Upload-Post call accepts `"facebook"` in `upload_post_platforms` (and posts to a Page) was not tested. Only the caption mapping is in code.
- Toonflow TTS providers were not enumerated.

## Q2. Activity and maturity signals (dated)

### Takeaway
Only five of the twelve original targets are clearly active in the last 30 days: MPT, ArcReel, Toonflow, short-video-factory and NarratoAI (lightly). MPT (151 commits in 30 days, 6 releases between 2026-08-12 and 2026-10-21) and ArcReel (491 commits in 30 days, weekly minor releases) are the two high-velocity projects.

Several earlier "active" assumptions are wrong:
- **Pixelle-Video has had no commits since 2026-06-14** and no tag since v0.1.15 (2026-01-27).
- **OpenDirector stopped on 2026-05-29** after a 17-day burst of 33 commits.
- **ShortGPT's last commit is 2025-02-10.**
- **AbdullahNaveed is a single commit from 2026-06-24.**

### Cited Findings
Git metrics, computed 2026-11-04/05 from clones of each repo (source: the repo's commit history on GitHub, e.g. [MPT commits](https://github.com/harry0703/MoneyPrinterTurbo/commits/main)):

| Repo (branch) | Total commits | First → last commit | Commits 30d / 90d / 365d | Distinct authors 365d | Tags: latest (count) |
|---|---|---|---|---|---|
| [harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo/commits/main) (main) | 1,233 | 2024-03-11 → **2026-11-03** | 151 / 545 / 761 | 142 | v1.3.9 2026-10-21; v1.3.8 10-03; v1.3.7 09-13; v1.3.6 09-02; v1.3.5 08-22; v1.3.4 08-12 (22) |
| [ArcReel/ArcReel](https://github.com/ArcReel/ArcReel/commits/main) (main) | 2,401 | 2026-02-06 → **2026-11-04** | 491 / 1,395 / 2,401 | 27 | v0.35.0 2026-11-01; v0.34.0 10-24; v0.33.0 10-08; v0.32.0 10-02; v0.31.0 09-23 (65) |
| [HBAI-Ltd/Toonflow-app](https://github.com/HBAI-Ltd/Toonflow-app/commits/master) (master) | 90 | 2026-09-21 → **2026-11-02** | 44 / 90 / 90 | 7 | v2.0.9 2026-10-31; v2.0.8 10-27; v2.0.7 10-21; v2.0.6 10-13; v2.0.5 10-09; v2.0.4 10-05 (31) |
| [YILS-LIN/short-video-factory](https://github.com/YILS-LIN/short-video-factory/commits/main) (main) | 151 | 2025-07-10 → **2026-11-02** | 16 / 34 / 72 | 2 | v1.3.0 2026-10-16; v1.2.2 04-07; v1.2.1 03-12; v1.2.0 01-22 (29) |
| [linyqh/NarratoAI](https://github.com/linyqh/NarratoAI/commits/main) (main) | 440 | 2024-08-12 → 2026-10-25 | 3 / 9 / 216 | 18 | v0.8.7 2026-07-18; v0.8.6 07-16; v0.8.5 07-13; v0.8.4 07-02 (34) |
| [SaarD00/AI-Youtube-Shorts-Generator](https://github.com/SaarD00/AI-Youtube-Shorts-Generator/commits/Main) (Main) | 19 | 2025-12-24 → 2026-10-13 | 1 / 11 / 19 | 7 | none |
| [leamsigc/ShortsGenerator](https://github.com/leamsigc/ShortsGenerator/commits/main) (main) | 25 | 2024-02-24 → 2026-10-11 | 1 / 7 / 13 | 1 | none |
| [FujiwaraChoki/MoneyPrinterV2](https://github.com/FujiwaraChoki/MoneyPrinterV2/commits/main) (main) | 116 | 2024-02-12 → 2026-09-16 | 0 / 1 / 20 | 4 | none |
| [AIDC-AI/Pixelle-Video](https://github.com/AIDC-AI/Pixelle-Video/commits/main) (main) | 377 | 2025-11-07 → **2026-06-14** | 0 / 0 / 377 | 22 | v0.1.15 2026-01-27 (14) |
| [AbdullahNaveed/ai-shorts-generator](https://github.com/AbdullahNaveed/ai-shorts-generator/commits/main) (main) | 1 | 2026-06-24 (single) | 0 / 0 / 1 | 1 | none |
| [seme-org/open-director](https://github.com/seme-org/open-director/commits/main) (main) | 33 | 2026-05-12 → **2026-05-29** | 0 / 0 / 33 | 1 | none |
| [RayVentura/ShortGPT](https://github.com/RayVentura/ShortGPT/commits/stable) (stable) | 298 | 2023-07-07 → **2025-02-10** | 0 / 0 / 0 | 0 | v0.3.0 2025-02-10 (6) |

Notes on the table:
- MPT's latest commit (2026-11-03) is "fix(video): stop keys typed into the console window from cutting the video short or stalling the clip join".
- Toonflow's git history starts on 2026-09-21 even though v2.x tags exist. This suggests the repository history was re-created or squashed (it matches the earlier note that the license changed several times).

Issue trackers, read 2026-11-05 (the "open" number is the repo-nav badge; "total" is the `is:issue` search result count; the two are not always consistent):

| Repo | Open | Total | Recurring complaints (from page 1 of issues) | Source |
|---|---|---|---|---|
| MoneyPrinterTurbo | 10 | 837 | TTS failures (#1762, #1711, #1692, #1647); subtitle timing (#1761 "Whisper sentence subtitles get zero timestamps"); concurrency and cache (#1741 "Redis max_concurrent_tasks is enforced per process", #1740 "Corrupt cached videos are reused without validation"); packaging (#1643 impostor PyPI package, #1583 uv cache lock, #1695 AppImage request). Most page-1 issues close within days | [issues](https://github.com/harry0703/MoneyPrinterTurbo/issues?q=is%3Aissue) |
| ArcReel | 62 | 1,781 | Model/provider catalog and config churn (#3673 "new built-in provider models require code changes"); task resume and retry reliability (#3677, #3676, #3668); provider capability mismatches (#3694, #3675); unclear 500 errors with missing config (#3663). Many issues are machine-generated "[Spec #…]" work items | [issues](https://github.com/ArcReel/ArcReel/issues?q=is%3Aissue) |
| Pixelle-Video | 151 | 193 | Digital-human bugs (#229, #240, #262); API, Ollama and connection-test failures (#239, #255, #251); "没有最新版Windows一键整合包" (no up-to-date Windows one-click package, #257, opened 2026-09-07, still open); many spam or placeholder titles; few closures | [issues](https://github.com/AIDC-AI/Pixelle-Video/issues?q=is%3Aissue) |
| ShortGPT | 74 | 124 | Install and Docker failures (#147, #149, #151); pipeline crashes at step 11 or 12 (#140, #154); Whisper errors (#145). Newest substantive bug is #166 from 2025-09-07 | [issues](https://github.com/RayVentura/ShortGPT/issues?q=is%3Aissue) |
| MoneyPrinterV2 | 49 | 140 | A batch of code-audit issues filed 2026-03-31: missing error handling (#231, #232), "Silent cron failure when account UUID is missing" (#229), Selenium browser leaks (#225, #227), "YouTube Shorts loops on 'Generated Title is too long' on Windows" (#265), 429 on image generation (#266) | [issues](https://github.com/FujiwaraChoki/MoneyPrinterV2/issues?q=is%3Aissue) |
| short-video-factory | 18 | 70 | EdgeTTS and network TTS failures (#76, #80); "渲染失败/合成失败" (render or synthesis failed; #69, #62, #65, #51); a missing subtitle file breaks synthesis (#54); BGM silences the second half (#53); requests for local or custom TTS (#81, #60, #57) | [issues](https://github.com/YILS-LIN/short-video-factory/issues?q=is%3Aissue) |
| NarratoAI | 3 | 194 | LLM flexibility and local models (#241, #243, #273), a hard-coded temperature (#287); Doubao and IndexTTS2 errors (#267, #268); a batch-production request (#274) | [issues](https://github.com/linyqh/NarratoAI/issues?q=is%3Aissue) |
| Toonflow | 2 | 237 | **Windows installer flagged as malware** (#373, #368 "Windows 2.0.8 deleted by the system as a virus"); launch failures on macOS, Windows and Android (#381, #376, #377); custom-provider issues (#372); "Batch running doesn't seem to really work" (#362) | [issues](https://github.com/HBAI-Ltd/Toonflow-app/issues?q=is%3Aissue) |

### Inferences
- Maturity ranking by evidence: MPT (high velocity, very low open-issue backlog, regular releases) > ArcReel (highest velocity but heavy churn) > Toonflow (weekly patch releases, but antivirus and packaging pain) > short-video-factory > NarratoAI (slowing since July) > all the rest (dormant or one-person).
- Pixelle-Video should be reclassified from "active" to **stalled since June 2026**: 151 open issues, no commits in 4.5 months, and an outdated Windows package.
- Recurring complaint classes across trackers are TTS-service fragility (Edge, Azure, Doubao), subtitle timing, provider-config churn, Windows packaging and antivirus, and silent or unhandled failures. These match ai-content-agent's planned investments (error-log dashboard, Windows packaging). The Toonflow antivirus issue argues for code-signing any Windows build.

### Gaps
- No issue counts were taken for OpenDirector, leamsigc, AbdullahNaveed or SaarD00. Their trackers are tiny relative to the others and were not prioritized.
- Release dates come from git tag creator dates. GitHub Release objects and their notes were not cross-checked for every repo.

## Q3. Missed projects with meaningful overlap (≥4 of 13)

### Takeaway
The earlier survey missed **PurffleShorts** (Chamanrajragu/purffle-shorts), which the source shows to be the closest functional match to ai-content-agent found so far. It is MIT-licensed and has:
- (1) storyboard: LLM scripts graded and rewritten by a second AI pass;
- (4) edit bundle: word-synced captions, hook title, watermark, loudness measurement;
- (5) thumbnail: candidate frame scoring;
- (6) publishing: YouTube Data API direct, TikTok and Facebook via Upload-Post;
- (7) rotation and dedup: weighted topic sources with a `topics_used` table;
- (8) a web Studio with a queue and progress;
- (11) Vietnamese voice support;
- (13) autopilot batch;
- an MCP server.

It is tiny (61 stars), and its multi-platform publishing is "not yet tested against live TikTok or Instagram accounts". A second missed project, **video-autopilot**, publishes daily to all four platforms (YT, TikTok, IG Reels, FB Reels), but through the paid Ayrshare or Upload-Post aggregators. For Vietnamese, **Cuongyd196/auto-video-gen** (196 stars) is an open-source Vietnamese-first 9:16 generator, which contradicts the earlier claim that no Vietnamese Shorts generator exists. It has no publishing.

### Cited Findings

**PurffleShorts — [Chamanrajragu/purffle-shorts](https://github.com/Chamanrajragu/purffle-shorts)**
- Basics: 61 stars on the topic page (2026-11-05), MIT, Python 3.10–3.13. 24 commits, 2026-06-13 → 2026-11-03, 19 of them in the last 90 days — [topic page](https://github.com/topics/shorts-generator?o=desc&s=stars); [LICENSE](https://github.com/Chamanrajragu/purffle-shorts/blob/main/LICENSE).
- (1) The README says the chosen LLM (GPT, Claude, Gemini, Ollama, DeepSeek, Grok, Mistral or OpenAI-compatible) writes the script, and "a second AI pass grades and rewrites" it. The script writer marks key words per scene through a "strict-schema field" (CHANGELOG) — [README](https://github.com/Chamanrajragu/purffle-shorts/blob/main/README.md); [CHANGELOG](https://github.com/Chamanrajragu/purffle-shorts/blob/main/CHANGELOG.md).
- (7) Topic sources are configured as `TOPIC_SOURCES=niche:4,trending:1,wikipedia:1`, with `file` ("each used once") and `rss` ("newest unused item") among them (purffle_shorts/topics.py:1–13). `history.py` keeps "what … were used (so nothing repeats), today's upload count (YouTube quota)" in SQLite tables `media_used` and `topics_used` (history.py:2, 26–27). There is a test `test_keyed_pipeline_uploads_and_dedupes` — [topics.py](https://github.com/Chamanrajragu/purffle-shorts/blob/main/purffle_shorts/topics.py); [history.py](https://github.com/Chamanrajragu/purffle-shorts/blob/main/purffle_shorts/history.py).
- (6) YouTube: "YouTube Data API v3: OAuth (token.json), resumable uploads with retries, scheduled publishing, AI-content disclosure, playlists and quota awareness" (youtube.py:1–2), plus `--publish-times` "schedule slots, e.g. 09:00,14:00,19:00" (cli.py:153) — [youtube.py](https://github.com/Chamanrajragu/purffle-shorts/blob/main/purffle_shorts/youtube.py).
- (6) Other platforms: `PLATFORMS = ("youtube","tiktok","instagram","facebook","threads","x","linkedin","bluesky","pinterest")` (crosspost.py:35). "TikTok and Facebook, Threads, X, LinkedIn, Bluesky and Pinterest go through the Upload-Post relay… TikTok's own API only lets audited apps publish public videos." Instagram can use the official API. "Tested against recorded API responses, not yet against live TikTok or Instagram accounts" — [crosspost.py](https://github.com/Chamanrajragu/purffle-shorts/blob/main/purffle_shorts/crosspost.py); [CHANGELOG](https://github.com/Chamanrajragu/purffle-shorts/blob/main/CHANGELOG.md).
- (4) overlays.py is "Everything drawn on top of the footage: word-synced animated captions, the hook title, the watermark, the end call-to-action…", with `hook_png()` (line 437) and `watermark_png()` (line 453). Loudness is measured via `loudnorm=print_format=json` ("Integrated loudness (LUFS)", ffmpeg.py:146–161). Generated SFX sit "11 dB under the voice" (CHANGELOG) — [overlays.py](https://github.com/Chamanrajragu/purffle-shorts/blob/main/purffle_shorts/overlays.py); [ffmpeg.py](https://github.com/Chamanrajragu/purffle-shorts/blob/main/purffle_shorts/ffmpeg.py).
- (5) "0..1 for a thumbnail candidate: sharp (text and detail fully drawn, not mid-fade…)" (render.py:432) is a scored frame pick, not a designed thumbnail — [render.py](https://github.com/Chamanrajragu/purffle-shorts/blob/main/purffle_shorts/render.py).
- (8), (10) and (13):
  - A web Studio (`purffle_shorts/web/index.html`, `app.js`) with Create, Queue and Library pages and an "edit-timeline progress display on Create and in the Queue" (CHANGELOG).
  - `mcp_server.py` exposes it to Claude Desktop and Cursor.
  - `studio.autopilot(count=…)` plus `--batch` and `--delay` (cli.py:208–219).
  - It runs on "macOS, Windows, Linux, in Docker or in Google Colab" (README:63).
  - Sources: [cli.py](https://github.com/Chamanrajragu/purffle-shorts/blob/main/purffle_shorts/cli.py); [README](https://github.com/Chamanrajragu/purffle-shorts/blob/main/README.md).
- (11) Vietnamese is in the language table (`"vi": "Vietnamese"`, script.py:26) and the default voice map (`"vi": "vi-VN-NamMinhNeural"`, tts.py:45) — [tts.py](https://github.com/Chamanrajragu/purffle-shorts/blob/main/purffle_shorts/tts.py).
- (9) CapCut and JianYing: no hits. **N**.
- The README carries its own competitor matrix, "Compiled on 29 September 2026", and concedes that "MoneyPrinterTurbo has a one-click Windows package" — [README](https://github.com/Chamanrajragu/purffle-shorts/blob/main/README.md).
- Estimated score: about 9.5–10/13 (1 Y, 2 P, 3 Y, 4 Y−, 5 P, 6 P (YT direct, TT and FB via a SaaS relay), 7 Y, 8 Y, 9 N, 10 P/Y, 11 P (voice and script language; UI not checked), 12 P, 13 Y). This is inference from the code above.

**Video Autopilot — [aredwan-xyz/video-autopilot](https://github.com/aredwan-xyz/video-autopilot)**
- Basics: 11 stars (topic page, 2026-11-05), MIT. 79 commits, 2026-06-26 → 2026-11-01 — [topic page](https://github.com/topics/faceless-video?o=desc&s=updated).
- The README says it "generates and posts 1–3 faceless AI videos every day to YouTube Shorts, Instagram Reels, Facebook Reels, and TikTok". Its pipeline: "trend/idea research → script → AI voiceover → visuals/B-roll → word-by-word captions → 9:16 video assembly → thumbnail → SEO metadata → multi-platform publish → analytics feedback loop" — [README](https://github.com/aredwan-xyz/video-autopilot/blob/main/README.md).
- Publishing runs through `AYRSHARE_API_KEY` ("Paid (~$29/mo)", "Auto-publish to all 4 platforms"), with `UPLOAD_POST_API_KEY` as the alternative (README:133–134; .env.example:27). A daily GitHub Actions `cron: "0 9 * * *"` runs it (.github/workflows/daily.yml). Assembly uses `loudnorm=I=-14:TP=-1.0:LRA=11` (src/assemble.py:91–98). `src/metadata.py` is "Stage 7 — SEO titles, description, hashtags, pinned comment, thumbnail text" — [assemble.py](https://github.com/aredwan-xyz/video-autopilot/blob/main/src/assemble.py); [metadata.py](https://github.com/aredwan-xyz/video-autopilot/blob/main/src/metadata.py).
- Its dashboard (`webapp/server.py`) has routes `/api/channels`, `/api/generate`, `/api/jobs`, `/api/jobs/{jid}`, `/api/library` and `/api/thumbnail/{rel}`. It also has `config/channels.yaml` (multi-channel), `output/history.json` and `docs/COMPLIANCE.md` — [server.py](https://github.com/aredwan-xyz/video-autopilot/blob/main/webapp/server.py).
- Topic dedup was not verified. `src/ideation.py` picks `ideas[0]` "ranked best-first by the prompt".

**OpenShorts (Chinese) — [jnMetaCode/openshorts](https://github.com/jnMetaCode/openshorts)**
- Basics: 59 stars (topic page, 2026-11-05), MIT, JavaScript. 194 commits, 2026-07-28 → 2026-09-25 — [topic page](https://github.com/topics/faceless-video?o=desc&s=updated).
- "Copy in, video out. A local-first, open-source short-video production line: give it a topic and it writes the script, finds the footage, voices it, burns in subtitles, and hands you a finished video plus publish copy". Each shot chooses a stock clip or a photo, scored by a vision model. It has ComfyUI and imagegen adapters and an Electron desktop build (`desktop/electron-builder.config.cjs`). Audio scripts apply `loudnorm=I=-16:LRA=7:TP=-1.5` — [README.en.md](https://github.com/jnMetaCode/openshorts/blob/main/README.en.md).
- It has no publishing code. It is distinct from the "OpenShorts" long-video clipper on Show HN (2026-03-08) — [hnshowcase](https://www.hnshowcase.com/post/47300951/open-source-ai-saas-to-turn-long-videos-into-viral-shorts).
- Estimated overlap is about 5–6/13 (1, 2, 3, 4, 12, partly 13).

**Otopilot — [wj-sidiss/otopilot](https://github.com/wj-sidiss/otopilot)**
- Basics: 194 stars (topic page, 2026-11-05), MIT, Node 22. Turkish-first with 15 UI languages. 36 commits, 2026-10-16 → 2026-11-04 — [youtube-automation topic](https://github.com/topics/youtube-automation?o=desc&s=updated).
- The README says: "turns a topic into a finished video: script → free stock images / museum art (CC0) / stock video → voice-over → edit → MP4 + subtitles + thumbnail + a YouTube publishing pack". The panel runs on `localhost:4173` (`node panel.js`, `PANEL.bat`), and the repo is designed to be handed to Claude Code or Codex (AGENTS.md) — [README](https://github.com/wj-sidiss/otopilot/blob/main/README.md).
- Its thumbnail generator `kapak-yap.js` ("KAPAK (thumbnail) URETICI — en iyi gorsel + buyuk, konturlu baslik", i.e. best image plus big outlined title) is a **designed thumbnail**, rarer than frame picks. It uses `loudnorm=I=-16` (lib/render-muzik.js:162) and `loudnorm=I=-15` (geri-sayim.js:102) — [kapak-yap.js](https://github.com/wj-sidiss/otopilot/blob/main/kapak-yap.js).
- No API upload code was found (no `videos.insert`/TikTok/Graph hits). It produces a "publishing pack" only.
- Estimated overlap is about 5–6/13.

**Gemini YouTube Automation — [ChaitanyaEswarRajeshJakki/gemini-youtube-automation](https://github.com/ChaitanyaEswarRajeshJakki/gemini-youtube-automation)**
- Basics: 373 stars (topic page, 2026-11-05). **No LICENSE file** in the repo. 425 commits, 2025-06-25 → 2026-11-04. Recent commits are mostly `github-actions[bot]` "Update content plan and demo GIF after daily video production", which is proof that it runs unattended daily — [youtube-automation topic](https://github.com/topics/youtube-automation?o=desc&s=updated); [commits](https://github.com/ChaitanyaEswarRajeshJakki/gemini-youtube-automation/commits/main).
- A daily `cron: '0 7 * * *'` runs it. `content_plan.json` holds lessons with `status: complete` and `youtube_id`, which acts as topic rotation and dedup by plan status. Voice is gTTS. Upload uses `youtube.videos().insert(` and `youtube.thumbnails().set(` (src/uploader.py:96, 116), so it **uploads custom thumbnails**, and `src/generator.py` makes them — [uploader.py](https://github.com/ChaitanyaEswarRajeshJakki/gemini-youtube-automation/blob/main/src/uploader.py).
- It targets education lessons plus shorts, on YouTube only.
- Estimated overlap is about 5/13 (1 P, 3 Y, 5 Y, 6 P, 7 P/Y, 13 P). Its license is unknown, so treat it as not reusable.

**Auto Video Gen (Vietnamese) — [Cuongyd196/auto-video-gen](https://github.com/Cuongyd196/auto-video-gen)**
- Basics: 196 stars (topic page, 2026-11-05), MIT, TypeScript. 11 commits, 2026-07-13 → 2026-09-28 — [shorts-generator topic](https://github.com/topics/shorts-generator?o=desc&s=stars).
- The README says "Biến URL bài báo & Repo GitHub thành Video ngắn 9:16 chuyên nghiệp… 0đ Voice (Edge TTS)… Sẵn sàng đăng TikTok, Reels, Shorts" (turn article URLs and GitHub repos into professional 9:16 short videos, free Edge TTS voice, ready for TikTok/Reels/Shorts). package.json describes it as "Auto-generate Vietnamese 9:16 short news videos from URL/txt — Claude Code skill + HyperFrames + LucyLab/ElevenLabs TTS" — [README](https://github.com/Cuongyd196/auto-video-gen/blob/main/README.md); [package.json](https://github.com/Cuongyd196/auto-video-gen/blob/main/package.json).
- TTS clients are Edge (`vi-VN-HoaiMyNeural` / `vi-VN-NamMinhNeural` in .env.example), **LucyLab** and **Vbee** (Vietnamese TTS vendors) and ElevenLabs (src/tts/).
- Its CapCut use is a hand-off, not a draft: the skill outputs "video.mp4 + voice.mp3 + script.txt cho CapCut" (`script.txt — for CapCut auto-caption`; .claude/skills/create-news-video/SKILL.md) — [SKILL.md](https://github.com/Cuongyd196/auto-video-gen/blob/main/.claude/skills/create-news-video/SKILL.md).
- It has no publishing code.
- Estimated overlap is about 4–5/13: (1) P, (2) P (HTML/CSS motion visuals and fetched images), (3) Y, (4) P, (11) **Y**, (12) P. It is not a full factory, but it is the first open-source Vietnamese-first short-video generator found.

**Lower-overlap or unverified candidates**
- Lower overlap, verified by clone or keyword scan:
  - [sw-aka/Short-Video-Creator](https://github.com/sw-aka/Short-Video-Creator): 186 stars, CC BY-NC-SA 4.0, last commit 2026-08-02, captions plus background video.
  - [Dark2C/Viral-Faceless-Shorts-Generator](https://github.com/Dark2C/Viral-Faceless-Shorts-Generator): 119 stars, no LICENSE file, last commit 2026-05-10.
  - In both, keyword scans found essentially no publishing, scheduling, thumbnail or loudness code. Overlap is below 4.
- Unverified topic-page entries, dated 2026-11-01 to 05, star counts from the topic pages:
  - [jashaidaslamhfd/Mr-Nextep](https://github.com/topics/faceless-video?o=desc&s=updated) (2 stars, "Autonomous AI YouTube Shorts production system… CI/CD");
  - aituberapp/ai-video-mcp (7 stars, hosted MCP for creating and publishing);
  - Negmus/narva-mcp (0 stars);
  - thunderifang/rpocket-team-tube-assistant (script, voice, stock, edit, thumbnails, upload via Telegram);
  - jasveerai88/creator-dedupe (0 stars, "checks new video ideas against past uploads to flag duplicate topics"), which shows topic dedup emerging as a standalone tool;
  - kaomei/stickman-video-director (4.3k stars, script-to-stickman video with voice and captions; generation only);
  - leminhnhutphpwp/hyperframes-film-studio (0 stars, AI puppets, TTS, YouTube publishing).
  - Source for all: [faceless-video topic](https://github.com/topics/faceless-video?o=desc&s=updated); [youtube-automation topic](https://github.com/topics/youtube-automation?o=desc&s=updated).
- [jutsuhq/content-factory](https://github.com/jutsuhq/content-factory) (search snippet: "Open-source AI faceless video generator… MCP server for Claude", MIT) **still returns HTTP 404** on 2026-11-05. It is unverifiable.
- Show HN in 2026 surfaced only the OpenShorts long-video clipper (2026-03-08, MIT, docker compose plus Gemini) — [hnshowcase](https://www.hnshowcase.com/post/47300951/open-source-ai-saas-to-turn-long-videos-into-viral-shorts). It is a clipper, not a topic-to-Shorts generator.

### Inferences
- The competitive picture changes. ai-content-agent's claimed rare features are each matched by at least one small 2026 project:
  - (5) thumbnail: Otopilot's designed thumbnails and Gemini-YT-Automation's `thumbnails().set`;
  - (6) four-platform publishing: video-autopilot and PurffleShorts, via SaaS relays;
  - (7) topic dedup: PurffleShorts `topics_used`, Gemini-YT-Automation plan status, creator-dedupe;
  - (11) Vietnamese: auto-video-gen.
- No single project combines all of them with **direct (non-SaaS) TikTok and Facebook Page APIs** and **CapCut International draft export**. Those two remain the genuinely unmatched features, along with full Vietnamese end-to-end delivery (script, voice, captions and UI) together with publishing.
- PurffleShorts should be added to the ranking as a top-tier direct competitor despite its 61 stars. It is effectively a Western-ecosystem, MIT-licensed counterpart of ai-content-agent's design (topic sources with dedup, YT scheduling, Upload-Post relay, Studio UI, MCP). Its relay choice for TikTok confirms the audit barrier noted in the earlier report.
- A clear pattern: new 2026 entrants use SaaS relays (Upload-Post, Ayrshare, MagicSync) for TikTok and Facebook rather than native APIs, because of TikTok's audit rule. A tested native Facebook Reels and TikTok publisher would therefore still differentiate ai-content-agent, but only once it is verified on live accounts.
- The 2026 wave of small, MIT-licensed, agent-built repos (Claude Code or Codex AGENTS.md, CLAUDE.md, MCP servers) is large and fast-moving. Topic pages show dozens updated in the first week of November 2026. Star counts in that wave are not a reliable signal of capability.

### Gaps
- Hugging Face Spaces and Gitee could not be searched because both hosts are outside the session's allowed network domains (DNS failure). They need to be allowed in the session network settings.
- Awesome lists (awesome-ai-video, awesome-video-generation) and the PyPI full-text search were not covered. The PyPI search page did not render, and only known package names were looked up via the JSON API: `mpt` 1.3.9, `moneyprinterturbo` 1.4.5 (unofficial, 2024), `shortgpt` 0.1.31 (2023-08-06); `purffle-shorts` and `pixelle-video` are not on PyPI.
- Reddit (r/SideProject, r/youtubeautomation) 2025–2026 mentions were not searched in this pass.
- GitHub topic pages show only the first 20 entries per topic, so entries after "Load more" (e.g. 79 more under faceless-video and 238 more under youtube-automation) were not reviewed. The topics text-to-video, ai-video-generator, video-automation and auto-video were not fetched.
- Star counts for the missed projects come from topic-page listings on 2026-11-05, not from repo pages, and could not be cross-checked via the API.
