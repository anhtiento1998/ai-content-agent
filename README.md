# ai-content-agent

Studio sản xuất video ngắn tự động: **chủ đề → kịch bản chia cảnh → hình
ảnh + giọng đọc cho từng cảnh → phụ đề, nhạc nền, logo → video MP4 dọc
hoàn chỉnh → đăng lên YouTube Shorts, TikTok, Facebook Page**.

Các AI (Claude, GPT, Gemini, Muse Spark, Imagen, Veo) tạo nguyên liệu;
studio dựng (bằng FFmpeg) ghép chúng thành video thành phẩm — khâu mà
trước đây phải làm tay trong CapCut. Có **dashboard web** để bấm tạo
video, theo dõi tiến trình, xem lịch sử, lịch tự động và log lỗi.

![Dashboard](docs/dashboard.png)

## Kiến trúc

```
chủ đề
  │
  ▼  TextGenerator  (claude | gpt | gemini | muse)
Storyboard {title, description, hashtags, scenes[{narration, visual_prompt, on_screen_text}]}
  │
  ├─► VoiceGenerator (gemini | gpt | silent)       ─┐  song song, mỗi cảnh 1 lần
  └─► Image/VideoGenerator (imagen | gpt-image |    │
                            veo | card)            ─┘
  │
  ▼  Studio (FFmpeg)
     ảnh → zoom chậm (Ken Burns) / clip → cắt hoặc lặp cho khớp lời đọc
     phụ đề khớp từng câu + chữ tiêu đề mỗi cảnh (ASS/libass)
     nhạc nền (tự hạ âm lượng dưới giọng) + logo + chuẩn hóa âm lượng -14 LUFS
  │
  ▼  final.mp4 1080x1920 30fps H.264/AAC  +  thumbnail.jpg
  │
  ▼  Publisher[] (youtube | tiktok | facebook)  →  HistoryStore (SQLite)
```

Mỗi lần chạy có 1 thư mục riêng `output/<tên>_<thời gian>/` chứa
`storyboard.json`, ảnh/clip và giọng đọc từng cảnh, `subtitles.ass`,
`final.mp4`, `thumbnail.jpg` — để kiểm tra lại hoặc (sắp tới) xuất sang
CapCut chỉnh tay. File trung gian (WAV đệm, từng đoạn cảnh đã encode) tự
xóa sau khi dựng xong để không đầy ổ đĩa; đặt `KEEP_INTERMEDIATES=true`
nếu cần giữ để debug.

Lỗi tạm thời của API (429 quá tải/hết quota tạm, 5xx, 529, rớt mạng) được
**tự thử lại** tối đa 3 lần với thời gian chờ tăng dần; lỗi vĩnh viễn (sai
key, prompt bị chặn) báo ngay. Veo bị giới hạn 2 clip chạy song song để
không vượt quota.

- `src/ai_content_agent/providers/` — adapter cho từng AI: 4 interface
  `TextGenerator`, `ImageGenerator`, `VideoGenerator`, `VoiceGenerator`
  (`providers/base.py`). `local_provider.py` có engine offline (`card`,
  `silent`) để xem thử bố cục không tốn API.
- `src/ai_content_agent/studio/` — lõi dựng phim: `storyboard.py` (kịch
  bản chia cảnh), `captions.py` (phụ đề), `render.py` (lệnh FFmpeg),
  `studio.py` (điều phối).
- `src/ai_content_agent/publishers/` — mỗi nền tảng đăng bài là 1 class
  implement `Publisher` (`publishers/base.py`).
- `src/ai_content_agent/pipeline/content_pipeline.py` — studio →
  thumbnail → đăng bài → lưu lịch sử.
- `src/ai_content_agent/media/` — helper FFmpeg và thumbnail 1280x720.
- `src/ai_content_agent/history.py` — SQLite lưu lịch sử + lỗi, chống
  đăng trùng topic trong `DEDUP_WINDOW_DAYS` ngày (chỉ tính lượt đã đăng
  thành công, nên lần đăng thất bại có thể chạy lại).
- `src/ai_content_agent/web/` — dashboard: `app.py` (API), `jobs.py`
  (hàng đợi job), `server.py` (khởi động), `static/` (giao diện).
- `src/ai_content_agent/agent.py` — đọc config, dựng pipeline cụ thể.
- `src/ai_content_agent/cli.py` — `run`, `schedule`, `history`,
  `dashboard`.

### Trạng thái từng provider/publisher

Cột "Đã test" phân biệt rõ: phần nào đã chạy thật trong quá trình phát
triển, phần nào mới viết theo docs của nhà cung cấp và cần API key thật để
xác nhận.

| Thành phần | Cấu hình | Đã test |
|---|---|---|
| Kịch bản — Claude / GPT / Gemini | `TEXT_PROVIDER=claude\|gpt\|gemini` + key tương ứng | phần parse/kiểm tra kịch bản: có; gọi API thật: chưa |
| Kịch bản — Muse Spark (Meta) | `TEXT_PROVIDER=muse`, `META_MODEL_API_KEY` + `META_MODEL_API_BASE_URL` (lấy từ [dev.meta.ai/docs](https://dev.meta.ai/docs)). Meta Model API đang public preview, chỉ developer ở Mỹ | chưa |
| Hình ảnh — Imagen / GPT image | `VISUAL_PROVIDER=imagen\|gpt-image` | chưa (cần key) |
| Hình ảnh — Veo (clip mỗi cảnh) | `VISUAL_PROVIDER=veo` — **đắt nhất**: 1 lần gọi Veo cho mỗi cảnh | phần cắt/lặp clip: có; gọi Veo thật: chưa |
| Hình ảnh / clip — ComfyUI (model chạy trên máy) | `VISUAL_PROVIDER=comfyui` hoặc `comfyui-video` + file workflow của bạn (Wan 2.2, FramePack, Flux…) | HTTP giả lập: có; ComfyUI thật: chưa |
| Hình ảnh — nền màu offline | `VISUAL_PROVIDER=card` — không cần API, để xem thử bố cục | có |
| Hình ảnh — Muse Video (Meta) | **chưa có** — tính đến 10/2026 Meta chưa mở API. Chọn `muse` sẽ báo lỗi ngay khi khởi tạo (không tốn tiền viết kịch bản trước) | — |
| Giọng đọc — Gemini / GPT TTS | `VOICE_PROVIDER=gemini\|gpt`, chọn giọng qua `VOICE_NAME` | chưa (cần key) |
| Giọng đọc — VieNeu-TTS (chạy trên máy) | `VOICE_PROVIDER=vieneu` — server cục bộ, 25 giọng Việt, không tốn phí | HTTP giả lập: có; server thật: chưa |
| Giọng đọc — ZeroTTS (chạy trên máy) | `VOICE_PROVIDER=zerotts`, `pip install -e ".[zerotts]"` | giả lập: có; model thật: chưa |
| Giọng đọc — không giọng | `VOICE_PROVIDER=silent` — video chỉ có phụ đề + nhạc | có |
| Mã hoá video bằng GPU | `VIDEO_ENCODER=auto` tự dò NVENC / Quick Sync / AMF, không được thì dùng CPU | dò & lùi về CPU: có; GPU thật: chưa |
| Dựng video (FFmpeg): zoom ảnh, ghép cảnh, phụ đề, nhạc, logo, chuẩn hóa âm lượng | luôn bật | có (dựng video thật trong test) |
| Đăng YouTube | OAuth app (xem dưới) | HTTP giả lập: chưa; API thật: chưa |
| Đăng TikTok | Content Posting API, tự chia chunk cho video > 64MB. **Trước khi TikTok audit app, bài chỉ đăng ở chế độ riêng tư** (`TIKTOK_PRIVACY_LEVEL=SELF_ONLY`) | HTTP giả lập: có; API thật: chưa |
| Đăng Facebook Page | Page access token dài hạn; trả về link `facebook.com/watch` | HTTP giả lập: có; API thật: chưa |
| Thumbnail tự động | YouTube chỉ nhận custom thumbnail nếu kênh đã xác minh số điện thoại (không thì bỏ qua, video vẫn đăng) | có |
| Chống đăng trùng topic, dashboard, lịch tự động | — | có |
| Xuất project nháp CapCut | `pip install -e ".[capcut]"`, chỉ CapCut bản quốc tế | trên bản giả lập pycapcut: có; mở trong CapCut thật: **chưa** |

**Lưu ý chi phí:** API của OpenAI, Anthropic, Google được tính tiền
**riêng** với gói ChatGPT Plus / Claude Pro / Google AI Pro dùng trên web
— cần tạo API key và nạp credit ở trang developer của từng hãng. Một video
40 giây ≈ 1 lần gọi kịch bản + 4–8 ảnh (hoặc 4–8 clip Veo) + 4–8 lần đọc
giọng.

## Chi phí từng video và hạn mức chi tiêu

Mỗi video được tính chi phí engine AI theo mức dùng thật: số token mà API
báo về (kịch bản), số ảnh, số giây clip, số phút giọng đọc. Engine chạy trên
máy (card, silent, vieneu, zerotts, comfyui) tính 0. Chi phí hiện trên thẻ
tiến trình, thẻ Chờ duyệt (rê chuột để xem từng engine) và ô thống kê; lưu
trong `provenance.json` và lịch sử — kể cả lần chạy thử và lần dựng lỗi giữa
chừng.

- **Bảng giá** (USD) nằm trong `src/ai_content_agent/costs.py`. Giá Claude
  là giá niêm yết của Anthropic ngày 3/11/2026. Giá OpenAI và Google là giá
  niêm yết tôi biết tới thời điểm viết, **chưa đối chiếu lại được** — hãy
  sửa bằng file JSON và trỏ `PRICING_FILE` tới đó (mẫu ở đầu `costs.py`).
  Model chưa có giá hiện "+?" thay vì đoán.
- Con số là **ước tính theo giá niêm yết**, không phải hoá đơn (chưa trừ
  giảm giá cache/batch, chưa tính thuế).
- `DAILY_BUDGET_USD=5`: khi 24 giờ qua đã tiêu tới mức này, app từ chối dựng
  video mới (lỗi giai đoạn "Hạn mức chi tiêu"); mục trong lô thì tự chờ 1
  giờ rồi thử lại, không bị đánh lỗi.
- `USD_VND_RATE=26000`: hiện thêm số tiền quy đổi ra đồng.

## Hình từ kho video/ảnh miễn phí (Pexels, Pixabay)

Thay vì tạo hình bằng AI (tốn tiền), lấy clip/ảnh thật từ kho miễn phí:

| `VISUAL_PROVIDER` | Lấy gì | Cần |
|---|---|---|
| `pexels` | clip dọc từ Pexels | `PEXELS_API_KEY` (miễn phí tại pexels.com/api) |
| `pexels-photo` | ảnh dọc từ Pexels, app tự zoom chậm | `PEXELS_API_KEY` |
| `pixabay` | clip từ Pixabay | `PIXABAY_API_KEY` (miễn phí tại pixabay.com/api/docs) |

- Kho stock tìm bằng vài từ cụ thể, nên kịch bản có thêm ô **từ khoá** cho
  mỗi cảnh (2–4 từ tiếng Anh, ví dụ `air conditioner remote`). Sửa được ở
  Bàn kịch bản, trong mục *Mô tả hình ảnh*. Tìm không ra thì app tự bỏ bớt
  từ cuối rồi tìm lại.
- Clip đã dùng được ghi nhớ (600 clip gần nhất, file `stock_used.json` cạnh
  cơ sở dữ liệu) nên một video không lặp clip và các video sau cũng không
  dùng lại clip cũ.
- Nguồn từng clip (link trang, tác giả) được ghi vào `provenance.json`.
- Giấy phép Pexels/Pixabay cho dùng miễn phí, không bắt buộc ghi nguồn,
  nhưng cấm bán lại nguyên bản và cấm ngụ ý người trong hình quảng cáo cho
  bạn — đọc giấy phép trước khi dùng thương mại. Chi phí tính là 0.
- Phần gọi API viết theo tài liệu hai dịch vụ, **chưa chạy với key thật**.

## Hình/clip từ model chạy trên máy (ComfyUI)

Chạy Wan 2.2, FramePack, Flux… trên card đồ hoạ của bạn, không tốn phí API:

1. Dựng workflow chạy được trong ComfyUI, rồi xuất bằng **Save (API
   Format)**.
2. Trong file JSON đó, đặt các chỗ giữ chỗ: `{{prompt}}` trong ô mô tả
   (prompt dương), `{{seed}}` làm giá trị seed, `{{width}}` / `{{height}}`
   làm kích thước khung.
3. `.env`: `VISUAL_PROVIDER=comfyui` (workflow ra **ảnh**, app tự zoom chậm)
   hoặc `comfyui-video` (workflow ra **clip**), `COMFYUI_WORKFLOW=đường dẫn
   file`, và `COMFYUI_URL` nếu ComfyUI không ở `http://127.0.0.1:8188`.

App tạo từng cảnh một (card đồ hoạ không chạy 2 model video cùng lúc), chờ
tối đa 30 phút mỗi cảnh. Không kèm sẵn workflow nào vì chúng phụ thuộc model
và node bạn đã cài.

## Avatar người nói (khớp miệng, chạy trên máy)

Thêm một người nói khớp miệng theo giọng đọc của từng cảnh, tạo bằng workflow
khớp miệng của bạn trong ComfyUI (SadTalker, LatentSync, InfiniteTalk, Wan
S2V…), không tốn phí API:

1. Dựng workflow chạy được trong ComfyUI: nhận **một ảnh chân dung + một
   file âm thanh**, lưu ra **video**. Xuất bằng **Save (API Format)**.
2. Trong file JSON, đặt `{{audio}}` vào ô chọn file âm thanh và `{{image}}`
   vào ô chọn ảnh (có thể dùng thêm `{{seed}}`, `{{width}}`, `{{height}}`).
3. `.env`:
   ```
   AVATAR_PROVIDER=comfyui
   AVATAR_WORKFLOW=duong/dan/lipsync.json
   AVATAR_IMAGE=duong/dan/chan-dung.png
   AVATAR_LAYOUT=corner        # hoặc full
   ```

Hai bố cục, đổi bằng `AVATAR_LAYOUT`:

- **`corner`** (mặc định): avatar trong vòng tròn viền trắng, đè lên hình
  minh hoạ của từng cảnh. Vị trí `AVATAR_POSITION` = `bottom-left` (mặc định,
  nằm phía trên phụ đề), `bottom-right`, `top-left`, `top-right`; cỡ
  `AVATAR_SIZE` = % chiều rộng khung hình (mặc định 34).
- **`full`**: avatar chiếm cả khung hình, **không tạo hình minh hoạ** nữa
  (không tốn tiền/không cần key engine hình); phụ đề, chữ hook, nhạc, logo
  vẫn như cũ.

App gửi giọng đọc từng cảnh và ảnh chân dung vào ComfyUI (ảnh chỉ gửi một
lần), tạo **từng cảnh một** sau khi có giọng đọc; âm thanh của clip avatar bị
bỏ, video dùng giọng đọc gốc. Clip ngắn hơn cảnh thì được lặp lại. Khi chạy
tiếp một lần dựng dở, clip avatar đã có được dùng lại. Bản xuất CapCut và gói
dựng có thêm track **avatar** riêng (trong CapCut là khung chữ nhật — muốn
bo tròn thì thêm mask trong CapCut).

**Lưu ý:** chỉ dùng khuôn mặt của chính bạn hoặc người đã đồng ý. Video vẫn
được gắn nhãn AI (nhãn trên video, mô tả, cờ `containsSyntheticMedia` của
YouTube, `is_aigc` của TikTok). Phần gọi ComfyUI mới thử với bản giả lập;
bước ghép hình đã dựng video thật trong test.

## Cho Claude điều khiển app (MCP server)

```bash
pip install -e ".[mcp]"
ai-content-agent mcp          # server MCP qua stdio
```

- **Claude Code**: repo có sẵn `.mcp.json` và skill
  `.claude/skills/video-factory/` — mở Claude Code trong thư mục dự án (đã
  kích hoạt venv), chấp nhận server `ai-content-agent`, rồi nói ví dụ "làm 3
  video về mẹo tiết kiệm điện cho YouTube".
- **Claude Desktop**: thêm vào file cấu hình MCP của app
  `{"mcpServers": {"ai-content-agent": {"command": "<đường dẫn đầy đủ tới
  ai-content-agent>", "args": ["mcp"]}}}` và đặt thư mục làm việc là thư mục
  dự án (nơi có `.env`).

30 công cụ: `status`, `get_config`, `get_batch`, `format_performance`, `produce_video`, `job_status`, `list_jobs`,
`create_batch`, `list_batches`, `batch_control`, `review_queue`, `get_run`,
`recent_runs`, `recent_errors`, `reject_run`, `export_edit_bundle`,
`export_capcut`, và ba công cụ đăng bài `approve_run`, `retry_publish`,
`takedown`, cùng 10 công cụ cho bàn kịch bản và lịch:

- Kịch bản: `write_script`, `list_drafts`, `get_draft`, `update_draft`,
  `discard_draft`, `render_draft`.
- Lịch: `get_schedule`, `update_schedule`, `add_schedule_topics`,
  `remove_schedule_topic`.

`get_config` cho biết engine đang chọn, engine nào đã có cấu hình, ghi chú
thiếu cấu hình, phụ đề, nhạc và ngân sách. Kết quả không chứa API key/token;
trạng thái `ready` chỉ phản ánh cấu hình, không xác nhận kết nối hoặc quyền
API thật. `get_batch(batch_id)` đọc đầy đủ một lô theo ID, kể cả lô cũ đã
ra ngoài danh sách gần đây hoặc sau khi khởi động lại.

**Sửa kịch bản qua MCP:** gọi `write_script(topic, platforms=["youtube"])`,
đợi `job_status(job_id)` trả `status=scripted` và `draft_id`, rồi đọc bằng
`get_draft(draft_id)`. `update_draft` nhận **toàn bộ** storyboard, ví dụ:

```json
{
  "draft_id": 1,
  "storyboard": {
    "title": "Mẹo tiết kiệm điện",
    "description": "Mô tả đã kiểm tra",
    "hashtags": ["meohay"],
    "scenes": [{
      "narration": "Lời đọc đã sửa và kiểm tra thông tin.",
      "visual_prompt": "a ceiling fan in a living room",
      "on_screen_text": "Mẹo nhỏ mỗi ngày",
      "keywords": "ceiling fan"
    }]
  }
}
```

Viết kịch bản chỉ cần engine văn bản; chưa cần cấu hình ảnh, TTS,
avatar, Whisper hay tài khoản đăng bài. Dashboard cũng dùng luồng chỉ viết
này. Các engine dựng video sẽ được khởi tạo khi bạn yêu cầu dựng.

Sau đó gọi `render_draft(draft_id)` và theo dõi job. Video dùng đúng lời đã
sửa, vẫn chờ duyệt theo `REQUIRE_APPROVAL`. `dry_run=true` chỉ dựng thử và
để bản nháp mở; lỗi dựng cũng trả bản nháp về trạng thái mở. Với
`update_draft` và `render_draft`, bỏ qua `platforms` sẽ giữ/dùng nền tảng
đã lưu; `platforms=[]` là xóa/bỏ chọn các nền tảng. Chỉ bản nháp đang mở mới
được sửa, bỏ hoặc bắt đầu dựng; hai client không thể cùng nhận dựng một
bản nháp. MCP không đặt lại trạng thái bản đang dựng khi kết nối; nếu tiến
trình dựng bị tắt đột ngột, khởi động lại dashboard để phục hồi bản nháp.

**Quản lý lịch qua MCP:** `get_schedule` trả cron, múi giờ, nền tảng và
các chủ đề (có ID). Thêm chủ đề bằng `add_schedule_topics(topics=[...])`,
xóa bằng `remove_schedule_topic(topic_id)`. Ví dụ đặt lịch 9 giờ thứ Hai
và thứ Sáu: `update_schedule(cron="0 9 * * mon,fri", platforms=["youtube"],
enabled=true)`. Đây là thay thế toàn bộ cấu hình lịch; đọc cấu hình trước
khi sửa. Dùng `enabled=false` để dừng lịch.

**Dashboard là tiến trình thực thi lịch.** Chạy `ai-content-agent dashboard`
với cùng `.env`, `HISTORY_DB_PATH` và `SCHEDULE_TIMEZONE` với MCP. Dashboard
nhận thay đổi cấu hình trong khoảng 5 giây; danh sách chủ đề được đọc mỗi
lượt chạy. MCP chỉ lưu cấu hình, không khởi động scheduler thứ hai và không
thể xác nhận dashboard khác đang chạy (`next_run_at` từ MCP là `null`). Khi
dashboard tắt, lịch không chạy. Bật lịch hoặc thêm chủ đề vào lịch đang bật
cũng phải qua kiểm tra `REQUIRE_APPROVAL` / `MCP_ALLOW_PUBLISH`; tắt lịch
luôn được phép.

**Kiểm tra đầu vào MCP:** chủ đề và style tối đa 300 ký tự, tên lô tối đa
120 ký tự; một lô nhận từ 1 đến 500 dòng chủ đề (bỏ qua dòng trống, nhưng
phải còn ít nhất một chủ đề). Dữ liệu quá dài hoặc sai kiểu báo lỗi trước
khi xếp job; chủ đề không bị tự cắt ngắn. `batch_control` kiểm tra quyền duyệt
khi tiếp tục/thử lại lô; worker MCP cũng kiểm tra trước mỗi mục của lô đã lưu.
Tạm dừng lô luôn được phép với ID hợp lệ.

**An toàn:** mặc định agent **không được đăng bài** — ba công cụ đăng bài trả
lỗi cho tới khi bạn đặt `MCP_ALLOW_PUBLISH=true`, và nếu
`REQUIRE_APPROVAL=false` thì agent cũng không được dựng video để đăng (chỉ
được chạy thử). Agent viết, dựng **và** đăng mà không ai xem chính là kiểu
"sản xuất hàng loạt tự động" các nền tảng đang phạt. Các quyết định duyệt, từ chối, đăng lại và gỡ bài của agent
được ghi vào nhật ký người duyệt với tên `mcp:...`.

## Giọng đọc chạy trên máy (miễn phí)

**VieNeu-TTS v3 Turbo** — giọng Việt tự nhiên, chạy trên CPU (khoảng 0,5×
thời gian thực trên Core i5 đời 12) hoặc GPU NVIDIA:

```powershell
pip install vieneu
git clone https://github.com/pnnbao97/VieNeu-TTS
cd VieNeu-TTS
uv run python -m apps.openai_speech     # chạy server tại http://localhost:8000/v1
```

Rồi trong `.env`: `VOICE_PROVIDER=vieneu`, chọn giọng bằng `VOICE_NAME`
(mặc định `Hải Đăng`; ví dụ `Mai Anh`, `Ngọc Huyền`, `Thùy Dung` giọng Nam,
`Quang Sơn` giọng Trung). Server ở máy khác thì đặt `VIENEU_BASE_URL`, có
khoá thì `VIENEU_API_KEY`. Xoay vòng nhiều giọng: `VOICE_NAMES=Hải Đăng,Mai
Anh,Ngọc Huyền`.

**ZeroTTS** — chạy ngay trong app, không cần server:
`pip install -e ".[zerotts]"`, `VOICE_PROVIDER=zerotts`, `VOICE_NAME=maichi`.
Lần đầu tải khoảng 900 MB model từ Hugging Face.

Giấy phép: mã nguồn VieNeu là Apache-2.0, ZeroTTS là MIT. Thẻ model trên
Hugging Face **chưa kiểm tra được** từ môi trường phát triển — nếu dùng thương
mại, hãy đọc giấy phép của đúng bản model bạn tải (bản VieNeu 0.3B cũ là
CC BY-NC, không dùng thương mại). App không đóng gói sẵn model nào.

## Mã hoá video bằng GPU

`VIDEO_ENCODER=auto` (mặc định) thử lần lượt NVIDIA NVENC, Intel Quick Sync,
AMD AMF — mỗi bộ phải mã hoá thử thành công vài khung hình mới được chọn
(nhiều bản FFmpeg liệt kê NVENC cả trên máy không có card NVIDIA). Không có
GPU dùng được thì dùng `libx264` như cũ. Ép một bộ cụ thể:
`VIDEO_ENCODER=h264_nvenc`; tắt GPU: `VIDEO_ENCODER=libx264`. Dashboard hiển
thị bộ đang dùng; `provenance.json` ghi lại bộ đã mã hoá từng video.

## Phụ đề và tiếng Việt

- **Phụ đề theo từng từ** (`CAPTION_STYLE=karaoke`, mặc định): mỗi dòng
  hiện 1 cụm ngắn, từ nào đang được đọc thì tô vàng dần. `phrase` = dòng
  chữ trắng như cũ.
- **Thời gian từng từ**: mặc định ước lượng theo số âm tiết *khi đọc* (ví dụ
  "2026" tính là 7 âm tiết) cộng khoảng nghỉ ở dấu câu — luôn khớp đầu/cuối
  cảnh. `CAPTION_ALIGNER=whisper` (cài `pip install -e ".[align]"`) nghe
  lại giọng đọc bằng faster-whisper để lấy thời gian thật từng từ, đồng thời
  chấm **điểm phát âm** (tỷ lệ từ nhận dạng lại được); cảnh dưới 60% được
  đánh dấu đỏ trong khu Chờ duyệt. Lần đầu sẽ tải model (`WHISPER_MODEL`,
  mặc định `small`) từ Hugging Face. *Phần này chưa chạy thử với model
  thật.*
- **Chuẩn hoá Unicode NFC** cho kịch bản, giọng đọc và phụ đề (văn bản
  tiếng Việt dạng tổ hợp làm vỡ dấu trên Windows).
- **Đọc số cho TTS**: trước khi gửi giọng đọc, số/ngày/giờ/đơn vị được đổi
  thành chữ — "26°C" → "hai mươi sáu độ C", "50.000đ" → "năm mươi nghìn
  đồng", "5/11/2026" → "ngày năm tháng mười một năm hai nghìn không trăm
  hai mươi sáu", "9h30", "15%", "5 km", "3–5"... Phụ đề vẫn giữ chữ số.
- **Font đóng gói sẵn**: Be Vietnam Pro (giấy phép SIL OFL, file trong
  `src/ai_content_agent/assets/fonts/`), đủ dấu tiếng Việt trên mọi máy.
  Đổi bằng `SUBTITLE_FONT` (phải là font đã cài trên máy).
- **Nhãn AI trên video**: `AI_LABEL_OVERLAY=true` (mặc định) giữ dòng
  `AI_DISCLOSURE_TEXT` nhỏ ở góc trên trái suốt video.

## Cài đặt (Windows)

Cần Python 3.11+ và FFmpeg:

```powershell
winget install Python.Python.3.12
winget install Gyan.FFmpeg
```

```powershell
cd ai-content-agent
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env    # rồi mở .env điền API key
```

(macOS/Linux: `brew install ffmpeg` hoặc `sudo apt install ffmpeg`,
kích hoạt venv bằng `source .venv/bin/activate`.)

Nhạc nền: bỏ file `.mp3`/`.wav` vào `assets/music/` **và khai báo giấy
phép** của từng bài trong `assets/music/licenses.json`:

```json
{
  "lofi-morning.mp3": {"license": "Pixabay Content License", "source": "https://pixabay.com/music/...", "attribution": ""}
}
```

Bài không có giấy phép sẽ không được dùng (`REQUIRE_MUSIC_LICENSE=true`),
vì Content ID và điều khoản của các dịch vụ nhạc AI là nguyên nhân phổ biến
khiến kênh mất kiếm tiền. Logo: đặt `BRAND_LOGO_PATH` tới 1 file PNG.

## Xem thử bố cục gần như không tốn API

Trong `.env` đặt `VISUAL_PROVIDER=card` và `VOICE_PROVIDER=silent` (chỉ
còn tốn 1 lần gọi AI viết kịch bản), rồi chạy:

```bash
ai-content-agent run "5 mẹo tiết kiệm điện mùa hè" --dry-run
```

`--dry-run` dựng video nhưng không đăng, in ra đường dẫn `final.mp4`.

## Sửa kịch bản trước khi dựng (Bàn kịch bản)

Viết kịch bản chỉ tốn một lần gọi AI; giọng đọc và hình mới là phần đắt.
Trên dashboard, bấm **✎ Viết kịch bản trước, sửa rồi mới dựng** thay cho
*Khởi động*: kịch bản hiện ở khu **Bàn kịch bản** để bạn sửa từng cảnh —
lời đọc, chữ trên màn hình, mô tả hình ảnh, tiêu đề, hashtag; thêm hoặc xoá
cảnh (tối đa 12). Bộ đếm cho biết số từ và thời lượng đọc ước tính.

- **Lưu** để giữ bản sửa (lưu trong `HISTORY_DB_PATH`, tắt app không mất).
- **Dựng thử** dựng video không đăng, kịch bản vẫn ở đó để sửa tiếp.
- **▶ Dựng video** dựng từ **đúng** kịch bản đã sửa — AI không viết lại —
  rồi video vào khu Chờ duyệt như thường. Dựng lỗi thì kịch bản vẫn còn.
- Cảnh thêm tay mà để trống mô tả hình thì app tự lấy lời đọc làm mô tả.
- Phần chữ đang gõ không bị mất khi trang tự cập nhật.

## Tạo video đầy đủ (không đăng)

```bash
ai-content-agent run "5 mẹo tiết kiệm điện mùa hè" --dry-run
```

## Chạy thật, đăng lên 1 hoặc nhiều nền tảng

```bash
ai-content-agent run "5 mẹo tiết kiệm điện mùa hè" --platform youtube --platform tiktok
```

Topic đã đăng trong 30 ngày gần nhất sẽ tự bị bỏ qua (so sánh không phân
biệt hoa thường/khoảng trắng). Muốn đăng lại vẫn được:

```bash
ai-content-agent run "5 mẹo tiết kiệm điện mùa hè" --platform youtube --force
```

## Sản xuất hàng loạt

Trên dashboard, khu **Xưởng hàng loạt**: dán danh sách chủ đề (mỗi dòng
một chủ đề, hoặc JSON Lines), chọn nền tảng ở LAUNCH PAD, bấm *Tạo lô*.
Trên CLI:

```bash
ai-content-agent batch chu_de.txt --platform youtube --platform facebook
ai-content-agent batches                      # tiến độ các lô
ai-content-agent batch --resume 3             # chạy tiếp lô #3 (sau khi tắt máy / Ctrl+C)
ai-content-agent batch --resume 3 --retry-failed
```

File danh sách có thể là văn bản thường, JSON Lines hoặc mảng JSON:

```
# dòng bắt đầu bằng # được bỏ qua
5 mẹo tiết kiệm điện mùa hè
{"topic": "Cách chọn dưa hấu ngọt", "style": "hài hước", "platforms": ["tiktok"]}
```

- Mỗi mục là một dòng trong SQLite (`HISTORY_DB_PATH`): tắt app giữa chừng
  không mất gì, lần mở sau mục đang chạy dở được làm tiếp **từ checkpoint**
  — dùng lại kịch bản đã viết và các cảnh giọng/hình đã tạo, không trả tiền
  lần hai.
- Một mục lỗi không làm dừng cả lô. Lỗi tạm thời (429, 5xx, mất mạng) được
  thử lại tối đa 3 lần, chờ tăng dần; lỗi khác ghi vào mục, bấm *Làm lại
  mục lỗi* sau khi sửa.
- Lô chạy **từng video một** qua cùng hàng đợi với các việc khác, nên không
  nhân chi phí hay số request đồng thời. Video làm xong vào khu Chờ duyệt
  như thường (vẫn chịu giới hạn đăng mỗi ngày).

## Biến thể và chống trùng nội dung

Chính sách spam của YouTube nêu đích danh "cùng nhạc nền… kịch bản do AI
viết" lặp lại giữa các video. Mỗi video được gán một **kế hoạch biến thể**
xoay vòng theo các video gần nhất (lưu trong lịch sử, không lặp lại cái vừa
dùng):

| Chiều | Lựa chọn | Cấu hình |
|---|---|---|
| Cách mở đầu | câu hỏi, sự thật gây sốc, danh sách, câu chuyện, phá lầm tưởng, trước/sau | `HOOK_STYLES` |
| Phong cách hình | cinematic, documentary, illustration, 3d, anime, watercolor | `VISUAL_STYLES` |
| Giọng đọc | danh sách giọng của engine, ví dụ `Kore,Puck,Charon` | `VOICE_NAMES` |
| Nhạc nền | các bài có giấy phép trong `assets/music` | — |

Kịch bản mới được so với các kịch bản gần đây (trùng cụm 3 từ). Nếu giống
từ `SIMILARITY_THRESHOLD`% trở lên (mặc định 35), app yêu cầu AI viết lại
một lần theo góc khác; độ giống còn lại hiện trên thẻ Chờ duyệt (đỏ nếu
vượt ngưỡng). Tắt toàn bộ bằng `VARIATION=false`.

## Kiểu video nào được xem nhiều (tự tạm nghỉ kiểu kém)

App đọc **lượt xem** các bài còn đang đăng (YouTube, TikTok, Facebook) rồi
chấm điểm từng lựa chọn của bốn chiều biến thể: cách mở đầu, phong cách
hình, giọng đọc, nhạc nền. Kết quả hiện ở khu **Hiệu quả theo kiểu video**
trên dashboard; lịch sử cũng ghi lượt xem cạnh từng link.

Cách chấm, để một video viral hay một nền tảng đông người không quyết định
tất cả:

- Chỉ tính bài đã đăng ít nhất **48 giờ**, trong **60 ngày** gần nhất.
- Lượt xem mỗi bài chia cho **trung vị lượt xem trên cùng nền tảng** — điểm
  ×1 nghĩa là bằng một bài điển hình ở đó. Điểm của một video là trung bình
  các nền tảng; điểm của một kiểu là **trung vị** các video dùng kiểu đó.
- Một kiểu bị **tạm nghỉ** khỏi vòng xoay khi: có ít nhất 3 video dùng nó,
  tổng cộng có ít nhất 8 video được tính, và điểm dưới ×0,5
  (`PRUNE_WEAK_RATIO=50`). Mỗi chiều luôn giữ ít nhất 2 lựa chọn; kiểu tệ
  nhất bị nghỉ trước. Khi số liệu cũ quá 60 ngày, kiểu đó tự quay lại để
  thử lại.
- Với số video ít, đây là quy tắc kinh nghiệm chứ không phải thống kê chặt
  chẽ — bảng hiện rõ số video để bạn tự đánh giá. Tắt việc tự tạm nghỉ bằng
  `AUTO_PRUNE_FORMATS=false` (bảng vẫn hiện).

Lượt xem tự cập nhật mỗi `STATS_REFRESH_HOURS` giờ (mặc định 12) khi
dashboard đang chạy; bấm **↻ Cập nhật lượt xem** hoặc chạy:

```bash
ai-content-agent stats            # cập nhật + in bảng
ai-content-agent stats --no-refresh
```

Quyền cần có: YouTube dùng luôn quyền đã cấp. TikTok cần thêm quyền
`video.list` — chạy lại `ai-content-agent tiktok-auth --scope
user.info.basic,video.publish,video.list` (app TikTok phải được cấp quyền
này). Facebook cần `read_insights`; phần đọc số liệu Facebook và TikTok viết
theo tài liệu, **chưa thử với tài khoản thật**. Nền tảng nào lỗi thì bỏ qua,
không ảnh hưởng nền tảng khác.

## Nguồn gốc (provenance)

Mỗi video có `provenance.json` cạnh `final.mp4`: engine và model đã viết,
vẽ, đọc; nhạc và giấy phép; kế hoạch biến thể; nhãn AI; điểm phát âm. Tóm
tắt được ghi vào metadata MP4 (`comment`/`description`). Video có nhạc
không giấy phép sẽ **không được đăng**. Đây chưa phải chứng chỉ C2PA có
chữ ký số (cần chứng thư ký số riêng) — xem Roadmap.

## Xem lịch sử đã sinh/đăng

```bash
ai-content-agent history --limit 20
```

## Lịch tự động trên dashboard

Trong ô **Lịch tự động** của dashboard, mở *⚙ Chỉnh lịch và danh sách chủ đề*:

- **Giờ chạy và các ngày** (T2…CN), hoặc *Cron nâng cao* nếu cần lịch phức
  tạp (ghi thứ bằng tên `mon tue wed thu fri sat sun`).
- **Nền tảng** đăng theo lịch, và công tắc **Bật lịch tự động**.
- **Danh sách chủ đề**: dán mỗi dòng một chủ đề để thêm (chủ đề trùng tự bỏ
  qua), bấm ✕ để xoá. Mỗi lượt lấy chủ đề **lâu chưa dùng nhất** và bỏ qua
  chủ đề vừa làm trong `DEDUP_WINDOW_DAYS` ngày; nhãn *kế tiếp* cho biết
  chủ đề của lượt tới.

Lịch và danh sách lưu trong `HISTORY_DB_PATH`: đổi là có hiệu lực ngay, không
cần khởi động lại, và vòng xoay chủ đề không quay về đầu khi mở lại app. Tham
số `--cron/--topic/--platform` của lệnh `dashboard` vẫn dùng được — chúng ghi
vào lịch đã lưu. Video làm theo lịch cũng vào khu Chờ duyệt.

## Chạy theo lịch bằng dòng lệnh (không cần dashboard)

```bash
ai-content-agent schedule "Chủ đề 1" "Chủ đề 2" --cron "0 9 * * *" --platform youtube
```

Giờ trong `--cron` tính theo `SCHEDULE_TIMEZONE` (mặc định
`Asia/Ho_Chi_Minh`). Mỗi lượt lệch ngẫu nhiên tối đa
`SCHEDULE_JITTER_MINUTES` phút (mặc định 15) để không đăng đúng một phút mỗi
ngày. Lượt bị lỡ vì máy ngủ **hoặc vì app đang tắt** sẽ được chạy bù khi app
mở lại, nếu trễ không quá 6 giờ (thời điểm chạy gần nhất lưu trong
`HISTORY_DB_PATH`).

## Duyệt trước khi đăng, đăng lại, gỡ bài

Mặc định (`REQUIRE_APPROVAL=true`) video dựng xong **không tự đăng**: nó vào
khu **Chờ duyệt** trên dashboard (xem video ngay trên trang, chọn nền tảng,
bấm *Duyệt & đăng* hoặc *Từ chối*). Lý do: YouTube từ 2026 xếp "sản xuất
hàng loạt tự động/tổng hợp" vào chính sách spam (có thể bị gỡ kênh), và
người vận hành có kinh nghiệm đều giữ bước người duyệt.

- **Đăng lại**: lần chạy "Một phần"/"Thất bại" có nút *Đăng lại* — chỉ đăng
  lên nền tảng chưa thành công, không dựng lại video, không đăng trùng.
- **Tự thử lại khi rớt mạng**:
  - Từng bước tải lên tự thử lại tối đa `UPLOAD_RETRIES` lần (mặc định 4),
    chờ tăng dần 2–4–8 giây. Thử lại theo **từng bước**, không đăng lại cả
    bài, nên không tạo bài trùng: YouTube tải nối tiếp đúng phiên tải lên dở
    dang; TikTok gửi lại đúng đoạn file bị rớt; Facebook Reels lặp lại đúng
    pha bị lỗi cho cùng một video.
  - Nếu **mất mạng hẳn** (chưa gửi được gì), dashboard tự xếp lịch đăng lại
    sau `AUTO_RETRY_MINUTES` phút (mặc định 5, rồi 10, 20 — tối đa 3 lần;
    đặt 0 để tắt). Thẻ tiến trình ghi "mất mạng — tự đăng lại lúc …".
  - Bước không an toàn để lặp lại (tải một lần là đăng luôn: video Facebook
    dài hơn 90 giây, Upload-Post) chỉ thử lại khi chắc chắn chưa kết nối
    được; nếu rớt giữa chừng thì báo lỗi để bạn kiểm tra rồi bấm *Đăng lại*.
- **Gỡ bài**: nút *Gỡ* xóa bài trên YouTube/Facebook (TikTok không có API
  xóa — app báo để gỡ tay trong ứng dụng). Chủ đề đã gỡ được phép làm lại.
- **Giới hạn**: `MAX_POSTS_PER_DAY` (mặc định 3 bài/nền tảng/24 h), cộng
  giới hạn cứng của từng nền tảng: YouTube 100/ngày/project, TikTok 15,
  Facebook 30 reels.
- **Không đăng trùng khi mạng rớt**: trước mỗi lần upload app ghi một "lần
  thử". Nếu lần thử trước không rõ kết quả (tắt app giữa chừng, mất phản
  hồi), lần đăng lại sẽ tìm video cùng tiêu đề trên kênh YouTube trước rồi
  mới upload.
- **Nhật ký người duyệt**: ghi ai duyệt / từ chối / đăng lại / gỡ, lúc nào,
  lý do. Trên dashboard điền ô *Người duyệt*; trên CLI dùng `--by` (mặc định
  tên user máy) và `--reason`.
- **Khai báo AI**: `AI_DISCLOSURE=true` đặt cờ `containsSyntheticMedia`
  (YouTube), `is_aigc` (TikTok) và ghi `AI_DISCLOSURE_TEXT` vào mô tả mọi
  nền tảng (Nghị định 142/2026 chấp nhận nhãn trong tiêu đề/mô tả).

CLI tương đương:

```bash
ai-content-agent review                       # danh sách chờ duyệt
ai-content-agent approve 12                   # duyệt & đăng lần chạy #12
ai-content-agent approve 12 --platform youtube
ai-content-agent reject 12 --reason "sai số liệu"
ai-content-agent publish 12                   # đăng lại nền tảng còn thiếu
ai-content-agent takedown 12 --platform facebook --by Lan --reason "khiếu nại"
```

## Dashboard web

```bash
ai-content-agent dashboard
```

Terminal sẽ in ra link dạng `http://127.0.0.1:8000/#token=...` — mở link
đó là đăng nhập luôn (token được lưu trong trình duyệt). Muốn token cố
định thì đặt `DASHBOARD_TOKEN` trong `.env`.

Chạy dashboard kèm lịch tự động (lịch chạy ngay trong tiến trình
dashboard, xoay vòng qua danh sách chủ đề, **tự bỏ qua chủ đề đã đăng
trong `DEDUP_WINDOW_DAYS` ngày**; khi mọi chủ đề đều đã đăng gần đây, lần
chạy được ghi vào mục Lỗi với hướng dẫn thêm chủ đề — giờ cron tính theo `SCHEDULE_TIMEZONE` (mặc định Asia/Ho_Chi_Minh), và lượt bị lỡ do máy ngủ/bận được chạy bù khi máy thức (trong 6 giờ) — nên danh sách chủ đề
cần dài hơn số ngày của cửa sổ chống trùng nếu đăng mỗi ngày):

```bash
ai-content-agent dashboard --cron "0 9 * * *" --topic "Chủ đề 1" --topic "Chủ đề 2" --platform youtube --platform tiktok
```

Giao diện "Mission Control" (phong cách vũ trụ cho dân IT):
- Nền sao 3 lớp chuyển động + sao băng (canvas), tự dừng khi tab ẩn.
- Mỗi nhiệm vụ là 1 **chuỗi phóng** 4 bước — Kịch bản → Giọng & hình
  (đếm x/y) → Dựng video → Đăng bài (x/y) — lấy từ **tiến độ thật** của
  backend, không phải hoạt ảnh giả; bước lỗi chuyển đỏ kèm tên bước.
- Lịch tự động dạng quỹ đạo với đồng hồ đếm ngược `T-HH:MM:SS`.
- Số liệu đếm tăng dần, thông báo nổi khi nhiệm vụ xong/lỗi, nút
  "Khởi động" có tên lửa cất cánh.
- Tôn trọng cài đặt "giảm chuyển động" của hệ điều hành (tắt hoạt ảnh).

Dashboard có:
- Thống kê: số video, lượt đăng theo nền tảng, lỗi 7 ngày qua.
- Form tạo video: chọn nền tảng (nền tảng chưa cấu hình bị khóa kèm lý
  do), chạy thử, đăng lại topic trùng.
- Tiến trình job realtime (đang chờ → đang chạy → thành công / một
  phần / bỏ qua / thất bại).
- Lịch tự động: cron, lần chạy tới, chủ đề tiếp theo.
- Lịch sử kèm link bài đã đăng, và log lỗi theo từng bước (khởi tạo,
  kịch bản, giọng đọc, hình ảnh, dựng video, thumbnail, đăng bài) — lỗi ở
  giọng/hình ghi rõ cảnh số mấy.

**Bảo mật:** mọi API của dashboard đều yêu cầu token, kể cả trên
localhost, vì dashboard có thể đăng bài thật lên tài khoản của bạn. Mặc
định chỉ nghe trên `127.0.0.1`. Nếu mở ra mạng ngoài (`--host 0.0.0.0`),
hãy đặt sau reverse proxy có HTTPS để token không bị gửi dạng plain text.

## Xuất project nháp CapCut (chỉnh tay)

Mỗi video đã dựng có thể xuất thành **project nháp mở được trong CapCut
desktop**, với từng phần là 1 track riêng để sửa: hình từng cảnh (ảnh có
keyframe zoom chậm, clip lặp cho đủ thời lượng), giọng đọc, nhạc nền (âm
lượng nhỏ), logo, chữ tiêu đề vàng, phụ đề (nhập từ `subtitles.srt`).

```bash
pip install -e ".[capcut]"     # thư viện pycapcut (cộng đồng, không chính thức)
```

3 cách xuất:
- Dashboard: nút **⇪ Xuất CapCut** trên mỗi nhiệm vụ đã dựng xong.
- CLI: `ai-content-agent capcut` (lần chạy mới nhất) hoặc
  `ai-content-agent capcut output/<thư mục lần chạy>`.
- Tự động sau mỗi lần dựng: đặt `CAPCUT_EXPORT=true` trong `.env` (lỗi
  xuất CapCut chỉ ghi vào log, không chặn việc đăng bài).

**Chuẩn bị một lần cho CapCut 9.x** (bản mới đọc draft khác bản cũ):

1. Mở CapCut, tạo **một project trống**, đặt tên ví dụ `Mẫu AI`, rồi **thoát
   CapCut**.
2. Trong `.env`: `CAPCUT_TEMPLATE=Mẫu AI` (mặc định `auto` = project gần
   nhất do CapCut tạo).
3. Kiểm tra: `ai-content-agent capcut --check` in ra phiên bản CapCut dò được
   và CapCut có đang chạy không.

Khi xuất, app sao chép "dấu phiên bản" và cách bố trí file
(`draft_info.json` / `draft_content.json` / `template-2.tmp`) của project
mẫu, tạo `draft_id` mới mỗi lần, không chép thư mục `Timelines/` (CapCut tự
dựng lại khi mở), đếm độ dài chữ theo UTF-16 như CapCut, sao lưu
`root_meta_info.json` trước khi đăng ký project mới. App **từ chối ghi** khi
CapCut đang chạy, hoặc khi CapCut là bản **10.x trở lên** (bản 10 báo draft do
công cụ tạo là "nội dung bị hỏng") — khi đó dùng *Gói dựng* bên dưới, hoặc
ép bằng `--force` / `CAPCUT_FORCE_WRITE=true`.

**Gói dựng (mọi phiên bản, mọi phần mềm):** nút **▤ Gói dựng** trên
dashboard hoặc `ai-content-agent capcut --bundle` tạo thư mục `edit_bundle/`
gồm file **FCPXML** (mở bằng DaVinci Resolve, Final Cut Pro), `captions.srt`,
thư mục `media/` và `README.txt` liệt kê chữ hook từng cảnh. Với CapCut bản
nào cũng được: nhập media + file SRT. Khi xuất tự động mà CapCut từ chối, app
tự tạo gói dựng thay thế.

Project được ghi vào thư mục nháp của CapCut trên Windows
(`%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft`, đổi bằng
`CAPCUT_DRAFTS_DIR`). **Đóng CapCut trước khi xuất**, mở lại để thấy project.
Media được tham chiếu trực tiếp từ thư mục `output/...` của lần chạy — đừng
xóa/di chuyển thư mục đó khi còn chỉnh trong CapCut.

**Lưu ý quan trọng:** CapCut không có API hay định dạng project chính thức.
Bộ xuất dùng `pycapcut` (định dạng do cộng đồng phân tích ngược, chỉ hỗ trợ
**CapCut bản quốc tế**, không phải JianYing; thư viện **không có file giấy
phép** nên app không đóng gói nó — bạn tự cài) và cách gia cố cho 9.x theo
ma trận phiên bản của [capcut-cli](https://github.com/renezander030/capcut-cli/blob/master/docs/version-support.md)
(MIT). Mới được kiểm tra trên bản giả lập — **chưa mở thử trong CapCut
thật**. Nếu mở được/không mở được, cho biết phiên bản CapCut để cập nhật.

Nếu project nháp không mở được, mọi thứ để dựng lại tay đã có sẵn trong thư
mục lần chạy: `scene_01_visual.*`, `scene_01_voice.wav`, … theo thứ tự,
`subtitles.srt` (dùng chức năng nhập phụ đề từ file SRT của CapCut), và `timeline.json` ghi
thời điểm bắt đầu/độ dài từng cảnh.

## Setup từng nền tảng

### YouTube
1. Tạo project trên Google Cloud Console, enable **YouTube Data API v3**.
2. Tạo OAuth client ID (loại *Desktop app*), tải `client_secret.json` về
   gốc project.
3. Chạy 1 lần trên máy có trình duyệt:
   ```bash
   ai-content-agent youtube-auth
   ```
   Token được lưu vào `youtube_token.json` và tự làm mới các lần sau. Khi
   đăng bài app **không bao giờ** mở trình duyệt (để không bị treo trên
   server); nếu thiếu token, job báo lỗi kèm hướng dẫn chạy lệnh trên. Chạy
   trên VPS thì xác thực ở máy bạn rồi copy file token lên.
4. Trong Google Cloud, để màn hình OAuth consent ở trạng thái **In
   production** (chế độ *Testing* làm refresh token hết hạn sau 7 ngày →
   lịch tự động gãy âm thầm). Dashboard cảnh báo khi token được 5–7 ngày
   tuổi, và nếu Google từ chối làm mới token thì lỗi ghi rõ nguyên nhân.
   Từ 1/6/2026 upload có quota riêng, mặc định 100 video/ngày/project.
   `YOUTUBE_PRIVACY` chọn public / unlisted / private; app đọc lại trạng
   thái thật sau khi upload vì cài đặt kênh có thể ghi đè.

### TikTok
1. Tạo app trên [TikTok for Developers](https://developers.tiktok.com/),
   bật sản phẩm **Content Posting API** (Direct Post).
2. Xin quyền `video.publish`.
3. Điền `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, rồi đăng nhập một lần:
   ```bash
   ai-content-agent tiktok-auth
   ```
   Lệnh in ra **Redirect URI** (mặc định `http://localhost:8721/callback/`)
   — thêm đúng địa chỉ đó vào phần *Login Kit* của app TikTok trước, rồi chạy
   lại. Trình duyệt mở trang TikTok, bạn bấm đồng ý, token được lưu vào
   `tiktok_token.json` và tự làm mới từ đó (không cần `TIKTOK_REFRESH_TOKEN`
   nữa). Đổi cổng bằng `--port`. Quyền xin mặc định theo `TIKTOK_MODE`
   (`video.publish` hoặc `video.upload`), đổi bằng `--scope`.
   - App TikTok loại **Web** chỉ cho redirect về địa chỉ https đã đăng ký:
     chạy `ai-content-agent tiktok-auth --redirect-uri https://ten-mien/cua-ban`,
     sau khi đồng ý thì copy địa chỉ trình duyệt đang đứng (có `?code=...`)
     dán vào terminal.
   - Lệnh viết theo luồng OAuth TikTok đã công bố (app Desktop dùng PKCE với
     mã băm dạng hex — khác chuẩn; có `--pkce base64url|none` nếu TikTok đổi),
     **chưa chạy với app thật**. `TIKTOK_ACCESS_TOKEN` tĩnh chỉ là phương án
     tạm vì hết hạn trong vài giờ.
4. Khi app chưa được TikTok audit, video chỉ đăng ở chế độ riêng tư
   (`TIKTOK_PRIVACY_LEVEL=SELF_ONLY`), tối đa 5 người dùng/24 h. Audit xong
   thì đổi thành `PUBLIC_TO_EVERYONE`; mỗi tài khoản đăng được khoảng 15
   bài/ngày. Lưu ý TikTok **từ chối audit** app "chỉ dùng cá nhân hoặc nội
   bộ công ty".
5. Trước mỗi bài app gọi `creator_info` (yêu cầu của TikTok) để kiểm tra
   chế độ riêng tư và độ dài cho phép, đặt `is_aigc`, và chờ TikTok xử lý
   xong để lấy link bài (nếu quá 3 phút thì ghi trạng thái "processing").

**Đăng công khai khi app chưa được audit** — hai cách:

- `TIKTOK_MODE=inbox` (cần quyền `video.upload`): video vào hộp thư nháp
  của TikTok, bạn mở app TikTok, viết caption, chọn chế độ hiển thị và bấm
  đăng. Mỗi video một lần chạm, nhưng không cần audit.
- `TIKTOK_VIA=upload-post`: đăng qua dịch vụ trung gian trả phí
  [Upload-Post](https://www.upload-post.com) (đã có app TikTok được audit).
  Kết nối tài khoản TikTok trong dashboard Upload-Post dưới một tên profile,
  rồi điền `UPLOAD_POST_API_KEY` và `UPLOAD_POST_USER`. App gửi
  `privacy_level` và `is_aigc` theo SDK chính thức của Upload-Post; **chưa
  thử với tài khoản thật** — kiểm tra vài bài đầu trong dashboard
  Upload-Post. Bài được ghi trạng thái "processing" kèm request id.

### Facebook Page
1. Tạo app trên [Meta for Developers](https://developers.facebook.com/).
2. Lấy token có quyền `pages_manage_posts`, `pages_read_engagement`,
   `pages_show_list`, điền `FACEBOOK_PAGE_ID` và `FACEBOOK_ACCESS_TOKEN`.
   Có thể dán Page token, hoặc token **System User** của Business Manager
   (không phải đăng nhập lại mỗi 60 ngày) — app tự đổi sang Page token của
   Page đó. Bản production cần App Review + Business Verification.
3. Video 3–90 giây, tối thiểu 540x960, được đăng dạng **Reels**
   (`/video_reels`, tối đa 30 reels/24 h/Page); dài hơn thì đăng thành video
   thường; ngắn hơn 3 giây hoặc độ phân giải thấp thì bị từ chối trước khi
   upload. Graph API không có trường khai báo AI nên app ghi dòng
   `AI_DISCLOSURE_TEXT` vào mô tả.

## Mở rộng thêm nền tảng/engine mới

1. Thêm nền tảng đăng bài (ví dụ X, LinkedIn, Pinterest):
   - Viết class mới trong `publishers/`, implement `Publisher.publish()`.
   - Đăng ký vào `PUBLISHERS` trong `publishers/__init__.py` — CLI và
     API dashboard tự nhận nền tảng mới từ đây.
   - Thêm biến môi trường vào `config.py` (+ 1 dòng trong
     `Config.status()` để dashboard biết đã cấu hình chưa), và 1 nhánh
     trong `ContentAgent._build_publishers()` để truyền credentials.
   - (Tuỳ chọn) thêm tên hiển thị vào `PLATFORM_LABELS` trong
     `web/static/app.js`.
2. Thêm AI engine mới (kịch bản, hình ảnh, video hoặc giọng đọc):
   - Viết class mới trong `providers/`, implement 1 trong
     `TextGenerator.complete()`, `ImageGenerator.generate_image()`,
     `VideoGenerator.generate_clip()`, `VoiceGenerator.synthesize()`.
   - Đăng ký vào `TEXT_PROVIDERS` / `VISUAL_PROVIDERS` /
     `VOICE_PROVIDERS` trong `providers/__init__.py`, thêm nhánh trong
     `agent.py` để truyền key, và 1 dòng trong `Config.status()`.
   - Chọn qua `TEXT_PROVIDER` / `VISUAL_PROVIDER` / `VOICE_PROVIDER`.

Không cần sửa `studio/` hay `content_pipeline.py` cho cả hai trường hợp.

## Test

```bash
pytest
```

Test dùng provider/publisher giả — không gọi API thật (không tốn tiền,
không cần key). Bao gồm: **dựng video thật bằng FFmpeg** (ảnh + nhạc +
logo, và clip video bị lặp cho khớp lời đọc — kiểm tra kích thước
1080x1920, có audio, đúng thời lượng), parse/kiểm tra kịch bản chia cảnh,
phụ đề không bao giờ cắt ngang câu, lỗi được gắn đúng bước và số cảnh,
interface compliance, pipeline end-to-end,
chống trùng topic, `--force`, dry-run, publisher lỗi không chặn
publisher khác, ghi log lỗi từng bước, parse JSON từ model (kể cả khi bọc
trong ```` ```json ````), toàn bộ API dashboard (xác thực token, trạng thái
job, validate input, không lộ secret), publisher TikTok/Facebook với HTTP
giả lập (lỗi API, upload thất bại, chia chunk), và tạo thumbnail thật bằng
ffmpeg (tự skip nếu máy không có ffmpeg).

## Roadmap

- [x] Tự thử lại khi tải lên bị rớt mạng (từng bước + tự đăng lại sau khi mất mạng).
- [x] Thêm bước tạo thumbnail tự động.
- [x] Thêm bước lưu lịch sử đã đăng (tránh trùng topic) — SQLite đơn giản.
- [x] Xem lịch sử qua CLI (`ai-content-agent history`).
- [x] Dashboard web xem lịch đăng / log lỗi / tạo video.
- [x] Kết nối Meta Muse Spark (text) qua Meta Model API.
- [x] Tập trung 3 nền tảng YouTube, TikTok, Facebook (đã bỏ Instagram).
- [x] **Bước 1 — Studio tự động:** kịch bản chia cảnh, hình/clip + giọng
      đọc mỗi cảnh, phụ đề, nhạc nền, logo, xuất MP4.
- [ ] **Bước 2 — App desktop Windows** (file cài `.exe`) — tạm hoãn theo yêu cầu, bạn tự đóng gói khi cần.
- [x] P3: MCP server + skill Claude Code, chi phí từng video + hạn mức ngày, ComfyUI (Wan 2.2/FramePack chạy trên máy).
- [x] Avatar người nói khớp miệng qua ComfyUI trên máy (bố cục góc màn hình hoặc toàn màn hình).
- [ ] Avatar qua dịch vụ trả phí (HeyGen, D-ID…) — chưa làm.
- [x] P2: CapCut 9.x (dò phiên bản, khuôn từ app, chặn 10.x), gói dựng FCPXML, TTS tiếng Việt chạy trên máy, tự dò NVENC.
- [ ] **Bước 3 — Bản server/VPS** chạy 24/7.
- [x] **Bước 4 — Xuất project nháp CapCut** (cần xác nhận trên CapCut desktop thật).
- [x] Sửa kịch bản từng cảnh ngay trên dashboard trước khi dựng (Bàn kịch bản).
- [x] Lệnh `tiktok-auth` đăng nhập TikTok một lần (chưa chạy với app thật).
- [x] Phụ đề theo từng từ (karaoke), chuẩn hoá NFC, đọc số tiếng Việt, font đóng gói.
- [x] Căn thời gian từng từ + điểm phát âm bằng faster-whisper (tuỳ chọn, chưa thử với model thật).
- [x] Sản xuất hàng loạt có hàng đợi bền và checkpoint.
- [x] Biến thể (hook, hình, giọng, nhạc) và chống trùng kịch bản.
- [x] Sổ giấy phép nhạc, provenance.json, metadata, nhãn AI trên video.
- [ ] Chứng chỉ C2PA có chữ ký số.
- [x] Đọc lượt xem và tự tạm nghỉ kiểu video kém (cần chạy thật một thời gian mới có đủ số liệu).
- [ ] Muse Video — chờ Meta mở API chính thức, rồi implement
      `MetaMuseVideoProvider.generate_clip()`.
- [x] Quản lý lịch và danh sách chủ đề ngay trên dashboard.
- [x] MCP: viết/sửa/dựng bản nháp, quản lý cấu hình lịch và danh sách chủ đề dùng chung dashboard.
