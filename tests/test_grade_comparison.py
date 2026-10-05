import io
import json
import zipfile
from html import escape
from pathlib import Path
import pytest
from backend.grade_comparison import pdf_grades, reference_grades, compare_grades
from tests.fixtures import grade_table_pdf, unsigned_pdf
from tests.test_system import env,pki,login,submit


def source(data='MSSV,Họ tên,Điểm\n24IT001,A,"8,50"\n24IT002,B,0\n'):
    return reference_grades(data.encode(),'export.csv')


def test_grade_parser_and_decimal_zero_missing_partial():
    pdf=pdf_grades(grade_table_pdf())
    assert pdf['columns']==[{'key':'3','label':'ĐIỂM'}]
    result=compare_grades(pdf,source(),{'3':'2'})
    assert result['status']=='match' and result['matched']==2
    changed=source('MSSV,Họ tên,Điểm\n24IT001,A,9\n24IT003,C,0\n')
    result=compare_grades(pdf,changed,{'3':'2'})
    assert (result['mismatched'],result['missing'],result['extra'])==(1,1,1)
    assert result['status']=='different'
    blank=source('MSSV,Họ tên,Điểm\n24IT001,A,8.5\n24IT002,B,\n')
    assert compare_grades(pdf,blank,{'3':'2'})['status']=='incomplete'
    pdf['columns'].append({'key':'4','label':'Điểm khác'})
    assert compare_grades(pdf,source(),{'3':'2'})['status']=='incomplete'
    for record in pdf['records'].values():record['values']['4']=''
    mixed=source('MSSV,Họ tên,Điểm,Khác\n24IT001,A,9,\n24IT002,B,0,\n')
    result=compare_grades(pdf,mixed,{'3':'2','4':'3'})
    assert result['status']=='different' and result['mismatched']==1 and result['unavailable']==2


@pytest.mark.parametrize('data',['MSSV,Điểm\n24IT001,8\n24IT001,9\n','Name,Điểm\nA,8\n','MSSV,Điểm\n,8\n'])
def test_source_ambiguity_rejected(data):
    with pytest.raises(ValueError):source(data)


def test_dotted_student_ids_preserved():
    result=source('MSSV,Điểm\n22IT.B019,8.5\n23IT.B049,0\n')
    assert set(result['records'])=={'22IT.B019','23IT.B049'}


def test_unsigned_pdf_reference_match_and_difference():
    pdf=pdf_grades(grade_table_pdf())
    reference=reference_grades(grade_table_pdf(),'export.PDF')
    assert compare_grades(pdf,reference,{'3':'3'})['status']=='match'
    reference=reference_grades(grade_table_pdf('9'),'export.pdf')
    result=compare_grades(pdf,reference,{'3':'3'})
    assert result['mismatched']==1 and result['matched']==1
    assert result['differences'][0]['cells'][0]=={'column':'ĐIỂM','pdf':'8.5','reference':'9','missing_value':False}


@pytest.mark.parametrize('kind',['wrong-type','broken','no-table'])
def test_unreadable_pdf_reference_rejected(kind):
    data={'wrong-type':b'not a pdf','broken':b'%PDF-1.7\ninvalid','no-table':unsigned_pdf()}[kind]
    with pytest.raises(ValueError):reference_grades(data,'export.pdf')


def test_read_xlsx_export_in_memory():
    buffer=io.BytesIO()
    files={'[Content_Types].xml':'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
           '_rels/.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
           'xl/workbook.xml':'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Diem" sheetId="1" r:id="rId1"/></sheets></workbook>',
           'xl/_rels/workbook.xml.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'}
    rows=[['MSSV','Điểm'],['24IT001','8.5'],['24IT002','0']]
    xml=''.join('<row r="'+str(i)+'">'+''.join(f'<c r="{chr(65+j)}{i}" t="inlineStr"><is><t>{escape(v)}</t></is></c>' for j,v in enumerate(row))+'</row>' for i,row in enumerate(rows,1))
    files['xl/worksheets/sheet1.xml']='<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+xml+'</sheetData></worksheet>'
    with zipfile.ZipFile(buffer,'w') as archive:
        for name,text in files.items():archive.writestr(name,text)
    result=reference_grades(buffer.getvalue(),'export.xlsx')
    assert result['records']['24IT002']['values']['1']=='0'
    assert compare_grades(pdf_grades(grade_table_pdf()),result,{'3':'1'})['status']=='match'


@pytest.mark.parametrize('path,count,columns',[('bang-diem-TP_N1.signed.pdf',71,3),('bang-diem-CK_N1.signed.pdf',71,1),('HK1_26_27/diem-huong-dan-do-an_Thực tập thực tế (22).signed.signed.pdf',19,1)])
def test_real_pdf_tables(path,count,columns):
    if not Path(path).exists():pytest.skip('Private PDF fixture unavailable')
    result=pdf_grades(Path(path).read_bytes())
    assert len(result['records'])==count and len(result['columns'])==columns
    reference=reference_grades(Path(path).read_bytes(),'export.pdf')
    pairs={column['key']:column['key'] for column in result['columns']}
    compared=compare_grades(result,reference,pairs)
    assert compared['mismatched']==0 and compared['missing']==0 and compared['extra']==0


def test_comparison_api_scope_csrf_version_and_preservation(env,pki):
    app,_=env;gv,tk,dt=login(app,1),login(app,2),login(app,3)
    data=pki.sign(pki.sign(grade_table_pdf(),0),2)
    assert submit(gv,data).status_code==200
    endpoint='/api/submissions/1/comparison'
    assert gv.get(endpoint).status_code==403
    assert tk.get(endpoint).status_code==403
    assert dt.get(endpoint).json()['columns']==[{'key':'3','label':'ĐIỂM'}]
    export=b'MSSV,Grade\n24IT001,8.5\n24IT002,0\n'
    args={'data':{'version':'1','mapping':json.dumps({'3':'1'})},'files':{'file':('export.csv',export,'text/csv')}}
    assert gv.post(endpoint,**args).status_code==403
    token=dt.headers.pop('X-CSRF-Token')
    assert dt.post(endpoint,**args).status_code==403
    dt.headers['X-CSRF-Token']=token
    assert dt.post(endpoint,**args).json()['status']=='match'
    pdf_args={'data':{'version':'1','mapping':json.dumps({'3':'3'})},'files':{'file':('daotao.pdf',grade_table_pdf(),'application/pdf')}}
    inspected=dt.post(endpoint+'/reference',data={'version':'1'},files=pdf_args['files'])
    assert inspected.status_code==200 and inspected.json()['student_count']==2
    assert dt.post(endpoint,**pdf_args).json()['status']=='match'
    pdf_args['files']={'file':('daotao.pdf',grade_table_pdf('9'),'application/pdf')}
    assert dt.post(endpoint,**pdf_args).json()['mismatched']==1
    pdf_args['files']={'file':('broken.pdf',b'%PDF-1.7\ninvalid','application/pdf')}
    assert dt.post(endpoint,**pdf_args).status_code==422
    args['data']['version']='99'
    assert dt.post(endpoint,**args).status_code==409
    args['data'].update(version='1',mapping='{"3":[]}')
    assert dt.post(endpoint,**args).status_code==422
    assert gv.get('/api/submissions/1/pdf').content==data
    item=gv.get('/api/submissions').json()['items'][0]
    assert item['version']==1 and item['status']=='submitted'
    with app.state.database.connect() as db:
        details=db.execute("SELECT details FROM audit WHERE action='compare_grade_export'").fetchone()[0]
        assert '24IT001' not in details and '8.5' not in details
