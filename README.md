# ai-content-agent

Agent tự động hóa toàn bộ chuỗi: **sinh ý tưởng/script → tạo video → đăng
lên nhiều nền tảng mạng xã hội**, dùng GPT, Claude, Google AI (Gemini/Veo)
và Meta Muse làm engine chính, với publisher cho YouTube, TikTok,
Facebook và Instagram.

Kiến trúc được thiết kế để **thêm nền tảng mới chỉ cần viết 1 class**,
không phải sửa lại pipeline.

## Kiến trúc

```
topic (string)
   │
   ▼
TextGenerator   (gpt | claude | gemini)   -> ScriptResult{title, script, hashtags}
   │
   ▼
VideoGenerator  (veo | muse)              -> VideoResult{file_path}
   │
   ▼
Thumbnail       (ffmpeg + Pillow)         -> VideoResult.thumbnail_path
   │
   ▼
Publisher[]     (youtube | tiktok | facebook | instagram)  -> PublishResult{url}
   │
   ▼
HistoryStore    (SQLite)                  -> lưu run + từng lượt đăng, chặn topic trùng
```

- `src/ai_content_agent/providers/` — mỗi AI engine là 1 class implement
  `TextGenerator` hoặc `VideoGenerator` (`providers/base.py`).
- `src/ai_content_agent/publishers/` — mỗi nền tảng đăng bài là 1 class
  implement `Publisher` (`publishers/base.py`).
- `src/ai_content_agent/pipeline/content_pipeline.py` — nối 3 bước lại,
  không biết chi tiết của bất kỳ provider/publisher cụ thể nào.
- `src/ai_content_agent/media/thumbnail.py` — cắt 1 frame từ video,
  crop giữa về 1280x720, phủ tiêu đề lên.
- `src/ai_content_agent/history.py` — SQLite lưu lịch sử, chống đăng
  trùng topic trong `DEDUP_WINDOW_DAYS` ngày.
- `src/ai_content_agent/agent.py` — đọc config, dựng pipeline cụ thể.
- `src/ai_content_agent/cli.py` — chạy 1 lần (`run`) hoặc theo lịch
  (`schedule`, dùng cron expression).

### Trạng thái từng provider/publisher

| Thành phần | Trạng thái |
|---|---|
| GPT (OpenAI) — script | hoạt động, cần `OPENAI_API_KEY` |
| Claude (Anthropic) — script | hoạt động, cần `ANTHROPIC_API_KEY` |
| Gemini (Google AI) — script | hoạt động, cần `GOOGLE_API_KEY` |
| Veo (Google AI Pro) — video | hoạt động nếu tài khoản có quyền Veo; tên model/tham số nên verify lại với docs hiện tại vì Google đổi khá thường xuyên |
| Meta Muse — video | **chỉ là interface stub** — Meta chưa có API public ổn định tại thời điểm viết code này; điền endpoint/payload thật vào `providers/meta_muse_provider.py` khi bạn có quyền truy cập |
| YouTube — publish | hoạt động, cần OAuth app (xem dưới) |
| TikTok — publish | khung đúng theo Content Posting API, cần app TikTok for Business được duyệt quyền `video.publish` |
| Facebook Page — publish | hoạt động, cần Page access token dài hạn |
| Instagram Reels — publish | hoạt động nhưng yêu cầu video đã có public URL (upload lên S3/GCS trước khi gọi) |
| Thumbnail tự động | hoạt động, cần `ffmpeg` trên máy; YouTube chỉ nhận custom thumbnail nếu kênh đã xác minh số điện thoại (không xác minh thì bỏ qua, video vẫn đăng bình thường) |
| Chống đăng trùng topic | hoạt động (SQLite, không cần cài thêm gì) |

## Cài đặt

Cần Python 3.11+ và `ffmpeg` (cho bước tạo thumbnail):

```bash
# macOS: brew install ffmpeg   |   Ubuntu: sudo apt install ffmpeg
```

```bash
cd ai-content-agent
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # rồi điền API key
```

## Chạy thử (không đăng, chỉ sinh nội dung)

```bash
python scripts/run_once.py "5 mẹo tiết kiệm điện mùa hè" --dry-run
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

## Setup từng nền tảng

### YouTube
1. Tạo project trên Google Cloud Console, enable **YouTube Data API v3**.
2. Tạo OAuth client ID (loại *Desktop app*), tải `client_secret.json` về
   gốc project.
3. Lần chạy đầu sẽ mở browser để bạn consent; token được lưu vào
   `youtube_token.json` và tự refresh các lần sau.

### TikTok
1. Tạo app trên [TikTok for Business Developer Portal](https://developers.tiktok.com/).
2. Xin quyền `video.publish` (cần review).
3. Lấy access token dài hạn cho tài khoản mục tiêu, bỏ vào
   `TIKTOK_ACCESS_TOKEN`.

### Facebook / Instagram
1. Tạo app trên [Meta for Developers](https://developers.facebook.com/).
2. Lấy Page access token dài hạn (`FACEBOOK_PAGE_ID`,
   `FACEBOOK_ACCESS_TOKEN`).
3. Với Instagram: lấy id của IG Business account đã liên kết với Page
   (`INSTAGRAM_USER_ID`), dùng cùng access token.

## Mở rộng thêm nền tảng/engine mới

1. Thêm nền tảng đăng bài (ví dụ X, LinkedIn, Pinterest):
   - Viết class mới trong `publishers/`, implement `Publisher.publish()`.
   - Đăng ký vào `PUBLISHERS` trong `publishers/__init__.py`.
   - Dùng ngay qua `--platform <tên>`.
2. Thêm AI engine mới (text hoặc video):
   - Viết class mới trong `providers/`, implement `TextGenerator` hoặc
     `VideoGenerator`.
   - Đăng ký vào `TEXT_PROVIDERS`/`VIDEO_PROVIDERS` trong
     `providers/__init__.py`.
   - Chọn qua `TEXT_PROVIDER`/`VIDEO_PROVIDER` trong `.env`.

Không cần sửa `content_pipeline.py` hay `agent.py` cho cả hai trường hợp.

## Test

```bash
pytest
```

Test dùng provider/publisher giả — không gọi API thật (không tốn tiền,
không cần key). Bao gồm: interface compliance, pipeline end-to-end,
chống trùng topic, `--force`, dry-run, publisher lỗi không chặn
publisher khác, và tạo thumbnail thật bằng ffmpeg (tự skip nếu máy
không có ffmpeg).

## Roadmap

- [ ] Thay `requests` upload trực tiếp bằng pre-signed URL upload cho
      video lớn (YouTube/TikTok resumable upload đã hỗ trợ, cần hoàn
      thiện retry/backoff).
- [x] Thêm bước tạo thumbnail tự động.
- [x] Thêm bước lưu lịch sử đã đăng (tránh trùng topic) — SQLite đơn giản.
- [x] Xem lịch sử qua CLI (`ai-content-agent history`).
- [ ] Dashboard web xem lịch đăng / log lỗi.
- [ ] Tự upload video lên storage public (S3/GCS) để Instagram dùng được
      ngay trong pipeline.
- [ ] Điền API thật cho Meta Muse khi có quyền truy cập.
