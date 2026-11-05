# Commercial (closed-source / SaaS / paid) AI short-video automation products vs "ai-content-agent" (as of November 2026)

> **How these notes were made:** Research date 2026-11-04. WebFetch could not reach any vendor site. DNS failed in this session for www.revid.ai, autoshorts.ai, faceless.video and storyshort.ai, so those hosts would have to be allowed in the session's network settings. Every fact below therefore comes from **WebSearch result snippets**, and many of those are third-party, affiliate or competitor pages: FluxNote, FlowShorts, Faceless.so, Creatify, Upload-Post, Blotato and PostPeer all sell competing products. Prices conflict often. Where they do, both figures are shown. **No price below was verified on a live official pricing page** unless it is marked "(official)". Treat every number as an approximate snapshot from May–Oct 2026.
>
> **Matrix legend:** Y = supported, with a source. Y~ = implied by the product's core category but not separately verified. P = partial. N = sources say it is absent or limited. U = unknown (no source found).

---

## Q1. Faceless / auto-posting SaaS (AutoShorts.ai, Faceless.video, StoryShort, Crayo, Revid.ai, Vidrush, ShortsFaceless, AutoReels, FacelessReels): pricing, limits, platforms, languages, reviews

### Takeaway
This segment is a crowded market of web-only subscriptions. The pattern is "set up a series once and it auto-posts on a schedule." Entry tiers cost about $15–39/month and scale to about $69–199/month, or $275+/month for agency or "dedicated agent" tiers. Posting usually goes to TikTok, YouTube Shorts and Instagram Reels. Facebook (Page) posting is rarely listed. None of the sources confirmed Vietnamese, a desktop/self-host option, or CapCut export. Only Revid clearly exposes an API (plus MCP/CLI).

### Cited Findings

**AutoShorts.ai** (autoshorts.ai; the official site was unreachable from this session)
- Pricing conflicts across sources. One guide lists Starter at $19/mo and says 2+ YouTube channels need the $99/mo "Scale" plan — [FluxNote (competitor)](https://fluxnote.io/guides/autoshorts-pricing-2026). Another says it starts at $12/mo and warns that plan names and prices change often — [BityClips](https://bityclips.com/tool/autoshorts/pricing).
- It has four plans tied to posting frequency, plus a free tier that creates one video — [SendShort review](https://sendshort.ai/guides/autoshorts-review/).
- Third-party comparisons say it publishes to YouTube Shorts, TikTok and Instagram Reels (as of April 2026). None listed Facebook — [FluxNote compare](https://fluxnote.io/compare/autoshorts-vs-shortx-for-automated-shorts); [ShortsFast vs AutoShorts](https://shortsfast.com/vs/autoshorts/).
- Reviewers say it supports multiple languages but that some language nuances need manual fixes. No official language list was found, so Vietnamese is unconfirmed — [Listnr review](https://listnr.ai/blog/autoshorts-review); [SourceForge](https://sourceforge.net/app/autoshorts-ai/web-app/).
- Quality: visual coherence "may vary between videos" and complex narratives are tricky, per [Vidpros](https://vidpros.com/autoshorts-ai-review/). Another reviewer says "you need to level your expectations" — [MSPowerUser](https://mspoweruser.com/autoshorts-ai-review). A competitor says it lacks advanced AI video models — [FluxNote](https://fluxnote.io/guides/autoshorts-review-honest-2026).
- G2 has "not enough reviews" — [G2](https://www.g2.com/sellers/autoshorts). ClipJury rates it 7.6/10 and quotes the FAQ: videos are "yours to do with as you please" — [ClipJury](https://clipjury.pages.dev/reviews/autoshorts).
- One promotional description claims it can create thematically connected series with consistent storylines. This is unverified — [AutoShorts review aggregation, search snippet](https://howtotechinfo.com/autoshorts-ai-review/).

**Faceless.video** (faceless.video; unreachable)
- Starter costs $15/month **per series**, with 3 auto-posts/week and HD. Business starts at $275/month and includes a "dedicated AI agent" — [Toolmage](https://www.toolmage.com/en/tool/faceless/).
- There are three tiers, billed monthly or yearly, with 50% off yearly — [Vidpros](https://vidpros.com/faceless-video-review/).
- Don't confuse it with **Faceless.so**, a different product. Faceless.so starts at $29/mo, has a Growth tier at $39/mo for about 50 videos/month, and is month-to-month — [Faceless.so vs InVideo](https://faceless.so/alternatives/invideo); [Faceless.so vs Revid](https://faceless.so/alternatives/revid). Faceless.so posts directly to YouTube/TikTok and offers automated scheduling — [TopAI.tools](https://topai.tools/t/faceless-so); [Creati.ai](https://creati.ai/ai-tools/faceless-so/).

**StoryShort** (storyshort.ai; unreachable)
- Monthly plans: Starter $39, Growth $69, Influencer $129, Ultra $199. Yearly billing brings these to $23 / $42 / $75 / $117 per month — [Gappsy](https://www.gappsy.com/tools/storyshort/). Other sites report $19–$129 — [FlowShorts (competitor)](https://flowshorts.app/blog/storyshort-ai-review).
- You "set a series and a schedule once," and StoryShort picks topics, produces the videos and posts them. Its AI Editor works **shot by shot**, so you can redo one shot without regenerating the whole video — [Gappsy](https://www.gappsy.com/tools/storyshort/).
- A directory says Starter is limited to about 40 videos/month and one automated series. Formats include faceless stories, documentaries and AI ASMR. Reviewers praise the voices but say narrative flow still needs "tweaking" — [Gappsy](https://www.gappsy.com/tools/storyshort/); [AI Indigo review](https://aiindigo.com/blog/storyshort-review-2026-the-reality-of-faceless-channel-automation).

**Revid.ai** (revid.ai; unreachable, but its LLM-facing docs appeared in search)
- Revid's own pricing doc (updated June 2026) lists plans from $29/mo (Lite) to $199/mo (Ultra), plus higher-volume plans at $459, $749 and $1,459/mo. It has no permanent free plan, but a refund within 14 days is reported — [Revid pricing doc (official)](https://www.revid.ai/llm/revid-ai-pricing-plans.md).
- An October 2026 comparison quotes Growth at $39/mo ($32/mo yearly) with 2,000 credits, 3 Auto-Mode workers, and publishing to TikTok, Instagram and YouTube. Ultra is $199 ($166/mo yearly) — [EasyViral (competitor)](https://easyviral.ai/blog/best-revid-ai-alternatives-2026). Revid's FAQ also lists Elite at $89 — [Revid FAQ (official)](https://revid.ai/faq-for-llms.md).
- "Auto-Mode workers" are always-on pipelines. Each generates a new video daily from a configured tool and content source and can publish it automatically. Standard plans get 3 workers, Elite 5, Ultra 10. Voices come from ElevenLabs and cover 70+ languages — [Revid FAQ (official)](https://revid.ai/faq-for-llms.md).
- An API, **MCP and CLI** are included from the entry paid plan, according to a May 2026 pricing-page snapshot. Auto top-up packs can be bought through the API/MCP — [Revid pricing doc](https://www.revid.ai/llm/revid-ai-pricing-plans.md). A Make.com app also exists — [Make.com Revid app](https://apps.make.com/revidai-ipol91?hl=fr-FR).
- Limitations: avatar videos cannot auto-publish yet — [EasyViral](https://easyviral.ai/blog/best-revid-ai-alternatives-2026). Character consistency across scenes is a known limitation — [AutoGPT.net review](https://autogpt.net/ai-tool/revid-ai/). Language counts conflict: subtitles claim 100+, captions page lists 32 — [Revid subtitle tool](https://revid.ai/tools/subtitle-generator).

**Vidrush** (vidrush.ai)
- It has no free plan or trial and uses credits. Starter is $99/mo for 2,000 credits, about 45 minutes or 6 videos. It is aimed at **long-form** faceless channels: Documentary and Top-10 formats from 6 to 60 minutes, with a credit quote shown before each render. German and Spanish are newer than English. It depends on third-party APIs — [AI Miracle review](https://www.aimiracle.ai/ai-tool-review/vidrush-ai-review/).
- Higher tiers are quoted as Pro at $479/mo and Scale at $1,313/mo. These come from a lower-reliability blog — [Blogspot review](https://success-alikadhem.blogspot.com/2026/05/vidrush-review-2026-setup-guide-best.html). Developer docs exist at [dev.docs.vidrush.ai](https://dev.docs.vidrush.ai/docs/faq).

**Crayo** (crayo.ai)
- Tiers run from Hobby at $19/mo to Pro at $79/mo. Hobby is quoted at 50 AI videos/mo, 40 min export, 30 voiceover minutes and 100 AI images — [Creatify (competitor)](https://creatify.ai/blog/crayo-pricing-(2026)-plans-credits-and-what-you-ll-actually-pay); [FlowShorts](https://flowshorts.app/blog/crayo-ai-review). Another source says $29/mo Basic with a free trial — [FluxNote](https://fluxnote.io/guides/crayoai-pricing-guide-2026).
- Sources conflict on auto-posting. One describes it as "TikTok-first" with Reddit imports, series automation and TikTok-tuned hooks — [Faceless.so compare](https://faceless.so/compare/crayo-vs-faceless). Another says it "does not auto-post to any platform" — [FlowShorts](https://flowshorts.app/blog/crayo-ai-review).

**AutoReels.ai / FacelessReels / ShortsFaceless**
- AutoReels: free, $19, $39 and $69/mo tiers, differing by posting frequency (3×/week, daily, 2×/day). Yearly billing is 20% off. It posts to TikTok, YouTube, Instagram Reels and **Facebook**. Directories list no user reviews — [Gappsy](https://www.gappsy.com/tools/autoreels/); [TopAI.tools](https://topai.tools/t/autoreels-ai).
- FacelessReels: tiers around $19, $39 and $69/mo. One review estimates "under $1.50 per video" even at the top tier. It auto-publishes to YouTube Shorts and TikTok. There are complaints about billing surprises and slow refunds — [Websites2Know review](https://websites2know.com/facelessreels-review/); [Trustpilot (124 reviews)](https://www.trustpilot.com/review/facelessreels.com). A competitor instead says it costs $29/mo and auto-posts to Instagram only, which conflicts — [Faceless.so compare](https://faceless.so/compare/autoshorts-vs-facelessreels).
- ShortsFaceless: $19/mo for 30 videos. Auto-posting is "Limited (primarily download)" and focused on YouTube Shorts. It uses standard TTS, has no timezone scheduling and no analytics dashboard. The only source is a competitor — [FlowShorts vs ShortsFaceless](https://flowshorts.app/blog/flowshorts-vs-shortsfaceless).
- Market signal: an Acquire.com listing advertises an "AI social video SaaS, 30k users, 80% margins, auto post to TikTok, IG and FB" — [Acquire.com](https://app.acquire.com/startup/03qrzfbts3-ai-social-video-saas-30k-users-80-margins-auto-post-to-tiktok-ig-and-fb).

**Vietnamese across faceless SaaS**
- A search for faceless tools with Vietnamese support plus auto-posting found **no tool that explicitly names Vietnamese**. GoFaceless offers Vietnamese AI dubbing and translation of existing videos, not generation plus posting — [GoFaceless Vietnamese dubbing](https://www.gofaceless.ai/en/tools/vietnamese-ai-dubbing). InVideo claims 50+ languages without naming Vietnamese — [InVideo info page](https://info.invideo.io/ai-tool-generate-faceless-videos-multiple-languages).

### Inferences
- Faceless SaaS costs an operator roughly $0.50–$5 per video at entry tiers. Examples: StoryShort Starter at $39 for about 40 videos is about $1/video; Vidrush at $99 for about 6 long videos is about $16/video; FacelessReels is under $1.50/video. These figures are rough divisions of quoted prices, not verified unit costs.
- Pricing is usually per series or channel and per posting frequency. That penalises multi-channel operators (e.g. AutoShorts reportedly needs $99 for 2+ channels). A self-hosted multi-channel agent avoids this.
- Revid is the closest commercial analogue to our agent. It has unattended daily "workers", auto-publishing, and API/MCP/CLI access. It is still cloud-only, and the sources list no Facebook posting.

### Gaps
- Official pricing pages for AutoShorts, Faceless.video, StoryShort, Crayo and Revid could not be fetched because their hosts were blocked. All prices are from third parties.
- No source confirmed Vietnamese voice or script support for AutoShorts, Faceless.video, StoryShort, Crayo or Revid. Revid's "70+ languages via ElevenLabs" may include Vietnamese, but this is not confirmed.
- No reliable data was found on watermarks in low tiers for AutoShorts, Faceless.video or StoryShort, or on their thumbnails, dashboards or dedup.
- No Trustpilot page was found for AutoShorts.ai. Reddit sentiment for specific tools was not retrievable.

---

## Q2. General AI video generators, clippers, caption and avatar tools (Fliki, InVideo AI, Pictory, Vidnoz, OpusClip, Submagic, Vizard, Klap, Captions.ai, HeyGen/Synthesia, CapCut, VEED, Canva)

### Takeaway
These are mostly **editing or generation suites with a human in the loop**, not unattended channel autopilots. The clippers (OpusClip, Vizard, Klap) repurpose long videos rather than writing scripts. Captions.ai and HeyGen/Synthesia are avatar-centric. Several sell **separate usage-priced APIs** (Captions/Mirage, HeyGen, VEED, Pictory, Submagic Business, Vizard paid plans), and these could be integrated as providers. Fliki is the only tool with **explicitly sourced Vietnamese voices**.

### Cited Findings

**Fliki**
- Fliki added 130+ voices in April 2026, including **Vietnamese**. Its Feb 2026 voice rebuild lists Vietnamese among supported languages — [Fliki What's New (official)](https://fliki.ai/whats-new?page=3). A Vietnamese voice directory shows Standard and "Ultra realistic" voices, some available on the free tier — [Fliki Vietnam voices (official)](https://Fliki.ai/resources/voices/dialect/vietnam-61b8b31d4268666c126bacef).
- Pricing conflicts. One source lists Free (5 min/mo), Basic $28 (180 min), Standard $66 (600 min) and Premium $99 — [FluxNote](https://fluxnote.io/guides/fliki-pricing-2026). Another lists Standard $28, Premium $88 and custom Enterprise — [ToolRadar](https://toolradar.com/tools/fliki/pricing). API access is mostly reported as Enterprise-only — [AIToolsAtlas](https://aitoolsatlas.ai/tools/fliki-ai/pricing).

**InVideo AI**
- Monthly: Plus $20, Max $100, Generative $200, Elite $1,000. Annual: $17 / $85 / $170 / $900 per month — [Creatify](https://creatify.ai/blog/invideo-pricing-(2026)-plans-credits-and-what-you-ll-actually-pay). Plus credits conflict: 750 per [YesPress](https://yespress.io/products/invideo-ai.md) vs 75 per a reviewer who paid $20 in July 2026 — [Marc Andrews](https://marcandrews.com/invideo-ai-pricing-uk-2026-worth-it-for-marketers/).
- Paid plans have no watermark. A hidden free plan has about 5 credits and a watermark. Credits don't roll over. A 60-second test used 4.8 of 5 free credits — [Magic Hour](https://magichour.ai/blog/invideo-ai-pricing); [Techpresso](https://academy.techpresso.co/reviews/is-invideo-ai-worth-it).
- It claims faceless videos in 50+ languages from one script. Vietnamese is not named — [InVideo (official)](https://info.invideo.io/ai-tool-generate-faceless-videos-multiple-languages).

**Pictory**
- Starter about $29/mo ($25 annual), Professional $59 ($35 annual), Team $199 ($119 annual). There is a 14-day trial. The API is a separate product with custom pricing (pictory.ai/pictory-api) — [CostBench](https://costbench.com/software/ai-video-editing-saas/pictory/); [Creatify](https://creatify.ai/blog/pictory-pricing-(2026)-plans-credits-and-what-you-ll-actually-pay).

**Vidnoz**
- It claims 1,380+ voices in 140+ languages. The free plan is watermarked (60 credits/day or 3 min/day by different accounts). Paid plans start at about $13.50–22/mo. Large first-month discounts and Trustpilot complaints about credit consumption and expiry are reported — [ToolsForHumans](https://toolsforhumans.ai/ai-tools/vidnoz-ai); [AIVidLab](https://aividlab.pages.dev/vidnoz-review).

**OpusClip** (clipping long video into shorts)
- Free; Starter $15/mo (down from $19); Pro $29/mo (about $14.50 on annual billing); Business by quote. The social scheduler is a Pro feature. The API is Business-only — [Ssemble](https://www.ssemble.com/blog/opus-clip-pricing-2026). Auto-posting to X costs 1 credit per post — [Quso](https://quso.ai/blog/opus-clip-pricing).

**Submagic** (captions)
- Starter $19, Pro $39, Business + API $69/mo ($41/mo annual) — [FluxNote](https://fluxnote.io/guides/submagic-pricing-2026). The public API comes with Business + API — [ToolsForHumans](https://www.toolsforhumans.ai/ai-tools/submagic). Captions cover about 48 languages; translation and dubbing cover 100+ — [AIVideoPicks](https://aivideopicks.com/posts/submagic-review-2026.html).

**Vizard**
- "API service is included in all paid plans" — [Vizard docs (official)](https://docs.vizard.ai/docs/pricing.md). The free tier gives 60 credits/mo. Creator is $49/mo for 2,500 credits. A "Founding" $39/mo **BYO-key** plan closed 2026-08-31 — [Layer3Labs](https://www.layer3labs.io/guides/vizard-ai-pricing); [AIToolsAtlas](https://aitoolsatlas.ai/tools/vizard/pricing). In-app scheduling publishes to social platforms — [AIToolsAtlas review](https://aitoolsatlas.ai/tools/vizard/review).

**Klap**
- Prices conflict ($14–$189/mo). A competitor says Klap moved to per-minute pricing (checked 2026-09-26) — [Cut.pro](https://cut.pro/en/blog/klap-vs-opusclip-2026); [CostBench](https://costbench.com/software/ai-video-editing-saas/klap/). No API information was found.

**Captions.ai / Mirage** (AI actors)
- Max is $24.99/mo for 500 credits. It is the cheapest tier with AI actors and no watermark — [Hooked](https://www.hooked.so/compare/captions-ai-pricing). Official credits: Max 500, Scale 1,400, Scale 2x 2,800, Scale 4x 5,600 — [Captions help (official)](https://captions.ai/help/mirage/account-management/mirage-credits).
- The Mirage API is billed by usage, per input-video minute, rounded up — [Captions API pricing (official)](https://www.captions.ai/help/docs/api/pricing).

**HeyGen / Synthesia** (avatars, brief)
- Synthesia has a free tier of about 10 min/mo, Starter at $29 and Creator at $89, with the API on Creator — [ForaSoft](https://www.forasoft.com/blog/article/heygen-alternatives). HeyGen's API is pay-as-you-go from $5 — [Anam](https://anam.ai/blog/heygen-vs-synthesia). An avatar costs about $0.05/sec (≈$3/min) — [Flowjam](https://flowjam.com/blog/synthesia-vs-heygen-2026).
- Tonal languages such as **Vietnamese** are a weak spot for avatar lip-sync on both platforms — [Vidico](https://vidico.com/news/heygen-vs-synthesia/).

**CapCut** (ByteDance)
- Pro prices conflict: about $19.99/mo or $179.99/yr with Standard at about $9.99, vs $7.99/mo. Some sources are competitors — [FluxNote](https://fluxnote.io/guides/capcut-pro-pricing-2026); [BigVU (Vietnamese)](https://bigvu.tv/blog/vi/gi%C3%A1-capcut-2026-mi%E1%BB%85n-ph%C3%AD-so-191/).
- Pro includes about 200 AI credits/mo, and an avatar clip costs 20–40 credits, so the allowance covers about 5–10 avatar videos — [FluxNote AI features free vs paid](https://fluxnote.io/guides/capcut-ai-features-free-vs-paid-2026).
- A **Vietnamese-locale** AI avatar page offers script → avatar video with TTS — [CapCut vi-VN (official)](https://www.capcut.com/vi-vn/create/ai-avatar). Sources disagree on whether script-to-video produces a finished narrated video or only a stock-footage draft — [VideoDubber](https://videodubber.ai/blogs/capcut-ai-video-generator/).
- **CapCut Commerce Pro** costs about $25.99/mo ($20.84 annual) for 1,800 credits — [Vantaige](https://vantaige.io/ar/ai-tool/capcut-commerce). Another source says from $24.17 — [FitGap](https://us.fitgap.com/products/030185/capcut-commerce-pro). It makes product videos in batch "with a single click" via Shopify — [Shopify app (official)](https://apps.shopify.com/capcut-commercepro-online). FitGap says its strength is "hands-on iteration, not batch backend orchestration" — [FitGap](https://us.fitgap.com/products/030185/capcut-commerce-pro).

**VEED**
- Prices conflict across 2026 sources: Creator ranges $10–25 and Pro $20–49 — [CostBench](https://costbench.com/software/ai-video-editing-saas/veed-io/); [FluxNote](https://fluxnote.io/guides/veed-io-pricing-2026). A USD list-price rise is logged on 2026-07-22 — [UsagePricing](https://www.usagepricing.com/blueprint/activity/veed-ai-2026-07-22-usd-list-price-rise).
- The API is separate: prepaid credits that expire after 2 years, Lip Sync at about $0.07/sec, and a Subtitle API from $0.10/min via fal.ai — [Magic Hour](https://magichour.ai/blog/veed-pricing).

**Canva**
- Magic Studio was rebranded to "Canva AI 2.0" in April 2026, and video generation became a Premium feature. **Bulk Create** turns CSV or Sheet rows into template variants and is reported as Pro at $14.99/mo. No official API for bulk *video* was found; Zapier/Make are used to automate it — [FrankX](https://frankx.ai/blog/ultimate-canva-ai-workflow-2026); [AIToolsDevPro](https://aitoolsdevpro.com/ai-tools/canva-magic-studio-guide/).

### Inferences
- For ai-content-agent, the most useful commercial pieces in this group are **component APIs**, not the full products: Submagic/ZapCap-style captioning, HeyGen/Captions avatars as an optional "avatar scene" provider, and Fliki or VEED voices or lip-sync. None of these tools replaces our end-to-end unattended pipeline.
- CapCut is a complement, not a competitor, for our CapCut draft export (feature 9). Its own AI features (script-to-video, avatars, Commerce Pro batch) are UI-driven and credit-limited, and no public API was found.

### Gaps
- Watermark status of entry tiers was not confirmed for Fliki, Pictory, OpusClip, Vizard or Klap.
- Vietnamese support was not confirmed for InVideo, Pictory, Submagic, Vizard, Klap, Captions or VEED. Vidnoz's 140+ languages probably include it, but no source said so.
- OpusClip's "virality score", trend features and analytics were not researched in the snippets found.

---

## Q3. Render / automation APIs used by builders (Creatomate, JSON2Video, Shotstack, Plainly, Orshot, Bannerbear)

### Takeaway
These APIs could replace or offload our FFmpeg editing stage (feature 4) and thumbnail stage (feature 5). They price by render minute or credit. The cheapest per minute at volume are **Shotstack** (about $0.10–0.16/min on plans) and **JSON2Video** (about $0.20/min on larger packs, with bundled Azure/ElevenLabs TTS at 0 extra credits). **Creatomate** is cheap at 720p but costs about 37 credits/min at 1080p. Bannerbear and Orshot are mainly image (thumbnail) APIs with light video.

### Cited Findings
- **Creatomate:** 1 image costs 1 credit, and about 1 minute of 720p/25fps video costs about 14 credits, scaling with resolution, fps and length — [Creatomate docs (official)](https://creatomate.com/docs/account/how-are-credits-calculated). One minute at 1080p/30 is about 37 credits — [Wireflow](https://www.wireflow.ai/blog/creatomate-pricing). Plans: Essential $54 for 2,000 credits, Growth $129 for 10,000, Beyond $329 for 50,000 — [ZapCap](https://www.zapcap.ai/blog/zapcap-api-vs-creatomate). Essential is $45/mo billed yearly, and a free trial gives 50 credits with no card — [Creatomate pricing (official)](https://creatomate.com/pricing).
- **JSON2Video:** 1 credit per second of rendered video, and a free 600 credits equals 10 minutes — [JSON2Video (official)](https://json2video.com/how-to/shotstack-alternative/). It offers free, monthly and prepaid plans — [JSON2Video docs (official)](https://json2video.com/docs/v2/pricing/plans). Azure and ElevenLabs voices cost 0 credits per minute — [JSON2Video credit consumption (official)](https://json2video.com/pricing/credit-consumption.html).
- JSON2Video prices conflict: Hobby $19.95 for 50 min, Startup $99.95 for 500 min, or from $16.95/mo yearly or $49.95 one-time. Reported catches include monthly credit expiry, a 30-min cap per video and 7-day file hosting — [Wireflow](https://www.wireflow.ai/blog/json2video-pricing); [SpotSaaS](https://www.spotsaas.com/product/json2video/pricing).
- **Shotstack:** On pay-as-you-go, 1 credit equals 1 minute. On plans, 1 credit equals 1.25 min (Starter), 1.5 (Pro), 2 (Scale) and 4 (Volume) — [Shotstack pricing (official)](https://shotstack.io/pricing/). Starter $39 for 250 min (≈$0.16/min), Pro $99 for 750 min (≈$0.13), Scale $199 for 2,000 min (≈$0.10) — [Wireflow](https://www.wireflow.ai/blog/shotstack-pricing). PAYG is quoted as both $0.30 and $0.40/min, which conflict.
- **Plainly** (After Effects templates): $59/mo per its own page vs $69/mo per directories. It has a 14-day trial, is API-first, works on a "Bring Your Own Template" basis, and puts the API on higher tiers — [Plainly (official)](https://plainlyvideos.com/templater-alternative); [Software Advice](https://www.softwareadvice.com/product/525571-Plainly/).
- **Bannerbear:** about $49/mo for 1,000 credits and $149 for 10,000. Video costs more credits than an image, and videos are capped at 5 minutes — [FitGap](https://us.fitgap.com/products/bannerbear); [Plainly blog](https://www.plainlyvideos.com/blog/best-video-editing-api).
- **Orshot:** free plan with 60 renders. It offers video with per-layer animation and MP4/WebM/GIF output and claims to be "2x cheaper" than Bannerbear. That claim is vendor marketing — [Orshot blog (official)](https://orshot.com/blog/bannerbear-api-alternative.md). Bannerbear concedes Orshot is cheaper at most volumes — [Bannerbear blog](https://www.bannerbear.com/blog/bannerbear-vs-orshot/). Orshot charges 1 credit per second of video — [Wireflow](https://www.wireflow.ai/blog/creatomate-pricing).

### Inferences
- Approximate render cost for a **60 s 9:16 1080p short**. This is my arithmetic from the quoted prices, not a vendor figure:
  - Shotstack: about $0.10–0.16.
  - JSON2Video: about $0.20–0.40, TTS included.
  - Creatomate Essential: about $1.00 (37 credits × $0.027). At Beyond it is about $0.24.
- Our local FFmpeg pipeline costs about $0 per render. For a self-hosted or desktop agent, these APIs make most sense as an *optional* cloud-render provider, e.g. for low-power machines, or for template-based thumbnails via Bannerbear or Orshot.

### Gaps
- No official dollar tables for JSON2Video, Orshot or Shotstack PAYG were retrievable, and figures conflict.
- No source documented whether these APIs support loudness normalization (EBU R128) or word-level caption timing out of the box.

---

## Q4. Publishing APIs (Blotato, Upload-Post, Ayrshare, Post Bridge, Late → Zernio): features, price per post, platforms, Facebook Page Reels, TikTok audit

### Takeaway
All five can post to TikTok and YouTube through one API. **Ayrshare** has the clearest documentation for **Facebook Page Reels** (`"reels": true`, Pages only, up to 90 s) and YouTube Shorts (up to 3 min), but it is expensive (from $149/mo per profile). **Blotato**'s help center lists Facebook Reels and TikTok video/slideshow posting ($29–$499/mo, with AI credits bundled). **Upload-Post** is cheapest for unlimited uploads ($24/mo, 5 profiles), but Reels-specific Facebook support and its own TikTok audit status are unconfirmed. **Late was rebranded to Zernio** and now prices per connected account (first 2 free). No source independently confirmed which vendors have passed TikTok's Content Posting API audit.

### Cited Findings
- **TikTok audit context:** The official TikTok Content Posting API has no published fee. Sandbox or unaudited apps can only post **privately** until they pass audit, and there is a cap of about 6 posts/min — [Blotato TikTok API guide](https://www.blotato.com/blog/tiktok-api-pricing); [PostPeer](https://www.postpeer.dev/blog/best-tiktok-posting-api).
- **Blotato:** Starter $29/mo includes 20 accounts and 1,250 AI credits. Creator $97/mo includes 40 accounts and 5,000 credits. Agency $499/mo includes 28,000 credits; its account cap is not stated. Source dated 2026-09-10 — [Blotato pricing (official)](https://www.blotato.com/pricing.md); [Mallary](https://mallary.ai/alternatives/blotato-pricing). AI credits cover image, video, voice and writing generation, and "active contacts" (DMs and comment replies) are metered separately. There is a 7-day trial, but reportedly not for the API — [Upload-Post on Blotato pricing (competitor, verified 2026-09-17)](https://www.upload-post.com/blotato-pricing/).
- Blotato's API publishes and schedules reels, slideshows, carousels and stories — [Blotato API docs (official)](https://help.blotato.com/api). Supported formats include **Facebook reels** and TikTok videos and slideshows. YouTube quota limits are enforced by YouTube, and new channels get lower quotas — [Blotato social accounts (official)](https://help.blotato.com/settings/social-accounts).
- **Upload-Post:**
  - Free: 10 uploads/mo, 2 profiles, all platforms **except TikTok**, 30 min of FFmpeg — [Upload-Post pricing (official)](https://www.upload-post.com/social-media-api).
  - Basic: $24/mo ($16 annual), unlimited uploads, 5 profiles.
  - Professional: $50 ($33 annual), 25 profiles.
  - Advanced: $147 ($118), 75 profiles.
  - Business: $438 ($350), 225 profiles — [Upload-Post agencies page (official)](https://www.upload-post.com/social-media-scheduler-for-agencies/); [Upload-Post docs](https://docs.upload-post.com/resources/pricing-and-limits).
  - A profile is a sub-account that can hold one account per platform — [Upload-Post docs](https://docs.upload-post.com/resources/pricing-and-limits).
  - It claims posting to "TikTok, Reels, and Shorts". Facebook support is described as posts, links, photos and videos, with no Reels-specific detail — [Upload-Post API (official)](https://www.upload-post.com/social-media-api).
- **Ayrshare:**
  - Premium about $149/mo for 1 profile ($129 annual); Launch $299 for up to 10 profiles; Business from $599 with 30 profiles; Enterprise can reach about $1/profile/mo at volume — [Ayrshare pricing (official)](https://www.ayrshare.com/pricing); [Upload-Post on Ayrshare (verified 2026-09-29)](https://www.upload-post.com/ayrshare-pricing/).
  - It supports 13 networks, including TikTok, YouTube, Facebook and Instagram — [Ayrshare docs (official)](https://www.ayrshare.com/docs/help-center/product/what_social_networks_are_supported).
  - Facebook Reels are posted with `"reels": true`, **only to Facebook Pages**, up to 90 s — [Ayrshare FB Reels (official)](https://www.ayrshare.com/facebook-reels-api-how-to-post-fb-reels-using-a-social-media-api/).
  - YouTube Shorts can now be up to 3 min — [Ayrshare changelog (official)](https://ayrshare.com/docs/whatsnew/archive).
  - TikTok supports standard video and a custom cover frame — [Ayrshare video use case (official)](https://www.ayrshare.com/use-cases/video-content-platforms/).
- **Post Bridge:** The API is live as a **$5/mo add-on** on top of a plan — [Post Bridge support (official)](https://support.post-bridge.com/api/post-bridge-api-overview-access-and-pricing). An older official article described a free closed beta with a proposed $0.05/post — [Post Bridge support (older)](https://support.post-bridge.com/articles/post-bridge-api-overview-access-and-pricing-hg4l3). Base plans are reported as Starter $9 (5 accounts), Creator $29, Growth $49 and Pro $99, unconfirmed on the official site — [Mallary](https://mallary.ai/alternatives/post-bridge-pricing).
- **Late (getlate.dev) → Zernio:** getlate.dev redirects to zernio.com. New per-account pricing (as of 2026-10-31): accounts 1–2 free, 3–10 at $6 each, 11–100 at $3 each, 101+ at $1 each, up to 2,000 — [PostPeer (competitor)](https://www.postpeer.dev/blog/zernio-pricing-change-2026); [Capterra](https://www.capterra.ie/software/1085150/Late).
  - The earlier free plan had 2 profiles, 20 posts/mo, full API and 13 platforms — [Late (official, older)](https://getlate.dev/ayrshare-vs-late).
  - X API calls are billed at X's rates. AppSumo lifetime-deal buyers complained about the price changes — [AppSumo reviews](https://appsumo.com/products/late/reviews/?page=1); [Trustpilot Zernio](https://de.trustpilot.com/review/zernio.com).

### Inferences
- **Cost for our three targets** (YouTube + TikTok + Facebook Page) **for one brand.** This is my arithmetic from the quoted prices:
  - Zernio: about $6/mo (2 free accounts + 1 × $6).
  - Upload-Post Basic: $24/mo, unlimited uploads.
  - Post Bridge: base plan + $5.
  - Blotato Starter: $29/mo.
  - Ayrshare Premium: $149/mo.
  - At 3 posts/day × 3 platforms (about 270 posts/mo), Upload-Post and Zernio come to well under $0.10 per post.
- For Facebook **Page Reels** specifically, Ayrshare and Blotato have first-party documentation. Upload-Post's Reels support should be tested before relying on it.
- Using a publishing API sidesteps our own TikTok audit, because the vendor's audited app is used. This only holds if the vendor is actually audited, which no source confirmed. It also adds a third-party dependency and a token-custody risk.

### Gaps
- Whether Upload-Post, Blotato, Zernio and Post Bridge each have **TikTok-audited** apps (public, non-private posting) was not independently confirmed.
- Upload-Post's Facebook **Reels** (vs. regular Page video) support is unconfirmed.
- Exact per-post overage costs for Blotato, Ayrshare and Zernio were not found.

---

## Q5. Mapping commercial products against ai-content-agent's 13 features

### Takeaway
No commercial product found covers all 13. The faceless SaaS tools cover features 2, 3, 4, 7 and 13 well and feature 6 partially (usually without Facebook Page). They are web-only (12 = N) and closed (10 is weak except Revid, Vizard and Submagic). None was found with CapCut draft export (9). None explicitly confirms Vietnamese (11), except Fliki voices and CapCut's vi-VN avatar page.

### Cited Findings
These are the evidence anchors; full citations are in Q1–Q4.
- Series + scheduled auto-posting: StoryShort [Gappsy](https://www.gappsy.com/tools/storyshort/); Faceless.video [Toolmage](https://www.toolmage.com/en/tool/faceless/); Revid workers [Revid FAQ](https://revid.ai/faq-for-llms.md); AutoReels [Gappsy](https://www.gappsy.com/tools/autoreels/).
- Facebook posting is listed only for AutoReels [Gappsy](https://www.gappsy.com/tools/autoreels/) among the faceless SaaS tools. Among the APIs, Ayrshare [Ayrshare](https://www.ayrshare.com/facebook-reels-api-how-to-post-fb-reels-using-a-social-media-api/) and Blotato [Blotato](https://help.blotato.com/settings/social-accounts) list it.
- Vietnamese is explicit only for Fliki voices [Fliki](https://fliki.ai/whats-new?page=3) and the CapCut vi-VN avatar page [CapCut](https://www.capcut.com/vi-vn/create/ai-avatar).
- APIs: Revid (API/MCP/CLI) [Revid pricing doc](https://www.revid.ai/llm/revid-ai-pricing-plans.md); Vizard [docs](https://docs.vizard.ai/docs/pricing.md); Submagic Business [ToolsForHumans](https://www.toolsforhumans.ai/ai-tools/submagic); Captions/Mirage [docs](https://www.captions.ai/help/docs/api/pricing).
- A "BYO-key" plan, a weak analogue of pluggable providers, existed briefly at Vizard [Layer3Labs](https://www.layer3labs.io/guides/vizard-ai-pricing).

### Inferences
**Feature matrix.** Columns: 1 storyboard/multi-LLM · 2 per-scene AI visuals · 3 TTS · 4 auto-edit · 5 thumbnail · 6 YouTube + TikTok + Facebook Page publish · 7 schedule/rotation/dedup · 8 dashboard · 9 CapCut draft · 10 pluggable/API · 11 Vietnamese · 12 desktop/self-host · 13 unattended batch. Each cell is based on the Q1–Q4 sources. "N~" for column 12 means a web-only SaaS with no desktop or self-host option found.

| Product (entry price) | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **ai-content-agent (ours)** | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| AutoShorts.ai (~$12–19) | P (AI script; multi-LLM U) | P (no advanced video models) | Y~ | Y~ captions; U music/logo/loudness | U | P (YT, TikTok, IG; no FB found) | P (frequency-based series; dedup U) | U | U | U | U ("multi-language") | N~ | Y~ |
| Faceless.video ($15/series) | U | U | Y~ | U | U | P (3 posts/wk; platforms U) | P (per series) | U | U | U | U | N~ | Y~ (Business "AI agent") |
| StoryShort ($39; $23 yr) | P (shot-by-shot editor) | Y~ (per-shot regen) | Y (voices praised) | U | U | P (auto-posts; platforms U) | P (series + schedule, AI picks topics) | U | U | U | U | N~ | Y (40 videos/1 series on Starter) |
| Revid.ai ($29–39) | P (tool + content source; LLM choice U) | Y~ (character consistency issue) | Y (ElevenLabs) | P (subtitles) | U | P (TikTok/IG/YT; no FB found) | P (daily worker) | U | U | **Y** (API, MCP, CLI, Make) | P (70+ langs; VI unconfirmed) | N~ | **Y** (3–10 workers) |
| Vidrush ($99) | P (long-form doc/Top-10) | U | Y~ | U | U | U | U | U | U | U (dev docs exist) | P (EN; DE/ES newer) | N~ | P (credit quotes) |
| Crayo ($19) | P (Reddit-story import) | P (100 AI images on Hobby) | Y (30 VO min) | Y~ | U | conflicting (TikTok-first vs no auto-post) | P (series automation claimed) | U | U | U | U | N~ | P |
| AutoReels ($19) | U | U | Y~ | U | U | **Y~** (TikTok, YT, IG, FB; Page vs profile U) | P (3×/wk–2×/day) | U | U | U | U | N~ | Y~ |
| FacelessReels (~$19) | U | U | Y~ | U | U | conflicting (YT+TikTok vs IG only) | P | U | U | U | U | N~ | Y~ |
| ShortsFaceless ($19) | U | U | Y (standard TTS) | U | U | N (mostly download) | N (no timezone scheduling) | N (no analytics) | U | U | U | N~ | P |
| Fliki ($21–28) | P (script→video) | U | Y | U | U | U | U | U | U | P (Enterprise API) | **Y** (VI voices) | N~ | U |
| InVideo AI ($20) | Y~ (agentic prompt→video) | Y (gen models on higher tiers) | Y~ | Y~ | U | U | U | U | U | U | P (50+ langs) | N~ | U |
| Pictory ($29) | P | U | Y~ | Y~ | U | U | U | U | U | P (separate API) | U | N~ | P (via API) |
| Vidnoz (~$15–22) | U | U | Y (140+ langs) | U | U | U | U | U | U | U | P (likely; unconfirmed) | N~ | U |
| OpusClip ($15) | N (clips long video) | N | N/A | Y~ (captions, reframe) | U | P (scheduler on Pro) | P | U | U | P (Business API) | U | N~ | P |
| Submagic ($19) | N | N | N/A | Y (captions) | U | U | U | U | U | Y (Business+API $69) | P (48 caption langs) | N~ | P |
| Vizard ($49) | N (clipping) | N | N/A | Y~ | U | P (in-app scheduling) | P | U | U | Y (API on paid) | U | N~ | P |
| Captions/Mirage ($24.99) | U | P (AI actors) | Y~ | Y~ | U | U | U | U | U | Y (usage API) | U | N~ | U |
| HeyGen / Synthesia ($29) | N | P (avatars) | Y~ | P | U | U | U | U | U | Y (APIs) | P (tonal lip-sync weak) | N~ | P (API) |
| CapCut (+Commerce Pro) | P (script-to-video) | P (stock/avatars) | Y~ | Y~ | U | U | U | U | (native) | N/U (no public API found) | P (vi-VN UI) | Y~ (desktop editor) | P (Commerce Pro batch) |
| VEED | U | U | Y~ | Y~ | U | U | U | U | U | P (separate API) | U | N~ | U |
| Canva | N | U | U | P | Y~ (templates) | U | U | U | U | P (Zapier/Make) | U | U | P (Bulk Create CSV) |

**Building-block APIs vs our features:**

| API | Covers | Price anchor |
|---|---|---|
| Creatomate | 4, 5 (render + images) | $54 / 2,000 credits; ~37 credits/min at 1080p |
| JSON2Video | 3 (bundled TTS), 4 | ~1 credit/s |
| Shotstack | 4 | ~$0.10–0.16/min on plans |
| Plainly | 4 (After Effects) | $59–69/mo |
| Bannerbear / Orshot | 5 (thumbnails) | $49 / 1,000 credits (Bannerbear); Orshot free 60 renders |
| Ayrshare | 6 (incl. FB Page Reels) | from $149/mo |
| Blotato | 6 (incl. FB Reels) | from $29/mo |
| Upload-Post | 6 (FB Reels unconfirmed) | from $24/mo |
| Zernio (ex-Late) | 6 | ~$6/mo for 3 accounts |
| Post Bridge | 6 | plan + $5/mo API |

### Gaps
- Most "U" cells reflect missing sources, not confirmed absence. This applies especially to thumbnails (5), dashboards and error logs (8), and dedup (7) across all SaaS products.
- No commercial product with CapCut draft export was found. This is an absence of evidence, not proof.

---

## Q6. Table stakes vs differentiation; what paid products have that we lack; known issues (bans, quality, billing)

### Takeaway
**Table stakes** in paid faceless tools: AI script → narrated video, AI voices, auto captions, series-based scheduled auto-posting to TikTok, YouTube and Instagram, credit-metered monthly plans, and no watermark on paid tiers. **Our differentiators**: self-host or Windows desktop, pluggable multi-LLM and multi-provider setup (no vendor lock-in or credit metering), Facebook Page publishing, CapCut draft export, Vietnamese-first content, explicit dedup and topic rotation, and loudness normalization and logo branding.

**Gaps in our product vs paid tools**:
- Avatars (Captions, HeyGen, Revid).
- Long-video clipping (OpusClip, Vizard, Klap).
- Translation and dubbing into 100+ languages (Submagic, GoFaceless).
- Reddit-story import (Crayo).
- Long-form documentaries (Vidrush).
- Agent interfaces such as MCP/CLI (Revid).
- Engagement automation such as DMs and comment replies (Blotato).
- Analytics add-ons (Zernio).

The biggest market-wide risk is YouTube's "inauthentic content" enforcement against mass-produced faceless channels.

### Cited Findings
- YouTube renamed and expanded its "repetitious content" policy to "inauthentic content" in mid-2025, and enforcement is visible through 2026. Reddit-story Shorts with AI voices and stock footage are a format at risk — [SubSub](https://www.subsub.io/blog/inauthentic-content-why-so-many-creators-are-getting-demonetized); [AIR Media-Tech timeline](https://air.io/en/monetization/youtube-monetization-policy-changes-2026-a-complete-dated-timeline).
- One report claims that in January 2026, 16 channels with 35M subscribers were terminated under the inauthentic content policy. This is unverified against YouTube statements — [SubSub](https://www.subsub.io/blog/inauthentic-content-why-so-many-creators-are-getting-demonetized). The "AI slop" purge also catches human faceless creators — [The Next Web](https://thenextweb.com/news/youtube-ai-slop-crackdown-faceless-creators-collateral-damage).
- More careful sources and Reddit commenters say neither being faceless nor using AI is the trigger. Reused or repetitive content is — [Reddit snapshot (r/PartneredYoutube)](https://reddit.sentinel-team.org/subreddits/PartneredYoutube/snapshots/2026-01-27T08%3A01%3A14.653756Z); [Oakgen](https://oakgen.ai/blog/faceless-ai-channel-youtube-monetization-rules).
- Fully automated faceless channels carry platform-policy risk, which Vidrush reviewers flag — [AI Miracle](https://www.aimiracle.ai/ai-tool-review/vidrush-ai-review/).
- Billing complaints:
  - FacelessReels: billing surprises and slow refunds — [Websites2Know](https://websites2know.com/facelessreels-review/).
  - Vidnoz: credit consumption and expiry — [AIVidLab](https://aividlab.pages.dev/vidnoz-review).
  - InVideo: credits don't roll over, and reasoning consumed more than 30% of credits before rendering — [Magic Hour](https://magichour.ai/blog/invideo-ai-pricing).
  - Zernio: lifetime-deal backlash — [AppSumo](https://appsumo.com/products/late/reviews/?page=1).
- Quality issues: inconsistent visuals and characters (AutoShorts [Vidpros](https://vidpros.com/autoshorts-ai-review/); Revid [AutoGPT.net](https://autogpt.net/ai-tool/revid-ai/)). StoryShort narratives need tweaking — [AI Indigo](https://aiindigo.com/blog/storyshort-review-2026-the-reality-of-faceless-channel-automation).
- Features paid tools have:
  - Per-shot regeneration in StoryShort's AI Editor — [Gappsy](https://www.gappsy.com/tools/storyshort/).
  - A "dedicated AI agent" on Faceless.video Business ($275) — [Toolmage](https://www.toolmage.com/en/tool/faceless/).
  - TikTok-tuned hooks and Reddit import in Crayo — [Faceless.so compare](https://faceless.so/compare/crayo-vs-faceless).
  - MCP/CLI in Revid — [Revid pricing doc](https://www.revid.ai/llm/revid-ai-pricing-plans.md).
  - DM/comment "active contacts" in Blotato — [Upload-Post on Blotato](https://www.upload-post.com/blotato-pricing/).
  - Inbox and Analytics add-ons in Zernio — [PostPeer](https://www.postpeer.dev/blog/zernio-pricing-change-2026).
  - A competitor flags missing analytics as a weakness of ShortsFaceless, which implies analytics is an expected feature — [FlowShorts](https://flowshorts.app/blog/flowshorts-vs-shortsfaceless).

### Inferences
- Most of our 13 features are table stakes **functionally**. Our real moat is **deployment and economics**: local or self-host, no per-series or credit fees, bring-your-own LLMs and providers. Two further moats are **localization** (Vietnamese) and **Facebook Page + CapCut** workflow integration, which the faceless SaaS market doesn't address.
- To compete with paid tools, the highest-value additions look like these:
  1. An analytics feedback loop that pulls YouTube, TikTok and Facebook stats to pick and rotate topics.
  2. A/B hook variants.
  3. Series or channel memory for consistent characters and style.
  4. Optional avatar and dubbing providers via API (HeyGen, Captions/Mirage).
  5. An MCP/CLI interface like Revid's.

  No source verified trend research or A/B hooks in the paid tools themselves, so treat these as hypotheses (see Gaps).
- Policy risk applies equally to us and to the SaaS tools. Features that add originality help mitigate it: per-scene unique AI visuals, scripted rather than reused content, dedup, and human review before posting.

### Gaps
- No source confirmed **trend research**, **A/B hook testing**, or **analytics-driven topic selection** inside AutoShorts, StoryShort, Faceless.video, Crayo or Revid.
- Reddit threads specific to each tool (r/NewTubers, r/SideProject) were not retrievable. Only aggregated Reddit snapshots were found.
- The January 2026 YouTube termination figures (16 channels, 35M subscribers) are unverified against official YouTube communications.
