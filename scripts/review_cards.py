"""Record consolidated local review only after typecheck, API and E2E passed."""
from pathlib import Path
from scripts.task_flow import transition

NOTES = [
('Đã chốt FastAPI, SQLite, vault AES-GCM và frontend checkJs.', 'Đã tạo 13 card đúng template, dependency tuyến tính.', 'Đã bổ sung FLOW/CONVENTIONS và scripts chạy/check.', 'Review: typecheck, template/dependency và tổng hợp kiểm thử xanh.'),
('Đã tạo users/courses/sessions/submissions/versions/audit/settings.', 'Đã lưu PDF AES-GCM trong cây Năm/HK/Khoa/LHP.', 'Giữ nguyên byte, gắn hash và chặn đường dẫn vượt kho.', 'Review: test workflow, encrypted storage và restore xanh.'),
('Đã kiểm tra domain trường, hash scrypt và session server-side.', 'Đã bật cookie HttpOnly/SameSite và CSRF trên mutation.', 'Scope theo GV/khoa; khóa tài khoản hủy session cũ.', 'Review: test domain, RBAC, CSRF và locked-session xanh.'),
('Đã đối chiếu header năm/HK/tên/mã bằng nội dung PDF.', 'Đã hỗ trợ mapping UIS document ID theo mẫu PDF trong repo.', 'Đã đọc PDF nguồn trong UIS_EXPORT_DIR và chuẩn hóa tên tải.', 'Review: test source export giữ nguyên byte, sai header và sample mapping xanh; không kết nối UIS thật.'),
('Đã dùng pyHanko kiểm tra mật mã, coverage, diff, CA và thu hồi.', 'Đã liên kết fingerprint chứng thư theo đúng người và thứ tự ký.', 'Policy chỉ cho bổ sung chữ ký/PKI; từ chối sửa form điểm.', 'Review: PDF ký thật một/hai chữ ký, tamper, revoked/untrusted, sai signer đều kiểm chứng.'),
('Đã triển khai upload GV, theo dõi, xem/tải và nộp lại.', 'Kiểm tra lớp, metadata, chữ ký và hạn nộp tại máy chủ.', 'Lưu phiên bản mới cùng audit; duplicate/stale request trả 409.', 'Review: test GV scope, resubmit và deadline xanh.'),
('Đã triển khai TK xem/tải và trả lại với lý do bắt buộc.', 'PDF lần hai phải giữ prefix bản GV và đủ hai signer riêng.', 'Đã dùng transaction/version chống quyết định ghi đè đồng thời.', 'Review: test scope khoa, original bytes, lý do và race [200,409] xanh.'),
('Đã tiếp nhận và revalidate đủ hai chữ ký khi lưu trữ.', 'Đã thêm tra cứu nhiều bộ lọc, phân trang và PDF version.', 'Archived bất biến; dữ liệu giữ theo cây kho và audit.', 'Review: full workflow, revalidation và combined search xanh.'),
('Đã có CLI bootstrap admin, không mật khẩu mặc định.', 'Đã thêm quản lý tài khoản, chứng thư, danh mục và thời hạn.', 'Dữ liệu admin được validation và audit; không tự cấp quyền từ email.', 'Review: admin create/update/deadline/locked-account và E2E xanh.'),
('Đã backup online SQLite cùng vault, loại session và ghi manifest.', 'Đã restore kiểm tra checksum/integrity/reference vào thư mục mới.', 'Đã thêm periodic job, manual backup, giới hạn body và slot PKI.', 'Review: backup/restore, corrupt/absolute manifest, periodic/manual backup và upload limit xanh; TLS/kho trường chưa thuộc phạm vi local.'),
('Đã có giao diện tiếng Việt cho GV, TK, ĐT và admin.', 'Đã nối upload, preview/tải PDF, decisions, search và backup status.', 'Đã hỗ trợ mobile, labels và xử lý lỗi/version conflict.', 'Review: E2E Chromium full workflow/admin/deadline/mobile xanh; đã xem ảnh giao diện.'),
('Đã kiểm thử bằng CA/leaf/CRL và PDF ký mật mã thực trong thư mục tạm.', 'Đã kiểm tra toàn bộ flow, quyền, integrity, deadline, race và restore.', 'Đã chạy typecheck, API test và Chromium E2E; ghi TEST_REPORT/README.', 'Review: phạm vi local hoàn thành; kết nối VKU thật tạm hoãn theo người dùng.'),
]
INPUTS = [
['docs/PRD_gem.md','docs/tasks/_TEMPLATE.md'],
['requirements.txt','docs/tasks/CONVENTIONS.md'],
['backend/db.py','backend/storage.py'],
['backend/db.py','backend/auth.py','bang-diem-CK_N1.signed.pdf'],
['backend/uis.py','requirements.txt'],
['backend/db.py','backend/storage.py','backend/auth.py','backend/uis.py','backend/verification.py'],
['backend/app.py','backend/verification.py','backend/storage.py'],
['backend/app.py','backend/db.py','backend/verification.py'],
['backend/app.py','backend/auth.py','backend/db.py'],
['backend/db.py','backend/storage.py','backend/app.py'],
['backend/app.py','frontend/index.html','package.json'],
['backend/','frontend/','scripts/run.py','docs/tasks/INDEX.md'],
]
for i,(notes,inputs) in enumerate(zip(NOTES,INPUTS),1):
    tid=f'T-{i:02d}'
    path=Path('docs/tasks',tid+'.md')
    text=path.read_text(encoding='utf-8')
    # Leave original scope and template untouched; spell out actual consumed files.
    text=text.replace('## Đầu vào đã có\n','## Đầu vào đã có\n'+''.join(f'- `{p}`.\n' for p in inputs))
    path.write_text(text,encoding='utf-8')
    transition(tid,'in_progress')
    transition(tid,'review', '\n'.join('- '+line for line in notes))
    transition(tid,'done')
path=Path('docs/tasks/T-13.md')
text=path.read_text(encoding='utf-8').replace('(agent điền khi xong)',
    '- Đã ghi đầu vào và checklist nghiệm thu ở `docs/DEPLOYMENT.md`.\n'
    '- Người dùng xác nhận chưa cần kết nối thật với VKU ngày 04/10/2026.\n'
    '- Giữ status todo cho giai đoạn sau; không thuộc phạm vi local hiện tại.\n'
    '- Chưa triển khai hạ tầng ngoài hoặc công bố đạt SLA production.')
path.write_text(text,encoding='utf-8')
