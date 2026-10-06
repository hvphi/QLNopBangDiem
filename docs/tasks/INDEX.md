# Task cards

Flow: [FLOW.md](FLOW.md). Conventions: [CONVENTIONS.md](CONVENTIONS.md).

| Task | Mục tiêu | Dependency | Trạng thái |
|---|---|---|---|
| [T-01](T-01.md) | Thiết lập kiến trúc và flow triển khai | — | done |
| [T-02](T-02.md) | Xây dựng dữ liệu, kho mã hóa và nhật ký | T-01 | done |
| [T-03](T-03.md) | Xây dựng đăng nhập và phân quyền | T-02 | done |
| [T-04](T-04.md) | Đối chiếu UIS và cung cấp bảng điểm xuất | T-03 | done |
| [T-05](T-05.md) | Xác thực chữ ký PDF với pyHanko | T-04 | done |
| [T-06](T-06.md) | Triển khai gửi và theo dõi bảng điểm của GV | T-05 | done |
| [T-07](T-07.md) | Triển khai phê duyệt và nộp lần hai của TK | T-06 | done |
| [T-08](T-08.md) | Tiếp nhận, lưu trữ và tra cứu kho | T-07 | done |
| [T-09](T-09.md) | Quản lý người dùng, danh mục và thời hạn | T-08 | done |
| [T-10](T-10.md) | Bảo vệ vận hành và sao lưu phục hồi | T-09 | done |
| [T-11](T-11.md) | Xây dựng giao diện cho bốn vai trò | T-10 | done |
| [T-12](T-12.md) | Kiểm thử tích hợp và review toàn bộ flow | T-11 | done |
| [T-13](T-13.md) | Kết nối trường và nghiệm thu triển khai sản xuất | T-12 | todo (hoãn) |

T-01…T-12 là phạm vi triển khai local. T-13 giữ todo và tạm hoãn theo yêu cầu người dùng ngày 04/10/2026: chưa cần kết nối thật với VKU. Không giả lập để nghiệm thu. Dependency tuyến tính loại trừ conflict kể cả touches giao nhau.

| Task bổ sung | Mục tiêu | Dependency | Trạng thái |
|---|---|---|---|
| [T-14](T-14.md) | Sửa xác thực VGCA và nhận diện người ký khi chạy local | T-12 | done |
| [T-15](T-15.md) | Một lớp nhận nhiều bảng điểm, nộp lại từng hồ sơ và mapping theo loại | T-14 | done |
| [T-16](T-16.md) | Danh sách mã UIS theo loại và cấu hình CSDL01 nhận hai mẫu | T-15 | done |
| [T-17](T-17.md) | Nhận diện URL giữa kỳ của bảng điểm thành phần | T-16 | done |
| [T-18](T-18.md) | Hiển thị người ký khi GV gửi và trên danh sách trưởng khoa | T-17 | done |
| [T-19](T-19.md) | Cho phép GV kiêm trưởng khoa dùng cùng chứng thư ở hai bước | T-18 | done |
| [T-20](T-20.md) | Chữ ký VGCA hiển thị và tag PDF sau certification | T-19 | done |
| [T-21](T-21.md) | Chọn vai trò khi đăng nhập, đối chiếu quyền tài khoản | T-20 | done |
| [T-22](T-22.md) | Một email cho nhiều vai trò, giữ IDs và quyền hồ sơ | T-21 | done |
| [T-23](T-23.md) | Lớp GV theo kỳ và nút Nộp điểm, import snapshot đã đọc | T-22 | done |
| [T-24](T-24.md) | Đối chiếu môn/lớp/kỳ từ header PDF, không yêu cầu mã UIS | T-23 | done |
| [T-25](T-25.md) | Hai nút nộp điểm thành phần/cuối kỳ cho từng lớp | T-24 | done |
| [T-26](T-26.md) | Bỏ loại/tên/cách nộp trên form, giữ nộp lại từ danh sách | T-25 | done |
| [T-27](T-27.md) | Tạo tài khoản GV theo quy tắc email và xuất Excel | T-26 | done |
| [T-28](T-28.md) | Nhãn theo loại lớp và cuối kỳ có hai GV khác nhau + TK | T-27 | done |
| [T-29](T-29.md) | Khóa nút và hiển thị Đã nộp riêng từng loại/lớp | T-28 | done |
| [T-30](T-30.md) | Cập nhật Excel, tách GV/TK và thêm Nguyễn Thị Thùy Giang ĐT | T-29 | done |
| [T-31](T-31.md) | Xóa bảng điểm đã nộp của Hồ Văn Phi theo yêu cầu | T-30 | done |
| [T-32](T-32.md) | Nhãn Chưa ký cho Trưởng khoa | T-31 | done |
| [T-33](T-33.md) | Tiến trình duyệt GV và ẩn nút khi hoàn thành | T-32 | done |
| [T-34](T-34.md) | Đồng bộ phiên CSRF và bảo vệ thao tác trả hồ sơ | T-33 | done |
| [T-35](T-35.md) | Mở nút Nộp điểm và chọn nộp lại khi bị trả | T-34 | done |
| [T-36](T-36.md) | GV ký thứ hai không cần dạy lớp hoặc phân công trước | T-35 | done |
| [T-37](T-37.md) | Duyệt/lưu từ cột trạng thái Phòng Đào tạo | T-36 | done |
| [T-38](T-38.md) | Đặt Đã lưu dưới nút Duyệt | T-37 | done |
| [T-39](T-39.md) | Giữ thông tin người ký trong danh sách khi trả/lưu | T-38 | done |
| [T-40](T-40.md) | Dropdown Khoa và so khớp PDF với Excel/CSV xuất daotao | T-39 | done |
| [T-41](T-41.md) | So khớp với PDF xuất từ daotao, lưu giấy phép thư viện | T-40 | done |
| [T-42](T-42.md) | Đồng bộ PRD và task cards với triển khai hiện tại | T-41 | done |
| [T-43](T-43.md) | So khớp trực tiếp bảng điểm từ daotao | T-42 | blocked (người dùng tạm dừng) |
| [T-44](T-44.md) | Triển khai Cloudflare theo đích được xác nhận | T-42 | todo (hoãn; dự kiến server VKU) |
| [T-45](T-45.md) | Thống kê lớp đã nộp bảng điểm theo khoa cho ĐT | T-42 | done |
| [T-46](T-46.md) | Hiển thị đủ bốn khoa và Tổ Cơ bản | T-45 | done |
| [T-47](T-47.md) | Đồng bộ lớp theo khoa từ thời khóa biểu và danh sách tài khoản | T-46 | done |
| [T-48](T-48.md) | Xem chi tiết lớp và giảng viên theo khoa | T-47 | done |
| [T-49](T-49.md) | Chọn năm học và học kỳ ngay trên bảng thống kê | T-48 | done |
| [T-50](T-50.md) | Quản lý CRUD khoa và tài khoản trường | T-49 | done |
| [T-51](T-51.md) | Đồng bộ PRD và task cards đến CRUD quản trị | T-50 | done |
| [T-52](T-52.md) | Kiểm kê giấy phép thư viện và thông báo bản quyền | T-51 | done |
| [T-53](T-53.md) | Quản lý hồ sơ cá nhân và đổi mật khẩu | T-52 | done |
| [T-54](T-54.md) | Chọn khoa nhận bảng điểm khi GV nộp | T-53 | done |

T-14 chạy sau T-12 và không phụ thuộc T-13 đang tạm hoãn; không có task triển khai song song.

## Cách đọc trạng thái và yêu cầu hiện tại

PRD [phiên bản 2.3](../PRD_gem.md) và prd_refs của từng card mô tả yêu cầu hiện hành. T-01…T-12, T-14…T-42 và T-45…T-54 đã done theo phạm vi local/tài liệu. T-13 todo/hoãn; T-43 blocked do người dùng tạm dừng API so khớp; T-44 todo/hoãn Cloudflare, dự kiến server VKU sau. Các card cũ giữ kết quả lịch sử, có ghi chú khi được card sau thay thế (mã UIS T-24, chữ ký T-36, nút/status T-33/T-35, PDF so khớp T-41). Bằng chứng kiểm thử theo từng lần chạy tại [TEST_REPORT.md](../TEST_REPORT.md); chưa nghiệm thu kết nối trường/SLA production.
