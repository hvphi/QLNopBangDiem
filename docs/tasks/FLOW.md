# Flow thực thi

`todo → in_progress → review → done`; `blocked` khi thiếu đầu vào cần thiết.

1. Chỉ lấy task khi mọi `depends_on` đã done. Đặt owner, started_at.
2. Kiểm tra touches không giao với task đang chạy. Triển khai tuần tự theo depends_on; không chạy agent song song. Nhánh local T-14 trở đi nối T-12, không phụ thuộc T-13 đang hoãn; hiện đã triển khai đến T-41, T-42 đồng bộ tài liệu.
3. Triển khai, chạy test được nêu trong card, cập nhật checklist và 3–5 dòng Đã làm gì; chuyển review và finished_at.
4. Review phạm vi, bảo mật và bằng chứng test. Chỉ chuyển done khi định nghĩa xong được chứng minh. Người triển khai có thể review tự động bằng test và kiểm tra code, không giả danh phê duyệt của người dùng.
5. Khi blocked, ghi rõ điều kiện mở khóa. Không đánh dấu đã tích hợp UIS/VGCA/cloud thật hay đạt tải sản xuất chỉ dựa trên fixture.

## Chống conflict

Chuỗi dependency tuyến tính là thứ tự thực thi chính thức. Những task sửa cùng backend/app.py hoặc frontend đều được serialize. T-12 chỉ kiểm thử/review sau khi toàn bộ tính năng đã hoàn thành. T-13 triển khai ngoài môi trường local phụ thuộc T-12 và đầu vào trường cung cấp.

## Yêu cầu hiện hành và lịch sử

PRD phiên bản 2.0 là mô tả hiện hành; prd_refs của card chỉ đến mục tương ứng. Card done giữ bằng chứng/mốc lịch sử; khi yêu cầu được thay thế, thêm ghi chú dẫn task mới thay vì sửa lịch sử kết quả. INDEX hiển thị status; T-13 giữ todo và ghi hoãn, không dùng blocked thay cho yêu cầu tạm hoãn của người dùng. Trước triển khai T-13 phải xác nhận phạm vi mới trong PRD và lập các dependency bổ sung cho file chung nếu tiếp tục phát triển local.
