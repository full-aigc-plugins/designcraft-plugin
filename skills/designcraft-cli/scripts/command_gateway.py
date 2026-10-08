"""三领域原生命令查询与单会话计划入口；标准库实现，不解析 shell。"""
import argparse
import hashlib
import json
import math
import os
import platform
import shutil
import tempfile
from pathlib import Path
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone

DOMAINS=('lightcraft','printcraft','designcraft')


def strict_json(text):
    """拒绝重复字段及非 JSON 的 NaN/Infinity，避免计划歧义。"""
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise ValueError('duplicate_json_field: '+k)
            result[k]=v
        return result
    def invalid(value):raise ValueError('nonfinite_json_number: '+value)
    def number(value):
        parsed=float(value)
        if not math.isfinite(parsed):invalid(value)
        return parsed
    return json.loads(text,object_pairs_hook=pairs,parse_constant=invalid,parse_float=number)


def normalize(domain,raw):
    """保留完整原生目录；文本参数说明不升级为 JSON Schema。"""
    if domain not in DOMAINS or not isinstance(raw,list) or not raw:raise ValueError('invalid_native_catalog')
    rows=[];seen=set()
    for item in raw:
        if not isinstance(item,dict):raise ValueError('invalid_native_catalog_entry')
        identifier=item.get('name' if domain=='printcraft' else 'id')
        if not isinstance(identifier,str) or not identifier:raise ValueError('invalid_command_id')
        if identifier in seen:raise ValueError('duplicate_command: '+identifier)
        seen.add(identifier)
        menu=item.get('menu',[])
        if not isinstance(menu,list) or any(not isinstance(x,str) for x in menu):raise ValueError('invalid_menu')
        schema=item.get('input_schema') if domain=='printcraft' else None
        if domain=='printcraft' and not isinstance(schema,dict):raise ValueError('missing_native_input_schema')
        rows.append({'id':identifier,'title':item.get('label',identifier),'description':item.get('description',''),
                     'category':(menu[0] if menu else identifier.split('.')[0].split('_')[0]),
                     'parameterGuidance':item.get('params',''),'inputSchema':schema,
                     'parameterValidation':'schema-subset' if schema is not None else 'native-only',
                     'observedEnabled':item.get('enabled'),'native':item})
    return rows


def validate_schema_definition(schema,depth=0):
    """先遍历完整定义；未选分支或未提供属性不能隐藏未知约束。"""
    if depth>48:raise ValueError('schema_depth_exceeded')
    if isinstance(schema,bool):return
    if not isinstance(schema,dict):raise ValueError('invalid_native_schema')
    allowed={'$schema','title','description','default','examples','type','properties','required','additionalProperties','items','minimum','maximum','exclusiveMinimum','exclusiveMaximum','minItems','maxItems','minLength','maxLength','enum','const','pattern','anyOf','oneOf','allOf'}
    if set(schema)-allowed:raise ValueError('unsupported_schema_constraint: '+','.join(sorted(set(schema)-allowed)))
    if 'type' in schema:
        types=schema['type'];types=[types] if isinstance(types,str) else types
        supported={'object','array','string','boolean','integer','number','null'}
        if not isinstance(types,list) or not types or any(not isinstance(t,str) or t not in supported for t in types):raise ValueError('unsupported_schema_type')
        if len(set(types))!=len(types):raise ValueError('invalid_native_schema')
    if 'properties' in schema:
        if not isinstance(schema['properties'],dict):raise ValueError('invalid_native_schema')
        for child in schema['properties'].values():validate_schema_definition(child,depth+1)
    if 'required' in schema:
        required=schema['required']
        if not isinstance(required,list) or any(not isinstance(k,str) for k in required) or len(set(required))!=len(required):raise ValueError('invalid_native_schema')
    for key in ('items','additionalProperties'):
        if key in schema:validate_schema_definition(schema[key],depth+1)
    for key in ('anyOf','oneOf','allOf'):
        if key in schema:
            if not isinstance(schema[key],list) or not schema[key]:raise ValueError('invalid_native_schema')
            for child in schema[key]:validate_schema_definition(child,depth+1)
    for key in ('minimum','maximum','exclusiveMinimum','exclusiveMaximum'):
        if key in schema and (type(schema[key]) not in (int,float) or (isinstance(schema[key],float) and not math.isfinite(schema[key]))):raise ValueError('invalid_native_schema')
    for key in ('minItems','maxItems','minLength','maxLength'):
        if key in schema and (type(schema[key]) is not int or schema[key]<0):raise ValueError('invalid_native_schema')
    if 'enum' in schema and (not isinstance(schema['enum'],list) or not schema['enum']):raise ValueError('invalid_native_schema')
    if 'pattern' in schema:
        if not isinstance(schema['pattern'],str):raise ValueError('invalid_native_schema')
        try:re.compile(schema['pattern'])
        except re.error as error:raise ValueError('invalid_native_schema: pattern') from error


def json_equal(left,right,depth=0):
    """JSON数字按值比较，布尔值保持独立，容器递归遵守同一规则。"""
    if depth>48:raise ValueError('schema_depth_exceeded')
    if type(left) in (int,float) and type(right) in (int,float):return left==right
    if type(left) is not type(right):return False
    if isinstance(left,dict):return left.keys()==right.keys() and all(json_equal(v,right[k],depth+1) for k,v in left.items())
    if isinstance(left,list):return len(left)==len(right) and all(json_equal(a,b,depth+1) for a,b in zip(left,right))
    return left==right


def validate_schema(schema,value,path='$',depth=0):
    """校验原生 schema 的明确支持子集；未知约束拒绝，不宣称通用 JSON Schema。"""
    if depth>48:raise ValueError('schema_depth_exceeded')
    if depth==0:validate_schema_definition(schema)
    if schema is True:return
    if schema is False:raise ValueError('parameter_schema_false: '+path)
    if not isinstance(schema,dict):raise ValueError('unsupported_native_schema')
    allowed={'$schema','title','description','default','examples','type','properties','required','additionalProperties','items','minimum','maximum','exclusiveMinimum','exclusiveMaximum','minItems','maxItems','minLength','maxLength','enum','const','pattern','anyOf','oneOf','allOf'}
    unknown=set(schema)-allowed
    if unknown:raise ValueError('unsupported_schema_constraint: '+','.join(sorted(unknown)))
    for key in ('anyOf','oneOf','allOf'):
        if key in schema:
            branches=schema[key]
            if not isinstance(branches,list) or not branches:raise ValueError('invalid_native_schema')
            matches=0
            for branch in branches:
                try:validate_schema(branch,value,path,depth+1);matches+=1
                except ValueError:pass
            if (key=='anyOf' and not matches) or (key=='oneOf' and matches!=1) or (key=='allOf' and matches!=len(branches)):
                raise ValueError('schema_branch_mismatch: '+path)
    types={'object':lambda v:isinstance(v,dict),'array':lambda v:isinstance(v,list),'string':lambda v:isinstance(v,str),'boolean':lambda v:isinstance(v,bool),'integer':lambda v:isinstance(v,int) and not isinstance(v,bool),'number':lambda v:isinstance(v,(int,float)) and not isinstance(v,bool) and (not isinstance(v,float) or math.isfinite(v)),'null':lambda v:v is None}
    wanted=schema.get('type');wanted=[wanted] if isinstance(wanted,str) else wanted
    if wanted is not None:
        if not isinstance(wanted,list) or any(t not in types for t in wanted):raise ValueError('unsupported_schema_type')
        if not any(types[t](value) for t in wanted):raise ValueError('parameter_type_mismatch: '+path)
    same=json_equal
    if 'enum' in schema and not any(same(value,x) for x in schema['enum']):raise ValueError('parameter_enum_mismatch: '+path)
    if 'const' in schema and not same(value,schema['const']):raise ValueError('parameter_const_mismatch: '+path)
    if isinstance(value,dict):
        props=schema.get('properties',{});required=schema.get('required',[])
        if not isinstance(props,dict) or not isinstance(required,list):raise ValueError('invalid_native_schema')
        if any(k not in value for k in required):raise ValueError('required_parameter_missing: '+path)
        for key,item in value.items():
            if key in props:validate_schema(props[key],item,path+'.'+key,depth+1)
            elif schema.get('additionalProperties') is False:raise ValueError('unknown_parameter: '+path+'.'+key)
            elif isinstance(schema.get('additionalProperties'),dict):validate_schema(schema['additionalProperties'],item,path+'.'+key,depth+1)
    elif isinstance(value,list):
        if len(value)<schema.get('minItems',0) or len(value)>schema.get('maxItems',1000000):raise ValueError('parameter_array_length: '+path)
        if 'items' in schema:
            for index,item in enumerate(value):validate_schema(schema['items'],item,f'{path}[{index}]',depth+1)
    elif isinstance(value,str):
        if len(value)<schema.get('minLength',0) or len(value)>schema.get('maxLength',1000000):raise ValueError('parameter_string_length: '+path)
        if 'pattern' in schema and not re.search(schema['pattern'],value):raise ValueError('parameter_pattern_mismatch: '+path)
    elif isinstance(value,(int,float)) and not isinstance(value,bool):
        if isinstance(value,float) and not math.isfinite(value):raise ValueError('nonfinite_json_number')
        for key,op in (('minimum',lambda a,b:a<b),('maximum',lambda a,b:a>b),('exclusiveMinimum',lambda a,b:a<=b),('exclusiveMaximum',lambda a,b:a>=b)):
            if key in schema and op(value,schema[key]):raise ValueError('parameter_number_range: '+path)


def validate_shape(domain,plan):
    """只接受本领域、已发现命令与对象参数；状态前置条件由真实会话判断。"""
    if not isinstance(plan,dict) or set(plan)-{'domain','steps'} or plan.get('domain')!=domain:raise ValueError('plan_domain_or_fields_invalid')
    steps=plan.get('steps')
    if not isinstance(steps,list) or not 1<=len(steps)<=1000:raise ValueError('plan_steps_invalid')
    for step in steps:
        if not isinstance(step,dict) or set(step)!={'command','params'} or not isinstance(step['command'],str) or not isinstance(step['params'],dict):raise ValueError('plan_step_invalid')
    return steps


def check_plan(domain,rows,plan):
    """校验目录中的实际命令和可用 schema；原生会话前置条件保持待执行。"""
    steps=validate_shape(domain,plan)
    index={r['id']:r for r in rows};native_only=False
    for step in steps:
        if not isinstance(step,dict) or set(step)!={'command','params'} or not isinstance(step['command'],str) or not isinstance(step['params'],dict):raise ValueError('plan_step_invalid')
        row=index.get(step['command'])
        if row is None:raise ValueError('unknown_command: '+step['command'])
        if row['inputSchema'] is not None:validate_schema(row['inputSchema'],step['params'])
        else:native_only=True
    return {'structuralCheck':'PASS','steps':len(steps),'nativeParameterValidation':'NOT_RUN','schemaSubsetCheck':'NOT_AVAILABLE' if native_only else 'PASS','execution':'NOT_RUN'}


def native_script(domain,steps):
    """整个计划只启动一个原生会话，保留文档 ID 与跨步骤状态。"""
    if domain=='printcraft':return [{'tool':s['command'],'args':s['params']} for s in steps]
    return steps


def file_sha(path):
    """以流方式计算输入摘要；不执行文件内容。"""
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def capture_inputs(paths):
    """登记调用者显式输入及目录内普通文件，拒绝链接与缺失输入。"""
    result={}
    for raw in paths:
        root=Path(raw).expanduser().absolute()
        if root.is_symlink() or not root.exists():raise ValueError('input_missing_or_symlink: '+str(root))
        entries=sorted(root.rglob('*')) if root.is_dir() else [root]
        if len(entries)>100000:raise ValueError('input_manifest_too_large')
        for path in entries:
            if path.is_symlink():raise ValueError('input_symlink: '+str(path))
            if path.is_dir():continue
            if not path.is_file():raise ValueError('input_not_regular_file: '+str(path))
            result[str(path)]=file_sha(path)
    return result


def capture_resources(script_dir):
    """把当前技能执行资源绑定到回执，不能借用兄弟技能的身份。"""
    names=('cli.py','bootstrap.py','runtime.lock.json','command_gateway.py','commands.py')
    result={}
    for name in names:
        path=script_dir/name
        if path.is_symlink() or not path.is_file():raise ValueError('skill_resource_missing_or_symlink: '+name)
        result[name]=file_sha(path)
    return result


def expected_runtime_identity(script_dir,runtime_home):
    """在原生启动前记录锁定的运行时身份；它不是安装或运行成功的证明。"""
    lock_path=Path(script_dir)/'runtime.lock.json'
    lock=strict_json(lock_path.read_text(encoding='utf-8'))
    system=platform.system().lower();machine=platform.machine().lower()
    if machine in ('aarch64','arm64'):machine='arm64'
    key=f'{system}-{machine}'
    artifact=lock.get('artifacts',{}).get(key)
    home=Path(runtime_home or os.environ.get('CRAFT_RUNTIME_HOME',str(Path.home()/'.local/share/craft-runtimes'))).expanduser().absolute()
    return {'verificationStatus':'LOCKED_EXPECTATION','name':lock.get('artifact'),'version':lock.get('resolvedVersion'),'platform':key,'runtimeHome':str(home),'expectedBinarySha256':artifact.get('binarySha256') if isinstance(artifact,dict) else None,'archiveSha256':artifact.get('archiveSha256') if isinstance(artifact,dict) else None,'lockSha256':file_sha(lock_path)}


def step_references(run_id,steps):
    """保留计划顺序和 command/params 身份，所有步骤仍交给同一原生会话。"""
    references=[]
    for index,step in enumerate(steps):
        params=json.dumps(step['params'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        references.append({'stepRef':f'{run_id}:step:{index}','index':index,'command':step['command'],'paramsSha256':hashlib.sha256(params).hexdigest()})
    return references


def observe_step_results(references,native_status,started,stdout=''):
    """优先映射固定原生批次给出的完整前缀；失败步仍保持可能已产生副作用。"""
    if started and native_status=='FAILED_OR_PARTIAL':
        try:
            batch=strict_json(stdout)
            if not isinstance(batch,dict) or set(batch)!={'completed','error','failedCommand','failedIndex','results'}:raise ValueError('native_batch_result_schema_unknown')
            completed=batch['completed'];failed_index=batch['failedIndex'];failed_command=batch['failedCommand'];results=batch['results'];reason=batch['error']
            if type(completed) is not int or type(failed_index) is not int or completed<0 or completed!=failed_index or failed_index>=len(references) or not isinstance(failed_command,str) or failed_command!=references[failed_index]['command'] or not isinstance(reason,str) or not reason or not isinstance(results,list) or len(results)!=completed:raise ValueError('native_batch_result_identity_mismatch')
            observed=[]
            for index,reference in enumerate(references):
                base={'stepRef':reference['stepRef'],'index':index,'command':reference['command']}
                if index<completed:
                    encoded=json.dumps(results[index],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')
                    observed.append({**base,'status':'STEP_COMPLETED_REVIEW_REQUIRED','granularity':'native-step-result','resultSha256':hashlib.sha256(encoded).hexdigest()})
                elif index==failed_index:
                    observed.append({**base,'status':'STEP_FAILED_OR_PARTIAL','granularity':'native-step-result','failureReason':reason})
                else:
                    observed.append({**base,'status':'NOT_STARTED','granularity':'single-native-session'})
            return observed
        except (ValueError,TypeError,KeyError):
            pass
    if not started or native_status=='NOT_STARTED':status='NOT_STARTED'
    elif native_status=='NATIVE_EXIT_ZERO_REVIEW_REQUIRED':status='BATCH_EXIT_ZERO_REVIEW_REQUIRED'
    else:status='UNKNOWN'
    return [{'stepRef':item['stepRef'],'index':item['index'],'command':item['command'],'status':status,'granularity':'single-native-session'} for item in references]


def saved_project_checkpoint(steps,references,native_status,started,stdout):
    """仅记录原生回执确认已完成的 file.saveAs 产物；它仍需新会话重开验证。"""
    if not started or native_status not in {'NATIVE_EXIT_ZERO_REVIEW_REQUIRED','FAILED_OR_PARTIAL'}:return None
    try:
        batch=strict_json(stdout)
        if not isinstance(batch,dict) or not isinstance(batch.get('completed'),int) or isinstance(batch.get('completed'),bool) or batch['completed']<0 or not isinstance(batch.get('results'),list):return None
        if native_status=='FAILED_OR_PARTIAL':
            failed_index=batch.get('failedIndex');failed_command=batch.get('failedCommand');error=batch.get('error')
            if set(batch)!={'completed','error','failedCommand','failedIndex','results'} or type(failed_index) is not int or failed_index!=batch['completed'] or failed_index>=len(steps) or failed_command!=steps[failed_index].get('command') or not isinstance(error,str) or not error or len(batch['results'])!=batch['completed']:return None
        elif batch['completed']!=len(steps) or len(batch['results'])!=batch['completed']:
            return None
        candidates=[]
        for index in range(min(batch['completed'],len(steps))):
            step=steps[index];result=batch['results'][index]
            if step.get('command')!='file.saveAs' or not isinstance(result,dict):continue
            raw_path=result.get('path');reported_bytes=result.get('bytes')
            if not isinstance(raw_path,str) or not raw_path or type(reported_bytes) is not int or reported_bytes<0:continue
            path=Path(raw_path).expanduser().absolute()
            if path.is_symlink() or not path.is_file() or path.stat().st_size!=reported_bytes:continue
            candidates.append({'status':'SAVED_REOPEN_REQUIRED','stepRef':references[index]['stepRef'],'path':str(path),'bytes':reported_bytes,'sha256':file_sha(path),'resultSha256':hashlib.sha256(json.dumps(result,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()})
        return candidates[-1] if candidates else None
    except (OSError,ValueError,TypeError,KeyError):return None


def _recovery_rejected(reason,discovered_objects=None):
    return {'status':'RECOVERY_REJECTED','resumeAllowed':False,'automaticExecution':False,'automaticReplay':False,'completeAcceptance':False,'reason':reason,'discoveredObjects':discovered_objects or []}


def _contains_cross_session_reference(value):
    if isinstance(value,str):return re.search(r'\bstep:\d+\b',value) is not None
    if isinstance(value,dict):return any(_contains_cross_session_reference(item) for item in value.values())
    if isinstance(value,list):return any(_contains_cross_session_reference(item) for item in value)
    return False


def build_recovery_plan(original,checkpoint,steps,checkpoint_steps=None):
    """核对真实保存工程的新会话重开结果，只输出未启动后缀，不执行恢复写入。"""
    if not isinstance(original,dict) or original.get('schemaVersion')!=2 or original.get('domain')!='designcraft':return _recovery_rejected('original_receipt_identity_missing_or_unsupported')
    if not isinstance(checkpoint,dict) or checkpoint.get('schemaVersion')!=2 or checkpoint.get('domain')!='designcraft':return _recovery_rejected('reopen_receipt_identity_missing_or_unsupported')
    if original.get('status')!='FAILED_OR_PARTIAL' or original.get('terminationVerified') is not True:return _recovery_rejected('original_process_not_verified_terminal_failure')
    saved=original.get('savedProjectCheckpoint')
    if not isinstance(saved,dict) or saved.get('status')!='SAVED_REOPEN_REQUIRED':return _recovery_rejected('saved_project_checkpoint_missing')
    raw_path=saved.get('path');expected_sha=saved.get('sha256');expected_bytes=saved.get('bytes')
    if not isinstance(raw_path,str) or not Path(raw_path).is_absolute() or not isinstance(expected_sha,str) or not re.fullmatch('[0-9a-f]{64}',expected_sha) or type(expected_bytes) is not int:return _recovery_rejected('saved_project_checkpoint_identity_invalid')
    project=Path(raw_path)
    if project.is_symlink() or not project.is_file():return _recovery_rejected('saved_project_checkpoint_missing_or_unsafe')
    try:
        if project.stat().st_size!=expected_bytes or file_sha(project)!=expected_sha:return _recovery_rejected('saved_project_checkpoint_digest_mismatch')
    except OSError:return _recovery_rejected('saved_project_checkpoint_unreadable')
    original_results=original.get('stepResults')
    try:original_batch=strict_json(original.get('stdout',''))
    except (ValueError,TypeError):return _recovery_rejected('original_native_result_unavailable')
    if not isinstance(original_results,list) or not isinstance(original_batch,dict) or type(original_batch.get('completed')) is not int or original_batch.get('failedIndex')!=original_batch.get('completed') or not isinstance(original_batch.get('results'),list) or len(original_batch['results'])!=original_batch['completed']:return _recovery_rejected('original_native_step_result_unverifiable')
    save_index=next((index for index,item in enumerate(original_results) if isinstance(item,dict) and item.get('stepRef')==saved.get('stepRef')),None)
    if save_index is None or save_index>=original_batch['completed'] or save_index>=len(steps) or steps[save_index].get('command')!='file.saveAs':return _recovery_rejected('saved_project_step_identity_mismatch')
    save_result=original_batch['results'][save_index]
    if not isinstance(save_result,dict):return _recovery_rejected('saved_project_native_result_mismatch')
    save_result_sha=hashlib.sha256(json.dumps(save_result,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    try:reported_path=Path(save_result.get('path','')).expanduser().absolute()
    except (TypeError,OSError):return _recovery_rejected('saved_project_native_result_mismatch')
    if str(reported_path)!=str(project.absolute()) or save_result.get('bytes')!=expected_bytes or saved.get('resultSha256')!=save_result_sha:return _recovery_rejected('saved_project_native_result_mismatch')
    project_path=str(project.absolute())
    if checkpoint.get('status')!='NATIVE_EXIT_ZERO_REVIEW_REQUIRED' or checkpoint.get('exitCode')!=0 or checkpoint.get('terminationVerified') is not True:return _recovery_rejected('reopen_process_not_verified_success')
    before=checkpoint.get('inputSha256');after=checkpoint.get('inputAfterSha256')
    if not isinstance(before,dict) or not isinstance(after,dict) or before.get(project_path)!=expected_sha or after.get(project_path)!=expected_sha:return _recovery_rejected('reopened_project_input_digest_mismatch')
    refs=checkpoint.get('stepReferences')
    if not isinstance(refs,list) or [item.get('command') for item in refs if isinstance(item,dict)]!=['file.open','document.inspect']:return _recovery_rejected('reopen_plan_not_read_only_identity_check')
    if not isinstance(checkpoint_steps,list) or len(checkpoint_steps)!=2 or checkpoint_steps[0].get('command')!='file.open' or checkpoint_steps[0].get('params')!={'path':project_path} or checkpoint_steps[1]!={'command':'document.inspect','params':{}}:return _recovery_rejected('reopen_plan_project_path_mismatch')
    try:batch=strict_json(checkpoint.get('stdout',''))
    except (ValueError,TypeError):return _recovery_rejected('reopen_output_invalid')
    if not isinstance(batch,dict) or type(batch.get('completed')) is not int or batch.get('completed')!=2 or not isinstance(batch.get('results'),list) or len(batch['results'])!=2:return _recovery_rejected('reopen_output_incomplete')
    inspection=batch['results'][1]
    if not isinstance(batch['results'][0],dict) or batch['results'][0].get('index')!=1:return _recovery_rejected('reopened_project_identity_mismatch')
    if not isinstance(inspection,dict) or inspection.get('path')!=project_path or inspection.get('dirty') is not False or type(inspection.get('pageCount')) is not int or inspection['pageCount']<1 or not isinstance(inspection.get('spreads'),list):return _recovery_rejected('reopened_document_inspection_incomplete')
    discovered=[];seen=set()
    for spread in inspection['spreads']:
        if not isinstance(spread,dict) or not isinstance(spread.get('items'),list):return _recovery_rejected('reopened_object_inventory_invalid')
        for item in spread['items']:
            if not isinstance(item,dict) or type(item.get('id')) is not int:continue
            identity={'id':item['id'],'kind':item.get('kind','unknown')}
            for key in ('name','story'):
                if isinstance(item.get(key),(str,int)):identity[key]=item[key]
            encoded=json.dumps(identity,sort_keys=True,ensure_ascii=False)
            if encoded not in seen:seen.add(encoded);discovered.append(identity)
    stories=inspection.get('stories',[])
    if not isinstance(stories,list):return _recovery_rejected('reopened_story_inventory_invalid',discovered)
    for story in stories:
        if not isinstance(story,dict) or type(story.get('id')) is not int:continue
        identity={'id':story['id'],'kind':'story'}
        if isinstance(story.get('name'),str):identity['name']=story['name']
        encoded=json.dumps(identity,sort_keys=True,ensure_ascii=False)
        if encoded not in seen:seen.add(encoded);discovered.append(identity)
    results=original.get('stepResults')
    if not isinstance(results,list) or len(results)!=len(steps) or not results:return _recovery_rejected('original_step_identity_missing',discovered)
    failed=[index for index,item in enumerate(results) if isinstance(item,dict) and item.get('status')=='STEP_FAILED_OR_PARTIAL']
    if len(failed)!=1:return _recovery_rejected('original_failed_step_not_unambiguous',discovered)
    failed_index=failed[0]
    failed_result=results[failed_index]
    if original_batch.get('failedIndex')!=failed_index or original_batch.get('failedCommand')!=failed_result.get('command') or original_batch.get('error')!=failed_result.get('failureReason') or original_batch['completed']!=failed_index:return _recovery_rejected('original_failure_identity_mismatch',discovered)
    failed_result=results[failed_index]
    if original_batch.get('failedIndex')!=failed_index or original_batch.get('failedCommand')!=failed_result.get('command') or original_batch.get('error')!=failed_result.get('failureReason') or original_batch['completed']!=failed_index:return _recovery_rejected('original_failure_identity_mismatch',discovered)
    if any(not isinstance(item,dict) or item.get('index')!=index for index,item in enumerate(results)):return _recovery_rejected('original_step_order_mismatch',discovered)
    if any(item.get('status')!='STEP_COMPLETED_REVIEW_REQUIRED' for item in results[:failed_index]) or any(item.get('status')!='NOT_STARTED' for item in results[failed_index+1:]):return _recovery_rejected('original_step_observation_not_recoverable',discovered)
    remaining=steps[failed_index+1:]
    if not remaining:return {'contractVersion':'designcraft-checkpoint-recovery/v1','status':'CHECKPOINT_VERIFIED_NO_REMAINING_STEPS','resumeAllowed':False,'automaticExecution':False,'automaticReplay':False,'completeAcceptance':False,'originalRunId':original.get('runId'),'reopenRunId':checkpoint.get('runId'),'failedStepIndex':failed_index,'savedProjectSha256':expected_sha,'discoveredObjects':discovered,'remainingPlan':{'domain':'designcraft','steps':[]}}
    if any(_contains_cross_session_reference(step) for step in remaining):return {'contractVersion':'designcraft-checkpoint-recovery/v1','status':'MANUAL_OBJECT_REBINDING_REQUIRED','resumeAllowed':False,'automaticExecution':False,'automaticReplay':False,'completeAcceptance':False,'originalRunId':original.get('runId'),'reopenRunId':checkpoint.get('runId'),'reason':'remaining_steps_reference_prior_session_objects','failedStepIndex':failed_index,'savedProjectSha256':expected_sha,'discoveredObjects':discovered,'remainingSteps':remaining}
    return {'contractVersion':'designcraft-checkpoint-recovery/v1','status':'RECOVERY_READY','resumeAllowed':True,'automaticExecution':False,'automaticReplay':False,'completeAcceptance':False,'originalRunId':original.get('runId'),'failedStepIndex':failed_index,'savedProjectPath':project_path,'savedProjectSha256':expected_sha,'reopenRunId':checkpoint.get('runId'),'discoveredObjects':discovered,'remainingPlan':{'domain':'designcraft','steps':remaining},'nextAction':'review remainingPlan and explicitly submit it as a new run'}


def _business_step(reference,status,reason,**details):
    return {'stepRef':reference['stepRef'],'index':reference['index'],'command':reference['command'],'status':status,'reason':reason,**details}


def _preflight_assessment(reference,result):
    if not isinstance(result,dict) or set(result)!={'errors','issues','warnings'}:
        return _business_step(reference,'UNKNOWN','preflight_result_schema_unknown')
    errors=result['errors'];warnings=result['warnings'];issues=result['issues']
    if type(errors) is not int or errors<0 or type(warnings) is not int or warnings<0 or not isinstance(issues,list):
        return _business_step(reference,'UNKNOWN','preflight_result_schema_unknown')
    normalized=[];observed_errors=0;observed_warnings=0;missing_image=False
    for issue in issues:
        allowed={'severity','kind','message','item','page'}
        if not isinstance(issue,dict) or set(issue)-allowed or not {'severity','kind','message'}.issubset(issue):
            return _business_step(reference,'UNKNOWN','preflight_issue_schema_unknown')
        severity=issue['severity'];kind=issue['kind'];message=issue['message']
        if severity not in ('info','warning','error') or not isinstance(kind,str) or not kind or not isinstance(message,str) or not message:
            return _business_step(reference,'UNKNOWN','preflight_issue_schema_unknown')
        if 'item' in issue and (type(issue['item']) is not int or issue['item']<0):
            return _business_step(reference,'UNKNOWN','preflight_issue_schema_unknown')
        if 'page' in issue and (type(issue['page']) is not int or issue['page']<1):
            return _business_step(reference,'UNKNOWN','preflight_issue_schema_unknown')
        observed_errors+=severity=='error';observed_warnings+=severity=='warning'
        normalized_issue={key:issue[key] for key in ('severity','kind','message','item','page') if key in issue}
        normalized.append(normalized_issue)
        compact=''.join(char.lower() for char in kind if char.isalnum())
        missing_image=missing_image or compact in {'missingimage','missingimagefile','missingasset'}
    if observed_errors!=errors or observed_warnings!=warnings:
        return _business_step(reference,'UNKNOWN','preflight_count_mismatch')
    if missing_image:
        status='REJECTED';reason='missing_image'
    elif errors:
        status='REJECTED';reason='preflight_errors'
    elif warnings:
        status='REVIEW_REQUIRED';reason='preflight_warnings'
    else:
        status='PASS';reason='preflight_clean'
    return _business_step(reference,status,reason,issueCounts={'errors':errors,'warnings':warnings},issues=normalized)


def _link_assessment(reference,result):
    if not isinstance(result,list):return _business_step(reference,'UNKNOWN','links_result_schema_unknown')
    unhealthy=[]
    for link in result:
        allowed={'asset','name','path','pixels','status','uses'}
        if not isinstance(link,dict) or set(link)!=allowed or type(link.get('asset')) is not int or link['asset']<0 or not isinstance(link.get('name'),str) or not link['name'] or (link.get('path') is not None and not isinstance(link.get('path'),str)) or link.get('status') not in ('ok','modified','missing','embedded') or not isinstance(link.get('pixels'),list) or len(link['pixels'])!=2 or any(type(value) is not int or value<1 for value in link['pixels']) or not isinstance(link.get('uses'),list):
            return _business_step(reference,'UNKNOWN','links_result_schema_unknown')
        for use in link['uses']:
            if not isinstance(use,dict) or set(use)!={'id','page','ppi'} or type(use.get('id')) is not int or not isinstance(use.get('page'),str) or not use['page'] or type(use.get('ppi')) not in (int,float) or use['ppi']<=0:
                return _business_step(reference,'UNKNOWN','links_result_schema_unknown')
        if link['status'] in ('missing','modified'):
            unhealthy.append({'name':link['name'],'status':link['status']})
    if any(link['status']=='missing' for link in unhealthy):
        return _business_step(reference,'REJECTED','missing_image',unhealthyLinks=unhealthy)
    if unhealthy:
        return _business_step(reference,'REVIEW_REQUIRED','modified_image',unhealthyLinks=unhealthy)
    return _business_step(reference,'PASS','links_available')


def assess_business_results(stdout,references,domain):
    """仅分类有固定输出合同的 DesignCraft 业务结果；未知形状保持 UNKNOWN。"""
    if domain!='designcraft':
        return {'contractVersion':'designcraft-business-assessment/v1','status':'NOT_APPLICABLE','steps':[]}
    unknown=[_business_step(item,'UNKNOWN','native_batch_result_unknown') for item in references]
    try:batch=strict_json(stdout)
    except (ValueError,TypeError):
        return {'contractVersion':'designcraft-business-assessment/v1','status':'UNKNOWN','steps':unknown}
    if not isinstance(batch,dict) or set(batch)!={'completed','results'} or type(batch.get('completed')) is not int or not isinstance(batch.get('results'),list) or batch['completed']!=len(references) or len(batch['results'])!=len(references):
        return {'contractVersion':'designcraft-business-assessment/v1','status':'UNKNOWN','steps':unknown}
    assessments=[]
    for reference,result in zip(references,batch['results']):
        command=reference['command']
        if command=='preflight.run':
            item=_preflight_assessment(reference,result)
        elif command=='links.list':
            item=_link_assessment(reference,result)
        elif command=='data.fields':
            valid=isinstance(result,list) and bool(result) and all(isinstance(field,str) and field.strip() for field in result) and len(set(result))==len(result)
            item=_business_step(reference,'PASS' if valid else 'UNKNOWN','field_list_read' if valid else 'data_fields_result_schema_unknown')
        elif command=='data.merge':
            valid=isinstance(result,dict) and set(result)=={'records','pages'} and type(result.get('records')) is int and result['records']>0 and type(result.get('pages')) is int and result['pages']>0
            item=_business_step(reference,'REVIEW_REQUIRED' if valid else 'UNKNOWN','merge_counts_need_content_verification' if valid else 'data_merge_result_schema_unknown')
        elif command=='file.exportPdf':
            valid=isinstance(result,dict) and set(result)=={'path','bytes','pages','warnings'} and isinstance(result.get('path'),str) and bool(result['path']) and type(result.get('bytes')) is int and result['bytes']>0 and type(result.get('pages')) is int and result['pages']>0 and isinstance(result.get('warnings'),list) and all(isinstance(warning,str) for warning in result['warnings'])
            if not valid:item=_business_step(reference,'UNKNOWN','pdf_export_result_schema_unknown')
            elif result['warnings']:item=_business_step(reference,'REVIEW_REQUIRED','pdf_export_warnings')
            else:item=_business_step(reference,'PASS','pdf_export_recorded')
        else:
            item=_business_step(reference,'NOT_CLASSIFIED','no_business_result_contract')
        assessments.append(item)
    classified=[item['status'] for item in assessments if item['status']!='NOT_CLASSIFIED']
    if 'REJECTED' in classified:status='REJECTED'
    elif 'UNKNOWN' in classified:status='UNKNOWN'
    elif 'REVIEW_REQUIRED' in classified:status='REVIEW_REQUIRED'
    elif 'PASS' in classified:status='PASS'
    else:status='NOT_CLASSIFIED'
    return {'contractVersion':'designcraft-business-assessment/v1','status':status,'steps':assessments}


def validate_business_assessment(value,references):
    """拒绝错绑、未知版本或结构漂移的业务分类回执。"""
    allowed_statuses={'PASS','REVIEW_REQUIRED','REJECTED','UNKNOWN','NOT_CLASSIFIED','NOT_APPLICABLE'}
    if not isinstance(value,dict) or set(value)!={'contractVersion','status','steps'} or value.get('contractVersion')!='designcraft-business-assessment/v1' or value.get('status') not in allowed_statuses or not isinstance(value.get('steps'),list):
        raise ValueError('receipt_business_assessment_invalid')
    if value['status']=='NOT_APPLICABLE':
        if value['steps']:raise ValueError('receipt_business_assessment_invalid')
        return
    if len(value['steps'])!=len(references):raise ValueError('receipt_business_assessment_invalid')
    step_statuses=[]
    statuses={'PASS','REVIEW_REQUIRED','REJECTED','UNKNOWN','NOT_CLASSIFIED'}
    for reference,step in zip(references,value['steps']):
        if not isinstance(step,dict) or set(step)-{'stepRef','index','command','status','reason','issueCounts','issues','unhealthyLinks'} or not {'stepRef','index','command','status','reason'}.issubset(step):
            raise ValueError('receipt_business_assessment_invalid')
        if step['stepRef']!=reference['stepRef'] or step['index']!=reference['index'] or step['command']!=reference['command'] or step['status'] not in statuses or not isinstance(step['reason'],str) or not step['reason']:
            raise ValueError('receipt_business_assessment_identity_mismatch')
        if 'issueCounts' in step and (step['command']!='preflight.run' or not isinstance(step['issueCounts'],dict) or set(step['issueCounts'])!={'errors','warnings'} or any(type(count) is not int or count<0 for count in step['issueCounts'].values())):
            raise ValueError('receipt_business_assessment_invalid')
        if 'issues' in step and (step['command']!='preflight.run' or not isinstance(step['issues'],list)):
            raise ValueError('receipt_business_assessment_invalid')
        if 'unhealthyLinks' in step and (step['command']!='links.list' or not isinstance(step['unhealthyLinks'],list) or any(not isinstance(link,dict) or set(link)!={'name','status'} or not isinstance(link['name'],str) or link['status'] not in ('missing','modified') for link in step['unhealthyLinks'])):
            raise ValueError('receipt_business_assessment_invalid')
        step_statuses.append(step['status'])
    classified=[item for item in step_statuses if item!='NOT_CLASSIFIED']
    expected=('REJECTED' if 'REJECTED' in classified else 'UNKNOWN' if 'UNKNOWN' in classified else 'REVIEW_REQUIRED' if 'REVIEW_REQUIRED' in classified else 'PASS' if 'PASS' in classified else 'NOT_CLASSIFIED')
    if value['status']!=expected:raise ValueError('receipt_business_assessment_aggregate_mismatch')


def copy_working_source(source,output):
    """把 DesignCraft 输入复制到新任务目录，原生编辑只接触副本。"""
    source=Path(source).expanduser().absolute()
    if source.is_symlink() or not source.exists():raise ValueError('working_source_missing_or_symlink')
    root=Path(output)/'working-copy';root.mkdir()
    target=root/source.name
    if source.is_dir():shutil.copytree(source,target)
    elif source.is_file():shutil.copy2(source,target)
    else:raise ValueError('working_source_not_regular')
    return target


def capture_working_copy(path):
    """记录工作副本的相对路径与文件摘要；允许原生命令修改副本。"""
    root=Path(path)
    if root.is_symlink() or not root.exists():raise ValueError('working_copy_missing_or_symlink')
    entries=sorted(root.rglob('*')) if root.is_dir() else [root]
    if len(entries)>100000:raise ValueError('working_copy_manifest_too_large')
    result={}
    for item in entries:
        if item.is_symlink():raise ValueError('working_copy_symlink')
        if item.is_dir():continue
        if not item.is_file():raise ValueError('working_copy_not_regular')
        relative=item.relative_to(root).as_posix() if root.is_dir() else item.name
        result[relative]=file_sha(item)
    return result


def write_receipt(path,receipt):
    """同目录暂存、刷盘并原子替换；中断不留下半个JSON回执。"""
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,prefix='.receipt-',delete=False) as stream:
            temporary=Path(stream.name)
            stream.write(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
            stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary is not None and temporary.exists():temporary.unlink()


def read_native_result(path,process_returncode):
    """只接受完整已知版本结果，并确保状态与启动器退出码一致。"""
    try:
        value=strict_json(Path(path).read_text(encoding='utf-8'))
        if not isinstance(value,dict) or type(value.get('schemaVersion')) is not int or value.get('schemaVersion')!=1:raise ValueError('unsupported_native_result_schema')
        statuses={'NOT_STARTED','FAILED_OR_PARTIAL','UNKNOWN','NATIVE_EXIT_ZERO_REVIEW_REQUIRED'}
        required={'schemaVersion','status','reason','exitCode','started','startedAt','finishedAt','terminationVerified','descendantsTerminationVerified'}
        optional={'error','stdout','stderr','dependencySetup'}
        if not required.issubset(value) or set(value)-required-optional or value.get('status') not in statuses or not isinstance(value.get('reason'),str) or not value['reason'] or type(value.get('started')) is not bool or type(value.get('terminationVerified')) is not bool or type(value.get('descendantsTerminationVerified')) is not bool or not isinstance(value.get('startedAt'),str) or not isinstance(value.get('finishedAt'),str):raise ValueError('invalid_native_result_shape')
        for field in ('error','stdout','stderr'):
            if field in value and not isinstance(value[field],str):raise ValueError('invalid_native_result_shape')
        if 'dependencySetup' in value:
            setup=value['dependencySetup']
            if not isinstance(setup,dict) or set(setup)!={'skill','bootstrapScript','runtimeHome','automaticRetry'} or any(not isinstance(setup.get(field),str) or not setup[field] for field in ('skill','bootstrapScript','runtimeHome')) or type(setup.get('automaticRetry')) is not bool:raise ValueError('invalid_native_result_shape')
        code=value.get('exitCode')
        if code is not None and type(code) is not int:raise ValueError('invalid_native_result_exit_code')
        if value['status']=='NOT_STARTED' and value['started'] or value['status']=='NATIVE_EXIT_ZERO_REVIEW_REQUIRED' and (not value['started'] or code!=0 or not value['terminationVerified']):raise ValueError('invalid_native_result_state')
        if process_returncode==0 and (value['status']!='NATIVE_EXIT_ZERO_REVIEW_REQUIRED' or code!=0):raise ValueError('native_result_exit_mismatch')
        if process_returncode!=0 and (value['status']=='NATIVE_EXIT_ZERO_REVIEW_REQUIRED' or code not in (None,process_returncode)):raise ValueError('native_result_exit_mismatch')
        return value
    except (OSError,ValueError,TypeError) as error:
        return {'schemaVersion':None,'status':'UNKNOWN','reason':'native_result_unavailable_or_invalid: '+str(error),'exitCode':None,'started':True,'terminationVerified':False}


def inspect_receipt(path,domain):
    """读取当前或旧回执；旧记录仅展示，不升级为可恢复或可重放身份。"""
    receipt_path=Path(path).expanduser()
    value=strict_json(receipt_path.read_text(encoding='utf-8'))
    if not isinstance(value,dict) or value.get('domain')!=domain:raise ValueError('receipt_domain_mismatch')
    if value.get('schemaVersion')==2:
        if not isinstance(value.get('runId'),str) or value.get('status') not in {'STARTED','NOT_STARTED','FAILED_OR_PARTIAL','UNKNOWN','NATIVE_EXIT_ZERO_REVIEW_REQUIRED','INPUT_CHANGED_REVIEW_REQUIRED','SKILL_CHANGED_REVIEW_REQUIRED','INPUT_OR_SKILL_CHANGED_REVIEW_REQUIRED'}:raise ValueError('invalid_receipt_schema')
        if 'stepReferences' in value or 'stepResults' in value:
            references=value.get('stepReferences');results=value.get('stepResults')
            if value.get('stepResultGranularity')!='single-native-session' or not isinstance(references,list) or not isinstance(results,list) or len(references)!=len(results):raise ValueError('receipt_step_identity_mismatch')
            for index,(reference,result) in enumerate(zip(references,results)):
                if not isinstance(reference,dict) or not isinstance(result,dict) or type(reference.get('index')) is not int or reference.get('index')!=index or reference.get('stepRef')!=f"{value['runId']}:step:{index}" or not isinstance(reference.get('command'),str) or not reference['command'] or not isinstance(reference.get('paramsSha256'),str) or not re.fullmatch('[0-9a-f]{64}',reference['paramsSha256']):raise ValueError('receipt_step_identity_mismatch')
                status=result.get('status')
                if result.get('stepRef')!=reference['stepRef'] or result.get('index')!=index or result.get('command')!=reference['command'] or status not in {'SUBMITTED','NOT_STARTED','BATCH_EXIT_ZERO_REVIEW_REQUIRED','UNKNOWN','STEP_COMPLETED_REVIEW_REQUIRED','STEP_FAILED_OR_PARTIAL'}:raise ValueError('receipt_step_identity_mismatch')
                if status in {'STEP_COMPLETED_REVIEW_REQUIRED','STEP_FAILED_OR_PARTIAL'}:
                    if result.get('granularity')!='native-step-result':raise ValueError('receipt_step_identity_mismatch')
                    if status=='STEP_COMPLETED_REVIEW_REQUIRED' and (not isinstance(result.get('resultSha256'),str) or not re.fullmatch('[0-9a-f]{64}',result['resultSha256'])):raise ValueError('receipt_step_identity_mismatch')
                    if status=='STEP_FAILED_OR_PARTIAL' and (not isinstance(result.get('failureReason'),str) or not result['failureReason']):raise ValueError('receipt_step_identity_mismatch')
                elif result.get('granularity')!='single-native-session':raise ValueError('receipt_step_identity_mismatch')
            partial=[item for item in results if item.get('status') in {'STEP_COMPLETED_REVIEW_REQUIRED','STEP_FAILED_OR_PARTIAL'}]
            if partial:
                batch=strict_json(output_text(value.get('stdout')))
                if not isinstance(batch,dict) or set(batch)!={'completed','error','failedCommand','failedIndex','results'}:raise ValueError('receipt_step_result_evidence_invalid')
                completed=batch['completed'];failed_index=batch['failedIndex'];native_results=batch['results']
                if type(completed) is not int or type(failed_index) is not int or completed!=failed_index or completed<0 or failed_index>=len(results) or not isinstance(native_results,list) or len(native_results)!=completed or batch.get('failedCommand')!=results[failed_index].get('command') or not isinstance(batch.get('error'),str) or not batch['error']:raise ValueError('receipt_step_result_evidence_invalid')
                for index,result in enumerate(results):
                    if result.get('status')=='STEP_COMPLETED_REVIEW_REQUIRED':
                        if index>=completed:raise ValueError('receipt_step_result_evidence_invalid')
                        encoded=json.dumps(native_results[index],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')
                        if result.get('resultSha256')!=hashlib.sha256(encoded).hexdigest():raise ValueError('receipt_step_result_evidence_invalid')
                    elif result.get('status')=='STEP_FAILED_OR_PARTIAL':
                        if index!=failed_index or result.get('failureReason')!=batch.get('error') or result.get('command')!=batch.get('failedCommand'):raise ValueError('receipt_step_result_evidence_invalid')
                    elif completed<len(results) and index>failed_index and result.get('status')!='NOT_STARTED':raise ValueError('receipt_step_result_evidence_invalid')
                    if index<completed and result.get('status')!='STEP_COMPLETED_REVIEW_REQUIRED':raise ValueError('receipt_step_result_evidence_invalid')
                    if index>failed_index and result.get('status')!='NOT_STARTED':raise ValueError('receipt_step_result_evidence_invalid')
                if sum(result.get('status')=='STEP_FAILED_OR_PARTIAL' for result in results)!=1:raise ValueError('receipt_step_result_evidence_invalid')
            if 'businessAssessment' in value:validate_business_assessment(value['businessAssessment'],references)
        saved=value.get('savedProjectCheckpoint')
        if saved is not None:
            if not isinstance(saved,dict) or set(saved)!={'status','stepRef','path','bytes','sha256','resultSha256'} or saved.get('status')!='SAVED_REOPEN_REQUIRED' or not isinstance(saved.get('stepRef'),str) or not isinstance(saved.get('path'),str) or not Path(saved['path']).is_absolute() or type(saved.get('bytes')) is not int or saved['bytes']<0 or not re.fullmatch('[0-9a-f]{64}',str(saved.get('sha256'))) or not re.fullmatch('[0-9a-f]{64}',str(saved.get('resultSha256'))):raise ValueError('receipt_saved_checkpoint_invalid')
            if not isinstance(value.get('stepReferences'),list) or saved['stepRef'] not in {item.get('stepRef') for item in value['stepReferences'] if isinstance(item,dict)}:raise ValueError('receipt_saved_checkpoint_identity_mismatch')
        runtime=value.get('runtimeIdentity')
        if runtime is not None:
            if not isinstance(runtime,dict) or runtime.get('verificationStatus')!='LOCKED_EXPECTATION' or not isinstance(runtime.get('name'),str) or not isinstance(runtime.get('version'),str) or not isinstance(runtime.get('platform'),str) or not isinstance(runtime.get('runtimeHome'),str) or not re.fullmatch('[0-9a-f]{64}',str(runtime.get('lockSha256'))):raise ValueError('receipt_runtime_identity_invalid')
            for key in ('expectedBinarySha256','archiveSha256'):
                if runtime.get(key) is not None and (not isinstance(runtime.get(key),str) or not re.fullmatch('[0-9a-f]{64}',runtime[key])):raise ValueError('receipt_runtime_identity_invalid')
        baseline=value.get('directoryBaseline')
        if baseline is not None and (not isinstance(baseline,dict) or set(baseline)!={'path','state','sha256'} or not isinstance(baseline.get('path'),str) or baseline.get('state')!='ABSENT' or baseline.get('sha256') is not None):raise ValueError('receipt_directory_baseline_invalid')
        return value
    if 'schemaVersion' in value:raise ValueError('unsupported_receipt_schema')
    status=value.get('status')
    legacy_statuses={'STARTED','FAILED_OR_PARTIAL','UNKNOWN','NATIVE_EXIT_ZERO_REVIEW_REQUIRED','INPUT_CHANGED_REVIEW_REQUIRED','SKILL_CHANGED_REVIEW_REQUIRED','INPUT_OR_SKILL_CHANGED_REVIEW_REQUIRED'}
    if status not in legacy_statuses:raise ValueError('invalid_legacy_receipt')
    return {'schemaVersion':None,'status':'LEGACY_READ_ONLY','legacyStatus':status,'domain':domain,'legacyReceiptSha256':hashlib.sha256(receipt_path.read_bytes()).hexdigest(),'automaticReplay':False,'resumeAllowed':False,'completeAcceptance':False,'stdout':output_text(value.get('stdout')),'stderr':output_text(value.get('stderr'))}


def output_text(value):
    """保留超时返回的部分日志，兼容subprocess的bytes和str。"""
    return value.decode('utf-8',errors='replace') if isinstance(value,bytes) else value or ''


def main(domain,script_dir):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('list','describe','check','run','receipt','recover'))
    parser.add_argument('argument',nargs='?')
    parser.add_argument('--checkpoint-receipt',type=Path,help='已在新原生会话重开并检查保存工程的回执')
    parser.add_argument('--catalog',type=Path,help='显式离线原生JSON目录；不能用于执行')
    parser.add_argument('--runtime-home',type=Path)
    parser.add_argument('--archive',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--source',type=Path)
    parser.add_argument('--library',type=Path)
    parser.add_argument('--import',dest='imports',type=Path,action='append',default=[])
    parser.add_argument('--root',type=Path)
    parser.add_argument('--input',dest='inputs',type=Path,action='append',default=[],help='显式登记需保全的输入；可重复，不改变原生参数')
    args=parser.parse_args()
    try:
        if args.action=='receipt':
            if args.argument is None:raise ValueError('receipt_path_required')
            print(json.dumps(inspect_receipt(args.argument,domain),ensure_ascii=False,indent=2));return 0
        if args.action=='recover':
            if domain!='designcraft' or args.argument is None or args.checkpoint_receipt is None:raise ValueError('recovery_requires_designcraft_original_and_checkpoint_receipts')
            original=inspect_receipt(args.argument,domain);checkpoint=inspect_receipt(args.checkpoint_receipt,domain)
            resources=capture_resources(script_dir)
            if original.get('skillResourceSha256')!=resources or checkpoint.get('skillResourceSha256')!=resources:raise ValueError('recovery_skill_resources_changed')
            if original.get('runtimeLockSha256')!=checkpoint.get('runtimeLockSha256') or original.get('runtimeIdentity')!=checkpoint.get('runtimeIdentity'):raise ValueError('recovery_runtime_identity_mismatch')
            native_plan=original.get('nativePlanPath');native_hash=original.get('nativePlanSha256')
            if not isinstance(native_plan,str) or not isinstance(native_hash,str) or not re.fullmatch('[0-9a-f]{64}',native_hash):raise ValueError('recovery_original_plan_identity_missing')
            native_path=Path(native_plan)
            if native_path.is_symlink() or not native_path.is_file() or file_sha(native_path)!=native_hash:raise ValueError('recovery_original_plan_changed')
            steps=[strict_json(line) for line in native_path.read_text(encoding='utf-8').splitlines() if line.strip()]
            references=original.get('stepReferences')
            if not isinstance(references,list) or len(steps)!=len(references) or any(not isinstance(step,dict) or step.get('command')!=references[index].get('command') for index,step in enumerate(steps)):raise ValueError('recovery_original_step_identity_mismatch')
            checkpoint_plan=checkpoint.get('nativePlanPath');checkpoint_hash=checkpoint.get('nativePlanSha256')
            if not isinstance(checkpoint_plan,str) or not isinstance(checkpoint_hash,str) or not re.fullmatch('[0-9a-f]{64}',checkpoint_hash):raise ValueError('recovery_reopen_plan_identity_missing')
            checkpoint_path=Path(checkpoint_plan)
            if checkpoint_path.is_symlink() or not checkpoint_path.is_file() or file_sha(checkpoint_path)!=checkpoint_hash:raise ValueError('recovery_reopen_plan_changed')
            checkpoint_steps=[strict_json(line) for line in checkpoint_path.read_text(encoding='utf-8').splitlines() if line.strip()]
            checkpoint_refs=checkpoint.get('stepReferences')
            if not isinstance(checkpoint_refs,list) or len(checkpoint_steps)!=len(checkpoint_refs) or any(not isinstance(step,dict) or step.get('command')!=checkpoint_refs[index].get('command') for index,step in enumerate(checkpoint_steps)):raise ValueError('recovery_reopen_step_identity_mismatch')
            reply=build_recovery_plan(original,checkpoint,steps,checkpoint_steps)
            print(json.dumps(reply,ensure_ascii=False,indent=2));return 0 if reply.get('resumeAllowed') else 1
        plan=None
        # 在安装前检查计划的 JSON、领域与结构；实际目录存在后再检查命令。
        if args.action in ('check','run'):
            if args.argument is None:raise ValueError('plan_required')
            plan=strict_json(Path(args.argument).read_text())
            validate_shape(domain,plan)
        if args.action=='run' and (args.catalog is not None or args.output is None or args.output.exists()):raise ValueError('run_requires_live_catalog_and_new_output')
        if args.action=='describe' and args.argument is None:raise ValueError('command_id_required')
        if domain!='designcraft' and args.source:raise ValueError('source_only_for_designcraft')
        if domain!='lightcraft' and (args.library or args.imports):raise ValueError('library_only_for_lightcraft')
        if domain!='printcraft' and args.root:raise ValueError('root_only_for_printcraft')
        prefix=[sys.executable,'-I','-B',str(script_dir/'cli.py')]
        if args.runtime_home:prefix+=['--runtime-home',str(args.runtime_home)]
        if args.archive:prefix+=['--archive',str(args.archive)]
        input_paths=args.inputs+([args.source] if args.source else [])+args.imports
        input_sha=capture_inputs(input_paths) if args.action=='run' else {}
        resources=capture_resources(script_dir) if args.action=='run' else {}
        if args.catalog:raw=strict_json(args.catalog.read_text())
        else:
            discovery=['tools'] if domain=='printcraft' else ['commands']+(['--json'] if domain=='lightcraft' else [])
            observed=subprocess.run(prefix+['--',*discovery],capture_output=True,text=True,timeout=900)
            if observed.returncode:raise ValueError('native_catalog_failed: '+observed.stdout.strip()+observed.stderr.strip())
            raw=strict_json(observed.stdout)
        rows=normalize(domain,raw)
        if args.action=='list':reply={'domain':domain,'count':len(rows),'commands':rows,'catalogSource':'offline-explicit' if args.catalog else 'live-native'}
        elif args.action=='describe':
            matches=[r for r in rows if r['id']==args.argument]
            if not matches:raise ValueError('unknown_command: '+args.argument)
            reply=matches[0]
        else:
            reply=check_plan(domain,rows,plan)
            if args.action=='run':
                if capture_inputs(input_paths)!=input_sha:raise ValueError('input_changed_before_native_edit')
                if capture_resources(script_dir)!=resources:raise ValueError('skill_resources_changed_before_native_edit')
                args.output.mkdir(parents=True)
                working_source=copy_working_source(args.source,args.output) if domain=='designcraft' and args.source else None
                if working_source is not None and capture_inputs(input_paths)!=input_sha:raise ValueError('input_changed_during_working_copy')
                if working_source is not None and capture_resources(script_dir)!=resources:raise ValueError('skill_resources_changed_during_working_copy')
                working_copy_before=capture_working_copy(working_source) if working_source is not None else None
                script=args.output/'native-plan.json'
                script_data=native_script(domain,plan['steps'])
                if domain=='printcraft':script.write_text(json.dumps(script_data,ensure_ascii=False)+'\n')
                else:script.write_text(''.join(json.dumps(s,ensure_ascii=False)+'\n' for s in script_data))
                argv=['script',str(script)] if domain=='designcraft' else ['run','--script',str(script)]
                if working_source is not None:argv+=['--in',str(working_source)]
                if args.library:argv+=['--library',str(args.library)]
                for source in args.imports:argv+=['--import',str(source)]
                if args.root:argv+=['--root',str(args.root)]
                machine_result=args.output/'native-result.json'
                run_id=str(uuid.uuid4());runtime_identity=expected_runtime_identity(script_dir,args.runtime_home)
                references=step_references(run_id,plan['steps'])
                receipt={'schemaVersion':2,'runId':run_id,'domain':domain,'status':'STARTED','startedAt':datetime.now(timezone.utc).isoformat(),'argv':prefix+['--result-file',str(machine_result),'--',*argv],'catalogSha256':hashlib.sha256(json.dumps(raw,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'planSha256':hashlib.sha256(json.dumps(plan,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'nativePlanPath':str(script),'nativePlanSha256':file_sha(script),'savedProjectCheckpoint':None,'automaticReplay':False,'completeAcceptance':False,'inputSha256':input_sha,'runtimeLockSha256':resources['runtime.lock.json'],'runtimeIdentity':runtime_identity,'skillResourceSha256':resources,'directoryBaseline':{'path':str(args.output),'state':'ABSENT','sha256':None},'outputDirectoryBefore':'ABSENT','stepResultGranularity':'single-native-session','stepReferences':references,'stepResults':[dict(item,status='SUBMITTED') for item in references],'workingCopyPath':str(working_source) if working_source is not None else None,'workingCopyBeforeSha256':working_copy_before}
                target=args.output/'receipt.json';write_receipt(target,receipt)
                try:
                    result=subprocess.run(receipt['argv'],capture_output=True,text=True,timeout=900)
                    native_result=read_native_result(machine_result,result.returncode)
                    receipt.update(status=native_result['status'],reason=native_result.get('reason'),exitCode=native_result.get('exitCode'),started=native_result.get('started'),terminationVerified=native_result.get('terminationVerified'),descendantsTerminationVerified=native_result.get('descendantsTerminationVerified'),nativeResultSchemaVersion=native_result.get('schemaVersion'),finishedAt=native_result.get('finishedAt',datetime.now(timezone.utc).isoformat()),stdout=result.stdout,stderr=result.stderr)
                    receipt['stepResults']=observe_step_results(references,native_result['status'],native_result.get('started') is True,result.stdout)
                    receipt['savedProjectCheckpoint']=saved_project_checkpoint(plan['steps'],references,native_result['status'],native_result.get('started') is True,result.stdout)
                    receipt['businessAssessment']=assess_business_results(receipt['stdout'],references,domain)
                except (OSError,subprocess.SubprocessError,KeyboardInterrupt) as error:
                    receipt.update(status='UNKNOWN',reason='gateway_interrupted_or_timed_out',terminationVerified=False,descendantsTerminationVerified=False,finishedAt=datetime.now(timezone.utc).isoformat(),error=str(error),stdout=output_text(getattr(error,'stdout',None)),stderr=output_text(getattr(error,'stderr',None)))
                    receipt['stepResults']=observe_step_results(references,'UNKNOWN',True)
                try:
                    receipt['inputAfterSha256']=capture_inputs(input_paths)
                    if receipt['inputAfterSha256']!=input_sha and receipt['status']=='NATIVE_EXIT_ZERO_REVIEW_REQUIRED':receipt['status']='INPUT_CHANGED_REVIEW_REQUIRED'
                    receipt['skillResourceAfterSha256']=capture_resources(script_dir)
                    if receipt['skillResourceAfterSha256']!=resources and receipt['status']=='NATIVE_EXIT_ZERO_REVIEW_REQUIRED':receipt['status']='SKILL_CHANGED_REVIEW_REQUIRED'
                    if working_source is not None:receipt['workingCopyAfterSha256']=capture_working_copy(working_source)
                except (OSError,ValueError) as error:
                    receipt['preservationCheckError']=str(error)
                    if receipt['status']=='NATIVE_EXIT_ZERO_REVIEW_REQUIRED':receipt['status']='INPUT_OR_SKILL_CHANGED_REVIEW_REQUIRED'
                write_receipt(target,receipt);reply=receipt
                if receipt['status']!='NATIVE_EXIT_ZERO_REVIEW_REQUIRED':print(json.dumps(reply,ensure_ascii=False));return 1
        print(json.dumps(reply,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,subprocess.SubprocessError,TypeError) as error:
        print(json.dumps({'error':str(error),'result':'failed','automaticReplay':False},ensure_ascii=False));return 1
