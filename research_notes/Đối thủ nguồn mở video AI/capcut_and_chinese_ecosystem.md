# CapCut / JianYing (剪映) draft automation and the Chinese AI short-video automation ecosystem (snapshot: 2026-11-04)

Method note: Star counts, licenses and last-push dates come from the GitHub search API, queried 2026-11-04 (`gh search repos`). Feature claims come from each project's README, fetched raw from GitHub on the same day. "License not detected" means GitHub's license detector returned none. That is flagged as an unknown or custom license, not as "no license". A feature is marked Unknown when the README did not mention it. Unknown does not mean the feature is absent.

Feature numbering used in all mappings (our project "ai-content-agent"):
(1) LLM scene-by-scene storyboard; (2) per-scene AI visuals (AI images + Ken Burns, or AI video clips); (3) AI voice-over TTS; (4) automatic FFmpeg editing (synced captions, hook text, music, logo, loudness, 9:16); (5) auto thumbnail; (6) auto-publish to YouTube Shorts / TikTok / Facebook Page; (7) scheduling/cron with topic rotation + dedup; (8) web dashboard with live progress, history, error log; (9) CapCut desktop draft export; (10) pluggable provider/publisher architecture; (11) Vietnamese content support; (12) Windows desktop app and/or server/self-host mode; (13) batch/mass production: many videos or drafts generated unattended from a list of topics or scripts.

---

## Q1. Which open-source tools generate or edit CapCut/JianYing drafts programmatically, and what can each do?

### Takeaway
The core library family is GuanYixuan's pyJianYingDraft (4,807★, Apache-2.0) and its CapCut sibling pyCapCut (733★; GitHub detects no license, so treat it as unknown). Our project uses pyCapCut. Most other tools wrap or copy that code. They fall into three groups:
- HTTP/MCP servers: VectCutAPI (formerly CapCutAPI, 2,356★) and capcut-mate (2,094★).
- A zero-dependency Node CLI: capcut-cli (1,106★, MIT), which has the most careful version and encryption engineering.
- A long tail of small MCP servers and agent skills.

All of them write drafts that a person still opens in the desktop app. Local, unattended MP4 export works only on old JianYing (6.x and below, via Windows UI automation). The alternatives are a closed or paid cloud renderer, or duo-video's AutoJY.

### Cited Findings

**pyJianYingDraft (GuanYixuan)**: https://github.com/GuanYixuan/pyJianYingDraft
- 4,807★, Apache-2.0, last push 2026-10-14. Described as a "Python剪映草稿生成及导出工具" for fully automated editing and remix pipelines. Its README says the CapCut version is developed separately in pyCapCut. [README](https://github.com/GuanYixuan/pyJianYingDraft)
- Feature table, listing support on 5.9 and on newer JianYing (10.8). Supported: local video/image/audio with trimming and speed; keyframes (video, sticker, text); masks; chroma key; blend modes; background fill; stickers; audio fades and volume; scene-sound and voice-changer effects; multi-track; clip animations, effects and filters; standalone effect and filter tracks; transitions; text styles, stroke, background and shadow; bubble and "花字" effects; auto line wrap; **`.srt` subtitle import**. [README](https://github.com/GuanYixuan/pyJianYingDraft)
- Template mode can load an existing draft, replace media by name or by segment, replace text, import tracks, and extract sticker/bubble resource_ids. On new JianYing, `draft_content.json` "往往不是可直接读取的明文 JSON", so template loading needs a `DraftFolder(..., fallback_loader=...)` (🟡 on 10.8). [README](https://github.com/GuanYixuan/pyJianYingDraft)
- Batch export through the `JianyingController` class uses the `uiautomation` library, so it runs on Windows only. It is tested on JianYing 5.9 and 6.8. JianYing 7+ hides the controls, so export is ❌ on 7 and later. The exporter brings the JianYing window to the front and moves the cursor, and the README recommends running it at idle times or overnight. Users without VIP who use VIP features can hit an infinite loop. The resolution and frame rate of the export can be set. [README](https://github.com/GuanYixuan/pyJianYingDraft)
- Draft generation works on Linux and macOS, but "生成的草稿仍然需要在Windows版剪映下导出". Python 3.8 or 3.11 is recommended. `uiautomation` has dependency problems on Python 3.13. [README](https://github.com/GuanYixuan/pyJianYingDraft)

**pyCapCut / `pycapcut` (GuanYixuan)**: https://github.com/GuanYixuan/pyCapCut
- 733★, last push 2026-10-16. **GitHub detects no license.** The README grep found no license statement, so the license is unknown and needs checking before redistribution. [GitHub search](https://github.com/GuanYixuan/pyCapCut)
- Installed with `pip install pycapcut`. It shares its source with pyJianYingDraft and targets CapCut drafts. "生成后请在 CapCut 中打开草稿，并通过应用手动导出视频。目前CapCut版暂不支持自动导出" (the CapCut version has no auto-export). [README](https://github.com/GuanYixuan/pyCapCut)
- Its feature table lists a verified CapCut version for each feature: media and timing, track layering, main-track magnet and text style at **8.2.0**; masks, chroma key, blend modes, fonts, 花字 and voice effects at **9.5.0.4050**. Many features, including keyframes, transitions, filters and SRT import, show "—" (version not recorded). [README](https://github.com/GuanYixuan/pyCapCut)
- The README warns about an upcoming **0.1.0 breaking change**: `add_track` will be removed in favour of `append_track(s)`/`insert_track(s)` with `TrackSpec`/`TrackRef`, and users may pin the old version. [README](https://github.com/GuanYixuan/pyCapCut)
- Installs on Windows, Linux and macOS. Drafts must be opened and exported manually in **Windows CapCut**. After a draft is generated, you may need to enter and leave an existing draft, or restart CapCut, before the list refreshes. [README](https://github.com/GuanYixuan/pyCapCut)

**aoguai/pyJianYingDraft (self-maintained fork)**: https://github.com/aoguai/pyJianYingDraft
- 27★, Apache-2.0, last push 2026-10-14. It adds encrypted-draft read/write, automatic draft-folder registration, the cloud music library, beauty filters, per-character rich text, local fonts and extra voices. [GitHub search](https://github.com/aoguai/pyJianYingDraft)
- Encryption is handled by a reversible `content_codec` that calls the **local JianYing `videoeditor.dll`**, which the fork does not redistribute. It needs 64-bit Windows Python and was verified on JianYing **10.3.0–10.6.5**. The support is ported from [wenshui330/jy-draftc](https://github.com/wenshui330/jy-draftc). [README](https://github.com/aoguai/pyJianYingDraft)
- "私有草稿注册": given the `JianyingPro User Data` path, it registers new drafts in JianYing's root metadata and its logical folders. [README](https://github.com/aoguai/pyJianYingDraft)

**VectCutAPI (sun-guannan; formerly "CapCutAPI")**: https://github.com/sun-guannan/VectCutAPI
- 2,356★, Apache-2.0, created 2025-07-11, last push 2026-10-24. The description reads "Open Cut API". Searching for `repo:sun-guannan/CapCutAPI` returned nothing. The MCP config key is still `capcut-api` and the server file is `capcut_server.py`. [GitHub search](https://github.com/sun-guannan/VectCutAPI); [README](https://github.com/sun-guannan/VectCutAPI)
- Positioned as a "toA (toAgent)" editing tool with cloud editing APIs and Skills. It works with Coze, Dify, n8n, OpenClaw, Claude Code and Trae. It exports drafts to "CapCut or Jianying" and needs Python 3.10+, "Jianying or CapCut International version" and FFmpeg. [README](https://github.com/sun-guannan/VectCutAPI)
- Its API and MCP cover: draft management, video (import, clip, transition, effects), audio, images (animation, masks, filters), multi-style text, **SRT subtitle import**, effects engine, stickers, **keyframes with easing**, and media analysis. `python capcut_server.py` starts an HTTP server on port 9001. `python mcp_server.py` starts an MCP server over stdio with 11 tools. [README](https://github.com/sun-guannan/VectCutAPI)
- "the code for the MCP Editing Agent, web-based editing client, and **cloud rendering modules has not been open-sourced yet**". The open-source repo therefore has no MP4 renderer. [README](https://github.com/sun-guannan/VectCutAPI)
- Many copies and forks exist, for example `xiaoxishui123/CapCutAPI-1.1.0` (Apache-2.0), `chenzhaohua11/CapCutAPI-Complete` (97★, license not detected, last push 2025-09) and `luhailiang98/CapCutAPI-YYZC` (32★, which claims async auto-export). [GitHub search](https://github.com/search?q=CapCutAPI&type=repositories)
- **huscpro/CapCutAPI**: the fork did not appear in any GitHub search I ran. Its existence and status are unverified.

**capcut-cli (renezander030)**: https://github.com/renezander030/capcut-cli
- 1,106★, MIT, last push 2026-11-04, current version v0.32.0. Installs with `npm install -g capcut-cli` (Node ≥18, zero native deps) or `pip install capcut` (a wrapper). It is described as an "Independent, unofficial CLI to edit CapCut and JianYing (剪映) projects". [README](https://github.com/renezander030/capcut-cli)
- Command groups:
  - inspect and lint
  - create (`init`, `quickstart`, `compile` from a JSON spec)
  - `render`: "low-res ffmpeg proxy — not CapCut's final render"
  - add video, audio and text
  - edit and animate: trim, speed, volume, transitions, masks, easing
  - templates and presets
  - subtitles: `caption` (Whisper), `import-srt`, `export-srt`, and `translate`, which clones a draft into other languages using `ANTHROPIC_API_KEY`
  - effects: sfx, chroma, matting
  - long-to-short: scene detection, silence and retake detection
  - automation: `serve` (a JSONL job runner for n8n, Make or Coze), `migrate`, `doctor`, `sync-timelines`
  
  [README](https://github.com/renezander030/capcut-cli)
- It ships an agent skill (`npx skills add renezander030/capcut-cli`) with "deterministic scripts for fades, **Ken Burns** and long-to-short cuts". It also offers an experimental read-only WebAssembly MCP sandbox. "The publish click stays human". [README](https://github.com/renezander030/capcut-cli)
- Optional `caption --cloud` uploads audio to ByteDance's CapCut servers for transcription. That path is experimental and unofficial. [README](https://github.com/renezander030/capcut-cli)
- Security note: fixture bundles made with versions up to 0.17.2 "may contain stable device identifiers". [README](https://github.com/renezander030/capcut-cli)
- The project is sponsor-funded, with paid tiers for template packs and a "full Claude viral-shorts pipeline" kept in a private repo. [README](https://github.com/renezander030/capcut-cli)

**capcut-mate (Hommy-master)**: https://github.com/Hommy-master/capcut-mate
- 2,094★, Apache-2.0, last push 2026-11-01. A FastAPI "剪映草稿自动化助手" that can be self-hosted (`uv run main.py`, docs at `:30000/docs`) or run with Docker Compose. It has a Coze plugin, an n8n integration, an Agent Skill ([capcut-mate-skill](https://github.com/Hommy-master/capcut-mate-skill)) and an Electron "剪映小助手客户端" desktop client. [README](https://github.com/Hommy-master/capcut-mate)
- Endpoints include `create_draft`, `add_videos`, `add_audios`, `add_images` and `add_captions` (batch; caption keyword highlighting), plus stickers, effects, masks and keyframes. `gen_video` is an asynchronous, queued "云端渲染" render job. [README (zh)](https://github.com/Hommy-master/capcut-mate/blob/main/README.zh.md); [gen_video doc](https://github.com/Hommy-master/capcut-mate/blob/main/docs/gen_video.zh.md)
- The `gen_video` doc's examples use the hosted `capcut-mate.jcaigc.cn` draft URLs. An `apiKey` from `jcaigc.cn` is required when `ENABLE_APIKEY=true`. The doc does not say whether a self-hosted install can render MP4 without the hosted service. [gen_video doc](https://github.com/Hommy-master/capcut-mate/blob/main/docs/gen_video.zh.md)

**JyDraft / "HDraft" (HTWMedia)**: https://github.com/HTWMedia/JyDraft
- 91★, the repo is Apache-2.0, created 2025-07-14, last push 2026-10-30. It is a **batch renderer** for existing JianYing/CapCut drafts. It reads a draft, auto-decrypts it, uploads the assets, renders concurrently **in HTWMedia's cloud**, and writes the MP4 back next to the draft. It ships as a CLI plus an HTTP API, as zip downloads for Windows x64 and macOS Intel/ARM with no installer. [README_EN](https://github.com/HTWMedia/JyDraft/blob/main/README_EN.md)
- It needs an emailed AuthKey. New accounts get a 1-month free quota, and quota is charged per submitted render. A `/Home/DecryptDraft` endpoint takes an uploaded encrypted draft JSON and returns plaintext. A lightweight **C# draft-generation library** (`ScriptFile.cs`) is included. [README_EN](https://github.com/HTWMedia/JyDraft/blob/main/README_EN.md)

**MCP servers**
- **JmsLdrn/capcut-mcp** (17★, MIT, last push 2026-08-07). Node 18+ and ffmpeg/ffprobe. It reads and edits CapCut desktop drafts: add, move, trim or split clips, text, audio and images; transforms; validate; save. It works "by cloning real segment/material templates out of an existing draft". It has a `CAPCUT_TEMPLATE_DRAFT` env var, whose default `0723` "is the author's own draft and won't exist on your machine". `capcut_save` refuses while CapCut is running or a `.locked` file exists, and it writes atomically with a `.mcpbak` backup. [README](https://github.com/JmsLdrn/capcut-mcp)
- **Atx-Guy/capcut-mcp-server** (88★, license not detected, last push 2026-01-13). A TypeScript MCP server with 11 tools over stdio or HTTP. It **requires VectCutAPI running on :9001**, so it is a thin wrapper. [README](https://github.com/Atx-Guy/capcut-mcp-server)
- **fancyboi999/capcut-mcp** (96★, license not detected, last push 2025-08-21, inactive in 2026). The README is titled "CapCutAPI" and lists the same `/create_draft`, `/add_video`, … `/save_draft` HTTP API. It needs Python 3.8.20 and ffmpeg, so it is a CapCutAPI derivative. [README](https://github.com/fancyboi999/capcut-mcp)
- **hey-jian-wei/jianying-mcp** (321★, license not detected, last push 2025-08-22). A JianYing MCP server with tools for drafts, tracks, video (animation, transition, filter, mask, keyframe), audio (effects, fades, keyframes), text (animation, bubble, 花字) and `export_draft`. Its tool set mirrors pyJianYingDraft's features. [README](https://github.com/hey-jian-wei/jianying-mcp)
- Others found:
  - mrbuslov/capcut-ai-editor (123★, MIT): a talking-head MCP that removes pauses and duplicate takes.
  - MigueDuque/capcut-mcp-server-extended (14★, MIT).
  - Mal-Suen/JianYing-AutoEdit-MCP (5★, GPL-3.0).
  - goransmoljanovic015-cell/capcut-mcp-server (a VectCutAPI backend).
  - yabdulaziz2009-dev/capcut-mcp (for CapCut International).
  
  [GitHub search "capcut mcp"](https://github.com/search?q=capcut+mcp&type=repositories)

**Other draft generators and skills**
- **duoec/duo-video** (162★, MIT, last push 2026-07-27). A Java SDK that builds JianYing projects from JSON and claims support for "the latest JianYing" (verified on **剪映 v10.1.0**). It includes **AutoJY**, which "以单任务的方式拉取视频任务，控制剪映生成视频", has Windows and macOS builds, and supports large batches through multi-machine deployment. [README](https://github.com/duoec/duo-video)
- **isYangs/jianying-editor-skill** (373★, MIT, last push 2026-10-15). A JianYing agent skill covering script writing, AI voice-over, subtitles aligned sentence by sentence to the voice-over, music (local or JianYing's cloud library), searchable effects, and auto-export to MP4 at 1080P–4K. **Auto-export needs JianYing 5.9 or lower** on Windows; on macOS it exports "via Windows Agent". [README](https://github.com/isYangs/jianying-editor-skill)
- **cutcli** (xuliang2024/cutcli-cookbook, 201★, MIT cookbook). A CapCut/JianYing draft CLI with cloud rendering since v1.3.9 (`cutcli cloud render <draftId>`) and `cutcli timer render` for scheduled rendering. The cookbook is MIT, but **the license of the cutcli binary and service is not stated** in the cookbook README. [README](https://github.com/xuliang2024/cutcli-cookbook)
- Inactive (no 2026 pushes):
  - notinmood/JianyingDraft.PY (213★, MIT, 2024-06)
  - xiaoyiv/JianYingProDraft (181★, license not detected, 2024-03)
  - JianYing-Automation/JianYingApi (263★, MIT, 2024-05)
  
  [GitHub search](https://github.com/search?q=jianying&type=repositories)
- A Go SDK, yxx1912008/com.linker.jianying.sdk (27★, Apache-2.0). Also Ersiter/Jianying-CapCut2XML, which converts drafts to FCP7 XML for DaVinci, and guodaxia9527/capcut-srt-exporter. [GitHub search](https://github.com/search?q=capcut+draft&type=repositories)

#### Feature mapping (1–13) for the draft tools

| Tool | (1) | (2) | (3) | (4) | (5) | (6) | (7) | (8) | (9) | (10) | (11) | (12) | (13) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pyJianYingDraft | No | No (keyframes allow zoom, no AI) | No | Partial (SRT, text, fades, keyframes in draft; no FFmpeg) | No | No | No | No | Yes (JianYing; CapCut via pyCapCut) | No | Unknown | Partial (library; auto-export Windows only) | Partial (templates + batch export only on JianYing ≤6) |
| pyCapCut | No | No | No | Partial (SRT import, text, keyframes in draft) | No | No | No | No | Yes (CapCut 8.2/9.5 verified) | No | Unknown | Partial (library) | Partial (bulk draft generation; **no auto-export**) |
| VectCutAPI | No | No | No ("AI voiceovers" listed for the cloud product, not shown in repo) | Partial (SRT, keyframes, effects in draft) | No | No | No | No (web client not open-sourced) | Yes (JianYing + CapCut Intl) | Partial (HTTP + MCP) | Unknown | Yes (HTTP server) | Partial (render module closed) |
| capcut-cli | No | Partial (Ken Burns script in skill) | No | Partial (Whisper captions, SRT; render = proxy only) | No | No | No | No | Yes (CapCut + JianYing namespaces) | Partial (CLI/library/JSONL) | Unknown (`translate` is generic) | Partial (CLI; `serve` runner) | Partial (`serve`/`compile` bulk drafts; human renders) |
| capcut-mate | No | No | No | Partial (captions w/ keyword highlight) | No | No | No | No | Yes (JianYing) | Partial (HTTP, Coze, n8n) | Unknown | Yes (Docker + Electron client) | Partial (async `gen_video` queue tied to jcaigc.cn key) |
| HDraft/JyDraft | No | No | No | No | No | No | No | No | Consumes drafts (renders them) | Partial (HTTP API) | Unknown | Partial (CLI zip; cloud service) | Yes for rendering, but via a paid/quota hosted cloud |
| duo-video + AutoJY | No | No | No | Partial (masks, text templates) | No | No | No | No | Yes (JianYing v10.1.0 claimed) | Unknown | Unknown | Partial (Java SDK) | Yes (claimed multi-machine auto-export) |
| jianying-editor-skill | Partial (writes 文案) | No | Yes (AI 配音) | Yes (aligned subtitles, music, effects) | No | No | No | No | Yes (JianYing) | Unknown | Unknown | Partial (skill; Windows) | Partial (auto-export only ≤5.9) |
| MCP servers (JmsLdrn, Atx-Guy, fancyboi999, jianying-mcp) | No | No | No | Partial | No | No | No | No | Yes | Partial (MCP) | Unknown | Partial | No (interactive, one draft per session) |

Sources for the table: the READMEs cited above.

### Inferences
- pyCapCut, our feature 9 dependency, is the only maintained Python library that targets **CapCut International** specifically. The rest of the ecosystem centres on JianYing, the Chinese build. Its license is not detected, and that is a real risk for ai-content-agent if we redistribute it in a Windows installer. We should check its LICENSE file or ask upstream.
- capcut-cli treats version support as tested evidence (a per-version evidence matrix and write guards). That makes it the strongest alternative or companion to pyCapCut for robustness against CapCut updates. Its `translate` and `compile` could cover multi-language drafts.
- Every open-source tool here stops at "editable draft". Rendering to MP4 has three routes: the user clicks Export; old-version UI automation; or a closed cloud service (VectCut cloud, jcaigc.cn, HDraft, cutcli cloud).

### Gaps
- huscpro's CapCutAPI fork was not found. Its status is unknown.
- I could not confirm that sun-guannan/CapCutAPI was renamed to VectCutAPI from a primary statement. The evidence is circumstantial: the search miss, the `capcut-api` naming, and forks called "CapCutAPI-1.1.0".
- The PyPI release dates and versions of `pycapcut` and `pyJianYingDraft` were not fetched.
- The license text of pyCapCut, hey-jian-wei/jianying-mcp, fancyboi999 and Atx-Guy was not verified. GitHub detected none.
- I found no independent confirmation that duo-video's AutoJY works on JianYing 7+ (README claim only), and I could not open the AutoJY sub-README.

---

## Q2. Known pitfalls: encryption, CapCut International vs JianYing, draft IDs, refresh/restart, media paths, schema drift

### Takeaway
JianYing 6.0+ encrypts `draft_content.json` (AES). CapCut International is reported as not encrypted, though one vendor disagrees. Encryption blocks *reading* app-authored drafts and templates, not *writing* new ones.

The bigger operational risk is **silent schema drift** on CapCut 8.7+, 9.x and 10.x:
- the app reads a different file than the one the tool wrote (template-2.tmp, draft_meta_info.json, or `Timelines/<id>/draft_info.json`);
- auto-updates migrate drafts in place;
- 10.x is reported to reject tool-written drafts as "内容已损坏".

Other recurring traps: drafts not showing until the app restarts, the app overwriting drafts edited while it is open, and duplicated IDs.

### Cited Findings
- **JianYing 6.0+ encryption.** "From 6.0+ it stores `draft_content.json` as an AES-encrypted binary payload … **CapCut International is not encrypted — only JianYing**." capcut-cli detects encryption but deliberately does not decrypt it, citing legal posture and an algorithm that has "shifted across JianYing point releases (see pyJianYingDraft #142/#169/#174)". [capcut-cli docs/jianying-encryption.md](https://github.com/renezander030/capcut-cli/blob/master/docs/jianying-encryption.md)
  - **Conflicting claim:** HDraft says "CapCut encrypts drafts since 5.9". [HDraft README_EN](https://github.com/HTWMedia/JyDraft/blob/main/README_EN.md). It probably conflates CapCut and JianYing, but this is unresolved.
- **Encryption blocks reading, not generation.** "on JianYing 11.4 (macOS) a plaintext `draft_info.json` is opened, upgraded to the encrypted format in place". The common "草稿内容已损坏" error "comes from writing the pre-6.0 file name `draft_content.json`" ([pyJianYingDraft#198](https://github.com/GuanYixuan/pyJianYingDraft/issues/198)). [capcut-cli encryption doc](https://github.com/renezander030/capcut-cli/blob/master/docs/jianying-encryption.md)
- JianYing 9.0.0 on Windows accepted a tool-written plaintext primary file on open, then "the app encrypts the legacy mirrors on close". [capcut-cli version-support.md](https://github.com/renezander030/capcut-cli/blob/master/docs/version-support.md)
- capcut-cli suggests three workarounds: pin JianYing 5.9.x and block auto-update; use CapCut International; or use community decryptors such as duo-video. [capcut-cli encryption doc](https://github.com/renezander030/capcut-cli/blob/master/docs/jianying-encryption.md)
  - The decryptors that exist in practice: aoguai's fork calls the local `videoeditor.dll` (verified 10.3.0–10.6.5), [aoguai README](https://github.com/aoguai/pyJianYingDraft); wenshui330/jy-draftc, [repo](https://github.com/wenshui330/jy-draftc); and HDraft's cloud `DecryptDraft` endpoint, which uploads the draft to a third party, [HDraft](https://github.com/HTWMedia/JyDraft/blob/main/README_EN.md).
- **The canonical file moves between CapCut versions.** This directly affects ai-content-agent's pyCapCut export. [capcut-cli version-support.md](https://github.com/renezander030/capcut-cli/blob/master/docs/version-support.md)
  - CapCut 8.7 (Windows): "`draft_content.json` edits may be ignored in favour of `template-2.tmp` / `draft_meta_info.json`" (issue #35).
  - CapCut 9.2.8-beta4 (macOS): the app reads `Timelines/<main_timeline_id>/draft_info.json`, so "a root-only write is a silent no-op".
  - CapCut 8.4.0 (macOS): the app migrated root files into a nested `Timelines/` on first open.
  - **CapCut 10.x (Mac and Windows): "New builds are reported to reject tool-written drafts as corrupted ('内容已损坏'; pyJianYingDraft#177, #194 for the JianYing 10.8 counterpart)"**. capcut-cli refuses writes to CapCut versions above 9.x unless `--force-write` is given.
  - CapCut 7.9/8.9: text `styles[].range` counts **UTF-16 code units**, not bytes.
- The recommended way to populate drafts on new CapCut builds is to "create an empty project in the app and quit CapCut", then `capcut compile spec.json --into <app-created-project> --active-timeline`. That keeps the app's own registration, and imported media "is staged under the project". [capcut-cli README](https://github.com/renezander030/capcut-cli); see also [zxypro1/capcut-shell-inject](https://github.com/zxypro1/capcut-shell-inject), cited by the version matrix.
- **Auto-upgrade migrates drafts.** "the app updates itself, rewrites the drafts it opens" ([pyJianYingDraft#115](https://github.com/GuanYixuan/pyJianYingDraft/issues/115), #178). The advice is to keep the validated installer, back up `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft` before the first launch after an update, and run bulk pipelines on a copy of the store. "we know of no documented setting that permanently disables" updates on Windows. [capcut-cli version-support.md](https://github.com/renezander030/capcut-cli/blob/master/docs/version-support.md)
- **Refresh and restart.**
  - pyJianYingDraft and pyCapCut both say new drafts may only appear after entering and leaving an existing draft, or after restarting JianYing/CapCut. [pyCapCut README](https://github.com/GuanYixuan/pyCapCut); [pyJianYingDraft README](https://github.com/GuanYixuan/pyJianYingDraft)
  - InsightCut: "如果剪映没有立即显示新草稿，完全退出并重新打开剪映专业版". [InsightCut README](https://github.com/SkyNotSilent/insightcut-jianying-image-video)
  - aoguai's fork adds registration in JianYing's root metadata, given the `JianyingPro User Data` path. [aoguai README](https://github.com/aoguai/pyJianYingDraft)
- **Editing while the app is open.** "CapCut autosaves on a timer; writing while it's open gets clobbered". JmsLdrn's save refuses if CapCut is running or `.locked` is present. [JmsLdrn/capcut-mcp](https://github.com/JmsLdrn/capcut-mcp). capcut-cli likewise protects managed draft paths "while the desktop editor is detected". [version-support.md](https://github.com/renezander030/capcut-cli/blob/master/docs/version-support.md)
- **Duplicated IDs.** duo-video: the segment `id` must be globally unique, because it "生成剪映工程时会将它作为临时文件名，如果重复，视频引用会乱掉". [duo-video README](https://github.com/duoec/duo-video)
- **Template drafts tied to the author.** JmsLdrn's default template draft `0723` "won't exist on your machine". [README](https://github.com/JmsLdrn/capcut-mcp)
- **Effects and fonts.** JianYing tries to download uncached animations, effects and transitions when it opens a draft and can time out ("xx加载失败"), more often on 5.9. Uncached fonts need the draft opened a second time. [pyJianYingDraft README](https://github.com/GuanYixuan/pyJianYingDraft)
- **Media paths.** Pilipili-AutoVideo writes its draft to `data/outputs/{project_id}/draft/` and says to "Copy the entire folder to CapCut's draft directory". [Pilipili README](https://github.com/OpenDemon/Pilipili-AutoVideo). InsightCut's backend "创建独立的草稿文件夹，复制素材和草稿 JSON". [InsightCut README](https://github.com/SkyNotSilent/insightcut-jianying-image-video)
- **JianYing vs CapCut International differences.**
  - capcut-cli tells the two apart by `platform.app_source` ("cc" for CapCut, "lv" for JianYing) and needs `--jianying` to use JianYing's enum namespace. [capcut-cli README](https://github.com/renezander030/capcut-cli); [version-support.md](https://github.com/renezander030/capcut-cli/blob/master/docs/version-support.md)
  - ArcReel's export "面向中国大陆版剪映，与 CapCut 的兼容性尚未验证". [ArcReel README](https://github.com/ArcReel/ArcReel)
  - GuanYixuan keeps two separate libraries. [pyCapCut](https://github.com/GuanYixuan/pyCapCut)

### Inferences
- For ai-content-agent, which writes CapCut International drafts with pyCapCut, encryption is not the main threat. The threats are writing the wrong file on CapCut 8.7+/9.x, and CapCut 10.x rejecting the draft. Validating against the user's installed CapCut version, and possibly seeding from an app-created empty project, would reduce support tickets.
- The UTF-16 code-unit finding matters for Vietnamese. Vietnamese text with precomposed versus combining diacritics changes string lengths, and style ranges computed in bytes or code points could misalign styled captions. This is untested; it is an inference, not a reported bug.

### Gaps
- **The "fixed/duplicated `draft_id` in `draft_meta_info.json` templates" pitfall had no primary source.** A targeted web search turned up only related material: the role of meta_info and the jy-draftc decryptor. [Search results: notinmood/JianyingDraft.PY](https://github.com/notinmood/JianyingDraft.PY); [jy-draftc](https://wingetly.io/apps/wenshui330/jy-draftc). It should be treated as anecdotal until reproduced.
- The texts of pyJianYingDraft issues #142, #169, #174, #177, #194 and #198 were not read directly. They are cited only through capcut-cli's docs.
- I found no evidence about which CapCut International version pyCapCut drafts break on beyond 9.5.0.4050.

---

## Q3. Chinese-ecosystem end-to-end AI video tools: which of our 13 features do they cover, and do any support Vietnamese?

### Takeaway
The feature-rich projects come in four types:
- **Topic-to-short generators**: MoneyPrinterTurbo (138k★), MoneyPrinterPlus, Pixelle-Video.
- **Commentary/recap editors**: NarratoAI (11.7k★).
- **AI 短剧/漫剧 studios** (novel or script → assets → storyboard → video): Toonflow (20.4k★), huobao-drama (17.0k★), ArcReel (6.1k★), BigBanana, LocalMiniDrama, TypeTale.
- **Social uploaders**: social-auto-upload (16.1k★).

Several of them (ArcReel, NarratoAI, Pilipili, InsightCut, story-studio, TypeTale, Dramaxis) export **JianYing** drafts, all through pyJianYingDraft. None I found targets CapCut International as its main format, and none combines our feature 6 (YouTube Shorts + TikTok + Facebook Page publishing) with feature 7 (cron topic rotation plus dedup).

Vietnamese support is thin:
- Toonflow has a Tiếng Việt UI.
- MoneyPrinterTurbo and NarratoAI include vi-VN TTS voices.
- Nothing else confirmed.

### Cited Findings

**MoneyPrinterTurbo (harry0703)**: https://github.com/harry0703/MoneyPrinterTurbo (138,464★, MIT, last push 2026-11-04)

(1) Partial: "AI 自动生成或改写多语言视频脚本". A script, not an explicit scene-by-scene storyboard.

(2) Partial: stock footage from Pexels, Pixabay and Coverr, or local media, plus MiniMax H3 text-to-video for 4–15 s AI clips. No AI images with Ken Burns.

(3) Yes: Edge TTS (free), Azure, SiliconFlow, Gemini, MiMo, MiniMax, ElevenLabs, Fish Audio, VoxCPM.

(4) Partial: automatic subtitles from TTS timestamps or Whisper, with font, position, colour, stroke and background options; background music; 9:16 output. Hook text, logo and loudness are Unknown.

(5) Unknown.

(6) Partial: "生成完成后可自动上传至 TikTok、Instagram 和 YouTube Shorts". No Facebook Page.

(7) Unknown.

(8) Partial: WebUI plus "任务历史记录". Live progress and error log are Unknown.

(9) No: no mention of 剪映 or CapCut in the README.

(10) Yes: many LLM, TTS and media providers.

(11) Partial: vi-VN voices in `docs/voice-list.txt` and `app/services/data/azure_voices.json` (GitHub code search).

(12) Partial: `webui.bat` on Windows (no installer) and Docker with a prebuilt GHCR image. Offered as "AI Agent、WebUI、API 和 CLI".

(13) Partial: "批量生成多条成片". Generating from a list of topics is not confirmed.

[README](https://github.com/harry0703/MoneyPrinterTurbo); [code search vi-VN](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/docs/voice-list.txt)

**NarratoAI (linyqh)**: https://github.com/linyqh/NarratoAI (11,706★, MIT, last push 2026-10-24)

"利用 AI 大模型，一键解说并剪辑视频": it narrates and edits *existing* footage.

(1) Partial: an LLM writes the commentary script for the source video.

(2) No: it uses the user's video.

(3) Yes: Tencent Cloud TTS, IndexTTS-1.5 and IndexTTS-2 voice cloning, Doubao TTS.

(4) Partial: automatic editing; optional "Sonilo AI 配乐".

(5) Unknown. (6) Unknown. (7) Unknown.

(8) Partial: a Streamlit `webui.py`.

(9) Yes: "支持导出剪映草稿" (JianYing).

(10) Partial: several TTS engines and LLM APIs.

(11) Partial: vi-VN in `app/services/voice.py` (code search).

(12) Yes: Windows 整合包 and Docker on macOS.

(13) Unknown.

The README warns that renamed copies of NarratoAI are being resold on Douyin and Bilibili.

[README](https://github.com/linyqh/NarratoAI)

**Pixelle-Video (AIDC-AI)**: https://github.com/AIDC-AI/Pixelle-Video (Apache-2.0; star count not retrieved)

(1) Partial: LLM-generated scripts, including scripts from uploaded media ("Custom Media", 2025-12-04).

(2) Yes: HTML templates `image_*.html` (AI-generated images as background) and `video_*.html` (AI videos). Image-to-video and digital-human pipelines were added 2026-01-14, and motion transfer 2026-01-26.

(3) Yes: Edge-TTS, Index-TTS (voice cloning), and custom ComfyUI TTS workflows.

(4) Partial: template-based composition in portrait or landscape. Details Unknown.

(5) Unknown. (6) Unknown. (7) Unknown.

(8) Partial: Streamlit Web UI with a history page.

(9) No: not mentioned.

(10) Yes: ComfyUI and RunningHub workflows plus direct API models; "image, video, TTS, VLM … swapped as needed".

(11) Unknown: "multi-language TTS voices", but no vi-VN code-search hit.

(12) Yes: Windows 一键整合包, "No need to install Python, uv, or ffmpeg".

(13) Partial: "batch video task creation support".

[README_EN](https://github.com/AIDC-AI/Pixelle-Video/blob/main/README_EN.md)

**MoneyPrinterPlus (ddean2009)**: https://github.com/ddean2009/MoneyPrinterPlus (7,302★; **GPL-3.0 plus a non-commercial clause**, a custom licence; last push 2025-03-07, no 2026 activity)

(1) Unknown. (2) Partial: Stable Diffusion and ComfyUI.

(3) Yes: local chatTTS, GPT-SoVITS, faster-whisper; cloud Azure, Alibaba, Tencent.

(4) Partial: batch 混剪. (5) Unknown.

(6) Partial: auto-publish to 抖音, 快手, 小红书, 视频号. No YouTube, TikTok or Facebook.

(7) Unknown. (8) Partial: a web UI (implied by the tutorials).

(9) No. (10) Partial. (11) Unknown.

(12) Partial: Windows 小白版 run with `setup.bat`/`start.bat`, and a Dockerfile.

(13) Yes: "AI一键批量生成各类短视频, 自动批量混剪".

The README says "任何人不得以本软件为基础进行商业使用".

[README](https://github.com/ddean2009/MoneyPrinterPlus)

**social-auto-upload (dreammis)**: https://github.com/dreammis/social-auto-upload (16,106★, MIT, last push 2026-10-22)

A publisher only, so only (6), (7), (10), (12) and (13) apply. The others are No.

(6) Yes for TikTok (Chrome implementation, no CLI), YouTube, and Facebook Page (video and image posts, with scheduling, query and cancel). It also covers 抖音, Bilibili, 小红书, 快手, 视频号, 百家号, 大鱼号, 微博, 虎扑, 知乎, Instagram (Reels) and Facebook.

(7) Partial: per-platform scheduled publishing. YouTube scheduling is "开发中". No topic rotation.

(10) Yes: per-platform uploaders as CLI (`sau`) and Agent Skills.

(12) Partial: CLI, self-hosted.

(13) Partial: CLI is batch-capable.

[README](https://github.com/dreammis/social-auto-upload)

**ArcReel**: https://github.com/ArcReel/ArcReel (6,129★, **AGPL-3.0 plus NOTICE**, with a commercial licence on request; last push 2026-11-04)

(1) Yes: novel or script → characters, scenes, props, 分镜图 and 多宫格分镜.

(2) Yes: image and video generation, with assets reused across shots for consistency.

(3) Yes: TTS providers.

(4) Partial: "可直接合成视频".

(5) Unknown. (6) No. (7) Unknown.

(8) Partial: a web workbench with cost and usage tracking. Live progress Unknown.

(9) Partial: JianYing draft export for "中国大陆版剪映"; CapCut is "尚未验证".

(10) Yes: abstraction over Agent, text, image, video and TTS providers.

(11) Unknown.

(12) Yes: server via Docker Compose (port 1241).

(13) Partial: a task queue. Unattended runs over a topic list are Unknown.

[README](https://github.com/ArcReel/ArcReel)

**Toonflow (HBAI-Ltd)**: https://github.com/HBAI-Ltd/Toonflow-app (20,396★; MIT now, previously AGPL-3.0, then Apache-2.0 for v1.0.8–v1.1.8; last push 2026-11-02)

(1) Yes: script creation and 智能分镜.

(2) Yes: image and video generation, with character and scene asset management.

(3) Unknown. (4) Partial: FFmpeg bundled. (5) Unknown. (6) No. (7) Unknown.

(8) Partial: an infinite canvas with visual workflow.

(9) Unknown: no 剪映 or CapCut mention.

(10) Yes: custom model providers, plugins, MCP.

(11) **Yes (UI)**: "支持 21 种界面语言", including Tiếng Việt, and a Vietnamese README.

(12) Yes: desktop, Android ARM64, Docker and server.

(13) Unknown.

[README](https://github.com/HBAI-Ltd/Toonflow-app)

**huobao-drama 火宝短剧 (chatfire-AI)**: https://github.com/chatfire-AI/huobao-drama (16,989★; **CC BY-NC-SA 4.0, commercial use prohibited**, which GitHub shows as "other"; created 2026-01-05)

(1) Yes: an LLM parses the script into characters, scenes and storyboards.

(2) Yes: Seedance 2.0, MiniMax H3, Wan 3.0 video.

(3) Unknown.

(4) Partial: "FFmpeg 单镜头合成与字幕处理".

(5) Unknown. (6) No. (7) Unknown.

(8) Partial: web UI settings stored in a database.

(9) Unknown. (10) Partial: multiple video providers.

(11) No: UI in zh, en, ja and ko only.

(12) Yes: an Electron desktop app (NSIS installer for Windows x64, dmg for Mac) and a Docker image.

(13) Partial: "Batch Generate Videos" per task, with one-click retry.

[README](https://github.com/chatfire-AI/huobao-drama)

**Pilipili-AutoVideo (OpenDemon)**: https://github.com/OpenDemon/Pilipili-AutoVideo (208★; the README says MIT but GitHub detects no licence; last push 2026-03-25)

(1) Yes: an LLM (DeepSeek, Kimi, MiniMax or Gemini) plans the scenes, which the user can edit in the Web UI.

(2) Yes: keyframe images (Nano Banana), then image-to-video clips (Kling 3.0 or Seedance 1.5).

(3) Yes: MiniMax TTS, measuring each clip's duration in milliseconds.

(4) Yes: FFmpeg xfade transitions, WhisperX subtitle burning, audio mix; 9:16, 16:9 or 1:1.

(5) Unknown. (6) No. (7) Unknown.

(8) Partial: React 19 studio over WebSocket.

(9) Yes: a CapCut/JianYing draft via pyJianYingDraft, delivered alongside the MP4.

(10) Partial: configurable providers. (11) Unknown.

(12) Yes: Docker Compose.

(13) Unknown.

[README](https://github.com/OpenDemon/Pilipili-AutoVideo)

**InsightCut (SkyNotSilent)**: https://github.com/SkyNotSilent/insightcut-jianying-image-video (123★, MIT, last push 2026-11-01)

(1) Yes: "文稿转分镜". (2) Yes: AI images per segment.

(3) Yes: TTS voice-over and voice cloning.

(4) Partial: subtitles and FFmpeg MP4.

(5) Unknown. (6) No. (7) Unknown.

(8) Partial: a FastAPI + React workbench.

(9) Yes: a JianYing/CapCut draft as a ZIP, or written directly into the local draft dir (Mac or Windows), using pyJianYingDraft.

(10) Unknown. (11) Unknown.

(12) Partial: self-hosted local app.

(13) Unknown.

[README](https://github.com/SkyNotSilent/insightcut-jianying-image-video)

**story-studio (konlu)**: https://github.com/konlu/story-studio (729★; **CC BY-NC-SA 4.0, non-commercial**; last push 2026-11-03)

An agent skill. Pipeline: "选题 → 文案 → 配音 → 配图 → 剪映草稿".

(1) Yes: it writes and splits the script into shots, with a separate step to optimise only the opening hook.

(2) Yes: generated images, plus slow push-pull keyframes (Ken Burns-like) in a 1080x1920 draft.

(3) Yes: voice-over with ffprobe/ffmpeg integrity checks.

(4) Partial: subtitle timestamp alignment, plus an optional local FFmpeg render.

(5) Unknown. (6) No.

(7) Partial: it records text and audio hashes so the same script and voice are never synthesised twice (dedup). No cron.

(8) No. (9) Yes: JianYing Pro draft via `pyJianYingDraft==0.3.1`.

(10) Partial. (11) Unknown.

(12) Partial: Windows `bootstrap.ps1`, and on Windows it detects the draft dir and can help install JianYing via WinGet.

(13) Partial.

[README](https://github.com/konlu/story-studio)

**Dramaxis 剧枢 (Agions)**: https://github.com/Agions/dramaxis (454★, MIT)

A Tauri 2 + Rust + React 19 desktop app built around multiple agents, including a VisualCriticAgent and a QualityReviewerAgent.

(1) Yes: multi-agent scripting.

(2) Partial: commentary over source footage, with FFmpeg scene detection.

(3) Yes: voice cloning and synthesis.

(4) Yes: FFmpeg millisecond-level sync, BGM ducking, silencedetect-based subtitles.

(5) Unknown.

(6) Partial or Unknown: it claims an "8 大平台消重发布矩阵" with platform specs for Douyin, TikTok and YouTube Shorts. Actual upload automation is not confirmed.

(7) Unknown. (8) Partial: desktop UI.

(9) Yes: "剪映草稿 (.draft) 原生工程导出与防重矩阵".

(10) Unknown. (11) Unknown.

(12) Yes: Tauri desktop.

(13) Unknown.

[README](https://github.com/Agions/dramaxis)

**TypeTale 字字动画**: https://github.com/TypeTale/TypeTale (904★, **licence not detected**, last push 2026-08-21)

"完全免费的AIGC视频软件", for AI 短剧, AI 电影 and 小说推文.

(1) Yes: batch chapter reasoning and rewriting into storyboards.

(2) Yes: images per shot, and video categories.

(3) Yes: batch multi-role dubbing with IndexTTS2 emotion vectors.

(4) Partial. (5) Unknown. (6) No. (7) Unknown. (8) Partial: desktop UI.

(9) Yes: "将视频草稿批量导出至剪映，全自动添加关键帧，应用分镜特效", with JianYing templates for watermark and subtitle style.

(10) Partial: plugins. (11) Unknown. (12) Partial: desktop software.

(13) Yes: batch chapter, image and voice operations.

The 即梦 CLI integration is limited to premium members.

[README](https://github.com/TypeTale/TypeTale)

**Other 小说推文 / 漫剧 tools**
- xuanyustudio/LocalMiniDrama (2,336★, MIT): an Electron exe in standard and Lite versions, local-first, with Seedance 2 and novel import. [README](https://github.com/xuanyustudio/LocalMiniDrama)
- shuyu-labs/BigBanana-AI-Director (2,414★, CC BY-NC-SA 4.0): an Electron desktop app (~122 MB) "适合系统化短剧制作、批量视频生产、工业化工作流". It exports master video, clip ZIPs and source assets for Premiere or Resolve, with no JianYing mention. [README](https://github.com/shuyu-labs/BigBanana-AI-Director)
- xhongc/ai_story (1,990★, CC BY-NC-SA 4.0): "批量生成，实时显示进度", video synthesis and subtitles, Docker. [README](https://github.com/xhongc/ai_story)
- zzy7517/novel2video (412★, licence not detected, inactive since 2025-01): "将小说内容批量转换为图片和音频" with SD WebUI or ComfyUI, then "字幕，BGM等视频处理可以使用剪映". [README](https://github.com/zzy7517/novel2video)
- alibaba/lumenx (1,445★, MIT): novel → script analysis → characters → storyboard → video, using FFmpeg. [README](https://github.com/alibaba/lumenx)
- zenstory-ai/drama-skills (3,759★, MIT) and zenstory-ai/video-recap-skills (601★, MIT) are Claude Code/Codex skills. wangcanyu/daihuo-fanpai (93★, MIT) is a pipeline: 即梦/Seedance → 剪映 draft. [GitHub search](https://github.com/search?q=%E5%89%AA%E6%98%A0+%E8%8D%89%E7%A8%BF&type=repositories)

**Vietnamese specifically**
- Toonflow lists Tiếng Việt among its 21 UI languages and links `docs/readme/readmeVi.md`. [Toonflow README](https://github.com/HBAI-Ltd/Toonflow-app)
- MoneyPrinterTurbo and NarratoAI contain vi-VN voice entries (GitHub code search hits in `docs/voice-list.txt`, `app/services/data/azure_voices.json` and `app/services/voice.py`). Pixelle-Video had no vi-VN hit. [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo); [NarratoAI](https://github.com/linyqh/NarratoAI)
- Small CapCut-TTS repos with Vietnamese-looking owner names: K07VN/capcut-tts-api (315★, licence not detected), MinhPhanCoder/capcut-tts-api, and KhoaDayy/CapDraft-TTS (Apache-2.0, "attach audio back into the same CapCut draft"). [GitHub search "capcut api"](https://github.com/search?q=capcut+api&type=repositories)

### Inferences
- Compared with ai-content-agent:
  - No Chinese project found combines all of the following, which is our differentiating mix: cron topic rotation with dedup (7), Western publishing to YouTube Shorts, TikTok and Facebook Page (6), *CapCut International* drafts (9), and Vietnamese (11).
  - The 漫剧 studios are much stronger on (1) and (2): character consistency, multi-provider video models and cost tracking.
  - social-auto-upload is the most complete open-source publisher. Its Facebook Page scheduling and TikTok support overlap our (6) and could be a reference or dependency, given its MIT licence.
- pyJianYingDraft is the shared foundation across the 剪映-draft ecosystem: Pilipili, InsightCut, story-studio and others. CapCut International drafts, our niche, are comparatively underserved.
- Licence caution: huobao-drama, story-studio, BigBanana and xhongc/ai_story are CC BY-NC-SA, which forbids commercial use. MoneyPrinterPlus is GPL plus a non-commercial clause. ArcReel is AGPL. TypeTale and novel2video have no detected licence. None of these should be copied into a commercial product.

### Gaps
- Pixelle-Video's star count and its pipeline details (storyboard step, captions) were not fully verified.
- For most projects, the README is silent on auto thumbnail (5), live progress and error-log dashboards (8), and cron or topic rotation (7), so those cells are Unknown rather than No.
- Whether MoneyPrinterTurbo's UI and script generation fully support Vietnamese, beyond the voice list, was not checked.
- I did not check Bilibili, CSDN or Zhihu for closed-source 小说推文 tools, such as commercial "一键推文" desktop apps. The open-source scope may miss the most-used commercial tools.

---

## Q4. Batch/mass production: which tools generate many videos or drafts unattended, and can CapCut-draft workflows be exported to MP4 with no human?

### Takeaway
Draft *generation* scales trivially, since it is just files. **MP4 export from the CapCut or JianYing desktop app is the bottleneck.**

- With open-source code alone, unattended local export exists only on JianYing ≤6 (pyJianYingDraft UI automation, Windows) or ≤5.9 (jianying-editor-skill). There is also duo-video's AutoJY, which claims support up to JianYing 10.1 with multi-machine farms; that claim is unverified.
- For CapCut International, which our project targets, I found no open-source auto-export. pyCapCut explicitly has none.
- Scaled pipelines use one of two routes:
  - render MP4 independently with FFmpeg and treat the draft only as an optional "fine-tune" deliverable (Pilipili, InsightCut, ArcReel, story-studio);
  - pay for or depend on a closed cloud renderer (VectCut cloud, capcut-mate/jcaigc.cn, HDraft, cutcli cloud).

### Cited Findings
- pyJianYingDraft export works only on JianYing ≤6 and only on Windows, because 7+ hides the controls. It takes over the window and cursor, so "建议在闲时/夜间运行", and it can loop forever on VIP-gated features. [pyJianYingDraft README](https://github.com/GuanYixuan/pyJianYingDraft)
- pyCapCut: "目前CapCut版暂不支持自动导出". [pyCapCut README](https://github.com/GuanYixuan/pyCapCut)
- jianying-editor-skill: "自动导出需要 5.9 或更低版本". [README](https://github.com/isYangs/jianying-editor-skill)
- duo-video's AutoJY: "以单任务的方式拉取视频任务，控制剪映生成视频。可以通过部署多个剪映生成服务，以支持大批量的视频创作". Windows and macOS builds; verified on JianYing v10.1.0. MIT. [duo-video README](https://github.com/duoec/duo-video)
- capcut-cli's `render` is only a "low-res ffmpeg proxy — not CapCut's final render". `serve` runs JSONL job queues for n8n, Make or Coze. [capcut-cli README](https://github.com/renezander030/capcut-cli)
- VectCutAPI offers "Automated Cloud Generation", but the "cloud rendering modules has not been open-sourced yet". Its README invites contact for "batch production of videos with AIGC". [VectCutAPI README](https://github.com/sun-guannan/VectCutAPI)
- capcut-mate: the `gen_video` async render queue, using a jcaigc.cn `apiKey` when enabled. [gen_video doc](https://github.com/Hommy-master/capcut-mate/blob/main/docs/gen_video.zh.md)
- HDraft: concurrent cloud rendering of many drafts (`--jobs`), quota-billed per render, aimed at "daily matrix accounts (dozens of similar drafts per batch), templated mass production". [HDraft README_EN](https://github.com/HTWMedia/JyDraft/blob/main/README_EN.md)
- cutcli v1.3.9: `cutcli cloud render` and `cutcli timer render` "可按固定间隔执行同一流程". [cutcli-cookbook](https://github.com/xuliang2024/cutcli-cookbook)
- Dual-output pattern, MP4 from FFmpeg plus a draft:
  - Pilipili: "Auto CapCut draft + MP4 dual output". [README](https://github.com/OpenDemon/Pilipili-AutoVideo)
  - InsightCut: "导出完整视频、分镜素材包和剪映 / CapCut 草稿，三种交付互不替代". [README](https://github.com/SkyNotSilent/insightcut-jianying-image-video)
  - ArcReel: "既可直接合成视频，也可导出剪映草稿". [README](https://github.com/ArcReel/ArcReel)
  - story-studio: optional local FFmpeg render. [README](https://github.com/konlu/story-studio)
- Batch-oriented end-to-end tools:
  - MoneyPrinterTurbo: "批量生成多条成片". [README](https://github.com/harry0703/MoneyPrinterTurbo)
  - MoneyPrinterPlus: "AI一键批量生成…自动批量混剪…自动把视频发布到抖音,快手,小红书,视频号". [README](https://github.com/ddean2009/MoneyPrinterPlus)
  - Pixelle-Video: "batch video task creation support" and configurable RunningHub concurrency. [README_EN](https://github.com/AIDC-AI/Pixelle-Video/blob/main/README_EN.md)
  - huobao-drama: "Batch Generate Videos". [README](https://github.com/chatfire-AI/huobao-drama)
  - TypeTale: "将视频草稿批量导出至剪映". [README](https://github.com/TypeTale/TypeTale)
  - BigBanana: "批量视频生产、工业化工作流". [README](https://github.com/shuyu-labs/BigBanana-AI-Director)
  - xhongc/ai_story: "批量生成，实时显示进度". [README](https://github.com/xhongc/ai_story)
  - novel2video: "将小说内容批量转换为图片和音频". [README](https://github.com/zzy7517/novel2video)
- Template-based bulk drafting: pyJianYingDraft's `duplicate_as_template` plus replacing media and text by name. [pyJianYingDraft README](https://github.com/GuanYixuan/pyJianYingDraft). TypeTale's JianYing templates set watermark and subtitle style. [TypeTale README](https://github.com/TypeTale/TypeTale)

### Inferences
- For a mass-production **agent**, ai-content-agent's current design is the pattern that scales: FFmpeg renders the publishable MP4, and the CapCut draft is an optional manual-polish artifact. Making CapCut export part of the unattended path would mean either pinning old JianYing builds with Windows UI automation (fragile, one render at a time per machine, and JianYing rather than CapCut) or a closed paid cloud renderer.
- duo-video's AutoJY is the only open-source claim of unattended export on a current JianYing (10.1). It deserves a hands-on test if JianYing-side rendering ever becomes a requirement. It is Java, and its support for CapCut International is unknown.
- "Matrix account" (矩阵号) mass production is a stated target market in this ecosystem (HDraft, MoneyPrinterPlus, Dramaxis's "消重" de-duplication matrix). Their de-duplication is about making near-identical videos look distinct to platforms, which is different from our topic-dedup (7).

### Gaps
- I could not confirm whether capcut-mate's self-hosted `gen_video` renders locally through an installed JianYing or only through the jcaigc.cn service.
- Pricing for the VectCut cloud, jcaigc.cn and the cutcli cloud was not retrieved. HDraft only states a 1-month free quota.
- No benchmark of throughput (videos per hour per machine) was found for UI-automation export.

---

## Q5. Desktop packaging patterns used by these projects (Electron, Tauri, PyInstaller, Windows installers, bundled FFmpeg)

### Takeaway
There are two dominant patterns.
- **Electron + electron-builder NSIS installers with bundled FFmpeg/FFprobe.** Used by huobao-drama, LocalMiniDrama, BigBanana and capcut-mate's client. Dramaxis uses Tauri 2 instead.
- **The Python "整合包" (portable all-in-one zip).** Ships an embedded runtime and tools, so users need not install Python, uv or ffmpeg. Used by Pixelle-Video, NarratoAI and MoneyPrinterPlus.

Server mode is almost always Docker Compose. I saw no PyInstaller usage cited in the READMEs.

### Cited Findings
- **huobao-drama.** "Shell: Electron (utilityProcess hosts the backend; BrowserWindow loads same-origin)". "esbuild (single-file backend bundle) + electron-builder (dmg arm64/x64, NSIS win-x64)". "FFmpeg/FFprobe binaries are bundled — no system install needed". It has a built-in updater ("silent installer on Windows, with local sha256 verification") and publishes `latest.json` plus the installer to a GitHub Release. "Electron is pinned to 37.x: better-sqlite3's win32 prebuilds max out at that ABI". It also offers a multi-arch Docker image. [README](https://github.com/chatfire-AI/huobao-drama)
- **LocalMiniDrama.** Electron 28 with electron-builder, later upgraded to Electron 44. It ships `本地短剧助手 x.x.x.exe` (with sample project) and a smaller `-Lite-` exe, plus "ffmpeg 自动解压". [README](https://github.com/xuanyustudio/LocalMiniDrama)
- **BigBanana.** An Electron client for Windows 10+ and macOS 11+, "安装包约 122MB，安装即用". [README](https://github.com/shuyu-labs/BigBanana-AI-Director)
- **Dramaxis.** Tauri 2 + Rust + React 19. Its macOS note covers the unsigned-app Gatekeeper "已损坏" warning. [README](https://github.com/Agions/dramaxis)
- **Pixelle-Video.** A "Windows 一键整合包", "No need to install Python, uv, or ffmpeg - ready to use out of the box", added 2025-12-05. [README](https://github.com/AIDC-AI/Pixelle-Video)
- **NarratoAI.** A 整合包, where users must not separate the bundled `NarratoAI`, `runtime` and `tools` folders. Docker is the recommended option on macOS. [README](https://github.com/linyqh/NarratoAI)
- **MoneyPrinterPlus.** A Windows 小白版: unzip, then run `setup.bat` and `start.bat`. It also requires the VC++ redistributable and ffmpeg 6+ on PATH for source installs. [README](https://github.com/ddean2009/MoneyPrinterPlus)
- **MoneyPrinterTurbo.** `webui.bat`, Docker with a prebuilt GHCR image (`docker-compose.release.yml`), and ffmpeg "会被自动下载" (via imageio), with a manual `ffmpeg_path` fallback. [README](https://github.com/harry0703/MoneyPrinterTurbo)
- **Toonflow.** Desktop clients, an Android ARM64 APK, and Docker. The Docker image is built with Bun 1.4.3 and includes FFmpeg. [README](https://github.com/HBAI-Ltd/Toonflow-app)
- **capcut-mate.** An Electron desktop client (it documents `ELECTRON_MIRROR=npmmirror` for users in China) plus Docker Compose. [README](https://github.com/Hommy-master/capcut-mate)
- **HDraft.** Per-platform zips with no installer, plus a macOS `xattr -dr com.apple.quarantine` workaround. [README_EN](https://github.com/HTWMedia/JyDraft/blob/main/README_EN.md)
- **story-studio.** Native launchers (`bootstrap.ps1` / `bootstrap.sh`) that use uv to create an isolated environment on first use; on Windows it can help install JianYing via WinGet. [README](https://github.com/konlu/story-studio)
- **ArcReel.** Docker Compose, with a warning not to expose port 1241 to the public internet. [README](https://github.com/ArcReel/ArcReel)

### Inferences
- For a Windows desktop version of ai-content-agent (feature 12), there are two proven local templates. One is the 整合包 approach: embedded Python, bundled ffmpeg, zero setup. The other is huobao-drama's Electron + NSIS + bundled ffmpeg + sha256-verified self-updater. Electron/NSIS gives a "real installer" experience, while 整合包 is the norm for Python-heavy Chinese AI tools.
- Bundling ffmpeg is effectively expected in this market. Several projects explicitly removed the system-FFmpeg dependency.

### Gaps
- No README I read cited PyInstaller or Nuitka. Whether any Python tool here ships a PyInstaller exe is unknown.
- Code signing practice on Windows (signed vs unsigned NSIS installers) was not documented in the sources read.
