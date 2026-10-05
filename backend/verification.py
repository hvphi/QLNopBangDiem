import asyncio
import io
import re
from pathlib import Path
from asn1crypto import algos
from pyhanko.keys import load_cert_from_pemder
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import async_validate_pdf_signature
from pyhanko.sign.validation.status import SignatureCoverageLevel
from pyhanko.sign.diff_analysis import (
    ModificationLevel, StandardDiffPolicy, CatalogModificationRule,
    XrefStreamRule, ObjectStreamRule, DSSCompareRule, FormUpdatingRule,
    SigFieldCreationRule, SigFieldModificationRule,
)
from pyhanko_certvalidator import ValidationContext
from .verification_rules import UnchangedInfoRule, SignatureTagRule

# Only signature fields and PKI evidence may be appended. Generic form filling
# (e.g. changing a grade in an AcroForm) is deliberately absent from this policy.
SIGNATURE_ONLY_POLICY = StandardDiffPolicy(
    global_rules=[CatalogModificationRule(),
        UnchangedInfoRule().as_qualified(ModificationLevel.LTA_UPDATES),
        SignatureTagRule().as_qualified(ModificationLevel.FORM_FILLING),
        XrefStreamRule().as_qualified(ModificationLevel.LTA_UPDATES),
        ObjectStreamRule().as_qualified(ModificationLevel.LTA_UPDATES),
        DSSCompareRule().as_qualified(ModificationLevel.LTA_UPDATES)],
    form_rule=FormUpdatingRule(field_rules=[SigFieldCreationRule(allow_new_visible_after_certify=True),SigFieldModificationRule()]),
)


def certificate_emails(cert):
    emails = []
    subject_email = cert.subject.native.get('email_address')
    if isinstance(subject_email, str):
        emails.append(subject_email.strip().lower())
    elif isinstance(subject_email, list):
        emails.extend(str(e).strip().lower() for e in subject_email)
    for extension in cert['tbs_certificate']['extensions']:
        if extension['extn_id'].native == 'subject_alt_name':
            emails.extend(str(name.native).strip().lower() for name in extension['extn_value'].parsed
                          if name.name == 'rfc822_name')
    return sorted(set(emails))


def normalize_vgca_algorithm(sig):
    # Some VGCA exports put id-ecPublicKey in SignerInfo.signatureAlgorithm.
    # This is a key OID, not the ECDSA signature OID expected by pyHanko.
    # Only correct that exact case for an EC certificate and supported digest.
    # SignerInfo.signatureAlgorithm is outside the signed attributes; the PDF
    # byte range, CMS signed attributes, signature value and certificate stay intact.
    algorithm = sig.signer_info['signature_algorithm']['algorithm'].dotted
    if algorithm != '1.2.840.10045.2.1':
        return False
    key_algorithm = sig.signer_cert.public_key['algorithm']['algorithm'].native
    if key_algorithm != 'ec' or sig.md_algorithm not in ('sha256','sha384','sha512'):
        raise ValueError('Mã thuật toán VGCA không khớp khóa EC hoặc hash được hỗ trợ.')
    sig.signer_info['signature_algorithm'] = algos.SignedDigestAlgorithm({'algorithm':sig.md_algorithm+'_ecdsa'})
    return True


class Verifier:
    def __init__(self, trust_dir, timeout=15, policy='strict'):
        self.trust_dir = Path(trust_dir)
        self.timeout = timeout
        if policy not in ('strict', 'local'):
            raise ValueError('APP_SIGNATURE_POLICY phải là strict hoặc local.')
        self.policy = policy

    def context(self):
        if self.policy == 'local':
            # Offline cryptographic/integrity validation for the local workflow.
            # It does not establish issuer trust or certificate revocation status.
            return ValidationContext(trust_roots=[], allow_fetching=False, revocation_mode='soft-fail')
        roots = [load_cert_from_pemder(str(p)) for p in self.trust_dir.glob('*.pem')]
        if not roots:
            raise ValueError('Chưa cấu hình chứng thư gốc VGCA. Liên hệ quản trị viên.')
        # Require revocation evidence; network failure is never treated as valid.
        return ValidationContext(trust_roots=roots, allow_fetching=True, revocation_mode='require')

    async def verify(self, data, expected):
        if not data.startswith(b'%PDF-'):
            raise ValueError('Chỉ nhận file PDF gốc có chữ ký số.')
        identities = [value if isinstance(value,dict) else {'fingerprint':value} for value in expected]
        fingerprints = [value.get('fingerprint','').lower() for value in identities]
        if not identities or any(f and not re.fullmatch('[a-f0-9]{64}',f) for f in fingerprints):
            raise ValueError('Chưa liên kết chứng thư riêng cho từng người ký.')
        if self.policy == 'strict' and any(not f for f in fingerprints):
            raise ValueError('Chưa liên kết chứng thư cho từng vai trò ký. Cấu hình fingerprint trong trang quản trị.')
        if self.policy == 'local' and any(not f and not value.get('email') for f,value in zip(fingerprints,identities)):
            raise ValueError('Cần fingerprint hoặc email tài khoản để nhận diện người ký.')
        async def run():
            reader = PdfFileReader(io.BytesIO(data), strict=True)
            signatures = reader.embedded_regular_signatures
            if len(signatures) != len(expected):
                raise ValueError(f'PDF phải có đúng {len(expected)} chữ ký của người dùng.')
            context = self.context()
            reports = []
            for index,sig in enumerate(signatures):
                compatible = normalize_vgca_algorithm(sig)
                status = await async_validate_pdf_signature(sig, signer_validation_context=context,
                                                            diff_policy=SIGNATURE_ONLY_POLICY)
                if not status.intact or not status.valid:
                    raise ValueError(f'Chữ ký số thứ {index+1} không hợp lệ về mật mã hoặc PDF đã bị sửa.')
                if self.policy == 'strict' and not status.bottom_line:
                    raise ValueError('Chứng thư không tin cậy, hết hạn hoặc không kiểm tra được thu hồi. Kiểm tra cấu hình CA/CRL/OCSP.')
                if status.docmdp_ok is False or status.coverage not in (
                    SignatureCoverageLevel.ENTIRE_FILE, SignatureCoverageLevel.ENTIRE_REVISION
                ) or status.modification_level not in (ModificationLevel.NONE, ModificationLevel.LTA_UPDATES,
                                                       ModificationLevel.FORM_FILLING):
                    raise ValueError(f'Chữ ký thứ {index+1}: thay đổi sau ký không được phép hoặc không bao phủ đầy đủ bản PDF. '
                                     'Kiểm tra quyền ký thêm của PDF và dùng bản tải từ đúng hồ sơ.')
                fingerprint = status.signing_cert.sha256.hex()
                emails = certificate_emails(status.signing_cert)
                identity = identities[index]
                if fingerprints[index]:
                    if fingerprint != fingerprints[index]:
                        raise ValueError(f'Chứng thư người ký thứ {index+1} không khớp tài khoản đã liên kết.')
                elif str(identity.get('email','')).strip().lower() not in emails:
                    raise ValueError(f'Email chứng thư người ký thứ {index+1} không khớp tài khoản. Quản trị viên cần liên kết fingerprint đúng người ký.')
                reports.append({'fingerprint': fingerprint, 'field': sig.field_name, 'valid': True,
                                'signer_name': status.signing_cert.subject.native.get('common_name',''),
                                'signer_emails': emails, 'validation_policy': self.policy,
                                'trust_verified': self.policy == 'strict',
                                'revocation_verified': self.policy == 'strict',
                                'vgca_algorithm_compatibility': compatible})
            if signatures[-1].evaluate_signature_coverage() != SignatureCoverageLevel.ENTIRE_FILE:
                raise ValueError('PDF có phần thêm sau chữ ký cuối.')
            return reports
        try:
            return await asyncio.wait_for(run(), timeout=self.timeout)
        except asyncio.TimeoutError as e:
            raise ValueError('Xác thực quá thời gian; thử lại khi dịch vụ PKI sẵn sàng.') from e
        except ValueError:
            raise
        except Exception as e:
            raise ValueError('Không xác minh được PDF. File lỗi hoặc dịch vụ PKI chưa sẵn sàng.') from e
