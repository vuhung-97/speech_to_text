# Chạy trong LAN (mic trình duyệt)

Mic được mở **trong trình duyệt** của từng người dùng, nên trang phải được phục
vụ qua HTTPS khi mở từ thiết bị khác (`getUserMedia` chỉ chạy trên `localhost`
hoặc HTTPS). Server STT vẫn chỉ chạy một lần trên máy chủ.

## 1. Chuẩn bị

- Máy chủ: `python run.py --host 0.0.0.0 --port 8765` (mở firewall cho cổng này).
- Biết IP LAN của máy chủ: `ipconfig` → IPv4, ví dụ `192.168.1.20`.
- KHÔNG cần cài gì trên điện thoại/máy khác — chỉ cần trình duyệt.

## 2. Cách A — Caddy (khuyến nghị, tự HTTPS)

1. Tải Caddy: https://caddyserver.com/download (Windows .zip).
2. Tạo `Caddyfile` cạnh `caddy.exe`:

```
192.168.1.20 {
    reverse_proxy 127.0.0.1:8765
}
```

3. Chạy `caddy run`. Caddy tự tạo CA cục bộ và cấp chứng chỉ cho IP.
4. Trên từng thiết bị, mở `https://192.168.1.20` và **tin cậy chứng chỉ**
   (Caddy in link tải root CA; trên Android/iOS cài trong mục chứng chỉ).
5. WebSocket `/ws/audio` đi qua cùng reverse proxy (Caddy tự nâng cấp).

## 3. Cách B — uvicorn TLS + mkcert

```powershell
# 1) tạo chứng chỉ cho IP LAN (mkcert: https://github.com/FiloSottile/mkcert)
mkcert -install
mkcert 192.168.1.20 localhost 127.0.0.1

# 2) chạy server với TLS
python run.py --host 0.0.0.0 --port 8765 `
  --ssl-certfile 192.168.1.20+2.pem --ssl-keyfile 192.168.1.20+2-key.pem
```

`run.py` hiện chưa nhận cờ TLS — thêm tạm bằng biến môi trường hoặc chạy trực
tiếp `uvicorn backend.main:app --ssl-...` sau khi khởi động app (xem ghi chú
trong `run.py`).

Cài root CA của mkcert trên điện thoại (file `rootCA.pem`) để trình duyệt chấp
nhận.

## 4. Kiểm tra

1. Mở `https://<ip>` trên điện thoại → trang Hỏi đáp hiện bình thường.
2. Panel phải → chọn đúng mic → bấm **Nghe** → trình duyệt hỏi quyền → cho phép.
3. Nói một câu hỏi → sau 2 giây im lặng, chữ xuất hiện trong ô soạn.
4. Trong lúc loa đọc câu trả lời, nói vào mic: không có chữ mới (mic đã đóng).

## 5. Sự cố thường gặp

| Hiện tượng | Nguyên nhân | Cách xử lý |
|---|---|---|
| Bấm Nghe báo "bạn chưa cho phép dùng micro" | Quyền mic bị chặn | Biểu tượng khoá trên thanh địa chỉ → cho phép micro, tải lại trang |
| Không thấy thiết bị mic | Trang chạy HTTP (không phải localhost) | Dùng HTTPS theo mục 2 hoặc 3 |
| WS báo mất kết nối | Reverse proxy không nâng cấp WebSocket | Caddy tự làm; nginx cần `proxy_set_header Upgrade` |
| Nhận dạng chậm khi nhiều người nói | Model dùng chung CPU | Giảm số client đồng thời; tăng `cpu_threads` trong Cài đặt |
| Điện thoại ngủ → mất mic | Hệ điều hành khoá trình duyệt | Giữ màn hình sáng khi đang hỏi |
