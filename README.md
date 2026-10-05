# VKU E-Gradebook

Web tiếng Việt cho GV nộp PDF ký số, TK ký bổ sung bên ngoài, Phòng ĐT xác minh/lưu trữ và admin quản lý tài khoản/danh mục/hạn nộp.

Task cards: [docs/tasks/INDEX.md](docs/tasks/INDEX.md). Flow: [docs/tasks/FLOW.md](docs/tasks/FLOW.md). Yêu cầu hiện hành: [PRD 2.0](docs/PRD_gem.md). Báo cáo: [TEST_REPORT](docs/TEST_REPORT.md). Giấy phép bộ đọc PDF: [THIRD_PARTY_NOTICES](docs/THIRD_PARTY_NOTICES.md).

## Chạy local

Python 3.12+, Node 20+, pnpm hoặc npm. Máy hiện tại có Python/Node bundled; `scripts/runner.cjs` tự tìm Python bundled nếu chưa đặt PYTHON.

```powershell
python -m pip install --target .local/packages -r requirements.txt
pnpm install
python scripts/run.py backend.manage --email admin@vku.udn.vn
./scripts/start-local.ps1
```

Ở máy dùng bundled Python, thay `python` bằng đường dẫn `C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe` (PowerShell cần toán tử `&`). CLI hỏi mật khẩu admin, tối thiểu 12 ký tự, không có mật khẩu mặc định. Có thể đặt APP_ADMIN_PASSWORD trong secret môi trường để bootstrap tự động. Đăng nhập tại [localhost:8000](http://localhost:8000).

Admin tạo tài khoản bằng email chính xác @vku.udn.vn, khoa và chứng thư; một email có thể có nhiều vai trò, chọn vai trò khi đăng nhập. Nhập danh mục lớp/GV/năm/kỳ và hạn nộp. PDF cần thông tin môn/lớp hoặc nhóm/năm/kỳ để đối chiếu; không bắt buộc mapping mã tài liệu UIS. Nếu dùng adapter PDF nguồn, đặt UIS_EXPORT_DIR và source_pdf tương đối trong thư mục đó. Danh mục hiện dùng nhập/snapshot; chưa kết nối thật VKU.

Script start-local chọn `APP_SIGNATURE_POLICY=local`: kiểm tra chữ ký mật mã, tính toàn vẹn, metadata và đúng người ký từ fingerprint hoặc email trong chứng thư. Nếu fingerprint trống và email chứng thư khớp tài khoản, tự liên kết sau xác minh thành công trong transaction. Kết quả local ghi rõ chưa xác minh CA/thu hồi trên giao diện và trong report.

Ứng dụng mặc định `APP_SIGNATURE_POLICY=strict` nếu không dùng script local. Trong strict, đặt APP_TRUST_DIR tới thư mục root CA PEM được trường xác nhận và cấu hình fingerprint đúng người; thiếu CA/fingerprint/revocation thì từ chối. Không tự tin cậy root CA nhúng trong file người nộp.

PDF VGCA một số phiên bản có CMS signatureAlgorithm ghi id-ecPublicKey thay cho mã ECDSA. Hệ thống tương thích đúng trường hợp chứng thư EC + SHA-256/384/512 ở bộ nhớ, rồi kiểm tra chữ ký mật mã bằng pyHanko. Byte PDF gốc không đổi. PDF bảng điểm thật, danh sách tài khoản, dữ liệu kho và khóa local được loại khỏi Git; không có dữ liệu/mật khẩu production trong repo.

## Kiểm tra

```powershell
pnpm run typecheck
pnpm test
pnpm run e2e
```

Các scripts tương đương `npm run typecheck`, `npm test`, `npm run e2e` trong checklist template. E2E dùng Playwright bundled hoặc `playwright` cài riêng, với Chromium đã cài; môi trường sạch cần `npm install --save-dev playwright` và `npx playwright install chromium`. Test sinh PKI và PDF có chữ ký thật trong thư mục tạm, dùng CA + CRL thật sinh cho test, không giả kết quả verification. Không chứa dữ liệu sinh viên thật.

## Kiến trúc và luồng

FastAPI + pyHanko, SQLite transaction/optimistic version, AES-GCM vault; giao diện ES modules không cần build, kiểm tra kiểu bằng TypeScript checkJs.

```text
GV: PDF đủ chữ ký GV theo loại → submitted
TK: trả có lý do → rejected → GV nộp lại → submitted
TK: giữ nguyên PDF GV + thêm chữ ký → head_signed
ĐT: xác minh lại → archived (bất biến)
ĐT: trả có lý do → rejected
```

Mỗi phiên bản PDF nằm dưới Năm học/Học kỳ/Khoa/Mã LHP; tên tải xuống theo MaLHP_TenMon_HocKy_Namhoc_TenGiangVien.pdf. Lịch sử phiên bản được giữ, lịch sử xử lý trong audit. Các thao tác trả/lưu trữ cũng tăng version để request cũ thất bại với 409.

Một lớp có nhiều hồ sơ/loại. GV chọn năm/kỳ và nút nộp thành phần/Cuối kỳ của lớp; lớp Đồ án/Đề án/Thực tập/Kiến tập dùng hướng dẫn/Hội đồng. Nút xác định loại, form không hỏi loại/tên/cách nộp. Pending khóa nút, rejected mở nộp lại nếu còn hạn, archived ẩn/Hoàn thành. Nộp lại giữ ID và tăng version. Cuối kỳ lớp thường cần hai GV khác nhau rồi TK; GV thứ hai không cần dạy lớp. Các loại khác giữ một GV + TK; GV kiêm TK được ký bằng cùng chứng thư ở hai bước theo chính sách.

PDF tải xuống của hồ sơ có thêm loại và ID vào tên file để phân biệt tài liệu của cùng lớp. Schema cũ tự migration khi khởi động: giữ IDs, versions, PDF và audit, bỏ giới hạn một hồ sơ/lớp. Sao lưu SQLite trước khi nâng cấp trên dữ liệu thực.

ĐT có dropdown Khoa, người ký PDF trong danh sách và nút Duyệt lưu ngay hồ sơ chờ ĐT. So Khớp cho chọn PDF xuất daotao, ghép cột theo MSSV và hiển thị lệch/thiếu/thừa; không sửa điểm/PDF hay tự duyệt. PDF scan chưa hỗ trợ OCR. Kết quả đối chiếu với file cán bộ chọn, không lấy điểm trực tiếp từ VKU.

[OPERATIONS](docs/OPERATIONS.md) mô tả khóa, HTTPS và backup/restore. [DEPLOYMENT](docs/DEPLOYMENT.md) ghi đầu vào còn thiếu. Bản local chưa nghiệm thu UIS/VGCA/kho trường hay SLA tải sản xuất.
