# Thư viện đọc PDF cho So Khớp

Kiểm tra ngày 05/10/2026 từ metadata và giấy phép của các gói đang cài. Không thêm thư viện mới cho T-41. Nội dung PDF được đọc bằng pdfplumber/pdfminer.six, không sửa hay ký lại file.

| Gói đang dùng | Giấy phép | Bản giấy phép đi kèm |
| --- | --- | --- |
| pdfplumber 0.11.9 | MIT | licenses/pdfplumber/licenses/LICENSE.txt |
| pdfminer.six 20251230 | MIT | licenses/pdfminer.six/licenses/LICENSE |
| Pillow 12.3.0 (phụ thuộc pdfplumber) | MIT-CMU; các thành phần khác theo thông báo của Pillow | licenses/Pillow/licenses/LICENSE |
| pypdfium2 5.13.0 (phụ thuộc pdfplumber) | Apache-2.0 hoặc BSD-3-Clause cho wrapper; PDFium và thành phần binary có giấy phép riêng | licenses/pypdfium2/licenses/ |

Đã sao chép nguyên văn các giấy phép từ distribution vào docs/licenses, gồm thông báo của PDFium binary Windows và các thành phần đi kèm. Chức năng So Khớp chỉ dùng trích xuất bảng, không gọi renderer PDFium. Giữ các thông báo bản quyền/giấy phép này cùng thư viện khi phân phối; với binary của nền tảng khác, giữ cả thông báo kèm binary đó.

Nguồn chính thức: [pdfplumber MIT](https://github.com/jsvine/pdfplumber/blob/v0.11.9/LICENSE.txt), [pdfminer.six](https://github.com/pdfminer/pdfminer.six/blob/master/LICENSE), [Pillow](https://github.com/python-pillow/Pillow/blob/main/LICENSE), [pypdfium2](https://github.com/pypdfium2-team/pypdfium2#licensing).

Tài liệu này ghi nhận các thư viện thuộc luồng đọc PDF của So Khớp, không thay thế kiểm kê giấy phép toàn bộ ứng dụng. File nguồn daotao do cán bộ chọn; kết quả không xác thực nguồn xuất của file.
