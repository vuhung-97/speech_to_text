# Kế hoạch phát triển — Trợ lý hỏi đáp giọng nói offline

> Trạng thái: đã chốt, dùng làm kim chỉ nam triển khai.
> Cập nhật: 2026-11-13.

## 1. Sản phẩm

Người dùng nói câu hỏi → hệ thống nhận dạng (STT, đã có) → khớp câu hỏi với kho
câu hỏi–câu trả lời soạn sẵn bằng embedding → trả lời nguyên văn → đọc bằng giọng
nói tự nhiên khi người dùng bấm Đọc.

Không dùng LLM sinh câu trả lời, không RAG trên tài liệu thô: nguồn tri thức là
các cặp (câu hỏi, câu trả lời) do người vận hành soạn, nên câu trả lời luôn đúng
nguyên văn và không có ảo giác.

## 2. Quyết định đã khóa

| Hạng mục | Quyết định |
|---|---|
| Nguồn tri thức | Kho câu hỏi–câu trả lời soạn sẵn (FAQ) |
| Embedding | ONNX + `multilingual-e5-small` (384 chiều), vendor tại `models/embed/` |
| Runtime embedding | `onnxruntime` + `tokenizers` (đã có sẵn) — không thêm package |
| Ngưỡng khớp | cosine ≥ **0.88** (đo trên e5-small: nội bộ ≥0.89, ngoài phạm vi ≤0.87); dưới ngưỡng → fallback + top-3 gợi ý |
| Giới hạn đọc | 2000 từ/lượt; chốt an toàn 20 000 ký tự |
| Lưu audio | PCM16 spill-to-disk, quota 512 MB, dọn session cũ khi khởi động |
| Tự động đọc | TẮT mặc định (bấm nút mới đọc), có công tắc trong Cài đặt |
| Mic | **TẮT mặc định**; chỉ mở khi bấm `Nghe`; đóng thiết bị khi đọc (half-duplex) |
| Frontend deps | chỉ thêm `react-router-dom`; test UI bằng checklist tay |
| Thứ tự | P0 → P6 |
| Tenant | `local`, nhưng mọi bảng/query đã scope `tenant_id` |

## 3. Kiến trúc

```
backend/
├─ domain/        # thuần Python: models, normalize, detector, limits, pcm
├─ ports/         # Protocol: FaqMatcher, FaqRepository, Embedder,
│                 #           SpeechSynthesizer, SessionRepository
├─ adapters/      # onnx_e5, sqlite_faq, vieneu, sqlite
├─ services/      # qa_service, faq_service, tts_service, audio/temp_store
├─ controllers/   # validate + gọi service (không domain logic)
└─ config/        # paths, settings
```

```
frontend/src/
├─ app/           App.jsx, router.jsx, providers.jsx
├─ features/      dictation, qa, tts, faq, sessions, settings
├─ components/ui/ primitives + CommandPalette
├─ services/      http.js, errors.js, sse.js
└─ styles/        tokens.css
```

Quy tắc: component không chứa business logic; không `fetch` ngoài `services/`;
`domain/` không import FastAPI; RAG/embedding nằm sau port.

## 4. Dữ liệu (SQLite, WAL, `PRAGMA user_version`)

```sql
sessions(id PK, tenant_id, title, created_at, updated_at)
turns(id PK, session_id, tenant_id, question, created_at, state)
answers(id PK, turn_id, tenant_id, text, entry_id NULL, score REAL,
        voice, audio_path, seconds, status, created_at)
faq_entries(id PK, tenant_id, question, answer, category, active,
            embedding BLOB, embed_model, embed_version, created_at, updated_at)
faq_queries(id PK, tenant_id, session_id, question, question_norm,
            matched_entry_id NULL, score REAL, answered INT, created_at)
faq_audio(entry_id, voice, sample_rate, path, seconds, bytes, created_at,
          PRIMARY KEY(entry_id, voice))
```

Index: `(tenant_id, created_at)`, `(tenant_id, category)`. Audio nằm ở
`%TEMP%\stt_binh\tts\<id>\`, DB chỉ lưu đường dẫn.

## 5. API

| Method | Path | Việc |
|---|---|---|
| POST | `/api/v1/qa/ask` | `{question, session_id?}` → `{answer_id, text, matched, candidates, status}` |
| POST | `/api/v1/qa/detect` | nhận diện câu hỏi từ transcript / gộp mảnh câu |
| CRUD | `/api/v1/faq/entries[/{id}]` | quản trị kho câu hỏi |
| POST | `/api/v1/faq/import` | CSV `question,answer,category` → báo cáo thêm/trùng/lỗi |
| POST | `/api/v1/faq/reindex` | embed lại entry thiếu/đổi version |
| GET | `/api/v1/faq/unanswered` | worklist câu hỏi chưa trả lời |
| GET | `/api/v1/faq/stats` | số entry, model, dim, ngưỡng, embed_note |
| GET | `/api/v1/sessions[/{id}]` | lịch sử hội thoại |
| POST | `/api/v1/qa/answers/{id}/speech` | trả `cached` (URL) hoặc `stream` (text) |
| GET | `/api/v1/audit` | nhật ký thao tác nhạy cảm |
| giữ | `/api/tts/stream`, `/api/state`, `/events` | tương thích ngược |

## 6. Giai đoạn

| # | Nội dung | Ngày | Định nghĩa hoàn thành |
|---|---|---|---|
| P0 | Khung domain/ports/adapters; `http.js`, `errors.js`; tách Live/Settings provider; mount `/api/v1`; catch-all SPA; router 5 route; `tokens.css` | 2 | refresh deep link 200; `fetch` chỉ trong `services/`; test cũ xanh |
| P1 | `pcm.py`, `TempAudioStore`, `synthesize_stream`, endpoint TTS, quota, cleanup | 4 | 2000 từ: RAM phẳng ±30 MB; Range 206; huỷ xoá temp |
| P2 | `pcmStream.js`, `pcmPlayer.js`, `PlayerBar`, `DocumentReader` | 3 | nghe < 2 s; Dừng < 200 ms; RAM tab phẳng |
| P3 | `QuestionDetector`, `QaService.ask` + `NullFaqMatcher`, sessions repo | 2.5 | nói câu hỏi → turn + trả lời thử + log unanswered |
| P4 | App shell 3 vùng, Thread/TurnCard/AnswerCard, Composer, Kho câu hỏi, command palette, 4 trạng thái | 6 | deep link, a11y ≥ 95, keyboard đầy đủ |
| P5 | `OnnxE5Embedder`, `SqliteFaqMatcher`, import/dedupe, tune threshold, prerender cache | 4 | 50 paraphrase top-1 ≥ 95%; tenant isolation |
| P6 | Log request-id/tenant, error envelope, audit, quota, docs, build dist | 2 | test + build xanh, có rollback |

Tổng ~23,5 ngày công.

## 7. Test

- Backend: `test_tts_pcm`, `test_tts_temp_store`, `test_tts_stream`, `test_tts_http`,
  `test_question_detector`, `test_qa_service`, `test_sessions_repo`,
  `test_faq_match`, `test_faq_import`, `test_faq_audio_cache`.
- Frontend: `docs/qa-ui.md` (routing, 4 trạng thái, focus, bàn phím, breakpoint,
  reduced-motion, rò rỉ AudioContext).
- Hiệu năng: đo RAM tiến trình khi đọc 15 phút; p95 `ask()` < 50 ms với 10k entry.

## 8. Rủi ro

| Rủi ro | Đối sách |
|---|---|
| Ngưỡng khớp sai | `faq_queries` ghi mọi lần khớp, script tune trên log thật, UI hiện điểm |
| Câu hỏi mơ hồ | ghép ngữ cảnh turn trước; dưới ngưỡng → hỏi lại + top-3 |
| Model ONNX thiếu | vendor `models/embed/`; fallback TF-IDF char n-gram |
| Đổi embedder | `embed_version` chặn match, buộc reindex |
| CPU yếu | prebuffer 3 s, hiện RTF, chọn giọng nhẹ, cache audio |
| Trùng câu hỏi | cảnh báo cosine ≥ 0.97 khi import |

## 9. Tiến độ triển khai

| Giai đoạn | Trạng thái | Ghi chú |
|---|---|---|
| P0 Nền kiến trúc | ✅ xong | `domain/`, `ports/`, `adapters/`, `/api/v1`, catch-all SPA, `react-router-dom`, tách Live/Settings/Toast provider, `http.js`, `tokens.css` |
| P1 Lõi audio | ✅ xong | `pcm.py`, `TempAudioStore`, `synthesize_stream`, 5 endpoint, quota 512 MB, dọn temp khi khởi động/thoát |
| P2 Player | ✅ xong | `pcmStream.js`, `pcmPlayer.js` (prebuffer 2,5 s), `useSpeechPlayer`, TtsDrawer 2 chế độ |
| P3 Q&A + sessions | ✅ xong | `QaService.ask`, SQLite (sessions/turns/answers/faq_queries, WAL, tenant scope), `/api/v1/qa/ask`, `/qa/detect`, `/qa/unanswered`, `/sessions` CRUD; `NullFaqMatcher` trả fallback + log |
| P4 Giao diện SaaS | ✅ xong | App shell rail+topbar+panel, `/` hỏi đáp, `/sessions(/:id)`, `/faq` (worklist), `/dictation`, `/settings`; command palette Ctrl+K; player đọc trong AnswerCard; `docs/qa-ui.md` |
| P5 FAQ embedding | ✅ xong | `OnnxE5Embedder` (multilingual-e5-small, 384d, quantized 118 MB tại `models/embed/`), `HashingEmbedder` fallback, `SqliteFaqRepository` + `SqliteFaqMatcher` (ma trận RAM, lazy embed, cache theo signature), CRUD + import CSV + chống trùng 0.97 + reindex + stats, `/faq` admin UI |
| P6 Gia cố | ✅ xong | `X-Request-ID` + log structured, audit log (schema v3) + `/audit`, prerender + cache bản đọc (`faq_audio`, LRU 512 MB) + `/qa/answers/{id}/speech`, panel hoạt động gần đây, `docs/API.md` |

Đo thực tế trên máy phát triển (VieNeu v3 Turbo, ONNX CPU):

| Chỉ số | Kết quả |
|---|---|
| Block audio từ `infer_stream` | ~0,92 s/block, 43 block cho 39,4 s audio |
| RTF ổn định (bỏ lần nạp model) | **0,55** (nhanh hơn thời gian thực) |
| RTF toàn phiên (gồm nạp model) | 0,71 |
| Block đầu tiên | 6,6 s (gồm nạp model lần đầu) |
| RAM tăng thêm khi stream | dưới 12 MB cho 200 s audio (test `tracemalloc`) |
| Đĩa | 96 KB/s → ~345 MB/giờ; quota mặc định 512 MB |

Kiểm thử P3 (109 test): `test_sessions_repo` (vòng đời, cách ly tenant, log),
`test_qa_service` (fallback, matched, near-miss, giới hạn, dùng lại phiên),
`test_qa_http` (envelope, detect, sessions CRUD, tenant header, worklist),
`test_question_detector` (marker giữa câu).

Kiểm thử P5 (148 test): `test_faq_repo` (schema v2, CRUD, embedding, signature),
`test_faq_matcher` (lazy embed, ngưỡng, xếp hạng, cache invalidation, tenant),
`test_faq_service` (validate, trùng, update, CSV, reindex/stats),
`test_faq_http` (CRUD, import multipart, ask khớp, tenant), `test_hashing_embedder`,
và `test_faq_onnx` (chỉ chạy khi đã tải model) chốt chất lượng thật.

### Hiệu chỉnh ngưỡng P5 (đo thật, e5-small quantized)

| Nhóm | Điểm cosine cao nhất |
|---|---|
| Trong phạm vi (10 câu diễn đạt lại) | 0,894 – 0,943 |
| Ngoài phạm vi (12 câu lạc đề) | 0,790 – 0,872 ("Mấy giờ rồi" cao nhất) |

→ Chọn **0,88**: ưu tiên không trả lời sai; câu diễn đạt quá xa sẽ rơi vào
fallback + gợi ý thay vì trả lời nhầm. `near_threshold = 0,88` (tắt dải "trả lời
kèm cảnh báo") vì e5-small có điểm nền cao với câu hỏi ngắn.
