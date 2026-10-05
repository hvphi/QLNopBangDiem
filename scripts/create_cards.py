from pathlib import Path

TASKS = [
('Thiết lập kiến trúc và flow triển khai', '§1, §2, §5', ['docs/tasks/', '.gitignore', 'requirements.txt', 'package.json', 'tsconfig.json', 'scripts/'], 'Chốt kiến trúc, conventions, flow và lệnh chạy/check nhất quán.', 'PRD: “Hệ thống Ký số và Quản lý Bảng điểm Điện tử”.', ['Ghi quyết định kiến trúc và ma trận traceability.', 'Tạo scripts chạy local, typecheck, test.'], ['Task có touches giao nhau luôn có dependency']),
('Xây dựng dữ liệu, kho mã hóa và nhật ký', '§3.3, §4 NFR-02', ['backend/db.py', 'backend/storage.py'], 'Lưu phiên bản PDF nguyên byte, metadata và lịch sử xử lý bền vững.', 'PRD: “Năm học -> Học kỳ -> Khoa -> Tên LHP”.', ['Tạo schema users/courses/submissions/versions/audit/settings/sessions.', 'Lưu PDF AES-GCM theo cây phân loại, chống traversal và giữ hash.'], ['PDF đọc lại giống nguyên byte', 'Không chấp nhận đường dẫn vượt kho']),
('Xây dựng đăng nhập và phân quyền', '§3 FR-GV-02, FR-TK-01; §4 NFR-01', ['backend/auth.py'], 'Người dùng đăng nhập bằng tài khoản email trường và chỉ truy cập đúng quyền.', 'PRD: “Yêu cầu tất cả người dùng phải đăng nhập bằng email vku.udn.vn”.', ['Hash mật khẩu, session cookie HttpOnly và CSRF.', 'Kiểm tra vai trò, email domain, scope khoa và khóa tài khoản.'], ['Email domain giả bị từ chối', 'Tài khoản khóa không sử dụng session cũ']),
('Đối chiếu UIS và cung cấp bảng điểm xuất', '§3 FR-GV-01, FR-GV-03; §5 UIS', ['backend/uis.py'], 'GV lấy PDF nguồn và đối chiếu metadata với danh mục UIS.', 'PRD: “đọc ... Năm học, Học kỳ, Lớp học phần, Tên học phần và đối chiếu”.', ['Adapter danh mục và PDF xuất từ snapshot được trường cấp.', 'Trích text PDF, so khớp học kỳ/năm/mã/tên môn với lớp được phân công.', 'Chuẩn hóa tên tải xuống không thay đổi byte.'], ['Metadata sai năm bị từ chối', 'GV không được xuất lớp người khác']),
('Xác thực chữ ký PDF với pyHanko', '§3 FR-KT-01; §4 NFR-03; §6.1–2', ['backend/verification.py'], 'Phát hiện thiếu chữ ký, sai người ký, PDF bị sửa và chứng thư không tin cậy.', 'PRD: “Tự động kiểm tra tính hợp lệ của cả 02 chữ ký số ... bằng thư viện pyhanko”.', ['Đọc chữ ký bằng pyHanko và validation context có trust roots.', 'Kiểm tra integrity, coverage, modification level, revocation và fingerprint.', 'Đặt giới hạn thời gian, kích thước và báo lỗi rõ.'], ['PDF không ký bị từ chối', 'PDF ký thật hợp lệ được chấp nhận', 'PDF chỉnh sửa sau ký bị từ chối', 'Chứng thư không tin cậy bị từ chối']),
('Triển khai gửi và theo dõi bảng điểm của GV', '§3 FR-GV-03; §2', ['backend/app.py'], 'GV nộp PDF một chữ ký hợp lệ và theo dõi trạng thái xử lý.', 'PRD: “Gửi file đã ký số ... để Trưởng khoa phê duyệt”.', ['API gửi, danh sách, xem/tải PDF theo quyền.', 'Kiểm tra lớp, signature, hạn nộp; cho nộp lại bản bị trả.', 'Chống duplicate và tạo audit transaction.'], ['GV không xem hồ sơ người khác', 'Nộp lại hồ sơ bị trả tạo phiên bản mới', 'Hết hạn GV không thể nộp']),
('Triển khai phê duyệt và nộp lần hai của TK', '§3 FR-TK-01–03; §6.1', ['backend/app.py'], 'TK xem hồ sơ trong khoa, trả kèm lý do hoặc nộp PDF có đủ hai chữ ký.', 'PRD: “Bảng điểm đã có đủ 2 chữ ký: giảng viên và trưởng khoa”.', ['API trả lại yêu cầu lý do và version.', 'Kiểm tra khoa, chữ ký lần hai, prefix bản gốc và metadata.', 'Chuyển submitted → head_signed bằng optimistic locking.'], ['TK không duyệt khoa khác', 'Từ chối thiếu lý do thất bại', 'Hai thao tác đồng thời chỉ một thành công', 'Lần hai không giữ PDF gốc bị từ chối']),
('Tiếp nhận, lưu trữ và tra cứu kho', '§3 FR-KT-01–03; §6.3', ['backend/app.py'], 'Phòng ĐT kiểm tra lại hai chữ ký và lưu trữ, tìm kiếm bảng điểm.', 'PRD: “Tra cứu nâng cao theo Năm học, Học kỳ, Khoa, Mã LHP, Tên môn, Tên giảng viên”.', ['API archived/reject training và revalidation.', 'Bộ lọc, phân trang, cây thư mục và audit.', 'PDF archived bất biến; không cung cấp API xóa/đè.'], ['ĐT xác minh lại trước lưu trữ', 'Tra cứu kết hợp bộ lọc trả đúng hồ sơ', 'Kho giữ nguyên PDF đã ký']),
('Quản lý người dùng, danh mục và thời hạn', '§1 Admin; §4 NFR-01; §6.4', ['backend/app.py', 'backend/manage.py'], 'Admin cấp tài khoản, cấu hình lớp và hạn nộp kiểm soát được.', 'PRD: “Quản lý phân quyền, cấu hình danh mục và sao lưu dữ liệu”.', ['CLI bootstrap admin không mật khẩu mặc định.', 'API users/courses/deadline có validation và audit.', 'Cấu hình fingerprint chứng thư theo tài khoản.'], ['User không tự nâng quyền', 'Admin thiết lập hạn nộp hợp lệ', 'Sai fingerprint bị từ chối']),
('Bảo vệ vận hành và sao lưu phục hồi', '§4 NFR-01–04; §5 Storage', ['backend/operations.py', 'backend/app.py', 'scripts/backup.ps1', 'docs/OPERATIONS.md'], 'Dữ liệu có backup nhất quán, phục hồi được và giới hạn tài nguyên khi xử lý PDF.', 'PRD: “Tự động sao lưu định kỳ ... Cloud/Ổ cứng dự phòng”.', ['Backup SQLite online + kho encrypted, manifest SHA256, phục hồi validate.', 'Hướng dẫn lịch Windows Task Scheduler, HTTPS và giữ khóa ngoài backup.', 'Giới hạn upload, worker, login rate và headers.'], ['Backup phục hồi giữ dữ liệu và PDF', 'Backup hỏng bị từ chối', 'Upload vượt giới hạn bị từ chối']),
('Xây dựng giao diện cho bốn vai trò', '§3.1–3.3; §1 Admin', ['frontend/'], 'Người dùng thực hiện quy trình nộp, duyệt, tra cứu và quản trị trên web tiếng Việt.', 'PRD: “Xem nhanh file PDF trực tiếp trên giao diện web”.', ['Login, dashboard, upload, PDF preview và download.', 'Bộ lọc và trạng thái rõ, lỗi server và xử lý thao tác version conflict.', 'Admin form, responsive, keyboard và labels.'], ['GV đăng nhập và theo dõi danh sách', 'TK trả hồ sơ kèm lý do', 'ĐT tìm kiếm kho', 'Admin mở trang quản trị']),
('Kiểm thử tích hợp và review toàn bộ flow', '§6.1–4; §4', ['tests/', 'scripts/check.py', 'docs/TEST_REPORT.md', 'README.md', 'requirements.txt', 'package.json'], 'Có bằng chứng chạy được flow chính và các đường từ chối quan trọng.', 'PRD: “cảnh báo chính xác khi ... PDF bị thay đổi nội dung sau khi ký”.', ['Tạo PDF ký thật một/hai chữ ký trong test; không dùng mẫu giả chữ ký.', 'Test RBAC, deadline, version conflict, storage backup và E2E.', 'Ghi kết quả và giới hạn tích hợp thật.'], ['Flow GV → TK → ĐT với hai chữ ký mật mã thực', 'Các test quyền, deadline, PDF tamper và E2E đều xanh']),
('Kết nối trường và nghiệm thu triển khai sản xuất', '§4 NFR-04; §5; §6', ['docs/DEPLOYMENT.md', 'deploy/'], 'Triển khai được với UIS, VGCA và kho trường; đo tải theo môi trường thực.', 'PRD: “< 3 giây/file” và “hàng nghìn yêu cầu ... đồng thời”.', ['Nhận API UIS/SSO, CA chain/CRL/OCSP và chứng thư người dùng thật.', 'Cấu hình kho ngoài, backup định kỳ, TLS và nghiệm thu chữ ký VGCA.', 'Đo p95 <3 giây và tải nghìn yêu cầu; lên PostgreSQL/queue/object storage nếu cần.'], ['PDF VGCA thực của trường xác minh đủ hai chữ ký', 'Backup kho trường phục hồi được', 'Đo tải đáp ứng mục tiêu trên môi trường nghiệm thu']),
]

for i, (title, refs, touches, goal, context, steps, cases) in enumerate(TASKS, 1):
    tid = f'T-{i:02d}'
    previous = '[]' if i == 1 else f'["T-{i-1:02d}"]'
    text = f'''---
id: {tid}
title: {title}
status: todo
model: codex
effort: high
depends_on: {previous}
touches:
''' + ''.join(f'  - {p}\n' for p in touches) + f'''prd_refs: ["{refs}"]
owner: null
started_at: null
finished_at: null
---

# {tid} · {title}

## Mục tiêu
{goal}

## Ngữ cảnh cần biết
{context}

## Phạm vi
**Trong:** {'; '.join(steps)}

**Ngoài:** thay đổi task khác; ký số thay người dùng; tự cấp tài khoản trường; công bố nghiệm thu khi chưa có chứng cứ.

## Đầu vào đã có
`docs/PRD_gem.md`, `docs/tasks/_TEMPLATE.md`, `docs/tasks/CONVENTIONS.md`, `docs/tasks/FLOW.md`.
''' + ('Task nền tảng, không có dependency.\n' if i == 1 else f'`T-{i-1:02d}` để lại code và kiểm tra theo phạm vi card; xem `touches` của card trước.\n') + '''
## Việc phải làm
''' + ''.join(f'{n}. {s}\n' for n, s in enumerate(steps,1)) + '''
## Quy ước bắt buộc
- Máy chủ kiểm tra quyền, khoa, chủ sở hữu, hạn nộp và trạng thái tại mỗi mutation. Dùng version để chống ghi đè đồng thời.
- Giữ nguyên byte PDF đã ký; không render, chỉnh sửa hoặc chuẩn hóa nội dung PDF. Tên file và đường dẫn do máy chủ sinh.
- Adapter UIS và kho trường cần cấu hình thật. Fixture chỉ dùng trong test, không coi là tích hợp sản xuất.
- Mỗi task chỉ sửa `touches`; task sửa chung file phải nối dependency. Cập nhật card tương ứng được phép mặc định.
- Task chưa có điều kiện kiểm chứng không được ghi done; ghi blocked với đầu vào cần cung cấp.

## Checklist đầu ra
- [ ] Typecheck: `npm run typecheck` xanh
- [ ] Test API: `npm test` xanh (test liên quan trong `tests/test_system.py`)
''' + ('- [ ] Test E2E: `npm run e2e` xanh (UI)\n' if i in (11,12) else '- [ ] Test E2E: không áp dụng riêng card không có UI; kiểm tra tổng hợp T-12\n') + '''- [ ] Không đụng file ngoài `touches`
- [ ] Cập nhật `status: review` + `finished_at` trong frontmatter card này
- [ ] Ghi 3–5 dòng "Đã làm gì" vào cuối card

## Test phải viết
''' + ''.join(f'- {c}.\n' for c in cases) + f'''
## Định nghĩa "xong"
{goal} Các test liên quan xanh và review đủ bằng chứng; không có blocker thuộc phạm vi.

## Cạm bẫy đã biết
Không dùng sự hiện diện trường chữ ký làm bằng chứng hợp lệ. Không ghi đè byte PDF. Không cho phép request cũ bỏ qua version hoặc session cũ bỏ qua khóa tài khoản. Kết quả local không chứng minh SLA sản xuất.

## Đã làm gì
(agent điền khi xong)
'''
    Path(f'docs/tasks/{tid}.md').write_text(text, encoding='utf-8')

Path('docs/tasks/INDEX.md').write_text('# Task cards\n\nFlow: [FLOW.md](FLOW.md). Conventions: [CONVENTIONS.md](CONVENTIONS.md).\n\n| Task | Mục tiêu | Dependency |\n|---|---|---|\n' + ''.join(f'| [T-{i:02d}](T-{i:02d}.md) | {t[0]} | '+ ('—' if i == 1 else f'T-{i-1:02d}') +' |\n' for i,t in enumerate(TASKS,1)) + '\nT-13 cần đầu vào trường; không được giả lập để nghiệm thu. Dependency tuyến tính loại trừ mọi conflict kể cả touches giao nhau.\n', encoding='utf-8')
