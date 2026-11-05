# Technical building blocks for ai-content-agent (as of 2026-11-04/05)

Method note: Licenses were read directly from each repo's LICENSE file on GitHub raw (`raw.githubusercontent.com/<repo>/HEAD/LICENSE*`) on 2026-11-04. Feature, VRAM and speed claims come from each project's README, fetched raw the same day. These hosts were blocked by the session's network policy: **huggingface.co** (proxy 403, so model-card licenses were not read directly), **ai.google.dev**, **www.remotion.dev** and **elevenlabs.io** (DNS blocked). cloud.google.com returned a truncated page. Prices therefore come from third-party aggregators and are flagged as such. "Code license" and "weights license" are kept separate on purpose, because they often differ.

## Q1. Word-level caption alignment (WhisperX, faster-whisper, stable-ts, MFA, aeneas, TTS-native timestamps; Vietnamese; karaoke ASS)

### Takeaway
Two options work for Vietnamese today, are permissively licensed, and need no change of TTS provider:
- **Align our own TTS audio against the known script.** Our audio is synthetic and we already have the exact text, so a forced alignment is enough. Tools: stable-ts `align()` (MIT), or WhisperX alignment, which uses the default Vietnamese wav2vec2 model `nguyenvulebinh/wav2vec2-base-vi-vlsp2020`.
- **Use Edge TTS word boundaries.** Call it with `boundary="WordBoundary"` explicitly, because the library now defaults to `SentenceBoundary`.

Then generate ASS `\k`/`\kf` karaoke tags from the word timings. aeneas is AGPL-3.0, so avoid it in a distributed app.

### Cited Findings
- **WhisperX** is BSD-2-Clause. [LICENSE](https://github.com/m-bain/whisperX/blob/main/LICENSE)
  - It uses forced alignment with phoneme-based wav2vec2 models to get word-level timings. The README notes that Whisper's native timestamps are utterance-level and "can be off by several seconds". [README](https://github.com/m-bain/whisperX)
  - Its v3 batched faster-whisper backend claims 70x realtime with large-v2. That backend needs under 8 GB of GPU memory at beam_size=5, and GPU use needs CUDA toolkit 12.8. [README](https://github.com/m-bain/whisperX)
  - A 2026 "Context-Aware Batching" update improves punctuation and proper nouns. [README](https://github.com/m-bain/whisperX)
  - Limitations: tokens with characters missing from the align model's dictionary (e.g. "2014.", "£13.60") get no timing. Overlapping speech is poorly handled. Each language needs its own wav2vec2 model. [README](https://github.com/m-bain/whisperX)
- **WhisperX Vietnamese:** `alignment.py` maps `"vi": 'nguyenvulebinh/wav2vec2-base-vi-vlsp2020'` in `DEFAULT_ALIGN_MODELS_HF`, so Vietnamese alignment works out of the box. [alignment.py](https://github.com/m-bain/whisperX/blob/main/whisperx/alignment.py)
- **stable-ts** is MIT. [LICENSE](https://github.com/jianfch/stable-ts/blob/main/LICENSE)
  - It provides alignment of a known transcript to audio, word regrouping (`regroup`), and VAD/denoise preprocessing for timestamps. [README](https://github.com/jianfch/stable-ts)
  - A Medium article describes adding timestamps to TTS output by re-running Whisper or stable-ts on the generated audio, because most TTS engines do not return word timings. [Medium](https://bar-offner.medium.com/syncing-speech-with-text-adding-timestamps-to-text-to-speech-using-python-13fe433b30a0)
- **faster-whisper** is MIT. [LICENSE](https://github.com/SYSTRAN/faster-whisper/blob/master/LICENSE)
- **Montreal Forced Aligner** is MIT. [LICENSE](https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner/blob/main/LICENSE)
- **aeneas** is **GNU AGPL-3.0**. [LICENSE](https://github.com/readbeyond/aeneas/blob/master/LICENSE)
- **Edge TTS (`edge-tts` Python):** licensed **LGPLv3**, except `srt_composer.py`, which is MIT. [LICENSE](https://github.com/rany2/edge-tts/blob/master/LICENSE)
  - In current source, `Communicate(..., boundary: Literal["WordBoundary","SentenceBoundary"] = "SentenceBoundary")`. Word-level metadata is only requested when `boundary == "WordBoundary"`. [communicate.py](https://github.com/rany2/edge-tts/blob/master/src/edge_tts/communicate.py)
  - The CLI's `--write-subtitles` writes SRT. [README](https://github.com/rany2/edge-tts)
- **ElevenLabs** offers character-level timing via its `/with-timestamps` endpoint. A third-party wrapper says ElevenLabs is the only engine it supports with "precise character-level timing data", and lists Google's word timing as "Estimated". [js-tts-wrapper README](https://app.unpkg.com/js-tts-wrapper@0.1.63/files/README.md)
- **Other vendors that return word timestamps** in TTS responses:
  - Inworld TTS (sync and async timestamp modes). [Inworld docs](https://docs.inworld.ai/tts/capabilities/timestamps)
  - Smallest.ai Lightning (WebSocket only; its HTTP endpoint ignores the flag). [Smallest docs](https://docs.smallest.ai/waves/documentation/text-to-speech-lightning/word-timestamps)
- **OpenAI TTS (`gpt-4o-mini-tts`, `tts-1`):** a search found no OpenAI documentation of word timestamps in the speech endpoint. Surveyed sources describe the general workaround of running Whisper on the output. [search summary sources: Medium](https://bar-offner.medium.com/syncing-speech-with-text-adding-timestamps-to-text-to-speech-using-python-13fe433b30a0)

### Inferences
- Recommended design: `captions/aligner.py`, with backends tried in order.
  1. TTS-native timings when the provider gives them: Edge `WordBoundary`, ElevenLabs alignment, Azure.
  2. Otherwise, forced alignment of the *known script* against the rendered TTS WAV, using stable-ts `model.align(audio, text, language="vi")` or WhisperX align with the vi wav2vec2 model.
  3. Fall back to the current estimate only if both fail.
- Aligning a known script is more robust than transcribe-then-match. The script text is exact, so Whisper's Vietnamese ASR errors and number formatting stop mattering. We must normalize numbers and symbols into words in the TTS text first, though. WhisperX cannot time "2014." or currency, and VieNeu and viXTTS also rely on Vietnamese normalizers such as Vinorm.
- Vietnamese is monosyllabic and space-separated, so each syllable is a "word". For karaoke captions, group 2–4 syllables per highlight chunk and emit ASS `{\kf<centiseconds>}` per syllable. Render with FFmpeg `subtitles=`/`ass=` (libass). No new dependency is needed beyond writing the ASS file.
- Keep aeneas out of the product because of AGPL-3.0. The edge-tts LGPLv3 license is acceptable when used as an unmodified pip dependency.
- On CPU-only Windows machines, stable-ts with faster-whisper `small`/`medium` in int8, or WhisperX align-only (the wav2vec2 base model is small), should be acceptable. We did not benchmark this, so treat it as a test item.

### Gaps
- The license of `nguyenvulebinh/wav2vec2-base-vi-vlsp2020` could not be read (huggingface.co blocked). Several nguyenvulebinh Vietnamese wav2vec2 models are believed to be CC-BY-NC, which is unverified. **This must be checked before commercial distribution.** If it is NC, alternatives are an MFA Vietnamese acoustic model or a Whisper-attention-based stable-ts alignment.
- No primary documentation could be fetched on four TTS timing questions, all of which need verification:
  - Google Cloud TTS `timepoints` (believed to be SSML `<mark>`-based via v1beta1, not per-word by default)
  - whether Gemini TTS returns any timing
  - Azure WordBoundary for vi-VN voices
  - ElevenLabs Vietnamese coverage
- No published quantitative benchmark of Vietnamese word-alignment accuracy (WhisperX vs stable-ts vs MFA) was found.
- Microsoft's terms for Edge's "Read Aloud" endpoint are unofficial. Commercial reliance on edge-tts carries ToS risk, but no primary source was retrieved.

## Q2. Open/local video and image generation vs paid APIs (Wan, LTX, Hunyuan, CogVideoX, Mochi, FramePack; Kling/MiniMax/Seedance vs Veo; FLUX/SDXL; VRAM; licenses)

### Takeaway
Two video options are free for commercial use and run on a 24 GB consumer GPU: **Wan 2.2 TI2V-5B (Apache-2.0)** at 720p/24 fps, and **FramePack (Apache-2.0, ≥6 GB)** for image-to-video. Both fit our "still → motion" scenes better than full T2V. LTX-2.x is free only for entities under $10M in annual revenue, and HunyuanVideo 1.5 excludes the EU, UK and South Korea.

For images, **FLUX.2 [klein] 4B is Apache-2.0 and fits about 8 GB VRAM**. FLUX.2 [dev] and klein 9B are non-commercial.

Among APIs, Veo 3.1 Fast is about $0.10/s at 720p, and Veo 3.1 Lite is about $0.05/s (both third-party figures). Kling, Hailuo and Seedance are in the $0.08–0.32/s range.

### Cited Findings
**Wan 2.2 (Alibaba)**
- Code is Apache-2.0. [LICENSE.txt](https://github.com/Wan-Video/Wan2.2/blob/main/LICENSE.txt)
- The TI2V-5B model does T2V+I2V at 720p (1280×704) at 24 fps. The command with `--offload_model True --convert_model_dtype --t5_cpu` "can run on a GPU with at least 24GB VRAM (e.g, RTX 4090)". [README](https://github.com/Wan-Video/Wan2.2)
- The A14B MoE T2V/I2V and S2V-14B models need "at least 80GB VRAM" for the reference command. [README](https://github.com/Wan-Video/Wan2.2)
- DiffSynth-Studio adds layer-by-layer offload and FP8 for low VRAM. [README](https://github.com/Wan-Video/Wan2.2)
- An S2V (speech-to-video) model exists. [README](https://github.com/Wan-Video/Wan2.2)

**LTX-2 / LTX-2.5 (Lightricks)**
- Code is Apache-2.0. Weights are under the separate "LTX-2 Community License" (LTX-2.3) and the "LTX-2.x Community License" (LTX-2.5). [README](https://github.com/Lightricks/LTX-2)
- "Entities with annual revenues of at least $10,000,000 … are required to obtain a paid commercial license". [LICENSE-2](https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2)
- It is a DiT audio+video model with synchronized audio. Defaults are 1024×1536 at 24 fps, with a 4K option (3840×2176). The Gemma 3 text encoder stays under Google's license. [README](https://github.com/Lightricks/LTX-2)

**HunyuanVideo 1.5 (Tencent)**
- Licensed under the "TENCENT HUNYUAN COMMUNITY LICENSE … DOES NOT APPLY IN THE EUROPEAN UNION, UNITED KINGDOM AND SOUTH KOREA". [LICENSE](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5/blob/main/LICENSE)
- Minimum GPU memory is 14 GB with offloading. The 480p I2V step-distilled model (8–12 steps) cuts end-to-end time on an RTX 4090 by 75%. Wan2GP runs it in about 6 GB VRAM. A few-step super-resolution network upscales to 1080p. [README](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5)

**CogVideoX, Mochi, FramePack**
- CogVideoX: the repo code is Apache-2.0. [LICENSE](https://github.com/zai-org/CogVideo/blob/main/LICENSE) The weights license could not be read (HF blocked). See Gaps.
- Mochi (Genmo): the repo is Apache-2.0. [LICENSE](https://github.com/genmoai/mochi/blob/main/LICENSE)
- FramePack: Apache-2.0. [LICENSE](https://github.com/lllyasviel/FramePack/blob/main/LICENSE)
  - It is next-frame-section prediction with constant-length context, so the workload is invariant to video length. It runs 13B models "even on laptop GPUs" and needs at least 6 GB GPU memory. [README](https://github.com/lllyasviel/FramePack)

**FLUX images (Black Forest Labs)**
- The FLUX.2 repo code is Apache-2.0. [LICENSE](https://github.com/black-forest-labs/flux/blob/main/LICENSE)
- Weight licenses by model:

| Model | Weights license |
|---|---|
| FLUX.2 [klein] 4B and 4B Base | **apache-2.0** |
| FLUX.2 [klein] 9B, 9B KV, 9B Base | **FLUX Non-Commercial License** |
| FLUX.2 [dev] | **FLUX Non-Commercial License** |

  Source: [flux2 README](https://github.com/black-forest-labs/flux2)
- Klein 4B "fits in ~8GB VRAM (RTX 3090/4070 and up)" with "sub-second generation on consumer GPUs". It was released 2026-01-15. [flux2 README](https://github.com/black-forest-labs/flux2)

**Veo pricing (third-party; Google's pricing page was unreachable)**
- Veo 3.1 Fast is $0.10/s at 720p, after a cut from $0.15 on April 7 (year not stated in the snippet; presumably 2026). Other quoted rates: Fast 1080p $0.12/s and Fast 4K $0.30/s. Veo 3.1 Lite is reported at $0.05/s. The free tier is "Not available". [benchlm](https://benchlm.ai/media-pricing/veo); [layer3labs (updated 2026-09-27)](https://www.layer3labs.io/guides/veo-3-pricing); [vo3ai on Lite](https://www.vo3ai.com/blog/veo-31-lite-pricing-explained-is-googles-005second-ai-video-the-cheapest-api-opt-2026-04-01)
- **Conflict:** one reseller page claims $0.75/s, which is likely stale or a reseller figure. [veo3gen](https://www.veo3gen.app/blog/veo-3-1-api-access-cost)

**Kling, Seedance and MiniMax pricing (third-party aggregators, mid-2026; figures conflict)**
- Kling:
  - $0.084–0.168/s. [costbench](https://costbench.com/software/ai-media-apis/kling-api/)
  - 720p native audio: Standard about $0.09/s, Pro about $0.12/s. 1080p with audio, Kling V3 Pro: about $0.168/s. [invideo (Aug 2026)](https://invideo.io/blog/ai-video-model-pricing/); [hedra](https://www.hedra.com/blog/video-model-api-cost-comparison)
- Seedance 2.0: Mini about $0.175/s (720p), Pro about $0.323/s (1080p). Official billing is token-based. [unifically](https://unifically.com/blogs/seedance-2.0-vs-kling-3.0); [hedra](https://www.hedra.com/blog/video-model-api-cost-comparison)
- MiniMax:
  - MiniMax-H3 (2026-07-31) is about $0.13/s at 2K. [hiapi](https://www.hiapi.ai/en/blog/hailuo-3-api-minimax-h3-comparison)
  - Hailuo 2.3 Pro 1080p is about $0.0817/s, but only for 6-second clips. [hedra](https://www.hedra.com/blog/video-model-api-cost-comparison)
  - Outlier quotes (e.g. $0.025/s) exist. [atlascloud](https://www.atlascloud.ai/blog/tips/cheapest-ai-video-generation-api-2026)

### Inferences
- For a 60 s short with about 8 motion scenes of about 5 s each (40 s of generated video):
  - Veo 3.1 Fast 720p: about $4.00
  - Veo 3.1 Lite: about $2.00
  - Kling Std: about $3.60
  - Local Wan 2.2 5B or FramePack: electricity only, but minutes of GPU time per clip

  These figures are derived from the per-second prices above.
- The best cost lever for our pipeline is a hybrid. Keep Ken Burns on stills (free) for most scenes. Generate motion only for the hook and one or two key scenes. Add a pluggable `video_backend` with these options:
  - `veo` (current)
  - `local_wan22_5b` via ComfyUI or DiffSynth
  - `local_framepack` (I2V from our Imagen/FLUX still)
  - `kling`/`hailuo` via an aggregator such as fal or Replicate
- The commercial-safe local stack is Wan 2.2 (Apache), FramePack (Apache) and FLUX.2 klein 4B (Apache).
  - Avoid FLUX.1/2 dev and klein 9B (non-commercial).
  - LTX-2.x is OK only while the user's revenue is under $10M.
  - Hunyuan is geo-restricted (not usable for EU, UK or South Korea users).
- On a typical Windows user machine (8–12 GB VRAM), only FLUX.2 klein 4B, FramePack, and offloaded Hunyuan 1.5 (Wan2GP) are realistic. Wan 2.2 5B needs 24 GB.

### Gaps
- **Weights licenses** for Wan 2.2 (believed Apache-2.0 on the model card), CogVideoX 1.5 (believed a custom "CogVideoX License" with restrictions), Mochi weights (believed Apache-2.0) and SDXL (CreativeML OpenRAIL++-M) could not be confirmed. Hugging Face was blocked.
- No primary per-clip generation-time benchmarks for Wan 2.2 5B or FramePack on an RTX 4090 were retrieved.
- Official Veo, Imagen and Gemini image prices could not be read (ai.google.dev blocked, Vertex page truncated). Official Kling, BytePlus and MiniMax price pages were not fetched. All prices above are aggregator figures.
- Mochi, CogVideoX and the 2026 status of Wan 2.5/2.6 (reported to be API-only, not open weights) were not investigated.

## Q3. Open TTS with good Vietnamese (F5-TTS fine-tunes, viXTTS, VieNeu-TTS, Kokoro, CosyVoice, IndexTTS2, Fish Speech, VoxCPM); licenses; voice cloning

### Takeaway
Two open TTS options support Vietnamese and allow commercial use:
- **VieNeu-TTS** (Apache-2.0 repo; Vietnamese-first; CPU ONNX RTF about 0.5; an OpenAI-compatible `/v1/audio/speech` server; a Windows installer)
- **VoxCPM2** (Apache-2.0 weights and code; 30 languages including Vietnamese; voice design and cloning)

Kokoro, CosyVoice 3 and IndexTTS-2.5 do not list Vietnamese. F5-TTS base weights and the hynt Vietnamese fine-tunes are **non-commercial**. Fish Speech is under a custom community license.

### Cited Findings
**VieNeu-TTS** (repo license: Apache-2.0) [LICENSE](https://github.com/pnnbao97/VieNeu-TTS/blob/main/LICENSE)
- Trained on 10,000+ hours of bilingual data, with instant voice cloning. [README](https://github.com/pnnbao97/VieNeu-TTS)
- CPU path: v3 Turbo at 48 kHz via ONNX Runtime with no torch, RTF about 0.5 on a 12th-gen Core i5. [README](https://github.com/pnnbao97/VieNeu-TTS)
- GPU path: RTF about 0.02 batched, with 16 real-time streams on an RTX 3060. [README](https://github.com/pnnbao97/VieNeu-TTS)
- Serving: an OpenAI-compatible `POST /v1/audio/speech` server and Docker. [README](https://github.com/pnnbao97/VieNeu-TTS)
- Windows: a standalone Windows installer. [README](https://github.com/pnnbao97/VieNeu-TTS)
- **License conflict:** a PyPI page says the 0.5B model is Apache-2.0 but **VieNeu-TTS-0.3B is CC BY-NC 4.0**. [PyPI vieneu 1.1.0](https://pypi.org/project/vieneu/1.1.0/)

**VoxCPM2 (OpenBMB, 2026-04)**
- 2B parameters, trained on over 2M hours, covering 30 languages including **Vietnamese**, Thai, Khmer, Lao and Indonesian. [README](https://github.com/OpenBMB/VoxCPM)
- Supports voice design from a text description, controllable cloning, and 48 kHz output. [README](https://github.com/OpenBMB/VoxCPM)
- RTF is about 0.3 on an RTX 4090, or about 0.13 with Nano-vLLM. [README](https://github.com/OpenBMB/VoxCPM)
- "Weights and code released under the Apache-2.0 license, free for commercial use". [README](https://github.com/OpenBMB/VoxCPM); [LICENSE](https://github.com/OpenBMB/VoxCPM/blob/main/LICENSE)

**F5-TTS and its Vietnamese fine-tunes**
- Code is MIT. "The pre-trained models are licensed under the CC-BY-NC license due to the training data Emilia". [README](https://github.com/SWivid/F5-TTS)
- hynt/F5-TTS-Vietnamese-100h and the ViVoice model are **CC-BY-NC-SA-4.0, research only**. EraX Smile Female F5 is **BY-NC 4.0**. [HF hynt (via search)](https://huggingface.co/hynt/F5-TTS-Vietnamese-ViVoice); [search summary](https://huggingface.co/hynt/F5-TTS-Vietnamese-100h)
- OpenF5-TTS is an Apache-2.0 alpha trained on permissive data, but it is reportedly inferior to the official model. [search summary](https://replicate.com/tuannha/f5-tts-vi/readme)

**viXTTS**
- A fine-tune of Coqui XTTS-v2.0.3 on the viVoice dataset. [vixtts-demo README](https://github.com/thinhlpg/vixtts-demo)
- Known weaknesses: subpar output for sentences under 10 words, with "odd trailing sounds". It is only fine-tuned for Vietnamese. It relies on Vinorm and underthesea for normalization. [vixtts-demo README](https://github.com/thinhlpg/vixtts-demo)

**Kokoro**
- Apache-2.0. [LICENSE](https://github.com/hexgrad/kokoro/blob/main/LICENSE)
- `LANG_CODES` covers American and British English, es, fr-fr, hi, it, pt-br, Japanese and Mandarin. **There is no Vietnamese.** [pipeline.py](https://github.com/hexgrad/kokoro/blob/main/kokoro/pipeline.py)

**Fun-CosyVoice 3.0**
- Apache-2.0. [LICENSE](https://github.com/FunAudioLLM/CosyVoice/blob/main/LICENSE)
- Covers 9 languages: zh, en, ja, ko, de, es, fr, it, ru, plus 18+ Chinese dialects. **No Vietnamese is listed.** [README](https://github.com/FunAudioLLM/CosyVoice)

**IndexTTS-2.5**
- Supports Chinese, English, Japanese, Spanish and Arabic, with duration control (`duration_factor` 0.5–2.0×). **No Vietnamese.** [README](https://github.com/index-tts/index-tts)
- License: the custom **"bilibili Model Use License Agreement"**. [LICENSE](https://github.com/index-tts/index-tts/blob/main/LICENSE)

**Fish Speech**
- Code and weights are under the "FISH AUDIO COMMUNITY LICENSE" v1.0 (updated 2026-10-13). The S2-Pro weights remain under the "Fish Audio Research License". [LICENSE](https://github.com/fishaudio/fish-speech/blob/main/LICENSE); [README](https://github.com/fishaudio/fish-speech)

### Inferences
- Add a `tts_backend` setting with two new local options:
  - `vieneu`: default for Vietnamese. It runs on CPU, so it suits Windows users without a GPU. Its API is OpenAI-compatible, so our existing OpenAI TTS client can point at `http://localhost:<port>/v1` with little new code.
  - `voxcpm2`: for multilingual output or voice design, on a GPU.

  Keep Gemini/OpenAI TTS as the paid fallback.
- Do not ship any F5-TTS-based Vietnamese checkpoint or VieNeu 0.3B in a commercial build. Both are non-commercial.
- Voice cloning legality is not covered by a primary legal source here. In practice, the app should require a consent checkbox and an upload of the speaker's own voice, and should ban cloning public figures. These are product policy recommendations, not legal findings.
- Local TTS output has no native word timings, so Q1's forced-alignment step becomes mandatory for local voices.

### Gaps
- No primary Vietnamese MOS/WER benchmark comparing VieNeu, VoxCPM2 and viXTTS was found.
- The viXTTS weights license is not stated in the demo README. Coqui XTTS-v2 is believed to be under the non-commercial Coqui Public Model License, which is unverified because HF was blocked.
- The VieNeu per-model license split (Apache for the repo vs CC-BY-NC for 0.3B, and the v3 Turbo weights license) needs verification on the model cards.
- No primary source on Vietnamese law on voice cloning or deepfakes (e.g. Decree 13/2023 on personal data) was researched.

## Q4. Editing frameworks (Remotion, MoviePy 2, FFmpeg-only, Revideo, editly) and NVENC throughput

### Takeaway
Keep the **FFmpeg-only renderer** as the core. It has no license cost, is fastest, and is Windows-friendly. Add NVENC as an optional encoder, capped at 8 concurrent sessions on GeForce.

Remotion is free only for individuals, non-profits, and for-profit companies with **up to 3 employees**. Larger companies need a paid Company License. That makes it a poor fit as a bundled dependency for customers.

MoviePy 2.2 (MIT), editly (MIT) and Revideo (MIT) are permissive alternatives for complex compositions.

### Cited Findings
- **Remotion LICENSE.md:**
  - Free for "an individual", "a for-profit organization with up to 3 employees", non-profits, or during evaluation. Otherwise "You are required to obtain a Company License". [LICENSE.md](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md)
  - It forbids selling or relicensing "your own derivate of Remotion". [LICENSE.md](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md)
  - It notes that "In Remotion 5.0, the license will slightly change" (PR #3750). [LICENSE.md](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md)
- **Remotion pricing (secondary):**
  - The Remotion FAQ says eligibility depends on total headcount. A 20-person company with one Remotion user still needs a Company License. [remotion FAQ via search](https://www.remotion.dev/docs/license/faq.md)
  - Price figures vary: $25/seat/month (Creators), or $0.01 per render with a $100/month minimum (Automators). [wireflow](https://www.wireflow.ai/blog/remotion-pricing); [autoae](https://autoae.online/blog/is-remotion-free)
- **Permissive alternatives:**
  - MoviePy is MIT, with `version = "2.2.0"` in pyproject. [pyproject](https://github.com/Zulko/moviepy/blob/master/pyproject.toml)
  - editly is MIT. [LICENSE](https://github.com/mifi/editly/blob/master/LICENSE)
  - Revideo is MIT (a Motion Canvas fork). [LICENSE](https://github.com/redotvideo/revideo/blob/main/LICENSE)
- **NVENC session limit:**
  - NVIDIA's application note says non-qualified (GeForce) GPUs are limited to 8 concurrent encode sessions per system. On qualified GPUs, the limit is system resources. [NVIDIA NVENC Application Note](https://docs.nvidia.com/video-technologies/video-codec-sdk/13.0/nvenc-application-note/index.html)
  - The 8-session limit needs Windows driver ≥551.76 or Linux ≥550.54.14. Older drivers allow 3 or 5 sessions. [NVIDIA forum](https://forums.developer.nvidia.com/t/how-to-increase-number-of-nvenc-concurrent-sessions/169367); [Tom's Hardware](https://tomshardware.com/news/nvidia-increases-concurrent-nvenc-sessions-on-consumer-gpus)

### Inferences
- Remotion would force our business customers (over 3 employees) to buy their own license. short-video-maker uses Remotion, so copying its stack inherits this constraint.
- Stay FFmpeg-first and add these changes:
  - auto-detect `h264_nvenc`/`hevc_nvenc` (and `h264_qsv`/`h264_amf` for Intel/AMD), with fallback to libx264
  - a render worker pool capped at min(8, CPU-based limit) when NVENC is on
  - a two-pass `loudnorm`, measured once per track and cached
  - ASS karaoke via libass instead of drawtext chains

  MoviePy 2 is useful only for prototyping. It is slower than a single filtergraph, though no benchmark was fetched.

### Gaps
- The current official Remotion Company License price could not be read (remotion.dev/remotion.pro blocked).
- No 2026 benchmark comparing FFmpeg, MoviePy 2 and Remotion render throughput was retrieved.
- Revideo's 2026 maintenance status was not checked.

## Q5. CapCut draft compatibility (capcut-cli matrix, Timelines on 9.2.8+, template-2.tmp on 8.7, 10.x rejection, pycapcut 0.1.0, license, VectCutAPI)

### Takeaway
CapCut drafts are only community-verified up to 9.3, and **no accepted tool-written draft for CapCut 10.x has been documented**. capcut-cli write-guards 10.x.

To work on 9.x, our exporter must:
- seed from an app-created empty project
- write `Timelines/<main_timeline_id>/draft_info.json` as well as the root files
- handle `template-2.tmp`/`draft_meta_info.json` precedence (8.7 on Windows)
- never drop a lone `draft_content.json` into a draft that uses `draft_info.json`

**pyCapCut still has no LICENSE file.** Version 0.1.0 will remove `add_track`.

### Cited Findings
- **capcut-cli** is MIT. [LICENSE](https://github.com/renezander030/capcut-cli/blob/master/LICENSE)
- **capcut-cli version-support matrix:** [version-support.md](https://github.com/renezander030/capcut-cli/blob/master/docs/version-support.md)

| CapCut version | Status | Notes |
|---|---|---|
| 6.2.8 | fixture-tested | Primary file is `draft_content.json` |
| 6.5–8.0 | expected-compatible, unverified | |
| 8.4.0 macOS | reported | The app creates `Timelines/` on first open, and root-only edits worked (#50, 2026-08-31) |
| 8.7.0 Windows | | "`template-2.tmp`/`draft_meta_info.json` take precedence over content/info". The bundled 6.5.0 template was refused as "from an unusual path" (#111, 2026-09-10). A template captured from the installed app round-tripped on 9.3.0 |
| 9.2.8-beta4 macOS | reported | `Timelines/<main_timeline_id>/draft_info.json` is authoritative and root files are legacy mirrors. "a root-only write is a silent no-op" (#50, 2026-08-23) |
| 9.3.0 macOS | reported round-trip | Uses the "shell-first" recipe ([zxypro1/capcut-shell-inject](https://github.com/zxypro1/capcut-shell-inject), 2026-09-11) |
| 10.x Mac/Windows | reported, **write-guarded** | Tool drafts are rejected as "内容已损坏" (pyJianYingDraft #177/#194 for JianYing 10.8). There is no fixture, and mutating commands refuse without `--force-write` |

- **Recommended 9.x recipe** from the same doc: create an empty project in the app and quit, write into it, then run `sync-timelines --nested --apply` and `register --materials --apply`. [version-support.md](https://github.com/renezander030/capcut-cli/blob/master/docs/version-support.md)
- **Related JianYing data points:**
  - JianYing 11.4 (macOS) accepts a plaintext `draft_info.json` and upgrades it to the encrypted format. A stray `draft_content.json` triggers "草稿内容已损坏". [pyJianYingDraft#198](https://github.com/GuanYixuan/pyJianYingDraft/issues/198), via [version-support.md](https://github.com/renezander030/capcut-cli/blob/master/docs/version-support.md)
  - JianYing 9.0.0 on Windows opened a tool-written plaintext `draft_info.json` and encrypted the mirrors on close. [Issue #148](https://github.com/renezander030/capcut-cli/issues/148)
  - The doc itself notes conflicting evidence on which file is primary. [version-support.md](https://github.com/renezander030/capcut-cli/blob/master/docs/version-support.md)
- **pyCapCut:**
  - No LICENSE/LICENSE.md/LICENSE.txt/COPYING exists at HEAD (checked 2026-11-04), and setup.py has `version="0.0.4"`. [repo](https://github.com/GuanYixuan/pyCapCut)
  - The README announces that 0.1.0 will add `append_track(s)`/`insert_track(s)` with `TrackSpec`/`TrackRef` and **remove `add_track`**. Users can pin `pycapcut==0.0.4`. [README](https://github.com/GuanYixuan/pyCapCut)
  - Feature-level verified versions are CapCut 8.2.0 and 9.5.0.4050. There is no auto-export for CapCut. [README](https://github.com/GuanYixuan/pyCapCut) (also summarized in our earlier note `research_notes/Đối thủ nguồn mở video AI/capcut_and_chinese_ecosystem.md`)
- **VectCutAPI:**
  - Apache-2.0. [LICENSE](https://github.com/sun-guannan/VectCutAPI/blob/main/LICENSE)
  - It runs an HTTP server on :9001 and an MCP server over stdio with 11 tools, and exports drafts to CapCut or JianYing. Its cloud rendering module is not open-sourced. [README](https://github.com/sun-guannan/VectCutAPI)

### Inferences
- Our pin `pycapcut>=0.0.4,<0.1` in `pyproject.toml` is correct and must stay until we migrate to the `append_track` API.
- Redistributing pycapcut inside a Windows installer is a legal risk, because it has no license, which means all rights are reserved by default. Options:
  - ask upstream to add a license
  - switch to capcut-cli (MIT; Node, zero-dependency) as a subprocess
  - write our own minimal draft writer, based on pyJianYingDraft (Apache-2.0) structures
- The exporter for 9.x/10.x should:
  1. Detect the installed CapCut version, from the app's install directory or the `draft_meta_info.json` `app_version` of an existing draft.
  2. Prefer "seed from an app-created template": the user creates one empty project, and we clone it.
  3. Write identical JSON to the root `draft_info.json`/`draft_content.json` (whichever the template has) **and** to `Timelines/<id>/draft_info.json`.
  4. Update `template-2.tmp`/`draft_meta_info.json` consistently, and register the draft in `root_meta_info.json`.
  5. For 10.x, show a "not verified" warning and offer SRT/XML/EDL plus media-folder export as a fallback.
- A fallback to FCPXML/EDL is worth considering because it is version-agnostic.

### Gaps
- No primary evidence of any tool-written draft being accepted by CapCut International 10.x was found. CapCut's internal schema is undocumented by ByteDance.
- The pycapcut 0.1.0 release date and PyPI status were not fetched.

## Q6. Agent/automation integration (MCP server, Claude Code skill, n8n, queues) for a single-machine Windows app plus server mode

### Takeaway
Expose the pipeline as an **MCP server** (stdio for local Claude Desktop or Claude Code, HTTP for server mode), plus a REST API that n8n can call. This copies the short-video-maker pattern (MIT) and Kinocut/mcp-video (Apache-2.0).

For queues on Windows:
- **Celery does not support Windows.**
- **RQ's fork/spawn workers need POSIX**, so only `SimpleWorker` runs on Windows.
- **Huey** offers SQLite/file storage and thread/greenlet workers, so it fits a single-machine Windows app with no Redis.

Redis/RQ, Celery or Temporal belong to Linux server mode only.

### Cited Findings
- **short-video-maker (gyoridavid):** MIT. [LICENSE](https://github.com/gyoridavid/short-video-maker/blob/main/LICENSE)
  - It "exposes an MCP and a REST server". n8n example workflows exist. [README](https://github.com/gyoridavid/short-video-maker)
  - Pipeline: Kokoro TTS, then Whisper captions, then Pexels background video, then music, then Remotion composition. [README](https://github.com/gyoridavid/short-video-maker)
  - Only English voiceover is supported ("kokoro-js doesn't support other languages"). It needs at least 3 GB RAM, and Docker images use whisper.cpp `tiny.en`. [README](https://github.com/gyoridavid/short-video-maker)
- **Kinocut / mcp-video (kyanitelabs):** Apache-2.0. [LICENSE](https://github.com/kyanitelabs/mcp-video/blob/main/LICENSE)
  - A local-first FFmpeg video-editing MCP server plus Python client and `kino` CLI, with "205 MCP tools served in published 1.16.5". [README](https://github.com/kyanitelabs/mcp-video)
  - Features: typed tools, preflight validation, "Video Receipts" and quality gates. It runs on macOS, Linux and Windows with FFmpeg on PATH. [README](https://github.com/kyanitelabs/mcp-video)
- **VectCutAPI** exposes the same kind of dual HTTP + MCP surface for CapCut drafts and lists n8n, Dify, Coze and Claude Code integrations. [README](https://github.com/sun-guannan/VectCutAPI)
- **Celery:** the README says "we don't support Microsoft Windows but it should be working. Please don't open any issues related to that platform." [Celery README](https://github.com/celery/celery)
  - Community reports describe tasks stuck in pending or reserved state on Windows, and recommend WSL2 or Docker. [Reddit](https://redlib.hbubli.cc/r/learnpython/comments/1kwjbkl/celery_on_windows_which_message_broker_async)
- **RQ:** `SpawnWorker` "requires POSIX; use `SimpleWorker` on Windows". `SimpleWorker` runs jobs in-process with no isolation or hard timeouts. [RQ workers docs](https://github.com/rq/rq/blob/master/docs/docs/workers.md)
- **Huey** supports redis/valkey, postgres, **sqlite**, file-system and in-memory storage, with multi-process, multi-thread or greenlet execution. [Huey README](https://github.com/coleifer/huey)
  - Community reports say only threaded mode works on Windows. [StackOverflow mirror](https://kaweah.freedombox.rocks/kiwix/content/stackoverflow.com_en_all_2023-11/questions/55612559/queue-background-tasks-in-python-application-on-windows)

### Inferences
- **MCP server design:** use the Python MCP SDK (FastMCP) in `ai_content_agent/mcp_server.py`. Proposed tools:
  - `create_video(topic, lang, style, backends) -> job_id`
  - `get_job(job_id)`
  - `list_assets`
  - `rerender_scene(job_id, scene, prompt)`
  - `export_capcut(job_id)`
  - `publish(job_id, platforms)`

  Long renders should return a job id, not block. A Claude Code skill (a `SKILL.md` that calls the CLI) is a cheap extra.
- **Queues:**
  - Windows desktop: keep the existing `web/jobs.py` in-process worker, or adopt Huey with `SqliteHuey` and thread workers. Run GPU-heavy steps (local video, TTS) in a single dedicated subprocess so a crash cannot take down the UI.
  - Linux server mode: Huey with Redis, or RQ. Temporal is overkill unless we need multi-day, multi-step durable workflows (for example scheduled publishing with retries).
- Don't vendor short-video-maker: its stack is English-only and Remotion-based. Its MCP and REST surface is a good reference for tool naming.

### Gaps
- Coverage of an official n8n community node for MCP-client usage, and of the 2026 MCP spec (streamable HTTP, auth), was not researched here.
- No primary benchmark exists for Huey on Windows. Windows thread-mode support is community-reported.
