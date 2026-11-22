# Checklist QA giao diện (P4)

Chạy `python run.py`, mở URL mà server in ra. Đánh dấu từng mục sau khi thử.
Mục nào lỗi thì ghi lại màn hình + bước tái hiện.

## 1. Khung ứng dụng

- [ ] Rail trái hiển thị 3 mục: Hỏi đáp, Phiên, Kho hỏi.
- [ ] Mục đang mở có nền accent, icon sáng và vạch accent bên trái; hover mục còn lại đổi màu.
- [ ] Topbar hiện tiêu đề từng màn hình + `StatusPill` + nút đổi sáng/tối + Ctrl+K + bánh răng.
- [ ] Nút "bảng phụ" chỉ hiện ở trang Hỏi đáp/Kho hỏi và ở màn ≥ 1024px; sidebar phải có 3 khối: Bộ đề, Đọc đáp án (chế độ + giọng + tốc độ + thử giọng), Mic.
- [ ] Dưới 1024px: rail đổi thành bottom navigation 4 mục; mục **Công cụ** mở bottom sheet chứa đúng 3 khối trên.
- [ ] Bottom sheet đóng bằng `Esc`, nút X hoặc bấm nền; focus quay về nút Công cụ.
- [ ] `Ctrl+K` mở palette; gõ để lọc; `↑`/`↓` đổi lựa chọn; `Enter` điều hướng;
      `Esc` đóng. Bấm ra ngoài cũng đóng.
- [ ] `Ctrl+,` mở/đóng drawer Cài đặt ở mọi màn hình.

## 2. Hỏi đáp (`/`)

- [ ] Trạng thái rỗng: 3 câu hỏi mẫu; bấm một câu → tạo lượt hỏi và câu trả lời.
- [ ] Mở app: `StatusPill` hiện **"Sẵn sàng"**; chưa có thiết bị mic nào bị mở.
- [ ] Ô nhập tự focus; gõ câu hỏi + `Enter` → gửi; nút `Hỏi` cũng gửi.
- [ ] Ba phần tử `Nghe` / ô nhập / `Hỏi` cao bằng nhau (44px), thẳng hàng, không
      nhô lệch; mobile 375px không tràn ngang.
- [ ] Card Mic trong sidebar phải có select thiết bị **của trình duyệt**, tách khỏi
      card Bộ đề; chọn mic khác và bấm `Nghe` → trình duyệt hỏi quyền (lần đầu) →
      đèn mic đúng thiết bị sáng.
- [ ] Nút **Sao chép** copy nguyên văn đáp án; nút **Tải WAV** chỉ hiện khi có audio stream.
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
- [ ] Nút `Đọc` phát audio; khi đang đọc, nút chuyển thành khối **“Đang đọc”**
      kèm thanh tiến độ và thời gian `4s/21s`; bấm lần nữa dừng ngay, thanh thời
      gian biến mất và nút trở lại **“Đọc”**.
- [ ] Thanh **“Đang đọc”** phía trên composer hiện nội dung đáp án đang đọc,
      progress, thời gian `4s/21s` và nút `Dừng`; biến mất khi đọc xong/dừng.
- [ ] `Tải WAV` xuất hiện sau khi audio bắt đầu và tải được file mở bằng
      Windows Media Player.
- [ ] Sidebar phải có 3 khối: **Bộ đề**, **Đọc đáp án**, **Mic** — mỗi khối cách nhau
      khoảng 12px, không dính nhau; phần **Thử giọng** nằm trong disclosure, mặc định đóng.
- [ ] Câu hỏi của user chỉ hiện nội dung + giờ, **không** hiện nhãn “gõ tay”/“giọng nói”.
- [ ] Badge khớp/percent và tiến độ đọc nằm trong AnswerCard; thanh “Đang đọc”
      là nơi duy nhất nhận diện nội dung đang phát.

## 3. Phiên (`/sessions`)

- [ ] Danh sách sắp xếp mới nhất trước, nhóm theo **Hôm nay / Hôm qua / Trước đó**.
- [ ] Ô tìm lọc theo câu hỏi/ID; số phiên cập nhật theo bộ lọc.
- [ ] Bấm một phiên → mở `/sessions/:id`, hội thoại tải lại đầy đủ.
- [ ] Nút xoá hỏi xác nhận; sau khi xoá dòng biến mất, mở lại URL cũ báo lỗi.
- [ ] `F5` trên `/sessions/abc` trả trang (không 404 server).
- [ ] Empty state có nút "Hỏi câu đầu tiên"; khi tìm không thấy có thông báo riêng.

## 4. Kho câu hỏi (`/faq`)

- [ ] **Thêm câu hỏi** mở drawer, không chiếm chỗ danh sách; lưu xong drawer đóng và câu mới xuất hiện.
- [ ] Sửa câu trả lời mở lại drawer với dữ liệu cũ; lưu → danh sách cập nhật.
- [ ] Bộ lọc **Tất cả / Đang bật / Đang tắt** lọc đúng danh sách.
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

## 5. Cài đặt (drawer, bánh răng / `Ctrl+,`)

- [ ] Không còn route `/settings`; bánh răng mở drawer ở mọi màn hình.
- [ ] Drawer đóng được bằng `Esc`, nút đóng, hoặc bấm ra ngoài; focus trả về nút mở.
- [ ] Drawer có mục **Giao diện** (Sáng/Tối) ở đầu; chọn đồng bộ ngay với nút topbar.
- [ ] Drawer chỉ còn engine/VAD/stream/preset; **không** còn chế độ, giọng đọc,
      hay “Thử nghiệm trên file”.
- [ ] Thay đổi một trường "live" áp dụng ngay; trường engine/capture có nút `Áp dụng`.
- [ ] Không còn đoạn hướng dẫn dài về micro.

## 6. Chế độ, Giọng đọc & Giao diện

- [ ] Khối **Đọc đáp án** có segmented `Chính xác` / `Realtime`; bấm đổi ngay, trạng thái
      `aria-pressed` đúng.
- [ ] Select **Giọng đọc** liệt kê preset + giọng clone.
- [ ] Thanh **Tốc độ đọc** chạy 0.8–2.0×, bước 0.2; đổi tốc độ không làm thay
      đổi audio đang phát, chỉ áp dụng ở lần bấm đọc/test kế tiếp.
- [ ] Đổi giọng → hiện “Đang nạp giọng vào RAM…”, sau đó biến mất; không chặn thao tác.
- [ ] Đổi giọng khi đang đọc đáp án → audio cũ dừng, giọng mới được nạp.
- [ ] Ô **Nội dung thử** + nút **Test giọng** đọc bằng đúng giọng đang chọn;
      nút chuyển `Dừng` khi đang phát.
- [ ] Lỗi nạp giọng hiện message + nút `Thử lại`.
- [ ] Mở DevTools → Network: đổi giọng có `POST /tts/preload`, sau đó poll
      `GET /tts/status` đến khi `preloading=false`.
- [ ] Nút topbar đổi Sáng ↔ Tối ngay; reload vẫn giữ theme; không nháy sai theme.
- [ ] Native select/option, scrollbar và focus ring đúng màu ở cả hai theme.
- [ ] Chữ/UI đạt tương phản AA ở cả hai theme; nền sáng dùng ivory, không phải trắng tinh.

## 7. Accessibility

- [ ] Chỉ dùng Tab: mọi nút/link/ô nhập đều tới được, focus ring rõ ràng.
- [ ] Đổi route: focus nhảy vào vùng nội dung chính (không kẹt ở rail).
- [ ] Câu trả lời mới được đọc bởi screen reader (`aria-live="polite"`).
- [ ] Mọi nút icon có `aria-label` (bánh răng, Ctrl+K, bảng phụ, quay lại).
- [ ] `prefers-reduced-motion`: caret mic không nhấp nháy.

## 8. Responsive & hiệu năng

- [ ] 1440px: đủ rail + nội dung + panel phải. 1024px: panel phải vẫn hiện; dưới 1024px ẩn panel.
- [ ] 768px: bottom navigation + nội dung; mở Công cụ bằng bottom sheet.
- [ ] 390px: không tràn ngang; composer và bottom nav dùng được; sheet cuộn dọc.
- [ ] Đọc một câu trả lời dài ~15 phút: RAM tab ổn định, không tăng dần.
- [ ] Đóng tab/route khi đang đọc: AudioContext dừng, server xoá file tạm
      (`%TEMP%\stt_binh\tts` trống sau khi job kết thúc).
- [ ] Không có lỗi đỏ trong DevTools Console khi đi qua 5 màn hình.
