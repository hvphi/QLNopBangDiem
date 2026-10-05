"""Ephemeral test PKI with a real CA, leaf keys and signed revocation list."""
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from asn1crypto import x509 as asn_x509, keys as asn_keys, crl as asn_crl
from pyhanko.sign import signers
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko_certvalidator import ValidationContext
from pyhanko_certvalidator.registry import SimpleCertificateStore
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from backend.verification import Verifier
from backend.auth import hash_password
from backend.db import Database


PASSWORD = 'Test-Only-Password-2026!'
COURSE = {'code':'CSDL01','title':'Cơ sở dữ liệu','year':'2025-2026','semester':'1','department':'CNTT','teacher_id':1}


def certificate(key, name, issuer, issuer_key, ca=False):
    t = datetime.now(timezone.utc)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,name)])
    return (x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(t-timedelta(days=1)).not_valid_after(t+timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=ca,path_length=1 if ca else None),critical=True)
        .add_extension(x509.KeyUsage(digital_signature=True,content_commitment=not ca,key_encipherment=False,
            data_encipherment=False,key_agreement=False,key_cert_sign=ca,crl_sign=ca,encipher_only=False,decipher_only=False),critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()),critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key.public_key()),critical=False)
        .sign(issuer_key,hashes.SHA256()))


def unsigned_pdf(with_form=False,assessment_type='final',title='Cơ sở dữ liệu',code='CSDL01',year='2025-2026',semester='1'):
    if 'TestFont' not in pdfmetrics.getRegisteredFontNames():
        candidates = [Path('C:/Windows/Fonts/arial.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
        font = next((p for p in candidates if p.exists()),None)
        if not font:
            raise RuntimeError('Install a Unicode font for Vietnamese PDF fixtures.')
        pdfmetrics.registerFont(TTFont('TestFont',str(font)))
    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=(595,842),pageCompression=0)
    pdf.setFont('TestFont',13)
    heading='BẢNG ĐIỂM THÀNH PHẦN' if assessment_type=='component' else 'BẢNG ĐIỂM KẾT THÚC HỌC PHẦN'
    for y,text in zip(range(790,650,-25),[heading,f'Mã LHP: {code}',
        f'Tên học phần: {title}',f'Năm học: {year}',f'Học kỳ: {semester}','Sinh viên thử nghiệm: 8.5']):
        pdf.drawString(40,y,text)
    if with_form:
        pdf.acroForm.textfield(name='Grade',value='8.5',x=100,y=570,width=100,height=20)
    pdf.save()
    return output.getvalue()


def grade_table_pdf(first_grade='8.5'):
    from reportlab.platypus import Table, TableStyle
    unsigned_pdf()  # Register the Vietnamese font used by the existing fixtures.
    output=io.BytesIO();pdf=canvas.Canvas(output,pagesize=(595,842))
    pdf.setFont('TestFont',12)
    for y,text in zip(range(810,700,-20),['BẢNG ĐIỂM KẾT THÚC HỌC PHẦN','Mã LHP: CSDL01',
        'Tên học phần: Cơ sở dữ liệu','Năm học: 2025-2026','Học kỳ: 1']):pdf.drawString(35,y,text)
    table=Table([['STT','SỐ THẺ','HỌ VÀ TÊN','ĐIỂM'],['1','24IT001','Sinh viên A',first_grade],['2','24IT002','Sinh viên B','0']],colWidths=[40,100,230,80])
    table.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'TestFont'),('GRID',(0,0),(-1,-1),0.5,(0,0,0))]))
    table.wrapOn(pdf,500,500);table.drawOn(pdf,35,600);pdf.save()
    return output.getvalue()


class TestPKI(Verifier):
    __test__ = False
    def __init__(self, path):
        super().__init__(path)
        ca_key = rsa.generate_private_key(public_exponent=65537,key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Test CA')])
        ca = certificate(ca_key,'Test CA',name,ca_key,ca=True)
        self.ca_key,self.ca_cert = ca_key,ca
        self.ca = asn_x509.Certificate.load(ca.public_bytes(serialization.Encoding.DER))
        self.signers = []
        self.fingerprints = []
        for label in ('Teacher','Head','SecondTeacher'):
            key = rsa.generate_private_key(public_exponent=65537,key_size=2048)
            cert = certificate(key,label,ca.subject,ca_key)
            asn = asn_x509.Certificate.load(cert.public_bytes(serialization.Encoding.DER))
            registry = SimpleCertificateStore();registry.register(self.ca)
            self.signers.append(signers.SimpleSigner(asn, asn_keys.PrivateKeyInfo.load(key.private_bytes(
                serialization.Encoding.DER,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())),registry))
            self.fingerprints.append(asn.sha256.hex())
        t=datetime.now(timezone.utc)
        crl=x509.CertificateRevocationListBuilder().issuer_name(ca.subject).last_update(t-timedelta(hours=1)).next_update(t+timedelta(days=1)).sign(ca_key,hashes.SHA256())
        self.crl = asn_crl.CertificateList.load(crl.public_bytes(serialization.Encoding.DER))

    def context(self):
        # Same strict policy as production, but use a locally signed CRL for isolated tests.
        return ValidationContext(trust_roots=[self.ca],crls=[self.crl],allow_fetching=False,revocation_mode='require')

    def sign(self, pdf, index, field_name=None):
        return signers.sign_pdf(IncrementalPdfFileWriter(io.BytesIO(pdf)),
            signature_meta=signers.PdfSignatureMetadata(field_name=field_name or ['Teacher','Head','SecondTeacher'][index]),
            signer=self.signers[index]).getvalue()


def seed(db: Database, pki):
    with db.connect() as conn:
        for uid,name,role,department,fp in [(1,'Giảng viên','teacher','CNTT',pki.fingerprints[0]),
             (2,'Trưởng khoa','head','CNTT',pki.fingerprints[1]),(3,'Đào tạo','training','VKU',''),
             (4,'Admin','admin','VKU',''),(5,'GV khác','teacher','KINHTE',''),(6,'TK khác','head','KINHTE',pki.fingerprints[1]),
             (7,'GV ký thứ hai','teacher','CNTT',pki.fingerprints[2])]:
            conn.execute('INSERT INTO users(id,email,name,role,department,password,fingerprint) VALUES(?,?,?,?,?,?,?)',
                (uid,f'{role}{uid}@vku.udn.vn',name,role,department,hash_password(PASSWORD),fp))
        conn.execute('INSERT INTO courses(code,title,year,semester,department,teacher_id) VALUES(?,?,?,?,?,?)',tuple(COURSE.values()))
        conn.execute('UPDATE courses SET co_teacher_id=7')
