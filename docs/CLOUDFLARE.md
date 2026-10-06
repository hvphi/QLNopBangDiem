# Triển khai Cloudflare — đang chuẩn bị (T-44)

**Đã hoãn theo yêu cầu người dùng ngày 05/10/2026.** Dự kiến triển khai trên server VKU sau; không tiếp tục cấu hình Cloudflare. Chỉ chuẩn bị script/tài liệu, chưa cài cloudflared, tạo tunnel hay publish URL. Website local giữ nguyên.

Ngày 05/10/2026: người dùng yêu cầu triển khai Cloudflare. Chưa có lựa chọn máy origin/tên miền/tài khoản để cấu hình và nghiệm thu URL thật; tài liệu này không ghi nhận đã publish.

## Kiến trúc phù hợp với code hiện tại

Cloudflare Tunnel → origin FastAPI trên máy/VPS → SQLite và vault mã hóa trên đĩa origin. Máy origin phải hoạt động để phục vụ website. Dữ liệu vẫn ở origin, cần backup và bảo quản khóa như OPERATIONS.md. Không dùng Cloudflare Pages để chỉ publish frontend rồi bỏ backend. Python Workers có filesystem tạm; chuyển toàn bộ sang Workers cần thiết kế lại dữ liệu/kho và kiểm chứng thư viện.

## Origin Windows đã chuẩn bị

```powershell
./scripts/start-cloudflare-origin.ps1
```

Chạy port 8001 để không đổi phiên local port 8000, cookie Secure, chỉ tin forwarded headers từ loopback, không bind ra LAN. Đọc khóa đang dùng từ APP_ENCRYPTION_KEY hoặc .local/encryption.key, không tạo khóa mới cho kho hiện có. Default strict cần cấu hình trust/fingerprint/thu hồi theo OPERATIONS.md. Nếu chỉ triển khai bản thử local, chọn rõ `-SignaturePolicy local`; giới hạn CA/thu hồi vẫn hiện trên giao diện, không coi là nghiệm thu PKI production.

## Phần cấu hình sau khi xác nhận đích triển khai

1. Chọn máy hiện tại/VPS hoặc phương án chạy hoàn toàn Cloudflare; cung cấp hostname và quyền đăng nhập Cloudflare. Không gửi token/mật khẩu trong chat.
2. Với Tunnel, cài cloudflared chính thức, tạo tunnel trong tài khoản và published application route tới `http://127.0.0.1:8001`. Giữ Host hostname công khai, HTTPS từ edge, không override Host thành localhost để tránh lỗi Origin/CSRF.
3. Chọn chính sách truy cập phù hợp trước khi publish dữ liệu thực; tạo Access policy nếu triển khai nội bộ. Origin vẫn bắt buộc đăng nhập/role/CSRF.
4. Chạy origin và tunnel; cấu hình chạy nền/khởi động lại trên đúng máy được chọn. Credential tunnel lưu ngoài Git, không đưa vào lệnh hay log công khai.
5. Kiểm tra HTTPS/health/login/cookie Secure, CSRF, quyền/đổi vai trò, upload/tải PDF/người ký/So Khớp; kiểm tra dữ liệu giữ khi restart và backup/restore. Chỉ ghi done sau kiểm chứng URL thật.

Không mở Tunnel vào script start-local (cookie Secure=false). Quick Tunnel là URL tạm cho thử nghiệm; nếu dùng cần chọn riêng, không coi là hostname triển khai lâu dài.

Nguồn chính thức: [Tunnel setup](https://developers.cloudflare.com/tunnel/get-started/), [Tunnel configuration](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/configuration-file/), [Python filesystem](https://developers.cloudflare.com/workers/languages/python/stdlib/).
