#!/usr/bin/env python3
"""AV-01：重算原生业务分类，并绑定当前 AV-02 工程与重开会话。"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

CONTRACT_VERSION='designcraft-business-evidence/v1'
SCRIPTS=Path(__file__).resolve().parent

def _module(name):
    path=SCRIPTS/(name+'.py')
    if path.is_symlink() or not path.is_file():raise ValueError('business_validator_resource_invalid')
    spec=importlib.util.spec_from_file_location('business_'+name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def validate_business(root,manifest_path,receipt_path):
    """核对固定预检/PDF 业务证据；参数是交付根、AV-02 清单及原始回执路径。"""
    artifact=_module('artifact_manifest');gateway=_module('command_gateway')
    root=Path(root).expanduser().absolute();manifest_path=Path(manifest_path).expanduser().absolute();receipt_path=Path(receipt_path).expanduser().absolute()
    for path in (manifest_path,receipt_path):
        if path.is_symlink() or not path.is_file():raise ValueError('business_evidence_path_invalid')
    manifest=gateway.strict_json(manifest_path.read_text(encoding='utf-8'))
    av02=artifact.validate_manifest(root,manifest)
    if av02['status']!='PASS':raise ValueError('business_artifact_reopen_required')
    receipt=gateway.inspect_receipt(receipt_path,'designcraft')
    if type(receipt.get('schemaVersion')) is not int or receipt['schemaVersion']!=2 or receipt.get('status')!='NATIVE_EXIT_ZERO_REVIEW_REQUIRED' or type(receipt.get('exitCode')) is not int or receipt['exitCode']!=0 or receipt.get('started') is not True or receipt.get('terminationVerified') is not True or receipt.get('automaticReplay') is not False or receipt.get('completeAcceptance') is not False:raise ValueError('business_receipt_not_accepted')
    if receipt.get('runId')!=manifest['reopenCheck']['sessionId']:raise ValueError('business_reopen_session_mismatch')
    project_sha=av02['projectSha256']
    before=receipt.get('inputSha256');after=receipt.get('inputAfterSha256')
    if not isinstance(before,dict) or before!=after or project_sha not in before.values():raise ValueError('business_project_identity_mismatch')
    if receipt.get('workingCopyBeforeSha256')!=receipt.get('workingCopyAfterSha256'):raise ValueError('business_project_changed_during_reopen')
    resources=receipt.get('skillResourceSha256')
    if not isinstance(resources,dict) or not resources or resources!=receipt.get('skillResourceAfterSha256'):raise ValueError('business_resource_changed_during_reopen')
    lock_path=SCRIPTS/'runtime.lock.json'
    lock=gateway.strict_json(lock_path.read_text(encoding='utf-8'));runtime=receipt.get('runtimeIdentity')
    if not isinstance(runtime,dict):raise ValueError('business_runtime_identity_mismatch')
    expected=lock.get('artifacts',{}).get(runtime.get('platform'),{})
    if runtime.get('name')!=lock.get('artifact') or runtime.get('version')!=lock.get('resolvedVersion') or runtime.get('lockSha256')!=artifact._sha256(lock_path) or resources.get('runtime.lock.json')!=runtime.get('lockSha256') or runtime.get('expectedBinarySha256')!=expected.get('binarySha256') or not expected:raise ValueError('business_runtime_identity_mismatch')
    references=receipt.get('stepReferences')
    if not isinstance(references,list) or not references:raise ValueError('business_step_identity_required')
    assessment=gateway.assess_business_results(receipt.get('stdout'),references,'designcraft')
    if receipt.get('businessAssessment')!=assessment:raise ValueError('business_assessment_raw_result_mismatch')
    commands=[item['command'] for item in references]
    if commands.count('preflight.run')!=1 or commands.count('file.exportPdf')!=1:raise ValueError('business_preflight_pdf_required')
    allowed={'document.inspect','story.get','file.open','preflight.run','file.exportPdf','links.list'}
    if set(commands)-allowed:raise ValueError('business_command_not_supported')
    if assessment['status']!='PASS':raise ValueError('business_assessment_not_pass:'+assessment['status'])
    native=gateway.strict_json(receipt['stdout'])
    export=native['results'][commands.index('file.exportPdf')]
    pdfs=[item for item in manifest['artifacts'] if item['kind']=='export' and item['format']=='pdf']
    if len(pdfs)!=1 or export['bytes']!=pdfs[0]['byteCount'] or export['pages']!=manifest['expectations']['pageCount']:raise ValueError('business_export_identity_mismatch')
    return {'contractVersion':CONTRACT_VERSION,'status':'PASS','projectSha256':project_sha,'artifactManifestSha256':artifact._sha256(manifest_path),'receiptSha256':artifact._sha256(receipt_path),'reopenRunId':receipt['runId'],'businessAssessment':assessment,'completeAcceptance':False,'acceptanceNote':'Validates recorded raw results and current candidate binding; does not prove native execution, visual quality, target-application compatibility or external PDF/X certification.'}

def main():
    """提供自包含、只读的 AV-01 JSON 校验命令。"""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True);parser.add_argument('--artifact-manifest',required=True);parser.add_argument('--receipt',required=True)
    args=parser.parse_args()
    try:
        result=validate_business(args.root,args.artifact_manifest,args.receipt)
        print(json.dumps({'status':'PASS','result':result},ensure_ascii=False));return 0
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({'status':'FAIL','error':str(error)},ensure_ascii=False));return 1

if __name__=='__main__':raise SystemExit(main())
