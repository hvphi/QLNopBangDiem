# Báo cáo kiểm tra local

## Hồ sơ cá nhân và đổi mật khẩu (T-53, 06/10/2026)

- Mọi role có Hồ sơ cá nhân, xem email/vai trò/khoa và sửa tên; tên đồng bộ cùng email, không cho tự đổi email/role/khoa/fingerprint. Đổi mật khẩu yêu cầu mật khẩu cũ, tối thiểu 12 ký tự mới khác cũ, xác nhận trùng; đồng bộ các role cùng email, hủy mọi session của email, xóa cookie và yêu cầu đăng nhập lại. CSRF/whitelist, hash scrypt, transaction, audit không secrets, giới hạn 5 lần thử/5 phút.
- 11 tests profile/admin catalog PASS; sau thêm kiểm tra mật khẩu cũ bị từ chối, 6 profile tests bản cuối PASS. Bao gồm 4 role sửa tên, extra field/tên trống, anonymous/CSRF, sai/yếu/trùng/xác nhận lệch/throttle, nhiều role cùng email, revoke toàn bộ phiên, giữ email khác và audit không secrets.
- Typecheck/Python syntax/53 cards DAG/diff check PASS. E2E PASS flow bảng điểm hiện có và hồ sơ: sửa tên/hiển thị sidebar, mobile không tràn, mật khẩu sai giữ form, đổi đúng về login, đăng nhập bằng mật khẩu mới vai trò ĐT cùng email và tên đồng bộ. Lần đầu sửa selector biểu tượng; lần hai chạm login throttle của toàn bộ suite, dùng route rotate-session test-only đã có cho bước chuyển role để dành real login cho kiểm tra password mới. Không nới throttle production.
- profile-mobile.png đã xem: hai form xếp dọc rõ trên mobile. Website restart port 8000, health OK và trang chủ 200. Không sửa dữ liệu live hoặc password thực trong kiểm thử; mọi mutation test ở database tạm. PRD 2.2 cập nhật T-53.

## Kiểm kê giấy phép thư viện (T-52, 06/10/2026)

- `scripts/run.py scripts.audit_licenses` kiểm kê 52 gói Python trong cây phụ thuộc hoạt động của requirements trên Windows/Python 3.12.14 và 3 công cụ Node (TypeScript, Playwright/core). Không thiếu distribution, mọi gói có license file; giữ 90 file license/notice nguyên byte cùng metadata và SHA-256 trong docs/dependency-licenses.json. Xác minh độc lập 90/90 hash PASS.
- Báo cáo LICENSE_AUDIT.md và THIRD_PARTY_NOTICES mở rộng ngoài luồng PDF T-41. Đọc metadata và notices native; đối chiếu nguồn chính thức. Ghi rõ lxml thông báo iconv LGPL-2.1, tài nguyên test/schema có license riêng/thiếu license cần kiểm tra phạm vi phân phối; certifi MPL-2.0; lựa chọn FreeType FTL; browser/OS/native binary chưa phân tích đầy đủ. Không kết luận toàn bộ bundle permissive hoặc đã tuân thủ đầy đủ chỉ từ metadata.
- pypdf requirements 6.1.1 nhưng import 6.10.0; reportlab requirements 4.4.4 nhưng import 4.4.9. Ghi font Arial của fixture không phải font nguồn mở và không được tự đóng gói file font. Không cài/đổi dependency, sửa chức năng, dữ liệu live, restart hoặc push trong lần audit.
- Kiểm tra Python syntax/template/dependency DAG và git diff --check (code/docs; notices giữ nguyên whitespace upstream); không chạy lại E2E cho thay đổi kiểm kê/tài liệu.

## Rà soát tài liệu và bản đưa lên GitHub (T-51, 06/10/2026)

- PRD 2.1 mô tả local đến T-50; cập nhật phạm vi, yêu cầu thống kê/chi tiết/bộ lọc/CRUD và truy vết T-43…T-51. CRUD nằm mục Quản trị §3.6; card T-50 trỏ đúng mục. Card/index/DEPLOYMENT ghi rõ API so khớp và Cloudflare do người dùng tạm dừng, không coi đã triển khai.
- Typecheck/Python syntax/51 cards/dependency DAG và git diff --check đạt. Giữ bằng chứng T-50: 69 system/catalog/statistics tests, 9 tests bản cuối và E2E đã đạt; không chạy lại toàn bộ test chức năng cho thay đổi chỉ tài liệu.
- Danh sách commit gồm code, test, script và tài liệu liên quan. Không đưa Acc, runtime, .local, báo cáo riêng, Excel/PDF/khóa hoặc Demo.docx lên GitHub. Không triển khai Cloudflare/API hay sửa dữ liệu live trong lần rà soát này.

## CRUD khoa và tài khoản trường (T-50, 06/10/2026)

- Admin có bảng/form CRUD Khoa/Đơn vị, sửa tên/thống kê với mã ổn định, xóa đơn vị chưa dùng. Combobox Khoa ở tạo/sửa tài khoản và tạo lớp lấy từ DB. Tài khoản có tìm kiếm, Sửa/Xóa ngoài Lưu fingerprint/trạng thái hiện có; sửa tên/email/role/khoa/password tùy chọn, cùng email nhiều role. UI xác nhận đối tượng xóa. Tên thống kê lấy danh mục động; đơn vị VKU/ĐT/Chưa phân khoa không là dòng thống kê mặc định.
- 69 tests hệ thống/statistics/catalog PASS; sau bổ sung đơn vị mặc định, 9 catalog/statistics tests PASS. Bao gồm migration giữ dữ liệu/không tái seed mục xóa, CRUD, duplicate, multi-role, password trống giữ nguyên/đổi password, session invalidation, không lộ password, RBAC/CSRF, tự khóa/xóa/mất quyền admin bị chặn, tài khoản có dữ liệu/audit hoặc khoa đang dùng cấm xóa, role/khoa có phân công cấm thay đổi.
- Typecheck/syntax/50 cards DAG đạt. E2E PASS thêm/sửa/xóa khoa, combobox thêm option động, cấp/sửa tên/khoa/xóa tài khoản chưa dùng, xác nhận xóa; các flow ký/trả/resubmit/duyệt/So Khớp/hạn/mobile cũ đạt. Ảnh admin.png kiểm tra có bảng Khoa, combobox, danh sách/search/nút sửa/xóa.
- Sao lưu trước migration tại .local/pre-admin-catalog-20261006.sqlite3. Website restart 8000; so sánh đầy đủ rows trước/sau giữ nguyên 211 users, 1.618 courses, 4 submissions, 6 versions; chỉ thêm danh mục 8 đơn vị, trong đó 5 thống kê. Không xóa dữ liệu live hay thay PDF/mật khẩu.

## Combo năm học/học kỳ thống kê (T-49, 06/10/2026)

- Thêm Năm học/Học kỳ ngay trên bảng thống kê ĐT, năm từ courses và Tất cả, kỳ 1/2/hè/Tất cả. Đổi chọn tự cập nhật, reset trang 1, đồng bộ với bộ lọc danh sách; bấm Lọc phía dưới đồng bộ ngược. Nút Chi tiết giữ cùng năm/kỳ. Chặn response cũ ghi đè khi đổi chọn nhanh.
- Typecheck/syntax/49 cards/DAG PASS. E2E PASS danh mục năm, đổi 2024–2025/kỳ 2 có 0/1 và dialog cùng kỳ; đổi hè đủ 5 dòng 0/0; quay Tất cả 1/7; đồng bộ ngược bộ lọc năm. Các flow hiện có còn đạt. Ảnh department-period-filters.png kiểm tra hai combo, bố cục và kỳ rỗng đạt.
- Chỉ frontend/docs/test thay đổi; không sửa API hay dữ liệu. Website port 8000 health OK, frontend phục vụ trực tiếp file mới; người dùng tải lại trang để nhận thay đổi.

## Chi tiết lớp/GV theo khoa (T-48, 06/10/2026)

- Mỗi khoa có nút Chi tiết trong thống kê ĐT. Dialog lấy dữ liệu live theo khoa được bấm và năm/kỳ đang lọc: họ tên/email GV, số đã nộp/tổng lớp, mở danh sách tên/mã lớp và năm/kỳ/đã nộp/chưa nộp; tìm GV/email/tên/mã lớp; trạng thái rỗng rõ ràng. Không dùng file Markdown làm dữ liệu cố định, không sửa phân công/hồ sơ/PDF.
- API chỉ training. 4 statistics tests PASS gồm 2 tests bổ sung details: khoa/năm/kỳ, một lớp nhiều hồ sơ/rejected tính một lần, rỗng/đơn vị lạ, whitelist trường trả về, 401/403 các vai trò khác. Typecheck/Python syntax/48 cards/DAG PASS.
- E2E PASS 5 nút, mở/đóng dialog, tìm OLD01, hiển thị lớp chưa nộp, tìm không có kết quả, Tổ Cơ bản rỗng, năm 2024–2025 chỉ có lớp tương ứng. Ảnh department-details.png đã kiểm tra: bảng GV và danh sách lớp trong dialog rõ, nút Chi tiết từng khoa hiện đầy đủ. Các luồng nộp/ký/trả/nộp lại/duyệt/So Khớp/admin/hạn/mobile còn đạt.
- Website restart port 8000, API details live từng đơn vị khớp tổng thống kê: CNTT 79 GV/789 lớp (4 đã nộp), KTMT 22/286, KTS 53/300, AIDS 2/26, CB 40/216. Bộ đếm dùng dữ liệu live có thể thay đổi khi admin thêm lớp; không đồng bộ lại hay xóa lớp trong task này.

## Đồng bộ lớp theo khoa từ thời khóa biểu/Excel (T-47, 06/10/2026)

- HTTP đọc trang công khai daotao thành công 200, 1.662 dòng, dropdown nguồn HK1 năm 2026–2027. Đối chiếu tên GV với sheet Tai khoan VKU, mã/tên khoa từ Danh muc Khoa trong Acc/DS_tai_khoan_VKU_cap_nhat.xlsx. Không xuất hay thay mật khẩu. Gom các buổi cùng GV/lớp: CNTT 789, KTMT 286, KTS 300, AIDS 26, CB 216, tổng 1.617. 28 lớp Bank Agribank có khoa chưa xác định được báo cáo riêng; 9 tên lớp có nhiều người phụ trách giữ riêng theo GV, lưu báo cáo để đối chiếu. Các mã lịch trình nguồn là mã buổi/phân công, không dùng làm số lớp.
- 8 tests PASS (6 importer + 2 statistics): rowspan, sai kỳ nguồn, tên thiếu/trùng/bỏ dấu, khoa chưa rõ, tài khoản không khớp, nhiều vai trò cùng email, bỏ qua cột mật khẩu, gom buổi/idempotence, bảo toàn hồ sơ và rollback khi quyền thay đổi. Không sửa UI; API live trả 200, đủ 5 khoa, 4/1.617 khớp SQL độc lập.
- Sao lưu SQLite online trước cập nhật tại .local/timetable-departments-20261006.backup.sqlite3. Đối chiếu toàn bộ dữ liệu trước/sau: 211 users, 4 submissions, 6 versions giữ nguyên; thêm 1.602 lớp, cập nhật lịch 5 lớp. Không xóa lớp/hồ sơ, không sửa PDF. Nguồn HTML và báo cáo JSON lưu .local, báo cáo đọc được trong docs/reports, không đưa dữ liệu riêng vào Git. API so khớp điểm và triển khai vẫn hoãn.

## Đủ 4 khoa và Tổ Cơ bản (T-46, 06/10/2026)

- Danh mục theo mã tài khoản: CNTT/Khoa Khoa học máy tính, KTMT/Khoa Kỹ thuật máy tính và Điện tử, KTS/Khoa Kinh tế số và Thương mại điện tử, AIDS/Khoa Trí tuệ nhân tạo và Khoa học dữ liệu, CB/Tổ Cơ bản. API thống kê ghép count từ lớp với danh mục, hiện 0/0 cho đơn vị không có lớp; giữ đơn vị ngoài danh mục nếu có để không mất tổng. Dropdown ĐT có đủ 5 tên và Tất cả khoa. Không sửa mã/phân công lớp/GV.
- 2 API tests PASS đủ 5 đơn vị/0-0/filter kỳ rỗng/filter CB/đơn vị lạ và quy tắc count/RBAC cũ. Typecheck/Python syntax/46 cards/DAG PASS. E2E PASS 5 dòng thống kê và 6 options, Tổ Cơ bản 0/0, lọc khoa/năm và các flow hiện có; ảnh department-statistics.png kiểm tra đạt.
- Website restart; API training live trả đủ CNTT/KTMT/KTS/AIDS/CB và giữ tổng 4/16. PRD/cards cập nhật. Tên tham chiếu nguồn VKU: https://vku.udn.vn/vi/co-cau-to-chuc/khoa-khoa-hoc-may-tinh/; https://daotao.vku.udn.vn/chuong-trinh-dao-tao; lịch VKU tháng 09/2026 ghi Khoa Trí tuệ nhân tạo và Khoa học dữ liệu: https://lichtuan.vku.udn.vn/index.php?module=LichTuan. Mã đơn vị lấy từ danh sách tài khoản đã được người dùng cung cấp.

## Thống kê nộp bảng điểm theo khoa (T-45, 06/10/2026)

- Dashboard training có bảng Tên Khoa — Lớp đã nộp/Tổng số lớp học phần và tổng cộng phía trên danh sách hồ sơ. Theo năm/kỳ/khoa; độc lập pagination, từ khóa, state và loại hồ sơ. EXISTS đếm mỗi lớp có ít nhất một hồ sơ một lần, kể cả rejected; không yêu cầu đủ hai loại. Denominator lấy toàn bộ courses trong cùng phạm vi, khoa chưa nộp hiện 0.
- 2 API tests PASS: nhiều loại/hồ sơ một lớp không trùng, rejected, khoa 0, filter năm/kỳ/khoa/rỗng, filters danh sách không ảnh hưởng tổng, training only/401. Chạy với thư mục tạm riêng và tắt pytest cache vì thư mục pytest cũ bị khóa ACL Windows; không đổi ACL hay xóa thư mục cũ.
- Typecheck/Python syntax/45 cards + DAG PASS. E2E PASS: CNTT 1/7 trong dataset, filter 2024-2025 hiện 0/1 dù danh sách hồ sơ rỗng; các luồng upload/ký/trả/resubmit/duyệt/archive/So Khớp/admin/hạn/mobile còn đạt. Ảnh department-statistics.png kiểm tra hiển thị đúng, không lẫn số hồ sơ với số lớp.
- Website local restart; health và API thống kê training live đối chiếu bằng COUNT DISTINCT độc lập trong DB PASS. Không thay bảng điểm, trạng thái hoặc danh mục live. API daotao/Cloudflare vẫn hoãn theo yêu cầu.

## So Khớp PDF xuất daotao (T-41, 05/10/2026)

- Giao diện chọn PDF nguồn, tự ghép cột cùng tên với PDF đã ký và cho chỉnh ghép cột. Đổi file xóa kết quả/cột cũ và yêu cầu xác nhận lại đúng môn/lớp/kỳ/loại. Hiển thị điểm từ PDF đã ký và PDF nguồn trên từng dòng lệch; PDF nguồn không cần chữ ký. API vẫn hỗ trợ CSV/XLSX để tương thích T-40.
- Dùng lại pdfplumber 0.11.9/pdfminer.six 20251230 có giấy phép MIT; không thêm thư viện. Metadata/giấy phép gói và nguồn chính thức đã kiểm tra, lưu nguyên văn vào docs/licenses, gồm Pillow và pypdfium2/PDFium binary Windows; hướng dẫn giữ thông báo khi phân phối tại docs/THIRD_PARTY_NOTICES.md.
- 14 parser/API tests PASS: PDF nguồn không ký, khớp/lệch giữa hai PDF; PDF hỏng, sai định dạng, không có bảng bị từ chối; bảng thành phần/cuối kỳ/hướng dẫn thật và nhiều trang; XLSX/CSV cũ, quyền/CSRF/version và bảo toàn PDF/trạng thái. Typecheck/Python syntax/41 task cards + DAG PASS.
- E2E PASS chọn PDF, ghép cột, khớp rồi thay PDF lệch; các luồng nộp/ký/trả/nộp lại/duyệt/lưu trữ/admin/hạn/mobile giữ hoạt động. Ảnh comparison.png đã kiểm tra nhãn PDF nguồn và chênh lệch 8.5/9 đúng. Không kết nối daotao trực tiếp; PDF scan cần bảng có thể trích xuất, lỗi đọc không kết luận khớp.

Ngày: 04/10/2026 (Asia/Saigon). Phạm vi: implementation local và adapter có cấu hình. Không phải biên bản nghiệm thu trường.

## Kết quả

- TypeScript `tsc --noEmit`: PASS (frontend checkJs strict).
- Python syntax + template/dependency của 13 task: PASS.
- pytest: **21 test PASS**, 29.19 giây tại lần kiểm tra cuối.
- Chromium headless E2E: PASS, luồng upload chữ ký thực → trả lại → nộp lại → ký bổ sung → archive; tìm kiếm; cấp user admin; hạn nộp; responsive 390px; không lỗi JavaScript.
- Ảnh kiểm tra tại `.local/e2e/`: login, teacher, archive, admin và mobile (không dùng dữ liệu sinh viên thật).

## Bằng chứng nghiệp vụ

| Yêu cầu PRD | Card | Kiểm tra |
|---|---|---|
| FR-GV-01: xuất PDF, tên file | T-04 | PDF nguồn giữ nguyên byte/tên chuẩn, chặn traversal; export chưa cấu hình trả 503; mapping sample UIS đúng/sai |
| FR-GV-02, FR-TK-01, NFR-01: email/RBAC | T-03, T-09 | Domain giả bị từ chối; khác GV/khoa không tải hồ sơ; CSRF, session khóa |
| FR-GV-03: upload/metadata/trạng thái | T-04, T-06 | Sai năm/thiếu chữ ký bị từ chối; rejected resubmit giữ version; E2E |
| FR-TK-01–03: xem/tải/trả/ký lần hai | T-07, T-11 | Lý do bắt buộc, giữ prefix PDF gốc, đúng hai signer; race [200,409] |
| FR-KT-01: chữ ký PKI | T-05, T-08 | CA + CRL ký thật; unsigned, tamper, untrusted, revoked, sai signer đều fail; revalidate archive |
| FR-KT-02: cây kho | T-02, T-08 | Năm/HK/Khoa/LHP, AES-GCM, PDF giải mã đúng byte và hash |
| FR-KT-03: tìm kiếm | T-08, T-11 | Năm + HK + khoa + mã + tên + GV, phân trang, E2E lọc |
| NFR-02: sao lưu | T-10 | Snapshot online, manifest, restore vào kho mới, corrupt backup fail; manual/scheduled job |
| NFR-03, §6.1–2: toàn vẹn | T-05, T-07 | 1/2 chữ ký thật; sửa điểm giữa chữ ký bằng form fill bị từ chối; không scan/rewrite PDF |
| §6.4: sau hạn chỉ xem | T-06–T-10 | GV/TK mutation 403, PDF download 200, ĐT vẫn archive; UI disabled |
| NFR-04: <3 giây, nghìn yêu cầu | T-13 | CHƯA NGHIỆM THU; giới hạn 4 slot không chứng minh tải production |
| §5: UIS/VGCA/kho trường thật | T-13 | TẠM HOÃN theo yêu cầu người dùng; card giữ todo cho giai đoạn sau |

## Review và giới hạn

SQLite một nút và vault local là phạm vi hiện tại. Chưa có cloud connector hay SSO thật. TLS và mã hóa ổ đĩa cho metadata cần cấu hình trên máy chủ trường. Không có bypass chữ ký trong sản phẩm; TestPKI chỉ nằm ở tests, dùng cùng validation policy với dữ liệu revocation thật sinh tại test.

Đoạn kết quả 21 test bên trên là baseline trước T-14. T-14 bổ sung policy local theo yêu cầu người dùng: luôn kiểm tra mật mã và integrity nhưng CA/thu hồi không kiểm tra, được thể hiện rõ trên UI/report. Strict giữ đầy đủ CA/thu hồi. TestPKI vẫn dùng strict với CA/CRL thật trong test.

Có một warning deprecation từ FastAPI/Starlette TestClient khuyên dùng httpx2; không làm fail test. API runtime dùng ASGI/uvicorn. Timeout xác minh 15 giây nhằm chịu mạng PKI, không được báo là đã đạt SLA 3 giây.

Review cuối phát hiện snapshot còn giữ kết nối SQLite khiến WAL/SHM đi theo manifest. Đã đóng kết nối rõ ràng, chuyển snapshot sang journal DELETE và kiểm tra restore bằng kết nối read-only immutable. Test backup/restore và manifest traversal đều xanh sau sửa.

HISTORY.jsonl ghi các chuyển trạng thái card trong lần review tổng hợp local; các timestamp này là thời điểm cập nhật/review card, không dựng lại thời điểm mỗi file được tác giả sửa. Task cards được hoàn thiện qua dependency tuyến tính, không có triển khai agent song song.

## Sửa lỗi xác thực VGCA (T-14, 04/10/2026)

- pytest: **28 passed**, 31.82 giây; một warning deprecation TestClient như baseline.
- TypeScript strict/checkJs + Python syntax + 14 task templates/dependency DAG: PASS.
- Chromium E2E **strict**: PASS full workflow và hiển thị tên người ký.
- Chromium E2E **local**: PASS full workflow và hiển thị phạm vi chưa xác minh CA/thu hồi.
- Hai PDF VGCA thực trong repo: trước tương thích OID, intact=true nhưng valid=false; sau chuyển đúng OID EC ở bộ nhớ, intact=true và valid=true. Common name/email nhận diện đúng Hồ Văn Phi / hvphi@vku.udn.vn. Byte PDF không đổi.
- Test local auto-link và download đúng byte chạy trong DB/kho tạm. Sai email không link/không lưu; signature value bị sửa dù digest không đổi vẫn bị từ chối; PDF thiếu chữ ký/tamper/trailing content bị từ chối.
- Strict thiếu fingerprint/trust roots vẫn fail closed. Bản app default strict; script local chọn local. Không công bố local đạt trust/revocation hay nghiệm thu trường.
- Server local đã khởi động lại; `/api/health` báo `signature_policy=local`, `trust_configured=false`. Tài khoản và lớp có sẵn được giữ.

Đã tham khảo hàm sync_validate_signature trong main.py người dùng cung cấp, áp dụng cách đọc chữ ký và tên chứng thư. Bổ sung kiểm tra `status.valid`, nhận diện email/fingerprint và diff/coverage thay vì chỉ dựa vào `status.intact`. Tài liệu [pyHanko signature status](https://docs.pyhanko.eu/en/latest/api-docs/pyhanko.sign.validation.html) mô tả riêng trạng thái integrity/validity/trust.

## Nhiều bảng điểm cho một lớp (T-15, 05/10/2026)

Người dùng xác nhận một lớp có bảng điểm thành phần và cuối kỳ riêng. Bỏ UNIQUE(course_id), thêm assessment_type/document_label; mỗi submission vẫn có version/status/audit riêng. Nộp mới không tự lấy hồ sơ đầu tiên của lớp; nộp lại phải chỉ định submission_id/version. Giữ các kiểm tra owner/khoa/hạn/chữ ký/metadata và chặn PDF trùng cùng loại.

- Test API cuối: **35 test PASS**, 66.91 giây, gồm domain giả/document ID mâu thuẫn; một warning deprecation TestClient như baseline.
- Migration test từ schema một hồ sơ/lớp: giữ ID/versions/PDF, foreign_key_check không lỗi, restart idempotent.
- Một lớp nộp thành phần/cuối kỳ có hai IDs; nộp lại thành phần giữ nguyên PDF/version cuối kỳ. Nộp lại sai loại/sai người bị từ chối.
- UI chọn loại, tên tùy chọn và nộp mới/nộp lại; danh sách/chi tiết hiển thị loại/ID, bộ lọc theo loại. E2E Chromium PASS: hai bảng điểm cùng lớp và nộp lại đúng hồ sơ, ký/duyệt/lưu trữ độc lập.
- Metadata đọc URL UIS từ text hoặc annotation, hỗ trợ route thành phần/cuối kỳ, mapping document ID riêng cho từng loại. Khi PDF có tiêu đề nhận diện được, chọn sai loại bị báo lỗi.
- Sao lưu SQLite local trước migration tại `.local/pre-multi-documents.sqlite3`. So sánh dữ liệu cũ trước/sau: 4 users, 1 course, 1 submission, 1 PDF version và 16 audit entries được giữ nguyên. Hồ sơ #1 vẫn là final/submitted; không tự nộp file thử vào kho người dùng.
- Server local đã restart với schema mới. Test typecheck/Python syntax/15 cards + DAG PASS.

Một môn có nhiều nhóm hoặc nhiều URL tài liệu không có nghĩa là cùng lớp. Không bỏ kiểm tra UIS để nhận mọi PDF cùng tên môn. Admin có thể cập nhật liên kết cuối kỳ/thành phần của lớp hiện có tại phần Liên kết PDF theo loại bảng điểm.

## Danh sách mã UIS được phép (T-16, 05/10/2026)

- Mỗi loại bảng điểm có danh sách mã UIS phân cách bằng dấu phẩy, tương thích dữ liệu ID đơn; API chuẩn hóa khoảng trắng và mã trùng, từ chối dữ liệu sai. Chỉ admin được sửa.
- PDF phải có một mã nguồn thuộc danh sách cho phép; mã lạ, domain giả và nhiều mã mâu thuẫn vẫn bị từ chối. Kiểm tra loại, học kỳ/năm học và chữ ký giữ nguyên.
- **37 test backend PASS** trong 57.38 giây; typecheck/Python syntax/16 cards và dependency DAG PASS. E2E PASS lưu và đọc lại danh sách nhiều mã; ảnh admin chờ form tải xong và đã kiểm tra.
- Hai PDF thật N1/17210 và N10/17219 nộp thành hai hồ sơ cuối kỳ riêng trong DB kiểm thử, tải lại nguyên byte. Không tự đổi N10 thành loại thành phần.
- Server localhost:8000 đã restart. CSDL01 local cập nhật qua API admin thành `17210,17219`, metadata cả hai mẫu PASS với cấu hình live; users/submissions/versions không đổi. Cấu hình local này không chứng minh hai nhóm UIS là một lớp thật và không kết nối UIS thật.

## URL giữa kỳ của bảng điểm thành phần (T-17, 05/10/2026)

- Hai mẫu TP_N1/TP_N10 có tiêu đề BẢNG ĐIỂM THÀNH PHẦN nhưng URL UIS là `/gv/bang-diem-giua-ky/17210` và `/17219`. Parser thiếu route giua-ky nên báo thiếu mã lớp/URL; đã bổ sung route này cho cả text và annotation, giữ kiểm tra domain và allowlist.
- **38 test backend PASS** trong 52.82 giây; typecheck/Python syntax/17 cards + DAG PASS. Test nộp cả bốn PDF thật thành bốn hồ sơ đúng loại và tải lại nguyên byte; sai loại/mã ngoài danh sách vẫn từ chối. Annotation route giữa kỳ cũng được kiểm thử.
- Server localhost:8000 đã restart, health 200. Metadata cả bốn mẫu PASS với cấu hình CSDL01 live. Không thêm hồ sơ thử vào dữ liệu live, không thay mapping hay sửa PDF. Không sửa UI nên không cần chạy lại E2E giao diện.

## Hiển thị người ký khi gửi trưởng khoa (T-18, 05/10/2026)

- GV gửi thành công thấy xác nhận hồ sơ với tên/email từ chứng thư (nếu có), fingerprint SHA-256 và trạng thái xác thực. Danh sách GV/TK có tên/email người ký PDF; chi tiết hiển thị cùng báo cáo và fingerprint. Dữ liệu được escape trước khi render, không lấy tên tài khoản thay tên chứng thư.
- API danh sách lấy signatures của đúng version hiện tại trong cùng truy vấn, giữ scope theo chủ sở hữu/khoa. Kiểm thử version 1 có Teacher, version 2 có Teacher/Head; teacher khác không thấy hồ sơ.
- **39 test backend PASS** trong 58.07 giây; typecheck/Python syntax/18 cards + DAG PASS. E2E PASS: thông tin ngay sau gửi/nộp lại, trưởng khoa thấy tên trong hàng chờ; ảnh teacher đã kiểm tra.
- Server đã restart. Đã xác nhận API live cho tài khoản TK trả thông tin người ký được lưu. Không thay đổi PDF hoặc policy xác thực; local vẫn ghi rõ CA/thu hồi chưa xác minh.

## GV kiêm trưởng khoa dùng chung chứng thư (T-19, 05/10/2026)

- Theo yêu cầu người dùng, bỏ điều kiện fingerprints của GV/TK phải khác nhau. Từng chữ ký vẫn phải hợp lệ và khớp fingerprint/email của tài khoản ở bước tương ứng; giữ hai chữ ký, quyền vai trò, bảo toàn bản GV, CA/thu hồi ở strict.
- 39 bài regression PASS trong lần chạy suite; test mới ban đầu lỗi tạo fixture ký trùng field, sau đó chỉnh fixture tạo field Head với cùng cert và giữ /Info, đăng nhập lại TK sau admin đổi fingerprint. Test mới PASS riêng trong 4.70 giây: strict/local nhận cùng cert, TK chưa liên kết bị từ chối, PDF một chữ ký bị từ chối, workflow tới archive giữ nguyên byte. Không mock xác thực chữ ký.
- Typecheck/Python syntax/19 cards + DAG PASS. Không sửa UI nên không chạy lại E2E.
- Server localhost:8000 restart; đã dùng API admin liên kết tài khoản `hvphi+tk@vku.udn.vn` với fingerprint đã xác thực của GV `hvphi@vku.udn.vn`. Phiên đăng nhập TK cũ bị thu hồi khi sửa liên kết; cần đăng nhập lại.
- File N1 ký hai lần hiện có vẫn bị chặn do không bảo toàn bản GV và kết quả chữ ký/diff không đạt. Thay đổi quy tắc danh tính không bỏ qua lỗi toàn vẹn PDF.

## VGCA thêm chữ ký hiển thị trên PDF có tag (T-20, 05/10/2026)

- File N1 ký hai lần hiện tại đã được thay bằng bản giữ nguyên prefix GV. Hai chữ ký intact/valid nhưng pyHanko từ chối visible signature sau certification và các object đánh dấu PDF do iText/VGCA thêm. Đây là lỗi tương thích policy, không phải trùng người ký hay lỗi CA local.
- Cho tạo visible signature với DocMDP hiện có; bổ sung rule rất giới hạn: Info chỉ rewrite nguyên nội dung; StructTreeRoot giữ mọi khóa khác, Document K chỉ append một Form/OBJR gắn signature widget mới trong AcroForm, parent mapping cũ giữ nguyên và chỉ append đúng StructParent mới. Không cho blanket whitelist tree/page/content; các rule chữ ký vẫn kiểm tra widget/appearance, permissions và coverage.
- **44 test backend PASS** trong 59.82 giây, gồm ba ca sửa role tag/parent mapping/widget type bị từ chối và các ca sửa điểm, giả chữ ký, strict thiếu CA. Test N1 được bổ sung workflow API GV→TK với cùng chứng thư, tải lại nguyên byte; chạy riêng PASS trong 5.07 giây. Typecheck/Python syntax/20 task cards + DAG PASS.
- Server localhost:8000 restart. Đối chiếu cấu hình live: file N1 giữ nguyên bản hồ sơ #1 và cả hai chứng thư khớp tài khoản GV/TK; xác thực local PASS. Không tự gửi file vào hồ sơ live. Không sửa UI.

## Chọn vai trò đăng nhập (T-21, 05/10/2026)

- Màn hình đăng nhập có select GV, TK, ĐT & BĐCL và Admin. Vẫn dùng email/mật khẩu của tài khoản đã cấp cho vai trò tương ứng; không thay đổi email hay tự nâng quyền.
- API kiểm tra role sau xác thực mật khẩu, trước tạo session. Sai vai trò trả 403, role không hợp lệ 422; request cũ thiếu role vẫn tương thích.
- **48 test backend PASS** trong 72.12 giây; typecheck/Python syntax/21 cards + DAG PASS. E2E PASS đăng nhập cả bốn vai trò và từ chối chọn admin với tài khoản teacher; đã xem ảnh giao diện.
- Server localhost:8000 restart; kiểm tra app.js live có select vai trò. Tài khoản/mật khẩu và quyền dữ liệu giữ nguyên.

## Một email cho bốn vai trò (T-22, 05/10/2026)

- Users dùng UNIQUE(email,role); migration rebuild nguyên tử giữ user IDs/mật khẩu/chứng thư/active và các foreign keys. Login chọn đúng email+role, kiểm tra mật khẩu của user đó; thiếu role khi email đa vai trò yêu cầu chọn rõ. Admin thêm role cho email sẵn có, duplicate cùng role vẫn 409.
- **51 test backend PASS** trong 86.06 giây; typecheck/Python syntax/22 cards + DAG PASS. Migration test giữ users/sessions/courses/submissions/versions/audit, foreign_key_check sạch và restart idempotent. Test password riêng role không đăng nhập chéo.
- E2E PASS: GV, TK, ĐT và admin đều dùng `shared@vku.udn.vn` trong DB thử, giữ luồng ký/duyệt/archive và kiểm tra quyền. Đã kiểm tra ảnh giao diện.
- SQLite live backup trước migration `.local/pre-shared-email.sqlite3`. Bốn tài khoản Hồ Văn Phi chuyển email thành `hvphi@vku.udn.vn`; chỉ đổi email và thu hồi sessions, giữ IDs/passwords/fingerprints/roles/department/active. Đối chiếu users ngoài email và toàn bộ courses/submissions/versions với backup nguyên vẹn; ghi audit từng thay đổi.
- Website đã restart và xác nhận đăng nhập live bằng cùng email/mật khẩu ở cả bốn vai trò, mỗi lựa chọn vào đúng ID cũ. Không tự nâng quyền, không gộp user IDs, không sửa PDF.

## Lớp giảng dạy theo học kỳ và Nộp điểm (T-23, 05/10/2026)

- Dashboard GV có bộ chọn năm học/học kỳ, mặc định kỳ mới nhất được phân công; danh sách lớp hiển thị lịch, phòng, tuần khi nguồn có dữ liệu. Nút Nộp điểm chọn đúng lớp và reset form để upload PDF đã ký, giữ kiểm tra quyền và hạn nộp.
- Import snapshot thời khóa biểu VKU cho GV Hồ Văn Phi: thêm 15 lớp HK1 2026–2027, chạy lại thêm 0 lớp. Đối chiếu lớp cũ, submissions và versions trước/sau nguyên vẹn. Không suy đoán document ID UIS từ tên môn; kỳ mới cần liên kết nguồn PDF phù hợp để đối chiếu khi nộp.
- **52 test backend PASS** trong 80.44 giây; typecheck/Python syntax/23 cards + dependency DAG PASS. Test import kiểm tra idempotent, scope GV và bảo toàn lớp/PDF cũ.
- E2E PASS: đổi năm/học kỳ, không thấy lớp GV khác, Nộp điểm chọn đúng course ID, luồng upload/duyệt/lưu trữ và khóa nút khi hết hạn. Đã kiểm tra ảnh dashboard GV.
- Website localhost:8000 đã restart; API live xác nhận 15 lớp kỳ mới và CSDL01 kỳ 2025–2026 vẫn tồn tại. Dữ liệu lịch lấy từ snapshot báo cáo, chưa đồng bộ UIS tự động.

## Đối chiếu môn/lớp/kỳ không cần mã UIS (T-24, 05/10/2026)

- Theo yêu cầu mới của người dùng, bỏ kiểm tra mã tài liệu/URL UIS khi nộp. Các trường mapping cũ còn tương thích API nhưng không quyết định nhận PDF. Đối chiếu header trang đầu trước bảng sinh viên: môn chính xác, lớp/nhóm chính xác, năm học và học kỳ; giữ loại bảng điểm, chữ ký số, scope và hạn nộp.
- Tên lớp có nhóm như `Cơ sở dữ liệu (1)_TA` đối chiếu trực tiếp với nhóm trong PDF, không yêu cầu mã TKB xuất hiện. Chấp nhận cohort tag UIS `_GIT_TA` khi tên lịch chỉ có `_TA`; nhóm 1 khác nhóm 10. Lớp cũ chỉ có tên môn cần mã lớp ghi rõ trong header để chứng minh lớp, không dùng URL thay thế.
- **59 test backend PASS** trong 76.97 giây; sau điều chỉnh parser alias chạy lại 14 test metadata/UIS/upload PASS trong 8.65 giây. Typecheck/Python syntax/24 cards + DAG PASS. PDF ký thật của hai nhóm nộp vào hai lớp riêng và tải lại nguyên byte; API từ chối GV khác, sai nhóm, môn, năm/kỳ và thiếu nhóm.
- Website đã restart với policy mới. Đối chiếu lớp trong ảnh `TKB-9B96AC4C50`: nhóm 1 HK1 2026–2027; PDF N10 hiện có là nhóm 10 HK1 2025–2026 nên bị từ chối do lớp/kỳ, không còn lỗi liên kết mã UIS. Không đổi phân công, hồ sơ hay PDF live. Không sửa UI nên không chạy lại E2E.

## Hai nút nộp theo loại (T-25, 05/10/2026)

- Mỗi lớp GV có Nộp điểm thành phần và Nộp điểm cuối kỳ. Nút chọn đúng lớp và assessment_type trước refresh hồ sơ nộp lại, reset file/tên/target về nộp mới. Cả hai khóa khi hết hạn.
- Typecheck/Python syntax/25 cards + dependency DAG PASS. E2E PASS chọn hai loại qua nút, upload hai hồ sơ độc lập, luồng ký/duyệt/archive, nộp lại, quyền và hạn; mobile không tràn ngang. Đã kiểm tra ảnh teacher với hai nút.
- Frontend live localhost:8000 đã phục vụ mã mới; backend/dữ liệu/policy không đổi nên không chạy lại API suite.

## Rút gọn form upload (T-26, 05/10/2026)

- Bỏ các labels Loại bảng điểm, Tên bảng điểm, Cách nộp và đoạn hướng dẫn khỏi form upload. Controls nội bộ ẩn vẫn gửi đúng loại/hồ sơ/version; loại lấy từ nút TP/HD hoặc cuối kỳ, nộp lại qua nút trên danh sách.
- Typecheck/Python syntax/26 cards + DAG PASS; E2E PASS kiểm tra các trường không hiển thị, hai loại nộp riêng, nộp lại đúng version, ký/duyệt/archive, hạn và mobile. Đã kiểm tra ảnh teacher: form chỉ còn lớp, PDF và Gửi trưởng khoa.
- Frontend live localhost:8000 đã phục vụ mã mới; không đổi backend hoặc dữ liệu.

## Cấp tài khoản GV và Excel (T-27, 05/10/2026)

- Snapshot có 197 tên nhóm: 193 cá nhân và 4 mục không xác định cá nhân (3 khoa, Bank Agribank). Tạo 192 tài khoản role teacher, active; giữ nguyên GV Hồ Văn Phi. Chưa có thông tin khoa nên GV mới ghi `Chưa phân khoa`, không tự cấp TK/admin hoặc phân công lớp.
- Email: bỏ học vị/dấu, chữ đầu họ/đệm + tên; các trùng đã được người dùng chọn thêm số: Nguyễn Thành Tâm → nttam2, Ngô Thị Hiền Trang → nthtrang2, Nguyễn Thị Thanh Thuý (ĐHNN) → nttthuy2. Tài khoản cũ tên Giảng viên HV Phi được đối chiếu alias đã biết, không đổi thông tin cũ.
- Mật khẩu batch mới ngẫu nhiên 8 ký tự gồm chữ hoa/thường/số theo yêu cầu. DB dùng scrypt; API tạo user thông thường vẫn mặc định tối thiểu 12. Không ghi mật khẩu vào audit. Credentials và workbook được giữ trong đường dẫn bỏ qua Git.
- **62 test backend PASS** trong 82.40 giây; test import sau thêm alias live PASS riêng 3 bài trong 4.02 giây: quy tắc email, login 8 ký tự, idempotent, giữ dữ liệu cũ, conflict rollback, loại mục tổ chức. Typecheck/Python syntax/27 cards + DAG PASS. Không thay UI nên không chạy E2E.
- Backup trước import `.local/pre-gv-account-import.sqlite3`; lần đầu gặp tên tài khoản cũ khác tên nguồn đã rollback nguyên tử, sau đối chiếu alias import thành công. So sánh users cũ và courses/submissions/versions/sessions/settings với backup nguyên vẹn, foreign keys sạch. Xác minh đủ 193 credentials khớp DB.
- Excel `outputs/gv-accounts-20261005/DS_tai_khoan_GV_VKU.xlsx` có 193 dòng tài khoản, sheet riêng 4 mục không tạo; tên nguồn/email/password/role/khoa/trạng thái/ghi chú, bảng lọc và freeze header. Artifact Tool tạo và render cả hai sheet, đã xem ảnh; preview che password, workbook giữ password thật. Đọc lại XLSX xác nhận tất cả email/password khớp credentials, 192 mật khẩu mới dài 8, không trùng email. Login live thành công dqhien và htmphuong, đã logout phiên thử.

## Nhãn theo loại lớp và hai GV + TK (T-28, 05/10/2026)

- Lớp có từ khóa đồ án/đề án/thực tập/kiến tập dùng Nộp điểm hướng dẫn và Nộp điểm Hội đồng. Lớp thường dùng Nộp điểm thành phần và Nộp điểm Cuối kỳ. Assessment keys component/final giữ tương thích dữ liệu; số ký hội đồng chưa được yêu cầu thay đổi nên giữ một GV + TK.
- Theo câu trả lời phương án 2, cuối kỳ lớp thường cần hai GV khác nhau. Admin chọn co_teacher_id active, khác GV phụ trách; không tự phân công và không cấp thêm quyền xem/nộp cho GV thứ hai. Submission chụp second_teacher_id khi nộp, đổi phân công lớp sau đó không thay người ký hồ sơ cũ.
- GV nộp PDF có đúng hai chữ ký của hai GV được phân công và chứng thư khác nhau; TK giữ nguyên prefix và append chữ ký thứ ba; Phòng Đào tạo xác thực lại đủ ba trước archive. GV kiêm TK vẫn dùng cùng chứng thư ở hai vai trò như T-19; hai GV phải khác chứng thư. Không cho chọn loại other để lách bảng điểm có header cuối kỳ/thành phần.
- **70 test backend PASS** trong 117.78 giây. Fixtures dùng PKI/CRL thật, hai cert GV khác nhau và cert TK; kiểm tra thiếu/sai/trùng cert, scope, admin-only, snapshot phân công, ba chữ ký và PDF nguyên byte, hình thức đặc biệt giữ workflow cũ. Các test mật mã âm tính được cập nhật đúng số ký để vẫn kiểm tra trust/giả chữ ký/toàn vẹn.
- Typecheck/Python syntax/28 cards + DAG PASS. E2E PASS cả bốn nhóm tên lớp, hai nút cho lớp thường, nộp hai loại, hiển thị hai GV, nộp lại, thêm TK/archive, cấu hình GV thứ hai từ admin, hạn và mobile. Đã kiểm tra ảnh teacher/admin.
- Backup `.local/pre-three-signatures.sqlite3`, migration thêm hai FK nullable; website restart và health/API live PASS. So sánh toàn bộ cột cũ users/courses/submissions/versions/audit/settings/sessions với backup nguyên vẹn, foreign keys sạch. Live có 16 lớp chưa tự phân công GV thứ hai; admin cần chọn người trước khi nộp cuối kỳ theo quy tắc mới. Không sửa PDF cũ hoặc tự công nhận PDF thiếu ký.

## Khóa nút bảng điểm đã nộp (T-29, 05/10/2026)

- API courses bổ sung submitted_assessments từ tất cả hồ sơ của từng course ID, độc lập phân trang/bộ lọc danh sách. GV chỉ nhận các lớp thuộc scope hiện có. Dashboard khóa nút đúng loại và hiện Đã nộp, giữ nhãn theo loại lớp và khóa theo hạn.
- Sau gửi thành công refresh courses và render lại; tải lại/đăng nhập lại vẫn giữ trạng thái. Hồ sơ bị trả vẫn khóa nút nộp mới và dùng Nộp lại trên danh sách. Không thay policy backend cho nhiều hồ sơ, version, chữ ký hay dữ liệu PDF.
- 9 test API/chữ ký liên quan PASS trong 17.30 giây, gồm trạng thái riêng từng loại, không phụ thuộc filter, hồ sơ bị trả và scope. Typecheck/Python syntax/29 cards + DAG PASS. E2E PASS nộp một loại chỉ khóa một nút, hai loại khóa cả hai, bộ lọc rỗng không mở lại, đăng nhập lại/nộp lại, workflow ký/archive và mobile; ảnh teacher đã kiểm tra.
- Website đã restart, health/API live PASS: CSDL01 có component/final đã nộp, các lớp TKB mới chưa nộp vẫn có nút khả dụng. Không đổi trạng thái hồ sơ hay PDF cũ.

## Đồng bộ tài khoản Excel và bổ sung ĐT (T-30, 05/10/2026)

- Nguồn chính: Acc/DS_tai_khoan_GV_VKU.xlsx, sheet tài khoản có 197 dòng. GV,TK tạo hai record cùng email/password; GV,TP ĐT ánh xạ teacher/training. Giữ TK/admin cũ của Hồ Văn Phi theo lựa chọn 2; không diễn giải sheet ghi chú lịch sử thành lệnh xóa hoặc từ chối tài khoản được người dùng thêm.
- Thêm Nguyễn Thị Thùy Giang, nttgiang@vku.udn.vn, training, đơn vị ĐT & BĐCL. Mật khẩu trống của tài khoản mới sinh 8 ký tự có chữ hoa/thường/số; tài khoản cũ không có mật khẩu nguồn giữ hash. Không ghi mật khẩu vào audit/log. File credentials và Excel kết quả nằm trong thư mục ignored; nguồn Excel không sửa.
- Import atomic: 15 record mới, 190 record cập nhật tên/khoa; tổng 197 GV, 11 TK, 2 ĐT, 1 admin. Import lặp tạo/cập nhật 0 record và credentials giữ nguyên. IDs/email/role/fingerprint/active của toàn bộ người dùng cũ giữ nguyên, TK/admin Phi không đổi; so sánh courses/submissions/versions/settings với backup nguyên vẹn, foreign keys sạch. Session của user có thay đổi bị thu hồi để đăng nhập lại với thông tin mới.
- Backup SQLite trước ghi: .local/pre-excel-account-sync.sqlite3. 9 test import/API PASS, gồm role/login, idempotency, blank password, preservation và dữ liệu bất hợp lệ. Typecheck/Python syntax/30 task cards + DAG PASS.
- Excel kết quả 211 dòng khớp credentials từng trường, mỗi email/vai trò duy nhất; có bảng lọc và freeze header. Artifact Tool inspect/error scan sạch, ảnh preview che mật khẩu kiểm tra đạt; bản Excel giao có mật khẩu thật. Health live và 5 lượt login/logout GV/TK/ĐT/admin PASS sau khi transaction hoàn tất. Không cần restart vì thay đổi này chỉ là dữ liệu tài khoản và công cụ import.

## Xóa bảng điểm Hồ Văn Phi (T-31, 05/10/2026)

- Theo yêu cầu trực tiếp, xóa 3 submissions của teacher email hvphi@vku.udn.vn (2 component submitted, 1 final archived) và 4 versions/PDF mã hóa liên quan. Giữ nguyên users/courses/settings và audit cũ; ghi audit xóa mới. Không còn hồ sơ người dùng này, foreign keys sạch, các bảng dữ liệu ngoài scope được so sánh nguyên vẹn.
- Backup DB, manifest và từng PDF nguyên bytes tại .local/deleted-phi-submissions-20261005T074740648315Z. Resolved source/destination đều kiểm tra trong vault/backup, không PDF nào được hồ sơ khác tham chiếu. Delete SQL trong transaction, unlink đúng file sau commit. Không thêm API/UI xóa.

## Nhãn Chưa ký cho Trưởng khoa (T-32, 05/10/2026)

- statusLabel hiển thị submitted thành Chưa ký cho head ở bảng và chi tiết; các vai trò khác giữ Chờ trưởng khoa. Backend/status/permissions không đổi.
- Kiểm chứng trực tiếp head/teacher/submitted và archived, cùng hai vị trí render PASS. Typecheck/Python syntax/32 task cards + DAG PASS. E2E hiện có PASS luồng upload/nộp lại/ký/archive/admin/hạn/mobile. Thay đổi frontend static có hiệu lực sau tải lại trang.

## Tiến trình duyệt GV và ẩn nút hoàn thành (T-33, 05/10/2026)

- Courses trả assessment_statuses theo từng loại. Nhiều hồ sơ cùng loại lấy bước chưa hoàn tất (rejected/submitted/head_signed/archived); chỉ archived khi tất cả đã archived. Tổng hợp từ toàn bộ hồ sơ, độc lập pagination/filter và giữ scope teacher/head hiện có. submitted_assessments vẫn tương thích.
- GV thấy Chờ Trưởng khoa duyệt, Chờ Đào tạo duyệt, Hoàn thành trong lớp học phần, bảng hồ sơ, chi tiết và bộ lọc. Nút pending còn hiển thị, disabled theo T-29; archived không render nút, giữ tên loại và badge Hoàn thành. Các loại độc lập; bị trả vẫn hiển thị Đã trả lại và nộp lại từ hồ sơ. TK giữ nhãn Chưa ký. Không thay backend workflow/chữ ký/PDF/quyền.
- 10 API tests assessment/signature PASS, gồm tiến trình ký/archive và nhiều hồ sơ chưa hoàn thành. Typecheck/Python syntax/33 cards + DAG PASS. E2E kiểm tra nút visible/disabled khi pending/head_signed, mất nút khi archived, Hoàn thành sau reload, component độc lập, bộ lọc nhãn và các luồng hiện có; ảnh teacher-completed và mobile kiểm tra đạt.
- Website đã restart; health và login/course-status API live PASS. Dữ liệu live có component submitted và head_signed thể hiện đúng tiến trình; không sửa trạng thái hồ sơ thực để thử nghiệm.

## Đồng bộ phiên CSRF khi trả hồ sơ (T-34, 05/10/2026)

- Cookie phiên dùng chung giữa các tab nhưng CSRF state riêng; xoay phiên cùng identity hoặc đổi vai trò khi form cũ mở đã được tái hiện trong E2E. api() lấy /api/me trước mutation (trừ login), cập nhật CSRF khi ID không đổi; khác ID cập nhật dashboard và dừng mutation với thông báo kiểm tra lại. Không tắt kiểm tra CSRF backend.
- Nếu race khiến request nhận đúng lỗi CSRF 403 trước handler, đồng bộ cùng identity rồi retry một lần. Không retry lỗi quyền/version/network, không gửi thao tác cũ bằng role khác. Lý do trả được giữ nguyên; UI vẫn refresh danh sách sau thành công.
- 3 API tests PASS: RBAC/CSRF/scope, lý do trả/nộp lại/stale version, ĐT xoay phiên với token cũ bị 403 (hồ sơ không đổi), lấy token mới rồi trả thành công. Typecheck/Python syntax/34 cards + DAG PASS.
- E2E PASS: đổi cookie TK sang GV khi form đang mở không phát POST reject; cùng TK xoay phiên vẫn trả thành công; mô phỏng một CSRF rejection cho thấy đúng một retry (2 requests), sau đó nộp lại/ký/lưu trữ và các luồng cũ hoạt động. ĐT xoay phiên trước archive cũng PASS. Session rotation test route chỉ nằm trong tests/e2e.py, đưa trước static mount và tránh tiêu thụ login throttle của fixture; production không có route này và throttle không đổi.
- Health live PASS và frontend app.js đang phục vụ code syncSession mới. Không thao tác trả hồ sơ thực hoặc thay PDF/dữ liệu live để kiểm thử; sửa frontend static, tải lại trang áp dụng.

## Mở nút nộp lại khi bị trả (T-35, 05/10/2026)

- Nút của assessment rejected được enabled nếu chưa hết hạn; pending vẫn disabled và archived vẫn ẩn. Status Đã trả lại giữ nguyên. Khi bấm nút lớp, lấy danh sách rejected theo course/type và chọn hồ sơ đầu tiên cùng version; dùng chung selectResubmission với nút Nộp lại trong bảng. Nếu hồ sơ không còn rejected, refresh và dừng thay vì tạo hồ sơ mới.
- E2E PASS: trả final mở nút final, component pending vẫn khóa; filter rỗng/reload vẫn mở đúng nút; bấm nút lớp chọn submission_id=1/version=2, nộp lại giữ ID=1, version tăng 3 và tổng hồ sơ giữ 2; sau gửi nút khóa lại với Chờ Trưởng khoa duyệt. Các kiểm tra session/CSRF/ký/archive/hạn/mobile hiện có PASS. Typecheck/Python syntax/35 cards + DAG PASS.
- Không thay backend, dữ liệu/PDF live; frontend static áp dụng sau tải lại. Quy tắc hạn nộp vẫn áp dụng.

## GV ký thứ hai không cần dạy lớp (T-36, 05/10/2026)

- Giữ scope GV nộp và đối chiếu môn/lớp/năm/học kỳ từ PDF. Với cuối kỳ lớp thường, nhận diện chứng thư người ký thứ hai trong các tài khoản teacher active khác primary, theo fingerprint hoặc email khi local và chưa liên kết. Chỉ chấp nhận khớp duy nhất; không xét khoa, lớp, kỳ của người ký thứ hai và không yêu cầu co_teacher_id cấu hình trước. GV phụ trách ký trước, GV thứ hai kế tiếp theo thứ tự PDF hiện có.
- Trích chứng thư chỉ chọn identity; toàn bộ PDF vẫn qua verifier mật mã/toàn vẹn/trust/revocation theo policy strict/local trước persist và bind_signer. Hai GV phải dùng chứng thư khác nhau. Khi commit nhận diện lại và kiểm tra active; lưu second_teacher_id thật vào submission. TK/ĐT tiếp tục dùng snapshot này để xác minh hai GV + TK, thay cấu hình lớp không đổi người ký hồ sơ cũ.
- UI giải thích GV thứ hai không cần dạy lớp; cấu hình GV thứ hai cũ chỉ tham khảo, không ràng buộc người ký thực. Không sửa schema, phân công lớp, chứng thư hay PDF live.
- 75 tests assessment/signatures/system PASS trong 383.32 giây: không cấu hình hoặc cấu hình người khác, GV thứ hai khác khoa/không dạy lớp vẫn nộp/ký/archive được; snapshot đúng, secondary không được cấp quyền xem/nộp lớp; inactive/unknown/ambiguous/same-cert/wrong/missing/tampered signatures bị từ chối. Các kiểm tra scope/CSRF/local VGCA/PDF thật/nộp lại và hệ thống hiện có PASS.
- Typecheck/Python syntax/36 cards + DAG PASS; E2E toàn luồng GV/TK/ĐT/admin, resubmit, CSRF, nhãn/status, archive/hạn/mobile PASS. Website restart, health và hướng dẫn frontend live PASS.

## Duyệt/lưu ngay từ cột trạng thái Phòng Đào tạo (T-37, 05/10/2026)

- Training hiển thị head_signed là Đang chờ P.ĐT duyệt, archived là Đã lưu ở bảng/chi tiết/filter. Cột trạng thái có nút Duyệt enabled cho head_signed và disabled cho archived; submitted/rejected không có nút duyệt. GV/TK giữ nhãn riêng hiện có.
- Nút gửi archive endpoint hiện có với đúng id/version, khóa ngay trong khi xử lý, refresh sau thành công. Backend tiếp tục xác minh chữ ký/PDF/trust theo policy, kiểm tra CSRF/quyền/state/version. Không bỏ qua bước kiểm tra, không tự archive hồ sơ live để thử.
- Typecheck/Python syntax/37 cards + DAG PASS; 4 API archive/workflow tests PASS. E2E PASS trạng thái chờ đúng nhãn/nút trong cột, chỉ một POST archive, Đã lưu/nút disabled sau thành công và reload, nhãn filter, không có nút cho hồ sơ submitted; GV vẫn Hoàn thành. Luồng session rotation/CSRF/reject/resubmit/ký/admin/hạn/mobile vẫn PASS. Ảnh archive kiểm tra đạt.
- Health live và app.js cập nhật PASS; frontend static có hiệu lực sau tải lại, không cần restart backend.

## Đặt Đã lưu dưới nút Duyệt (T-38, 05/10/2026)

- Trong cột trạng thái training/archived, chèn nút Duyệt disabled trước badge, xuống dòng để Đã lưu nằm dưới nút. Không đổi vị trí trạng thái chờ hay hành vi archive.
- Typecheck/Python syntax/38 cards + DAG PASS; E2E hiện có PASS. Ảnh archive xác nhận Duyệt phía trên/Đã lưu phía dưới, nút disabled. app.js live cập nhật PASS; tải lại trang để áp dụng.

## Người ký PDF trong Giảng viên/Khoa sau trả/lưu (T-39, 05/10/2026)

- Sửa subquery signatures lấy versions gần nhất có version <= submissions.version, ORDER BY version DESC LIMIT 1. Reject/archive tăng phiên bản workflow mà không sinh PDF mới, vì vậy equality cũ trả chữ ký rỗng. Frontend hiện có tiếp tục hiển thị từng tên/email chứng thư; không suy người ký từ tên người nộp.
- Test API regression PASS submitted/rejected/resubmit/head_signed/archived: dữ liệu danh sách khớp verification, đủ hai GV rồi thêm TK; GV ngoài scope không thấy hồ sơ. Typecheck/Python syntax/39 cards + DAG PASS. E2E PASS tên người ký còn sau rejected/archived/reload; ảnh archive hiển thị Teacher, SecondTeacher, Head trong cột Giảng viên/Khoa và luồng khác hoạt động.
- Website restart; đối chiếu live training list với verification PASS: hồ sơ #2 archived có 2 chữ ký, #1 rejected có 1 chữ ký đúng PDF gần nhất. Không sửa PDF, versions, metadata chữ ký hay trạng thái dữ liệu live.
## Dropdown Khoa và So Khớp điểm (T-40, 05/10/2026)

- Khoa là dropdown theo danh mục lớp được cấp quyền; cột So Khớp nằm ngay sau trạng thái, chỉ dành cho Phòng Đào tạo. Người dùng chọn Excel .xlsx hoặc CSV UTF-8 xuất từ daotao, xác nhận đúng môn/lớp/kỳ/loại và ghép cột điểm. Kết quả theo MSSV, hiển thị điểm lệch, thiếu/thừa sinh viên và dữ liệu chưa đầy đủ; chưa ghép đủ cột hoặc ô trống không được kết luận khớp toàn bộ.
- PDF được đọc nguyên bản từ kho mã hóa theo phiên bản PDF gần nhất. Không sửa điểm/PDF, không tự duyệt; file nguồn xử lý tạm. API kiểm tra quyền training, CSRF và phiên bản trước/khi ghi audit; audit chỉ lưu số lượng/kết quả, không ghi dữ liệu điểm hoặc MSSV.
- 10 parser/API tests PASS: bảng điểm thật thành phần 71 SV/3 cột, cuối kỳ 71 SV/1 cột, hướng dẫn 19 SV/1 cột; CSV/XLSX, mã SV có dấu chấm, số thập phân/dấu phẩy/0, lệch/thiếu/thừa/trống/ghép thiếu, quyền/CSRF/version và bảo toàn PDF/trạng thái. Typecheck/Python syntax/40 cards và DAG PASS.
- E2E PASS: dropdown/filter Khoa, vị trí/quyền nút So Khớp, upload/ghép cột, kết quả khớp rồi lệch, các luồng nộp lại/ký/trả/duyệt/archive/admin/hạn/mobile hiện có. Ảnh comparison.png đã kiểm tra hiển thị MSSV, điểm PDF và điểm file lệch rõ ràng.
- Chưa kết nối trực tiếp daotao theo lựa chọn nguồn file của người dùng. PDF scan không có bảng trích xuất được sẽ báo lỗi; file cần cột MSSV/Mã sinh viên/Số thẻ và tiêu đề cột rõ ràng. Kết quả phản ánh file cán bộ chọn.
- Website đã restart; health/login training và preview So Khớp của cả 4 hồ sơ live đều HTTP 200 (5, 2, 19, 6 sinh viên). Không upload nguồn điểm thử hay thay đổi trạng thái hồ sơ live.

