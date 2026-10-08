#!/usr/bin/env python3
"""校验局部修订授权、受影响页面、修订前后审阅与导出身份关联。"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re

SCRIPT_DIR=Path(__file__).resolve().parent
ARTIFACT_SPEC=importlib.util.spec_from_file_location('artifact_manifest',SCRIPT_DIR/'artifact_manifest.py')
ARTIFACT_MODULE=importlib.util.module_from_spec(ARTIFACT_SPEC)
ARTIFACT_SPEC.loader.exec_module(ARTIFACT_MODULE)
REVIEW_SPEC=importlib.util.spec_from_file_location('page_review',SCRIPT_DIR/'page_review.py')
REVIEW_MODULE=importlib.util.module_from_spec(REVIEW_SPEC)
REVIEW_SPEC.loader.exec_module(REVIEW_MODULE)
CONTRACT_VERSION='designcraft-revision/v1'
SHA256=re.compile(r'[0-9a-f]{64}')

def _sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()

def _rooted_file(root,raw,reason):
    if not isinstance(raw,str) or not raw or '\\' in raw:
        raise ValueError(reason)
    relative=PurePosixPath(raw)
    if relative.is_absolute() or any(part in ('','.', '..') for part in relative.parts):
        raise ValueError(reason)
    path=Path(root)
    for part in relative.parts:
        path=path/part
        if path.is_symlink():
            raise ValueError(reason)
    if not path.is_file():
        raise ValueError(reason)
    return path

def _load_bound_json(root,entry,path_key,digest_key,error_prefix):
    path=_rooted_file(root,entry.get(path_key),f'{error_prefix}_path_invalid')
    digest=entry.get(digest_key)
    if not isinstance(digest,str) or not SHA256.fullmatch(digest) or _sha256(path)!=digest:
        raise ValueError(f'{error_prefix}_identity_mismatch')
    try:
        value=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as error:
        raise ValueError(f'{error_prefix}_invalid') from error
    return path,value

def _snapshot(value,page_count):
    if not isinstance(value,dict) or set(value)!={'schemaVersion','projectSha256','objects'} or type(value.get('schemaVersion')) is not int or value['schemaVersion']!=1 or not SHA256.fullmatch(str(value.get('projectSha256',''))):
        raise ValueError('revision_snapshot_invalid')
    objects=value.get('objects')
    if not isinstance(objects,list):
        raise ValueError('revision_snapshot_invalid')
    by_id={}
    for item in objects:
        if not isinstance(item,dict) or set(item)!={'id','page','contentSha256','storyId'}:
            raise ValueError('revision_snapshot_invalid')
        identifier=item.get('id');page=item.get('page');content=item.get('contentSha256');story=item.get('storyId')
        if not isinstance(identifier,str) or not identifier.strip() or identifier in by_id or type(page) is not int or not 1<=page<=page_count or not isinstance(content,str) or not SHA256.fullmatch(content) or (story is not None and (not isinstance(story,str) or not story.strip())):
            raise ValueError('revision_snapshot_invalid')
        by_id[identifier]=item
    return by_id

def _changed_ids(before,after):
    return {identifier for identifier in before.keys()|after.keys() if before.get(identifier)!=after.get(identifier)}

def _authorize(scope,changed,before,after):
    if not isinstance(scope,dict) or scope.get('type') not in ('page','object','story'):
        raise ValueError('revision_scope_invalid')
    kind=scope['type']
    if kind=='page' and (set(scope)!={'type','page'} or type(scope.get('page')) is not int or scope['page']<1):
        raise ValueError('revision_scope_invalid')
    if kind=='object' and (set(scope)!={'type','objectId'} or not isinstance(scope.get('objectId'),str) or not scope['objectId'].strip()):
        raise ValueError('revision_scope_invalid')
    if kind=='story' and (set(scope)!={'type','storyId'} or not isinstance(scope.get('storyId'),str) or not scope['storyId'].strip()):
        raise ValueError('revision_scope_invalid')
    if not changed:
        raise ValueError('revision_no_changes')
    for identifier in changed:
        records=[record for record in (before.get(identifier),after.get(identifier)) if record is not None]
        if kind=='page' and any(record['page']!=scope['page'] for record in records):
            raise ValueError('revision_out_of_scope')
        if kind=='object' and identifier!=scope['objectId']:
            raise ValueError('revision_out_of_scope')
        if kind=='story' and any(record['storyId']!=scope['storyId'] for record in records):
            raise ValueError('revision_out_of_scope')
    if kind=='object' and changed!={scope['objectId']}:
        raise ValueError('revision_out_of_scope')

def _affected_pages(changed,before,after):
    pages=set();story_ids=set()
    for identifier in changed:
        for record in (before.get(identifier),after.get(identifier)):
            if record is not None:
                pages.add(record['page'])
                if record['storyId'] is not None:
                    story_ids.add(record['storyId'])
    for objects in (before,after):
        for record in objects.values():
            if record['storyId'] in story_ids:
                pages.add(record['page'])
    return sorted(pages)

def validate_revision(root,revision_path):
    root=Path(root).expanduser().absolute();revision_path=Path(revision_path).expanduser().absolute()
    if root.is_symlink() or not root.is_dir() or revision_path.is_symlink() or not revision_path.is_file() or not revision_path.is_relative_to(root):
        raise ValueError('revision_path_invalid')
    try:
        revision=json.loads(revision_path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as error:
        raise ValueError('revision_invalid') from error
    required={'schemaVersion','contractVersion','authorization','before','after','affectedPages','revalidatedExports'}
    if not isinstance(revision,dict) or set(revision)!=required or type(revision.get('schemaVersion')) is not int or revision.get('schemaVersion')!=1 or revision.get('contractVersion')!=CONTRACT_VERSION:
        raise ValueError('revision_invalid')
    authorization=revision.get('authorization')
    if not isinstance(authorization,dict) or set(authorization)!={'scope','authorizationText'} or not isinstance(authorization.get('authorizationText'),str) or not authorization['authorizationText'].strip():
        raise ValueError('revision_authorization_invalid')
    evidence={}
    for label in ('before','after'):
        entry=revision.get(label)
        if not isinstance(entry,dict) or set(entry)!={'artifactManifestPath','artifactManifestSha256','pageReviewPath','pageReviewSha256','snapshotPath','snapshotSha256'}:
            raise ValueError('revision_evidence_invalid')
        artifact_path,artifact_manifest=_load_bound_json(root,entry,'artifactManifestPath','artifactManifestSha256',f'{label}_artifact_manifest')
        review_path,_=_load_bound_json(root,entry,'pageReviewPath','pageReviewSha256',f'{label}_page_review')
        snapshot_path,snapshot_value=_load_bound_json(root,entry,'snapshotPath','snapshotSha256',f'{label}_snapshot')
        artifact_root=artifact_path.parent
        artifact_result=ARTIFACT_MODULE.validate_manifest(artifact_root,artifact_manifest)
        if artifact_result['status']!='PASS' or artifact_result['reopenEvidence']!='PASS':
            raise ValueError(f'{label}_artifact_reopen_not_verified')
        review_result=REVIEW_MODULE.validate_review(artifact_root,artifact_path,review_path)
        if review_result['status']!='PASS':
            raise ValueError(f'{label}_page_review_not_passed')
        page_count=artifact_manifest['expectations']['pageCount']
        objects=_snapshot(snapshot_value,page_count)
        if snapshot_value['projectSha256']!=artifact_result['projectSha256']:
            raise ValueError(f'{label}_snapshot_project_mismatch')
        evidence[label]={'artifactPath':artifact_path,'artifactManifest':artifact_manifest,'artifactResult':artifact_result,
            'reviewPath':review_path,'reviewResult':review_result,'snapshotPath':snapshot_path,'objects':objects}
    before=evidence['before'];after=evidence['after']
    if before['artifactManifest']['runId']==after['artifactManifest']['runId'] or before['artifactResult']['projectSha256']==after['artifactResult']['projectSha256']:
        raise ValueError('revision_after_identity_not_new')
    changed=_changed_ids(before['objects'],after['objects'])
    _authorize(authorization['scope'],changed,before['objects'],after['objects'])
    affected=_affected_pages(changed,before['objects'],after['objects'])
    requested=revision.get('affectedPages')
    if not isinstance(requested,list) or any(type(page) is not int for page in requested) or requested!=sorted(set(requested)) or requested!=affected:
        raise ValueError('revision_affected_pages_mismatch')
    before_exports={item['id']:item for item in before['artifactManifest']['artifacts'] if item['kind']=='export'}
    after_exports={item['id']:item for item in after['artifactManifest']['artifacts'] if item['kind']=='export'}
    receipts=revision.get('revalidatedExports')
    if not before_exports or set(before_exports)!=set(after_exports) or not isinstance(receipts,list):
        raise ValueError('revision_export_set_mismatch')
    seen=set()
    for receipt in receipts:
        if not isinstance(receipt,dict) or set(receipt)!={'artifactId','format','sha256','status'} or receipt.get('status')!='PASS' or not isinstance(receipt.get('artifactId'),str) or not isinstance(receipt.get('format'),str) or not isinstance(receipt.get('sha256'),str) or not SHA256.fullmatch(receipt['sha256']):
            raise ValueError('revision_export_revalidation_invalid')
        identifier=receipt['artifactId'];current=after_exports.get(identifier)
        if identifier in seen or current is None or receipt['format']!=current['format'] or receipt['sha256']!=current['sha256']:
            raise ValueError('revision_export_identity_mismatch')
        seen.add(identifier)
    if seen!=set(after_exports):
        raise ValueError('revision_export_revalidation_incomplete')
    return {'contractVersion':CONTRACT_VERSION,'status':'PASS','scopeType':authorization['scope']['type'],'changedObjectCount':len(changed),
        'affectedPages':affected,'beforeProjectSha256':before['artifactResult']['projectSha256'],'afterProjectSha256':after['artifactResult']['projectSha256'],
        'beforeRunId':before['artifactManifest']['runId'],'afterRunId':after['artifactManifest']['runId'],'revalidatedExports':sorted(seen),
        'beforeReviewSha256':_sha256(before['reviewPath']),'afterReviewSha256':_sha256(after['reviewPath']),
        'completeAcceptance':False,'acceptanceNote':'AV-04 validates the recorded scope and evidence chain; it cannot prove the truth of native edits, authorization, snapshots, reviews or export judgments.'}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True);parser.add_argument('--revision',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        result=validate_revision(args.root,args.revision)
    except (OSError,ValueError,ImportError,AttributeError) as error:
        print(json.dumps({'status':'FAIL','error':str(error)},ensure_ascii=False));return 1
    print(json.dumps({'status':result['status'],'result':result},ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
