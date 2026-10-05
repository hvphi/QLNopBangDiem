# Vận hành và khôi phục

## Khóa và kho

`APP_ENCRYPTION_KEY` là 32 byte biểu diễn bằng 64 ký tự hex. Giữ khóa ở secret manager ngoài kho backup; mất khóa đồng nghĩa không thể giải mã. Script local tạo khóa tại `.local/encryption.key`, chỉ dùng máy phát triển. Dữ liệu tại `APP_DATA_DIR` (mặc định runtime) gồm SQLite và vault AES-GCM. Payload encrypted gắn AAD với đường dẫn nên không thể tráo file giữa hồ sơ.

`APP_COOKIE_SECURE=true` mặc định; production phục vụ HTTPS qua reverse proxy. Local chỉ bind 127.0.0.1 và script local đặt false. Không mở local HTTP ra Internet. Proxy giữ Host/Origin nhất quán, giới hạn body 21 MB, timeout > thời gian xác minh; chỉ tin proxy được cấu hình cụ thể.

## PKI

Đặt trust roots đã xác minh nguồn gốc trong `APP_TRUST_DIR/*.pem`. Đây là trust anchors do quản trị hệ thống quản lý, không phải file người dùng tải lên. Chứng thư trung gian phải có trong PDF/chuỗi do cơ quan cấp cung cấp; đảm bảo kết nối CRL/OCSP. Fingerprint là SHA-256 của chứng thư DER, liên kết đúng từng tài khoản. Không bật soft-fail khi kiểm tra thu hồi.

Validation dùng pyHanko, yêu cầu revocation evidence. Policy diff chỉ cho thêm trường chữ ký và dữ liệu PKI, loại bỏ generic form filling. Tham khảo chính thức: [pyHanko validation](https://docs.pyhanko.eu/en/latest/api-docs/pyhanko.sign.validation.html). Chữ ký hết hạn, thiếu LTV, không truy cập được CRL/OCSP sẽ bị từ chối; cần policy LTV được trường phê duyệt trước khi mở rộng chấp nhận chữ ký lịch sử.

Đoạn trên áp dụng `APP_SIGNATURE_POLICY=strict` (mặc định của app). Theo yêu cầu sửa lỗi local, start-local chọn `local`: không truy cập CA/CRL/OCSP, vẫn bắt buộc `intact` và `valid`, coverage/diff hợp lệ, đúng email chứng thư hoặc fingerprint. Local không chứng nhận CA, thời hạn/thu hồi hay policy LTV; report ghi `trust_verified=false`, `revocation_verified=false`. Giao diện hiển thị phạm vi này. Không dùng policy local cho nghiệm thu sản xuất.

Nếu chưa liên kết fingerprint, local so email chứng thư từ subject/SAN với email tài khoản. Chỉ sau xác minh thành công mới lưu fingerprint trong transaction; nộp lỗi không liên kết. Lần sau fingerprint phải khớp. Chứng thư không có email hoặc có email khác: admin liên kết fingerprint đúng người theo quy trình của trường. Không tự gắn chứng thư bất kỳ chỉ vì người dùng đã đăng nhập.

Một số PDF VGCA trong repo ghi OID `1.2.840.10045.2.1` (id-ecPublicKey) vào CMS SignerInfo.signatureAlgorithm. Chỉ khi khóa chứng thư là EC và digest SHA-256/384/512, validator chuyển OID trong đối tượng CMS ở bộ nhớ sang ECDSA tương ứng trước khi kiểm tra mật mã. Không đổi signature value, signed attributes, byte range, chứng thư hay PDF trên đĩa. Không áp dụng chuyển đổi này cho khóa RSA/thuật toán khác.

## Backup định kỳ

Chạy `scripts/backup.ps1 -Destination <ổ dự phòng hoặc thư mục kho trường đã mount>` hằng ngày bằng Windows Task Scheduler (tài khoản dịch vụ có quyền đọc dữ liệu và ghi đích). Hoặc đặt `APP_BACKUP_DIR` để ứng dụng tự snapshot mỗi `APP_BACKUP_INTERVAL` giây (mặc định 86400). Theo dõi lỗi job; không tự xóa backup cũ. Backup dùng SQLite online dưới khóa ghi, copy vault, loại sessions và xuất manifest SHA-256. Backup chứa thông tin tài khoản/metadata, do đó thư mục đích phải dùng mã hóa ổ đĩa và ACL của trường.

`python scripts/run.py backend.operations backup runtime D:/Backups/snapshot-YYYYMMDD` yêu cầu đích mới bên ngoài runtime.

Phục hồi vào thư mục mới: `python scripts/run.py backend.operations restore D:/Backups/snapshot-YYYYMMDD runtime-restored`. Kiểm tra manifest, SQLite integrity và đủ các PDF. Dừng dịch vụ, đặt `APP_DATA_DIR=runtime-restored`, dùng đúng khóa cũ và trust roots (không đi theo backup), khởi động lại và chạy smoke test. Không ghi đè kho đang chạy. Cần diễn tập restore định kỳ trên dữ liệu trường và đo RPO/RTO trước nghiệm thu.

## Giới hạn hiện tại

SQLite một nút, 4 slot xác minh PDF, 20 MB/file và 100 trang/file. Khi hết slot, API trả 503 để client thử lại. Xác minh tối đa 15 giây cho mạng PKI; đây là timeout, không phải chứng minh SLA <3 giây. Cần benchmark p95, hàng đợi, PostgreSQL và kho object dùng chung trước triển khai tải hàng nghìn người. Parser PDF vẫn cần resource isolation ở production (container/process worker) để chống file gây tải CPU/bộ nhớ.
