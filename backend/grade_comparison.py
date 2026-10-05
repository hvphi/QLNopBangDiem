"""Read-only grade comparison against an explicitly supplied export."""
import csv
import io
import re
import unicodedata
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
import openpyxl
import pdfplumber

MAX_ROWS = 5000


def clean(value):
    return ' '.join(str(value if value is not None else '').split())


def normalized(value):
    value = clean(value).lower().replace('đ', 'd')
    return ''.join(c for c in unicodedata.normalize('NFD', value) if not unicodedata.combining(c))


def student_id(value):
    value = clean(value).upper()
    if not re.fullmatch(r'[A-Z0-9_.-]{3,30}', value) or not any(c.isdigit() for c in value):
        raise ValueError('Mã sinh viên không hợp lệ hoặc bị mất định dạng trong file.')
    return value


def id_header(value):
    return normalized(value) in ('so the','mssv','ma sv','ma sinh vien','student id','student_id','masv')


def pdf_grades(data):
    records, columns, text_ids = {}, None, set()
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        if len(pdf.pages) > 100:
            raise ValueError('PDF vượt 100 trang.')
        for page in pdf.pages:
            for match in re.finditer(r'^\s*\d+\s+([A-Za-z0-9_.-]{3,30})\s+',page.extract_text() or '',re.M):
                if any(c.isdigit() for c in match[1]):text_ids.add(match[1].upper())
            for table in page.extract_tables():
                start = next((i for i,r in enumerate(table) if len(r)>1 and clean(r[0]).isdigit() and clean(r[1])), None)
                if start is None:
                    continue
                header = table[:start]
                id_col = next((j for r in header for j,v in enumerate(r) if id_header(v)), None)
                if id_col is None:
                    continue
                labels = [' '.join(dict.fromkeys(clean(r[j]) for r in header if j<len(r) and clean(r[j]))) for j in range(len(table[start]))]
                score_cols = [{'key':str(j),'label':label} for j,label in enumerate(labels)
                              if any(w in normalized(label) for w in ('diem','chuyen can','bai tap','giua ky','cuoi ky'))
                              and not re.search(r'\bchu\b',normalized(label))]
                if not score_cols:
                    raise ValueError('Không xác định được cột điểm số trong PDF; không thể kết luận so khớp.')
                if columns is not None and score_cols != columns:
                    raise ValueError('Các trang PDF có cấu trúc cột điểm khác nhau.')
                columns = score_cols
                name_start = next((j for j,l in enumerate(labels) if 'ho va ten' in normalized(l)), None)
                for row in table[start:]:
                    if not clean(row[0]).isdigit():
                        continue
                    sid = student_id(row[id_col])
                    if sid in records:
                        raise ValueError('Mã sinh viên trùng trong PDF: '+sid)
                    name = ''
                    if name_start is not None:
                        end = next((j for j in range(name_start+1,len(labels)) if labels[j]),len(labels))
                        name = ' '.join(clean(v) for v in row[name_start:end] if clean(v))
                    records[sid] = {'name':name,'values':{c['key']:clean(row[int(c['key'])]) for c in columns}}
                    if len(records)>MAX_ROWS:
                        raise ValueError('Bảng điểm vượt 5000 sinh viên.')
    if not records:
        raise ValueError('Không đọc được bảng điểm có mã sinh viên trong PDF. PDF scan cần dữ liệu có thể trích xuất.')
    if text_ids-records.keys():
        raise ValueError('Một số dòng sinh viên trong PDF không trích xuất được đầy đủ; không thể kết luận so khớp.')
    return {'columns':columns,'records':records}


def reference_grades(data, filename):
    suffix = Path(filename or '').suffix.lower()
    if suffix == '.pdf':
        if b'%PDF-' not in data[:1024]:
            raise ValueError('File nguồn không phải PDF hợp lệ.')
        try:
            return pdf_grades(data)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError('Không đọc được PDF nguồn. Hãy chọn PDF xuất từ daotao không bị lỗi hoặc khóa mật khẩu.') from exc
    elif suffix == '.csv':
        try:
            text = data.decode('utf-8-sig')
            dialect = csv.Sniffer().sniff(text[:8192],delimiters=',;\t')
            rows = list(csv.reader(io.StringIO(text),dialect))
        except (UnicodeError,csv.Error) as exc:
            raise ValueError('CSV cần mã hóa UTF-8 và cột phân cách dấu phẩy, chấm phẩy hoặc tab.') from exc
    elif suffix == '.xlsx':
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if len(archive.infolist())>1000 or sum(item.file_size for item in archive.infolist())>50*1024*1024:
                    raise ValueError('Excel vượt giới hạn kích thước giải nén.')
            workbook = openpyxl.load_workbook(io.BytesIO(data),read_only=True,data_only=True)
            try:
                candidates=[]
                for sheet in workbook:
                    sheet_rows=[]
                    for row in sheet.iter_rows(values_only=True):
                        sheet_rows.append(row)
                        if len(sheet_rows)>MAX_ROWS+50:
                            raise ValueError('File Excel vượt giới hạn dòng.')
                    if any(any(id_header(v) for v in r) for r in sheet_rows[:50]):
                        candidates.append(sheet_rows)
                if len(candidates)!=1:
                    raise ValueError('Excel cần đúng một sheet bảng điểm có cột MSSV/Số thẻ.')
                rows=candidates[0]
            finally:
                workbook.close()
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError('Không đọc được file Excel .xlsx.') from exc
    else:
        raise ValueError('Hãy chọn PDF xuất từ daotao; cũng hỗ trợ .xlsx hoặc .csv.')
    if len(rows)>MAX_ROWS+50:
        raise ValueError('File vượt giới hạn dòng.')
    header_index = next((i for i,r in enumerate(rows[:50]) if any(id_header(v) for v in r)),None)
    if header_index is None:
        raise ValueError('Không tìm thấy cột MSSV/Mã sinh viên/Số thẻ trong file.')
    header = [clean(v) for v in rows[header_index]]
    id_cols = [i for i,v in enumerate(header) if id_header(v)]
    if len(id_cols)!=1:
        raise ValueError('Cần duy nhất một cột mã sinh viên.')
    id_col=id_cols[0]
    columns=[{'key':str(i),'label':label} for i,label in enumerate(header) if label and i!=id_col]
    if len({normalized(c['label']) for c in columns})!=len(columns):
        raise ValueError('Các cột trong file nguồn cần có tên khác nhau.')
    records={}
    for row in rows[header_index+1:]:
        if not any(clean(v) for v in row):
            continue
        if id_col>=len(row) or not clean(row[id_col]):
            raise ValueError('File nguồn có dòng dữ liệu thiếu mã sinh viên.')
        sid=student_id(row[id_col])
        if sid in records:
            raise ValueError('Mã sinh viên trùng trong file nguồn: '+sid)
        records[sid]={'values':{c['key']:clean(row[int(c['key'])]) if int(c['key'])<len(row) else '' for c in columns}}
    if not records or len(records)>MAX_ROWS:
        raise ValueError('File nguồn không có sinh viên hoặc vượt 5000 dòng.')
    return {'columns':columns,'records':records}


def score(value):
    value=clean(value)
    if not value:
        return None
    try:
        number=Decimal(value.replace(',','.'))
        if not number.is_finite() or not 0<=number<=10:
            raise ValueError('Điểm số phải nằm trong khoảng 0 đến 10.')
        return number
    except InvalidOperation:
        return value.upper()


def compare_grades(pdf, reference, mapping):
    pdf_cols={c['key']:c['label'] for c in pdf['columns']}
    ref_cols={c['key']:c['label'] for c in reference['columns']}
    if not isinstance(mapping,dict) or not mapping or any(not isinstance(k,str) or not isinstance(v,str) or k not in pdf_cols or v not in ref_cols for k,v in mapping.items()):
        raise ValueError('Hãy ghép ít nhất một cột điểm hợp lệ.')
    if len(set(mapping.values()))!=len(mapping):
        raise ValueError('Không ghép nhiều cột PDF với cùng một cột nguồn.')
    differences=[];matched=mismatched=missing=extra=unavailable=0
    for sid,row in pdf['records'].items():
        other=reference['records'].get(sid)
        if other is None:
            missing+=1;differences.append({'student_id':sid,'name':row['name'],'type':'missing','cells':[]});continue
        cells=[];has_blank=False
        for key,target in mapping.items():
            left,right=row['values'][key],other['values'][target]
            a,b=score(left),score(right)
            if a is None or b is None or a!=b:
                cells.append({'column':pdf_cols[key],'pdf':left,'reference':right,'missing_value':a is None or b is None})
                has_blank=has_blank or a is None or b is None
        if cells:
            has_difference=any(not cell['missing_value'] for cell in cells)
            if has_blank:unavailable+=1
            if has_difference:mismatched+=1
            differences.append({'student_id':sid,'name':row['name'],'type':'mismatch' if has_difference else 'unavailable','cells':cells})
        else:matched+=1
    for sid in reference['records'].keys()-pdf['records'].keys():
        extra+=1;differences.append({'student_id':sid,'name':'','type':'extra','cells':[]})
    complete=len(mapping)==len(pdf_cols)
    status='different' if mismatched or missing or extra else 'incomplete' if unavailable or not complete else 'match'
    return {'status':status,'matched':matched,'mismatched':mismatched,'missing':missing,'extra':extra,'unavailable':unavailable,
            'mapped_columns':len(mapping),'total_columns':len(pdf_cols),'pdf_students':len(pdf['records']),
            'reference_students':len(reference['records']),'differences':differences}
