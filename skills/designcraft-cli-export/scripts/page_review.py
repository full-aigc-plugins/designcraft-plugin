#!/usr/bin/env python3
"""校验绑定工程、页预览与固定排版 rubric 的审阅记录。"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

SCRIPT_DIR=Path(__file__).resolve().parent
ARTIFACT_VALIDATOR=SCRIPT_DIR/'artifact_manifest.py'
CONTRACT_VERSION='designcraft-page-review/v1'
RUBRIC_VERSION='designcraft-layout-rubric/v1'
CRITERIA=('hierarchy','whitespace','alignment','readability','cropping','crossPageConsistency')
CONCLUSIONS=('structure','visual','output','editability')
PREVIEW_EXTENSIONS={'.png','.jpg','.jpeg','.webp'}

def _sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def _relative_file(root,raw):
    if not isinstance(raw,str) or not raw or '\\' in raw:raise ValueError('review_path_invalid')
    relative=PurePosixPath(raw)
    if relative.is_absolute() or any(part in ('','.', '..') for part in relative.parts):raise ValueError('review_path_invalid')
    path=Path(root)
    for part in relative.parts:
        path=path/part
        if path.is_symlink():raise ValueError('review_file_invalid')
    if not path.is_file():raise ValueError('review_file_invalid')
    return path

def _status(value):
    if value not in ('PASS','FAIL','NOT_RUN'):raise ValueError('review_status_invalid')
    return value

def _time(value):
    if not isinstance(value,str):raise ValueError('review_time_invalid')
    try:parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError as error:raise ValueError('review_time_invalid') from error
    if parsed.tzinfo is None:raise ValueError('review_time_invalid')

def validate_review(root,artifact_manifest_path,review_path):
    root=Path(root).expanduser().absolute();artifact_manifest_path=Path(artifact_manifest_path).expanduser().absolute();review_path=Path(review_path).expanduser().absolute()
    if root.is_symlink() or not root.is_dir() or artifact_manifest_path.is_symlink() or review_path.is_symlink() or not artifact_manifest_path.is_file() or not review_path.is_file():raise ValueError('review_path_invalid')
    artifact_run=subprocess.run([sys.executable,'-I','-B',str(ARTIFACT_VALIDATOR),'--root',str(root),'--manifest',str(artifact_manifest_path)],capture_output=True,text=True,timeout=900)
    try:artifact_report=json.loads(artifact_run.stdout)
    except json.JSONDecodeError as error:raise ValueError('artifact_validator_output_invalid') from error
    artifact_result=artifact_report.get('result') if isinstance(artifact_report,dict) else None
    if artifact_run.returncode!=0 or not isinstance(artifact_report,dict) or artifact_report.get('status')!='PASS' or not isinstance(artifact_result,dict) or artifact_result.get('reopenEvidence')!='PASS':raise ValueError('artifact_reopen_not_verified')
    try:artifact_manifest=json.loads(artifact_manifest_path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as error:raise ValueError('artifact_manifest_invalid') from error
    try:review=json.loads(review_path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as error:raise ValueError('page_review_invalid') from error
    required={'schemaVersion','contractVersion','runId','projectSha256','artifactManifestSha256','rubricVersion','basis','reviewer','reviewedAt','pages','conclusions'}
    if not isinstance(review,dict) or set(review)!=required or type(review.get('schemaVersion')) is not int or review['schemaVersion']!=1 or review.get('contractVersion')!=CONTRACT_VERSION:raise ValueError('page_review_invalid')
    if review.get('runId')!=artifact_manifest.get('runId') or review.get('projectSha256')!=artifact_result.get('projectSha256') or review.get('artifactManifestSha256')!=_sha256(artifact_manifest_path):raise ValueError('page_review_identity_mismatch')
    if review.get('rubricVersion')!=RUBRIC_VERSION:raise ValueError('rubric_version_unsupported')
    basis=review.get('basis')
    if not isinstance(basis,dict) or set(basis)!={'type','path','sha256'} or basis.get('type') not in ('task-spec','reference-image'):raise ValueError('review_basis_invalid')
    basis_path=_relative_file(root,basis.get('path'))
    if _sha256(basis_path)!=basis.get('sha256'):raise ValueError('review_basis_identity_mismatch')
    reviewer=review.get('reviewer')
    if not isinstance(reviewer,dict) or reviewer.get('kind') not in ('human','automated') or not isinstance(reviewer.get('identity'),str) or not reviewer['identity'].strip():raise ValueError('reviewer_invalid')
    if reviewer['kind']=='human' and set(reviewer)!={'kind','identity'}:raise ValueError('reviewer_invalid')
    if reviewer['kind']=='automated' and (set(reviewer)!={'kind','identity','model'} or not isinstance(reviewer.get('model'),str) or not reviewer['model'].strip()):raise ValueError('reviewer_invalid')
    _time(review.get('reviewedAt'))
    expected_count=artifact_manifest['expectations']['pageCount'];pages=review.get('pages')
    if not isinstance(pages,list) or len(pages)!=expected_count:raise ValueError('review_page_count_mismatch')
    outcomes=[]
    for number,page in enumerate(pages,1):
        if not isinstance(page,dict) or set(page)!={'page','previewPath','previewSha256','checks'} or page.get('page')!=number:raise ValueError('review_page_identity_invalid')
        preview=_relative_file(root,page.get('previewPath'))
        if preview.suffix.lower() not in PREVIEW_EXTENSIONS or _sha256(preview)!=page.get('previewSha256'):raise ValueError('review_preview_identity_mismatch')
        checks=page.get('checks')
        if not isinstance(checks,list) or len(checks)!=len(CRITERIA):raise ValueError('review_criteria_incomplete')
        values={}
        for item in checks:
            if not isinstance(item,dict) or set(item)!={'criterion','status','note'} or item.get('criterion') not in CRITERIA or item['criterion'] in values or not isinstance(item.get('note'),str) or not item['note'].strip():raise ValueError('review_criteria_invalid')
            values[item['criterion']]=_status(item['status'])
        if set(values)!=set(CRITERIA):raise ValueError('review_criteria_incomplete')
        outcomes.extend(values.values())
    conclusions=review.get('conclusions')
    if not isinstance(conclusions,dict) or set(conclusions)!=set(CONCLUSIONS):raise ValueError('review_conclusions_invalid')
    for name in CONCLUSIONS:
        item=conclusions[name]
        if not isinstance(item,dict) or set(item)!={'status','note'} or not isinstance(item.get('note'),str) or not item['note'].strip():raise ValueError('review_conclusions_invalid')
        outcomes.append(_status(item['status']))
    status='FAIL' if 'FAIL' in outcomes else ('NOT_RUN' if 'NOT_RUN' in outcomes else 'PASS')
    return {'contractVersion':CONTRACT_VERSION,'status':status,'projectSha256':artifact_result['projectSha256'],'artifactManifestSha256':_sha256(artifact_manifest_path),'rubricVersion':RUBRIC_VERSION,'pagesReviewed':len(pages),'reviewSource':reviewer['kind'],'reviewerIdentity':reviewer['identity'],'basisType':basis['type'],'completeAcceptance':False,'acceptanceNote':'AV-03 structure binds review claims to current previews; it does not establish AV-01/02/04 or the truth of human/automated visual judgments.'}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True);parser.add_argument('--artifact-manifest',type=Path,required=True);parser.add_argument('--review',type=Path,required=True)
    args=parser.parse_args(argv)
    try:result=validate_review(args.root,args.artifact_manifest,args.review)
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        print(json.dumps({'status':'FAIL','error':str(error)},ensure_ascii=False));return 1
    print(json.dumps({'status':result['status'],'result':result},ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
