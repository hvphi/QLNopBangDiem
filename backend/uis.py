import io
import re
import unicodedata
from pathlib import Path
from pypdf import PdfReader
from .storage import slug


def normalized(text):
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split())


def canonical_uis_ids(value):
    value = value.strip()
    if not value:
        return ''
    if not re.fullmatch(r'[0-9]+(?:\s*,\s*[0-9]+)*', value):
        raise ValueError('Mã UIS cần là số, phân cách bằng dấu phẩy nếu có nhiều mã (ví dụ: 17210, 17219).')
    return ','.join(dict.fromkeys(part.strip() for part in value.split(',')))


def header_values(header, aliases):
    labels = ['tên lớp học phần', 'tên học phần', 'tên môn', 'học phần',
              'mã lớp học phần', 'mã lhp', 'lớp học phần', 'năm học',
              'học kỳ', 'học kì', 'số tín chỉ', 'nhóm', 'lớp', 'giảng viên']
    # Longest labels first so "học phần" cannot split "tên lớp học phần".
    stop = '|'.join(re.escape(x) for x in sorted(labels, key=len, reverse=True))
    alternatives = []
    for alias in sorted(aliases, key=len, reverse=True):
        separator = r'\s*[:\-]\s*' if alias in ('học phần', 'lớp học phần') else r'\s*[:\-]?\s*'
        alternatives.append(re.escape(alias) + separator)
    pattern = (r'(?<!\w)(?:' + '|'.join(alternatives) + r')'
               r'(.+?)(?=\s+(?:' + stop + r')\s*[:\-]?|$)')
    return [m.strip() for m in re.findall(pattern, header)]


def class_identity(title):
    title = normalized(title)
    match = re.fullmatch(r'(.*?)\s*\(\s*(\d+)\s*\)(.*)', title)
    if not match:
        return title, None, ''
    subject, group, suffix = match.groups()
    return subject.strip(), str(int(group)), re.sub(r'[\s_]+', '_', suffix).strip('_')


def validate_metadata(data, course, assessment_type='final'):
    # Compare visible labelled headers; neither /Info nor a UIS URL proves the class.
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted or len(reader.pages) > 100:
        raise ValueError('PDF mã hóa hoặc vượt 100 trang không được hỗ trợ.')
    header = normalized(reader.pages[0].extract_text() or '') if reader.pages else ''
    header = re.split(r'(?<!\w)stt(?!\w)', header, maxsplit=1)[0]
    detected = 'component' if 'bảng điểm thành phần' in header else 'final' if (
        'bảng điểm kết thúc học phần' in header or 'bảng điểm cuối kỳ' in header) else None
    if detected and assessment_type != detected:
        name = 'thành phần' if detected == 'component' else 'cuối kỳ'
        raise ValueError(f'PDF là bảng điểm {name}. Hãy chọn đúng loại bảng điểm trước khi nộp.')
    labels = {'code': ['mã lhp', 'mã lớp học phần', 'lớp học phần'],
              'title': ['tên lớp học phần', 'tên học phần', 'tên môn', 'học phần'],
              'year': ['năm học'], 'semester': ['học kỳ', 'học kì']}
    titles = header_values(header, labels['title'])
    # Overlapping aliases return the same value; conflicting titles are rejected.
    identities = set(class_identity(title) for title in titles)
    if len(identities) != 1:
        raise ValueError('Không đọc được tên môn/lớp duy nhất trong header PDF.')
    subject, group, suffix = identities.pop()
    expected_subject, expected_group, expected_suffix = class_identity(course['title'])
    if subject != expected_subject:
        raise ValueError(f'Môn học trong PDF không khớp lớp đã chọn ({course["title"]}).')
    if expected_group is not None:
        if group != expected_group:
            raise ValueError(f'Lớp/nhóm trong PDF không khớp lớp đã chọn ({course["title"]}).')
        # The timetable may omit cohort tags (e.g. _GIT) before the language _TA.
        suffix_matches = suffix == expected_suffix or (
            expected_suffix == 'ta' and re.fullmatch(r'[a-z0-9]+_ta', suffix))
        if not suffix_matches:
            raise ValueError(f'Tên lớp trong PDF không khớp lớp đã chọn ({course["title"]}).')
    else:
        codes = set(header_values(header, ['mã lhp', 'mã lớp học phần']))
        if codes != {normalized(course['code'])}:
            raise ValueError('Chưa xác định được lớp/nhóm từ tên lớp đã chọn. '
                             'Cần tên lớp có nhóm hoặc mã lớp ghi rõ trong header PDF.')
    for key in ('year', 'semester'):
        value_pattern = r'\d{4}\s*[-–]\s*\d{4}' if key == 'year' else r'\d+'
        values = set(re.sub(r'\s*[-–]\s*', '-', value) for alias in labels[key]
                     for value in re.findall(r'(?<!\w)' + re.escape(alias) +
                                             r'\s*[:\-]?\s*(' + value_pattern + r')(?!\w)', header))
        if values != {normalized(course[key])}:
            name = {'year':'Năm học', 'semester':'Học kỳ'}[key]
            raise ValueError(f'{name} trong PDF không khớp lớp đã chọn ({course[key]}) hoặc không đọc được header tương ứng.')


def source_pdf(course, export_root):
    if not course['source_pdf'] or not export_root:
        raise ValueError('Chưa cấu hình PDF xuất từ UIS cho lớp này.')
    root = Path(export_root).resolve()
    path = (root / course['source_pdf']).resolve()
    if not path.is_relative_to(root) or path.suffix.lower() != '.pdf':
        raise ValueError('Đường dẫn PDF UIS không hợp lệ.')
    data = path.read_bytes()
    validate_metadata(data, course)
    return data


def filename(course, teacher):
    name = '_'.join(slug(x) for x in (course['code'], course['title'], course['semester'], course['year'], teacher))
    if course.get('assessment_type'):
        name += '_' + slug(course['assessment_type']) + '_' + str(course['id'])
    return name + '.pdf'
