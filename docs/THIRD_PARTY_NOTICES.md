# Thông báo thư viện bên thứ ba

Cập nhật 06/10/2026 (T-52). Kiểm kê toàn hệ thống ở [LICENSE_AUDIT.md](LICENSE_AUDIT.md), phiên bản và SHA-256 ở [dependency-licenses.json](dependency-licenses.json). [licenses/runtime](licenses/runtime/) chứa 90 file license/notice từ 52 gói Python và 3 công cụ Node đang cài.

## Nghĩa vụ khi bàn giao/phân phối

Giữ toàn bộ license, copyright và miễn trừ trách nhiệm tương ứng cùng thư viện, gồm component native. MIT/BSD/PSF có điều kiện cụ thể trong từng file. Apache-2.0 yêu cầu giữ license, NOTICE nếu có, các thông báo liên quan và ghi nhận file đã sửa khi áp dụng. [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).

certifi 2026.7.22 dùng MPL-2.0: giữ license/notice và đáp ứng yêu cầu nguồn Covered Software khi phân phối. Dùng nguồn đúng phiên bản bàn giao, không thay bằng nhánh mới nhất. [certifi upstream](https://github.com/certifi/python-certifi), [Mozilla MPL FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/).

**lxml cần xem xét trước đóng gói:** LICENSES.txt bản cài khai báo iconv LGPL-2.1 trong binary wheels, cùng test runner GPL và tài nguyên schema/XSL có điều kiện hoặc thiếu license. Cần xác định component/file bàn giao, cách liên kết và nghĩa vụ nguồn tương ứng. Bộ notices này chưa chứng minh hoàn tất mọi nghĩa vụ LGPL. [Thông báo upstream](https://github.com/lxml/lxml/blob/master/LICENSES.txt).

Sản phẩm sử dụng thành phần của FreeType Project (David Turner, Robert Wilhelm, Werner Lemberg) theo lựa chọn FreeType License. Giữ bản FTL và copyright/attribution cụ thể trong notices Pillow/PDFium, cùng thông báo của các tác giả khác trong bundle.

Giữ đầy đủ component licenses của Pillow/PDFium/cryptography và notices công cụ TypeScript/Playwright. Bản server/Linux khác bản Windows được kiểm tra cần kiểm kê lại exact wheel/build; Chromium và OS runtime chưa nằm trong kiểm kê này.

## Thư viện đọc PDF cho So Khớp (T-41)

Kiểm tra ngày 05/10/2026 từ metadata và giấy phép của các gói đang cài. Không thêm thư viện mới cho T-41. Nội dung PDF được đọc bằng pdfplumber/pdfminer.six, không sửa hay ký lại file.

| Gói đang dùng | Giấy phép | Bản giấy phép đi kèm |
| --- | --- | --- |
| pdfplumber 0.11.9 | MIT | licenses/pdfplumber/licenses/LICENSE.txt |
| pdfminer.six 20251230 | MIT | licenses/pdfminer.six/licenses/LICENSE |
| Pillow 12.3.0 (phụ thuộc pdfplumber) | MIT-CMU; các thành phần khác theo thông báo của Pillow | licenses/Pillow/licenses/LICENSE |
| pypdfium2 5.13.0 (phụ thuộc pdfplumber) | Apache-2.0 hoặc BSD-3-Clause cho wrapper; PDFium và thành phần binary có giấy phép riêng | licenses/pypdfium2/licenses/ |

Đã sao chép nguyên văn các giấy phép từ distribution vào docs/licenses, gồm thông báo của PDFium binary Windows và các thành phần đi kèm. Chức năng So Khớp chỉ dùng trích xuất bảng, không gọi renderer PDFium. Giữ các thông báo bản quyền/giấy phép này cùng thư viện khi phân phối; với binary của nền tảng khác, giữ cả thông báo kèm binary đó.

Nguồn chính thức: [pdfplumber MIT](https://github.com/jsvine/pdfplumber/blob/v0.11.9/LICENSE.txt), [pdfminer.six](https://github.com/pdfminer/pdfminer.six/blob/master/LICENSE), [Pillow](https://github.com/python-pillow/Pillow/blob/main/LICENSE), [pypdfium2](https://github.com/pypdfium2-team/pypdfium2#licensing).

Phần T-41 giữ lịch sử thư viện đọc PDF; kiểm kê toàn ứng dụng được bổ sung tại T-52. File nguồn daotao do cán bộ chọn; kết quả không xác thực nguồn xuất của file. Tài liệu này không cấp phép code riêng hay PDF/font người dùng đưa vào, và bộ license copies không phải chứng nhận tuân thủ đầy đủ.
