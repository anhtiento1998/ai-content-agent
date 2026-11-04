# Open-source multi-platform social video publishing and scheduling tools (as of Nov 2026), compared with ai-content-agent

Research date: 2026-11-04. Star counts are what the GitHub repo page showed when fetched on that date. Network limits in this session: the GitHub REST API (`gh api`, api.github.com), docs.postiz.com, developers.tiktok.com and cdn.jsdelivr.net could not be reached. So exact last-commit dates, release dates and Postiz/TikTok doc pages were not read directly. Where only search snippets were available, that is stated.

Feature numbers used below (from the brief): (1) LLM storyboard, (2) per-scene AI visuals, (3) TTS voice-over, (4) automatic FFmpeg editing, (5) auto thumbnail, (6) auto-publish to YouTube Shorts/TikTok/Facebook Page, (7) scheduling/cron with topic rotation and dedup, (8) web dashboard with live job progress/history/error log, (9) CapCut draft export, (10) pluggable provider/publisher architecture, (11) Vietnamese content support, (12) Windows desktop app and/or server/self-host, (13) batch/mass production: many videos unattended (bulk upload/queue, CSV import, per-day posting caps, multi-account).

---

## Q1. Which open-source schedulers/publishers and uploader libraries exist, how capable are they, and which of our 13 features do they cover?

### Takeaway
Postiz (AGPL-3.0, about 40.9k stars, official OAuth APIs, public API + MCP + n8n node, Docker self-host) is the only mature, actively developed open-source multi-platform scheduler that covers YouTube, TikTok, Facebook and Instagram and can be driven by a program. Mixpost (MIT Lite; TikTok/YouTube/Reels only in the paid Pro edition) is the main alternative. The uploader libraries (social-auto-upload, tiktok-uploader, autotok) avoid platform app audits by driving a logged-in browser session or cookies. That carries ToS and ban risk. None of these tools generates videos, so they cover only features 6, 7 (partly), 8 (partly), 10, 12 and 13 of our project.

### Cited Findings

**Postiz — gitroomhq/postiz-app** ([GitHub](https://github.com/gitroomhq/postiz-app))
- Stars 40.9k, forks 7.8k, about 3,524 commits, license AGPL-3.0, tagline "The ultimate agentic social media scheduling tool" — [GitHub](https://github.com/gitroomhq/postiz-app). One listing claims Apache 2.0, but the repo page says AGPL-3.0 — [search summary citing G2/listing](https://www.g2.com/products/postiz/). Treat AGPL-3.0 (from the repo itself) as correct.
- Stack: pnpm monorepo, Next.js (React), NestJS, Prisma (PostgreSQL by default), Temporal (workflow engine), Redis, Resend for email — [GitHub](https://github.com/gitroomhq/postiz-app).
- Platforms listed under "Schedule posts to": Instagram, YouTube, Dribbble, LinkedIn, Reddit, TikTok, Facebook, Pinterest, Threads, X, Slack, Discord, Mastodon, Bluesky — [GitHub](https://github.com/gitroomhq/postiz-app). A Railway template markets it as "for 30 platforms" — [Railway](https://railway.com/deploy/postiz-open-source-social-media-scheduler-for-30-platforms--deploy-postiz).
- Features in both Cloud and self-hosted: "Scheduling, calendar views, cross-posting, repeated posts, post comments & delays, sets, signatures". Analytics are included, but self-hosters need their own app credentials with analytics scopes. Team members can "collaborate, comment, and schedule posts". No explicit approval workflow is described — [GitHub](https://github.com/gitroomhq/postiz-app).
- Programmatic access: public API and webhooks (docs.postiz.com/public-api), "MCP, CLI, Claude / ChatGPT / Codex / OpenClaw / Cursor connectors", an MCP server, an "AI Agents CLI", an N8N custom node and a Make.com integration — [GitHub](https://github.com/gitroomhq/postiz-app).
- AI features: "AI Copilot, AI images, AI videos", AI video clipping, and a "Smart Agent" that needs an LLM key on self-hosted installs — [GitHub](https://github.com/gitroomhq/postiz-app).
- Self-host: "Deploy with Docker / Coolify / Railway / any VPS", with docker-compose files in the repo. No desktop app is mentioned — [GitHub](https://github.com/gitroomhq/postiz-app).
- Official APIs only: "Postiz hosted service uses official, platform-approved OAuth flows" and "Postiz does not automate or scrape content from social media platforms". Self-hosters must create their own developer apps on each platform and go through each platform's approval — [GitHub](https://github.com/gitroomhq/postiz-app).
- Version conflict: Railway templates are pinned to different versions (v2.11.3 and v2.25.1) — [search summary of Railway pages](https://railway.com/deploy/deploy-postiz). The current release could not be verified because the GitHub releases list was empty in the captured page.
- Self-hosted tier reportedly has no connected-channel restrictions — [search summary, Railway/listing](https://railway.com/deploy/postiz-open-source-social-media-scheduler-for-30-platforms--deploy-postiz).
- Public API limit: the official docs (seen only as a search snippet) say the hourly limit applies only to the create-post endpoint, at 90 requests/hour self-hosted (100 on Cloud). Each API call counts as one request even if it carries several posts, so batching posts in one call is recommended. Self-hosters can change it with the `API_LIMIT` env var, and going over returns HTTP 429 — [Postiz docs intro (snippet)](https://docs.postiz.com/public-api/introduction.md). Conflicting: a Mintlify-hosted page describes a global 30 requests/hour per API key across all endpoints — [Mintlify](https://www.mintlify.com/gitroomhq/postiz-app/api/rate-limits). An API Evangelist spec says no rate-limit headers are returned — [API Evangelist](https://raw.githubusercontent.com/api-evangelist/postiz/refs/heads/main/rate-limits/postiz-rate-limits.yml).
- CSV bulk import: a search for Postiz CSV/bulk import returned only other products (PostFast 200 posts per CSV, SocialBu up to 2000, ContentStudio/Zernio/Late up to 500) — [PostFast](https://help.postfa.st/publishing-scheduling/bulk-import-posts-from-csv), [Late changelog](https://getlate.dev/changelog/bulk-upload-500-social-media-posts-with-csv). No source confirms a CSV importer in Postiz.

**Mixpost — inovector/mixpost** ([GitHub](https://github.com/inovector/mixpost))
- Stars 3.9k, forks 588, MIT license, PHP/Laravel + Vite. The repo is "the Lite version of Mixpost Pro" — [GitHub](https://github.com/inovector/mixpost).
- Features listed: "Queue and Calendar Management", "Advanced Analytics" per platform, "Team Collaboration and Workspaces" with permissions, and a media library for "images, GIFs, and videos". The README mentions neither an API nor Docker. It is self-hosted "on your server" — [GitHub](https://github.com/inovector/mixpost).
- Edition split (secondary sources): Lite covers Facebook Pages, X and Mastodon. Pro/Enterprise add Instagram, LinkedIn, YouTube, TikTok, Pinterest, Threads, Bluesky and Google Business Profile — [search summary, linux-server-admin wiki](https://wiki.linux-server-admin.com/web-apps/social-media/mixpost) / [contentcreators.com](https://contentcreators.com/tools/mixpost-review).
- Reels/Shorts: a review says Mixpost supports Facebook Reels, Instagram Reels, YouTube Shorts and TikTok, including TikTok videos over 64MB — [contentcreators.com](https://contentcreators.com/tools/mixpost-review).
- Pro price conflict: $149 (2024) — [Gigazine](https://www.gigazine.net/gsc_news/en/20240309-mixpost); $269 one-time — [contentcreators.com](https://contentcreators.com/tools/mixpost-review).

**social-auto-upload — dreammis/social-auto-upload** ([GitHub](https://github.com/dreammis/social-auto-upload))
- Stars 16.1k, forks 2.7k, 343 commits, MIT (bundled Skills are MIT-0), Python 3.10–3.12 with `uv` — [GitHub](https://github.com/dreammis/social-auto-upload).
- Video platforms: Douyin, Bilibili, Xiaohongshu, Kuaishou, WeChat Channels, Baijiahao, Dayu, Alipay Life, Weibo, Hupu, TikTok, Xueqiu, YouTube, Zhihu, Facebook, Facebook Page, Instagram. Some are marked "in development" (YouTube in one column) or "experimental". TikTok is a Chrome-based implementation with no `sau` CLI command — [GitHub](https://github.com/dreammis/social-auto-upload).
- Login: a "cookie scheme". You log in once with `sau <platform> login --account <name>`, and the account name is a local alias for a saved session. YouTube login is an interactive Google sign-in in the browser, and YouTube upload "uses browser automation" rather than the official API — [GitHub](https://github.com/dreammis/social-auto-upload).
- Scheduling: there is a scheduled-publishing column. Facebook Page supports scheduled video and image posts (`--schedule`), including querying and cancelling schedules — [GitHub](https://github.com/dreammis/social-auto-upload).
- UI: the `sau_frontend/` web UI is described as legacy, and the CLI is the mainline. A Dockerfile exists. `start-win.bat` is the Windows launcher. Agent Skills are provided for Codex/OpenClaw/Claude Code — [GitHub](https://github.com/dreammis/social-auto-upload).
- The README does not discuss ToS or ban risk — [GitHub](https://github.com/dreammis/social-auto-upload).

**tiktok-uploader — wkaisertexas/tiktok-uploader** ([GitHub](https://github.com/wkaisertexas/tiktok-uploader))
- Stars 781, forks 168, MIT, "A Playwright-based automated TikTok video uploader". The repo still carries a "selenium" topic tag, which conflicts with that description — [GitHub](https://github.com/wkaisertexas/tiktok-uploader).
- Auth works by "duplicating your browser's cookies which tricks TikTok into believing you are logged in". The sessionid cookie may need to be added to cookies.txt by hand — [GitHub](https://github.com/wkaisertexas/tiktok-uploader).
- Scheduling uses TikTok's own scheduler: "at least 20 minutes in the future and a maximum of 10 days". `upload_videos` takes a list. Other features: proxies (Chrome only), covers, product links, stitch/duet/comment toggles, headless mode — [GitHub](https://github.com/wkaisertexas/tiktok-uploader).
- Caveats: "This bot is not fool proof"; uploads "will fail to upload after too many uploads" (waiting hours fixed it); "think of this more as a scheduled uploader … rather than a spam bot" — [GitHub](https://github.com/wkaisertexas/tiktok-uploader).

**autotok (formerly TiktokAutoUploader) — makiisthenes/TiktokAutoUploader** ([GitHub](https://github.com/makiisthenes/TiktokAutoUploader))
- Stars 1.2k, forks 251, AGPL-3.0, dual-licensed (commercial license available). About text: "Automatically Edits Videos and Uploads to Tiktok with CLI, Requests not Selenium". Uploads go through "TikTok's web upload API", with request signatures "computed in headless Chromium" — [GitHub](https://github.com/makiisthenes/TiktokAutoUploader).
- Interfaces: Python SDK, CLI, TypeScript SDK, Go package/binary, an MCP server for AI agents, a Docker image and a self-hosted web app. Multiple accounts (log in once per account), a proxy per account (HTTP(S)/SOCKS5), TikTok-side scheduling from 15 minutes to 30 days (some accounts limited to 10 days), and an unlimited scheduler in the web app. Settings cover visibility, comments, duet/stitch and an AI-generated label — [GitHub](https://github.com/makiisthenes/TiktokAutoUploader).
- Activity: the footer shows "© 2026" and the license says "Copyright © 2021–2026". The changelog notes an update "to TikTok's new upload endpoint" (09/12/2024) — [GitHub](https://github.com/makiisthenes/TiktokAutoUploader).
- Warnings: "Automating uploads may break TikTok's terms of service and can get accounts restricted or banned"; "Running several accounts from one IP is the quickest way to get them flagged"; failed uploads may "or may not have been posted"; and "Invalid parameters (status_code=5)" means "TikTok changed its upload API" — [GitHub](https://github.com/makiisthenes/TiktokAutoUploader).

**Automation platforms (n8n, Activepieces)**
- Official n8n.io templates for AI-video auto-posting mostly rely on paid posting services, Blotato or Upload-Post, not native APIs. Examples: VEO3 + Blotato posting to 9 platforms (community nodes, self-hosted n8n only), Veo3 → Instagram/TikTok via Blotato, Seedance + Blotato → TikTok/YouTube/Instagram — [n8n template 5035](https://n8n.io/workflows/5035), [n8n template 5338](https://n8n.io/workflows/5338), [n8n template 6669](https://n8n.io/workflows/6669) (summarised from search results).
- Upload-Post (closed SaaS) publishes n8n templates that generate metadata, save drafts to Google Sheets for client approval and auto-publish approved posts — [Upload-Post n8n templates](https://www.upload-post.com/n8n-templates).
- Postiz ships its own n8n custom node — [GitHub](https://github.com/gitroomhq/postiz-app).
- Activepieces is MIT and self-hostable. A YouTube piece exists on npm (`@activepieces/piece-youtube` v0.3.4). No TikTok piece was found — [npm](https://www.npmjs.com/package/@activepieces/piece-youtube), [YC launch](https://www.ycombinator.com/launches/HrV-activepieces-open-source-alternative-to-zapier).

**Dormant or minor OSS**
- Socioboard 5.0: a GitHub discussion titled "Dead project?" exists. The changelog wiki is dated Nov 15, 2019, and a third-party wiki calls it unmaintained, with its last release v5.0 in Nov 2019 — [GitHub discussion #425](https://github.com/socioboard/Socioboard-5.0/discussions/425), [Change Log](https://github.com/Socioboard-developers/Socioboard-5.0/wiki/Change-Log), [linux-server-admin wiki](https://wiki.linux-server-admin.com/web-apps/social-media/socioboard/history).
- TryPost is listed as an OSS alternative to Vista Social, with few details — [openalternative.co](https://openalternative.co/alternatives/vistasocial).
- An unnamed MIT FastAPI/Reflex Docker app posts to X, Telegram, Reddit and Discord only, so it does not cover video platforms — [AlternativeTo](https://alternativeto.net/software/ayrshare/?p=4).
- No open-source project was found that offers a true Ayrshare-style multi-tenant unified posting API. Postiz and Mixpost are closer to self-hosted schedulers with APIs — [search summary, AlternativeTo/Postiz compare pages](https://postiz.com/compare/ayrshare/mixpost).
- Closed SaaS context only: Ayrshare (13 platforms) — [Ayrshare](https://www.ayrshare.com); Blotato (sells an audited TikTok app) — [Blotato](https://www.blotato.com/api/tiktok); Upload-Post, Late/Zernio, Buffer, Hootsuite.

#### Feature coverage matrix (Y = Yes, P = Partial, N = No, U = Unknown)

| # | Postiz | Mixpost (Lite / Pro) | social-auto-upload | tiktok-uploader (wkaisertexas) | autotok (makiisthenes) | n8n/Activepieces templates |
|---|---|---|---|---|---|---|
| 1 Storyboard | N. AI Copilot writes post text; no scene storyboard is documented | N. Nothing documented | N. Uploader only | N | N | P. Templates call LLMs for scripts and ideas (e.g. OpenAI nodes in template 6669), but not a scene storyboard engine |
| 2 Per-scene AI visuals | P. "AI images, AI videos" listed; not per-scene | N | N | N | N | P. Templates call Veo3/Seedance for one generated clip |
| 3 TTS | U. Not mentioned | N | N | N | N | U |
| 4 FFmpeg editing | P. "AI video clipping" is listed; no captions, music, loudness or 9:16 pipeline is documented | N | N | N | P. "Automatically Edits Videos" in its About text; no details | U |
| 5 Thumbnail | U | U | U | P. Custom cover upload, not generation | U | U |
| 6 YT Shorts/TikTok/FB Page | Y. Official OAuth APIs; YouTube, TikTok, Facebook (also IG, etc.) | Lite: N (FB Pages only). Pro: Y (YouTube Shorts, TikTok, FB/IG Reels, secondary sources) | Y but unofficial. YouTube via browser automation, TikTok via Chrome, FB Page | P. TikTok only, cookies + Playwright | P. TikTok only, unofficial web API | P. Through paid SaaS (Blotato/Upload-Post) or the Postiz node |
| 7 Scheduling + topic rotation/dedup | P. Calendar, repeated posts, delays, "sets"; no topic rotation or dedup | P. Queue + calendar | P. Per-platform scheduling (FB Page `--schedule`) | P. TikTok native schedule, 20 min to 10 days | P. 15 min to 30 days on TikTok; unlimited in the web app | P. n8n cron triggers; dedup needs custom logic (e.g. Sheets) |
| 8 Dashboard w/ live progress/history/errors | P. Full web UI, calendar, analytics; no video-job progress (it has no render jobs) | P. Web UI + analytics | P. Legacy web frontend; CLI is the mainline | N | P. Self-hosted web app | P. n8n execution history UI |
| 9 CapCut export | N | N | N | N | N | N |
| 10 Pluggable providers | Y. 14+ provider integrations, public API, MCP, n8n node (internal plugin interface not verified) | P. Provider set fixed by edition | P. One module per platform plus per-platform Skills | N. Single platform | P. Multiple SDKs/MCP, TikTok only | Y. n8n/Activepieces node/piece model |
| 11 Vietnamese | U. Platforms accept any Unicode text; UI localisation not verified | U | U. Focus on Chinese platforms | U | U | U |
| 12 Desktop / self-host | Self-host Y (Docker, Coolify, Railway, VPS); desktop N | Self-host Y (Laravel); desktop N | P. `start-win.bat` on Windows, Dockerfile; no packaged desktop app | P. Python library on any OS | Y. Docker + self-hosted web app; no desktop app | Y. Self-hostable |
| 13 Batch/mass production | P. Multi-account with no channel cap on self-host; repeated posts; API create-post capped at 90 calls/hour (configurable via `API_LIMIT`) with several posts per call; no CSV import found | U. Queue exists; bulk/CSV not documented | P. Multiple accounts via `--account` aliases; no bulk queue documented | P. `upload_videos` list for batches, but "fail[s] … after too many uploads" | P. Multiple accounts + per-account proxies; warns that many accounts on one IP get flagged | P. Loops/queues are possible; caps come from the posting service |

Sources for the matrix: the Postiz, Mixpost, social-auto-upload, tiktok-uploader and autotok GitHub pages, and the n8n templates cited above.

### Inferences
- No open-source tool combines video generation with multi-platform publishing the way ai-content-agent does. The schedulers (Postiz, Mixpost) start once a finished video exists. The n8n "AI video → auto-post" templates are the closest functional analogue, but they rely on paid SaaS for both generation and posting.
- There are two separate categories. "Official API" tools (Postiz, Mixpost) are bound by app audits and quotas. "Browser/cookie" tools (social-auto-upload, tiktok-uploader, autotok) avoid audits but take on ToS and ban risk and break when platforms change their web UI or endpoints. autotok's "status_code=5 … TikTok changed its upload API" troubleshooting entry is evidence of that breakage.
- For mass production (13), the bottleneck is the platform caps (Q2), not the tools. Postiz's per-call batching and configurable `API_LIMIT` mean Postiz itself will not limit a pipeline making dozens of videos a day.

### Gaps
- Exact last-commit and release dates for every repo: the GitHub API and release pages were not reachable or were empty in the fetch.
- Whether Postiz has a CSV bulk importer: not found.
- Whether Postiz supports Vietnamese UI localisation: not verified.
- Postiz's internal provider-plugin interface, i.e. how much work a new platform takes: the source files could not be fetched (cdn.jsdelivr.net blocked).
- Mixpost Pro feature details from official docs (mixpost.app, docs.mixpost.app): only secondary sources.
- tokland/youtube-upload status (archived or maintained): no search results.
- MoneyPrinterV2 and other AI-video repos with built-in YouTube/TikTok uploaders: not verified in this pass (outside the tools-only scope and GitHub API blocked).
- n8n's license terms: not verified in this session.

---

## Q2. How do these tools handle the hard platform problems (TikTok 24h tokens, TikTok unaudited = private, YouTube unverified = private, YouTube quota, Facebook Reels API), and what caps mass posting?

### Takeaway
The platform limits are confirmed and, apart from YouTube's quota, still current. TikTok access tokens last 24h (refresh tokens 365 days, and they can rotate). Unaudited TikTok clients can only post SELF_ONLY, for at most 5 users per 24h. Audited apps are capped at about 15 Direct Posts per creator per day, shared across all apps. YouTube projects created after 28 July 2020 upload as private until they pass a compliance audit. Facebook Page Reels go through `/{page-id}/video_reels` (start → rupload → finish), with a cap of 30 API-published reels per 24h. The YouTube upload cost reportedly fell from about 1,600 to about 100 units in Dec 2025, so our "about 6 uploads/day" assumption is likely out of date. Postiz self-hosters hit the same audits. Browser-automation tools avoid the audits at the cost of ban risk.

### Cited Findings

**TikTok**
- Token lifetimes: TikTok's example response shows `"expires_in": 86400` and `"refresh_expires_in": 31536000`. The access token is valid for 24h and the refresh token for 365 days — [TikTok OAuth token management](https://developers.tiktok.com/doc/oauth-user-access-token-management), [TikTok Minis OAuth](https://developers.tiktok.com/doc/minis-oauth) (via search snippet).
- Refresh-token rotation: "the returned refresh_token may be different than the one passed in the payload. You must use the newly-returned token" — [TikTok OAuth token management](https://developers.tiktok.com/doc/oauth-user-access-token-management) (snippet). The access token can be refreshed without user consent, so a backend job can keep tokens fresh — [TikTok legacy guide](https://developers.tiktok.com/doc/legacy-user-access-guide) (snippet). OAuth v1 tokens are deprecated — same source.
- Unaudited clients: "to lift the restriction on content visibility, your API client must undergo an audit". Publishing as public fails with `unaudited_client_can_only_post_to_private_accounts` at `/publish/content/init/` — [TikTok Direct Post reference](https://developers.tiktok.com/doc/content-posting-api-reference-direct-post) (snippet).
- "Unaudited API Clients can allow up to 5 users to post in a 24 hour window", and those accounts must be private at the time of posting — [adaptlypost (quoting TikTok docs)](https://adaptlypost.com/de/blog/why-does-my-app-need-approval-post-tiktok); also [Postiz TikTok provider docs (snippet)](https://docs.postiz.com/self-host/providers/tiktok).
- Daily cap (audited): "the upper limit may vary among creators (typically around 15 posts per day/creator account) and is shared across all API Clients using Direct Post". `creator_info` signals when a creator cannot post — [TikTok Content Sharing Guidelines](https://developers.tiktok.com/doc/content-sharing-guidelines) (snippet). A vendor claims 25/day — [Zernio](https://zernio.com/blog/tiktok-posting-api), unverified. Others report 6 init requests per minute per user token — [website-apn blog](https://website-apn.pages.dev/blog/social-media-platform-api-rules-rate-limits-media-specs), and a `spam_risk_too_many_posts` 403 error — secondary, unverified.
- At most 5 pending shares per 24h (photo/inbox flow) — [TikTok photo post reference](https://developers.tiktok.com/doc/content-posting-api-reference-photo-post) (snippet).
- How Postiz handles it: self-hosters create their own TikTok app with redirect path `/integrations/social/tiktok`. While the app is unaudited, "the only privacy level it can send is SELF_ONLY" — [Railway "Postiz for TikTok" guide](https://railway.com/deploy/deploy-postiz-for-tiktok-scheduling) (vendor page). A Postiz-affiliated Reddit reply (Jan 2025) said "except for TikTok I think, most of them don't need approval for private app" — [r/selfhosted via redlib](https://redlib.hackliberty.org/r/selfhosted/comments/1fl8n2b/postiz_v130_opensource_social_media_scheduling/m7gl5lj/?context=3). A 2024 comment from the Postiz builder said approvals "can take you a few months for some of them (Facebook / Instagram / Threads)" — [r/selfhosted via psf.lt](https://lr.eu.psf.lt/r/selfhosted/comments/1f4x806/postiz_opensource_social_media_scheduling_tool/m3qqva0/?context=3).
- How the browser tools handle it: tiktok-uploader and autotok bypass the Content Posting API with cookies or session files, so the audit and the SELF_ONLY rule do not apply. autotok warns of restrictions and bans, and of flagging when many accounts share one IP — [autotok](https://github.com/makiisthenes/TiktokAutoUploader), [tiktok-uploader](https://github.com/wkaisertexas/tiktok-uploader).
- Commercial workaround: Blotato offers its audited app so posts can be public before your own app passes review — [Blotato](https://www.blotato.com/api/tiktok).

**YouTube**
- Videos uploaded by API projects created after 28 July 2020 that have not passed the compliance audit are forced to `privacyStatus: private`, even if the request asks for public. Projects created before that date are not affected. The fix is the API Services compliance audit. Videos already locked cannot be appealed and must be re-uploaded — [timetopost blog](https://timetopost.co/blog/how-to-upload-videos-youtube-api), [Stack Overflow archive](https://kiwix.lema.org/stackoverflow.com_en_all_2023-11/questions/64079139/using-youtube-data-api-makes-my-videos-private-on-upload), [Stack Overflow archive 2](https://kiwix.lema.org/stackoverflow.com_en_all_2023-11/questions/66277512/youtube-videos-privacy-locked-on-upload). These are secondary sources; the official revision history was not fetched.
- Quota: 10,000 units/day per Cloud project by default. Several sources report Google's Dec 4, 2025 revision cut `videos.insert` from about 1,600 to about 100 units — [Blotato](https://www.blotato.com/blog/youtube-api-pricing), [getphyllo](https://www.getphyllo.com/post/is-the-youtube-api-free-in-2026-quota-limits-costs-when-to-pay), [ChannelCrawler (Mar 2026, still lists 1,600)](https://channelcrawler.com/insights/youtube-api-daily-limit-quotas-costs-and-how-to-scale-beyond-10000-units-channelcrawler). One Activepieces article claims a further cut to 1 unit from June 1, 2026 — [Activepieces blog](https://www.activepieces.com/blog/youtube-api-quota-exceeded-how-to-fix-and-avoid-it), not confirmed by any other source.
- Arithmetic from those figures: 10,000 / 1,600 ≈ 6 uploads/day (old). 10,000 / 100 ≈ 100 uploads/day (post-Dec-2025, before thumbnail or other calls).
- How social-auto-upload handles it: it uses browser automation for YouTube because API uploads from unverified projects are forced to private, and "browser automation does not have this restriction" — [social-auto-upload](https://github.com/dreammis/social-auto-upload).
- How Postiz handles it: no Postiz-specific source on the YouTube audit was found — [search summary](https://socialrails.com/blog/postiz-review). Postiz self-hosters use their own Google project, so the same audit and quota apply (inferred from "you must create your own developer apps" — [GitHub](https://github.com/gitroomhq/postiz-app)).

**Facebook Page Reels**
- Flow: `POST /{page-id}/video_reels` with `upload_phase=start` returns a video ID and an upload URL. The binary goes to `rupload.facebook.com` and can be resumed by byte offset. Then `upload_phase=finish` with `video_state` ∈ {DRAFT, PUBLISHED, SCHEDULED} — [Meta Reels Publishing guide](https://developers.facebook.com/docs/video-api/guides/reels-publishing), [Page video_reels reference](https://developers.facebook.com/docs/graph-api/reference/page/video_reels).
- Limits: 30 API-published reels per 24h moving window, enforced on `POST /{page_id}/video_reels`. Minimum resolution 540p. The edge cannot read, update or delete reels after posting. Official examples use Graph v25.0/v26.0 — [Meta Reels Publishing guide](https://developers.facebook.com/documentation/video-api/guides/reels-publishing).
- Scheduling up to 29 days ahead is a third-party claim — [OpenSource Clipping wiki](https://github.com/NaufalRizqullah/opensource-clipping/wiki/Facebook-Reels-Uploader). Unverified.
- Mixpost reportedly supports Facebook Reels specifically — [contentcreators.com](https://contentcreators.com/tools/mixpost-review). Whether Postiz posts Facebook video as a Reel or as a regular Page video was not verified.

**Per-platform caps on mass posting (criterion 13)**

| Platform | Cap | Source |
|---|---|---|
| TikTok (unaudited app) | SELF_ONLY only; at most 5 users posting per 24h | [adaptlypost quoting TikTok](https://adaptlypost.com/de/blog/why-does-my-app-need-approval-post-tiktok) |
| TikTok (audited) | About 15 Direct Posts/day per creator, shared across all apps; check `creator_info` before each post | [TikTok guidelines](https://developers.tiktok.com/doc/content-sharing-guidelines) |
| TikTok (browser tools) | No documented cap; uploads fail "after too many uploads"; multi-account on one IP gets flagged; ToS/ban risk | [tiktok-uploader](https://github.com/wkaisertexas/tiktok-uploader), [autotok](https://github.com/makiisthenes/TiktokAutoUploader) |
| YouTube | 10,000 units/day/project; upload ≈100 units (post-Dec-2025) → about 100/day; ≈1,600 (old) → about 6/day | [Blotato](https://www.blotato.com/blog/youtube-api-pricing), [getphyllo](https://www.getphyllo.com/post/is-the-youtube-api-free-in-2026-quota-limits-costs-when-to-pay) |
| Facebook Page Reels | 30 API-published reels / 24h rolling | [Meta Reels guide](https://developers.facebook.com/documentation/video-api/guides/reels-publishing) |
| Postiz API (self-host) | 90 create-post calls/hour by default (configurable via `API_LIMIT`); several posts per call | [Postiz docs (snippet)](https://docs.postiz.com/public-api/introduction.md) |

### Inferences
- The 24h TikTok token problem is solved the same way everywhere. A background job refreshes the token before `expires_in` runs out and saves the possibly rotated refresh token. The 365-day refresh lifetime means users must re-authorise about once a year. Postiz uses Temporal and has a scheduler architecture, so it very likely does this, but its source code could not be checked.
- For an unattended mass-production agent, the realistic ceilings per account per day are about 15 TikTok posts (audited) and 30 Facebook Reels. YouTube, at about 100 units per upload, is now the least limiting of the three if the Dec 2025 change is accurate. Our pipeline should read `creator_info` and the quota status rather than hard-coding these numbers.
- Using Postiz does not remove the TikTok/YouTube audits for a self-hosted install, because each self-hoster's own apps must be audited. Only Postiz Cloud (or a SaaS like Blotato or Upload-Post) gives already-approved apps.

### Gaps
- Official text of YouTube's Dec 2025 quota change and the claimed June 2026 cut to 1 unit: Google pages were not fetched.
- Whether YouTube applies channel-level daily upload caps separate from the API quota: not researched or found.
- Postiz's exact TikTok refresh implementation, its YouTube privacy handling, and its Facebook Reels vs regular video handling: docs.postiz.com and the source files were unreachable.
- How Mixpost Pro handles TikTok token refresh and audits: no source.

---

## Q3. Which tools could serve as our publishing backend instead of maintaining our own publishers?

### Takeaway
Postiz is the strongest candidate for a pluggable "external publisher" backend. It is self-hostable, uses official APIs, covers YouTube, TikTok, Facebook and Instagram plus about 10 more platforms, and offers a public API, MCP server, CLI and n8n node, with batched create-post calls. Its costs are AGPL-3.0, a heavy stack (Next.js/NestJS/Postgres/Redis/Temporal), and the fact that self-hosters still need their own audited TikTok and YouTube apps. Browser-based uploaders (social-auto-upload, autotok) are useful fallbacks for unaudited or private accounts, but only as clearly labelled high-risk options.

### Cited Findings
- Postiz exposes a public API and webhooks, an MCP server, an "AI Agents CLI", an n8n custom node and a Make.com integration, and is meant for automation "with platforms like N8N, Make.com, Zapier" — [GitHub](https://github.com/gitroomhq/postiz-app).
- The Postiz API limit is per create-post call (90/h self-hosted, configurable via `API_LIMIT`), and batching posts in one call is the recommended way to get more throughput — [Postiz docs (snippet)](https://docs.postiz.com/public-api/introduction.md). This conflicts with a 30 req/h global figure on a Mintlify page — [Mintlify](https://www.mintlify.com/gitroomhq/postiz-app/api/rate-limits).
- Postiz requires Postgres (Prisma), Redis and Temporal, and is AGPL-3.0 — [GitHub](https://github.com/gitroomhq/postiz-app).
- Self-hosted Postiz requires your own developer apps on each platform and their approvals. Some approvals reportedly take "a few months" (Meta) — [GitHub](https://github.com/gitroomhq/postiz-app), [r/selfhosted comment](https://lr.eu.psf.lt/r/selfhosted/comments/1f4x806/postiz_opensource_social_media_scheduling_tool/m3qqva0/?context=3).
- Mixpost Lite (MIT) has no documented API, and its video platforms (TikTok, YouTube, Reels) are in the paid Pro edition — [GitHub](https://github.com/inovector/mixpost), [contentcreators.com](https://contentcreators.com/tools/mixpost-review).
- autotok offers Python/TS/Go SDKs, an MCP server and Docker, but uses TikTok's private web upload API and warns of bans — [autotok](https://github.com/makiisthenes/TiktokAutoUploader).
- social-auto-upload is a CLI with cookie sessions per `--account` and agent Skills. It covers YouTube (browser), TikTok (Chrome) and Facebook Page, plus many Chinese platforms — [social-auto-upload](https://github.com/dreammis/social-auto-upload).
- n8n AI-video templates delegate posting to paid SaaS (Blotato/Upload-Post) — [n8n templates](https://n8n.io/workflows/5035), [Upload-Post](https://www.upload-post.com/n8n-templates).

### Inferences
- Recommended pattern for ai-content-agent: keep our own publisher interface (feature 10) and add a "Postiz" publisher that uploads media and creates scheduled posts through the Postiz public API. Users who already run Postiz, or use Postiz Cloud, then get many more platforms at once. We keep native YouTube/TikTok/Facebook publishers for users who don't want the Postiz stack, which matters for a Windows desktop install (12). Calling Postiz over HTTP from a separate process is generally treated as arm's-length use under AGPL. Bundling or modifying Postiz is different. This is a licensing inference, not legal advice.
- Postiz does not replace our scheduling-intelligence layer (7). It has calendar, repeat and "sets" features but no topic rotation or dedup of already-posted topics. It also does not replace our job dashboard (8), because it has no render jobs. Our cron + topic-dedup logic should stay upstream and hand finished videos to Postiz.
- For mass production (13), Postiz's batching helps, but platform caps (about 15 TikTok/day per creator, 30 FB Reels/day, YouTube quota) still apply per account. Our agent needs per-account daily budgets regardless of backend.
- What we can learn from the uploader libraries: per-account proxy isolation, "check before retrying" after an ambiguous upload failure, and reusing TikTok's native schedule windows (10–30 days) (autotok/tiktok-uploader). Browser automation is a deliberate workaround for YouTube's private lock (social-auto-upload). If we add browser-mode publishers, they should be opt-in with explicit ToS/ban warnings.

### Gaps
- Postiz public API endpoint details (media upload size limits, per-provider settings such as TikTok `privacy_level` or YouTube title/type fields): docs.postiz.com was unreachable, so how much of our current publisher logic maps onto Postiz could not be confirmed.
- Whether the Postiz MCP server or CLI supports video upload with per-platform options: not verified.
- Postiz resource requirements (RAM/CPU) for self-hosting next to our pipeline: not found.
- To close these gaps, allow docs.postiz.com, developers.tiktok.com and cdn.jsdelivr.net (or GitHub API access) in the session's network settings.
