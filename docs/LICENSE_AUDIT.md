# Kiểm kê giấy phép thư viện

Ngày kiểm tra: 06/10/2026. Môi trường Windows, Python 3.12.14; resolver `scripts/run.py` ưu tiên `.local/packages`.

## Kết quả

Đã kiểm kê 52 gói Python trong cây phụ thuộc hoạt động và 3 công cụ Node. Các thư viện chính có giấy phép nguồn mở; chưa thấy SDK thương mại yêu cầu mua license trong imports/manifest đã kiểm tra. Tuy nhiên **chưa thể xác nhận toàn bộ bản đóng gói đáp ứng bản quyền**: lxml có thông báo native LGPL và tài nguyên phụ cần xem xét riêng. Nguồn mở vẫn có bản quyền và điều kiện sử dụng/phân phối.

Đã lưu 90 file license/notice nguyên byte trong [licenses/runtime](licenses/runtime/), kèm SHA-256 trong [dependency-licenses.json](dependency-licenses.json). Mọi gói được kiểm kê có file license; việc có file không chứng minh đã đáp ứng mọi nghĩa vụ native/source. Xem thêm [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Các điểm cần lưu ý

### lxml: không chỉ BSD

pyHanko phụ thuộc lxml 6.1.3. Wheel đang cài có tag `cp312-cp312-win_amd64`, không phải pure Python. [LICENSES.txt bản cài](licenses/runtime/lxml/6.1.3/lxml-6.1.3.dist-info/licenses/LICENSES.txt) ghi core BSD, phần ElementTree/CPython PSF và binary wheels có zlib, iconv, libxml2/libxslt/libexslt; **iconv dùng LGPL-2.1**. Đây là thông báo distribution, chưa phải phân tích binary để xác định cách liên kết từng thành phần. [Nguồn upstream lxml](https://github.com/lxml/lxml/blob/master/LICENSES.txt).

Trước khi bàn giao wheel/container, cần đối chiếu exact build, notices, nguồn tương ứng và nghĩa vụ LGPL theo cách liên kết. Sao chép LICENSES.txt chưa đủ để kết luận hoàn tất nghĩa vụ này. Nếu yêu cầu mọi thành phần đều có giấy phép permissive, cần chọn/build bản được kiểm chứng phù hợp; không tự xóa lxml vì pyHanko phụ thuộc thư viện này.

File trên còn ghi test runner `test.py` GPL, một schema ISO có bản quyền riêng và `RNG2Schtrn.xsl`/`XSD2Schtrn.xsl` không có license. Code ứng dụng không gọi trực tiếp các tài nguyên này. Cần kiểm tra file thực sự có trong gói bàn giao và quyền phân phối; không gán toàn bộ ứng dụng là GPL chỉ vì test runner, cũng không coi toàn bộ wheel chỉ là BSD.

### certifi: MPL-2.0

certifi 2026.7.22 dùng MPL-2.0. Khi phân phối Covered Software cần giữ thông báo và đáp ứng yêu cầu cung cấp nguồn phần được MPL bảo hộ, kể cả sửa đổi nếu có. MPL áp dụng ở cấp tệp, không tự buộc toàn bộ ứng dụng dùng MPL. Chỉ chạy trên server khác với chuyển bản sao thư viện cho bên khác. [Mozilla MPL FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/), [certifi upstream](https://github.com/certifi/python-certifi).

### Pillow, PDFium và native components

Pillow 12.3.0 có core MIT-CMU và component notices. FreeType trong notices có lựa chọn FreeType License (FTL) hoặc GPL; có thể chọn FTL với đầy đủ điều kiện/attribution, không suy ra cả ứng dụng là GPL. Giữ nguyên toàn bộ [license Pillow](licenses/runtime/pillow/12.3.0/pillow-12.3.0.dist-info/licenses/LICENSE).

pypdfium2 5.13.0 có wrapper Apache-2.0 hoặc BSD-3-Clause; PDFium, binary và tài liệu có giấy phép riêng. Đã giữ notices distribution cung cấp, gồm Windows x64. So Khớp dùng pdfplumber trích xuất bảng, không trực tiếp gọi renderer PDFium; phụ thuộc vẫn cần notices nếu đi cùng gói bàn giao. [Licensing pypdfium2](https://pypdfium2.readthedocs.io/en/stable/readme.html#licensing).

cryptography có lựa chọn Apache-2.0 hoặc BSD-3-Clause. Đã giữ license wheel cung cấp; chưa phân tích đầy đủ từng binary/native/Rust/OpenSSL và cách đóng gói. Không dùng metadata wrapper để chứng nhận mọi thành phần native.

### Phiên bản khai báo và thực tế khác nhau

| Gói | requirements.txt | Import thực tế | License bản thực tế |
| --- | --- | --- | --- |
| pypdf | 6.1.1 | 6.10.0 | BSD-3-Clause |
| reportlab | 4.4.4 | 4.4.9 | BSD-3-Clause |

Hai gói thực tế lấy từ bundled Python site-packages. Đây là vấn đề tái lập môi trường/phạm vi kiểm kê, chưa phải bằng chứng vi phạm bản quyền. Chưa đổi phiên bản. Trước triển khai VKU cần chốt manifest và kiểm kê chính bản deploy; báo cáo này không chứng nhận một image Linux chưa tạo.

### Công cụ kiểm thử và font

TypeScript là devDependency. Playwright/playwright-core lấy từ bundled runtime dùng E2E, chưa khai báo trong package.json. Ba công cụ có Apache-2.0 và notices. Frontend dùng JavaScript của dự án, không thấy CDN/framework tải thêm. Binary Chromium kiểm thử nằm ngoài kiểm kê; nếu phân phối browser cần rà soát và giữ notices riêng.

`tests/fixtures.py` chọn Arial từ Windows hoặc DejaVuSans trên Linux để nhúng PDF kiểm thử. Arial là font hệ điều hành, không phải font nguồn mở của dự án. Không có TTF Arial trong repo; PDF test bị ignore. Không sao chép Arial vào server/container nếu chưa có quyền; quyền nhúng phụ thuộc license/embedding flags. CSS gọi tên font không đồng nghĩa phân phối file font. [Microsoft font FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq). Nên chọn font nguồn mở có license đi kèm khi chuẩn hóa fixture.

## Phạm vi và tái kiểm tra

- Đã đọc requirements.txt, package.json/lock, imports backend/scripts/tests, metadata/license gói đang cài. Cây phụ thuộc xét marker hoạt động trên Windows, không gồm optional extras chưa bật.
- Không cài mới, nâng/hạ thư viện, sửa logic hoặc dữ liệu học vụ. Không kiểm kê toàn bộ Python/Node runtime, OS, Chromium hay phân tích mọi binary.
- Không xác định quyền của PDF, chữ ký/font trong tài liệu người dùng; không tự cấp license code trường. Repo chưa có LICENSE ở gốc; chủ sở hữu quyết định nếu muốn cấp quyền nguồn mở cho code riêng.
- Chạy lại: `python scripts/run.py scripts.audit_licenses`. Truyền `--node-tools-root` trên máy khác nếu cần. Script không tải gói; kết quả là snapshot môi trường resolve. cryptography/asn1crypto/pyhanko_certvalidator/pydantic đang được import trực tiếp nhưng lấy qua phụ thuộc bắc cầu, cần lưu ý khi chốt manifest.
- Metadata chỉ là chỉ dẫn. License/notice exact distribution và điều kiện từng component là bằng chứng chi tiết; bảng dưới ghi ngoại lệ thay vì suy luận mọi file theo license core.

## Danh sách phiên bản thực tế

| Gói | Phiên bản | Giấy phép/ngoại lệ | Bản license đầu tiên (inventory chứa đầy đủ) |
| --- | --- | --- | --- |
| aiohappyeyeballs | 2.7.1 | PSF-2.0 | [License](licenses/runtime/aiohappyeyeballs/2.7.1/aiohappyeyeballs-2.7.1.dist-info/licenses/LICENSE) |
| aiohttp | 3.14.3 | Apache-2.0 AND MIT | [License](licenses/runtime/aiohttp/3.14.3/aiohttp-3.14.3.dist-info/licenses/LICENSE.txt) |
| aiosignal | 1.4.0 | Apache 2.0 | [License](licenses/runtime/aiosignal/1.4.0/aiosignal-1.4.0.dist-info/licenses/LICENSE) |
| annotated-doc | 0.0.5 | MIT | [License](licenses/runtime/annotated-doc/0.0.5/annotated_doc-0.0.5.dist-info/licenses/LICENSE) |
| annotated-types | 0.8.0 | MIT | [License](licenses/runtime/annotated-types/0.8.0/annotated_types-0.8.0.dist-info/licenses/LICENSE) |
| anyio | 4.15.1 | MIT | [License](licenses/runtime/anyio/4.15.1/anyio-4.15.1.dist-info/licenses/LICENSE) |
| asn1crypto | 1.5.1 | MIT | [License](licenses/runtime/asn1crypto/1.5.1/asn1crypto-1.5.1.dist-info/LICENSE) |
| attrs | 26.1.0 | MIT | [License](licenses/runtime/attrs/26.1.0/attrs-26.1.0.dist-info/licenses/LICENSE) |
| certifi | 2026.7.22 | MPL-2.0 | [License](licenses/runtime/certifi/2026.7.22/certifi-2026.7.22.dist-info/licenses/LICENSE) |
| cffi | 2.1.1 | MIT-0 | [License](licenses/runtime/cffi/2.1.1/cffi-2.1.1.dist-info/licenses/LICENSE) |
| charset-normalizer | 3.5.1 | MIT | [License](licenses/runtime/charset-normalizer/3.5.1/charset_normalizer-3.5.1.dist-info/licenses/LICENSE) |
| click | 8.5.0 | BSD-3-Clause | [License](licenses/runtime/click/8.5.0/click-8.5.0.dist-info/licenses/LICENSE.txt) |
| colorama | 0.4.6 | BSD-3-Clause | [License](licenses/runtime/colorama/0.4.6/colorama-0.4.6.dist-info/licenses/LICENSE.txt) |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | [License](licenses/runtime/cryptography/50.0.2/cryptography-50.0.2.dist-info/licenses/LICENSE) |
| et_xmlfile | 2.0.0 | MIT; kèm LICENCE.python | [License](licenses/runtime/et-xmlfile/2.0.0/et_xmlfile-2.0.0.dist-info/LICENCE.python) |
| fastapi | 0.142.2 | MIT | [License](licenses/runtime/fastapi/0.142.2/fastapi-0.142.2.dist-info/licenses/LICENSE) |
| frozenlist | 1.8.0 | Apache-2.0 | [License](licenses/runtime/frozenlist/1.8.0/frozenlist-1.8.0.dist-info/licenses/LICENSE) |
| h11 | 0.16.0 | MIT | [License](licenses/runtime/h11/0.16.0/h11-0.16.0.dist-info/licenses/LICENSE.txt) |
| httpcore | 1.0.9 | BSD-3-Clause | [License](licenses/runtime/httpcore/1.0.9/httpcore-1.0.9.dist-info/licenses/LICENSE.md) |
| httpx | 0.28.1 | BSD-3-Clause | [License](licenses/runtime/httpx/0.28.1/httpx-0.28.1.dist-info/licenses/LICENSE.md) |
| idna | 3.20 | BSD-3-Clause | [License](licenses/runtime/idna/3.20/idna-3.20.dist-info/licenses/LICENSE.md) |
| iniconfig | 2.3.0 | MIT | [License](licenses/runtime/iniconfig/2.3.0/iniconfig-2.3.0.dist-info/licenses/LICENSE) |
| lxml | 6.1.3 | BSD-3-Clause core; PSF/native LGPL-2.1 và tài nguyên phụ (xem trên) | [License](licenses/runtime/lxml/6.1.3/lxml-6.1.3.dist-info/licenses/LICENSE.txt) |
| multidict | 6.9.1 | Apache License 2.0 | [License](licenses/runtime/multidict/6.9.1/multidict-6.9.1.dist-info/licenses/LICENSE) |
| openpyxl | 3.1.5 | MIT | [License](licenses/runtime/openpyxl/3.1.5/openpyxl-3.1.5.dist-info/LICENCE.rst) |
| opentelemetry-api | 1.45.0 | Apache-2.0 | [License](licenses/runtime/opentelemetry-api/1.45.0/opentelemetry_api-1.45.0.dist-info/licenses/LICENSE) |
| oscrypto | 1.3.0 | MIT | [License](licenses/runtime/oscrypto/1.3.0/oscrypto-1.3.0.dist-info/LICENSE) |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | [License](licenses/runtime/packaging/26.3/packaging-26.3.dist-info/licenses/LICENSE) |
| pdfminer.six | 20251230 | MIT | [License](licenses/runtime/pdfminer-six/20251230/pdfminer_six-20251230.dist-info/licenses/LICENSE) |
| pdfplumber | 0.11.9 | MIT | [License](licenses/runtime/pdfplumber/0.11.9/pdfplumber-0.11.9.dist-info/licenses/LICENSE.txt) |
| pillow | 12.3.0 | MIT-CMU core; component notices, gồm FreeType FTL/GPL lựa chọn | [License](licenses/runtime/pillow/12.3.0/pillow-12.3.0.dist-info/licenses/LICENSE) |
| pluggy | 1.6.0 | MIT | [License](licenses/runtime/pluggy/1.6.0/pluggy-1.6.0.dist-info/licenses/LICENSE) |
| propcache | 0.5.4 | Apache-2.0 | [License](licenses/runtime/propcache/0.5.4/propcache-0.5.4.dist-info/licenses/LICENSE) |
| pycparser | 3.0 | BSD-3-Clause | [License](licenses/runtime/pycparser/3.0/pycparser-3.0.dist-info/licenses/LICENSE) |
| pydantic | 2.13.5 | MIT | [License](licenses/runtime/pydantic/2.13.5/pydantic-2.13.5.dist-info/licenses/LICENSE) |
| pydantic_core | 2.46.5 | MIT | [License](licenses/runtime/pydantic-core/2.46.5/pydantic_core-2.46.5.dist-info/licenses/LICENSE) |
| Pygments | 2.21.0 | BSD-2-Clause | [License](licenses/runtime/pygments/2.21.0/pygments-2.21.0.dist-info/licenses/AUTHORS) |
| pyHanko | 0.37.0 | MIT | [License](licenses/runtime/pyhanko/0.37.0/pyhanko-0.37.0.dist-info/licenses/LICENSE) |
| pyhanko-certvalidator | 0.32.1 | MIT | [License](licenses/runtime/pyhanko-certvalidator/0.32.1/pyhanko_certvalidator-0.32.1.dist-info/licenses/LICENSE) |
| pypdf | 6.10.0 | BSD-3-Clause | [License](licenses/runtime/pypdf/6.10.0/pypdf-6.10.0.dist-info/licenses/LICENSE) |
| pypdfium2 | 5.13.0 | Apache-2.0 OR BSD-3-Clause wrapper; PDFium/component/tài liệu riêng | [License](licenses/runtime/pypdfium2/5.13.0/pypdfium2-5.13.0.dist-info/licenses/LICENSES/Apache-2.0.txt) |
| pytest | 9.1.1 | MIT | [License](licenses/runtime/pytest/9.1.1/pytest-9.1.1.dist-info/licenses/LICENSE) |
| python-multipart | 0.0.32 | Apache-2.0 | [License](licenses/runtime/python-multipart/0.0.32/python_multipart-0.0.32.dist-info/licenses/LICENSE.txt) |
| reportlab | 4.4.9 | BSD-3-Clause | [License](licenses/runtime/reportlab/4.4.9/reportlab-4.4.9.dist-info/licenses/LICENSE) |
| starlette | 1.7.0 | BSD-3-Clause | [License](licenses/runtime/starlette/1.7.0/starlette-1.7.0.dist-info/licenses/LICENSE.md) |
| typing_extensions | 4.16.0 | PSF-2.0 | [License](licenses/runtime/typing-extensions/4.16.0/typing_extensions-4.16.0.dist-info/licenses/LICENSE) |
| typing-inspection | 0.4.4 | MIT | [License](licenses/runtime/typing-inspection/0.4.4/typing_inspection-0.4.4.dist-info/licenses/LICENSE) |
| tzdata | 2026.5 | Apache-2.0 | [License](licenses/runtime/tzdata/2026.5/tzdata-2026.5.dist-info/licenses/LICENSE) |
| tzlocal | 5.4.4 | MIT | [License](licenses/runtime/tzlocal/5.4.4/tzlocal-5.4.4.dist-info/licenses/LICENSE.txt) |
| uritools | 6.1.3 | MIT | [License](licenses/runtime/uritools/6.1.3/uritools-6.1.3.dist-info/licenses/LICENSE) |
| uvicorn | 0.54.0 | BSD-3-Clause | [License](licenses/runtime/uvicorn/0.54.0/uvicorn-0.54.0.dist-info/licenses/LICENSE.md) |
| yarl | 1.25.1 | Apache-2.0 | [License](licenses/runtime/yarl/1.25.1/yarl-1.25.1.dist-info/licenses/LICENSE) |
| typescript | 5.9.3 | Apache-2.0 | [License](licenses/runtime/typescript/5.9.3/LICENSE.txt) |
| playwright | 1.62.1 | Apache-2.0 | [License](licenses/runtime/playwright/1.62.1/LICENSE) |
| playwright-core | 1.62.1 | Apache-2.0 | [License](licenses/runtime/playwright-core/1.62.1/LICENSE) |
