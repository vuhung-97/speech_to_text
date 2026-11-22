# STT Trực Tiếp

[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Tailwind](https://img.shields.io/badge/Tailwind-4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Offline](https://img.shields.io/badge/100%25-offline-success)](#)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](#)

**Hỏi đáp tiếng Việt offline theo bộ đề, có đọc đáp án bằng TTS.**

Ứng dụng nhận câu hỏi bằng **giọng nói hoặc bàn phím**, tìm câu trả lời **nguyên văn** trong kho câu hỏi bằng embedding + BM25, rồi đọc đáp án bằng **VieNeu-TTS v3 Turbo**. Không dùng LLM, không gửi dữ liệu ra cloud sau khi cài.

- Backend: **FastAPI + SQLite**
- Giao diện: **React 19 + Tailwind 4**
- STT: **zipformer 30M int8 (sherpa-onnx)**
- TTS: **VieNeu-TTS v3 Turbo (ONNX, CPU)**
- Chạy được trên **Windows / Linux / macOS**, không cần GPU.

---

## Mục lục

- [Tính năng](#tính-năng)
- [Yêu cầu](#yêu-cầu)
- [Cài đặt nhanh](#cài-đặt-nhanh)
- [Sử dụng](#sử-dụng)
- [Micro trên LAN](#micro-trên-lan)
- [Dữ liệu và model](#dữ-liệu-và-model)
- [Kiến trúc](#kiến-trúc)
- [Cấu hình](#cấu-hình)
- [API](#api)
- [Kiểm thử](#kiểm-thử)
- [Khắc phục sự cố](#khắc-phục-sự-cố)
- [Tài liệu](#tài-liệu)

---

## Tính năng

### Hỏi đáp offline

- Hỏi bằng **giọng nói** (micro trình duyệt) hoặc **bàn phím**.
- Câu hỏi được embed bằng `multilingual-e5-small` (ONNX, 384 chiều), so cosine với kho rồi rerank bằng BM25.
- Câu trả lời là **nguyên văn đáp án** của câu hỏi khớp nhất, không sinh văn bản bằng LLM.
- Khi không đủ điểm khớp: hiện fallback, ghi vào danh sách **Chưa có đáp án**, gợi ý 3 câu gần nhất.
- Phiên hội thoại được lưu SQLite, mở lại qua URL hoặc trang **Phiên**.

### Đọc đáp án

- Nút **Đọc** trên từng câu trả lời; khi đang đọc chuyển thành **Đang đọc** kèm thanh tiến độ và `4s/21s`; bấm lần nữa dừng.
- Thanh **Đang đọc** phía trên composer hiển thị nội dung đang phát và nút **Dừng**.
- Chọn giọng preset hoặc giọng clone; đổi giọng tự nạp vào RAM ở nền.
- Thanh **Tốc độ đọc** `0.8–2.0×` (bước `0.2`), áp dụng ở lần đọc kế tiếp.
- Ô **Nội dung thử** + **Test giọng** trong sidebar.
- Tải WAV 48 kHz; đọc dài dùng PCM stream, không tạo Blob toàn bộ trong RAM.

### Quản lý kho câu hỏi

- Bộ đề tách riêng; chọn một bộ hoặc hỏi tất cả.
- Thêm/sửa/xoá/bật/tắt câu hỏi.
- Nhập CSV hoặc đề cương `.docx`.
- Chống trùng exact và cosine; cập nhật bộ đề theo tên tệp.
- Xem thống kê, trạng thái embedding, câu chưa có đáp án và audit gần đây.
- Tạo sẵn bản đọc cho từng câu để lần đọc sau phát ngay.

### Giao diện

- **Sáng/tối**: đổi trên topbar hoặc **Cài đặt → Giao diện**; lưu trên trình duyệt.
- Sidebar phải gồm **Bộ đề**, **Đọc đáp án**, **Mic**.
- Dưới `1024px`: rail đổi thành bottom navigation; công cụ mở trong bottom sheet.
- Trang **Hỏi đáp**, **Phiên**, **Kho hỏi** dùng chung app shell.
- Cài đặt dạng drawer: `Ctrl+,` hoặc bánh răng.

### Riêng tư

- Dữ liệu, phiên và audio lưu trên máy chủ nội bộ.
- Không gọi API cloud sau khi đã có model.
- Không đưa private key/cert hay dữ liệu bộ đề vào frontend bundle.

---

## Yêu cầu

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| Python | 3.11+ | đã test 3.13.5 trên Windows 11 |
| Node.js | 20+ | chỉ cần khi build/dev giao diện (Vite 7) |
| Trình duyệt | Chrome/Edge/Safari hiện đại | micro cần secure context |
| GPU | không cần | model chạy CPU int8 |
| Ổ đĩa | ~vài trăm MB | model STT/TTS/embedding |

- Micro trên `localhost` không cần HTTPS.
- Máy khác trong LAN muốn dùng micro phải mở app qua **HTTPS** — xem [Micro trên LAN](#micro-trên-lan).

---

## Cài đặt nhanh

```powershell
git clone https://github.com/vuhung-97/speech_to_text.git
cd speech_to_text

python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
npm run build
cd ..

python run.py
```

Mở URL server in ra, thường là:

```text
http://127.0.0.1:8765/
```

`frontend/dist/` không commit vào git, nên cần build một lần trước khi chạy. Nếu cổng bận, server tự nhảy sang cổng kế tiếp.

### Chạy cho LAN

```powershell
python run.py --host 0.0.0.0 --port 8765
```

Máy khác mở `http://<IP-LAN>:8765` để hỏi bằng bàn phím và nghe đáp án. Muốn dùng micro trên máy khác, xem [Micro trên LAN](#micro-trên-lan).

### Phát triển giao diện

```powershell
# terminal 1
python run.py --no-browser

# terminal 2
cd frontend
npm install
npm run dev
```

Vite proxy `/api`, `/events` và WebSocket về backend. Khi xong:

```powershell
cd frontend
npm run build
```

### Tham số dòng lệnh

```powershell
python run.py --help
python run.py --mode accurate --cpu-threads 2
python run.py --host 0.0.0.0 --port 8765
python run.py --threshold 0.008 --silence-hang 0.5
python run.py --no-browser --no-tts-preload
```

Các tham số chính: `--host`, `--port`, `--mode`, `--cpu-threads`, `--silence-hang`, `--threshold`, `--decode-interval`, `--settings`, `--no-browser`, `--no-tts-preload`.

---

## Sử dụng

### Hỏi đáp

1. Gõ câu hỏi vào ô dưới cùng rồi `Enter`, hoặc bấm **Hỏi**.
2. Bấm **Nghe**, nói câu hỏi; sau khoảng 2 giây im lặng micro tự đóng, chữ vào ô và **không tự gửi**.
3. Đọc đáp án; bấm **Sao chép** để copy, **Tải WAV** để tải bản đọc.
4. Nếu câu trả lời chưa khớp, bấm một gợi ý để hỏi lại.

### Thanh công cụ bên phải

- **Bộ đề**: chọn bộ câu hỏi dùng để tìm.
- **Đọc đáp án**: chọn chế độ `Chính xác`/`Realtime`, giọng đọc, tốc độ; mở **Thử giọng** để test.
- **Mic**: trạng thái, mức âm lượng, chọn thiết bị.

### Phiên

- Danh sách phiên nhóm theo **Hôm nay / Hôm qua / Trước đó**.
- Tìm theo câu hỏi, mở lại hội thoại, xoá phiên.
- URL `/sessions/:id` mở trực tiếp.

### Kho câu hỏi

- **Thêm câu hỏi** mở drawer nhập câu hỏi/đáp án/danh mục.
- Lọc theo trạng thái, tìm theo từ khoá, sửa, tắt/bật, xoá.
- **Nhập tệp** để nạp CSV hoặc `.docx`.
- **Tổng hợp sẵn** tạo file đọc cho câu trả lời.
- Panel phải hiển thị thống kê, bộ đề, câu chưa có đáp án và hoạt động gần đây.

### Cài đặt

- `Ctrl+,` hoặc bánh răng để mở.
- **Giao diện**: Sáng/Tối.
- **Model & tài nguyên**, **Câu & im lặng**, **Luồng**, preset.
- Thay đổi `live` áp dụng ngay; đổi model/capture sẽ nạp lại nền.

### Phím tắt

| Phím | Tác dụng |
|---|---|
| `Enter` | Gửi câu hỏi |
| `Shift` + `Enter` | Xuống dòng |
| `Ctrl` + `K` | Mở điều hướng nhanh |
| `Ctrl` + `,` | Mở/đóng Cài đặt |
| `Esc` | Đóng drawer/palette |

---

## Micro trên LAN

`getUserMedia` chỉ chạy khi trang là **secure context**:

- `http://localhost` / `http://127.0.0.1`, hoặc
- `https://...`.

Vì vậy:

- **Máy chủ** có thể dùng micro qua `http://127.0.0.1:8765`.
- **Máy khác trong LAN** mở `http://<IP>:8765` vẫn **xem/nghe đáp án** bình thường, nhưng **micro bị chặn**.
- Muốn dùng micro trên máy khác/điện thoại, cần HTTPS và trust root CA trên thiết bị đó.

Hướng dẫn Caddy/mkcert và các lưu ý bảo mật:

- [`docs/TRIEN_KHAI_LAN.md`](docs/TRIEN_KHAI_LAN.md)
- [`docs/ke_hoach_https.md`](docs/ke_hoach_https.md)

WebSocket mic tự dùng `wss://` khi trang là HTTPS. Không cần sửa frontend.

---

## Dữ liệu và model

| Thư mục | Nội dung |
|---|---|
| `models/sherpa/` | model zipformer STT |
| `models/vieneu/` | cache VieNeu-TTS, giọng clone (không commit) |
| `models/embed/` | model embedding ONNX (không commit) |
| `data/` | SQLite, audio lưu sẵn, log (không commit) |
| `settings.json` | cấu hình runtime (không commit) |
| `frontend/dist/` | build UI (không commit) |

Tải model embedding:

```powershell
python tools/fetch_embed_model.py
```

Nếu chưa có model TTS local, lần đọc đầu tiên backend sẽ tải từ Hugging Face; sau đó chạy offline.

---

## Kiến trúc

```text
speech_to_text/
├── backend/                     # FastAPI
│   ├── main.py                  # create_app, lifespan
│   ├── bootstrap.py             # CLI, uvicorn
│   ├── config/                  # settings, fields, paths, constants
│   ├── controllers/             # HTTP/WebSocket endpoints
│   ├── routes/                  # route table
│   ├── domain/                  # luật thuần: QA, FAQ, text, audio
│   ├── ports/                   # interface repository/embedder
│   ├── adapters/                # SQLite, ONNX, importer
│   ├── services/                # QA, FAQ, TTS, STT, jobs
│   └── middleware/              # lỗi, request log
├── frontend/                    # React 19 + Vite + Tailwind
│   └── src/
│       ├── app/                 # shell, router, providers
│       ├── components/          # UI primitives
│       ├── features/            # qa, sessions, faq, settings, tts
│       ├── shared/              # live, mic, playback, tts, ui
│       └── services/            # HTTP client
├── tools/                       # import, fetch model, eval
├── tests/                       # pytest
├── run.py
└── requirements.txt
```

Luồng chính:

```text
Micro trình duyệt
    → WebSocket PCM16
    → STT (zipformer)
    → câu hỏi → embedding + BM25
    → đáp án nguyên văn
    → TTS stream/WAV
    → loa trình duyệt
```

---

## Cấu hình

`settings.json` được tạo tự động. Thứ tự ưu tiên: mặc định → `settings.json` → tham số CLI.

| Nhóm | Thông số |
|---|---|
| Chế độ | `mode` (`accurate` / `realtime`) |
| Model | `model`, `cpu_threads`, field riêng của engine |
| Câu & im lặng | `silence_hang`, `threshold`, `noise_floor_ratio`, `min_speech`, `preroll`, `max_utterance` |
| Luồng | `decode_interval`, `queue_size` |
| Mic | thiết bị chọn trong sidebar (không lưu phía server) |

---

## API

Base: `/api/v1`; prefix `/api` vẫn hoạt động cho tương thích ngược. Swagger UI:

```text
http://127.0.0.1:8765/api/docs
```

Các nhóm chính:

| Nhóm | Endpoint |
|---|---|
| Hỏi đáp | `POST /qa/ask`, `POST /qa/answers/{id}/speech` |
| Phiên | `GET /sessions`, `GET /sessions/{id}`, `DELETE /sessions/{id}` |
| Kho câu hỏi | `GET/POST /faq/entries`, `PATCH/DELETE /faq/entries/{id}`, `POST /faq/import`, `POST /faq/import-docx`, `POST /faq/reindex` |
| Bộ đề | `GET /faq/documents`, `PATCH/DELETE /faq/documents/{id}` |
| TTS | `GET /tts/voices`, `GET /tts/status`, `POST /tts/preload`, `POST /tts/stream`, `GET /tts/sessions/{id}.wav` |
| Vận hành | `GET /health`, `GET /state`, `GET /events` (SSE) |

Chi tiết request/response: [`docs/API.md`](docs/API.md).

---

## Kiểm thử

Backend:

```powershell
python -m pytest -q
```

Frontend:

```powershell
cd frontend
npm test
npm run build
```

Kết quả hiện tại:

- Backend: **208 passed, 1 skipped**
- Frontend: **102 passed / 24 file**
- Build production: thành công

Đo chất lượng tìm kiếm:

```powershell
python tools/eval_matcher.py
```

---

## Khắc phục sự cố

| Hiện tượng | Cách xử lý |
|---|---|
| UI trắng / báo chưa build | `cd frontend && npm install && npm run build` rồi tải lại |
| Cổng bận | Server tự nhảy cổng; hoặc `python run.py --port 9000` |
| Không mở được micro trên máy khác | Dùng HTTPS/secure context; xem `docs/TRIEN_KHAI_LAN.md` |
| Micro bị chặn trên Windows | Settings → Privacy → Microphone → cho phép ứng dụng |
| TTS báo 405 | Server đang chạy bản cũ; tắt và chạy lại `python run.py` |
| TTS báo 409 | Job đọc trước còn bận; dừng đọc, chờ vài giây rồi thử lại |
| Không thấy giọng/model TTS | Kiểm tra `models/vieneu/`, `pip install -r requirements.txt`, kết nối mạng cho lần tải đầu |
| Kho câu hỏi không khớp | Kiểm tra embedding bằng `python tools/fetch_embed_model.py`, `POST /faq/reindex`, xem ngưỡng khớp |
| Nhập `.docx` lỗi | Mỗi câu cần dòng `Câu …` và bảng/đoạn `Đáp án`; file `.doc` cũ phải lưu lại thành `.docx` |
| Câu trả lời quá dài bị từ chối | Giới hạn đọc 2000 từ / 20.000 ký tự; WAV nhanh ≤1000 ký tự |
| Đổi giọng xong không đọc | Chờ “Đang nạp giọng…” kết thúc; thử **Test giọng** trước |

---

## Tài liệu

- [`docs/API.md`](docs/API.md) — API v1, giới hạn, storage.
- [`docs/TRIEN_KHAI_LAN.md`](docs/TRIEN_KHAI_LAN.md) — HTTPS/mic trong LAN.
- [`docs/ke_hoach_https.md`](docs/ke_hoach_https.md) — kế hoạch HTTPS, CA và wizard cài đặt.
- [`docs/qa-ui.md`](docs/qa-ui.md) — checklist QA giao diện.
- [`docs/KE_HOACH_PHAT_TRIEN.md`](docs/KE_HOACH_PHAT_TRIEN.md) — kế hoạch phát triển.

---

## Đóng góp

1. Fork repo, tạo nhánh `feat/...`.
2. Chạy `python -m pytest -q`, `cd frontend && npm test && npm run build`.
3. Mở Pull Request kèm mô tả thay đổi và cách kiểm chứng.

---

## Giấy phép

Repo chưa kèm file `LICENSE`. Nếu công bố theo giấy phép cụ thể, thêm `LICENSE` ở thư mục gốc.
