# API (v1)

Base: `http://127.0.0.1:<port>/api/v1` — prefix `/api` vẫn hoạt động cho tương
thích ngược. Mọi lỗi trả cùng một envelope:

```json
{ "ok": false, "error": "thông điệp tiếng Việt" }
```

Mỗi response có header `X-Request-ID` (echo lại giá trị client gửi, hoặc tự sinh)
để đối chiếu với log `rid=…`.

## Tenant

Header `X-Workspace` (mặc định `local`, `[a-z0-9_-]{1,64}`). Hiện là workspace
cục bộ; khi có đăng nhập, server sẽ lấy tenant từ identity và bỏ qua header này.
Mọi bảng đều có `tenant_id`, mọi query đều lọc theo tenant.

## Hỏi đáp

| Method | Path | Body / query | Kết quả |
|---|---|---|---|
| POST | `/qa/ask` | `{question, session_id?, source?}` | `{session_id, question, answer:{id, turn_id, session_id, text, status, answered, entry_id, score, matched, candidates}}` |
| GET | `/qa/unanswered` | `limit` | `{items:[{question_norm, asks, last_asked, sample}]}` |
| POST | `/qa/answers/{id}/speech` | `{voice?}` | `{mode:"cached", url, seconds}` hoặc `{mode:"stream", text, voice}` |

`/qa/detect`, `/capture`, `/devices`, `/pause`, `/clear` đã bị xoá: mic và câu
hỏi thuộc về trình duyệt, không còn điều khiển thiết bị phía server.

## Mic (WebSocket)

| Hướng | Nội dung |
|---|---|
| Kết nối | `ws(s)://<host>/ws/audio?sample_rate=16000` |
| Client → Server | binary PCM16LE mono, 16 000 Hz, gói ~20 ms, tối đa **64 KB/gói** |
| Server → Client | `{type:"ready",sample_rate,mode,max_frame_bytes}` · `partial` · `final` · `level` · `queue` · `warning` · `error` · `settings_changed` |
| Giới hạn | tối đa **8 phiên** đồng thời; vượt → đóng **1013** |
| Đóng | gửi `{"type":"stop"}` hoặc đóng socket |

Mỗi kết nối là một phiên nhận dạng độc lập (segmenter + event bus riêng), dùng
chung một engine ONNX. Sample rate khác 16 000 → đóng **1003**; origin khác host
→ **1008**; cài đặt đổi → server gửi `settings_changed` rồi đóng để client mở
phiên mới. Gói quá lớn bị bỏ và trả `warning`.

`status`: `matched` (≥ ngưỡng), `near_miss` (cấu hình), `unanswered` (fallback +
`candidates` top-3).

## Phiên

| Method | Path | Kết quả |
|---|---|---|
| GET | `/sessions?limit&offset` | danh sách phiên, mới nhất trước |
| GET | `/sessions/{id}` | phiên + turns + answer (kèm `matched` dựng lại từ kho; `candidates` chỉ có ở response `ask`) |
| DELETE | `/sessions/{id}` | xoá (cascade turns/answers), ghi audit |

## Kho câu hỏi

| Method | Path | Ghi chú |
|---|---|---|
| GET | `/faq/entries?q&category&active&limit&offset` | tìm theo câu hỏi/đáp án |
| POST | `/faq/entries` | `{question, answer, category}` — chặn trùng exact |
| PATCH | `/faq/entries/{id}` | `{question?, answer?, category?, active?}` |
| DELETE | `/faq/entries/{id}` | xoá cả bản đọc lưu sẵn |
| POST | `/faq/import` | multipart `file` CSV UTF-8, cột `question,answer,category`, ≤2 MB → `{total, added, duplicates[], errors[]}` |
| POST | `/faq/reindex` | embed lại entry thiếu/đổi version |
| GET | `/faq/stats` | `{entries, active, embedded, categories, model, version, dim, threshold, near_threshold, embed_note}` |
| POST | `/faq/entries/{id}/prerender` | `{voice?}` → job nền `{job:{id,status,…}}` (409 nếu đang tổng hợp) |
| GET | `/faq/prerender/{job}` | `{status: running|done|error, seconds, error}` |
| GET | `/faq/entries/{id}/audio?voice=` | WAV đã lưu, hỗ trợ Range |

Import chống trùng: trùng exact (đã chuẩn hoá) và cosine ≥ 0,97 với entry đã có
hoặc với câu vừa nhận trong cùng tệp.

## Giọng đọc

Khi khởi động `python run.py`, model VieNeu được **nạp trước vào RAM** ở luồng
nền (~10–15 giây, log `TTS model đã nạp vào RAM`), nên lần bấm “Đọc” đầu tiên
không còn chờ nạp. Tắt bằng `--no-tts-preload`; muốn chạy thử luôn một câu lúc
khởi động đặt `TTS_PRELOAD_INFER=1`. Khi đổi giọng trong Cài đặt, frontend gọi
`POST /tts/preload` để nạp giọng đó ở nền, rồi poll `GET /tts/status`
(`loaded`, `preloading`, `preload_error`, `warmed_voice`). Tốc độ đọc 0.8–2.0×
do client áp dụng bằng `playbackRate` khi phát, nên không có tham số `speed`
trong API và file WAV tải về vẫn ở tốc độ gốc.

| Method | Path | Ghi chú |
|---|---|---|
| GET | `/tts/voices` | danh sách giọng, `max_chars`, `max_words`, status |
| GET | `/tts/status` | trạng thái nạp model/giọng |
| POST | `/tts/preload` | `{voice?}` → nạp engine/giọng vào RAM ở nền |
| GET | `/tts/limits` | `{max_quick_chars:1000, max_words:2000, max_stream_chars:20000, sample_rate, busy}` |
| POST | `/tts` | WAV trong RAM cho văn bản ≤1000 ký tự |
| POST | `/tts/stream` | PCM16 chunked, ≤2000 từ; header `X-Tts-Session`, `X-Sample-Rate`, `X-Estimated-Seconds`; lỗi 400/409/413/507 trước khi stream |
| GET | `/tts/sessions/{id}.wav` | WAV hoàn chỉnh, Range 206; 425 nếu chưa xong |
| GET | `/tts/sessions/{id}` | tiến độ `{seconds, bytes, finalized, progress}` |
| DELETE | `/tts/sessions/{id}` | huỷ + xoá temp |

## Vận hành

| Method | Path | Ghi chú |
|---|---|---|
| GET | `/audit?limit` | thao tác nhạy cảm: `faq.create/update/delete/import/reindex/prerender`, `session.delete` |
| GET | `/health` | engine hiện tại |
| GET | `/state` | snapshot cho UI (poll 2 s) |
| GET | `/events` | SSE sự kiện STT (không có `/api` prefix) |

## Giới hạn & lưu trữ

- Đọc: **2000 từ**/lượt (chốt an toàn 20 000 ký tự); WAV nhanh ≤1000 ký tự.
- Câu hỏi: ≤1000 ký tự; câu trả lời soạn sẵn: ≤2000 từ.
- Audio tạm: `%TEMP%\stt_binh\tts\` (tự xoá khi huỷ/thoát), quota 512 MB.
- Bản đọc lưu sẵn: `data/audio/` (LRU theo quota 512 MB), index trong `faq_audio`.
- CSDL: `data/app.db` (SQLite WAL), schema version 4 (`faq_entries.question_norm`
  + index phục vụ chống trùng trên toàn kho).
- Embedding: `models/embed/model.onnx` + `tokenizer.json` (tải bằng
  `python tools/fetch_embed_model.py`); thiếu model → hashing fallback.
