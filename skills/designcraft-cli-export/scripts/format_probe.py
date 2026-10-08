#!/usr/bin/env python3
"""Conservative offline structural checks for exported DesignCraft files."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import struct
import xml.etree.ElementTree as ET
import zipfile

CONTRACT_VERSION='designcraft-format-probe/v1'
FORMATS={'pdf','idml','epub','png','jpg','jpeg','webp','tif','tiff'}
PNG=b'\x89PNG\r\n\x1a\n'

def _base(path,fmt):
    data=path.read_bytes()
    return {'contractVersion':CONTRACT_VERSION,'format':fmt,'fileName':path.name,'byteCount':len(data),'sha256':hashlib.sha256(data).hexdigest(),
        'status':'FAIL','structure':'NOT_VERIFIED','visualContent':'NOT_VERIFIED','editability':'NOT_VERIFIED','lossAssessment':'NOT_VERIFIED',
        'targetAppReopen':'NOT_RUN','targetReaderReview':'NOT_RUN','pdfxExternalCertification':'NOT_RUN','completeAcceptance':False,
        'acceptanceNote':'结构探针仅检查可离线识别的文件特征；不证明视觉质量、内容正确、应用互操作、转换损失或完整验收。'}

def _xml(raw):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('xml_doctype_forbidden')
    return ET.fromstring(raw)

def _zip_members(path):
    try:
        archive=zipfile.ZipFile(path)
        infos=archive.infolist()
        names=[]
        for info in infos:
            name=info.filename
            posix=PurePosixPath(name)
            mode=(info.external_attr >> 16) & 0o170000
            if not name or '\\' in name or posix.is_absolute() or any(part in ('','..') for part in posix.parts) or mode==0o120000:
                archive.close();raise ValueError('zip_member_path_invalid')
            if name in names:
                archive.close();raise ValueError('zip_duplicate_member')
            names.append(name)
        bad=archive.testzip()
        if bad:
            archive.close();raise ValueError('zip_crc_invalid')
        return archive,infos,names
    except zipfile.BadZipFile as error:
        raise ValueError('zip_invalid') from error

def _pdf(path,result):
    raw=path.read_bytes()
    if not raw.startswith(b'%PDF-') or b'%%EOF' not in raw[-2048:]:raise ValueError('pdf_signature_invalid')
    objects=re.findall(rb'\b\d+\s+\d+\s+obj\b(.*?)\bendobj\b',raw,re.S)
    pages=[obj for obj in objects if re.search(rb'/Type\s*/Page(?!s)\b',obj)]
    if not pages:
        result['status']='PARTIAL';result['structure']='PARTIAL';result['limitations']=['page_objects_not_visible_in_basic_parser']
        return
    boxes=[]
    for obj in pages:
        found=re.search(rb'/MediaBox\s*\[\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\]',obj)
        if not found:continue
        x0,y0,x1,y1=(float(value) for value in found.groups())
        if x1<=x0 or y1<=y0:raise ValueError('pdf_page_box_invalid')
        boxes.append({'widthPoints':x1-x0,'heightPoints':y1-y0})
    result.update({'status':'PASS' if len(boxes)==len(pages) else 'PARTIAL','structure':'PASS' if len(boxes)==len(pages) else 'PARTIAL','pageCount':len(pages),'pageBoxes':boxes})
    if len(boxes)!=len(pages):result['limitations']=['inherited_or_unsupported_page_box']
    if re.search(rb'/Encrypt\b|/ObjStm\b',raw):
        result['status']='PARTIAL';result['structure']='PARTIAL';result.setdefault('limitations',[]).append('encrypted_or_compressed_objects_not_fully_parsed')

def _image(path,fmt,result):
    with path.open('rb') as stream:raw=stream.read(1024*1024)
    width=height=None
    if fmt=='png':
        if not raw.startswith(PNG) or len(raw)<33 or raw[12:16]!=b'IHDR' or struct.unpack('>I',raw[8:12])[0]!=13:raise ValueError('png_header_invalid')
        width,height=struct.unpack('>II',raw[16:24])
        if width<1 or height<1:raise ValueError('image_dimensions_invalid')
    elif fmt in ('jpg','jpeg'):
        if not raw.startswith(b'\xff\xd8'):raise ValueError('jpeg_signature_invalid')
        i=2
        while i+4<=len(raw):
            if raw[i]!=0xff:i+=1;continue
            while i<len(raw) and raw[i]==0xff:i+=1
            if i>=len(raw):break
            marker=raw[i];i+=1
            if marker in (0xd8,0xd9) or 0xd0<=marker<=0xd7:continue
            if i+2>len(raw):break
            length=int.from_bytes(raw[i:i+2],'big')
            if length<2 or i+length>len(raw):break
            if marker in (0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf):
                if length<7:break
                height=int.from_bytes(raw[i+3:i+5],'big');width=int.from_bytes(raw[i+5:i+7],'big');break
            i+=length
        if width is None:raise ValueError('jpeg_dimensions_unavailable')
    elif fmt=='webp':
        if len(raw)<30 or raw[:4]!=b'RIFF' or raw[8:12]!=b'WEBP':raise ValueError('webp_signature_invalid')
        chunk=raw[12:16]
        if chunk==b'VP8X':width=1+int.from_bytes(raw[24:27],'little');height=1+int.from_bytes(raw[27:30],'little')
        elif chunk==b'VP8L' and raw[20]==0x2f:
            bits=int.from_bytes(raw[21:25],'little');width=(bits&0x3fff)+1;height=((bits>>14)&0x3fff)+1
        else:raise ValueError('webp_dimensions_unsupported')
    elif fmt in ('tif','tiff'):
        if len(raw)<8 or raw[:2] not in (b'II',b'MM'):raise ValueError('tiff_signature_invalid')
        little=raw[:2]==b'II';endian='<' if little else '>'
        if struct.unpack(endian+'H',raw[2:4])[0]!=42:raise ValueError('tiff_bigtiff_unsupported')
        offset=struct.unpack(endian+'I',raw[4:8])[0]
        if offset+2>len(raw):raise ValueError('tiff_ifd_unavailable')
        count=struct.unpack(endian+'H',raw[offset:offset+2])[0];tags={}
        for index in range(count):
            start=offset+2+index*12
            if start+12>len(raw):raise ValueError('tiff_ifd_truncated')
            tag,kind,n=struct.unpack(endian+'HHI',raw[start:start+8])
            if tag in (256,257) and kind in (3,4) and n==1:tags[tag]=struct.unpack(endian+'H' if kind==3 else endian+'I',raw[start+8:start+(10 if kind==3 else 12)])[0]
        width,height=tags.get(256),tags.get(257)
        if width is None or height is None:raise ValueError('tiff_dimensions_unavailable')
    if width<1 or height<1:raise ValueError('image_dimensions_invalid')
    result.update({'status':'PASS','structure':'PASS','width':width,'height':height,'frameCount':'NOT_DETERMINED','editability':'NOT_APPLICABLE','limitations':['header_and_dimensions_only_full_decode_and_frame_count_not_checked']})

def _idml(path,result):
    archive,infos,names=_zip_members(path)
    if 'designmap.xml' not in names:raise ValueError('idml_designmap_missing')
    try:
        _xml(archive.read('designmap.xml'))
        stories=[name for name in names if name.startswith('Stories/') and name.lower().endswith('.xml')]
        for name in stories:_xml(archive.read(name))
    finally:archive.close()
    result.update({'status':'PASS','structure':'PASS','memberCount':len(names),'storyCount':len(stories),'editability':'NOT_VERIFIED'})

def _epub(path,result):
    archive,infos,names=_zip_members(path)
    try:
        if not infos or infos[0].filename!='mimetype' or infos[0].compress_type!=zipfile.ZIP_STORED or archive.read('mimetype')!=b'application/epub+zip':raise ValueError('epub_mimetype_invalid')
        if 'META-INF/container.xml' not in names:raise ValueError('epub_container_missing')
        container=_xml(archive.read('META-INF/container.xml'))
        rootfile=next((item for item in container.iter() if item.tag.rsplit('}',1)[-1]=='rootfile'),None)
        if rootfile is None:raise ValueError('epub_package_path_missing')
        package_path=rootfile.attrib.get('full-path','')
        package=PurePosixPath(package_path)
        if not package_path or package.is_absolute() or any(part in ('','..') for part in package.parts) or package_path not in names:raise ValueError('epub_package_path_invalid')
        doc=_xml(archive.read(package_path));base=package.parent
        manifest={}
        for item in doc.iter():
            if item.tag.rsplit('}',1)[-1]=='item':
                identifier=item.attrib.get('id');href=item.attrib.get('href')
                if not identifier or not href or identifier in manifest:raise ValueError('epub_manifest_item_invalid')
                member=str(base / PurePosixPath(href))
                if PurePosixPath(href).is_absolute() or any(part=='..' for part in PurePosixPath(href).parts) or member not in names:raise ValueError('epub_manifest_resource_missing')
                manifest[identifier]=member
        spine=[]
        for item in doc.iter():
            if item.tag.rsplit('}',1)[-1]=='itemref':
                ref=item.attrib.get('idref')
                if ref not in manifest:raise ValueError('epub_spine_reference_invalid')
                spine.append(ref)
        if not spine:raise ValueError('epub_spine_empty')
    finally:archive.close()
    result.update({'status':'PASS','structure':'PASS','memberCount':len(names),'manifestItemCount':len(manifest),'spineItemCount':len(spine),'targetReaderReview':'NOT_RUN','editability':'NOT_VERIFIED'})

def probe(file_path,fmt=None):
    path=Path(file_path)
    if path.is_symlink() or not path.is_file():raise ValueError('format_probe_file_invalid')
    fmt=(fmt or path.suffix.lstrip('.')).lower()
    if fmt not in FORMATS:raise ValueError('format_probe_format_unsupported')
    result=_base(path,fmt)
    try:
        if fmt=='pdf':_pdf(path,result)
        elif fmt in ('idml','epub'):
            (_idml if fmt=='idml' else _epub)(path,result)
        else:_image(path,fmt,result)
    except (OSError,ValueError,ET.ParseError,zipfile.BadZipFile,struct.error) as error:
        result['error']=str(error)
    return result

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--file',type=Path,required=True);parser.add_argument('--format',choices=sorted(FORMATS))
    args=parser.parse_args(argv)
    try:result=probe(args.file,args.format)
    except (OSError,ValueError) as error:result={'contractVersion':CONTRACT_VERSION,'status':'FAIL','error':str(error),'completeAcceptance':False}
    print(json.dumps(result,ensure_ascii=False,sort_keys=True));return 0 if result['status'] in ('PASS','PARTIAL') else 1

if __name__=='__main__':raise SystemExit(main())
