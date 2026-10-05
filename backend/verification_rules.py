"""Narrow compatibility rules for tagged VGCA signature widgets."""
from pyhanko.pdf_utils import generic
from pyhanko.pdf_utils.reader import RawPdfPath
from pyhanko.sign.diff_analysis.commons import safe_whitelist
from pyhanko.sign.diff_analysis.rules_api import WhitelistRule, ReferenceUpdate, Context


def unchanged(a, b, except_keys=()):
    return ({k: a.raw_get(k) for k in a if k not in except_keys} ==
            {k: b.raw_get(k) for k in b if k not in except_keys})


class UnchangedInfoRule(WhitelistRule):
    def apply(self, old, new):
        a=old.trailer_view.get('/Info');b=new.trailer_view.get('/Info')
        a=a.get_object() if a is not None else None;b=b.get_object() if b is not None else None
        if a is not None and b is not None and unchanged(a,b):
            ar=old.trailer_view.get_value_as_reference('/Info')
            br=new.trailer_view.get_value_as_reference('/Info')
            for ref in safe_whitelist(old,ar,br):
                yield ReferenceUpdate(ref,context_checked=Context.from_absolute(old,RawPdfPath('/Info')))


class SignatureTagRule(WhitelistRule):
    def apply(self, old, new):
        a=old.root.get('/StructTreeRoot');b=new.root.get('/StructTreeRoot')
        a=a.get_object() if a is not None else None;b=b.get_object() if b is not None else None
        if a is None or b is None or not unchanged(a,b,('/ParentTree','/ParentTreeNextKey')):
            return
        ad=a.get('/K');bd=b.get('/K')
        ad=ad.get_object() if ad is not None else None;bd=bd.get_object() if bd is not None else None
        if not isinstance(ad,generic.DictionaryObject) or not isinstance(bd,generic.DictionaryObject):
            return
        if not unchanged(ad,bd,('/K',)):
            return
        ak=ad.get('/K');bk=bd.get('/K')
        if not isinstance(ak,generic.ArrayObject) or not isinstance(bk,generic.ArrayObject) or list(bk)[:len(ak)]!=list(ak):
            return
        added=list(bk)[len(ak):]
        if len(added)!=1 or not isinstance(added[0],generic.IndirectObject):
            return
        tag_ref=added[0];tag=tag_ref.get_object()
        if not old.is_ref_unassignable(tag_ref.reference) or set(tag)!={'/K','/P','/Pg','/S','/Type'}:
            return
        if tag['/S']!='/Form' or tag['/Type']!='/StructElem' or tag.raw_get('/P')!=b.raw_get('/K'):
            return
        objr=tag['/K']
        if not isinstance(objr,generic.DictionaryObject) or set(objr)!={'/Obj','/Type'} or objr['/Type']!='/OBJR':
            return
        widget_ref=objr.raw_get('/Obj');widget=widget_ref.get_object()
        if not isinstance(widget_ref,generic.IndirectObject) or not old.is_ref_unassignable(widget_ref.reference):
            return
        if widget.get('/FT')!='/Sig' or widget.get('/Subtype')!='/Widget' or '/V' not in widget:
            return
        if widget_ref not in new.root['/AcroForm']['/Fields'] or widget.raw_get('/P')!=tag.raw_get('/Pg'):
            return
        ap=a.get('/ParentTree');bp=b.get('/ParentTree')
        ap=ap.get_object() if ap is not None else None;bp=bp.get_object() if bp is not None else None
        if not isinstance(ap,generic.DictionaryObject) or not isinstance(bp,generic.DictionaryObject) or set(ap)!={'/Nums'} or set(bp)!={'/Nums'}:
            return
        an=list(ap['/Nums']);bn=list(bp['/Nums']);next_key=a.get('/ParentTreeNextKey')
        if len(bn)!=len(an)+2 or bn[-2:]!=[next_key,tag_ref] or b.get('/ParentTreeNextKey')!=next_key+1 or widget.get('/StructParent')!=next_key:
            return
        pairs=[]
        for i in range(0,len(an),2):
            av=an[i+1];bv=bn[i+1]
            if an[i]!=bn[i] or av.get_object()!=bv.get_object():
                return
            if av!=bv:
                if not isinstance(bv,generic.IndirectObject) or not old.is_ref_unassignable(bv.reference):
                    return
                pairs.append(bv.reference)
        # Only new tag/number-tree objects are approved; signature, page and
        # appearance objects remain subject to the existing signature rules.
        for ref in [tag_ref.reference,b.raw_get('/ParentTree').reference,*pairs]:
            if not old.is_ref_unassignable(ref):
                return
        for key,path in [('/StructTreeRoot',RawPdfPath('/Root','/StructTreeRoot'))]:
            for ref in safe_whitelist(old,old.root.raw_get(key).reference,new.root.raw_get(key).reference):
                yield ReferenceUpdate(ref,context_checked=Context.from_absolute(old,path))
        for ref in safe_whitelist(old,a.raw_get('/K').reference,b.raw_get('/K').reference):
            yield ReferenceUpdate(ref,context_checked=Context.from_absolute(old,RawPdfPath('/Root','/StructTreeRoot','/K')))
        for ref in [tag_ref.reference,b.raw_get('/ParentTree').reference,*pairs]:
            yield ReferenceUpdate(ref)
