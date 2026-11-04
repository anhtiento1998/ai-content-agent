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
| Hình ảnh — nền màu offline | `VISUAL_PROVIDER=card` — không cần API, để xem thử bố cục | có |
| Hình ảnh — Muse Video (Meta) | **chưa có** — tính đến 10/2026 Meta chưa mở API. Chọn `muse` sẽ báo lỗi ngay khi khởi tạo (không tốn tiền viết kịch bản trước) | — |
| Giọng đọc — Gemini / GPT TTS | `VOICE_PROVIDER=gemini\|gpt`, chọn giọng qua `VOICE_NAME` | chưa (cần key) |
| Giọng đọc — không giọng | `VOICE_PROVIDER=silent` — video chỉ có phụ đề + nhạc | có |
| Dựng video (FFmpeg): zoom ảnh, ghép cảnh, phụ đề, nhạc, logo, chuẩn hóa âm lượng | luôn bật | có (dựng video thật trong test) |
| Đăng YouTube | OAuth app (xem dưới) | HTTP giả lập: chưa; API thật: chưa |
| Đăng TikTok | Content Posting API, tự chia chunk cho video > 64MB. **Trước khi TikTok audit app, bài chỉ đăng ở chế độ riêng tư** (`TIKTOK_PRIVACY_LEVEL=SELF_ONLY`) | HTTP giả lập: có; API thật: chưa |
| Đăng Facebook Page | Page access token dài hạn; trả về link `facebook.com/watch` | HTTP giả lập: có; API thật: chưa |
| Thumbnail tự động | YouTube chỉ nhận custom thumbnail nếu kênh đã xác minh số điện thoại (không thì bỏ qua, video vẫn đăng) | có |
| Chống đăng trùng topic, dashboard, lịch tự động | — | có |

**Lưu ý chi phí:** API của OpenAI, Anthropic, Google được tính tiền
**riêng** với gói ChatGPT Plus / Claude Pro / Google AI Pro dùng trên web
— cần tạo API key và nạp credit ở trang developer của từng hãng. Một video
40 giây ≈ 1 lần gọi kịch bản + 4–8 ảnh (hoặc 4–8 clip Veo) + 4–8 lần đọc
giọng.

Phụ đề được căn thời gian theo độ dài từng câu trong mỗi cảnh (không phải
nhận dạng giọng từng từ), nên luôn khớp đầu/cuối cảnh nhưng có thể lệch
nhẹ trong cảnh dài.

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

Nhạc nền: bỏ file `.mp3`/`.wav` không bản quyền vào `assets/music/`, mỗi
video chọn ngẫu nhiên 1 bài. Logo: đặt `BRAND_LOGO_PATH` tới 1 file PNG.

## Xem thử bố cục gần như không tốn API

Trong `.env` đặt `VISUAL_PROVIDER=card` và `VOICE_PROVIDER=silent` (chỉ
còn tốn 1 lần gọi AI viết kịch bản), rồi chạy:

```bash
ai-content-agent run "5 mẹo tiết kiệm điện mùa hè" --dry-run
```

`--dry-run` dựng video nhưng không đăng, in ra đường dẫn `final.mp4`.

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

## Xem lịch sử đã sinh/đăng

```bash
ai-content-agent history --limit 20
```

## Chạy theo lịch (cron, trong 1 tiến trình dài hạn)

```bash
ai-content-agent schedule "Chủ đề 1" "Chủ đề 2" --cron "0 9 * * *" --platform youtube
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
chạy được ghi vào mục Lỗi với hướng dẫn thêm chủ đề — nên danh sách chủ đề
cần dài hơn số ngày của cửa sổ chống trùng nếu đăng mỗi ngày):

```bash
ai-content-agent dashboard --cron "0 9 * * *" --topic "Chủ đề 1" --topic "Chủ đề 2" --platform youtube --platform tiktok
```

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

### TikTok
1. Tạo app trên [TikTok for Developers](https://developers.tiktok.com/),
   bật sản phẩm **Content Posting API** (Direct Post).
2. Xin quyền `video.publish`.
3. Lấy access token cho tài khoản mục tiêu, bỏ vào `TIKTOK_ACCESS_TOKEN`.
4. Khi app chưa được TikTok audit, video chỉ đăng ở chế độ riêng tư
   (`TIKTOK_PRIVACY_LEVEL=SELF_ONLY`). Audit xong thì đổi thành
   `PUBLIC_TO_EVERYONE`.

### Facebook Page
1. Tạo app trên [Meta for Developers](https://developers.facebook.com/).
2. Lấy Page access token dài hạn có quyền `pages_manage_posts` và
   `pages_read_engagement`, điền `FACEBOOK_PAGE_ID` và
   `FACEBOOK_ACCESS_TOKEN`.

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

- [ ] Retry/backoff khi upload lên YouTube/TikTok/Facebook bị lỗi mạng
      tạm thời.
- [x] Thêm bước tạo thumbnail tự động.
- [x] Thêm bước lưu lịch sử đã đăng (tránh trùng topic) — SQLite đơn giản.
- [x] Xem lịch sử qua CLI (`ai-content-agent history`).
- [x] Dashboard web xem lịch đăng / log lỗi / tạo video.
- [x] Kết nối Meta Muse Spark (text) qua Meta Model API.
- [x] Tập trung 3 nền tảng YouTube, TikTok, Facebook (đã bỏ Instagram).
- [x] **Bước 1 — Studio tự động:** kịch bản chia cảnh, hình/clip + giọng
      đọc mỗi cảnh, phụ đề, nhạc nền, logo, xuất MP4.
- [ ] **Bước 2 — App desktop Windows** (file cài `.exe`).
- [ ] **Bước 3 — Bản server/VPS** chạy 24/7.
- [ ] **Bước 4 — Xuất project nháp CapCut** từ thư mục của mỗi lần chạy.
- [ ] Xem trước video + sửa kịch bản từng cảnh ngay trên dashboard trước
      khi dựng.
- [ ] Phụ đề khớp từng từ (nhận dạng giọng đọc để lấy thời gian chính xác).
- [ ] Muse Video — chờ Meta mở API chính thức, rồi implement
      `MetaMuseVideoProvider.generate_clip()`.
- [ ] Quản lý danh sách chủ đề cho lịch tự động ngay trên dashboard
      (hiện truyền qua `--topic` khi khởi động).
