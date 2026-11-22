# Kế hoạch HTTPS + micro trên LAN

> Trạng thái: **kế hoạch, chưa triển khai**  
> Mục tiêu: máy khác trong LAN (Windows/macOS/Android/iOS) mở app bằng HTTPS, được cấp quyền micro và dùng nút **Nghe** để hỏi.

---

## 1. Vấn đề

`getUserMedia` chỉ hoạt động khi trang là **secure context**:

- `https://...`, hoặc
- `http://localhost`, `http://127.0.0.1`.

Hiện app chạy LAN dạng:

```text
http://192.168.1.20:8765
```

nên máy khác:

- vẫn **đọc đáp án / tải WAV** bình thường;
- nhưng **không mở được micro** để hỏi.

Đây không phải lỗi TTS. Cần HTTPS cho toàn bộ origin.

---

## 2. Giới hạn bắt buộc phải chấp nhận

Web app **không thể tự cài hoặc tự trust root CA** vào hệ điều hành.

Lý do: nếu web có quyền đó, mọi trang độc hại đều có thể cài CA giả. Browser/OS cố tình không cung cấp API này.

Vì vậy:

- Có thể tải CA, hướng dẫn, thậm chí tải script cài.
- **Không thể** có một nút trong web tự chạy `trust CA` im lặng.
- Windows: người dùng phải chạy installer với quyền admin/UAC.
- Android: người dùng phải vào Settings → Install CA certificate.
- iOS: người dùng phải cài profile và bật Certificate Trust Settings.

Nếu muốn **zero-touch trên client**, chỉ có:

1. Domain thật + chứng chỉ công khai (Let’s Encrypt/cert mua), hoặc
2. MDM/Group Policy, hoặc
3. Tunnel HTTPS công khai (Cloudflare Tunnel/ngrok).

Với LAN nội bộ, phương án thực tế là **Caddy local CA + wizard cài một lần trên mỗi thiết bị**.

---

## 3. Kiến trúc đề xuất

### 3.1. Caddy làm HTTPS reverse proxy

Chỉ **máy chủ** chạy Caddy. Máy khác chỉ cần trình duyệt.

```caddyfile
# HTTP: trang setup + tải CA (truy cập được trước khi trust)
http://192.168.1.20:8080 {
    handle /setup* {
        root * C:\stt_binh\lan-setup
        file_server
    }
    handle /root.crt {
        root * C:\stt_binh\lan-setup
        file_server
    }
    handle {
        redir https://192.168.1.20:8443{uri}
    }
}

# HTTPS: app chính
https://192.168.1.20:8443 {
    tls internal
    reverse_proxy 127.0.0.1:8765
}
```

- App vẫn chạy nội bộ:

```powershell
python run.py --host 0.0.0.0 --port 8765
```

- Caddy chịu trách nhiệm TLS và WebSocket upgrade.
- Frontend đã tự dùng `wss://` khi `location.protocol === "https:"`.
- Không cần sửa `useMic` cho WebSocket.

### 3.2. Phương án thay thế: TLS trực tiếp trong `run.py`

Bổ sung:

- `--ssl-certfile`
- `--ssl-keyfile`

và truyền vào `uvicorn.run(...)`.

Dùng `mkcert` hoặc CA nội bộ để tạo cert cho IP LAN. Vẫn phải cài root CA trên client.

**Khuyến nghị:** Caddy, vì tự quản lý cert, WebSocket và HTTP setup page dễ hơn.

---

## 4. Tính năng trong web

### 4.1. Card “Micro trên LAN / HTTPS” trong Cài đặt

Thêm component:

```text
frontend/src/features/settings/HttpsSettings.jsx
frontend/src/features/settings/useHttpsStatus.js
```

Hiển thị 4 trạng thái:

| Trạng thái | Điều kiện | Hành động |
|---|---|---|
| HTTP — micro bị chặn | `!window.isSecureContext` | Tải CA / mở hướng dẫn |
| HTTPS — CA chưa tin cậy | HTTPS nhưng browser cảnh báo / `isSecureContext` false | Hướng dẫn cài CA |
| HTTPS — thiếu quyền mic | secure context, `getUserMedia` bị từ chối | Mở hướng dẫn quyền mic |
| Sẵn sàng | secure context + có `mediaDevices` | Nút kiểm tra mic |

Nội dung card:

- Trạng thái hiện tại.
- Nút **Tải root CA**.
- Fingerprint SHA-256 của CA.
- Hướng dẫn theo thiết bị: Windows / Android / iOS.
- Nút **Tải script cài Windows**.
- Nút **Kiểm tra lại**:
  - reload `window.isSecureContext`
  - kiểm tra `navigator.mediaDevices?.getUserMedia`
- Link **Mở app qua HTTPS**.

### 4.2. Trang setup ngoài app

Route/HTTP page riêng để tránh “chicken-and-egg” (chưa trust CA thì chưa vào được HTTPS):

```text
http://192.168.1.20:8080/setup
```

Nội dung:

- Giải thích ngắn.
- Tải `root.crt`.
- Tab Windows / Android / iOS.
- Nút tải script Windows.
- Link mở `https://192.168.1.20:8443`.

Trang này có thể là HTML tĩnh trong `lan-setup/`, không cần React.

---

## 5. API / file server đề xuất

Chỉ phục vụ **public certificate**, tuyệt đối không phục vụ private key.

| Endpoint | Mục đích |
|---|---|
| `GET /api/v1/lan/status` | `{ https_enabled, ca_available, ca_sha256, setup_url }` |
| `GET /api/v1/lan/ca.crt` | Tải root CA, `application/x-x509-ca-cert` |
| `GET /api/v1/lan/install-windows.ps1` | Script cài CA cho Windows |
| `GET /api/v1/lan/install-windows.bat` | Bản `.bat` dùng `certutil` |
| `GET /api/v1/lan/ios.mobileconfig` | Profile CA cho iOS (nếu triển khai) |
| `GET /api/v1/lan/setup` | Trang hướng dẫn (hoặc static) |

Cấu hình server:

```text
LAN_CA_CERT=C:\stt_binh\lan-setup\root.crt
LAN_CA_SHA256=<fingerprint>
LAN_HTTPS_URL=https://192.168.1.20:8443
```

Không đưa các biến này vào frontend bundle nếu không cần; ưu tiên endpoint status.

---

## 6. Script cài Windows

### `.bat` tối giản

```bat
@echo off
net session >nul 2>&1
if %errorLevel% neq 0 (
  echo Vui long chay bang quyen Administrator.
  pause
  exit /b 1
)
certutil -addstore -f Root "%~dp0root.crt"
if %errorLevel% equ 0 (
  echo Da cai root CA. Mo lai Chrome/Edge.
) else (
  echo Cai that bai.
)
pause
```

### PowerShell

```powershell
# Chạy PowerShell as Administrator
Import-Certificate -FilePath .\root.crt -CertStoreLocation Cert:\LocalMachine\Root
```

Yêu cầu:

- Script hiển thị fingerprint để người dùng đối chiếu.
- Không tải private key.
- Không tự chạy silent.
- Windows SmartScreen/UAC sẽ hỏi; đây là hành vi mong đợi.

---

## 7. Hướng dẫn client

### Windows
1. Tải `root.crt` hoặc `install-windows.bat`.
2. Chạy installer bằng **Run as administrator** (hoặc double-click `.crt` → Install Certificate → Local Machine → Trusted Root).
3. Đóng hoàn toàn Chrome/Edge rồi mở lại.
4. Mở `https://192.168.1.20:8443`.

### Android
1. Tải `root.crt`.
2. Settings → Security → Encryption & credentials → Install a certificate → **CA certificate**.
3. Chọn file, xác nhận cảnh báo.
4. Mở lại Chrome.
5. Kiểm tra `window.isSecureContext === true`.

### iOS/iPadOS
1. Tải `root.crt` / `.mobileconfig`.
2. Settings → Profile Downloaded → Install.
3. Settings → General → About → **Certificate Trust Settings** → bật full trust.
4. Mở Safari/Chrome, kiểm tra HTTPS.

### Firefox
Firefox dùng kho riêng:
Settings → Privacy & Security → Certificates → Authorities → Import.

---

## 8. Bảo mật

- Chỉ serve **root.crt**; không bao giờ serve `root.key`.
- CA private key chỉ nằm trên máy chủ, quyền hạn chế.
- Chỉ mở cổng HTTPS/setup trong LAN; không NAT ra Internet.
- Fingerprint hiển thị trên web và trong script.
- Cảnh báo người dùng chỉ cài CA của server tin cậy.
- Khi đổi máy chủ/IP, cần tạo lại cert và cài lại CA trên client.
- Cân nhắc thời hạn CA/cert và quy trình rotate.
- Không dùng mẹo “ignore certificate” cho production; mic vẫn có thể bị chặn.

---

## 9. Các phase triển khai

### Phase 1 — Caddy + CA export
- [ ] Thêm `Caddyfile` mẫu.
- [ ] Script `tools/export_caddy_ca.ps1` copy root CA từ Caddy data dir sang `lan-setup/root.crt`.
- [ ] Tạo `lan-setup/index.html` với hướng dẫn và download.
- [ ] Kiểm tra HTTPS + `wss` trên một máy khác.

### Phase 2 — Backend
- [ ] Thêm cấu hình `LAN_CA_CERT`, `LAN_HTTPS_URL`.
- [ ] Endpoint status/ca/installer.
- [ ] Không serve private key.
- [ ] Test content-type và tải file.

### Phase 3 — Frontend wizard
- [ ] `HttpsSettings` trong `SettingsForm`.
- [ ] `useHttpsStatus`.
- [ ] Hiển thị trạng thái + fingerprint + hướng dẫn.
- [ ] Nút “Kiểm tra lại” và “Mở HTTPS”.
- [ ] Không chặn các phần cài đặt khác khi HTTP.

### Phase 4 — Script/UX
- [ ] `install-windows.bat`/`.ps1`.
- [ ] `.mobileconfig` cho iOS (optional).
- [ ] Hướng dẫn Android/iOS trong setup page.
- [ ] Copy/QR link setup (optional).

### Phase 5 — Test
- [ ] Windows client.
- [ ] Android Chrome.
- [ ] iPhone Safari.
- [ ] Firefox (nếu hỗ trợ).
- [ ] Mic xin quyền, nói thử, transcript xuất hiện.
- [ ] TTS vẫn đọc bình thường.
- [ ] Dừng đọc → đọc lại được.
- [ ] `window.isSecureContext === true`.
- [ ] Network có `wss://.../ws/audio` status 101.

---

## 10. Tiêu chí hoàn thành

- [ ] Từ máy khác trong LAN mở được `https://<ip>:8443` không cảnh báo cert.
- [ ] Trang Cài đặt hiển thị đúng trạng thái HTTPS/CA/mic.
- [ ] Tải CA từ web được, fingerprint đúng.
- [ ] Windows cài CA bằng script/UAC; Android/iOS có hướng dẫn rõ.
- [ ] Bấm **Nghe** trên điện thoại → xin quyền micro → nhận transcript.
- [ ] WebSocket dùng `wss`, không bị mixed content.
- [ ] TTS, tải WAV, đổi giọng, đọc lại vẫn hoạt động.
- [ ] Không có private key trong repo/web.
- [ ] Docs cập nhật: `README`, `docs/TRIEN_KHAI_LAN.md`, `docs/ke_hoach_https.md`.

---

## 11. Không nằm trong phạm vi

- Tự động trust CA không cần người dùng (không khả thi trên browser/OS thông thường).
- Cài CA trên thiết bị qua web mà không có bước xác nhận của OS.
- Public CA cho IP LAN thuần (Let’s Encrypt không cấp cho IP nội bộ).
- Hỗ trợ mọi browser cũ không có `getUserMedia`/AudioWorklet.

---

## 12. Quyết định cần chốt

1. Dùng **Caddy** (khuyến nghị) hay TLS trực tiếp trong `run.py`.
2. Có cần iOS `.mobileconfig` tự động không, hay chỉ hướng dẫn tải `.crt`.
3. Cổng HTTPS: `443` hay `8443` (tránh xung đột/quyền admin).
4. Có cần trang setup riêng ở HTTP `8080` hay chỉ dùng app HTTP 8765.
5. Có cần QR code trên trang setup cho điện thoại không.

---

## 13. Rollback

- Tính năng chỉ đọc cấu hình/env; không sửa DB.
- Nếu lỗi HTTPS, tắt Caddy và quay lại `http://IP:8765`.
- Không ảnh hưởng TTS/API hiện có.
- File CA/cert nằm ngoài git, có thể xoá và tạo lại.
