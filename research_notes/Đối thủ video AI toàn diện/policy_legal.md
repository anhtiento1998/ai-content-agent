# Policy, Monetization, Disclosure and Legal Rules for Automated AI Short Videos (YouTube / TikTok / Facebook; Vietnam / EU / US), as of November 2026

> Method note: WebFetch could not reach any page in this session. support.google.com, developers.google.com, developers.tiktok.com, eur-lex.europa.eu, transparency.meta.com and loc.gov all failed DNS under the session's network policy. All findings therefore come from search-result snippets and summaries, including snippets of official pages where the search engine returned them. Exact quotes should be re-checked against the primary pages before anyone relies on them. This is research, not legal advice. Each item is tagged **[LAW]**, **[PLATFORM POLICY]** or **[GUIDANCE/INDUSTRY]**.

## 1. YouTube: inauthentic and reused content, synthetic-content disclosure, AI music/voice, Shorts monetization

### Takeaway
YouTube does not ban AI. It demonetizes, and since January 2026 has terminated, channels that publish templated, mass-produced or near-identical videos. That describes the default output of an unvaried batch pipeline. Two things are separate:
- **Disclosure:** the "altered or synthetic" disclosure is required for *realistic* content and can be set programmatically with `status.containsSyntheticMedia` in the Data API.
- **Monetization thresholds:** these get stricter on 1 Feb 2027, when an ongoing 10M-views-per-90-days test applies before a channel shares in Shorts revenue.

### Cited Findings
- **[PLATFORM POLICY] Rename.** On 15 July 2025 YouTube renamed the YPP "repetitious content" policy to "inauthentic content" and clarified that it covers "content that is repetitive or mass-produced". YouTube described this as a minor clarification of rules that already existed. — [PPC Land](https://ppc.land/youtube-clarifies-inauthentic-content-policy-changes/); [Search Engine Journal](https://www.searchenginejournal.com/youtube-clarifies-monetization-update-targeting-spam-not-reaction-channels/550755/)
- **[PLATFORM POLICY] Examples on the official help page.** The page (answer 1311392) lists content that can lose monetization:
  - "image slideshows, templated storylines, or scrolling text with minimal or no narrative, commentary, or educational value"
  - repetitive content with low educational value
  - mass-produced content built on a template with little variation
  - direct readings of website or news text you did not create
  - songs altered only in pitch or speed

  YouTube's own illustrations of mass-produced content are "a channel that uploads narrated stories with only superficial differences between them" and "a channel that uploads slideshows that all have the same narration". YouTube says the list is not exhaustive. — [YouTube Help: channel monetization policies (via search snippet)](https://support.google.com/youtube/answer/1311392); [ThePrint summary](https://theprint.in/world/youtube-cracks-down-on-inauthentic-content-with-monetisation-policy-update-what-new-guidelines-say/2691562)
- **[PLATFORM POLICY] Reused content vs inauthentic content.** "Reused content" (repurposing someone else's content without significant original commentary, modification or value) is a separate rule. According to YouTube's Rene Ritchie, the July 2025 change does not affect legitimate reaction or clip-based videos. — [Search Engine Journal](https://www.searchenginejournal.com/youtube-clarifies-monetization-update-targeting-spam-not-reaction-channels/550755/)
- **[GUIDANCE/INDUSTRY] Scope.** The policy reportedly applies to Shorts, long-form and livestreams. One source claims enforcement uses metadata, content patterns and upload frequency, but this is unconfirmed by YouTube. — [subsub.io](https://www.subsub.io/blog/youtube-inauthentic-content-policy-2025); [exemplary.ai](https://exemplary.ai/blog/youtube-inauthentic-content-policy)
- **[GUIDANCE/INDUSTRY] Precedent.** In 2020 YouTube demonetized channels that used TTS voices to read Reddit stories, treating them as "mass-produced". — [YouTube help page/summary via search](https://www.subsub.io/blog/youtube-inauthentic-content-policy-2025)
- **[PLATFORM POLICY / enforcement] January 2026 terminations.** YouTube acted against 16 channels with about 35M subscribers and about 4.7B lifetime views under the inauthentic-content policy. Reports differ on the split: either 11 terminated and 5 wiped, or 11 terminated and 6 wiped. Estimated lost revenue is about $10M/yr. A figure of "130,000 channels" circulates only in aggregators and is unverified. — [TechTimes](https://www.techtimes.com/articles/320629/20260715/youtube-wiped-35m-subscribers-over-ai-slop-now-its-judging-your-taste.htm); [OutlierKit](https://outlierkit.com/resources/youtube-ai-slop-crackdown-2026/); [The Next Web](https://thenextweb.com/news/youtube-ai-slop-crackdown-faceless-creators-collateral-damage)
- **[GUIDANCE/INDUSTRY] Collateral damage.** Faceless creators who did not use AI report being demonetized, and the absence of an on-camera host is apparently treated as a proxy signal. — [The Next Web](https://thenextweb.com/news/youtube-ai-slop-crackdown-faceless-creators-collateral-damage); [Kompozy](https://kompozy.io/news/youtube-ai-detection-backlash)
- **[PLATFORM POLICY] CEO priorities for 2026.** Neal Mohan's annual letter of 21 Jan 2026 named "managing AI slop" and deepfake detection as top priorities. YouTube said it would:
  - extend its spam and clickbait systems to low-quality AI content
  - require clear labels on AI-made or altered content
  - expand likeness detection (launched Oct 2025 for eligible creators) to millions of creators

  — [eWeek](https://www.eweek.com/news/youtube-ai-slop-crackdown-creators/); [Tubefilter](https://www.tubefilter.com/2026/01/21/neal-mohans-2026-letter-to-creators-a-lot-of-ai-a-tiktok-shop-competitor-and-beautifully-produced-tv-to-compete-with-netflix/amp/); [RightsTech](https://rightstech.com/2026/01/youtube-chief-says-managing-ai-slop-is-a-priority-for-2026/)
- **[PLATFORM POLICY] Altered or synthetic disclosure.** Creators must disclose *meaningfully altered or synthetically generated content that seems realistic* at upload.
  - Viewers see a label in the expanded description. For sensitive topics (elections, conflicts, disasters, finance, health) the label appears on the player itself.
  - YouTube may apply the label proactively.
  - Consistent non-disclosure can lead to content removal, YPP suspension or other penalties.
  - Unrealistic content (e.g., animation or fantasy), minor edits, and AI used only for scripts or captions do not require disclosure.
  - According to YouTube documentation as reported, disclosing does not limit audience or monetization eligibility.

  — [YouTube Help 14328491 (via search)](https://support.google.com/youtube/answer/14328491); [NBC News](https://www.nbcnews.com/tech/tech-news/youtube-says-will-require-creators-label-ai-content-rcna143937); [Android Central](https://www.androidcentral.com/apps-software/youtube-ai-synthetic-content-disclosure); [Euronews](https://www.euronews.com/2023/11/14/youtube-creators-to-disclose-use-of-generative-ai-in-videos-or-risk-suspension)
- **[PLATFORM POLICY] Removal requests.** People can ask YouTube, through its privacy process, to remove synthetic content that simulates an identifiable individual's face or voice. — [Android Central](https://www.androidcentral.com/apps-software/youtube-ai-synthetic-content-disclosure)
- **[PLATFORM/API] Data API flag.** The YouTube Data API v3 added `status.containsSyntheticMedia` on **30 Oct 2024**. It is set via `videos.insert` or `videos.update` and returned in the video resource when set, which lets developers flag realistic altered or synthetic videos. — [YouTube Data API revision history](https://developers.google.com/youtube/v3/revision_history)
- **[PLATFORM/API] Unverified API projects.** Videos uploaded through `videos.insert` from unverified API projects created after **28 July 2020** are locked to private until the project passes a compliance audit. — [YouTube Data API videos.insert reference (via search)](https://Developers.Google.com/youtube/v3/docs/videos/insert); [Stack Overflow archive](https://kiwix.lema.org/stackoverflow.com_en_all_2023-11/questions/64079139/using-youtube-data-api-makes-my-videos-private-on-upload)
- **[PLATFORM POLICY] Shorts monetization from 1 Feb 2027.** YouTube's official Shorts monetization page (snippet) says that from **1 February 2027** a channel needs at least **10M qualified Shorts views in the previous 90 days** to share in that month's Shorts Creator Pool ad and Premium revenue.
  - Third-party guides say this test also applies to existing YPP partners.
  - They also say new YPP applicants will need 1,000 subscribers plus 8,000 qualified watch hours in 365 days or 20M qualified Shorts views in 90 days. This is up from the current 4,000 hours or 10M Shorts views.
  - The measurement window reportedly ends on the 15th of the previous month.

  — [YouTube Help: Shorts monetization policies](https://support.google.com/youtube/answer/12504220?hl=en); [vidIQ](https://vidiq.com/blog/post/youtube-partner-program-changes-2027/); [postfa.st](https://postfa.st/blog/youtube-monetization-requirements)
- **[PLATFORM POLICY] Shorts and music.**
  - Shorts longer than one minute that contain Content ID-claimed content are blocked and not monetizable.
  - A Short's share of the Creator Pool is "not affected by your use of a music track". Instead, revenue tied to a Short's views is split between the Creator Pool and music partners according to the number of tracks used.
  - One third-party guide's "50/50 split for one track" claim is unverified.

  — [YouTube Help 12504220](https://support.google.com/youtube/answer/12504220?hl=en); [Hootsuite](https://blog.hootsuite.com/youtube-shorts-monetization/)
- **[GUIDANCE/INDUSTRY] YouTube's own likeness tools.** YouTube is adding tools for creators to make Shorts with their own likeness and to "experiment with music". These will have to coexist with likeness detection. — [Tubefilter](https://www.tubefilter.com/2026/01/21/neal-mohans-2026-letter-to-creators-a-lot-of-ai-a-tiktok-shop-competitor-and-beautifully-produced-tv-to-compete-with-netflix/amp/)

### Inferences
- Batch-generated channels where every video shares the same template, voice, music bed and structure are exactly the official "mass-produced" examples. Variation across scripts, visuals, voices and structure, plus genuine narrative or educational value, is the main mitigating factor. Labeling does not cure inauthentic content: disclosure and monetization are evaluated separately.
- `status.containsSyntheticMedia` lets ai-content-agent automate disclosure. It should be set to true whenever a video contains *realistic* AI people, places, events or voices. It can stay false for clearly stylized or cartoon output, but defaulting to true is low-cost because disclosure reportedly does not reduce monetization.
- The project must pass the YouTube API audit, or every auto-uploaded video stays private.
- From Feb 2027, small channels under 10M Shorts views per 90 days earn nothing from the Shorts pool. Spreading output across many small channels becomes less viable economically, on top of the policy risk.

### Gaps
- I could not fetch the full current text of the YPP "inauthentic content" and "reused content" sections, or of help article 14328491. The exact wording above comes from snippets.
- I could not confirm whether YouTube has made a public statement on what share of the Jan 2026 terminations were AI-generated channels.
- I found no official YouTube page on AI-generated music specifically, such as whether Suno or Udio tracks are eligible for Content ID.
- I could not verify the 2027 YPP entry thresholds (8,000 hours / 20M views) against YouTube's own page. Only the 10M ongoing Shorts test appeared in an official snippet.

## 2. TikTok: AIGC labeling, C2PA auto-detection, unoriginal content and Creator Rewards, Content Posting API fields

### Takeaway
TikTok requires a label on realistic AI-generated content and auto-labels content that carries C2PA Content Credentials. Since Nov 2025 it also uses invisible watermarks and gives users an "AI content" slider that can reduce reach. Unoriginal content is ineligible for the Creator Rewards Program.

The Direct Post API exposes `is_aigc`, `brand_content_toggle` and `brand_organic_toggle` for video. Unaudited API clients can post only privately.

### Cited Findings
- **[PLATFORM POLICY] Labeling requirement.** TikTok has required creators to label realistic AIGC since 2023. In May 2024 it became the first major platform to auto-label AIGC from other platforms using C2PA Content Credentials metadata, starting with images and video, with audio to follow. TikTok also said it would attach Content Credentials to its own content so the label persists on re-upload. — [TikTok Newsroom, 9 May 2024](https://newsroom.tiktok.com/advancing-ai-transparency-and-literacy); [Tubefilter](https://tubefilter.com/2024/05/09/tiktok-transparency-labels-for-generative-ai-content/)
- **[PLATFORM POLICY] Community Guidelines update of 13 Sep 2025.** Realistic AI or heavily edited content must be disclosed, via the AI toggle, caption or sticker.
  - Synthetic media of private individuals is not allowed.
  - Synthetic media of public figures is barred when used for endorsements or when it breaks other rules. Sources disagree on whether the explicit endorsement language was retained.
  - Once applied, the AI label reportedly cannot be removed by the creator.

  — [TechCrunch, 15 Aug 2025](https://techcrunch.com/2025/08/15/tiktoks-new-guidelines-add-subtle-changes-for-live-creators-ai-content-and-more/); [WebProNews](https://www.webpronews.com/tiktok-overhauls-guidelines-ai-labels-misinfo-bans-start-sept-2025); [Gizbot](https://www.gizbot.com/internet/news/tiktok-bans-deepfakes-of-nonpublic-figures-and-fake-endorsements-in-latest-rule-refresh-084735)
- **[PLATFORM POLICY] Invisible watermarks and AI slider (Nov 2025).** TikTok added invisible watermarks, readable only by TikTok, to content made with its AI tools and to files carrying C2PA credentials, so labels survive re-upload. It also added an "AI-generated content" slider in Manage Topics that lets users see less AI content in For You. AI content cannot be blocked entirely, and the slider was described as experimental at launch. — [TechCrunch, 18 Nov 2025](https://techcrunch.com/2025/11/18/tiktok-now-lets-you-choose-how-much-ai-generated-content-you-want-to-see/); [TechSpot](https://www.techspot.com/news/110315-sick-ai-slop-feed-tiktok-finally-you-turn.html); [MacRumors](https://www.macrumors.com/2025/11/19/tiktok-ai-content-limits/)
- **[PLATFORM POLICY] Originality and Creator Rewards.** Per the TikTok Creator Academy originality policy, unoriginal content is ineligible for monetization programs such as the Creator Rewards Program, which uses "originality" as a key metric in its rewards formula. Its examples include:
  - content copied completely from others
  - content combined from multiple sources "with little or no additional information and/or content value"

  — [TikTok Creator Academy: Originality policy](https://www.tiktok.com/creator-academy/article/tiktok-originality-policy)
- **[GUIDANCE/INDUSTRY, conflicting] AI content and Creator Rewards.** Some blogs claim fully AI-generated core creative is ineligible for Creator Rewards. Others say AI-assisted, original, labeled content qualifies. Neither claim is clearly supported by TikTok's own text. Duets, Stitches and photo posts are commonly listed as non-paying formats. — [Storrito](https://storrito.com/resources/what-tiktoks-ai-monetization-restrictions-signal-for-creator-income/); [mintface.ai](https://mintface.ai/blog/tiktok-ai-content-policy-2026); [Kompozy](https://kompozy.io/creator-growth/tiktok-creator-rewards-program)
- **[PLATFORM/API] Direct Post video `post_info`.** The official reference describes these fields:
  - `brand_content_toggle`: true when the video is a paid partnership promoting a third-party business
  - `brand_organic_toggle`: true when the video promotes the creator's own business
  - `is_aigc`: true when the video is AI-generated content; the video is then labeled "Creator labeled as AI-generated" in its description

  The photo-post endpoint accepts the brand toggles but shows no `is_aigc`. One third-party guide says the inbox (draft) upload endpoint has no AIGC field. — [TikTok for Developers: Direct Post reference (via search)](https://developers.tiktok.com/doc/content-posting-api-reference-direct-post); [TikTok photo post reference](https://developers.tiktok.com/doc/content-posting-api-reference-photo-post); [adaptlypost](https://adaptlypost.com/blog/tiktok-ai-generated-label); [Upload-Post docs](https://docs.upload-post.com/guides/ai-content-labeling)
- **[PLATFORM/API] Labels are distinct.** The creator label set via `is_aigc` is separate from TikTok's automatic "AI-generated" label, which TikTok applies when it detects C2PA metadata or its own effects. The automatic label cannot be removed. — [adaptlypost](https://adaptlypost.com/blog/tiktok-ai-generated-label)
- **[PLATFORM/API] Unaudited clients.** "All content posted by unaudited clients will be restricted to private viewing mode" (error `unaudited_client_can_only_post_to_private_accounts`). An audit is required to lift this. Vendor guides add a cap of 5 users per 24 hours for unaudited apps. — [TikTok photo post reference (via search)](https://developers.tiktok.com/docs/en/content-posting-api-reference-photo-post); [Postiz docs](https://docs.postiz.com/self-host/providers/tiktok)

### Inferences
- ai-content-agent should set `is_aigc=true` on all TikTok video posts that contain AI visuals or voice. If its generators embed C2PA, TikTok will auto-label anyway, so a consistent self-label avoids a mismatch.
- The AI slider and the originality score in the rewards formula mean labeled AI batches face both reduced distribution and reduced payouts. Original value per video matters more than volume.
- If ai-content-agent publishes sponsored or affiliate content, it must set the brand toggles.
- Photo or slideshow posts cannot carry an API AIGC flag, so AI disclosure for them would have to go in the caption.

### Gaps
- I could not access the current Creator Rewards Program terms to confirm whether AI-generated content is explicitly addressed.
- The current status (Nov 2026) of the AI-content slider and of C2PA audio labeling is unconfirmed.
- I found no official TikTok statement on daily posting caps per account through the API, beyond the unaudited-client limits.

## 3. Meta (Facebook Pages / Reels): AI info label, C2PA/IPTC detection, unoriginal content crackdown, API fields

### Takeaway
Meta auto-labels content as "AI info" based on C2PA and IPTC signals. Its policy requires self-disclosure for photorealistic video and realistic audio, with possible penalties for failing to disclose. Separately, since July 2025 and with stricter guidance in March 2026, it has cut reach and monetization for unoriginal or reposted content. I found no documented Graph API field for AI disclosure.

### Cited Findings
- **[PLATFORM POLICY] Detection.** In Feb 2024 Meta said it would detect AI images through industry-standard invisible markers (C2PA and IPTC) and label them on Facebook, Instagram and Threads. — [SiliconANGLE](https://siliconangle.com/2024/02/06/meta-will-label-ai-generated-images-across-facebook-instagram-threads/); [TechCrunch](https://techcrunch.com/2024/02/06/meta-ai-generated-image-labelling/)
- **[PLATFORM POLICY] Mandatory self-disclosure.** Nick Clegg (Feb 2024): "We'll require people to use this disclosure and label tool when they post organic content with a photorealistic video or realistic-sounding audio that was digitally created or altered, and we may apply penalties if they fail to do so." Coverage described possible penalties ranging from warnings to removal. Clegg acknowledged that watermark detection for video and audio was not yet mature at scale. — [Cointelegraph](https://cointelegraph.com/news/meta-may-apply-penalties-generative-ai-artificial-intelligence-images); [Business Today](https://www.businesstoday.in/amp/technology/news/story/meta-announces-plans-to-combat-deepfakes-and-ai-generated-content-on-facebook-instagram-threads-ahead-of-key-elections-416458-2024-02-07)
- **[PLATFORM POLICY] Label name.** In 2024 the label was renamed from "Made with AI" to "AI info" after criticism. It can be triggered even by minor AI edits such as generative fill. — [Jang](https://jang.com.pk/en/15206-meta-replaces-made-with-ai-label-with-ai-info-amid-user-criticism-news); [Lilach Bullock](https://www.lilachbullock.com/why-instagram-ai-info-label/)
- **[PLATFORM POLICY] Ads.** Meta uses C2PA and similar signals to detect and label ads made or edited with third-party generative AI tools. — [Marketing Dive](https://marketingdive.com/news/sociable-meta-adds-updated-disclosure-tags-for-ai-generated-ads/824833)
- **[PLATFORM POLICY] Unoriginal content crackdown (July 2025).** Facebook accounts that repeatedly repost others' content without meaningful changes or credit lose monetization and get reduced distribution. Meta also tested attribution links that point duplicates to the original. — [Engadget](https://www.engadget.com/social-media/meta-says-its-cracking-down-on-facebook-creators-who-steal-content-203713569.html?src=rss); [iPhone in Canada](https://www.iphoneincanada.ca/2025/07/15/meta-crackdown-unoriginal-facebook-content/)
- **[PLATFORM POLICY] March 2026 guidance.** Meta's newsroom post "Rewarding Original Creators on Facebook" says it shifts reach and monetization toward original creators and has updated its original-content guidelines for Feed and Reels.
  - Per summaries, original means filmed or produced by the creator or Page owner, or a remix that adds substantive value.
  - Watch-alongs, reaction faces, stitched clips, narrating what is already on screen, and re-uploads with borders or captions count as unoriginal and are deprioritized.
  - Repeat offenders may become non-recommendable or lose monetization.
  - Meta says views and watch time for original Reels roughly doubled in H2 2025 compared with H2 2024.

  — [Meta Newsroom, Mar 2026](https://about.fb.com/news/2026/03/rewarding-original-creators-on-facebook/); [Relevant Audience](https://www.relevantaudience.com/general-topics/metas-new-rules-for-original-content/); [Search Engine World](https://www.searchengineworld.com/metas-cracks-down-on-unoriginal-content)
- **[PLATFORM POLICY] Monetization access.** Facebook Content Monetization is reportedly still invite-only. — [MonetizedYet](https://monetizedyet.com/facebook-monetization-requirements/)
- **[GUIDANCE/INDUSTRY] Enforcement criticism.** A petition with about 30,000 signatures alleges wrongful takedowns without human review. — [search summary of trade coverage](https://routenote.com/blog/meta-cracks-down-on-unoriginal-content/)

### Inferences
- Fully AI-generated, ai-content-agent-original videos are not "reposts", so the unoriginal-content rule mainly bites if the agent uses third-party footage, stock clips stitched together without commentary, or narration that merely describes the visuals.
- Embedding C2PA in outputs will trigger "AI info" labels automatically. That satisfies the self-disclosure expectation for photorealistic content.
- Because I found no Graph API AI-disclosure parameter, the product should rely on embedded C2PA/IPTC metadata plus a caption disclosure for Facebook.

### Gaps
- I found no source on a Graph API field for AI disclosure on Page video or Reels uploads. This should be checked directly in Meta developer docs, which were unreachable.
- Meta's published penalties for non-disclosure are unclear. One 2026 blog says they had still not been published as of an Oversight Board decision in March 2026, but this is unverified.
- I could not get the full text of the March 2026 originality guidelines.

## 4. Copyright and licensing: music, AI image/video outputs, TTS and voice cloning

### Takeaway
Licensing risk sits mostly in:
- **Music:** Content ID claims, AI music tiers, and the Suno and Udio settlements changing their terms.
- **Generator terms:** free tiers of Veo and Kling often bar commercial use.
- **Copyrightability:** purely AI outputs are not copyrightable in the US, so the operator cannot assert exclusive rights or register AI music in Content ID with confidence.

### Cited Findings
- **[GUIDANCE/INDUSTRY] Royalty-free libraries.** Epidemic Sound says a Content ID claim on its music means YouTube detected its track but could not verify a valid license. Subscribed channels must be safelisted. Royalty-free music does not automatically include public performance rights. — [Epidemic Sound Help](https://help.epidemicsound.com/hc/en-us/articles/26253712691730-Why-was-a-Content-ID-claim-received-from-Epidemic-Sound); [Epidemic Sound blog](https://www.epidemicsound.com/blog/how-we-handle-youtube-content-id-claims/)
- **[GUIDANCE/INDUSTRY] False claims.** Third parties can register licensed or Creative Commons tracks in Content ID after you have used them, producing false claims that can take months to unwind. — [Breaking Copyright](https://breakingcopyright.com/blog/how-to-dispute-false-youtube-copyright-claims); [lesfm](https://lesfm.net/blog/how-to-avoid-copyright-strikes-on-youtube)
- **[GUIDANCE/INDUSTRY] Suno and Warner.** Suno settled with Warner Music Group in Nov 2025 and struck a licensing deal.
  - Suno said free-tier songs would no longer be downloadable, paid tiers would get monthly download caps, and licensed models would launch in 2026 to replace the current ones.
  - One source says download caps took effect 3 Sep 2026 and apply retroactively; this is single-sourced.
  - UMG and Sony litigation against Suno reportedly continues.

  — [Billboard](https://www.billboard.com/pro/suno-warner-music-sign-ai-licensing-deal-settle-lawsuit/); [Music Business Worldwide](https://www.musicbusinessworldwide.com/warner-music-group-settles-with-suno-strikes-first-of-its-kind-deal-with-ai-song-generator/); [Forklog](https://forklog.com/en/suno-imposes-music-download-limits-amid-legal-and-content-concerns/)
- **[GUIDANCE/INDUSTRY] Suno rights by tier.** Paid Pro and Premier plans grant ownership and a commercial-use license for songs made while subscribed. Free-tier songs are non-commercial, and upgrading does not convert past free songs. A commercial license does not guarantee YouTube monetization or Content ID eligibility, since YouTube expects exclusive rights for reference files. — [terms.law Suno guide](https://terms.law/ai-output-rights/suno/); [Dynamoi](https://dynamoi.com/learn/ai-music-distribution/suno-commercial-rights-explained)
- **[GUIDANCE/INDUSTRY, conflicting] Udio.** Udio settled with UMG and Warner. Sources conflict on whether downloads are banned entirely or limited to paid users. — [Forklog](https://forklog.com/en/suno-imposes-music-download-limits-amid-legal-and-content-concerns/); [vinylculture](https://vinylculture.substack.com/p/the-ai-music-endgame-part-2-warner)
- **[GUIDANCE/INDUSTRY] OpenAI terms.** OpenAI's terms assign to the user OpenAI's rights in outputs "if any". Outputs may not be unique, and other users can receive similar output. — [ConductAtlas: OpenAI ToU](https://conductatlas.com/platform/openai/openai-terms-of-use/output-ownership-assignment/); [terms.law](https://terms.law/ai-output-rights/chatgpt/)
- **[GUIDANCE/INDUSTRY] Google Veo and Imagen.** Users reportedly own outputs subject to Google's terms. Free and consumer tiers may restrict commercial use, while paid Vertex AI or Gemini API access permits it. Outputs carry an invisible SynthID watermark. Sources are inconsistent, so check the current Gemini API and Vertex terms. — [CIPIT](https://cipit.org/from-prompt-to-video-the-ip-puzzle-behind-googles-veo-3); [Google AI developer forum](https://discuss.ai.google.dev/t/inquiry-about-commercial-use-of-videos-generated-via-google-labs-flow-free-tier-for-a-contest/169174); [flowith](https://flowith.io/blog/veo-faq-commercial-rights-watermarks)
- **[GUIDANCE/INDUSTRY] Kling.**
  - Kling's ToS reportedly grant Kling a broad license over inputs and outputs, including for training and promotion.
  - One version reportedly bars commercial use of output without written permission (s. 4.6), while the paid-member terms reportedly allow commercial use.
  - Free-tier outputs reportedly do not become commercial after an upgrade.

  — [ConductAtlas: Kling ToS](https://conductatlas.com/platform/kling-ai/kling-ai-terms-of-service/); [bloomeria](https://bloomeria.jp/blog/kling-ai-commercial-use); [WaveSpeed](https://wavespeed.ai/blog/video-model-access/can-i-use-kling-ai-api-for-commercial-projects/)
- **[LAW, US guidance] Copyrightability.** US Copyright Office Report Part 2 (29 Jan 2025): copyright requires human authorship, and prompts alone are insufficient. Human selection, arrangement or modification can be protected, and AI material does not void protection of the larger human-authored work. — [Sidley Data Matters](https://datamatters.sidley.com/2025/02/07/u-s-copyright-office-issues-report-on-artificial-intelligence-and-copyrightability/); [Mintz](https://www.mintz.com/insights-center/viewpoints/54731/2025-02-07-us-copyright-office-publishes-second-part-report-ai)
- **[LAW, US federal pending] NO FAKES Act.** The bill would create a federal right over digital replicas of voice and likeness. The Senate Judiciary Committee advanced it unanimously on 18 June 2026. A unanimous-consent floor attempt reportedly drew an objection from Sen. Cruz on 30 Sep 2026; this is single-sourced. It is not law. — [IIPLA](https://iipla.org/news/senate-judiciary-committee-unanimously-advances-no-fakes-act-to-combat-ai-deepfakes-and-voice-cloning); [MLex](https://www.mlex.com/mlex/artificial-intelligence/articles/2491616); [aimusicpreneur](https://www.aimusicpreneur.com/ai-music-industry/riaa-mitch-glazier-no-fakes-act-lame-duck-cruz-objection-2026/)
- **[LAW, US state] Tennessee ELVIS Act.** It is in force and covers AI voice clones of performers. — [voxbooster roundup (secondary)](https://voxbooster.com/blog/voice-cloning-legal-cases-2026-roundup/)

### Inferences
- **Music.** ai-content-agent should track, for every music asset: source, license ID, plan tier at the time of generation, whether the license covers YouTube, TikTok and Meta, and any safelisting status. Suno or Udio tracks should be used only from paid tiers, with records of the subscription date. Platform-native libraries are safer for TikTok and Meta. TikTok's Commercial Music Library could not be verified here.
- **Generators.** API and paid tiers should be required, and the provider and tier logged per asset.
- **Voices.** Use only stock TTS voices whose commercial license covers social platforms. Cloned voices of real people require documented consent. Under Vietnam Decree 142, and under EU and TikTok rules, simulating a real person's voice also triggers mandatory labeling or prohibition.

### Gaps
- I could not retrieve ElevenLabs, Google TTS or Vietnamese TTS vendor terms on commercial voice rights and cloning consent.
- I found no authoritative source on TikTok's Commercial Music Library use through the Content Posting API.
- Vietnam's position on the copyrightability of AI output was not covered. Tilleke has a piece on a new copyright decree in the AI era, but its content was not retrieved.

## 5. Law: Vietnam

### Takeaway
Vietnam now has binding AI-labeling law in three layers, all in force by November 2026:
- the Law on Digital Technology Industry (from 1 Jan 2026)
- the AI Law 134/2025/QH15 (from 1 Mar 2026)
- Decree 142/2026/NĐ-CP (from 1 May 2026), which requires *deployers* to apply visible labels to AI audio, images or video that simulate real people's appearance or voice, or recreate real events

Decree 147/2024 separately requires phone- or ID-verified accounts and 24-hour takedowns.

### Cited Findings
- **[LAW] AI Law No. 134/2025/QH15.** Passed 10 Dec 2025 (429 of 434 deputies present) and in force 1 Mar 2026.
  - Art. 11(2): providers must mark AI-generated audio, images and video in a machine-readable format.
  - Art. 11(3)/(4): deployers must notify users and apply easily identifiable labels when publishing AI-generated or edited content that simulates real people or recreates real events in a way that could mislead.
  - Transition periods for existing systems are reported inconsistently: 12 months, to 1 Mar 2027, or 18 months for critical sectors, to 1 Sep 2027.

  — [Duane Morris](https://blogs.duanemorris.com/vietnam/2026/03/03/vietnam-the-first-law-on-artificial-intelligence-what-you-must-know/); [Báo Nghệ An](https://baonghean.vn/en/viet-nam-bat-buoc-gan-nhan-noi-dung-ai-tu-thang-3-nam-2026-theo-luat-tri-tue-nhan-tao-10325945.html); [Baker McKenzie](https://connectontech.bakermckenzie.com/vietnams-first-standalone-ai-law-an-overview-of-key-provisions-future-implications/); [casrai](https://casrai.org/guides/vietnam-ai-law-134-2025)
- **[LAW] Penalties under the AI Law.** Baker McKenzie says the Law itself contains no administrative-sanction framework and defers this to a government decree. Other sources mention administrative or criminal liability depending on severity. — [Baker McKenzie](https://connectontech.bakermckenzie.com/vietnams-first-standalone-ai-law-an-overview-of-key-provisions-future-implications/)
- **[LAW] Decree 142/2026/NĐ-CP.** Issued 30 Apr 2026, in force 1 May 2026, implementing the AI Law.
  - Art. 18(2): deployers must apply easily recognizable labels in two cases: (i) content simulating the appearance or voice of a real person; (ii) content recreating real events, so viewers can tell it apart from real content.
  - Art. 18(4): lists four narrow exemption groups (details not retrieved).
  - The party that creates or edits the content must supply the information the publishing party needs to label it.
  - The Ministry of Science and Technology (MOST) will publish technical reference guidance on the form of labels and notices.

  — [lsvn.vn](https://lsvn.vn/thong-bao-va-gan-nhan-nhan-biet-noi-dung-do-ai-tao-ra-the-nao-a172678.html); [Báo Pháp luật](https://doanhnhan.baophapluat.vn/gan-nhan-hien-thi-doi-voi-noi-dung-do-ai-tao-ra-phai-bao-dam-cac-yeu-cau-nao-d87d1db9.html); [Atsumi & Sakai newsletter](https://www.aplawjapan.com/newsletter/20260528); [LuatVietnam](https://luatvietnam.vn/legal-updates/mandatory-labels-required-for-ai-generated-content-892-109041-article.html); [Tilleke & Gibbins](https://www.tilleke.com/insights/vietnam-takes-major-step-in-ai-governance-with-new-guiding-decree/9/)
- **[GUIDANCE/INDUSTRY] Industry pushback.** Businesses have proposed adjusting the AI-labeling rules. — [VnEconomy](https://vneconomy.vn/doanh-nghiep-de-xuat-dieu-chinh-quy-dinh-gan-nhan-noi-dung-do-ai-tao-ra.htm)
- **[LAW] Law on Digital Technology Industry No. 71/2025/QH15.** Passed 14 June 2025, in force 1 Jan 2026. Art. 44 requires identification markings on AI-generated digital products so that users or detection systems can recognize them. The MOST Minister issues the list of AI-created digital technology products in scope (Art. 44(3)). — [VietNamNet](https://vietnamnet.vn/en/vietnam-mandates-ai-generated-content-labels-starting-in-2026-2424484.html); [LuatVietnam (English text)](https://english.luatvietnam.vn/law-on-digital-technology-industry-no-71-2025-qh15-dated-june-14-2025-of-the-national-assembly-405695-doc1.html); [thuvienphapluat](https://thuvienphapluat.vn/van-ban/Cong-nghe-thong-tin/Law-71-2025-QH15-Digital-Technology-Industry-668801.aspx); [Viet An Law](https://vietanlaw.com/identifying-ai-products-in-vietnam/)
- **[LAW] Decree 147/2024/NĐ-CP (internet services), in force 25 Dec 2024.**
  - Social-network accounts, including on foreign platforms, must be authenticated with a Vietnamese mobile number, or a personal ID number if the user has no Vietnamese number. Existing accounts had 90 days.
  - Only authenticated accounts may post, comment, livestream or share.
  - Platforms must remove violating content within 24 hours of a request from competent authorities. A 48-hour window applies to user complaints, according to one summary.
  - Foreign platforms with more than 100,000 monthly visits from Vietnam, or with servers in Vietnam, must notify the Ministry of their contact details.

  — [LuatVietnam](https://luatvietnam.vn/legal-updates/social-network-user-accounts-to-be-verified-with-subscriber-phone-numbers-892-100003-article.html); [Vietnam News](https://vietnamnews.vn/society/1666838/social-network-users-must-authenticate-accounts-from-december-25.html); [Allen & Gledhill](https://www.allenandgledhill.com/perspectives/articles/29440/vnkh-vietnam-introduces-additional-requirements-relating-to-provision-of-information-and-internet-services); [DFDL](https://www.dfdl.com/insights/legal-and-tax-updates/vietnam-more-requirements-on-internet-service-and-online-information/)
- **[LAW] Decree 330/2026/NĐ-CP.** Covers administrative penalties for cybersecurity and personal-data violations, not AI labeling specifically. — [search summary](https://www.aplawjapan.com/publications/20260528)

### Inferences
- A Vietnamese operator using ai-content-agent is a "deployer" under Decree 142. For content that depicts realistic people, AI voices imitating real people, or reconstructed news or historical events, a visible label is legally required, not just a platform preference.
- Because the creator must pass labeling information downstream, ai-content-agent should keep per-video provenance records: models used and which elements are AI-generated.
- Each publishing account used for Vietnamese audiences must be phone- or ID-verified under Decree 147. Bulk unverified accounts are non-compliant.
- Takedown requests reach operators via the platforms within 24 hours, so the product needs a fast unpublish or delete function across all channels.

### Gaps
- I could not retrieve the full text of Decree 142 Art. 18(4) exemptions, the MOST technical labeling guidance, the Art. 44(3) product list, or a specific administrative fine schedule for AI-labeling breaches. Some sources also cite Art. 12 instead of Art. 18, so the numbering is uncertain.
- I could not resolve whether stylized or non-realistic AI faceless content, such as cartoon visuals with a generic TTS voice, falls outside the two mandatory cases. This appears likely but is unconfirmed.

## 6. Law: EU AI Act Article 50

### Takeaway
Article 50 transparency obligations have applied since **2 August 2026**. Under Art. 50(4), *deployers* must disclose deepfake image, audio or video, with a lighter regime for evidently artistic, satirical or fictional works. Under Art. 50(2), *providers* of generative systems must machine-mark outputs. Providers of systems already on the market before 2 Aug 2026 reportedly have until **2 Dec 2026** for marking. A Commission Code of Practice on marking and labelling, and Art. 50 guidelines, were published in mid-2026.

### Cited Findings
- **[LAW] Application date.** Article 50 applies from 2 Aug 2026. Several sources say the Digital Omnibus did not amend Art. 50 itself. — [Usercentrics](https://usercentrics.com/knowledge-hub/eu-ai-act-high-risk-delay-article-50-transparency-consent/); [Paul Weiss](https://www.paulweiss.com/insights/client-memos/eu-finalises-transparency-rules-for-ai-generated-content)
- **[LAW, reported] Marking grace period.** Systems placed on the market before 2 Aug 2026 have until **2 Dec 2026** to meet Art. 50(2) marking; new systems must comply when placed on the market. One source cites 2 Feb 2027 for watermark-detection interoperability. Content generated before 2 Aug 2026 reportedly needs no retroactive labeling.
  - Sources report the Digital Omnibus as Regulation (EU) 2026/1744, published in the OJ 24 Jul 2026 and in force 27 Jul 2026. Earlier sources describe only the political deal of 7 May 2026. I could not verify the OJ publication directly.

  — [aiacto.eu](https://www.aiacto.eu/en/blog/digital-omnibus-ai-act-report-2027); [Usercentrics](https://usercentrics.com/knowledge-hub/eu-ai-act-high-risk-delay-article-50-transparency-consent/); [Winston Taylor](https://www.winstontaylor.com/insights/ai-act-rules-on-high-risk-ai-delayed-as-ai-digital-omnibus-agreed)
- **[GUIDANCE] Code of Practice on marking and labelling AI-generated content.** Final version published 10 June 2026 per one source, or 20 July 2026 per another. Commission Art. 50 guidelines reportedly came out 20 July 2026.
  - Providers must use at least two machine-readable techniques, such as signed metadata plus imperceptible watermarking, and must bar users from stripping the metadata.
  - Short text of about 150 words is exempt.

  — [Paul Weiss](https://www.paulweiss.com/insights/client-memos/eu-finalises-transparency-rules-for-ai-generated-content); [archivemacropolo](https://archivemacropolo.org/analysis/eu-ai-act-article-50-watermarking-mandate)
- **[LAW] Art. 50(4) deepfakes.** Deployers of systems that generate or manipulate deepfake image, audio or video must disclose that it is artificial. For evidently artistic, creative, satirical or fictional works, disclosure is limited to an appropriate form that does not hamper enjoyment of the work: reduced, not eliminated.
  - For AI text published to inform the public on matters of public interest, disclosure is required unless the text underwent human review or editorial control and someone holds editorial responsibility. The Commission guidelines reportedly read this exception narrowly.

  — [ai-act-law.eu Art. 50](https://ai-act-law.eu/article/50/); [McCann FitzGerald](https://www.mccannfitzgerald.com/knowledge/data-privacy-and-cyber-risk/ai-transparency-european-commissions-guidelines-on-article-50-part-2-deployer-obligations); [SRD Rechtsanwälte](https://www.srd-rechtsanwaelte.de/en/blog/deepfake-labelling-under-the-ai-act-what-the-new-eu-guidance-clarifies)

### Inferences
- If ai-content-agent videos reach EU audiences, the operator as deployer must label any deepfake-like realistic content.
- AI-generated narration scripts on news or public-interest topics need either disclosure or a documented human editorial review. That directly supports a human-approval queue with an audit log.
- ai-content-agent itself, if offered as a generative system to third parties in the EU, may be a "provider" under Art. 50(2). It would then need to embed machine-readable marks such as C2PA plus a watermark in its outputs.

### Gaps
- I could not verify exact Article 50 text or Art. 99 fine levels from EUR-Lex, which was unreachable. Secondary sources generally describe fines for transparency breaches as up to €15M or 3% of turnover, but that was not confirmed in this session.
- I could not confirm the Omnibus OJ publication or the Code of Practice final date.

## 7. Law: United States (FTC, state AI disclosure, political deepfakes)

### Takeaway
There is no general US federal AI-labeling law for organic video. The relevant rules are:
- **FTC:** the rule against fake or AI-generated reviews and testimonials.
- **California:** the AI Transparency Act, operative 2 Aug 2026 for GenAI providers, with platform provenance duties from 1 Jan 2027.
- **Synthetic performers in ads:** New York (in force 9 June 2026) and California SB 1050 (from 1 Jan 2027).
- **Political deepfakes:** laws in about 31 states, several of them enjoined.

### Cited Findings
- **[LAW] FTC Consumer Reviews and Testimonials rule (16 CFR Part 465).** In effect 21 Oct 2024; one source says 13 Oct.
  - Bans fake or false reviews and testimonials, including AI-generated ones and reviews from people who do not exist.
  - Bans buying reviews, undisclosed insider reviews, and fake social-influence indicators.
  - Civil penalties of up to $53,088 per violation after the Jan 2025 adjustment. The FTC has sent warning letters.

  — [Morgan Lewis](https://www.morganlewis.com/pubs/2024/08/ftc-issues-final-rule-on-consumer-reviews-and-testimonials); [Fenwick](https://www.fenwick.com/insights/publications/the-ftc-cracks-down-on-fake-reviews-with-new-rule); [JD Supra](https://www.jdsupra.com/legalnews/five-stars-zero-tolerance-ftc-turns-up-3594404/)
- **[LAW] California AI Transparency Act (SB 942 as amended by AB 853, signed 13 Oct 2025).**
  - Operative 2 Aug 2026 for covered GenAI providers, which must provide latent disclosures and detection tools.
  - From 1 Jan 2027, large online platforms must detect standards-compliant provenance data where feasible, make it viewable to users, and not knowingly strip it.
  - Capture-device obligations start 1 Jan 2028.
  - The definition of "large online platform" is reported inconsistently.

  — [Sidley AI Monitor PDF](https://www.sidley.com/en/-/media/resource-pages/ai-monitor/laws-and-regulations/cal-ab853-california-ai-transparency-act.pdf?la=en); [Crowell](https://www.crowell.com/en/insights/client-alerts/californias-ai-transparency-act-caita-may-be-amended-to-regulate-social-media-platforms); [OneTrust](https://www.onetrust.com/blog/california-ai-transparency-act-requirements-deadlines-and-compliance-steps/)
- **[LAW] New York synthetic performer disclosure (GBL §396-b, S.8420-A).** In effect 9 June 2026. Ads must conspicuously disclose synthetic performers when the producer has actual knowledge. Audio-only ads are excluded. — [FRB Law](https://frblaw.com/new-yorks-synthetic-performer-disclosure-law-a-guide-to-the-nations-first-ai-advertising-rule/); [Crowell](https://www.crowell.com/en/insights/client-alerts/california-follows-new-yorks-lead-in-requiring-ai-synthetic-performer-disclosures-in-advertising)
- **[LAW] California SB 1050.** Signed 16 Sep 2026, effective 1 Jan 2027. Ads that prominently include a synthetic performer need a clear and conspicuous disclosure, such as "this performance features a synthetic performer". Audio ads are covered. — [Skadden](https://www.skadden.com/insights/publications/2026/10/california-joins-new-york-in-regulating-ai); [BakerHostetler](https://www.bakerlaw.com/insights/roll-the-disclosures-california-enacts-synthetic-performer-disclosure-law/)
- **[LAW] Political deepfakes.**
  - About 31 states regulate election deepfakes per NCSL (June 2026); Ballotpedia counted 28 as of Jan 2026. Many apply within 90 days of an election, and Colorado and Utah require metadata disclosures.
  - California AB 2655 is permanently enjoined as to X and Rumble on Section 230 grounds. AB 2839 is enjoined on First Amendment grounds in Kohls v. Bonta. Hawaii's Act 191 was struck down in Babylon Bee v. Lopez.

  — [Covington PDF, Sep 2026](https://www.cov.com/-/media/files/corporate/publications/2026/09/what-state-ai-election-laws-mean-for-the-2026-midterms.pdf); [MultiState](https://www.multistate.ai/updates/vol-107-state-political-deepfake-laws); [Ballotpedia](https://ballotpedia.org/Deepfake_policy_in_the_United_States,_2019_-_Present); [Wiley](https://www.wiley.law/alert-AI-Restrictions-in-Political-Ads-What-to-Know-About-Deepfake-Disclaimers-and-Bans)

### Inferences
- For US audiences, the main legal exposure is commercial:
  - AI "customer testimonials" or fake reviews in affiliate or promotional videos are banned outright.
  - AI human presenters in ads trigger NY and CA synthetic-performer disclosures.
- Political or election topics near elections should be blocked or force-labeled.
- From 2027, California-scale platforms will surface C2PA data. Embedded provenance will become visible to viewers, so the product should not strip it.

### Gaps
- I did not verify FTC Endorsement Guides specifics on AI influencers, or whether any FTC action has targeted AI-generated video ads.
- The exact definition of "large online platform" and "covered provider" thresholds in CA AB 853 is unconfirmed.

## 8. Concrete product implications for ai-content-agent (feature list with rationale)

### Takeaway
To stay compliant and monetizable, ai-content-agent should move from "batch auto-publish" to "batch generate, then label, vary, human-approve, then publish at a cadence". It needs per-asset provenance and license records, platform-specific AI flags set through the APIs, and C2PA embedding. Each feature below maps to a documented rule.

### Cited Findings
- **AI disclosure flags on upload.**
  - YouTube: set `status.containsSyntheticMedia=true` via `videos.insert` for realistic AI content. — [YouTube Data API revision history](https://developers.google.com/youtube/v3/revision_history)
  - TikTok: set `post_info.is_aigc=true`, plus the brand toggles for promotional content. — [TikTok Direct Post reference](https://developers.tiktok.com/doc/content-posting-api-reference-direct-post)
  - Facebook: no API field was found, so rely on C2PA/IPTC auto-labeling plus a caption disclosure. — [SiliconANGLE](https://siliconangle.com/2024/02/06/meta-will-label-ai-generated-images-across-facebook-instagram-threads/)
- **C2PA metadata embedding and preservation.** TikTok and Meta auto-label from C2PA/IPTC. The EU Code of Practice expects at least two marking techniques and prohibits stripping. California platforms must surface provenance from 2027. Vietnam's AI Law Art. 11(2) requires machine-readable marking by providers. — [TikTok Newsroom](https://newsroom.tiktok.com/advancing-ai-transparency-and-literacy); [Paul Weiss](https://www.paulweiss.com/insights/client-memos/eu-finalises-transparency-rules-for-ai-generated-content); [Sidley](https://www.sidley.com/en/-/media/resource-pages/ai-monitor/laws-and-regulations/cal-ab853-california-ai-transparency-act.pdf?la=en); [Duane Morris](https://blogs.duanemorris.com/vietnam/2026/03/03/vietnam-the-first-law-on-artificial-intelligence-what-you-must-know/)
- **Visible on-video or caption label for Vietnam and the EU.** This is mandatory where content simulates real people or voices or recreates real events (Decree 142 Art. 18(2); EU Art. 50(4)). — [lsvn.vn](https://lsvn.vn/thong-bao-va-gan-nhan-nhan-biet-noi-dung-do-ai-tao-ra-the-nao-a172678.html); [McCann FitzGerald](https://www.mccannfitzgerald.com/knowledge/data-privacy-and-cyber-risk/ai-transparency-european-commissions-guidelines-on-article-50-part-2-deployer-obligations)
- **Human approval queue with an audit log.** Human review supports the EU Art. 50(4) text exception for public-interest narration and counters the "no human creative input" pattern targeted in YouTube's Jan 2026 terminations. — [SRD Rechtsanwälte](https://www.srd-rechtsanwaelte.de/en/blog/deepfake-labelling-under-the-ai-act-what-the-new-eu-guidance-clarifies); [OutlierKit](https://outlierkit.com/resources/youtube-ai-slop-crackdown-2026/)
- **Originality and variation engine.** It should avoid the officially listed signals: same template, same narration, slideshow or scrolling text without narrative, superficial differences between videos. It should also track a similarity score across a channel's videos. — [YouTube Help 1311392](https://support.google.com/youtube/answer/1311392); [TikTok originality policy](https://www.tiktok.com/creator-academy/article/tiktok-originality-policy)
- **No unlicensed third-party footage or stitched clips.** Meta's March 2026 guidance and YouTube's reused-content rule demote or demonetize this. — [Meta Newsroom](https://about.fb.com/news/2026/03/rewarding-original-creators-on-facebook/)
- **Music license tracking.** Record source, license ID, plan tier, generation date and safelisting status for every track. Keep Shorts using claimed music to 60 seconds or less, since longer ones are blocked. Use only paid-tier Suno output and keep subscription proof. — [YouTube Help 12504220](https://support.google.com/youtube/answer/12504220?hl=en); [Epidemic Sound](https://help.epidemicsound.com/hc/en-us/articles/26253712691730-Why-was-a-Content-ID-claim-received-from-Epidemic-Sound); [terms.law Suno](https://terms.law/ai-output-rights/suno/)
- **Generator and TTS license registry.** Log provider, model, tier and whether commercial use is allowed. Block free-tier Veo or Kling outputs from publishing. — [ConductAtlas Kling](https://conductatlas.com/platform/kling-ai/kling-ai-terms-of-service/); [CIPIT](https://cipit.org/from-prompt-to-video-the-ip-puzzle-behind-googles-veo-3)
- **Voice-likeness safeguards.** Block cloning of real people's voices without stored consent. Prohibit synthetic depictions of private individuals and public-figure endorsements, per TikTok guidelines, NO FAKES (pending) and the ELVIS Act. — [TechCrunch](https://techcrunch.com/2025/08/15/tiktoks-new-guidelines-add-subtle-changes-for-live-creators-ai-content-and-more/); [IIPLA](https://iipla.org/news/senate-judiciary-committee-unanimously-advances-no-fakes-act-to-combat-ai-deepfakes-and-voice-cloning)
- **Topic guardrails.** Force a prominent label or human review for elections, conflict, disasters, finance and health, where YouTube shows the label on the player. Block political deepfakes. Ban AI testimonials and fake reviews (FTC Part 465). — [Android Central](https://www.androidcentral.com/apps-software/youtube-ai-synthetic-content-disclosure); [Morgan Lewis](https://www.morganlewis.com/pubs/2024/08/ftc-issues-final-rule-on-consumer-reviews-and-testimonials)
- **Account and API compliance.**
  - Pass the YouTube API audit; otherwise uploads stay private.
  - Pass the TikTok Content Posting audit; otherwise posts are private-only and capped at 5 users per 24 hours.
  - Verify Vietnamese accounts by phone or ID under Decree 147.

  — [videos.insert](https://Developers.Google.com/youtube/v3/docs/videos/insert); [TikTok photo post reference](https://developers.tiktok.com/docs/en/content-posting-api-reference-photo-post); [LuatVietnam](https://luatvietnam.vn/legal-updates/social-network-user-accounts-to-be-verified-with-subscriber-phone-numbers-892-100003-article.html)
- **Fast takedown and unpublish across platforms.** Needed to meet Vietnam's 24-hour authority requests under Decree 147. — [Allen & Gledhill](https://www.allenandgledhill.com/perspectives/articles/29440/vnkh-vietnam-introduces-additional-requirements-relating-to-provision-of-information-and-internet-services)
- **Monetization planner.** Model the YouTube Shorts 10M-qualified-views-per-90-days test from 1 Feb 2027 per channel, and favor fewer, stronger channels. — [YouTube Help 12504220](https://support.google.com/youtube/answer/12504220?hl=en); [vidIQ](https://vidiq.com/blog/post/youtube-partner-program-changes-2027/)

### Inferences
- **Per-account cadence limits.** No platform publishes a numeric daily cap for organic posting. One unconfirmed source says upload frequency is a YouTube enforcement signal. Cadence limits plus jitter are a reasonable precaution, not a documented rule.
- **Default-on disclosure.** YouTube reportedly does not penalize disclosure, while all three platforms penalize non-disclosure. Disclosure should therefore be on by default, with opt-out only for clearly non-realistic styles.
- **Provenance record per video.** Models, AI elements, music license, voice license and human reviewer. One record set serves four needs: Vietnam's Decree 142 information-passing duty, EU deployer documentation, platform appeals, and Content ID disputes.

### Gaps
- None of the platforms publish numeric thresholds for "too similar" content or for upload frequency, so variation targets cannot be calibrated from primary sources.
- I could not verify whether YouTube's or TikTok's flags are honored when C2PA metadata conflicts with the API flag, for example C2PA present but `is_aigc=false`.
