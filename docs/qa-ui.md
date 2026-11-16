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
- [ ] Mở app: `StatusPill` hiện **"Sẵn sàng"**; chưa có thiết bị mic nào bị mở.
- [ ] Ô nhập tự focus; gõ câu hỏi + `Enter` → gửi; `Shift+Enter` → xuống dòng
      (không gửi); nút `Hỏi` cũng gửi.
- [ ] Panel Mic có select thiết bị **của trình duyệt**; chọn mic khác và bấm
      `Nghe` → trình duyệt hỏi quyền (lần đầu) → đèn mic đúng thiết bị sáng.
- [ ] Bấm `Nghe` → mic mở, nói một câu → im 2 giây → mic tự đóng và câu vừa nói
      xuất hiện trong ô, **không tự gửi**.
- [ ] Trong 2 giây sau khi chốt câu, nói tiếp → mic vẫn mở, chữ nối thêm; hết
      2 giây mới đóng.
- [ ] Ô đã có chữ rồi bấm `Nghe` → chữ mới nối sau, chữ cũ còn nguyên.
- [ ] Bấm `Dừng` khi đang nghe → mic đóng ngay, chữ đã chốt (hoặc bản nháp) vào ô.
- [ ] Nghe lần hai không dính câu của lần một.
- [ ] Đang nghe mà bấm `Đọc` → mic đóng trước, sau đó mới phát; ngược lại đang
      đọc mà bấm `Nghe` → tiếng đọc dừng ngay.
- [ ] Trong lúc loa đọc, nói vào mic → không có transcript mới (track đã dừng).
- [ ] Mở trang từ **máy thứ hai trong LAN qua HTTPS** → mic của máy đó hoạt động;
      mic laptop chạy server không sáng.
- [ ] Chọn đúng micro trong panel; nếu thanh level phẳng khi nói, thử micro khác
      (jack combo “Microphone with Headphone (Intel…)” chỉ hoạt động khi cắm tai nghe).
- [ ] DevTools → Network: để yên 5 phút **không** thấy `GET /api/state` mỗi 2 s
      (chỉ ~1 lần/60 s watchdog); ẩn tab thì không có request.
- [ ] Đổi cài đặt khi đang nghe → mic dừng và báo “cài đặt vừa thay đổi — bấm Nghe lại”.
- [ ] Mở phiên thứ 9 (nếu thử) → báo máy chủ đang bận (giới hạn 8 phiên).
- [ ] Sau câu đầu tiên, URL thành `/?session=…`; `F5` vẫn còn hội thoại.
- [ ] Câu trả lời chưa khớp hiện badge "Chưa có đáp án", text fallback, và ghi
      vào "Kho câu hỏi → chưa trả lời".
- [ ] Nút `Đọc` phát audio sau ~2–3 giây; progress chạy; `Dừng đọc` cắt ngay.
- [ ] `Tải WAV` xuất hiện sau khi audio bắt đầu và tải được file mở bằng
      Windows Media Player.
- [ ] Panel phải: "Mic" hiện Mic tắt / Đang nghe / Đang đọc và số từ đang nói;
      "Câu hỏi khớp" hiện điểm/percent; "Đang đọc" hiện tiến độ.

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

- [ ] Nút mũi tên quay về Hỏi đáp; mic trình duyệt, transcript, `Bắt đầu nghe` hoạt động.
- [ ] `Esc` bật/tắt mic; `Ctrl+,` mở cài đặt.
- [ ] Trang này không mở mic của server (đèn mic laptop không sáng khi dùng trình duyệt khác).

## 6. Cài đặt (`/settings`)

- [ ] Drawer tự mở; đóng được; thay đổi một trường "live" áp dụng ngay.
- [ ] Không còn ô chọn “Micro” của server; có ghi chú mic nằm ở trình duyệt.
- [ ] Model đổi được và có cảnh báo nếu cần nạp lại.

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
