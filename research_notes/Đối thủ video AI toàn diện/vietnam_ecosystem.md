# Vietnamese ecosystem for automated AI short-video creation and mass production (as of 4–5 Nov 2026)

Method note: WebSearch ran in Vietnamese and English. WebFetch was blocked by the session's network policy for every Vietnamese host tried: phanmemmkt.vn, phanmemtudong.net, w5g.io.vn, lsvn.vn, atpsoftware.vn, mktsoftware.vn and docs.fpt.ai. It was also blocked for docs.cloud.google.com and huggingface.co (proxy 403). Commercial and legal findings therefore come from search snippets only. GitHub was reachable through the search API and raw.githubusercontent.com, so the open-source READMEs were read in full on 4 Nov 2026. "pushed" dates come from the GitHub search API on 4 Nov 2026. Voz, Viblo and Kipalog returned no relevant hits in any search.

## 1. Vietnamese tools (open source and commercial) and how they map to our 13 features

### Takeaway
Our earlier finding that "no open-source tool documents end-to-end Vietnamese" is out of date. Since mid-2026 a wave of small Vietnamese GitHub repos (0–200★) does topic or script → Vietnamese script → Vietnamese TTS (Edge, VieNeu, Vbee or LucyLab) → synced captions → 9:16 MP4. Most of them ship as **Claude Code or Antigravity "skills"** rather than as apps. **None documents auto-publishing to YouTube, TikTok or Facebook, topic-rotation scheduling, or a CapCut export for AI-generated videos.** Those remain our differentiators. The commercial Vietnamese market is dominated by **reup, "lách bản quyền" and multi-account "nuôi nick" tools** (MKT, ATP Software, V-Shorts, Chrome extensions for batch Veo on Google Flow). Only one AI-video-plus-auto-post SaaS was found ("Xây kênh AI"), and it is closed and its pricing is unverified.

### Cited Findings

**Open-source Vietnamese generators (READMEs read 4 Nov 2026)**
- **Cuongyd196/auto-video-gen**: MIT, 195★, TypeScript/Node 22, pushed 2026-09-28. It is a fork of hoquanghai/Auto-Create-Video. It turns a news article URL, GitHub repo or .txt/.md file into a 1080×1920 60fps MP4 ("Kịch bản → TTS → HTML Motion Graphics → Ghép âm thanh & SFX → Render"). It is built for Claude Code and Antigravity through the `/create-news-video` skill. TTS is switchable via `TTS_PROVIDER`: Edge TTS (free, default), LucyLab ("~25k/1M ký tự", with SRT), Vbee and ElevenLabs. There are 6 HTML/GSAP templates (HyperFrames). Output is an MP4 plus a `caption.txt` with TikTok hashtags. The README mentions no upload, scheduler, thumbnail or dashboard. — [GitHub](https://github.com/Cuongyd196/auto-video-gen)
- **Cuongyd196/whiteboard-video**: MIT, 41★, pushed 2026-09-30, a fork of geeklee/srt-whiteboard-animation. It takes a topic, script or SRT and produces a hand-drawn whiteboard video. The agent writes the script and "dừng để bạn duyệt" (stops for your review). Voice comes from Vbee or Edge TTS, and the SRT is built from the real voice timing. Scenes run 20–35 s, there is a browser preview editor, and there are Windows run instructions. — [GitHub](https://github.com/Cuongyd196/whiteboard-video)
- Cuongyd196 also maintains **auto-compare-video** (225★, HyperFrames-based "A vs B" knowledge Shorts with published YouTube Shorts demos) and **remotion-cuongit-template** (226★). He also runs a Facebook group and a Zalo group for "Làm Video với AI". — [auto-compare-video](https://github.com/Cuongyd196/auto-compare-video); [auto-video-gen README](https://github.com/Cuongyd196/auto-video-gen)
- **andyluu98/MotionFly**: Claude Code plugin; code is MIT, vendored parts keep their own licenses (GitHub shows NOASSERTION); 9★, pushed 2026-10-13.
  - Pipeline: brief → script by scene → **VieNeu voice with Whisper self-scoring of pronunciation and word-level timestamps** → storyboard anchored to spoken keywords → **background music that ducks under speech, −14 LUFS** → scenes built in code by parallel agents, with an independent checker → render plus `phude.srt`.
  - There are 43 styles, and saying "tự làm hết" skips the approval gates.
  - It installs 2–3 GB of models (VieNeu, Whisper).
  - [GitHub](https://github.com/andyluu98/MotionFly)
- **fx-studio/mini-video-workspace**: 7★, **non-commercial license**, pushed 2026-10-12. script.json → edge-tts → HTML frames captured with Playwright → ffmpeg → 1080×1920 30fps. It ships with a Claude-style skill `tao-video`. The README says "Repo không đăng video lên đâu cả. Cổng cuối là người" (the repo posts nothing; the last gate is a human). It also says fonts on Linux/Windows "có thể thiếu dấu tiếng Việt" (may lack Vietnamese diacritics) and suggests installing Noto Sans. — [GitHub](https://github.com/fx-studio/mini-video-workspace)
- **alexluffy/video-pipeline**: local web app, no license, pushed 2026-04-27; the clone URL points to chauanhdung995/video-pipeline.
  - Flow: "Topic → Script → Normalize TTS → Asset Keywords → TTS + SRT → HTML scenes + **Thumbnail** → Preview → Render → Concat + Music → Subtitle + **Logo**".
  - The LLM is Chato1 or Gemini, and TTS is LucyLab.
  - Captions are **karaoke subtitles from faster-whisper large-v3 word timestamps**, and "AI tạo thumbnail HTML → render ảnh JPG".
  - There are Windows install steps.
  - [GitHub](https://github.com/alexluffy/video-pipeline)
- **alexluffy/vibe-tool-video**: no license, pushed 2026-04-25. Topic or JSON script → AI script → **AI images** (Chato1) → LucyLab TTS → subtitles → per-scene render. Uses Puppeteer and Chrome, with Windows instructions. — [GitHub](https://github.com/alexluffy/vibe-tool-video)
- **tanthanh381/ai-short-video-studio**: no license, 0★, pushed 2026-10-31. This is the most "productized" of the group.
  - Stack: React web studio, Express API with Supabase auth and allow-list, and a worker with a durable PostgreSQL queue, per-step and per-scene checkpoints, bounded retries, heartbeat, daily budget and idempotency.
  - Generation: LLM scene split via Ollama (`qwen3.5:4b` by default; Claude/OpenAI optional), SDXL-Turbo images via MLX, an optional LTX-Video motion pass, and VieNeu-TTS v3 Turbo or Piper for voice.
  - Output: captions from the measured audio, 1080×1920 by default, and logo and music options.
  - Studio: shows progress, has a "Lịch sử xuất" (export history), and has a "Tiếp tục" (continue) button after errors.
  - Deployment: self-hosted via Docker and Tailscale Funnel, with a macOS focus.
  - The README mentions no publishing or scheduling.
  - [GitHub](https://github.com/tanthanh381/ai-short-video-studio)
- **huuthi139/Wevideo2**: local FastAPI web app on macOS. Paste a Vietnamese script and it produces edge-tts (NamMinh) voice, kinetic subtitles and **Veo clips generated by driving Google Flow through a Chrome extension**. This needs "tab flow.google.com đã đăng nhập" (a logged-in Flow tab) with Flow credits. — [GitHub](https://github.com/huuthi139/Wevideo2)
- **hungdata/text-to-video**: pushed 2026-10-09. Antigravity skills produce Vietnamese TikTok explainers: 9:16, 45–90 s, `vi-VN-NamMinhNeural`, word-synced karaoke captions, whiteboard scenes from the Explainroo engine with a Vietnamese patch, and a **`batch-video-maker` skill** that works from a topic list. macOS. — [GitHub](https://github.com/hungdata/text-to-video)
- **andyluu98/auto-video-maker**: MIT, 2★. Idea → DeepSeek script → Edge TTS (HoaiMy by default, NamMinh optional, adjustable rate) → per-scene images via ai-image-gpt-mcp → ffmpeg MP4 with "ảnh tĩnh + lời dẫn + pan nhẹ" (Ken Burns-like) and an .srt file. — [GitHub](https://github.com/andyluu98/auto-video-maker)
- **pennydinh/marketing-pineline-share**: 104★, no license. Claims research crawling, Claude/OpenAI writing in EN and VI, Remotion video, and a Next.js UI "để lên lịch đăng" (for scheduling posts). The README is marketing-style and does not document a publish mechanism. — [GitHub](https://github.com/pennydinh/marketing-pineline-share)
- **NamNguyenBmt/VideoLocalizer**: MIT badge (GitHub NOASSERTION), Windows 10/11, web UI plus desktop .exe. This is a **batch localization and reup pipeline**:
  - It downloads with yt-dlp from YouTube, TikTok and Facebook, and takes speech from Whisper or OCR.
  - It "xoá/làm mờ sub gốc" (removes or blurs the original subtitles), then translates, dubs and clones voices.
  - It can flip, change speed, zoom and reframe to 9:16, and adds watermark and **thumbnail**.
  - It exports **MP4 or a CapCut draft**, with a batch queue.
  - [GitHub](https://github.com/NamNguyenBmt/VideoLocalizer)
- **HuanEnzie/capcut-auto**: writes CapCut draft JSON directly, "Đã kiểm chứng trên CapCut 9.0.0". It batch-builds one draft per folder and installs on Windows through a `cai_dat.bat` double-click. — [GitHub](https://github.com/HuanEnzie/capcut-auto)
- **truongqv12/ntd-labs**: a **proprietary** Windows 10/11 app that does "tạo ảnh và video AI hàng loạt trên Google Labs" (mass AI images and videos on Google Labs), activated by license key or Google login. — [GitHub](https://github.com/truongqv12/ntd-labs)
- Other Vietnamese repos found, read from descriptions only:
  - chrisx9z/history-ai-studio: a FastAPI + Tauri desktop scaffold for history videos with script, storyboard, TTS and timeline; its own README calls it "chưa phải sản phẩm hoàn thiện" (not yet a finished product).
  - bitgacon/muse2api: a Vietnamese Muse image/video studio, Windows portable 1.6.8, MIT.
  - sonlovinbot-team/Muse-animated-short-film: a skill, MIT.
  - ONMM2025/cachdungai-youtube-shorts-vi: a Vietnamese Shorts script skill, MIT.
  - haingt-dev/Bookie: Remotion + viXTTS + Gemini + n8n + Google Sheets; marked "Paused", with 3 videos shipped.
  - wahdalo/tiktok-facebook-reuploader: 187★, a TikTok-to-Facebook-Reels reuploader using Puppeteer, last push 2024.
  - [GitHub search results, 4 Nov 2026](https://github.com/search?q=t%E1%BA%A1o+video+t%E1%BB%B1+%C4%91%E1%BB%99ng&type=repositories); [history-ai-studio](https://github.com/chrisx9z/history-ai-studio); [Bookie](https://github.com/haingt-dev/Bookie)

**13-feature mapping of the Vietnamese open-source tools**

● = Yes, ◐ = Partial, ○ = No, ? = Unknown. Ratings come only from the READMEs cited above.

| Tool | 1 Storyboard multi-LLM | 2 Per-scene AI visuals | 3 TTS | 4 FFmpeg full edit | 5 Thumb | 6 Auto-publish YT/TT/FB | 7 Schedule+rotation/dedup | 8 Dashboard | 9 CapCut | 10 Pluggable | 11 Vietnamese | 12 Win app/server | 13 Batch unattended |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| auto-video-gen | ◐ coding agent writes scenes; no LLM provider layer | ○ HTML/GSAP motion graphics, not AI images | ● Edge/LucyLab/Vbee/ElevenLabs | ◐ SFX+BGM mix, 1080×1920; logo/loudnorm ? | ? | ○ caption.txt only | ? | ○ CLI | ○ | ◐ TTS only | ● | ◐ CLI, Windows winget steps | ? one URL per run |
| whiteboard-video | ◐ agent script, human approval | ◐ per-scene line-art drawing animation | ● Vbee/Edge | ◐ synced subs; music/logo ? | ? | ○ | ? | ◐ preview editor | ○ | ◐ 2 TTS | ● | ◐ Windows run steps | ○ approval gates |
| MotionFly | ◐ Claude only | ◐ code-built motion graphics, 43 styles | ● VieNeu + Whisper check | ◐ strong: ducking, −14 LUFS, SRT; hook/logo ? | ? | ○ | ? | ○ | ○ | ◐ styles | ● | ? | ◐ "tự làm hết" mode |
| mini-video-workspace | ◐ agent skill | ○ HTML text frames | ● edge-tts | ◐ | ? | ○ explicitly none | ? | ○ | ○ | ? | ● | ◐ cross-platform CLI | ? |
| alexluffy/video-pipeline | ◐ Chato1 or Gemini | ◐ HTML scenes + asset keywords | ● LucyLab | ◐ karaoke subs, music, logo; loudnorm ? | ● HTML→JPG | ? | ? | ◐ local web UI | ? | ◐ | ● | ◐ local web, Windows steps | ? |
| alexluffy/vibe-tool-video | ◐ | ● AI images (Ken Burns ?) | ● LucyLab | ◐ | ? | ? | ? | ◐ server UI | ? | ? | ● | ◐ | ? |
| ai-short-video-studio | ● Ollama / Claude / OpenAI | ● SDXL images + optional LTX motion | ● VieNeu/Piper | ◐ subs from audio, logo, music, 9:16; loudnorm ? | ? | ○ | ? | ● progress, history, resume after error | ○ | ◐ adapters | ● | ◐ server mode (Docker), macOS-focused | ◐ durable queue, one script per job |
| Wevideo2 | ? | ● Veo clips via Flow extension | ● edge-tts | ◐ kinetic subs | ? | ? | ? | ◐ UI with progress | ? | ? | ● | ○ macOS | ? |
| hungdata/text-to-video | ◐ agent | ◐ whiteboard animation | ● NamMinh | ◐ karaoke | ? | ? | ? | ○ | ○ | ? | ● | ○ macOS | ◐ batch-video-maker skill |
| andyluu98/auto-video-maker | ◐ DeepSeek only | ● AI images + light pan | ● Edge | ◐ SRT | ? | ? | ? | ○ CLI | ○ | ? | ● | ◐ CLI | ? |
| VideoLocalizer (reup/localize) | n/a | ○ uses source videos | ● dubbing + clone | ◐ reframe, watermark | ● | ? | ? | ◐ web UI | ● CapCut draft | ? | ● | ● Windows exe | ◐ batch queue |
| capcut-auto | n/a | n/a | n/a | ◐ audio balancing | ? | ○ | ? | ◐ app | ● CapCut 9.0.0 drafts | ? | ● Vietnamese UI | ● Windows .bat | ◐ folder batch |

All sources for this table are the GitHub READMEs cited above.

**Commercial and closed Vietnamese tools (search snippets only, Nov 2026)**
- **Xây kênh AI** (phanmemmkt.net/.vn): a Web SaaS for AI video creation plus automatic TikTok posting from one interface, with batch scheduling. The snippets give no pricing. — [phanmemmkt.net](https://phanmemmkt.net/dang-tiktok-tu-dong/); [phanmemmkt.vn](https://phanmemmkt.vn/xay-kenh-ai)
- The same vendor markets a "Phần mềm **lách bản quyền** video Youtube, TikTok tự động TOP 1" (automatic copyright-evasion software for YouTube and TikTok videos) and a "Tool đăng video Tiktok hàng loạt" (mass TikTok posting tool). — [phanmemmkt.vn](https://phanmemmkt.vn/phan-mem-lach-ban-quyen-video); [phanmemmkt.vn](https://phanmemmkt.vn/tool-dang-video-tiktok)
- **MKT Viral** (MKT Software), a multi-platform reup tool: 3,000,000 VND for 1 year, 7,000,000 VND for 5 years, 12,000,000 VND for 10 years. Some blogs call it "miễn phí" (free), which contradicts this pricing. — [mktsoftware.vn](https://mktsoftware.vn/tool-reup-video); [mktcare.net](https://mktcare.net/phan-mem-mkt-viral-2/)
- **ATP Software, Simple Tikdown**: downloads whole TikTok, Douyin or Kuaishou channels "không logo" (without watermark) and reposts them to FB/IG Reels, YouTube Shorts or TikTok. 1,500,000 VND for 3 months, 3,500,000 VND for 1 year. — [atpsoftware.vn/bang-gia](https://atpsoftware.vn/bang-gia)
- **V-Shorts** (phanmemtudong.net): bulk-uploads prepared video folders to many accounts and fills in caption and hashtags automatically. No price in the snippet. — [phanmemtudong.net](https://phanmemtudong.net/phan-mem-tiktok-tu-dong-vshorts)
- **taovideoai.com** advertises "Tạo video AI chỉ trong 15 giây – video triệu view không cần quay" (AI video in 15 seconds, million-view videos without filming) for TikTok, YouTube and Facebook. — [taovideoai.com](https://taovideoai.com/)
- **Hiddle** (Vietnamese-localized page): TikTok multi-account management with AI copywriting and RPA auto-posting. — [hiddle.net](https://www.hiddle.net/vi/use-cases/tiktok)
- A YouTube tutorial is titled "Tool Tự Đăng Video TikTok Hàng Loạt – Lên Lịch Tự Động 100 Video/Ngày" (tool that auto-posts TikTok in bulk, schedules 100 videos a day). — [YouTube](https://www.youtube.com/watch?v=XWLMAV8Af5o)
- A Vietnamese blog (w5g.io.vn) describes a DIY workflow: one topic → 100 titles → filter → scene script → TTS → images → assemble → store → posting queue. — [w5g.io.vn](https://w5g.io.vn/ai-tao-video-dang-tiktok-tu-1-cau-lenh-duy-nhat/)
- Chrome extensions for batch Veo on Google Flow:
  - "Tiến Minh Auto Flow Pro": prompt queue in a side panel; the free tier gives 50 videos/day.
  - "Flow Master Auto Veo3 AI": batch text-to-video and image-to-video with auto-download; Vietnamese UI.
  - "VEO3 Auto" and "VEO Automation".
  - [Chrome Web Store](https://chromewebstore.google.com/detail/ti%E1%BA%BFn-minh-auto-flow-pro/cdiniklmmackfcccfaleieajhbocphhe); [extscope](https://extscope.org/extension/paciebadikcaalknhocbdmmllmemofnb); [Chrome Web Store](https://chromewebstore.google.com/detail/veo-automation-auto-veo-o/fnmijgmnjpealnnadjpjilaanhhambeb)
- The MMO marketplace Tạp hóa MMO sells "Tiktok Video Reup – Lách bản quyền video Tiktok" (TikTok reup, copyright evasion), and prices vary widely. — [taphoammo.net](https://taphoammo.net/gian-hang/reup-tiktok-video-multiple-lach-ban-quyen-video-tiktok_588726)
- Earlier report (unchanged): vnrom.net covered MoneyPrinterTurbo in May 2026. MoneyPrinterTurbo ships the voices `vi-VN-HoaiMyNeural` and `vi-VN-NamMinhNeural`, re-confirmed in azure_voices.json on 4 Nov 2026. — [vnrom.net](https://vnrom.net/2026/05/moneyprinterturbo-tao-video-ngan-chuan-tiktok-va-youtube-shorts-bang-ai-chi-voi-keyword/); [azure_voices.json](https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/main/app/services/data/azure_voices.json)

**Commercial 13-feature mapping (from snippets; mostly Unknown)**
- Xây kênh AI:
  - Yes: (2) AI video, (6) TikTok auto-post, (11) Vietnamese.
  - Partial: (7) batch scheduling.
  - Partial or Unknown: (13).
  - Yes as a web SaaS for (12) server mode.
  - Unknown: (1), (3), (4), (5), (8), (9), (10); YouTube and Facebook posting also Unknown.
  - [phanmemmkt.net](https://phanmemmkt.net/dang-tiktok-tu-dong/)
- MKT Viral, Simple Tikdown and V-Shorts:
  - Yes: (6)-style reposting/upload and (13) batch.
  - Windows desktop for (12): Unknown, not confirmed in snippets.
  - No: (1)–(3), because they reuse existing videos rather than generate new ones.
  - [mktsoftware.vn](https://mktsoftware.vn/tool-reup-video); [atpsoftware.vn](https://atpsoftware.vn/bang-gia); [phanmemtudong.net](https://phanmemtudong.net/phan-mem-tiktok-tu-dong-vshorts)

### Inferences
- Vietnamese open source now covers features (1)–(4) and (11) end to end, often in better quality than MoneyPrinterTurbo for Vietnamese: VieNeu voices, Whisper word-level karaoke, −14 LUFS. **The empty space is still the operations layer**: (6) direct posting to all three platforms, (7) rotation and dedup, (8) error-log dashboard, (9) CapCut for AI-generated videos, and (12) Windows packaging. Only ai-short-video-studio comes close on (8), and only VideoLocalizer and capcut-auto do (9).
- The dominant Vietnamese pattern is to package the generator as a **Claude Code or Antigravity skill**, with a human in the loop and no publishing step. That makes our cron + publisher + dashboard design a different product category, not a competitor of these repos.
- Commercial "hàng loạt" (mass) tools are mostly reup and anti-detection tools. Several advertise "lách bản quyền" or "không vi phạm bản quyền" (copyright evasion, or claims of no copyright violation). **Flag these as gray or black-hat**: re-uploading others' videos with flips or zooms still infringes copyright and platform rules. Our positioning should explicitly distance itself from them.
- Several pipelines automate the consumer UIs of Google Flow or Google Labs through extensions or logged-in tabs (Wevideo2, ntd-labs, the Flow extensions). That is a ToS and fragility risk, and it should not be copied as a provider pattern.

### Gaps
- Full feature lists and VND prices for Xây kênh AI, V-Shorts, taovideoai.com and Hiddle. The hosts were blocked and snippets gave no prices.
- Whether any Vietnamese commercial tool posts via the official TikTok, YouTube or Meta APIs, or via browser automation. Not found.
- "Ninja" tools: searches returned only Tik.ninja, a TikTok viewer, and an unpriced "Tool Nuôi Nick Tiktok" on Behance. Simplize appears to be a stock-analysis platform. No video tool under that name was found.
- Star counts of these Vietnamese repos are small (0–226). Adoption and real-world reliability are unknown.

## 2. Communities, practices, and reported failures or bans

### Takeaway
Vietnamese "video AI hàng loạt" (mass AI video) practice splits two ways:
- **Builder communities** on GitHub, Facebook and Zalo share skills, templates and TTS tips around repos such as Cuongyd196's.
- **MMO / "kiếm tiền" circles** push reup, multi-account farming with proxies, and income claims.

The failures most often reported are YouTube demonetization under the "inauthentic content" (formerly "repetitious content") policy and TikTok shadowbans for duplicate content or shared IPs. Voz, Viblo and Kipalog yielded nothing citable.

### Cited Findings
- Cuongyd196 runs a Facebook group ([facebook.com/groups/1010029065373486](https://www.facebook.com/groups/1010029065373486/)) and a Zalo group "cho các bạn trao đổi về Làm Video với AI" (for people to discuss making videos with AI). His demos are published on YouTube Shorts, Facebook Reels and TikTok @cuongit96. — [auto-video-gen README](https://github.com/Cuongyd196/auto-video-gen)
- Fx Studio publishes a Vietnamese video series "Xưởng video AI" (AI video workshop) alongside mini-video-workspace. — [GitHub](https://github.com/fx-studio/mini-video-workspace)
- A Tinhte thread (2026) on configuring proxies for TikTok "nuôi nick" (account farming) says duplicate network signals trigger an immediate "Shadowban". It also says 100% reup content or copyrighted audio/images is a case "proxy không thể cứu được" (proxies cannot save you). — [tinhte.vn](https://tinhte.vn/thread/cau-hinh-proxy-nuoi-nick-tiktok-chong-shadowban-hieu-qua-2026.4164168/)
- YouTube renamed "repetitious content" to "inauthentic content" effective 15 Jul 2025, with the same definition: mass-produced or repetitive content. Channels that keep posting it may be removed from YPP. — [Search Engine Journal](https://www.searchenginejournal.com/youtube-monetization-update-spam-not-reaction-channels/550755/); [Social Media Today](https://www.socialmediatoday.com/news/youtube-clarifies-monetization-update-inauthentic-repeated-content/752892/); [Gulf News](https://gulfnews.com/technology/youtube-updates-monetisation-policies-ai-and-repetitive-content-ban-begins-july-15-1.500192660)
- YouTube's Vietnamese help page says the whole channel may lose monetization if it has violating videos, or "nếu chúng tôi không thể xác định rõ ràng rằng bạn là người đã tạo ra nội dung đó" (if YouTube cannot clearly determine you created the content). — [YouTube Trợ giúp](https://support.google.com/youtube/answer/1311392?hl=vi)
- Vietnamese press framing:
  - Znews asked "Dấu chấm hết cho các kênh YouTube tạo video AI?" (the end for AI-video YouTube channels?). It said AI voice without personal commentary may be ineligible, but that it is unclear which videos are affected. — [Znews](https://znews.vn/dau-cham-het-cho-cac-kenh-youtube-tao-video-ai-post1567548.html)
  - PVM covered the 15/7/2025 tightening. — [PVM](https://pvm.com.vn/youtube-se-han-che-kiem-tien-va-ngung-phan-phoi-video-tao-bang-ai-tu-15-7-2025/)
  - E-Techreview published "'Bão' tắt kiếm tiền YouTube 2026: Từ 'Nội dung trùng lặp' sang 'Nội dung không trung thực'" (the 2026 demonetization "storm": from "duplicate content" to "inauthentic content"). — [e-techreview.com](https://e-techreview.com/2026/01/09/bao-tat-kiem-tien-youtube-2026-tu-noi-dung-trung-lap-sang-noi-dung-khong-trung-thuc-nhung-dieu-creator-can-biet/); [ninhdon.com](https://ninhdon.com/noi-dung-khong-trung-thuc/)
- VnReview reported, citing a Kapwing report, that YouTube deleted AI-video channels with more than 4.7 billion total views in early 2026, and that some manual creators were wrongly demonetized. This is a forum repost, and the figure was not verified at the source. — [VnReview](https://vnreview.vn/threads/soc-youtube-da-xoa-cac-kenh-co-video-ai-voi-tong-luot-xem-hon-4-7-ty-luot.83469/)
- Finhay claims "90% kênh video AI bị tắt kiếm tiền" (90% of AI-video channels demonetized) without evidence, so it is unreliable. — [Finhay](https://www.finhay.com.vn/en/cach-kiem-tien-youtube-bang-video-ai)
- VnExpress (Jul 2025): Vietnamese creators earn "thousands of dollars monthly" from AI faceless videos for YouTube and TikTok, which a reviewer attributes to cheap, fast production. — [VnExpress International](https://e.vnexpress.net/news/tech/tech-news/vietnamese-content-creators-earn-thousands-of-dollars-monthly-from-ai-generated-faceless-videos-4911697.html)
- VnExpress also reports user frustration with AI "trash" flooding social media. — [VnExpress International](https://e.vnexpress.net/news/tech/tech-news/users-grow-frustrated-as-ai-generated-trash-floods-social-media-4914474.html)
- VietnamNet: within a month of Veo 3's release, Vietnamese social media was flooded with AI comedic videos. — [VietnamNet](https://vietnamnet.vn/en/ai-filmmaking-with-veo-3-creative-leap-or-recycled-tropes-2431801.html)
- VnEconomy warns about the AI content-creation trend pushed by startups. — [VnEconomy](https://vneconomy.vn/canh-giac-voi-trao-luu-sang-tao-noi-dung-bang-ai-cua-cac-cong-ty-khoi-nghiep.htm)
- **Scam-like marketing flags**:
  - A Vietnamese course is titled "$40.512 với 1 kênh shorts giấu mặt bằng cách ăn cắp nội dung" ($40,512 from one faceless Shorts channel by stealing content). — [lilys.ai](https://lilys.ai/notes/vi/youtube-shorts-automation-20251230/faceless-shorts-stolen-content-course)
  - A "700 monetizable shorts in 18 minutes" video summary circulates on a Vietnamese page. — [dicloak.com/vn](https://dicloak.com/vn/video-insights-detail/i-made-700-monetizable-youtube-shorts-for-faceless-channel-in-18-minutes-using-ai-automation)
  - Tools claim "0 tài khoản bị khóa" (0 accounts banned) with virtual devices, per the search summary of "Heidou".
  - Vendors claim their reup tools are "không vi phạm bản quyền" (no copyright violation). — [fptshop.com.vn](https://fptshop.com.vn/tin-tuc/thu-thuat/tool-reup-tiktok-khong-vi-pham-ban-quyen-176293); [mktsoftware.vn](https://mktsoftware.vn/tool-reup-video)
- TikTok in Vietnam:
  - VnReview reports TikTok is rolling out AI-content identification for Vietnamese users, including "Quản lý chủ đề" (Manage topics) to dial down AI content in the feed. Timing is unclear. — [VnReview](https://vnreview.vn/threads/tiktok-ra-mat-loat-giai-phap-giup-nguoi-dung-viet-nhan-biet-noi-dung-ai.87478/)
  - An older VnReview post says unlabeled AI videos may be removed. — [VnReview](https://vnreview.vn/threads/tiktok-se-tu-dong-gan-nhan-noi-dung-tao-bang-ai.40739/)
  - A Kapwing survey reported by Doanh nghiệp Hội nhập (25 Jun 2026) says nearly 60% of TikTok videos are AI-generated. — [doanhnghiephoinhap.vn](https://doanhnghiephoinhap.vn/gan-60-video-tren-tiktok-la-noi-dung-tao-bang-ai-141033.html)

### Inferences
- What Vietnamese creators actually do for "video AI hàng loạt":
  - Generate with Veo / Google Flow batch extensions or MoneyPrinterTurbo-style pipelines.
  - Voice with Edge HoaiMy/NamMinh or Vbee.
  - Spread output across many TikTok and Facebook accounts with proxies.
  - Or reup and translate Douyin/TikTok content with flip, zoom and speed transforms.
- The legitimate, sustainable version of this is what our design already favors: original scripts, moderate cadence, labeling, and human review.
- Reported failures center on duplicate or reup detection and mass-produced sameness, not on AI use as such. Topic rotation, dedup and per-video variety in our scheduler therefore directly address the documented failure mode.

### Gaps
- No Voz, Viblo, Kipalog or Spiderum threads surfaced through the US-only search engine, and direct fetches were blocked. The forum sentiment on these sites is unknown.
- No official TikTok document was found confirming that AI videos are excluded from For You in Vietnam as "nội dung không nguyên bản" (unoriginal content). Only marketing blogs claim it ([dicloak](https://dicloak.com/vn/blog-detail/tiktok-is-changing--heres-how-to-get-views-in-2025)).
- No named, verifiable Vietnamese channel demonetization case studies were found.

## 3. Vietnamese TTS options: quality, pricing, licenses

### Takeaway
For a commercial product, the best open option in Nov 2026 is **VieNeu-TTS v3 Turbo**: Apache-2.0 per its README, 10k+ hours of training data, CPU real-time, an OpenAI-compatible API and a Windows installer. **ZeroTTS** (MIT code and weights) is a newer contender. Most other Vietnamese open models are **non-commercial**: viXTTS (CPML), V-TTS, VietTTS weights and the hynt F5-TTS models. zalopay's F5 fine-tune is CC-BY-4.0. Among cloud options, Gemini-TTS lists vi-VN as GA, and Vbee is the main local vendor with published per-character pricing (500 VND per 1,000 characters on its custom plan). Edge TTS is free but unofficial.

### Cited Findings
- **Edge TTS**: free, with no key needed, and the default in Vietnamese repos (auto-video-gen, Wevideo2, auto-video-maker). The Vietnamese voices are `vi-VN-HoaiMyNeural` and `vi-VN-NamMinhNeural`. — [azure_voices.json](https://raw.githubusercontent.com/harry0703/MoneyPrinterTurbo/main/app/services/data/azure_voices.json); [auto-video-gen](https://github.com/Cuongyd196/auto-video-gen)
  - It is not an official, documented Microsoft API and may be changed or restricted without notice. Commercial use is a gray area, and Azure AI Speech is the supported route. — [promptquorum review](https://www.promptquorum.com/power-local-llm/openai-edge-tts-review); [edge-tts-browser README](https://cdn.jsdelivr.net/npm/edge-tts-browser@1.0.1/README.md); [wikidocs](https://wikidocs.net/blog/@jaehong/9554/)
- **Google Gemini-TTS**: the Cloud docs list Vietnamese (vi-VN) as **GA**. Gemini 3.1 Flash TTS voices are all in Preview. — [Google Cloud docs](https://docs.cloud.google.com/text-to-speech/docs/gemini-tts)
- **OpenAI TTS and ElevenLabs**: no Vietnamese-specific quality review was found. A general comparison puts ElevenLabs ahead of OpenAI on pronunciation accuracy (81.97% vs 77.30%), but does not say which languages were tested. OpenAI TTS has no user voice cloning. — [unrealspeech](https://unrealspeech.com/compare/openai-text-to-speech-vs-elevenlabs); [vips comparison](https://learn.engineering.vips.edu/compare/elevenlabs-multilingual-v2-vs-openai-tts-hd)
- **Vbee AIVoice** (Vietnamese vendor):
  - Custom plan per the April 2025 help-center update: 500 VND per 1,000 characters; minimum 5M and maximum 999M characters; 1-year term only; +39,000 VND per extra device and +100,000 VND per cloned voice; 10/20/30% discounts at 15M, 30M and 60M characters. — [help.vbee.vn](https://help.vbee.vn/docs/thong-bao/ban-cap-nhat-thang-04-2025)
  - The App Store lists Standard at $6.49/month, VIP at $15.49/month and 1M characters for $8.29. — [App Store](https://apps.apple.com/app/id6737223131)
  - A third-party site reports monthly tiers of 199k, 399k and 799k VND (unverified). — [FitGap](https://us.fitgap.com/products/059235/vbee-ai-voice-studio)
  - Vbee is integrated by auto-video-gen and whiteboard-video. — [whiteboard-video](https://github.com/Cuongyd196/whiteboard-video)
- **FPT.AI TTS**: the pricing page gives no public per-character price ("Please contact for detailed pricing", hotline 1900 638 399). Voices are male and female across the three regional accents. — [docs.fpt.ai](https://docs.fpt.ai/docs/en/speech/documentation/tts-pricing); [fptshop.com.vn](https://fptshop.com.vn/tin-tuc/danh-gia/chuyen-van-ban-thanh-giong-noi-bang-ai-192547)
- **Viettel AI TTS**: the free web version is limited to 500 characters per request, per a review site, and it serves individuals and businesses. — [viettelai.vn](https://viettelai.vn/en/tin-tuc/top-5-phan-mem-doc-van-ban-thanh-giong-noi-mien-phi); [viettelstore.vn](https://viettelstore.vn/tin-tuc/giong-doc-ai)
- **LucyLab**: priced at "~25k/1M ký tự" (about 25,000 VND per 1M characters), with voice cloning and automatic SRT, per auto-video-gen. Used by alexluffy's two tools. — [auto-video-gen](https://github.com/Cuongyd196/auto-video-gen); [video-pipeline](https://github.com/alexluffy/video-pipeline)
- **VieNeu-TTS** (pnnbao97): 3,093★, pushed 2026-11-04.
  - Specs: 10,000+ hours of bilingual training, instant voice cloning and 48 kHz output.
  - Speed: CPU RTF about 0.5 (ONNX, torch-free, 12th-gen i5); GPU RTF about 0.02 batched.
  - Serving: an OpenAI-compatible `/v1/audio/speech` streaming API with Docker, and a Windows standalone installer.
  - The README states "License: Apache 2.0 (Free to use)".
  - **v4 is proprietary and API-only** (vieneu.io) because of misuse risk; v3 Turbo is the latest open version.
  - [GitHub README](https://raw.githubusercontent.com/pnnbao97/VieNeu-TTS/main/README.md)
- **ZeroTTS** (zeroweight-ai): 320★, pushed 2026-09-17. "Code and weights: MIT"; the bundled MOSS codec is Apache-2.0. It does zero-shot cloning from 3 s, CPU RTF 0.5 with about 70 ms to first audio, and reads dates and numbers without a normalizer. It claims "4× fewer word errors than the next open model" on its own ZeroBench-TTS (vendor-run benchmark). — [GitHub](https://github.com/zeroweight-ai/ZeroTTS)
- **V-TTS** (tronghieuit): 385★. 74.8M parameters, CPU RTF about 0.24, Windows .exe v1.0.5 (April 2026). **CC BY-NC 4.0, non-commercial**. — [GitHub](https://github.com/tronghieuit/v-tts)
- **viXTTS** (capleaf, fine-tuned from XTTS-v2.0.3 on viVoice): **Coqui Public Model License, non-commercial** use of the model *and its outputs*. The demo code is MPL-2.0 (517★), and local use is designed for Ubuntu/WSL2. — [HF model card mirror](https://huggingface.co/yukiakai/viXTTS/blame/main/README.md); [thinhlpg/vixtts-demo](https://github.com/thinhlpg/vixtts-demo)
- **VietTTS** (dangvansam): code is Apache-2.0, **pre-trained models CC BY-NC**. — [Hugging Face](https://huggingface.co/dangvansam/viet-tts); [PyPI](https://pypi.org/project/viet-tts/)
- **F5-TTS Vietnamese**:
  - hynt 1000h: CC-BY-NC-SA-4.0 for research use, and it asks users to disclose AI audio; the 150h variant is gated.
  - **zalopay/vietnamese-tts: CC-BY-4.0**, trained on 200+ hours of public Vietnamese voice and YouTube data.
  - toandev mirror: CC-BY-NC-4.0.
  - nguyenthienhy/F5-TTS-Vietnamese repo: MIT, 175★.
  - [hynt](https://huggingface.co/hynt/F5-TTS-Vietnamese-ViVoice/blob/main/README.md); [zalopay](https://huggingface.co/zalopay/vietnamese-tts); [toandev](https://toandev-f5-tts-vietnamese.hf.space/); [nguyenthienhy](https://github.com/nguyenthienhy/F5-TTS-Vietnamese)
- **NTT123/vietTTS**: MIT, 260★, last push 2023 (dormant). — [GitHub](https://github.com/NTT123/vietTTS)
- Ecosystem around VieNeu:
  - NguyenSiTrung/VieNeuTTSApp: an offline desktop app, 74★.
  - tqk2811/local-tts-server: a local HTTP server for viXTTS, F5 and VieNeu.
  - anpc849/real-time-video-subs: Vietnamese dubbing with faster-whisper, Demucs, an LLM and VieNeu.
  - [GitHub search, 4 Nov 2026](https://github.com/search?q=vieneu+tts&type=repositories)

### Inferences
- For our project, a sensible default chain is Edge TTS (free, fragile), then VieNeu v3 Turbo or ZeroTTS locally (commercial-safe per README; HF weight cards still to verify), then Gemini-TTS, Vbee or ElevenLabs as paid fallbacks.
- Avoid shipping viXTTS, V-TTS or VietTTS weights in a monetized pipeline, because their licenses exclude commercial use of the outputs.
- MotionFly's pattern of Whisper-scoring the TTS output for mispronunciation is a cheap quality gate worth adopting for Vietnamese tones.

### Gaps
- Hugging Face was blocked, so VieNeu v3 Turbo's **weights** license on HF could not be checked against the README's Apache-2.0 claim.
- No Vietnamese blind-listening comparison of Edge, Gemini, OpenAI, ElevenLabs, FPT, Viettel and Zalo was found.
- Current FPT.AI, Viettel AI and Zalo AI TTS prices are unpublished or not found. VAIS was not found.

## 4. Vietnamese LLM content quality and caption fonts/diacritics

### Takeaway
There is no citable head-to-head of GPT, Claude and Gemini on Vietnamese short-video scripts. Vietnamese builders mostly use Claude Code, Antigravity/Gemini or DeepSeek for scripts, and local Ollama Qwen for privacy. Local Vietnamese models (Vistral, SeaLLM, Arcee-VyLinh) are small 3–7B models with modest VMLU scores. Vietnamese diacritics in burned-in captions fail mainly because system fonts lack the glyphs (fontconfig/libass fallback). The documented fix is bundling Noto Sans or Be Vietnam Pro.

### Cited Findings
- VMLU (Zalo AI + JAIST) has 10,880 multiple-choice questions across 58 subjects. Leaderboard snapshot: VNPTAI.IO-14B 55.83, SeaLLM-7B-v2.5 53.30, Vistral-7B-Chat 50.07, SeaLLM-7B-v2 45.79. These are 2024 entries. — [VMLU GitHub](https://github.com/ZaloAI-Jaist/VMLU/); [ACL 2025](https://aclanthology.org/2025.acl-long.563)
- The SeaLLM-7B-v2 card reports VMLU 45.46, "competitive with" Vistral-7B. This conflicts slightly with the leaderboard ordering. — [Hugging Face](https://huggingface.co/SeaLLMs/SeaLLM-7B-v2/blob/fc81c0e59108e78c6eaeae4cdd60c7a033419f6a/README.md)
- Arcee-VyLinh (around Oct 2024): a 3B Vietnamese model built on Qwen2.5-3B with 32K context, trained with ORPO/DPO, and evaluated on Vietnamese m-ArenaHard with Claude 3.5 Sonnet as judge. The card warns it may hallucinate on culture-specific content. — [Hugging Face](https://huggingface.co/arcee-ai/Arcee-VyLinh)
- LLMs used by Vietnamese pipelines:
  - Claude Code / Antigravity, which "viết lời bình tiếng Việt chuẩn ngữ âm" (writes phonetically correct Vietnamese narration). — [auto-video-gen](https://github.com/Cuongyd196/auto-video-gen)
  - DeepSeek. — [auto-video-maker](https://github.com/andyluu98/auto-video-maker)
  - Chato1 or Gemini. — [video-pipeline](https://github.com/alexluffy/video-pipeline)
  - Ollama `qwen3.5:4b` by default, with Claude/OpenAI optional. Here "lời gốc được khóa bằng code" (the original script text is locked by code), so the LLM only writes image prompts and cannot rewrite the narration. — [ai-short-video-studio](https://github.com/tanthanh381/ai-short-video-studio)
  - Gemini. — [Bookie](https://github.com/haingt-dev/Bookie)
- A "Normalize TTS" step between script and TTS is used to make numbers and abbreviations speakable. — [video-pipeline](https://github.com/alexluffy/video-pipeline)
- ZeroTTS claims it reads forms like `31/12/2026` without a normalizer. — [ZeroTTS](https://github.com/zeroweight-ai/ZeroTTS)
- Diacritics:
  - mini-video-workspace: fonts on Linux/Windows "có thể thiếu dấu tiếng Việt, khi đó cài font Noto Sans" (may lack Vietnamese diacritics; install Noto Sans). — [GitHub](https://github.com/fx-studio/mini-video-workspace)
  - ai-short-video-studio's worker bundles Noto Sans. — [GitHub](https://github.com/tanthanh381/ai-short-video-studio)
  - FFmpeg/libass picks fonts via fontconfig by registered name and silently falls back (for example to DroidSansFallback) when glyphs are missing. — [FFmpeg trac #9227](https://trac.ffmpeg.org/ticket/9227); [UMS forum](https://www.universalmediaserver.com/forum/viewtopic.php?p=26063)

### Inferences
- Pin a bundled Vietnamese-complete font and pass it to libass via `fontsdir`. Normalize Unicode to NFC before captioning and TTS, so that precomposed and combining diacritics do not break word timing or CapCut style ranges (UTF-16 offsets, per the earlier report). Add a TTS text normalizer for numbers, dates and units.
- Locking the narration text and letting the LLM only write visual prompts, as ai-short-video-studio does, is a useful guard against LLMs "improving" Vietnamese wording after review.

### Gaps
- No source compared GPT, Claude and Gemini Vietnamese script quality, idiom or tone. No newer (2025–2026) VMLU leaderboard snapshot was retrieved.
- No source documented diacritics bugs specifically in MoneyPrinterTurbo or CapCut with Vietnamese.

## 5. Vietnamese regulatory and platform context for automated posting

### Takeaway
Decree 147/2024 (effective 25 Dec 2024) means **only phone-number-authenticated accounts can post** on social networks in Vietnam, which constrains anonymous multi-account farms. The **Law on AI 134/2025/QH15 (effective 1 Mar 2026)** and **Decree 142/2026/NĐ-CP (effective 1 May 2026, Art. 18)** introduce AI-content labeling. The obligation falls on the party that publishes content, at least where content simulates real people or re-creates real events. The scope is disputed across secondary sources.

### Cited Findings
- **Decree 147/2024/NĐ-CP**:
  - Effective 25/12/2024. Art. 23(3)(e) requires social networks to authenticate users via Vietnamese mobile number. Platforms got 90 days to comply.
  - Users without a VN number authenticate with a personal ID number.
  - Only authenticated accounts may post, comment or livestream.
  - Commercial livestream accounts must authenticate by personal ID.
  - [LuatVietnam](https://luatvietnam.vn/tin-van-ban-moi/tu-25-12-2024-tai-khoan-mang-xa-hoi-da-xac-thuc-bang-so-dien-thoai-moi-duoc-dang-bai-186-99855-article.html); [VnEconomy](https://vneconomy.vn/tu-ngay-25-12-tai-khoan-mang-xa-hoi-phai-xac-thuc-so-dien-thoai-moi-duoc-dang-bai.htm); [VOV](https://vov.vn/xa-hoi/tu-hom-nay-nguoi-dung-mxh-phai-xac-thuc-moi-duoc-dang-bai-binh-luan-post1144421.vov); [VietnamNet](https://vietnamnet.vn/xac-thuc-tai-khoan-bang-so-dien-thoai-moi-duoc-dang-livestream-facebook-2341051.html)
- **Law on AI (Luật Trí tuệ nhân tạo 134/2025/QH15)**: effective 01/03/2026. — [VnReview](https://vnreview.vn/threads/luat-tri-tue-nhan-tao-chinh-thuc-co-hieu-luc-tu-01-3-dinh-hinh-hanh-lang-phap-ly-cho-ai-va-bao-ve-nguoi-dung.79722/latest); [Luật Minh Khuê](https://luatminhkhue.vn/yeu-cau-bat-buoc-doi-voi-noi-dung-tao-boi-ai-tu-1-3-2026.aspx); [Phong Vũ](https://phongvu.vn/cong-nghe/luat-ai-moi-tu-1-3-phai-gan-nhan-noi-dung-do-ai-tao-ra/)
- **Decree 142/2026/NĐ-CP**: guides the AI Law and is effective 01/05/2026. **Art. 18** covers notification and visible labeling of AI-created or AI-edited content. — [hethongphapluat](https://hethongphapluat.com/nghi-dinh-142-2026-nd-cp-huong-dan-luat-tri-tue-nhan-tao.html); [LSVN](https://lsvn.vn/thong-bao-va-gan-nhan-nhan-biet-noi-dung-do-ai-tao-ra-the-nao-a172678.html)
  - Scope, per Luật Long Phan: labeling is mandatory for the deployer when content **simulates a real person's appearance or voice, or re-creates real events** (cl. 2). Other outlets present it as covering all AI content. **Conflicting secondary readings.** — [Luật Long Phan](https://luatlongphan.vn/?p=90894); contrasted with [Phong Vũ](https://phongvu.vn/cong-nghe/luat-ai-moi-tu-1-3-phai-gan-nhan-noi-dung-do-ai-tao-ra/)
  - Form (cl. 3): the label must be clear and easy to recognize. It can be shown on the content itself or in the title or description.
  - Responsibility: the creator or editor supplies the information, and **the party making the content public performs the labeling**.
  - The Ministry of Science and Technology issues technical guidance.
  - Cl. 4 lists four exemption groups, whose details were not retrieved.
  - [Doanh nhân & Pháp luật](https://doanhnhan.baophapluat.vn/gan-nhan-hien-thi-doi-voi-noi-dung-do-ai-tao-ra-phai-bao-dam-cac-yeu-cau-nao-d87d1db9.html); [Vietnam Law Magazine](https://vietnamlawmagazine.vn/mandatory-labels-required-for-ai-generated-content-79501.html)
  - Transition: AI systems operating before 01/03/2026 have 12–18 months, ending 01/03/2027 to 01/09/2027. Businesses lobbied to narrow labeling in the draft, where it was numbered Art. 19. — [Luật Minh Khuê](https://luatminhkhue.vn/quy-dinh-bat-buoc-gan-nhan-minh-bach-cho-noi-dung-tao-bang-ai-tu-1-3-2026.aspx); [VnEconomy](https://vneconomy.vn/doanh-nghiep-de-xuat-dieu-chinh-quy-dinh-gan-nhan-noi-dung-do-ai-tao-ra.htm)
- Platform-side labeling: TikTok auto-labels AI content and has said unlabeled AI videos may be removed. VnReview also tags articles on YouTube auto-labeling AI. — [VnReview TikTok](https://vnreview.vn/threads/tiktok-se-tu-dong-gan-nhan-noi-dung-tao-bang-ai.40739/); [VnReview tag](https://www.vnreview.vn/tags/youtube-tu-dong-gan-nhan-ai/)

### Inferences
- An automated publisher targeting Vietnam should do three things:
  - Set the platforms' AI-content disclosure flags.
  - Add a visible "Nội dung có sử dụng AI" (contains AI-generated content) label in the description or on-screen by default. This is likely mandatory for cloned voices or real-event re-creations, which most "tin tức" and news-explainer formats are.
  - Assume one authenticated (phone-verified) account per channel rather than account farms.
- Voice cloning of real people (VieNeu, ZeroTTS, viXTTS) falls squarely in the labeling scope.

### Gaps
- The full text of Decree 142/2026 Art. 18 cl. 4 exemptions and the penalty provisions (for example, administrative fines) was not retrieved. Primary text (Công báo / chinhphu.vn) was not accessible.
- Whether "deployer" obligations reach individual creators posting via an automated tool, or only organizations, is unresolved in the snippets.
