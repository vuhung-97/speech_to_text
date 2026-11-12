# STT Trực Tiếp

> Nhận dạng tiếng Việt **offline, realtime trên CPU** — không cần GPU, không cần internet
> sau khi cài. Lõi là **zipformer 30M int8 (sherpa-onnx)**, backend **FastAPI**,
> giao diện **React + Tailwind**, kèm cơ chế **plugin để cắm model AI khác**.

Đo trên file bản tin đọc liên tục 168 giây (CPU 8 luồng, 2 thread cho model):

| | Kết quả |
| --- | --- |
| Tốc độ | decode 168s audio trong **8.3s** (RTF 0.049 — nhanh hơn realtime ~20 lần) |
| Độ chính xác | **99% khớp** với bản đối chiếu (chỉ 6/604 từ lệch) |
| Hallucination | không có (transducer không tự sinh văn bản trên nhiễu) |
| Thu âm | 99–100% audio thực, 0 frame bị rơi |

---

## Tính năng

- **Hai chế độ**: `accurate` (chốt từng câu, chất lượng cao) và `realtime` (chữ chạy theo từng từ).
- **Thu âm bằng callback** (PortAudio) + tự fallback sang burst; hiển thị `fr/s`, `coverage`, `dropped` để biết audio có bị rơi không.
- **VAD chống khoá**: noise-floor chỉ học từ frame yên tĩnh, ngưỡng ≤ 30% đỉnh gần đây, hysteresis, giữ trạng thái khi tạm dừng.
- **Bảng cài đặt 11 thông số** ngay trên web (schema động theo engine đang chọn).
- **Replay file audio** (wav/mp3/m4a…) với đúng cấu hình đang dùng → A/B thông số trên cùng một file.
- **Preset** lưu/nạp bộ thông số (localStorage).
- **API + docs tự động** tại `/api/docs`, sự kiện realtime qua **SSE**.
- **Plugin model**: thêm model mới bằng 1 file, không sửa code lõi.

## Kiến trúc

```
backend/                          # FastAPI
  main.py                         # entry: uvicorn + lifespan
  config/                         # paths, constants, schema settings (động)
  controllers/                    # HTTP mỏng: health, state/SSE, settings, devices, samples, session
  routes/                         # bảng route duy nhất
  middleware/                     # mọi lỗi → JSON {ok, error}
  models/                         # DTO: CaptureStats, ReplayResult…
  services/
    capture_service.py            # InputProber · Resampler · MicStream
    segmentation_service.py       # EnergyGate · UtteranceSegmenter · LocalAgreement
    transcription_service.py      # pipeline (2 mode, reload nền, hàng đợi câu)
    replay_service.py · event_service.py · device_service.py
    engines/                      # ASREngine (contract) + registry + plugins
      base.py
      zipformer_engine.py
  utils/                          # priority (ưu tiên thread), errors

frontend/                         # React 19 + Tailwind 4 (Vite)
  public/
  src/
    pages/ components/ services/ context/ utils/
  dist/                           # bản build sẵn (backend phục vụ thư mục này)
```

Luồng xử lý:

```
mic → callback capture → resample 16kHz mono → VAD/segmenter → decode worker (zipformer)
                                                     ↓
                                    EventBus → SSE → React UI
```

## Bắt đầu nhanh

Yêu cầu: **Python 3.11+**, micro. (Node 18+ chỉ cần nếu bạn sửa giao diện.)

```powershell
git clone https://github.com/vuhung-97/speech_to_text.git
cd speech_to_text

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python run.py
```

Trình duyệt tự mở `http://127.0.0.1:8765/` (cổng bận thì tự nhảy cổng kế tiếp).
`Ctrl+C` ở terminal để dừng.

> Repo đã kèm model zipformer trong `models/sherpa/` và bản build frontend trong
> `frontend/dist/`, nên chỉ cần cài Python là chạy được.
> Nếu sửa giao diện: `cd frontend && npm install && npm run build`.

### Chế độ phát triển giao diện

```powershell
python run.py --no-browser          # terminal 1
cd frontend
npm install
npm run dev                         # terminal 2 → http://127.0.0.1:5173
```

Vite proxy `/api` và `/events` về backend.

### Tham số dòng lệnh hữu ích

```powershell
python run.py --list-devices
python run.py --mode accurate --cpu-threads 2
python run.py --device 1 --silence-hang 0.5 --threshold 0.008
python run.py --port 9000 --no-browser
```

## Sử dụng

1. Nói tiếng Việt; ở chế độ `realtime` chữ hiện dần (chữ mờ = bản nháp đang chờ xác nhận).
2. Nghỉ ~0.6s để chốt câu.
3. **Esc** tạm dừng / tiếp tục · **Ctrl+,** mở cài đặt · **Sao chép** lấy toàn bộ nội dung.
4. Tab **Thử nghiệm trên file**: kéo–thả file audio vào `samples/` rồi chạy thử để so thông số.

## Cài đặt (⚙)

| Nhóm | Thông số | Ghi chú |
| --- | --- | --- |
| Chế độ | `mode` | `accurate` / `realtime` |
| Model & micro | `model`, `cpu_threads`, `device` + field riêng của engine | đổi model hoặc thread → nạp lại nền, không chặn UI |
| Câu & micro | `silence_hang`, `threshold`, `noise_floor_ratio`, `min_speech`, `preroll`, `max_utterance` | áp dụng ngay |
| Luồng | `decode_interval` (realtime), `queue_size` | |

Giá trị được lưu vào `settings.json` (file này **không** commit — mỗi máy tự sinh).
Ưu tiên: mặc định ← `settings.json` ← tham số CLI (chỉ hiệu lực phiên chạy).

## Cắm thêm model AI

Hợp đồng nằm ở `backend/services/engines/base.py`:

```python
class ASREngine(ABC):
    key: str        # id dùng trong settings
    label: str      # tên hiển thị trong UI

    def __init__(self, values: dict): ...
    def transcribe(self, audio) -> tuple[str, float]: ...   # (text, RTF)
    def describe(self) -> dict: ...

    @classmethod
    def fields(cls) -> tuple[Field, ...]: ...               # thông số riêng (UI tự render)
    @classmethod
    def is_available(cls) -> tuple[bool, str]: ...          # (ready, lý do)
```

Thêm model = **3 bước**:

1. Tạo `backend/services/engines/<ten>_engine.py` (sherpa-onnx có sẵn loader cho
   Zipformer, SenseVoice, Moonshine, Paraformer, FireRedASR, Whisper…).
2. Khai báo `key`, `label`, viết `transcribe()`; khai báo `fields()` nếu model có
   tham số riêng; kiểm tra package/file trong `is_available()`.
3. Khởi động lại → model xuất hiện trong **⚙ → Model**.

Plugin thiếu package/model sẽ hiện cảnh báo kèm lý do, app vẫn chạy engine cũ.
Ví dụ tối thiểu:

```python
from ...config.fields import Field
from .base import ASREngine

class EchoEngine(ASREngine):
    key = "echo"
    label = "Echo (demo)"

    @classmethod
    def fields(cls):
        return (Field("gain", "engine", "Gain", "float", 1.0, minimum=0, maximum=2),)

    def transcribe(self, audio):
        return "xin chào", 0.01
```

## API

Swagger UI: `http://127.0.0.1:8765/api/docs`

| Endpoint | Ý nghĩa |
| --- | --- |
| `GET /api/health` | engine đang dùng |
| `GET /api/state` | snapshot (status, engine, capture, queue, settings, warnings) |
| `GET /events` | SSE: `status` · `level` · `partial` · `final` · `queue` · `engine` · `warning` |
| `GET/POST /api/settings` | schema + values / partial update |
| `POST /api/settings/reset` | khôi phục mặc định |
| `GET /api/devices` | danh sách micro |
| `GET/POST /api/samples` | liệt kê / upload (multipart `file`) |
| `POST /api/replay` | decode file trong `samples/` bằng cấu hình hiện tại |
| `POST /api/pause`, `POST /api/clear` | tạm dừng/tiếp tục, xoá transcript |

## Hiệu năng (tham khảo)

Máy test: CPU 8 luồng, model chạy 2 thread, int8.

| Cấu hình | Decode 168s audio | RTF | Ghi chú |
| --- | --- | --- | --- |
| **zipformer-vi-30M** | **8.3s** | **0.049** | mặc định, khớp 99% |
| whisper small (CT2) | ~53s | 0.31 | sai tên riêng, hay lặp |
| PhoWhisper small (CT2) | 48–85s | 0.29–0.50 | khớp 98%, không dấu câu |

## Test

```powershell
python tests/test_settings.py     # schema động, clamp, effects, persistence
python tests/test_streaming.py    # pipeline, engine registry, replay, FastAPI + SSE
python smoke_test.py              # zipformer + micro thật
```

## Khắc phục sự cố

| Hiện tượng | Cách xử lý |
| --- | --- |
| Không mở được micro | Windows → Settings → Privacy → Microphone: bật "Let desktop apps access"; hoặc `python run.py --list-devices` rồi `--device <index>` |
| UI trắng / báo "frontend chưa build" | `cd frontend && npm install && npm run build` |
| Cổng bận | app tự nhảy cổng; hoặc `--port 9000` |
| Chữ bị rơi, coverage thấp | tăng `threshold` nếu phòng ồn; xem `dropped` trong ⚙; thử đổi `--device` |
| Nạp model lỗi | kiểm tra `models/sherpa/sherpa-onnx-zipformer-vi-30M-int8-2026-02-09/` có `encoder.int8.onnx` |

## Ghi chú

- Model zipformer: [k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) release
  `sherpa-onnx-zipformer-vi-30M-int8-2026-02-09`.
- Repo chưa kèm file license — thêm `LICENSE` nếu bạn muốn công bố theo giấy phép cụ thể.
- File audio trong `samples/` không được commit (mỗi người tự thêm file của mình).
