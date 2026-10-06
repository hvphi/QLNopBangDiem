# Đầu vào và nghiệm thu sản xuất (T-13)

## Quyết định triển khai mới nhất — 05/10/2026

Người dùng yêu cầu hoãn Cloudflare (T-44), dự kiến triển khai trên server VKU sau. Chưa publish website; khi mở lại cần thông tin server, domain/TLS và quyền triển khai. So Khớp trực tiếp API daotao (T-43) cũng đang tạm dừng; So Khớp PDF/local vẫn giữ. Không tự tiếp tục các hạng mục hoãn.

Người dùng xác nhận ngày 04/10/2026: **chưa cần kết nối thật với VKU**. T-13 giữ todo để triển khai trong giai đoạn sau; không thuộc phạm vi hoàn thành local hiện tại. Chưa triển khai hoặc gửi dữ liệu đến hệ thống bên ngoài.

| Đầu vào cần từ VKU | Mục đích |
|---|---|
| API/snapshot UIS được phê duyệt; mapping document ID, lớp, GV, khoa và mẫu xuất | Đối chiếu đúng lớp và tải PDF nguồn; hiện hỗ trợ nhập danh mục bởi admin + UIS_EXPORT_DIR |
| SSO/IdP nếu trường bắt buộc; tài khoản email và phân quyền chính thức | Thay cơ chế tài khoản local do admin cấp bằng xác thực tổ chức |
| Trust anchors VGCA, intermediate chain, CRL/OCSP, policy LTV, certificate fingerprints | Nghiệm thu PDF ký bằng phần mềm thật, thu hồi và ký hai lần |
| Kho trường hoặc credentials object storage với quyền tối thiểu | Đồng bộ/lưu trữ bên ngoài; vault local chưa phải cloud connector |
| TLS domain, máy chủ, secret manager, backup destination, RPO/RTO | Triển khai và diễn tập phục hồi |
| Tải kỳ vọng, tập PDF hợp pháp để benchmark | Xác minh p95 <3s/file và hàng nghìn yêu cầu đồng thời |

## Nghiệm thu

1. Nhập snapshot UIS và xác nhận header/document ID của hai mẫu PDF trong repo. Không sử dụng dữ liệu sinh viên làm fixture công khai.
2. GV thật đăng nhập, xuất PDF UIS, ký bằng VGCA Sign Tool, nộp. TK tải đúng byte, ký bổ sung, nộp lại. Phòng ĐT xác thực lại và lưu trữ.
3. Thử PDF mất chữ ký, sửa điểm sau ký, ký sai chứng thư, chứng thư bị thu hồi/hết hạn, CA chưa tin cậy, mạng OCSP/CRL lỗi và AcroForm bị sửa sau ký.
4. Hết hạn: GV/TK xem/tải, không được nộp/trả/ghi đè. Kho archived bất biến. RBAC theo khoa/chủ sở hữu.
5. Xác nhận replication vào kho trường; phục hồi backup bằng khóa từ secret manager và kiểm tra SHA-256 PDF.
6. Đo latency, throughput và lỗi với tải nghìn người. Nếu vượt giới hạn SQLite/worker, chuyển DB PostgreSQL, đưa PKI vào process worker + queue, dùng kho object mã hóa và idempotency keys. Không công bố SLA trước kết quả benchmark.

T-13 chỉ chuyển in_progress khi người dùng mở lại phạm vi kết nối thật và cung cấp đầu vào tương ứng.

## Bổ sung ngày 05/10/2026 — So Khớp trực tiếp (T-43)

Người dùng đã yêu cầu mở riêng chức năng đọc bảng điểm thật daotao. Cần URL bảng điểm/export và cơ chế phiên đăng nhập cán bộ hoặc API được xác nhận; không gửi mật khẩu/token trong chat. Hiện adapter chỉ đọc PDF local, chức năng upload/so khớp PDF T-41 vẫn hoạt động. T-43 chờ đầu vào truy cập, chưa triển khai trực tiếp; T-13 về SSO/kho/TLS/trust/nghiệm thu tải còn hoãn.

Ngày 06/10/2026: bản local đã hoàn tất thống kê/chi tiết khoa, bộ lọc năm/kỳ và CRUD khoa/tài khoản T-45…T-50. Không thay đổi trạng thái hoãn API daotao hoặc Cloudflare.
