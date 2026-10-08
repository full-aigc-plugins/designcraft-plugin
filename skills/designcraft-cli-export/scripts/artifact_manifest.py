#!/usr/bin/env python3
"""校验 DesignCraft 交付文件身份与独立工程重开记录。"""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys
import uuid

FORMATS={'.designcraft':'designcraft','.pdf':'pdf','.idml':'idml','.epub':'epub','.png':'png','.jpg':'jpg','.jpeg':'jpeg','.webp':'webp','.tif':'tif','.tiff':'tiff'}

def _sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()

def _path(root,raw):
    if not isinstance(raw,str) or not raw or '\\' in raw:raise ValueError('artifact_path_invalid')
    relative=PurePosixPath(raw)
    if relative.is_absolute() or any(part in ('','.', '..') for part in relative.parts):raise ValueError('artifact_path_invalid')
    candidate=Path(root)
    for part in relative.parts:
        candidate=candidate/part
        if candidate.is_symlink():raise ValueError('artifact_file_invalid')
    if not candidate.is_file():raise ValueError('artifact_file_invalid')
    return candidate

def _positive_number(value):
    if type(value) is int:return value>0
    return type(value) is float and math.isfinite(value) and value>0

def _relative_name(value):
    if not isinstance(value,str) or not value or '\\' in value:return False
    path=PurePosixPath(value)
    return not path.is_absolute() and all(part not in ('','.', '..') for part in path.parts)

def _expectations(value):
    if not isinstance(value,dict) or set(value)!={'pageCount','pageDimensionsMm','criticalText','linkedAssets'}:raise ValueError('artifact_expectations_invalid')
    count=value['pageCount'];dimensions=value['pageDimensionsMm'];texts=value['criticalText'];assets=value['linkedAssets']
    if type(count) is not int or count<1 or not isinstance(dimensions,list) or len(dimensions)!=count:raise ValueError('artifact_expectations_invalid')
    if not isinstance(texts,list) or any(not isinstance(item,str) or not item.strip() for item in texts) or len(set(texts))!=len(texts):raise ValueError('artifact_expectations_invalid')
    if not isinstance(assets,list):raise ValueError('artifact_expectations_invalid')
    pages=[]
    for index,item in enumerate(dimensions,1):
        if not isinstance(item,dict) or set(item)!={'page','width','height'} or item.get('page')!=index or not _positive_number(item.get('width')) or not _positive_number(item.get('height')):raise ValueError('artifact_expectations_invalid')
        pages.append(item)
    asset_keys=set()
    for item in assets:
        if not isinstance(item,dict) or set(item)!={'path','sha256'} or not _relative_name(item.get('path')) or not re.fullmatch(r'[0-9a-f]{64}',str(item.get('sha256',''))):raise ValueError('artifact_expectations_invalid')
        key=(item['path'],item['sha256'])
        if key in asset_keys:raise ValueError('artifact_expectations_invalid')
        asset_keys.add(key)
    return {'pageCount':count,'pageDimensionsMm':pages,'criticalText':texts,'linkedAssets':assets}

def _check_reopen(root,manifest,project,project_sha,expectations):
    check=manifest.get('reopenCheck')
    if not isinstance(check,dict) or check.get('status') not in ('PASS','FAIL','NOT_RUN'):raise ValueError('reopen_check_invalid')
    if check['status']!='PASS':return check['status']
    required={'status','sessionId','projectSha256','pageCount','pageDimensionsMm','criticalText','linkedAssets','verifiedBy','verifiedAt'}
    if set(check)!=required:raise ValueError('reopen_check_invalid')
    if not isinstance(check['sessionId'],str) or not check['sessionId'].strip() or check['sessionId']==manifest['runId']:raise ValueError('reopen_session_identity_invalid')
    if check['projectSha256']!=project_sha:raise ValueError('reopen_project_identity_mismatch')
    if type(check['pageCount']) is not int or check['pageCount']!=expectations['pageCount']:raise ValueError('reopen_page_count_mismatch')
    dimensions=check['pageDimensionsMm']
    if not isinstance(dimensions,list) or len(dimensions)!=len(expectations['pageDimensionsMm']):raise ValueError('reopen_page_dimensions_mismatch')
    for expected,actual in zip(expectations['pageDimensionsMm'],dimensions):
        if not isinstance(actual,dict) or set(actual)!={'page','width','height'} or actual.get('page')!=expected['page'] or not _positive_number(actual.get('width')) or not _positive_number(actual.get('height')) or not math.isclose(actual['width'],expected['width'],rel_tol=0,abs_tol=0.01) or not math.isclose(actual['height'],expected['height'],rel_tol=0,abs_tol=0.01):raise ValueError('reopen_page_dimensions_mismatch')
    if not isinstance(check['criticalText'],list) or any(not isinstance(item,str) for item in check['criticalText']) or not set(expectations['criticalText']).issubset(check['criticalText']):raise ValueError('reopen_critical_text_mismatch')
    observed_assets=check['linkedAssets']
    if not isinstance(observed_assets,list):raise ValueError('reopen_linked_assets_mismatch')
    observed=set()
    for item in observed_assets:
        if not isinstance(item,dict) or set(item)!={'path','sha256'} or not _relative_name(item.get('path')) or not re.fullmatch(r'[0-9a-f]{64}',str(item.get('sha256',''))):raise ValueError('reopen_linked_assets_mismatch')
        observed.add((item['path'],item['sha256']))
    if not {(item['path'],item['sha256']) for item in expectations['linkedAssets']}.issubset(observed):raise ValueError('reopen_linked_assets_mismatch')
    if not isinstance(check['verifiedBy'],str) or not check['verifiedBy'].strip() or not isinstance(check['verifiedAt'],str):raise ValueError('reopen_check_invalid')
    try:
        observed=datetime.fromisoformat(check['verifiedAt'].replace('Z','+00:00'))
        if observed.tzinfo is None:raise ValueError('reopen_check_invalid')
    except ValueError as error:raise ValueError('reopen_check_invalid') from error
    return 'PASS'

def validate_manifest(root,manifest):
    root=Path(root).expanduser().absolute()
    if root.is_symlink() or not root.is_dir():raise ValueError('artifact_root_invalid')
    if not isinstance(manifest,dict) or set(manifest)!={'schemaVersion','runId','projectArtifactId','artifacts','expectations','reopenCheck'} or type(manifest.get('schemaVersion')) is not int or manifest['schemaVersion']!=1:raise ValueError('artifact_manifest_invalid')
    try:uuid.UUID(manifest.get('runId',''))
    except (ValueError,TypeError,AttributeError) as error:raise ValueError('artifact_run_id_invalid') from error
    expectations=_expectations(manifest.get('expectations'))
    artifacts=manifest.get('artifacts')
    if not isinstance(artifacts,list) or not artifacts:raise ValueError('artifact_manifest_invalid')
    identifiers=set();paths=set();projects=[];project_sha=None
    for item in artifacts:
        if not isinstance(item,dict) or set(item)!={'id','kind','path','format','byteCount','sha256'}:raise ValueError('artifact_manifest_invalid')
        identifier=item['id'];kind=item['kind'];fmt=item['format'];raw_path=item['path']
        if not isinstance(identifier,str) or not identifier or identifier in identifiers or kind not in ('project','export') or not isinstance(fmt,str):raise ValueError('artifact_manifest_invalid')
        identifiers.add(identifier)
        path=_path(root,raw_path)
        if raw_path in paths:raise ValueError('artifact_path_duplicate')
        paths.add(raw_path)
        expected_format=FORMATS.get(path.suffix.lower())
        if expected_format!=fmt or (kind=='project' and fmt!='designcraft') or (kind=='export' and fmt=='designcraft'):raise ValueError('artifact_format_mismatch')
        size=path.stat().st_size;digest=_sha256(path)
        if type(item['byteCount']) is not int or type(item['byteCount']) is bool or item['byteCount']!=size or not re.fullmatch(r'[0-9a-f]{64}',str(item['sha256'])) or item['sha256']!=digest:raise ValueError('artifact_identity_mismatch')
        if kind=='project':projects.append(identifier);project_sha=digest
    if projects!=[manifest['projectArtifactId']] or len(projects)!=1:raise ValueError('project_artifact_missing_or_ambiguous')
    project=next(item for item in artifacts if item['id']==projects[0])
    reopen_status=_check_reopen(root,manifest,project,project_sha,expectations)
    evidence_status='PASS' if reopen_status=='PASS' else ('FAIL' if reopen_status=='FAIL' else 'NOT_RUN')
    return {'contractVersion':'designcraft-artifact-manifest/v1','status':evidence_status,'artifactIdentity':'PASS','projectArtifactId':project['id'],'projectSha256':project_sha,'artifactCount':len(artifacts),'reopenEvidence':reopen_status,'completeAcceptance':False,'acceptanceNote':'AV-02 identity validation does not establish AV-01/03/04 or truth of native reopen evidence.'}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True);parser.add_argument('--manifest',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        manifest_path=args.manifest.expanduser().absolute()
        if manifest_path.is_symlink() or not manifest_path.is_file():raise ValueError('artifact_manifest_path_invalid')
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        result=validate_manifest(args.root,manifest)
    except (OSError,json.JSONDecodeError,ValueError) as error:
        print(json.dumps({'status':'FAIL','error':str(error)},ensure_ascii=False));return 1
    print(json.dumps({'status':result['status'],'result':result},ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
