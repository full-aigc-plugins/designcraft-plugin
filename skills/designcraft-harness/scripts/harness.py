#!/usr/bin/env python3
"""DesignCraft 本地任务状态库；不安装原生运行时，也不执行技能命令。"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
import uuid

REQUIRED_EVIDENCE=('AV-01','AV-02','AV-03','AV-04')
PACKAGE_ROOT=Path(__file__).resolve().parents[3]
EXTERNAL_COMMANDS=PACKAGE_ROOT/'skills/designcraft-use/scripts/commands.py'
ARTIFACT_VALIDATOR=PACKAGE_ROOT/'skills/designcraft-cli-export/scripts/artifact_manifest.py'
PAGE_REVIEW_VALIDATOR=PACKAGE_ROOT/'skills/designcraft-cli-export/scripts/page_review.py'
REVISION_VALIDATOR=PACKAGE_ROOT/'skills/designcraft-cli-export/scripts/revision_evidence.py'
TRANSITIONS={
 'PREPARED':{'EXECUTING','FAILED'},
 'EXECUTING':{'VERIFYING','RECONCILING','FAILED'},
 'RECONCILING':{'VERIFYING','PREPARED','FAILED'},
 'VERIFYING':{'REVIEW_REQUIRED','REVISION_REQUIRED','FAILED'},
 'REVIEW_REQUIRED':{'COMPLETED','REVISION_REQUIRED','FAILED'},
 'REVISION_REQUIRED':{'PREPARED','FAILED'},
 'COMPLETED':set(),'FAILED':set(),
}
TASK_FIELDS={'runId','nativeStatus','nativeReceiptRef','candidateSha256','artifactRefs','checkpointRefs','blockers','nextAction','reconciledRunId','recoveryAction','recoveryEvidence','revisionScope','revisionPageRefs'}
PROTECTED_RECOVERY_FIELDS={'recoveryPlan','recoveryPlanSha256','recoveryProof'}
SUPPORTED_SOURCE_VERSIONS={'0.1.0-dev.1'}
SUPPORTED_NATIVE_RECEIPT_SCHEMA=2
SUPPORTED_ARTIFACT_CONTRACTS={'designcraft-artifact-manifest/v1','designcraft-page-review/v1','designcraft-revision/v1'}

def _freshness_report():
    """读取证据清单的逐层新鲜度结果；失败时返回空状态而不放行能力。"""
    manifest=PACKAGE_ROOT/'evidence-manifest.json'
    checker=PACKAGE_ROOT/'scripts/evidence_freshness.py'
    if not manifest.is_file() or manifest.is_symlink() or not checker.is_file() or checker.is_symlink():return {}
    try:
        result=subprocess.run([sys.executable,'-I','-B',str(checker),str(manifest)],capture_output=True,text=True,timeout=20)
        report=json.loads(result.stdout)
        return report if isinstance(report,dict) and isinstance(report.get('records'),dict) else {}
    except (OSError,ValueError,subprocess.SubprocessError,json.JSONDecodeError):return {}

def now():
    """返回 UTC ISO-8601 时间。"""
    return datetime.now(timezone.utc).isoformat()

def task_id(value):
    """验证任务标识，避免路径遍历。"""
    try:return str(uuid.UUID(value))
    except (ValueError,TypeError,AttributeError) as error:raise ValueError('invalid_task_id') from error

def readiness_report(runtime_home=None,capability_evidence=None,required_commands=()):
    """只读核验插件候选、源契约、固定 CLI 与指定命令能力；不安装或调用原生写操作。"""
    components={}
    components['harnessInvocation']={'status':'READY','evidence':str(Path(__file__).resolve())}
    try:
        result=subprocess.run([sys.executable,'-I','-B',str(PACKAGE_ROOT/'scripts/validate_package.py')],capture_output=True,text=True,timeout=30)
        if result.returncode!=0:raise ValueError('plugin_validation_failed:'+result.stderr.strip())
        validation=json.loads(result.stdout)
        if not isinstance(validation,dict):raise ValueError('plugin_validation_report_invalid')
        components['pluginSnapshot']={'status':'READY' if result.returncode==0 and validation.get('snapshot')=='PASS' else 'UNAVAILABLE','evidence':validation}
    except (OSError,ValueError,subprocess.SubprocessError,json.JSONDecodeError) as error:
        components['pluginSnapshot']={'status':'UNAVAILABLE','reason':str(error)}
    source={}
    try:
        source=json.loads((PACKAGE_ROOT/'candidate-source.json').read_text(encoding='utf-8'))
        if not isinstance(source,dict):raise ValueError('candidate_source_invalid')
        valid=(source.get('sourceProject')=='designcraft-skills' and source.get('candidateType')=='local-unpublished-candidate'
               and source.get('sourceVersion') in SUPPORTED_SOURCE_VERSIONS and source.get('releaseTag') is None)
        components['sourceIdentity']={'status':'READY' if valid and components['pluginSnapshot']['status']=='READY' else 'UNAVAILABLE','sourceProject':source.get('sourceProject'),'sourceVersion':source.get('sourceVersion'),'releaseTag':source.get('releaseTag')}
    except (OSError,ValueError,json.JSONDecodeError) as error:
        components['sourceIdentity']={'status':'UNAVAILABLE','reason':str(error)}
    lock={};expected={};version=None;binary_sha=None;runtime_path=None
    try:
        lock=json.loads((PACKAGE_ROOT/'skills/designcraft-use/scripts/runtime.lock.json').read_text(encoding='utf-8'))
        if not isinstance(lock,dict) or not isinstance(lock.get('artifacts'),dict):raise ValueError('runtime_lock_invalid')
        version=lock.get('resolvedVersion');key=f'{platform.system().lower()}-{platform.machine().lower()}';expected=lock.get('artifacts',{}).get(key,{})
        if not isinstance(expected,dict):raise ValueError('runtime_platform_unsupported:'+key)
        binary_sha=expected.get('binarySha256')
        home=Path(runtime_home or os.environ.get('CRAFT_RUNTIME_HOME',str(Path.home()/'.local/share/craft-runtimes'))).expanduser().absolute()
        runtime_path=home/'designcraft'/str(version)
        binary=runtime_path/'designcraft-cli';receipt_path=runtime_path/'installation.json'
        if sys.version_info<(3,11):raise ValueError('python_version_unsupported')
        if not expected:raise ValueError('runtime_platform_unsupported:'+key)
        if runtime_path.is_symlink() or binary.is_symlink() or receipt_path.is_symlink():raise ValueError('runtime_path_unsafe')
        if not runtime_path.is_dir() or not binary.is_file() or not receipt_path.is_file():
            components['runtime']={'status':'UNAVAILABLE','expectedVersion':version,'runtimePath':str(runtime_path),'reason':'locked_cli_not_installed'}
        else:
            receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
            required=dict(expected,name='designcraft',version=str(version))
            valid_receipt=isinstance(receipt,dict) and all(receipt.get(name)==value for name,value in required.items())
            valid_binary=hashlib.sha256(binary.read_bytes()).hexdigest()==binary_sha
            components['runtime']={'status':'READY' if valid_receipt and valid_binary else 'DEGRADED','expectedVersion':version,'runtimePath':str(runtime_path),'binarySha256':hashlib.sha256(binary.read_bytes()).hexdigest() if binary.is_file() else None,'reason':None if valid_receipt and valid_binary else 'runtime_identity_mismatch'}
    except (OSError,ValueError,TypeError,json.JSONDecodeError) as error:
        components['runtime']={'status':'UNAVAILABLE','expectedVersion':version,'runtimePath':str(runtime_path) if runtime_path else None,'reason':str(error)}
    receipt_entry=PACKAGE_ROOT/'skills/designcraft-use/scripts/commands.py'
    components['sharedContract']={'status':'READY' if source.get('sourceVersion') in SUPPORTED_SOURCE_VERSIONS and receipt_entry.is_file() and all((PACKAGE_ROOT/'skills/designcraft-cli-export/scripts'/name).is_file() for name in ('artifact_manifest.py','page_review.py','revision_evidence.py')) else 'UNAVAILABLE','sourceVersion':source.get('sourceVersion'),'receiptSchemaVersion':SUPPORTED_NATIVE_RECEIPT_SCHEMA,'artifactContracts':sorted(SUPPORTED_ARTIFACT_CONTRACTS)}
    matrix={}
    try:
        matrix=json.loads((PACKAGE_ROOT/'support-matrix.json').read_text(encoding='utf-8'))
        if not isinstance(matrix,dict):matrix={}
    except (OSError,ValueError,json.JSONDecodeError):pass
    host=matrix.get('host',{}) if isinstance(matrix,dict) else {}
    if not isinstance(host,dict):host={}
    try:project_status=json.loads((PACKAGE_ROOT/'project-status.json').read_text(encoding='utf-8'))
    except (OSError,ValueError,json.JSONDecodeError):project_status={}
    fresh=_freshness_report();fresh_records=fresh.get('records',{}) if isinstance(fresh,dict) else {}
    def layer_readiness(record_id,project_key,matrix_value):
        recorded=fresh_records.get(record_id,'NOT_RUN')
        project_value=project_status.get(project_key) if isinstance(project_status,dict) else None
        if recorded=='PASS' and project_value=='PASS' and matrix_value=='PASS':return {'status':'READY','evidence':record_id,'freshness':'PASS'}
        if recorded in ('FAIL','STALE') or (recorded=='PASS' and (project_value!='PASS' or matrix_value!='PASS')):return {'status':'UNAVAILABLE','evidence':record_id,'freshness':recorded,'reason':'acceptance_evidence_failed_stale_or_status_mismatch'}
        return {'status':'NOT_CHECKED','evidence':record_id,'freshness':recorded}
    components['hostDiscovery']=layer_readiness('host','hostDiscovery',host.get('discovery'))
    components['modelDispatch']=layer_readiness('model-dispatch','modelDispatch',host.get('modelDispatch'))
    commands=tuple(required_commands)
    if not commands:
        components['requestCapability']={'status':'READY','commands':[],'mode':'read-only-preflight'}
    elif not capability_evidence:
        components['requestCapability']={'status':'NOT_CHECKED','commands':list(commands),'reason':'version-bound-native-capability-evidence_required'}
    else:
        try:
            evidence_path=Path(capability_evidence).expanduser().absolute()
            evidence_root=PACKAGE_ROOT/'evidence'
            if evidence_root.is_symlink() or evidence_path.is_symlink() or not evidence_path.is_file() or not evidence_path.resolve().is_relative_to(evidence_root.resolve()):raise ValueError('evidence_not_in_plugin_evidence_root')
            manifest=json.loads((PACKAGE_ROOT/'evidence-manifest.json').read_text(encoding='utf-8'))
            manifest_records=manifest.get('records') if isinstance(manifest,dict) else None
            bound_record=next((item for item in manifest_records if isinstance(item,dict) and item.get('id')=='native-capabilities'),None) if isinstance(manifest_records,list) else None
            relative_path=evidence_path.resolve().relative_to(PACKAGE_ROOT.resolve()).as_posix()
            if not isinstance(bound_record,dict) or bound_record.get('layer')!='native-capabilities' or not any(item.get('path')==relative_path for item in bound_record.get('artifacts',[]) if isinstance(item,dict)):
                raise ValueError('capability_evidence_record_missing')
            if fresh_records.get('native-capabilities')!='PASS':
                components['requestCapability']={'status':'UNAVAILABLE' if fresh_records.get('native-capabilities') in ('FAIL','STALE') else 'NOT_CHECKED','commands':list(commands),'reason':'capability_evidence_not_current','evidencePath':str(evidence_path)}
                statuses=[item['status'] for item in components.values()]
                overall='UNAVAILABLE' if 'UNAVAILABLE' in statuses else ('DEGRADED' if any(status in ('DEGRADED','NOT_CHECKED') for status in statuses) else 'READY')
                next_action='proceed_with_explicit_scope' if overall=='READY' else 'resolve_readiness_gaps_without_automatic_install_or_write'
                return {'contractVersion':'designcraft-readiness/v1','status':overall,'readOnly':True,'dispatchPrerequisitesMet':overall=='READY','userAuthorizationStillRequired':True,'components':components,'completeAcceptance':False,'nextAction':next_action}
            evidence=json.loads(evidence_path.read_text(encoding='utf-8'))
            if not isinstance(evidence,dict):raise ValueError('capability_evidence_invalid')
            identity=evidence.get('nativeCatalogIdentity')
            rows=evidence.get('nativeCommands')
            valid_identity=(evidence.get('schemaVersion')==1 and evidence.get('domain')=='designcraft' and evidence.get('nativeCatalogStatus')=='VERIFIED' and isinstance(identity,dict) and identity.get('cliVersion')==version and identity.get('binarySha256')==binary_sha and isinstance(identity.get('catalogSha256'),str) and re.fullmatch('[0-9a-f]{64}',identity['catalogSha256']) is not None)
            row_ids=[item.get('id') for item in rows if isinstance(item,dict)] if isinstance(rows,list) else []
            if not isinstance(rows,list) or len(row_ids)!=len(rows) or any(not isinstance(value,str) or not value for value in row_ids) or len(set(row_ids))!=len(row_ids):raise ValueError('capability_command_inventory_invalid')
            proven={item.get('id') for item in rows if item.get('validationStatus') in ('NATIVE_TESTED','HOST_TESTED')}
            missing=sorted(set(commands)-proven)
            status='READY' if valid_identity and not missing else ('DEGRADED' if valid_identity else 'UNAVAILABLE')
            components['requestCapability']={'status':status,'commands':list(commands),'missingCommands':missing,'evidencePath':str(evidence_path),'freshness':'PASS','catalogSha256':identity.get('catalogSha256') if isinstance(identity,dict) else None}
        except (OSError,ValueError,TypeError,json.JSONDecodeError) as error:
            components['requestCapability']={'status':'UNAVAILABLE','commands':list(commands),'reason':str(error)}
    statuses=[item['status'] for item in components.values()]
    overall='UNAVAILABLE' if 'UNAVAILABLE' in statuses else ('DEGRADED' if any(status in ('DEGRADED','NOT_CHECKED') for status in statuses) else 'READY')
    next_action='proceed_with_explicit_scope' if overall=='READY' else 'resolve_readiness_gaps_without_automatic_install_or_write'
    return {'contractVersion':'designcraft-readiness/v1','status':overall,'readOnly':True,'dispatchPrerequisitesMet':overall=='READY','userAuthorizationStillRequired':True,'components':components,'completeAcceptance':False,'nextAction':next_action}

class TaskStore:
    """以原子 JSON 更新和跨进程锁持久化任务状态。"""
    def __init__(self,root):
        self.root=Path(root).expanduser().resolve()
        if self.root==PACKAGE_ROOT or PACKAGE_ROOT in self.root.parents:raise ValueError('task_home_inside_plugin_cache')

    def _dir(self,identifier):return self.root/task_id(identifier)

    def _locked(self,identifier):
        self.root.mkdir(parents=True,exist_ok=True)
        lock_dir=self.root/'.locks'
        if lock_dir.is_symlink():raise ValueError('task_lock_invalid')
        lock_dir.mkdir(exist_ok=True)
        lock_path=lock_dir/(task_id(identifier)+'.lock')
        if lock_path.is_symlink():raise ValueError('task_lock_invalid')
        lock=lock_path.open('a+b')
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        return lock

    @staticmethod
    def _unlock(lock):
        fcntl.flock(lock.fileno(),fcntl.LOCK_UN);lock.close()

    def _load(self,identifier):
        folder=self._dir(identifier)
        if folder.is_symlink():raise ValueError('task_state_invalid')
        path=folder/'task.json'
        if path.is_symlink():raise ValueError('task_state_invalid')
        try:data=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError) as error:raise ValueError('task_state_invalid') from error
        required={'schemaVersion','taskId','state','revision','goal','authorizationScope','skillRoute','createdAt','updatedAt','requiredEvidence','evidenceRefs','artifactRefs','checkpointRefs','blockers','nextAction'}
        if not isinstance(data,dict) or not required.issubset(data) or data.get('schemaVersion')!=1 or data.get('taskId')!=task_id(identifier) or data.get('state') not in TRANSITIONS or type(data.get('revision')) is not int:
            raise ValueError('task_state_invalid')
        if not all(isinstance(data.get(key),list) for key in ('requiredEvidence','evidenceRefs','artifactRefs','checkpointRefs','blockers')) or any(not isinstance(item,str) for item in data['blockers']):raise ValueError('task_state_invalid')
        for item in data['evidenceRefs']:
            if not isinstance(item,dict) or not isinstance(item.get('file'),str) or Path(item['file']).name!=item['file'] or not re.fullmatch('[0-9a-f]{64}',str(item.get('sha256',''))):raise ValueError('task_state_invalid')
        # 旧状态文件可继续读取；新字段只在发生修订时要求写入。
        data.setdefault('revisionPageRefs',[])
        data.setdefault('recoveryPlan',None)
        data.setdefault('recoveryPlanSha256',None)
        data.setdefault('recoveryProof',None)
        if not isinstance(data['revisionPageRefs'],list) or any(not isinstance(item,str) or not item.strip() or '\n' in item for item in data['revisionPageRefs']) or len(set(data['revisionPageRefs']))!=len(data['revisionPageRefs']):raise ValueError('task_state_invalid')
        if data.get('revisionScope') is not None and not isinstance(data['revisionScope'],str):raise ValueError('task_state_invalid')
        if data['recoveryPlan'] is not None and (not isinstance(data['recoveryPlan'],dict) or data['recoveryPlan'].get('domain')!='designcraft' or not isinstance(data['recoveryPlan'].get('steps'),list) or not data['recoveryPlan']['steps']):raise ValueError('task_state_invalid')
        if data['recoveryPlan'] is None and data['recoveryPlanSha256'] is not None or data['recoveryPlan'] is not None and data.get('recoveryPlanSha256')!=self._canonical_sha256(data['recoveryPlan']):raise ValueError('task_state_invalid')
        if data['recoveryProof'] is not None and not isinstance(data['recoveryProof'],dict):raise ValueError('task_state_invalid')
        return data

    def _save(self,identifier,data):
        folder=self._dir(identifier);folder.mkdir(parents=True,exist_ok=True)
        if folder.is_symlink():raise ValueError('task_state_invalid')
        target=folder/'task.json';temporary=None
        if target.is_symlink():raise ValueError('task_state_invalid')
        try:
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=folder,prefix='.task-',delete=False) as stream:
                temporary=Path(stream.name);json.dump(data,stream,ensure_ascii=False,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,target)
            descriptor=os.open(folder,os.O_RDONLY)
            try:os.fsync(descriptor)
            finally:os.close(descriptor)
        finally:
            if temporary is not None and temporary.exists():temporary.unlink()

    def create(self,goal,authorization_scope,skill_route='designcraft-use'):
        """创建待执行任务；目标、操作范围和路由必须显式给出。"""
        for value in (goal,authorization_scope,skill_route):
            if not isinstance(value,str) or not value.strip():raise ValueError('task_fields_required')
        identifier=str(uuid.uuid4());lock=self._locked(identifier)
        try:
            stamp=now();data={'schemaVersion':1,'taskId':identifier,'state':'PREPARED','revision':0,'goal':goal.strip(),'authorizationScope':authorization_scope.strip(),'skillRoute':skill_route.strip(),'runId':None,'nativeStatus':'NOT_RUN','nativeReceiptRef':None,'candidateSha256':None,'reconciledRunId':None,'recoveryAction':None,'recoveryEvidence':[],'recoveryPlan':None,'recoveryPlanSha256':None,'recoveryProof':None,'revisionScope':None,'revisionPageRefs':[],'createdAt':stamp,'updatedAt':stamp,'requiredEvidence':list(REQUIRED_EVIDENCE),'evidenceRefs':[],'artifactRefs':[],'checkpointRefs':[],'blockers':[],'nextAction':'confirm_inputs_and_prepare'}
            self._save(identifier,data);return data
        finally:self._unlock(lock)

    def get(self,identifier):
        """读取任务，不修复或覆盖损坏状态。"""
        identifier=task_id(identifier);lock=self._locked(identifier)
        try:return self._load(identifier)
        finally:self._unlock(lock)

    @staticmethod
    def _check_revision(data,expected_revision):
        if type(expected_revision) is not int or data['revision']!=expected_revision:raise ValueError('task_revision_conflict')

    @staticmethod
    def _apply_updates(data,updates):
        if not isinstance(updates,dict) or set(updates)-TASK_FIELDS:raise ValueError('task_update_fields_invalid')
        for key,value in updates.items():
            if key=='candidateSha256' and value is not None and (not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value)):raise ValueError('candidate_identity_invalid')
            if key in ('artifactRefs','checkpointRefs','blockers') and not isinstance(value,list):raise ValueError('task_update_fields_invalid')
            if key=='revisionPageRefs' and (not isinstance(value,list) or not value or any(not isinstance(item,str) or not item.strip() or '\n' in item for item in value) or len(set(value))!=len(value)):raise ValueError('revision_page_refs_invalid')
            if key in ('runId','nativeReceiptRef','nextAction') and value is not None and not isinstance(value,str):raise ValueError('task_update_fields_invalid')
            if key=='nativeStatus' and value not in {'NOT_RUN','STARTING','NOT_STARTED','FAILED_OR_PARTIAL','UNKNOWN','NATIVE_EXIT_ZERO_REVIEW_REQUIRED'}:raise ValueError('task_update_fields_invalid')
            if key in ('recoveryEvidence',) and (not isinstance(value,list) or any(not isinstance(item,str) or not item for item in value)):raise ValueError('task_update_fields_invalid')
            if key in ('reconciledRunId','recoveryAction','revisionScope') and value is not None and not isinstance(value,str):raise ValueError('task_update_fields_invalid')
            data[key]=value

    def update(self,identifier,updates,expected_revision):
        """更新任务身份或引用，并拒绝基于旧 revision 的写入。"""
        if isinstance(updates,dict) and set(updates)&PROTECTED_RECOVERY_FIELDS:raise ValueError('recovery_fields_are_protected')
        identifier=task_id(identifier);lock=self._locked(identifier)
        try:
            data=self._load(identifier);self._check_revision(data,expected_revision);self._apply_updates(data,updates)
            data['revision']+=1;data['updatedAt']=now();self._save(identifier,data);return data
        finally:self._unlock(lock)

    def _fresh_evidence(self,data):
        found=set();folder=self._dir(data['taskId'])/'evidence'
        for entry in data['evidenceRefs']:
            path=folder/entry['file']
            if folder.is_symlink() or path.is_symlink():continue
            try:payload=json.loads(path.read_text(encoding='utf-8'))
            except (OSError,json.JSONDecodeError):continue
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            validator_valid=(entry.get('kind')!='AV-02' or self._valid_artifact_evidence(payload,data)) and (entry.get('kind')!='AV-03' or self._valid_page_review_evidence(payload,data)) and (entry.get('kind')!='AV-04' or self._valid_revision_evidence(payload,data))
            if digest==entry.get('sha256') and payload.get('taskId')==data['taskId'] and payload.get('status')=='PASS' and payload.get('candidateSha256')==data.get('candidateSha256') and payload.get('kind')==entry.get('kind') and validator_valid:
                found.add(entry['kind'])
        return found

    @staticmethod
    def _run_artifact_validator(root,manifest):
        if not ARTIFACT_VALIDATOR.is_file() or ARTIFACT_VALIDATOR.is_symlink():raise ValueError('artifact_validator_missing_or_unsafe')
        root=Path(root).expanduser().absolute();manifest=Path(manifest).expanduser().absolute()
        if root.is_symlink() or manifest.is_symlink() or not manifest.is_file():raise ValueError('artifact_manifest_path_invalid')
        result=subprocess.run([sys.executable,'-I','-B',str(ARTIFACT_VALIDATOR),'--root',str(root),'--manifest',str(manifest)],capture_output=True,text=True,timeout=900)
        try:report=json.loads(result.stdout)
        except json.JSONDecodeError as error:raise ValueError('artifact_validator_output_invalid') from error
        if result.returncode!=0 or not isinstance(report,dict):raise ValueError('artifact_manifest_invalid')
        return report,root,manifest

    def _valid_artifact_evidence(self,payload,data):
        try:
            root=payload['artifactRoot'];manifest=payload['manifestPath'];report,root_path,manifest_path=self._run_artifact_validator(root,manifest)
            result=report.get('result')
            return (
                payload.get('verifiedBy')=='designcraft-harness'
                and payload.get('manifestSha256')==hashlib.sha256(manifest_path.read_bytes()).hexdigest()
                and payload.get('validatorSha256')==hashlib.sha256(ARTIFACT_VALIDATOR.read_bytes()).hexdigest()
                and payload.get('artifactReport')==report
                and report.get('status')=='PASS'
                and isinstance(result,dict)
                and result.get('artifactIdentity')=='PASS'
                and result.get('contractVersion')=='designcraft-artifact-manifest/v1'
                and result.get('reopenEvidence')=='PASS'
                and result.get('projectSha256')==data.get('candidateSha256')
                and result.get('completeAcceptance') is False
            )
        except (OSError,KeyError,TypeError,ValueError,subprocess.SubprocessError):
            return False

    @staticmethod
    def _run_page_review_validator(root,manifest,review):
        if not PAGE_REVIEW_VALIDATOR.is_file() or PAGE_REVIEW_VALIDATOR.is_symlink():raise ValueError('page_review_validator_missing_or_unsafe')
        root=Path(root).expanduser().absolute();manifest=Path(manifest).expanduser().absolute();review=Path(review).expanduser().absolute()
        if root.is_symlink() or not root.is_dir() or manifest.is_symlink() or review.is_symlink() or not manifest.is_file() or not review.is_file():raise ValueError('page_review_path_invalid')
        result=subprocess.run([sys.executable,'-I','-B',str(PAGE_REVIEW_VALIDATOR),'--root',str(root),'--artifact-manifest',str(manifest),'--review',str(review)],capture_output=True,text=True,timeout=900)
        try:report=json.loads(result.stdout)
        except json.JSONDecodeError as error:raise ValueError('page_review_validator_output_invalid') from error
        if result.returncode!=0 or not isinstance(report,dict):raise ValueError('page_review_invalid')
        return report,root,manifest,review

    @staticmethod
    def _run_revision_validator(root,revision):
        if not REVISION_VALIDATOR.is_file() or REVISION_VALIDATOR.is_symlink():raise ValueError('revision_validator_missing_or_unsafe')
        root=Path(root).expanduser().absolute();revision=Path(revision).expanduser().absolute()
        if root.is_symlink() or not root.is_dir() or revision.is_symlink() or not revision.is_file() or not revision.is_relative_to(root):raise ValueError('revision_path_invalid')
        result=subprocess.run([sys.executable,'-I','-B',str(REVISION_VALIDATOR),'--root',str(root),'--revision',str(revision)],capture_output=True,text=True,timeout=900)
        try:report=json.loads(result.stdout)
        except json.JSONDecodeError as error:raise ValueError('revision_validator_output_invalid') from error
        if not isinstance(report,dict):raise ValueError('revision_validator_output_invalid')
        if result.returncode!=0:raise ValueError(report.get('error','revision_invalid'))
        return report,root,revision

    def _valid_revision_evidence(self,payload,data):
        try:
            root=payload['revisionRoot'];revision=payload['revisionPath']
            report,root_path,revision_path=self._run_revision_validator(root,revision)
            result=report.get('result')
            return (
                payload.get('verifiedBy')=='designcraft-harness'
                and payload.get('revisionSha256')==hashlib.sha256(revision_path.read_bytes()).hexdigest()
                and payload.get('validatorSha256')==hashlib.sha256(REVISION_VALIDATOR.read_bytes()).hexdigest()
                and payload.get('revisionReport')==report
                and report.get('status')=='PASS'
                and isinstance(result,dict)
                and result.get('contractVersion')=='designcraft-revision/v1'
                and result.get('status')=='PASS'
                and result.get('afterProjectSha256')==data.get('candidateSha256')
                and result.get('completeAcceptance') is False
            )
        except (OSError,KeyError,TypeError,ValueError,subprocess.SubprocessError,json.JSONDecodeError):
            return False

    def verify_revision(self,identifier,root,revision,expected_revision):
        """经技能源 AV-04 校验器核对范围、影响页和修订后导出的证据。"""
        identifier=task_id(identifier);task=self.get(identifier);self._check_revision(task,expected_revision)
        if task['state'] not in ('VERIFYING','REVIEW_REQUIRED'):raise ValueError('revision_verification_state_required')
        if not task.get('candidateSha256'):raise ValueError('candidate_identity_required')
        current=self._fresh_evidence(task)
        if 'AV-02' not in current:raise ValueError('artifact_reopen_not_verified')
        if 'AV-03' not in current:raise ValueError('page_review_not_verified')
        report,root_path,revision_path=self._run_revision_validator(root,revision)
        result=report.get('result') if isinstance(report,dict) else None
        if report.get('status')!='PASS' or not isinstance(result,dict) or result.get('contractVersion')!='designcraft-revision/v1' or result.get('completeAcceptance') is not False:raise ValueError('revision_not_pass')
        if result.get('afterProjectSha256')!=task['candidateSha256']:raise ValueError('revision_candidate_mismatch')
        payload={'taskId':identifier,'kind':'AV-04','status':'PASS','candidateSha256':task['candidateSha256'],
            'revisionRoot':str(root_path),'revisionPath':str(revision_path),'revisionSha256':hashlib.sha256(revision_path.read_bytes()).hexdigest(),
            'validatorSha256':hashlib.sha256(REVISION_VALIDATOR.read_bytes()).hexdigest(),'revisionReport':report,'verifiedBy':'designcraft-harness'}
        folder=self._dir(identifier)/'evidence';folder.mkdir(parents=True,exist_ok=True)
        if folder.is_symlink():raise ValueError('evidence_path_invalid')
        filename='AV-04-'+hashlib.sha256((payload['revisionSha256']+payload['candidateSha256']).encode()).hexdigest()+'.json';target=folder/filename
        encoded=(json.dumps(payload,ensure_ascii=False,indent=2)+'\n').encode()
        if target.exists():
            if target.is_symlink() or target.read_bytes()!=encoded:raise ValueError('evidence_file_conflict')
        else:
            temporary=None
            try:
                with tempfile.NamedTemporaryFile(mode='wb',dir=folder,prefix='.revision-evidence-',delete=False) as stream:
                    temporary=Path(stream.name);stream.write(encoded);stream.flush();os.fsync(stream.fileno())
                os.replace(temporary,target)
            finally:
                if temporary is not None and temporary.exists():temporary.unlink()
        return self.attach_evidence(identifier,filename,expected_revision)

    def _artifact_manifest_hashes(self,data):
        """返回仍有效的 AV-02 清单摘要，供 AV-03 绑定同一份重开证据。"""
        folder=self._dir(data['taskId'])/'evidence';hashes=set()
        for entry in data['evidenceRefs']:
            if entry.get('kind')!='AV-02':continue
            path=folder/entry['file']
            if folder.is_symlink() or path.is_symlink():continue
            try:
                payload=json.loads(path.read_text(encoding='utf-8'))
                if hashlib.sha256(path.read_bytes()).hexdigest()!=entry.get('sha256'):continue
                if payload.get('taskId')!=data['taskId'] or payload.get('candidateSha256')!=data.get('candidateSha256') or payload.get('status')!='PASS' or not self._valid_artifact_evidence(payload,data):continue
                hashes.add(payload['manifestSha256'])
            except (OSError,KeyError,TypeError,ValueError,json.JSONDecodeError,subprocess.SubprocessError):
                continue
        return hashes

    def _valid_page_review_evidence(self,payload,data):
        try:
            root=payload['artifactRoot'];manifest=payload['manifestPath'];review=payload['reviewPath']
            report,root_path,manifest_path,review_path=self._run_page_review_validator(root,manifest,review)
            result=report.get('result')
            manifest_sha=hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            return (
                'AV-02' in self._fresh_evidence_without_page_review(data)
                and manifest_sha in self._artifact_manifest_hashes(data)
                and payload.get('verifiedBy')=='designcraft-harness'
                and payload.get('manifestSha256')==manifest_sha
                and payload.get('reviewSha256')==hashlib.sha256(review_path.read_bytes()).hexdigest()
                and payload.get('validatorSha256')==hashlib.sha256(PAGE_REVIEW_VALIDATOR.read_bytes()).hexdigest()
                and payload.get('pageReviewReport')==report
                and report.get('status')=='PASS'
                and isinstance(result,dict)
                and result.get('contractVersion')=='designcraft-page-review/v1'
                and result.get('projectSha256')==data.get('candidateSha256')
                and result.get('artifactManifestSha256')==manifest_sha
                and result.get('completeAcceptance') is False
            )
        except (OSError,KeyError,TypeError,ValueError,subprocess.SubprocessError):
            return False

    def _fresh_evidence_without_page_review(self,data):
        """避免 AV-03 freshness 递归，同时复用 AV-02 的真实校验。"""
        found=set();folder=self._dir(data['taskId'])/'evidence'
        for entry in data['evidenceRefs']:
            if entry.get('kind')!='AV-02':continue
            path=folder/entry['file']
            if folder.is_symlink() or path.is_symlink():continue
            try:
                payload=json.loads(path.read_text(encoding='utf-8'))
                if hashlib.sha256(path.read_bytes()).hexdigest()==entry.get('sha256') and payload.get('taskId')==data['taskId'] and payload.get('status')=='PASS' and payload.get('candidateSha256')==data.get('candidateSha256') and self._valid_artifact_evidence(payload,data):found.add('AV-02')
            except (OSError,json.JSONDecodeError,ValueError,TypeError,KeyError,subprocess.SubprocessError):continue
        return found

    def verify_artifact_manifest(self,identifier,root,manifest,expected_revision):
        """通过技能源公开清单校验入口登记与当前工程重开绑定的 AV-02 证据。"""
        identifier=task_id(identifier);task=self.get(identifier);self._check_revision(task,expected_revision)
        if task['state'] not in ('VERIFYING','REVIEW_REQUIRED'):raise ValueError('artifact_verification_state_required')
        if not task.get('candidateSha256'):raise ValueError('candidate_identity_required')
        report,root_path,manifest_path=self._run_artifact_validator(root,manifest)
        result=report.get('result') if isinstance(report,dict) else None
        if report.get('status')=='NOT_RUN' or not isinstance(result,dict) or result.get('reopenEvidence')=='NOT_RUN':raise ValueError('artifact_reopen_not_verified')
        if report.get('status')!='PASS' or result.get('artifactIdentity')!='PASS' or result.get('reopenEvidence')!='PASS' or result.get('contractVersion')!='designcraft-artifact-manifest/v1':raise ValueError('artifact_reopen_failed')
        if result.get('projectSha256')!=task['candidateSha256']:raise ValueError('artifact_candidate_mismatch')
        manifest_sha=hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        payload={'taskId':identifier,'kind':'AV-02','status':'PASS','candidateSha256':task['candidateSha256'],'artifactRoot':str(root_path),'manifestPath':str(manifest_path),'manifestSha256':manifest_sha,'validatorSha256':hashlib.sha256(ARTIFACT_VALIDATOR.read_bytes()).hexdigest(),'artifactReport':report,'verifiedBy':'designcraft-harness'}
        folder=self._dir(identifier)/'evidence';folder.mkdir(parents=True,exist_ok=True)
        if folder.is_symlink():raise ValueError('evidence_path_invalid')
        filename='AV-02-'+manifest_sha+'.json';target=folder/filename
        encoded=(json.dumps(payload,ensure_ascii=False,indent=2)+'\n').encode()
        if target.exists():
            if target.is_symlink() or target.read_bytes()!=encoded:raise ValueError('evidence_file_conflict')
        else:
            temporary=None
            try:
                with tempfile.NamedTemporaryFile(mode='wb',dir=folder,prefix='.artifact-evidence-',delete=False) as stream:
                    temporary=Path(stream.name);stream.write(encoded);stream.flush();os.fsync(stream.fileno())
                os.replace(temporary,target)
            finally:
                if temporary is not None and temporary.exists():temporary.unlink()
        return self.attach_evidence(identifier,filename,expected_revision)

    def verify_page_review(self,identifier,root,manifest,review,expected_revision):
        """经源方公开 AV-03 校验器验证后，登记当前 AV-02/工程/预览绑定的页审阅。"""
        identifier=task_id(identifier);task=self.get(identifier);self._check_revision(task,expected_revision)
        if task['state'] not in ('VERIFYING','REVIEW_REQUIRED'):raise ValueError('page_review_state_required')
        if not task.get('candidateSha256'):raise ValueError('candidate_identity_required')
        if 'AV-02' not in self._fresh_evidence_without_page_review(task):raise ValueError('artifact_reopen_not_verified')
        report,root_path,manifest_path,review_path=self._run_page_review_validator(root,manifest,review)
        result=report.get('result') if isinstance(report,dict) else None
        if report.get('status')!='PASS' or not isinstance(result,dict) or result.get('status')!='PASS' or result.get('contractVersion')!='designcraft-page-review/v1' or result.get('completeAcceptance') is not False:raise ValueError('page_review_not_pass')
        manifest_sha=hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        if manifest_sha not in self._artifact_manifest_hashes(task):raise ValueError('page_review_artifact_manifest_mismatch')
        if result.get('projectSha256')!=task['candidateSha256']:raise ValueError('page_review_candidate_mismatch')
        payload={'taskId':identifier,'kind':'AV-03','status':'PASS','candidateSha256':task['candidateSha256'],'artifactRoot':str(root_path),'manifestPath':str(manifest_path),'manifestSha256':manifest_sha,'reviewPath':str(review_path),'reviewSha256':hashlib.sha256(review_path.read_bytes()).hexdigest(),'validatorSha256':hashlib.sha256(PAGE_REVIEW_VALIDATOR.read_bytes()).hexdigest(),'pageReviewReport':report,'verifiedBy':'designcraft-harness'}
        folder=self._dir(identifier)/'evidence';folder.mkdir(parents=True,exist_ok=True)
        if folder.is_symlink():raise ValueError('evidence_path_invalid')
        filename='AV-03-'+hashlib.sha256((manifest_sha+payload['reviewSha256']).encode()).hexdigest()+'.json';target=folder/filename
        encoded=(json.dumps(payload,ensure_ascii=False,indent=2)+'\n').encode()
        if target.exists():
            if target.is_symlink() or target.read_bytes()!=encoded:raise ValueError('evidence_file_conflict')
        else:
            temporary=None
            try:
                with tempfile.NamedTemporaryFile(mode='wb',dir=folder,prefix='.page-review-evidence-',delete=False) as stream:
                    temporary=Path(stream.name);stream.write(encoded);stream.flush();os.fsync(stream.fileno())
                os.replace(temporary,target)
            finally:
                if temporary is not None and temporary.exists():temporary.unlink()
        return self.attach_evidence(identifier,filename,expected_revision)

    def attach_evidence(self,identifier,file_name,expected_revision):
        """登记任务目录中的 PASS 证据，并绑定当前候选摘要。"""
        identifier=task_id(identifier)
        if not isinstance(file_name,str) or Path(file_name).name!=file_name or file_name in ('','.','..'):raise ValueError('evidence_path_invalid')
        lock=self._locked(identifier)
        try:
            data=self._load(identifier);self._check_revision(data,expected_revision)
            if not data.get('candidateSha256'):raise ValueError('candidate_identity_required')
            path=self._dir(identifier)/'evidence'/file_name
            if path.parent.is_symlink() or path.is_symlink():raise ValueError('evidence_path_invalid')
            try:payload=json.loads(path.read_text(encoding='utf-8'))
            except (OSError,json.JSONDecodeError) as error:raise ValueError('evidence_file_invalid') from error
            if not isinstance(payload,dict):raise ValueError('evidence_file_invalid')
            if not isinstance(payload,dict) or payload.get('taskId')!=identifier or payload.get('candidateSha256')!=data['candidateSha256']:raise ValueError('evidence_candidate_mismatch')
            kind=payload.get('kind')
            if kind not in data['requiredEvidence'] or payload.get('status')!='PASS':raise ValueError('evidence_not_accepted')
            if kind=='AV-02' and not self._valid_artifact_evidence(payload,data):raise ValueError('artifact_reopen_not_verified')
            if kind=='AV-03' and not self._valid_page_review_evidence(payload,data):raise ValueError('page_review_not_verified')
            if kind=='AV-04' and not self._valid_revision_evidence(payload,data):raise ValueError('revision_not_verified')
            reference={'kind':kind,'file':file_name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'candidateSha256':data['candidateSha256']}
            data['evidenceRefs']=[item for item in data['evidenceRefs'] if item.get('kind')!=kind]+[reference]
            data['revision']+=1;data['updatedAt']=now();self._save(identifier,data);return data
        finally:self._unlock(lock)

    @staticmethod
    def _read_recovery_json(path):
        """读取显式提供的恢复证据文件，拒绝符号链接与非 JSON 对象。"""
        path=Path(path).expanduser()
        if path.is_symlink() or not path.is_file():raise ValueError('source_recovery_evidence_missing_or_unsafe')
        try:value=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError) as error:raise ValueError('source_recovery_evidence_invalid') from error
        if not isinstance(value,dict):raise ValueError('source_recovery_evidence_invalid')
        return path,value

    @staticmethod
    def _canonical_sha256(value):
        return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest()

    def _verify_recovery_proof_bundle(self,data):
        """执行恢复前重验用户任务目录内的合同证据与保存工程。"""
        proof=data.get('recoveryProof')
        if not isinstance(proof,dict) or proof.get('contractVersion')!='designcraft-checkpoint-recovery/v1':raise ValueError('recovery_proof_missing')
        entries=proof.get('evidence')
        if not isinstance(entries,list) or not entries:raise ValueError('recovery_proof_evidence_missing')
        task_root=self._dir(data['taskId'])
        seen=set();plan_bytes=None
        for entry in entries:
            if not isinstance(entry,dict) or not isinstance(entry.get('path'),str) or not re.fullmatch('[0-9a-f]{64}',str(entry.get('sha256',''))):raise ValueError('recovery_proof_evidence_invalid')
            relative=PurePosixPath(entry['path'])
            if relative.is_absolute() or '..' in relative.parts or relative.as_posix() in seen:raise ValueError('recovery_proof_evidence_invalid')
            seen.add(relative.as_posix());path=task_root.joinpath(*relative.parts)
            if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('recovery_proof_evidence_changed')
            if relative.as_posix()==proof.get('remainingPlanRef'):plan_bytes=path.read_bytes()
        if plan_bytes is None or hashlib.sha256(plan_bytes).hexdigest()!=next((item['sha256'] for item in entries if item.get('path')==proof.get('remainingPlanRef')),None):raise ValueError('recovery_plan_file_missing_or_changed')
        try:stored_plan=json.loads(plan_bytes.decode('utf-8'))
        except (UnicodeDecodeError,json.JSONDecodeError) as error:raise ValueError('recovery_plan_file_invalid') from error
        if stored_plan!=data.get('recoveryPlan') or data.get('recoveryPlanSha256')!=self._canonical_sha256(stored_plan):raise ValueError('recovery_remaining_plan_mismatch')
        project=Path(proof.get('savedProjectPath',''))
        if project.is_symlink() or not project.is_file() or hashlib.sha256(project.read_bytes()).hexdigest()!=proof.get('savedProjectSha256'):
            raise ValueError('recovery_checkpoint_changed_after_review')
        return True

    @staticmethod
    def _step_params_sha256(step):
        encoded=json.dumps(step.get('params'),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _recovery_object_inventory(inspection):
        discovered=[];seen=set()
        for spread in inspection.get('spreads',[]):
            if not isinstance(spread,dict) or not isinstance(spread.get('items'),list):raise ValueError('source_recovery_inspection_invalid')
            for item in spread['items']:
                if not isinstance(item,dict) or type(item.get('id')) is not int:continue
                identity={'id':item['id'],'kind':item.get('kind','unknown')}
                for key in ('name','story'):
                    if isinstance(item.get(key),(str,int)):identity[key]=item[key]
                encoded=json.dumps(identity,sort_keys=True,ensure_ascii=False)
                if encoded not in seen:seen.add(encoded);discovered.append(identity)
        stories=inspection.get('stories',[])
        if not isinstance(stories,list):raise ValueError('source_recovery_inspection_invalid')
        for story in stories:
            if not isinstance(story,dict) or type(story.get('id')) is not int:continue
            identity={'id':story['id'],'kind':'story'}
            if isinstance(story.get('name'),str):identity['name']=story['name']
            encoded=json.dumps(identity,sort_keys=True,ensure_ascii=False)
            if encoded not in seen:seen.add(encoded);discovered.append(identity)
        return discovered

    def _verify_source_recovery(self,data,original_payload,*,recovery_report_path,reopen_receipt_path,reopen_plan_path,original_plan_path,saved_project_path):
        """独立核对技能源恢复合同、两份回执、计划身份和保存工程摘要。"""
        try:
            report_path,report=self._read_recovery_json(recovery_report_path)
            reopen_path,reopen=self._read_recovery_json(reopen_receipt_path)
            reopen_plan_path,reopen_plan=self._read_recovery_json(reopen_plan_path)
            original_plan_path,original_plan=self._read_recovery_json(original_plan_path)
            project=Path(saved_project_path).expanduser()
            if project.is_symlink() or not project.is_file():raise ValueError('source_recovery_checkpoint_missing_or_unsafe')
            project_path=str(project.resolve(strict=True))
            project_sha=hashlib.sha256(project.read_bytes()).hexdigest()
            project_bytes=project.stat().st_size
            saved=original_payload.get('savedProjectCheckpoint')
            if not isinstance(saved,dict) or saved.get('status')!='SAVED_REOPEN_REQUIRED' or saved.get('path')!=project_path or saved.get('sha256')!=project_sha or saved.get('bytes')!=project_bytes:
                raise ValueError('source_recovery_checkpoint_mismatch')
            if data.get('runId')!=original_payload.get('runId') or report.get('originalRunId')!=data.get('runId'):
                raise ValueError('source_recovery_original_run_mismatch')
            if report.get('contractVersion')!='designcraft-checkpoint-recovery/v1' or report.get('status')!='RECOVERY_READY':
                raise ValueError('source_recovery_contract_unsupported')
            try:reopen_id=str(uuid.UUID(report.get('reopenRunId','')))
            except (ValueError,TypeError,AttributeError) as error:raise ValueError('source_recovery_reopen_run_invalid') from error
            if reopen_id!=report.get('reopenRunId') or reopen_id==report.get('originalRunId'):raise ValueError('source_recovery_reopen_run_invalid')
            if report.get('savedProjectPath')!=project_path or report.get('savedProjectSha256')!=project_sha:
                raise ValueError('source_recovery_checkpoint_mismatch')
            if report.get('resumeAllowed') is not True or report.get('automaticExecution') is not False or report.get('automaticReplay') is not False or report.get('completeAcceptance') is not False:
                raise ValueError('source_recovery_flags_invalid')
            if original_payload.get('schemaVersion')!=2 or original_payload.get('domain')!='designcraft' or original_payload.get('status')!='FAILED_OR_PARTIAL' or original_payload.get('terminationVerified') is not True:
                raise ValueError('source_recovery_original_receipt_invalid')
            if not isinstance(original_plan,dict) or original_plan.get('domain')!='designcraft' or not isinstance(original_plan.get('steps'),list) or not original_plan['steps'] or self._canonical_sha256(original_plan)!=original_payload.get('planSha256'):
                raise ValueError('source_recovery_original_plan_mismatch')
            original_steps=original_plan['steps']
            original_refs=original_payload.get('stepReferences');original_results=original_payload.get('stepResults')
            if not isinstance(original_refs,list) or not isinstance(original_results,list) or len(original_refs)!=len(original_steps) or len(original_results)!=len(original_steps):
                raise ValueError('source_recovery_original_steps_invalid')
            for index,step in enumerate(original_steps):
                ref=original_refs[index];result=original_results[index]
                if not isinstance(step,dict) or set(step)!={'command','params'} or not isinstance(step['params'],dict) or not isinstance(ref,dict) or not isinstance(result,dict):
                    raise ValueError('source_recovery_original_steps_invalid')
                if type(ref.get('index')) is not int or type(result.get('index')) is not int or ref.get('index')!=index or ref.get('command')!=step['command'] or ref.get('paramsSha256')!=self._step_params_sha256(step) or result.get('index')!=index or result.get('stepRef')!=ref.get('stepRef') or result.get('command')!=step['command']:
                    raise ValueError('source_recovery_original_steps_mismatch')
            try:original_batch=json.loads(original_payload.get('stdout',''))
            except (TypeError,json.JSONDecodeError) as error:raise ValueError('source_recovery_original_result_invalid') from error
            failed_index=original_batch.get('failedIndex') if isinstance(original_batch,dict) else None
            if type(failed_index) is not int or not 0<=failed_index<len(original_steps)-1 or report.get('failedStepIndex')!=failed_index or original_batch.get('failedCommand')!=original_steps[failed_index].get('command'):
                raise ValueError('source_recovery_failed_step_mismatch')
            if original_batch.get('completed')!=failed_index or not isinstance(original_batch.get('results'),list) or len(original_batch['results'])!=failed_index:
                raise ValueError('source_recovery_failed_step_mismatch')
            if any(original_results[i].get('status')!='STEP_COMPLETED_REVIEW_REQUIRED' for i in range(failed_index)) or original_results[failed_index].get('status')!='STEP_FAILED_OR_PARTIAL' or any(result.get('status')!='NOT_STARTED' for result in original_results[failed_index+1:]):
                raise ValueError('source_recovery_step_sequence_invalid')
            save_ref=saved.get('stepRef')
            save_index=next((i for i,ref in enumerate(original_refs) if ref.get('stepRef')==save_ref),None)
            if save_index is None or save_index>=failed_index or original_steps[save_index].get('command')!='file.saveAs':
                raise ValueError('source_recovery_save_step_mismatch')
            save_result=original_batch['results'][save_index]
            save_result_sha=hashlib.sha256(json.dumps(save_result,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
            if not isinstance(save_result,dict) or save_result.get('bytes')!=project_bytes or save_result.get('path') is None or str(Path(save_result['path']).expanduser().resolve())!=project_path or saved.get('resultSha256')!=save_result_sha:
                raise ValueError('source_recovery_save_result_mismatch')
            if not isinstance(reopen,dict) or reopen.get('schemaVersion')!=2 or reopen.get('domain')!='designcraft' or reopen.get('runId')!=report.get('reopenRunId') or reopen.get('status')!='NATIVE_EXIT_ZERO_REVIEW_REQUIRED' or reopen.get('exitCode')!=0 or reopen.get('terminationVerified') is not True:
                raise ValueError('source_recovery_reopen_receipt_invalid')
            for key in ('runtimeLockSha256','runtimeIdentity','skillResourceSha256'):
                if reopen.get(key)!=original_payload.get(key):raise ValueError('source_recovery_runtime_identity_mismatch')
            if not isinstance(reopen_plan,dict) or reopen_plan.get('domain')!='designcraft' or reopen_plan.get('steps')!=[{'command':'file.open','params':{'path':project_path}},{'command':'document.inspect','params':{}}] or self._canonical_sha256(reopen_plan)!=reopen.get('planSha256'):
                raise ValueError('source_recovery_reopen_plan_invalid')
            reopen_refs=reopen.get('stepReferences');reopen_results=reopen.get('stepResults')
            if not isinstance(reopen_refs,list) or not isinstance(reopen_results,list) or len(reopen_refs)!=2 or len(reopen_results)!=2:
                raise ValueError('source_recovery_reopen_steps_invalid')
            for index,step in enumerate(reopen_plan['steps']):
                ref=reopen_refs[index];result=reopen_results[index]
                if not isinstance(ref,dict) or not isinstance(result,dict) or type(ref.get('index')) is not int or type(result.get('index')) is not int or ref.get('index')!=index or ref.get('command')!=step['command'] or ref.get('paramsSha256')!=self._step_params_sha256(step) or result.get('index')!=index or result.get('stepRef')!=ref.get('stepRef') or result.get('command')!=step['command'] or result.get('status')!='BATCH_EXIT_ZERO_REVIEW_REQUIRED':
                    raise ValueError('source_recovery_reopen_steps_mismatch')
            if not isinstance(reopen.get('inputSha256'),dict) or not isinstance(reopen.get('inputAfterSha256'),dict) or reopen['inputSha256'].get(project_path)!=project_sha or reopen['inputAfterSha256'].get(project_path)!=project_sha:
                raise ValueError('source_recovery_input_digest_mismatch')
            try:reopen_batch=json.loads(reopen.get('stdout',''))
            except (TypeError,json.JSONDecodeError) as error:raise ValueError('source_recovery_reopen_result_invalid') from error
            if not isinstance(reopen_batch,dict) or reopen_batch.get('completed')!=2 or not isinstance(reopen_batch.get('results'),list) or len(reopen_batch['results'])!=2:
                raise ValueError('source_recovery_reopen_result_invalid')
            inspection=reopen_batch['results'][1]
            if not isinstance(reopen_batch['results'][0],dict) or reopen_batch['results'][0].get('index')!=1 or not isinstance(inspection,dict) or inspection.get('path')!=project_path or inspection.get('dirty') is not False or type(inspection.get('pageCount')) is not int or inspection['pageCount']<1 or not isinstance(inspection.get('spreads'),list):
                raise ValueError('source_recovery_inspection_invalid')
            remaining=original_steps[failed_index+1:]
            plan=report.get('remainingPlan')
            if not isinstance(plan,dict) or plan!={'domain':'designcraft','steps':remaining} or not remaining:
                raise ValueError('source_recovery_remaining_plan_mismatch')
            discovered=report.get('discoveredObjects')
            if not isinstance(discovered,list) or discovered!=self._recovery_object_inventory(inspection):
                raise ValueError('source_recovery_object_inventory_invalid')
            risks=[]
            if original_payload.get('descendantsTerminationVerified') is not True or reopen.get('descendantsTerminationVerified') is not True:risks.append('process_descendants_termination_unverified')
            return {'valid':True,'report':report,'remainingPlan':plan,'originalRunId':original_payload['runId'],'reopenRunId':reopen['runId'],'projectSha256':project_sha,'reportSha256':hashlib.sha256(report_path.read_bytes()).hexdigest(),'reopenReceiptSha256':hashlib.sha256(reopen_path.read_bytes()).hexdigest(),'reopenPlanSha256':hashlib.sha256(reopen_plan_path.read_bytes()).hexdigest(),'originalPlanSha256':hashlib.sha256(original_plan_path.read_bytes()).hexdigest(),'reportPath':str(report_path.absolute()),'reopenReceiptPath':str(reopen_path.absolute()),'reopenPlanPath':str(reopen_plan_path.absolute()),'originalPlanPath':str(original_plan_path.absolute()),'savedProjectPath':project_path,'discoveredObjects':discovered,'risks':risks}
        except (ValueError,OSError,TypeError,KeyError) as error:
            return {'valid':False,'reason':str(error)}

    def reconcile(self,identifier,*,recovery_report_path=None,reopen_receipt_path=None,reopen_plan_path=None,original_plan_path=None,saved_project_path=None):
        """只读核对任务回执；可选地独立验证技能源的持久工程恢复合同。"""
        identifier=task_id(identifier);data=self.get(identifier)
        if data['state']!='RECONCILING':raise ValueError('reconciliation_state_required')
        blockers=[];receipt_identity='MISSING';receipt_sha=None;payload={}
        reference=data.get('nativeReceiptRef')
        if isinstance(reference,str):
            relative=PurePosixPath(reference);task_root=self._dir(identifier);receipt_path=task_root.joinpath(*relative.parts)
            if relative.is_absolute() or '..' in relative.parts or len(relative.parts)!=2 or relative.parts[0]!='runs' or relative.suffix!='.json' or task_root.is_symlink() or receipt_path.parent.is_symlink() or receipt_path.is_symlink() or not receipt_path.is_file():
                blockers.append('native_receipt_missing_or_unsafe')
            else:
                try:
                    wrapper=json.loads(receipt_path.read_text(encoding='utf-8'))
                    if not isinstance(wrapper,dict) or not isinstance(wrapper.get('payload'),dict):raise ValueError('native_receipt_invalid')
                    payload=wrapper['payload'];receipt_sha=hashlib.sha256(receipt_path.read_bytes()).hexdigest()
                    if wrapper.get('taskId')!=identifier:
                        receipt_identity='MISMATCH';blockers.append('receipt_task_id_mismatch')
                    elif payload.get('schemaVersion')!=2 or payload.get('status') not in {'NOT_STARTED','FAILED_OR_PARTIAL','UNKNOWN','NATIVE_EXIT_ZERO_REVIEW_REQUIRED'}:
                        blockers.append('native_receipt_schema_unsupported')
                    elif not data.get('runId') or payload.get('runId')!=data.get('runId'):
                        receipt_identity='MISMATCH';blockers.append('receipt_run_id_mismatch')
                    elif wrapper.get('processExitCode')!=payload.get('exitCode'):
                        receipt_identity='MISMATCH';blockers.append('receipt_exit_code_mismatch')
                    else:
                        receipt_identity='MATCHED'
                    if payload.get('terminationVerified') is not True:
                        blockers.append('process_termination_unverified')
                except (OSError,json.JSONDecodeError,ValueError,TypeError):
                    blockers.append('native_receipt_invalid')
        else:
            blockers.append('native_receipt_reference_missing')
        recovery_inputs=(recovery_report_path,reopen_receipt_path,reopen_plan_path,original_plan_path,saved_project_path)
        recovery=None
        if all(value is not None for value in recovery_inputs) and receipt_identity=='MATCHED' and not blockers:
            recovery=self._verify_source_recovery(data,payload,recovery_report_path=recovery_report_path,reopen_receipt_path=reopen_receipt_path,reopen_plan_path=reopen_plan_path,original_plan_path=original_plan_path,saved_project_path=saved_project_path)
            if not recovery['valid']:blockers.append(recovery.get('reason','source_recovery_bundle_invalid'))
        else:
            if any(value is not None for value in recovery_inputs):blockers.append('source_recovery_bundle_incomplete')
            else:blockers.append('source_checkpoint_contract_unavailable')
        if not data.get('checkpointRefs'):blockers.append('persistent_project_checkpoint_missing')
        source_steps=payload.get('stepResults',[])
        if not isinstance(source_steps,list) or len(source_steps)>1000 or any(not isinstance(item,dict) for item in source_steps):
            blockers.append('source_step_results_malformed');source_steps=[]
        valid_recovery=bool(recovery and recovery.get('valid') and not blockers)
        recovery_risks=recovery.get('risks',[]) if valid_recovery else []
        return {
            'taskId':identifier,
            'state':data['state'],
            'status':recovery.get('report',{}).get('status') if valid_recovery else payload.get('status','UNKNOWN'),
            'nativeStatus':payload.get('status','UNKNOWN'),
            'runId':data.get('runId'),
            'receiptIdentity':receipt_identity,
            'receiptSha256':receipt_sha,
            'revision':data.get('revision'),
            'checkpointRefs':data.get('checkpointRefs',[]),
            'stepResults':source_steps,
            'stepResultGranularity':payload.get('stepResultGranularity'),
            'stepResultsVerified':valid_recovery,
            'planVerified':valid_recovery,
            'recoveryContract':recovery.get('report',{}).get('contractVersion') if valid_recovery else None,
            'reconciledRunId':recovery.get('reopenRunId') if valid_recovery else None,
            'recoveryEvidence':{'reportSha256':recovery.get('reportSha256'),'reopenReceiptSha256':recovery.get('reopenReceiptSha256'),'originalPlanSha256':recovery.get('originalPlanSha256'),'reopenPlanSha256':recovery.get('reopenPlanSha256'),'savedProjectSha256':recovery.get('projectSha256')} if valid_recovery else None,
            'remainingPlan':recovery.get('remainingPlan') if valid_recovery else None,
            'remainingPlanSha256':self._canonical_sha256(recovery['remainingPlan']) if valid_recovery else None,
            'discoveredObjects':recovery.get('discoveredObjects',[]) if valid_recovery else [],
            'risks':recovery_risks,
            'blockers':list(dict.fromkeys(blockers)),
            'resumeAllowed':valid_recovery and not recovery_risks,
            'automaticExecution':False,
            'automaticReplay':False,
            'completeAcceptance':False,
            'nextAction':'acknowledge_recovery_risks_and_confirm_plan' if valid_recovery and recovery_risks else ('review_verified_remaining_plan_and_explicitly_resume' if valid_recovery else 'inspect_saved_project_and_source_checkpoints'),
        }

    def prepare_recovery(self,identifier,expected_revision,confirmed_plan_sha256,*,acknowledged_risks=(),recovery_report_path,reopen_receipt_path,reopen_plan_path,original_plan_path,saved_project_path):
        """在人工确认计划摘要后，把已验证后缀一次性准备到原任务，不创建重复任务。"""
        identifier=task_id(identifier)
        diagnostic=self.reconcile(identifier,recovery_report_path=recovery_report_path,reopen_receipt_path=reopen_receipt_path,reopen_plan_path=reopen_plan_path,original_plan_path=original_plan_path,saved_project_path=saved_project_path)
        if not diagnostic.get('planVerified') or not diagnostic.get('remainingPlan'):
            raise ValueError('reconciliation_checkpoint_verification_required')
        risks=set(diagnostic.get('risks',[]));acknowledged=set(acknowledged_risks or ())
        if not risks.issubset(acknowledged):raise ValueError('recovery_risk_acknowledgement_required')
        plan=diagnostic['remainingPlan'];plan_sha=self._canonical_sha256(plan)
        if not isinstance(confirmed_plan_sha256,str) or confirmed_plan_sha256!=plan_sha:
            raise ValueError('recovery_plan_confirmation_mismatch')
        lock=self._locked(identifier)
        try:
            data=self._load(identifier);self._check_revision(data,expected_revision)
            if data['state']!='RECONCILING' or data.get('runId')!=diagnostic.get('runId') or data.get('nativeReceiptRef') is None:
                raise ValueError('reconciliation_task_changed')
            receipt_ref=PurePosixPath(data['nativeReceiptRef']);receipt_path=self._dir(identifier).joinpath(*receipt_ref.parts)
            if receipt_ref.is_absolute() or '..' in receipt_ref.parts or receipt_path.is_symlink() or not receipt_path.is_file() or hashlib.sha256(receipt_path.read_bytes()).hexdigest()!=diagnostic.get('receiptSha256'):
                raise ValueError('reconciliation_receipt_changed')
            wrapper=json.loads(receipt_path.read_text(encoding='utf-8'))
            if not isinstance(wrapper,dict) or not isinstance(wrapper.get('payload'),dict):raise ValueError('native_receipt_invalid')
            verified=self._verify_source_recovery(data,wrapper['payload'],recovery_report_path=recovery_report_path,reopen_receipt_path=reopen_receipt_path,reopen_plan_path=reopen_plan_path,original_plan_path=original_plan_path,saved_project_path=saved_project_path)
            if not verified.get('valid') or self._canonical_sha256(verified.get('remainingPlan'))!=plan_sha:
                raise ValueError('reconciliation_checkpoint_verification_required')
            evidence_dir=self._dir(identifier)/'evidence'
            if evidence_dir.is_symlink():raise ValueError('recovery_evidence_path_invalid')
            evidence_dir.mkdir(parents=True,exist_ok=True)
            bundle_name='recovery-'+str(uuid.uuid4())
            bundle=evidence_dir/bundle_name
            bundle.mkdir()
            entries=[]
            sources=(('recovery.json',Path(recovery_report_path),verified['reportSha256']),('reopen-receipt.json',Path(reopen_receipt_path),verified['reopenReceiptSha256']),('original-plan.json',Path(original_plan_path),verified['originalPlanSha256']),('reopen-plan.json',Path(reopen_plan_path),verified['reopenPlanSha256']))
            try:
                for name,source,expected_sha in sources:
                    target=bundle/name;shutil.copyfile(source,target)
                    actual_sha=hashlib.sha256(target.read_bytes()).hexdigest()
                    if actual_sha!=expected_sha:raise ValueError('recovery_evidence_changed_during_copy')
                    entries.append({'path':f'evidence/{bundle_name}/{name}','sha256':actual_sha})
                plan_file=bundle/'remaining-plan.json';plan_file.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
                entries.append({'path':f'evidence/{bundle_name}/remaining-plan.json','sha256':hashlib.sha256(plan_file.read_bytes()).hexdigest()})
            except (OSError,ValueError):
                shutil.rmtree(bundle,ignore_errors=True)
                raise
            data['recoveryPlan']=plan;data['recoveryPlanSha256']=plan_sha
            data['recoveryProof']={'schemaVersion':1,'contractVersion':'designcraft-checkpoint-recovery/v1','originalRunId':verified['originalRunId'],'reopenRunId':verified['reopenRunId'],'savedProjectPath':verified['savedProjectPath'],'savedProjectSha256':verified['projectSha256'],'remainingPlanRef':f'evidence/{bundle_name}/remaining-plan.json','risks':verified.get('risks',[]),'acknowledgedRisks':sorted(risks),'evidence':entries}
            data['reconciledRunId']=verified['reopenRunId'];data['recoveryAction']='manual_review_confirmed';data['recoveryEvidence']=[entry['sha256'] for entry in entries]+[verified['projectSha256']]
            data['checkpointRefs']=list(dict.fromkeys(data['checkpointRefs']+[verified['savedProjectPath']]))
            data['nativeStatus']='NOT_RUN';data['nativeReceiptRef']=None;data['runId']=None
            data['state']='PREPARED';data['nextAction']='submit_confirmed_remaining_plan';data['revision']+=1;data['updatedAt']=now()
            self._save(identifier,data);return data
        finally:self._unlock(lock)

    def dispatch_native(self,identifier,argv,expected_revision,capability_evidence=None,runtime_home=None):
        """仅从执行态通过技能源公开命令入口调用，并保存版本化运行回执。"""
        identifier=task_id(identifier)
        if not isinstance(argv,list) or not argv or any(not isinstance(value,str) for value in argv):raise ValueError('native_arguments_invalid')
        task=self.get(identifier);self._check_revision(task,expected_revision)
        if task['state']!='EXECUTING':raise ValueError('native_dispatch_requires_executing_state')
        if task.get('nativeStatus')!='NOT_RUN':raise ValueError('native_dispatch_already_started_or_requires_reconciliation')
        if task.get('recoveryPlan') is not None and argv[0]!='run':raise ValueError('recovery_remaining_plan_requires_native_run')
        if not EXTERNAL_COMMANDS.is_file() or EXTERNAL_COMMANDS.is_symlink():raise ValueError('shared_skill_entry_missing')
        uses_native=argv[0] in ('list','describe','run') or (argv[0]=='check' and '--catalog' not in argv)
        if uses_native:
            requested=[]
            if argv[0]=='run':
                if len(argv)<2:raise ValueError('plan_required')
                try:plan=json.loads(Path(argv[1]).read_text(encoding='utf-8'))
                except (OSError,json.JSONDecodeError) as error:raise ValueError('plan_unreadable_before_readiness') from error
                if not isinstance(plan,dict) or not isinstance(plan.get('steps'),list):raise ValueError('plan_invalid_before_readiness')
                requested=[step.get('command') for step in plan['steps'] if isinstance(step,dict) and isinstance(step.get('command'),str)]
                if len(requested)!=len(plan['steps']) or not requested:raise ValueError('plan_commands_invalid_before_readiness')
                if task.get('recoveryPlan') is not None:
                    if task.get('recoveryPlanSha256')!=self._canonical_sha256(task['recoveryPlan']) or plan!=task['recoveryPlan']:
                        raise ValueError('recovery_remaining_plan_mismatch')
                    self._verify_recovery_proof_bundle(task)
            readiness=readiness_report(runtime_home,capability_evidence,requested)
            if readiness['status']!='READY':raise ValueError('readiness_gate_blocked:'+readiness['status'])
        starting=self.update(identifier,{'nativeStatus':'STARTING','nextAction':'native_command_running'},expected_revision)
        if starting.get('recoveryPlan') is not None:
            lock=self._locked(identifier)
            try:
                data=self._load(identifier);self._check_revision(data,starting['revision'])
                if data.get('recoveryPlanSha256')!=self._canonical_sha256(data.get('recoveryPlan')):
                    raise ValueError('recovery_remaining_plan_mismatch')
                proof=data.get('recoveryProof')
                if not isinstance(proof,dict):raise ValueError('recovery_proof_missing')
                proof['consumedPlanSha256']=data['recoveryPlanSha256'];data['recoveryProof']=proof
                data['recoveryPlan']=None;data['recoveryPlanSha256']=None
                data['revision']+=1;data['updatedAt']=now();self._save(identifier,data);starting=data
            finally:self._unlock(lock)
        try:result=subprocess.run([sys.executable,'-I','-B',str(EXTERNAL_COMMANDS),*argv],capture_output=True,text=True)
        except (OSError,subprocess.SubprocessError) as error:
            latest=self.get(identifier)
            return self.update(identifier,{'nativeStatus':'UNKNOWN','nextAction':'reconcile_native_result','blockers':latest['blockers']+[str(error)]},latest['revision'])
        try:payload=json.loads(result.stdout)
        except json.JSONDecodeError:payload=None
        run_id=payload.get('runId') if isinstance(payload,dict) else None
        status=payload.get('status') if isinstance(payload,dict) else None
        supported={'NOT_STARTED','FAILED_OR_PARTIAL','UNKNOWN','NATIVE_EXIT_ZERO_REVIEW_REQUIRED'}
        try:valid_run_id=isinstance(run_id,str) and str(uuid.UUID(run_id))==run_id
        except ValueError:valid_run_id=False
        exit_code=payload.get('exitCode') if isinstance(payload,dict) else None
        versioned=bool(isinstance(payload,dict) and payload.get('schemaVersion')==2 and status in supported and valid_run_id and (exit_code is None or type(exit_code) is int) and (status!='NATIVE_EXIT_ZERO_REVIEW_REQUIRED' or exit_code==0 and result.returncode==0) and not (result.returncode==0 and status!='NATIVE_EXIT_ZERO_REVIEW_REQUIRED'))
        if argv[0]=='run' and not versioned:
            status='UNKNOWN';run_id=None;payload={'schemaVersion':None,'status':status,'reason':'shared_receipt_missing_or_unsupported','stdout':result.stdout,'stderr':result.stderr,'exitCode':result.returncode}
        elif argv[0]!='run':status='NOT_RUN'
        folder=self._dir(identifier)/'runs';folder.mkdir(parents=True,exist_ok=True)
        ref=f"runs/{run_id if run_id and re.fullmatch(r'[0-9a-f-]{36}',run_id) else uuid.uuid4()}.json"
        target=self._dir(identifier)/ref;temporary=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=folder,prefix='.run-',delete=False) as stream:
                temporary=Path(stream.name);json.dump({'taskId':identifier,'payload':payload,'stdout':result.stdout,'stderr':result.stderr,'processExitCode':result.returncode},stream,ensure_ascii=False,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,target)
        finally:
            if temporary is not None and temporary.exists():temporary.unlink()
        updates={'nativeStatus':status,'nativeReceiptRef':ref,'nextAction':'reconcile_native_result' if status=='UNKNOWN' else ('review_native_result' if status=='NATIVE_EXIT_ZERO_REVIEW_REQUIRED' else 'continue_task')}
        if run_id:updates['runId']=run_id
        latest=self.get(identifier)
        return self.update(identifier,updates,latest['revision'])

    def transition(self,identifier,target,expected_revision,updates=None):
        """执行受限状态迁移；完成必须具有当前候选的完整验收证据。"""
        identifier=task_id(identifier);lock=self._locked(identifier)
        try:
            data=self._load(identifier);self._check_revision(data,expected_revision)
            if target not in TRANSITIONS[data['state']]:raise ValueError('invalid_state_transition')
            next_updates=updates or {}
            if isinstance(next_updates,dict) and set(next_updates)&PROTECTED_RECOVERY_FIELDS:raise ValueError('recovery_fields_are_protected')
            if target=='RECONCILING' and data.get('nativeStatus')=='STARTING':
                if not next_updates.get('recoveryEvidence') or not next_updates.get('recoveryAction'):raise ValueError('reconciliation_evidence_required')
            if data['state']=='RECONCILING' and target in ('PREPARED','VERIFYING'):
                raise ValueError('reconciliation_checkpoint_verification_required')
            if target=='EXECUTING' and data.get('nativeStatus') in ('UNKNOWN','FAILED_OR_PARTIAL','NATIVE_EXIT_ZERO_REVIEW_REQUIRED'):
                raise ValueError('reconciliation_checkpoint_verification_required')
            if data['state']=='REVISION_REQUIRED' and target=='PREPARED':
                revision_scope=next_updates.get('revisionScope',data.get('revisionScope'))
                page_refs=next_updates.get('revisionPageRefs',data.get('revisionPageRefs',[]))
                if not isinstance(revision_scope,str) or not revision_scope.strip() or not page_refs:raise ValueError('revision_scope_required')
                if ' '.join(revision_scope.casefold().split()) not in ' '.join(data['authorizationScope'].casefold().split()):raise ValueError('revision_scope_exceeds_authorization')
            self._apply_updates(data,updates or {})
            if target=='PREPARED' and data['state']=='REVISION_REQUIRED':data['nextAction']='execute_scoped_revision'
            if target=='REVISION_REQUIRED':
                data['revisionScope']=None;data['revisionPageRefs']=[];data['nextAction']='define_revision_scope'
            if target=='PREPARED' and data['state'] in ('RECONCILING','REVISION_REQUIRED') and not data.get('nextAction'):
                raise ValueError('recovery_action_required')
            if target=='COMPLETED':
                if data['blockers']:raise ValueError('unresolved_blockers')
                if not data.get('candidateSha256') or not set(data['requiredEvidence']).issubset(self._fresh_evidence(data)):raise ValueError('required_acceptance_evidence_missing')
            data['state']=target;data['revision']+=1;data['updatedAt']=now();self._save(identifier,data);return data
        finally:self._unlock(lock)

def render_status(task):
    """渲染稳定的 Harness 回执字段，区分状态、证据、风险和下一动作。"""
    proof=task.get('recoveryProof') if isinstance(task.get('recoveryProof'),dict) else {}
    risks=list(dict.fromkeys(task['blockers']+proof.get('risks',[])))
    return {'taskId':task['taskId'],'status':task['state'],'scope':task['authorizationScope'],'actions':[task['skillRoute']],'evidence':task['evidenceRefs'],'artifacts':task['artifactRefs'],'skipped':[],'risks':risks,'next_action':task['nextAction'],'revision':task['revision'],'runId':task.get('runId'),'nativeStatus':task.get('nativeStatus'),'nativeReceiptRef':task.get('nativeReceiptRef'),'checkpointRefs':task['checkpointRefs'],'reconciledRunId':task.get('reconciledRunId'),'recoveryAction':task.get('recoveryAction'),'recoveryEvidence':task.get('recoveryEvidence',[]),'recoveryPlanSha256':task.get('recoveryPlanSha256'),'recoveryPlanRef':proof.get('remainingPlanRef'),'revisionScope':task.get('revisionScope'),'affectedPages':task.get('revisionPageRefs',[])}

def main():
    """提供本地任务创建、状态读取、显式迁移和证据登记入口。"""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--task-home',default=os.environ.get('DESIGNCRAFT_TASK_HOME',str(Path.home()/'.local/share/designcraft/tasks')))
    commands=parser.add_subparsers(dest='command',required=True)
    create=commands.add_parser('new');create.add_argument('--goal',required=True);create.add_argument('--scope',required=True);create.add_argument('--route',default='designcraft-use')
    show=commands.add_parser('show');show.add_argument('task_id')
    update=commands.add_parser('update');update.add_argument('task_id');update.add_argument('--expected-revision',type=int,required=True);update.add_argument('--json',required=True)
    transition=commands.add_parser('transition');transition.add_argument('task_id');transition.add_argument('state');transition.add_argument('--expected-revision',type=int,required=True);transition.add_argument('--updates-json',default='{}')
    evidence=commands.add_parser('attach-evidence');evidence.add_argument('task_id');evidence.add_argument('file');evidence.add_argument('--expected-revision',type=int,required=True)
    native=commands.add_parser('native');native.add_argument('task_id');native.add_argument('--expected-revision',type=int,required=True);native.add_argument('--capability-evidence');native.add_argument('--runtime-home');native.add_argument('arguments',nargs=argparse.REMAINDER)
    reconcile=commands.add_parser('reconcile');reconcile.add_argument('task_id')
    for option in ('recovery-report','reopen-receipt','reopen-plan','original-plan','saved-project'):
        reconcile.add_argument('--'+option,dest=option.replace('-','_'))
    prepare_recovery=commands.add_parser('prepare-recovery');prepare_recovery.add_argument('task_id');prepare_recovery.add_argument('--expected-revision',type=int,required=True);prepare_recovery.add_argument('--confirm-plan-sha256',required=True);prepare_recovery.add_argument('--acknowledge-risk',action='append',default=[])
    for option in ('recovery-report','reopen-receipt','reopen-plan','original-plan','saved-project'):
        prepare_recovery.add_argument('--'+option,dest=option.replace('-','_'),required=True)
    artifacts=commands.add_parser('verify-artifacts');artifacts.add_argument('task_id');artifacts.add_argument('--expected-revision',type=int,required=True);artifacts.add_argument('--root',required=True);artifacts.add_argument('--manifest',required=True)
    review=commands.add_parser('verify-review');review.add_argument('task_id');review.add_argument('--expected-revision',type=int,required=True);review.add_argument('--root',required=True);review.add_argument('--artifact-manifest',required=True);review.add_argument('--review',required=True)
    revision=commands.add_parser('verify-revision');revision.add_argument('task_id');revision.add_argument('--expected-revision',type=int,required=True);revision.add_argument('--root',required=True);revision.add_argument('--revision',required=True)
    readiness=commands.add_parser('readiness');readiness.add_argument('--runtime-home');readiness.add_argument('--capability-evidence');readiness.add_argument('--command-id',action='append',default=[])
    args=parser.parse_args();store=TaskStore(args.task_home)
    try:
        if args.command=='new':task=store.create(args.goal,args.scope,args.route)
        elif args.command=='show':task=store.get(args.task_id)
        elif args.command=='update':task=store.update(args.task_id,json.loads(args.json),args.expected_revision)
        elif args.command=='transition':task=store.transition(args.task_id,args.state,args.expected_revision,json.loads(args.updates_json))
        elif args.command=='attach-evidence':task=store.attach_evidence(args.task_id,args.file,args.expected_revision)
        elif args.command=='reconcile':
            print(json.dumps(store.reconcile(args.task_id,recovery_report_path=args.recovery_report,reopen_receipt_path=args.reopen_receipt,reopen_plan_path=args.reopen_plan,original_plan_path=args.original_plan,saved_project_path=args.saved_project),ensure_ascii=False,indent=2));return 0
        elif args.command=='prepare-recovery':
            task=store.prepare_recovery(args.task_id,args.expected_revision,args.confirm_plan_sha256,acknowledged_risks=args.acknowledge_risk,recovery_report_path=args.recovery_report,reopen_receipt_path=args.reopen_receipt,reopen_plan_path=args.reopen_plan,original_plan_path=args.original_plan,saved_project_path=args.saved_project)
            response=render_status(task);response.update({'recoveryPlan':task['recoveryPlan'],'recoveryPlanSha256':task['recoveryPlanSha256'],'recoveryProof':task['recoveryProof']})
            print(json.dumps(response,ensure_ascii=False,indent=2));return 0
        elif args.command=='verify-artifacts':task=store.verify_artifact_manifest(args.task_id,args.root,args.manifest,args.expected_revision)
        elif args.command=='verify-review':task=store.verify_page_review(args.task_id,args.root,args.artifact_manifest,args.review,args.expected_revision)
        elif args.command=='verify-revision':task=store.verify_revision(args.task_id,args.root,args.revision,args.expected_revision)
        elif args.command=='readiness':
            print(json.dumps(readiness_report(args.runtime_home,args.capability_evidence,args.command_id),ensure_ascii=False,indent=2));return 0
        else:
            native_args=args.arguments[1:] if args.arguments[:1]==['--'] else args.arguments
            task=store.dispatch_native(args.task_id,native_args,args.expected_revision,args.capability_evidence,args.runtime_home)
        print(json.dumps(render_status(task),ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,json.JSONDecodeError,subprocess.SubprocessError) as error:
        print(json.dumps({'error':str(error)},ensure_ascii=False));return 1

if __name__=='__main__':raise SystemExit(main())
