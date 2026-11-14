# Checklist QA giao diện (P4)

Chạy `python run.py`, mở URL mà server in ra. Đánh dấu từng mục sau khi thử.
Mục nào lỗi thì ghi lại màn hình + bước tái hiện.

## 1. Khung ứng dụng

- [ ] Rail trái hiển thị 5 mục: Hỏi đáp, Phiên, Kho hỏi, Chính tả, Cài đặt.
- [ ] Mục đang mở có nền accent và icon sáng; hover các mục còn lại đổi màu.
- [ ] Topbar hiện tiêu đề từng màn hình + `StatusPill` + nút Ctrl+K + bánh răng.
- [ ] Nút "bảng phụ" chỉ hiện ở trang Hỏi đáp và ở màn ≥ 1280px.
- [ ] `Ctrl+K` mở palette; gõ để lọc; `↑`/`↓` đổi lựa chọn; `Enter` điều hướng;
      `Esc` đóng. Bấm ra ngoài cũng đóng.
- [ ] `Ctrl+,` mở/đóng drawer Cài đặt ở mọi màn hình.

## 2. Hỏi đáp (`/`)

- [ ] Trạng thái rỗng: 3 câu hỏi mẫu; bấm một câu → tạo lượt hỏi và câu trả lời.
- [ ] Gõ câu hỏi + `Ctrl+Enter` → gửi; nút `Hỏi` cũng gửi.
- [ ] Sau câu đầu tiên, URL thành `/?session=…`; `F5` vẫn còn hội thoại.
- [ ] Câu trả lời chưa khớp hiện badge "Chưa có đáp án", text fallback, và ghi
      vào "Kho câu hỏi → chưa trả lời".
- [ ] Nút `Đọc` phát audio sau ~2–3 giây; progress chạy; `Dừng đọc` cắt ngay.
- [ ] `Tải WAV` xuất hiện sau khi audio bắt đầu và tải được file mở bằng
      Windows Media Player.
- [ ] Panel phải: "Mic" cập nhật số từ và câu đang nghe; "Câu hỏi khớp" hiện
      điểm/percent; "Đang đọc" hiện tiến độ.
- [ ] Nói một câu hỏi qua mic → sau ~0,7 giây hiện gợi ý "Nghe được câu hỏi";
      bấm `Hỏi` gửi đúng câu đó; `Bỏ qua` ẩn gợi ý.

## 3. Phiên (`/sessions`)

- [ ] Danh sách sắp xếp mới nhất trước, hiện câu hỏi đầu, thời gian, số lượt.
- [ ] Bấm một phiên → mở `/sessions/:id`, hội thoại tải lại đầy đủ.
- [ ] `Xoá` hỏi xác nhận; sau khi xoá dòng biến mất, mở lại URL cũ báo lỗi.
- [ ] `F5` trên `/sessions/abc` trả trang (không 404 server).
- [ ] Empty state có nút "Hỏi câu đầu tiên".

## 4. Kho câu hỏi (`/faq`)

- [ ] Thêm câu hỏi (question + answer + category) → xuất hiện ngay trong danh sách.
- [ ] Sửa câu trả lời → hỏi lại đúng câu đó, giọng đọc trả về nội dung mới.
- [ ] Tắt/Bật một câu: câu tắt không còn được khớp.
- [ ] Xoá hỏi xác nhận; xoá xong hỏi lại → fallback.
- [ ] Tìm theo từ khoá trong câu hỏi/câu trả lời.
- [ ] Nhập CSV 3 cột `question,answer,category` → báo thêm/trùng/lỗi đúng số dòng.
- [ ] Panel phải hiện số câu, đã embedding, ngưỡng khớp, tên model.
- [ ] `Embedding lại` không lỗi; stats cập nhật.
- [ ] `Tổng hợp sẵn` → nút chuyển “Đang tạo…” rồi “Đã lưu bản đọc”; hỏi lại câu đó
      và bấm Đọc: phát ngay (không chờ tổng hợp), vẫn có nút Dừng.
- [ ] Panel “Hoạt động gần đây” hiện các thao tác vừa làm (thêm/sửa/xoá/nhập/reindex).
- [ ] Danh sách "Chưa có đáp án" hiện câu đã hỏi nhưng kho chưa có.
- [ ] Empty state đúng khi kho trống.

## 5. Đọc chính tả (`/dictation`)

- [ ] Nút mũi tên quay về Hỏi đáp; mic, transcript, tạm dừng vẫn hoạt động.
- [ ] `Esc` tạm dừng/tiếp tục; `Ctrl+,` mở cài đặt.

## 6. Cài đặt (`/settings`)

- [ ] Drawer tự mở; đóng được; thay đổi một trường "live" áp dụng ngay.
- [ ] Model / thiết bị micro đổi được và có cảnh báo nếu cần nạp lại.

## 7. Accessibility

- [ ] Chỉ dùng Tab: mọi nút/link/ô nhập đều tới được, focus ring rõ ràng.
- [ ] Đổi route: focus nhảy vào vùng nội dung chính (không kẹt ở rail).
- [ ] Câu trả lời mới được đọc bởi screen reader (`aria-live="polite"`).
- [ ] Mọi nút icon có `aria-label` (bánh răng, Ctrl+K, bảng phụ, quay lại).
- [ ] `prefers-reduced-motion`: caret mic không nhấp nháy.

## 8. Responsive & hiệu năng

- [ ] 1440px: 3 vùng đầy đủ. 1024px: ẩn panel phải. 768px: rail + nội dung.
- [ ] 390px: không tràn ngang; composer dùng được; bảng phiên cuộn dọc.
- [ ] Đọc một câu trả lời dài ~15 phút: RAM tab ổn định, không tăng dần.
- [ ] Đóng tab/route khi đang đọc: AudioContext dừng, server xoá file tạm
      (`%TEMP%\stt_binh\tts` trống sau khi job kết thúc).
- [ ] Không có lỗi đỏ trong DevTools Console khi đi qua 5 màn hình.
