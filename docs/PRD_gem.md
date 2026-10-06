# PRD — VKU E-Gradebook

Phiên bản 2.1 · Cập nhật 06/10/2026 (Asia/Saigon). Phản ánh yêu cầu đã chốt và triển khai local đến T-50; tài liệu được rà soát tại T-51. Các thay đổi của người dùng thay thế giả định cũ về mã UIS, tài khoản, số chữ ký và nguồn so khớp. Tích hợp thật VKU/nghiệm thu sản xuất vẫn hoãn; snapshot và fixture không phải bằng chứng tích hợp thật.

## 1. Tổng quan sản phẩm

Quản lý GV nộp PDF đã ký số, TK ký phê duyệt, Phòng Đào tạo và Bảo đảm chất lượng (ĐT) kiểm tra/so khớp/duyệt lưu trữ. Người dùng ký bằng phần mềm bên ngoài; website xác minh và giữ nguyên PDF.

| Vai trò | Mã | Phạm vi |
| --- | --- | --- |
| Giảng viên (GV) | teacher | Lớp được phân công theo năm/kỳ và hồ sơ của mình |
| Trưởng khoa (TK) | head | Hồ sơ thuộc khoa, tải/ký/nộp phê duyệt hoặc trả lại |
| Phòng ĐT&BDCL (ĐT) | training | Tra cứu, so khớp, trả lại, duyệt/lưu trữ |
| Quản trị | admin | CRUD khoa/tài khoản, chứng thư, danh mục lớp, hạn và vận hành |

## 2. Luồng nghiệp vụ

1. GV đăng nhập bằng email trường/mật khẩu/vai trò, chọn năm học/kỳ để xem lớp mình dạy.
2. Chọn nút loại bảng điểm của lớp; xuất PDF từ daotao và ký bên ngoài theo §3.3.
3. Website đối chiếu quyền/môn/lớp/kỳ, xác minh chữ ký/toàn vẹn rồi lưu hồ sơ và phiên bản PDF; chuyển TK.
4. TK tải đúng PDF đã nộp, thêm chữ ký bằng incremental update và upload; website kiểm tra phần PDF cũ còn nguyên, đủ người ký rồi chuyển ĐT.
5. ĐT xem người ký, kiểm tra hồ sơ; có thể So Khớp với PDF xuất daotao. So Khớp không tự duyệt.
6. ĐT bấm Duyệt, website xác minh lại và lưu trữ; GV thấy Hoàn thành và ẩn nút tương ứng.
7. TK/ĐT trả có lý do: GV nộp lại đúng hồ sơ/loại nếu còn hạn. Giữ ID hồ sơ, tăng phiên bản và lưu lịch sử.

### 2.1. Trạng thái và nút

| Trạng thái lưu | GV | TK | ĐT |
| --- | --- | --- | --- |
| submitted | Chờ Trưởng khoa duyệt | Chưa ký | Chờ trưởng khoa |
| head_signed | Chờ Đào tạo duyệt | Chờ Đào tạo | Đang chờ P.ĐT duyệt |
| rejected | Đã trả lại và lý do | Đã trả lại | Đã trả lại |
| archived | Hoàn thành | Đã lưu trữ | Đã lưu |

Nút GV còn hiển thị nhưng disabled khi pending; rejected enable lại nếu còn hạn; archived ẩn nút, giữ tên loại/Hoàn thành. Các loại độc lập. Nhiều hồ sơ cùng loại chỉ coi hoàn thành khi tất cả đã lưu trữ. ĐT: head_signed có Duyệt enabled, archived có Duyệt disabled với Đã lưu phía dưới; submitted/rejected không có nút duyệt lưu trữ.

## 3. Yêu cầu chức năng

### 3.1. Tài khoản và đăng nhập

- **FR-AUTH-01:** Trang đăng nhập cho chọn GV/TK/ĐT/admin. Domain email chính xác vku.udn.vn; chỉ nhận vai trò của tài khoản active, lựa chọn không tự cấp quyền.
- **FR-AUTH-02:** Một email có nhiều tài khoản vai trò với ID riêng; đăng nhập theo email/vai trò. DS ghi GV, TK được cấp hai vai trò độc lập. Đồng bộ giữ ID liên kết lớp/hồ sơ.
- **FR-AUTH-03:** Công cụ import danh sách GV/Excel: bỏ học hàm/học vị và dấu, ghép chữ đầu họ/tên đệm với tên cuối (Đặng Quang Hiển → dqhien; Hà Thị Minh Phương → htmphuong). Trùng email thêm hậu tố số theo lựa chọn người dùng; tạo mật khẩu ngẫu nhiên 8 ký tự và xuất Excel. Form admin vẫn có chính sách mật khẩu riêng.
- **FR-AUTH-04:** Băm mật khẩu; không ghi mật khẩu/khóa/file danh sách tài khoản chứa mật khẩu vào PRD, task card hoặc nhật ký công khai.

### 3.2. Lớp học phần và nộp bảng điểm

- **FR-GV-01:** Nhập danh mục hoặc snapshot thời khóa biểu đã đọc; dashboard lọc năm/kỳ và chỉ liệt kê lớp được phân công. Chưa truy vấn VKU trực tiếp khi đăng nhập.
- **FR-GV-02:** Một lớp nhận nhiều hồ sơ và loại bảng điểm độc lập. Tên lớp chứa Đồ án/Đề án/Thực tập/Kiến tập: Nộp điểm hướng dẫn, Nộp điểm Hội đồng; lớp còn lại: Nộp điểm thành phần, Nộp điểm Cuối kỳ. Hướng dẫn dùng component, Hội đồng dùng final trong dữ liệu hiện có. Nhãn TP/HD cũ được thay bởi quy tắc này.
- **FR-GV-03:** Nút chọn xác định lớp/loại. Form upload bỏ loại bảng điểm, tên tùy ý và cách nộp. Nộp lại gắn đúng hồ sơ bị trả/version, không tạo hồ sơ thay thế.
- **FR-GV-04:** Đối chiếu header PDF theo môn, lớp/nhóm, năm/kỳ với danh mục GV được dạy. Không bắt buộc mã tài liệu UIS hoặc mã lớp nội bộ TKB xuất hiện trong PDF; sai môn/lớp/kỳ hoặc thiếu thông tin vẫn bị từ chối. Không chỉnh PDF đã ký để bổ sung mã.
- **FR-GV-05:** Trạng thái/nút theo §2.1; từng loại độc lập, nộp lại giữ ID/lịch sử/lý do.

### 3.3. Chữ ký số và người ký

- **FR-SIGN-01:** GV phụ trách đúng lớp/kỳ phải ký. Cuối kỳ lớp thông thường cần hai GV khác nhau trước gửi TK và một chữ ký TK trước lưu (ba chữ ký theo vai trò). GV thứ hai là teacher active nhận diện duy nhất từ chứng thư, không cần dạy môn/lớp/kỳ đó hoặc cùng khoa, không bắt buộc phân công trước. Snapshot người ký thứ hai thật vào hồ sơ.
- **FR-SIGN-02:** Thành phần và lớp đặc biệt ở FR-GV-02 giữ một GV + một TK. GV kiêm TK được dùng cùng chứng thư hợp lệ cho hai vai trò nhưng vẫn cần hai lần ký. Ngoại lệ không thay thế hai GV khác nhau của cuối kỳ thông thường.
- **FR-SIGN-03:** TK phải giữ nguyên PDF GV và thêm chữ ký bằng incremental update. Kiểm tra mật mã, toàn vẹn, coverage/diff và đúng người ký mỗi bước/khi lưu; không chỉ đếm trường chữ ký hay đọc tên hiển thị.
- **FR-SIGN-04:** Strict kiểm tra trust/thu hồi/fingerprint đã liên kết. Local theo yêu cầu kiểm tra mật mã/toàn vẹn và nhận diện fingerprint hoặc email chứng thư trong điều kiện hỗ trợ; ghi rõ CA/thu hồi chưa xác minh. Local không phải nghiệm thu PKI/VGCA production.
- **FR-SIGN-05:** Hiển thị tên/email chứng thư từ báo cáo PDF trong hồ sơ/cột Giảng viên/Khoa. Trả/lưu tăng workflow version nhưng không sinh PDF mới; lấy chữ ký ở PDF gần nhất <= version hồ sơ, không suy từ người upload.

### 3.4. Trưởng khoa

- **FR-TK-01:** Danh sách theo khoa, submitted là Chưa ký; xem PDF/người ký và tải nguyên bản.
- **FR-TK-02:** Upload bản thêm chữ ký theo §3.3 để chuyển ĐT hoặc trả có lý do. Máy chủ kiểm tra quyền/hạn/state/version.
- **FR-TK-03:** Đồng bộ CSRF khi phiên đổi giữa các tab. Cùng identity cập nhật token; đổi tài khoản/vai trò dừng mutation. Chỉ retry một lần đúng lỗi CSRF trước handler; không bỏ CSRF hoặc retry lỗi nghiệp vụ.

### 3.5. Phòng Đào tạo và Bảo đảm chất lượng

- **FR-DT-01:** Lọc từ khóa/năm/kỳ/khoa/state/loại. Khoa dropdown từ danh mục Khoa/Đơn vị dùng cho thống kê và các đơn vị có lớp. Cột Giảng viên/Khoa hiển thị người ký PDF.
- **FR-DT-02:** Duyệt trong cột Trạng thái lưu ngay hồ sơ head_signed, xác minh PDF/chữ ký/version. Archived: Duyệt disabled, Đã lưu dưới nút. Có thể trả hồ sơ có lý do.
- **FR-DT-03:** Cột So Khớp ngay sau Trạng thái, chỉ training. Chọn PDF xuất daotao, xác nhận đúng môn/lớp/kỳ/loại và ghép cột với PDF đã ký. Nguồn không cần chữ ký; chưa kết nối trực tiếp. Backend giữ XLSX/CSV tương thích T-40, giao diện mặc định PDF theo T-41.
- **FR-DT-04:** So theo MSSV/Số thẻ (có dấu chấm như 22IT.B019), số thập phân dấu phẩy/chấm; 0 khác trống. Báo lệch/thiếu/thừa/thiếu giá trị. Thiếu cột/điểm không kết luận khớp toàn bộ; trùng/mơ hồ/PDF hỏng/không trích đầy đủ báo lỗi. Chưa OCR PDF scan.
- **FR-DT-05:** Đổi file xóa kết quả/ghép cột và xác nhận lại. Không sửa PDF/điểm, không tự duyệt hoặc xác thực nguồn daotao. Nguồn xử lý tạm; audit chỉ kết quả tổng hợp/version, không MSSV/điểm. Kiểm tra quyền/CSRF/version và kiểm tra version lại trước audit.
- **FR-DT-06 — Người dùng tạm dừng, chưa triển khai (T-43):** Nút So Khớp trực tiếp lấy điểm hiện tại từ daotao bằng nguồn có quyền được xác nhận, đối chiếu đúng môn/lớp/nhóm/năm/kỳ/loại và ghi rõ thời điểm lấy. Chỉ tiếp tục khi người dùng mở lại và cung cấp tài liệu/cấu hình API của trường; không coi mở tab daotao hoặc PDF upload là kết nối trực tiếp. Yêu cầu này mở riêng phần lấy điểm thật, các hạng mục sản xuất khác ở T-13 vẫn hoãn.
- **FR-DT-07 (T-45, 06/10/2026):** Bảng thống kê theo khoa ở dashboard ĐT: tên khoa và lớp đã nộp/tổng số lớp học phần, kèm tổng cộng. Lớp có ít nhất một hồ sơ (kể cả bị trả) được tính một lần, không phải số bảng điểm/số môn duy nhất/số đã duyệt hoặc đã đủ hai loại. Mẫu số gồm mọi lớp trong danh mục cùng năm/kỳ/khoa, kể cả chưa nộp; không phụ thuộc trang/từ khóa/trạng thái/loại trong danh sách hồ sơ. API chỉ training.

Danh mục thống kê/dropdown ĐT bổ sung T-46: CNTT — Khoa Khoa học máy tính; KTMT — Khoa Kỹ thuật máy tính và Điện tử; KTS — Khoa Kinh tế số và Thương mại điện tử; AIDS — Khoa Trí tuệ nhân tạo và Khoa học dữ liệu; CB — Tổ Cơ bản. Luôn hiện đủ 5 đơn vị khi chọn tất cả, kể cả 0/0 trong kỳ không có lớp; chọn một khoa chỉ hiển thị khoa đó. Mã danh mục theo tài khoản đã nhập, không tự chuyển phân công lớp/GV. Đơn vị ngoài danh mục nếu có vẫn giữ dòng/count để không mất dữ liệu tổng.

**Nguồn danh mục lớp theo khoa (T-47, 06/10/2026):** Đọc thời khóa biểu công khai daotao và Excel tài khoản do người dùng cung cấp. Ghép họ tên GV bỏ học hàm/khoảng trắng, cho phép bỏ dấu khi tên duy nhất; lấy khoa từ Excel và liên kết đến tài khoản teacher đang hoạt động theo email, không suy quyền hay thay mật khẩu. Gom các buổi cùng tên lớp/nhóm và GV thành một lớp. Cùng tên lớp nhưng khác GV giữ phân công riêng và báo cáo đối chiếu; không gom chỉ theo tên môn. Kiểm tra năm/kỳ đang chọn trên trang nguồn. Nhập lại không nhân đôi, giữ mã lớp, hồ sơ và phiên bản PDF đã có; sao lưu trước nhập. Tên thiếu/trùng, khoa chưa xác định hoặc tài khoản không khớp được giữ riêng trong báo cáo, không tự đoán khoa. Lần đồng bộ local HK1 2026–2027 có 1.617 lớp xác định khoa; 28 lớp Bank Agribank chưa xác định khoa. Đây là bản chụp nguồn, không phải đồng bộ API so khớp điểm đang hoãn.

**Chi tiết khoa (T-48):** Mỗi dòng thống kê có nút Chi tiết. Chỉ P.Đào tạo được xem API/dialog theo khoa được chọn và năm/kỳ đang lọc. Hiển thị tên/email GV, số lớp đã nộp/tổng lớp từng GV, mở danh sách lớp gồm tên, mã, năm/kỳ và đã nộp/chưa nộp; có tìm GV/email/tên lớp/mã lớp. Khoa không có lớp báo rỗng. Lấy dữ liệu live từ courses/submissions/users, không tải báo cáo Markdown cố định; đếm mỗi lớp một lần kể cả nhiều hồ sơ/loại hoặc bị trả. Không trả thông tin xác thực, không sửa lớp/hồ sơ.

**Chọn kỳ thống kê (T-49):** Hai combo Năm học/Học kỳ đặt ngay trên bảng thống kê. Danh mục năm từ lớp hiện có, có Tất cả năm học; học kỳ gồm Tất cả, 1, 2 và hè. Đổi lựa chọn tự cập nhật thống kê/danh sách, quay về trang 1; đồng bộ hai chiều với bộ lọc danh sách khi bấm Lọc. Nút Chi tiết dùng đúng năm/kỳ của thống kê. Kỳ không có lớp vẫn hiện đủ 5 đơn vị 0/0; dữ liệu từ yêu cầu cũ không ghi đè khi đổi lựa chọn nhanh.

### 3.6. Quản trị và vận hành

**Quản trị khoa/tài khoản (T-50):** Admin CRUD danh mục Khoa/Đơn vị: mã ổn định, sửa tên và tùy chọn hiển thị thống kê; chỉ xóa đơn vị chưa có tài khoản/lớp. Danh mục được lưu DB, khởi tạo một lần từ 5 đơn vị thống kê và các đơn vị cũ; không tự tạo lại mục đã xóa khi restart. Tên khoa thống kê và combobox tài khoản/lớp dùng danh mục động. Danh sách tài khoản hỗ trợ tìm kiếm, sửa họ tên/email/vai trò/khoa, trạng thái, fingerprint và mật khẩu mới (bỏ trống giữ nguyên). Cùng email được phép nhiều vai trò nhưng không trùng email–vai trò. Cấm tự xóa/khóa/bỏ vai trò admin của tài khoản đang dùng; cấm xóa tài khoản có lớp/hồ sơ/audit, cấm đổi vai trò đã liên kết hoặc đổi khoa GV phá phân công. Khóa là lựa chọn khi cần ngừng tài khoản có lịch sử. Sửa tài khoản hủy phiên cũ, sửa chính mình phải đăng nhập lại. Admin-only/CSRF/audit không secrets, không trả password và không xóa dây chuyền bảng điểm.

- **FR-ADMIN-01:** Quản lý tài khoản/active/vai trò/fingerprint, lớp/GV/khoa/năm/kỳ/hạn. Mapping UIS/GV thứ hai cũ chỉ tham khảo theo FR-GV-04/FR-SIGN-01.
- **FR-ADMIN-02:** Nhật ký/vận hành và backup/restore local. Kho trường/lịch backup ngoài/hạ tầng production thuộc T-13 chưa nghiệm thu.
- **FR-ADMIN-03:** T-31 xóa bảng điểm tài khoản theo yêu cầu cụ thể là thao tác quản trị một lần; không cấp quyền xóa cho GV hoặc tự xóa khi đăng nhập.

## 4. Yêu cầu phi chức năng


- **NFR-01:** RBAC/scope tại server, phiên/CSRF/băm mật khẩu/rate limit/giới hạn upload. Hết hạn GV/TK xem/tải, ĐT tiếp tục xử lý. HTTPS/TLS cần production; localhost hiện HTTP phát triển.
- **NFR-02:** AES-GCM/khóa ngoài mã nguồn/hash, phân loại năm/kỳ/khoa/lớp; SQLite/kho local. Backup/restore local đã kiểm thử; lịch backup/kho trường chưa nghiệm thu.
- **NFR-03:** Giữ byte PDF và audit/versions, không chuyển đổi/in/scan/chỉnh PDF đã ký. Version chống ghi đè; workflow version có thể không có PDF mới.
- **NFR-04:** Mục tiêu production <3 giây/file và hàng nghìn yêu cầu đồng thời cần đo thật, chưa chứng minh bằng SQLite một nút/fixture. Upload 20 MiB; So Khớp tối đa 100 trang PDF/5.000 SV.
- **NFR-05:** Giấy phép thư viện phù hợp, giữ bản quyền/notice khi phân phối. So Khớp dùng pdfplumber/pdfminer.six MIT; giấy phép và phụ thuộc lưu ở [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) và docs/licenses. Không thêm thư viện thương mại cần giấy phép chưa cấp cho T-41.

## 5. Kiến trúc và tích hợp

| Thành phần | Đang triển khai local | Còn cần đầu vào/nghiệm thu |
| --- | --- | --- |
| Backend/frontend | FastAPI/JavaScript ES modules/checkJs | Hạ tầng production, đo tải/giám sát |
| Database/kho | SQLite, PDF mã hóa, audit/versions, backup/restore local | Kho trường/lịch backup/mở rộng hạ tầng |
| Chữ ký | pyHanko, strict/local, test ký mật mã | CA/CRL/OCSP và chứng thư trường đầy đủ |
| Daotao/UIS | Danh mục/snapshot, đối chiếu header | API/SSO/kết nối thật theo cho phép của trường |
| So Khớp | PDF cán bộ chọn, trích bảng bằng pdfplumber/pdfminer.six | Không OCR/chưa lấy điểm trực tiếp |
| Ký số | Người dùng ký bên ngoài, website nhận PDF | Không ký thay người dùng |

## 6. Tiêu chí chấp nhận và bằng chứng

1. Cùng email đăng nhập từng vai trò được cấp, role/scope sai bị chặn tại máy chủ.
2. GV thấy đúng lớp/kỳ, nút theo tên lớp; nộp đúng môn/lớp/kỳ không cần mã UIS. Pending khóa, rejected mở nộp lại, archived ẩn.
3. Cuối kỳ thường có hai GV khác nhau + TK, GV thứ hai không cần dạy lớp; GV kiêm TK được nhận theo chính sách.
4. TK incremental update giữ nguyên bản GV; chữ ký sai/thiếu/PDF sửa bị chặn, local ghi rõ giới hạn trust/thu hồi.
5. ĐT Duyệt lưu ngay hồ sơ chờ, nút disabled/Đã lưu dưới sau xong; người ký còn sau trả/lưu.
6. So Khớp PDF hiển thị lệch/thiếu/thừa, không báo khớp khi thiếu dữ liệu, không đổi PDF/điểm/state.
7. Trả/nộp lại/CSRF/phiên/version đúng; PDF tải nguyên bản, kho mã hóa.

Bằng chứng theo từng task: [TEST_REPORT.md](TEST_REPORT.md), [INDEX.md](tasks/INDEX.md), tests. T-41 đạt 14 parser/API tests, typecheck và E2E; không suy mọi test lịch sử đã chạy cùng lúc hoặc production/SLA đã đạt.

## 7. Truy vết yêu cầu và thay thế

- T-01…T-12: nền tảng local. T-13: tích hợp/nghiệm thu thật, todo/hoãn theo yêu cầu.
- T-14…T-20: PDF/chữ ký local, nhiều hồ sơ, người ký và GV kiêm TK. Mapping mã UIS T-15…T-17 được T-24 thay thế.
- T-21…T-27/T-30: chọn vai trò/cùng email, lớp theo kỳ, form/nút nộp và danh sách account Excel. Nhãn TP/HD trước đây thay bởi T-28.
- T-28…T-39: nhãn/chữ ký cuối kỳ, trạng thái/nộp lại/CSRF, GV thứ hai, ĐT Duyệt/người ký. T-36 thay điều kiện phân công GV thứ hai của T-28; T-33/T-35 thay hành vi nút/trạng thái T-29.
- T-40…T-41: dropdown Khoa/So Khớp; T-41 chuyển nguồn UI Excel/CSV sang PDF và lưu giấy phép.
- T-42: đồng bộ PRD/cards, giữ lịch sử và phân biệt local với hạng mục hoãn.

Card done ghi nhận kết quả lúc triển khai; ghi chú thay thế nêu yêu cầu hiện hành, không xóa lịch sử/mốc hoàn thành. Task mới nối dependency và kiểm tra touches tránh sửa chung file đồng thời.

- T-43: API so khớp điểm trực tiếp tạm dừng theo người dùng; T-44: Cloudflare hoãn, dự kiến server VKU sau.
- T-45…T-46: thống kê theo khoa, đủ 4 khoa và Tổ Cơ bản.
- T-47: nhập lớp từ thời khóa biểu ghép tên GV với tài khoản/khoa; báo cáo ngoại lệ, giữ mã và hồ sơ.
- T-48…T-49: Chi tiết khoa/GV/lớp và combo năm học/học kỳ đồng bộ phạm vi.
- T-50: CRUD khoa/tài khoản, combobox khoa, bảo toàn liên kết và lịch sử.
- T-51: rà soát phiên bản, trạng thái và truy vết tài liệu đến T-50.
