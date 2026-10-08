"""校验插件候选的自包含技能快照；不声明来源已发布。"""
from pathlib import Path
from pathlib import PurePosixPath
import hashlib
import importlib.util
import json
import re
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[1]
SEMVER=re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?')
INTERFACE_FIELDS={'displayName','shortDescription','longDescription','developerName','category','capabilities','websiteURL','privacyPolicyURL','termsOfServiceURL','defaultPrompt','brandColor','composerIcon','logo','logoDark','screenshots'}

def validate_image_resource(value):
    if not isinstance(value,str) or not value.startswith('./assets/') or '\\' in value:
        raise ValueError('plugin_resource_invalid')
    relative=Path(value[2:])
    if relative.is_absolute() or any(part in ('..','.') for part in relative.parts):
        raise ValueError('plugin_resource_invalid')
    path=ROOT/relative
    if not path.is_file() or path.is_symlink() or path.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):
        raise ValueError('plugin_resource_invalid')
    header=path.read_bytes()[:12]
    valid=(path.suffix.lower()=='.png' and header.startswith(b'\x89PNG\r\n\x1a\n')) or (path.suffix.lower() in ('.jpg','.jpeg') and header.startswith(b'\xff\xd8\xff')) or (path.suffix.lower()=='.webp' and header.startswith(b'RIFF') and header[8:12]==b'WEBP')
    if not valid:raise ValueError('plugin_resource_invalid')

def validate_interface(interface):
    if not isinstance(interface,dict) or set(interface)-INTERFACE_FIELDS:
        raise ValueError('plugin_interface_invalid')
    for field in ('displayName','shortDescription','longDescription','developerName','category','websiteURL','privacyPolicyURL','termsOfServiceURL','brandColor'):
        if field in interface and (not isinstance(interface[field],str) or not interface[field]):
            raise ValueError('plugin_interface_invalid')
    for field in ('capabilities','defaultPrompt'):
        if field in interface and (not isinstance(interface[field],list) or not interface[field] or any(not isinstance(item,str) or not item for item in interface[field])):
            raise ValueError('plugin_interface_invalid')
    if 'brandColor' in interface and not re.fullmatch(r'#[0-9a-fA-F]{6}',interface['brandColor']):
        raise ValueError('plugin_interface_invalid')
    for field in ('composerIcon','logo','logoDark'):
        if field in interface:
            validate_image_resource(interface[field])
    if 'screenshots' in interface:
        if not isinstance(interface['screenshots'],list):raise ValueError('plugin_interface_invalid')
        for resource in interface['screenshots']:validate_image_resource(resource)

def validate_openai_extension(extension):
    if not isinstance(extension,dict) or set(extension)-{'interface','onboardingSkill'}:
        raise ValueError('plugin_extension_not_implemented')
    if 'interface' in extension:validate_interface(extension['interface'])
    if 'onboardingSkill' in extension:
        value=extension['onboardingSkill']
        if not isinstance(value,str) or not value.startswith('./skills/') or not value.endswith('/SKILL.md') or '..' in Path(value).parts:
            raise ValueError('plugin_resource_invalid')
        path=ROOT/value[2:]
        if not path.is_file() or path.is_symlink():raise ValueError('plugin_resource_invalid')

def validate_host_manifest(manifest):
    path=ROOT/'.codex-plugin/plugin.json'
    if path.is_symlink():raise ValueError('plugin_host_manifest_invalid')
    if not path.exists():return None
    if not path.is_file():raise ValueError('plugin_host_manifest_invalid')
    host=json.loads(path.read_text(encoding='utf-8'))
    allowed={'name','version','description','author','homepage','repository','license','keywords','skills','interface'}
    if not isinstance(host,dict) or set(host)-allowed or host.get('name')!=manifest.get('name'):
        raise ValueError('plugin_host_manifest_invalid')
    if host.get('version')!=manifest.get('version'):
        raise ValueError('plugin_host_manifest_version_mismatch')
    for field in ('description','homepage','repository','license'):
        if field in host and host[field]!=manifest.get(field):raise ValueError('plugin_host_manifest_identity_mismatch')
    if 'skills' in host and host['skills']!='./skills/':raise ValueError('plugin_host_manifest_component_mismatch')
    if 'interface' in host:validate_interface(host['interface'])
    return host

def validate_local_skill_references(skill_root):
    root=skill_root.resolve()
    for document in skill_root.rglob('*.md'):
        if document.is_symlink():raise ValueError('plugin_local_skill_reference_invalid')
        content=document.read_text(encoding='utf-8')
        for match in re.finditer(r'\[[^\]]*\]\(([^)]+)\)',content):
            target=match.group(1).strip()
            if target.startswith(('https://','http://','mailto:','#')):continue
            relative=unquote(target.split('#',1)[0].split('?',1)[0])
            if not relative:continue
            linked=(document.parent/relative).resolve()
            try:linked.relative_to(root)
            except ValueError as error:raise ValueError('plugin_local_skill_reference_invalid') from error
            if not linked.is_file():raise ValueError('plugin_local_skill_reference_invalid')

def transient_path(path):
    value=Path(path)
    return '__pycache__' in value.parts or value.name=='.DS_Store' or value.suffix in ('.pyc','.pyo')

def validate_host_platform_evidence(matrix):
    host=matrix.get('host',{})
    if host.get('discovery')!='PASS' and host.get('modelDispatch')!='PASS':
        return
    manifest=json.loads((ROOT/'evidence-manifest.json').read_text(encoding='utf-8'))
    records={item.get('id'):item for item in manifest.get('records',[]) if isinstance(item,dict)}
    host_record=records.get('host')
    if not isinstance(host_record,dict) or host_record.get('status')!='PASS':
        raise ValueError('host_evidence_status_mismatch')
    artifacts=host_record.get('artifacts',[])
    host_artifact=next((item.get('path') for item in artifacts if isinstance(item,dict) and isinstance(item.get('path'),str)),None)
    if not host_artifact:
        raise ValueError('host_evidence_report_missing')
    relative=PurePosixPath(host_artifact)
    if relative.is_absolute() or not relative.parts or '..' in relative.parts or '\\' in host_artifact:
        raise ValueError('host_evidence_report_path_invalid')
    report_path=ROOT.joinpath(*relative.parts)
    current=ROOT
    for part in relative.parts:
        current=current/part
        if current.is_symlink():
            raise ValueError('host_evidence_report_path_invalid')
    try:
        report_path.resolve().relative_to(ROOT.resolve())
    except ValueError as error:
        raise ValueError('host_evidence_report_path_invalid') from error
    if not report_path.is_file():
        raise ValueError('host_evidence_report_missing')
    report=json.loads(report_path.read_text(encoding='utf-8'))
    if report.get('testedPlatforms')!=host.get('testedPlatforms'):
        raise ValueError('host_evidence_platform_mismatch')
    freshness_path=Path(__file__).with_name('evidence_freshness.py')
    spec=importlib.util.spec_from_file_location('designcraft_evidence_freshness',freshness_path)
    freshness=importlib.util.module_from_spec(spec);spec.loader.exec_module(freshness)
    statuses=freshness.evaluate_manifest(ROOT,manifest)
    if statuses.get('host')!='PASS' or (host.get('modelDispatch')=='PASS' and statuses.get('model-dispatch')!='PASS'):
        raise ValueError('host_evidence_stale')

def validate_invocation_policy(skill, implicit):
    """校验本包维护的最小 Codex 策略格式，不将其当作通用 YAML 解析器。"""
    path=skill/'agents/openai.yaml'
    expected='policy:\n  allow_implicit_invocation: '+('true' if implicit else 'false')
    if path.is_symlink() or not path.is_file() or path.read_text(encoding='utf-8').strip()!=expected:
        raise ValueError('skill_invocation_policy_invalid:'+skill.name)

def validate():
    manifest=json.loads((ROOT/'plugin.json').read_text())
    if manifest['$schema']!='https://agent-plugins.org/schemas/1.0.0/plugin.schema.json':raise ValueError('unsupported_plugin_schema')
    allowed={'$schema','name','version','description','author','homepage','repository','license','keywords','extensions'}
    if set(manifest)-allowed or not isinstance(manifest.get('name'),str) or not re.fullmatch(r'(?=.{1,64}$)(?!.*--)(?!.*\.\.)(?:[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?)',manifest['name']):raise ValueError('plugin_manifest_invalid')
    for key in ('version','description','homepage','repository','license'):
        if key in manifest and not isinstance(manifest[key],str):raise ValueError('plugin_manifest_invalid')
    if not isinstance(manifest.get('version'),str) or not SEMVER.fullmatch(manifest['version']):raise ValueError('plugin_manifest_invalid')
    if 'keywords' in manifest and (not isinstance(manifest['keywords'],list) or any(not isinstance(item,str) for item in manifest['keywords'])):raise ValueError('plugin_manifest_invalid')
    extensions=manifest.get('extensions',{})
    if not isinstance(extensions,dict):raise ValueError('plugin_manifest_invalid')
    if set(extensions)-{'com.openai'}:raise ValueError('plugin_extension_not_implemented')
    if 'com.openai' in extensions:validate_openai_extension(extensions['com.openai'])
    host_manifest=validate_host_manifest(manifest)
    if not extensions and host_manifest and 'interface' in host_manifest:validate_interface(host_manifest['interface'])
    status=json.loads((ROOT/'project-status.json').read_text());matrix=json.loads((ROOT/'support-matrix.json').read_text())
    if matrix.get('schemaVersion')!=1 or matrix.get('packageVersion')!=manifest.get('version') or not isinstance(matrix.get('offline'),dict) or matrix['offline'].get('status') not in ('PASS','FAIL','NOT_RUN') or not matrix['offline'].get('os') or not matrix['offline'].get('python') or not matrix['offline'].get('tests') or not matrix['offline'].get('packageValidation'):
        raise ValueError('support_matrix_invalid')
    if matrix.get('ci',{}).get('status') not in ('PASS','FAIL','NOT_RUN') or matrix.get('nativeRuntime',{}).get('status')!=status.get('nativeInstallation') or matrix.get('host',{}).get('discovery')!=status.get('hostDiscovery') or matrix.get('host',{}).get('modelDispatch')!=status.get('modelDispatch') or matrix.get('creativeAcceptance')!=status.get('creativeAcceptance') or (matrix.get('host',{}).get('discovery')=='NOT_RUN' and matrix.get('host',{}).get('testedPlatforms')!=[]) or matrix.get('release')!=('PUBLISHED' if status.get('published') else 'UNPUBLISHED'):
        raise ValueError('support_matrix_status_mismatch')
    if not isinstance(matrix.get('authorization'),str) or not matrix['authorization']:
        raise ValueError('support_matrix_authorization_missing')
    future=matrix.get('futureScope')
    if not isinstance(future,list) or not all(isinstance(item,str) and item for item in future) or not any('Additional hosts' in item for item in future) or not any('Automatic multi-round' in item for item in future) or not any('ArtCraft' in item for item in future):
        raise ValueError('support_matrix_future_scope_missing')
    provenance=json.loads((ROOT/'candidate-source.json').read_text())
    if type(provenance.get('schemaVersion')) is not int or provenance['schemaVersion']!=1 or provenance.get('candidateType')!='local-unpublished-candidate':raise ValueError('unsupported_candidate_schema')
    identity=provenance.get('bundledSourceIdentity')
    if not isinstance(identity,dict) or provenance.get('sourceProject')!='designcraft-skills' or identity.get('sourceProject')!='designcraft-skills' or provenance.get('sourceVersion')!=identity.get('sourceVersion') or not isinstance(provenance.get('sourceVersion'),str) or provenance.get('sourceStatus')!='local-unpublished-candidate' or provenance.get('releaseTag') is not None or identity.get('releaseTag') is not None:
        raise ValueError('candidate_source_identity_mismatch')
    if not isinstance(identity.get('skills'),list) or any(not isinstance(name,str) for name in identity['skills']) or len(set(identity['skills']))!=len(identity['skills']):raise ValueError('candidate_source_skills_invalid')
    if not isinstance(provenance.get('skillFileSha256'),dict) or any(not isinstance(path,str) or not re.fullmatch('[0-9a-f]{64}',digest) for path,digest in provenance['skillFileSha256'].items()):raise ValueError('candidate_snapshot_hash_invalid')
    if any(p.is_symlink() for p in (ROOT/'skills').rglob('*')):raise ValueError('snapshot_symlink')
    external_names=set(provenance['bundledSourceIdentity']['skills'])
    local=json.loads((ROOT/'plugin-local-skills.json').read_text())
    local_names=[item.get('name') for item in local.get('skills',[]) if isinstance(item,dict)]
    if local.get('schemaVersion')!=1 or len(local_names)!=len(local.get('skills',[])) or len(set(local_names))!=len(local_names) or external_names.intersection(local_names):raise ValueError('local_skill_manifest_invalid')
    actual={p.name for p in (ROOT/'skills').iterdir() if p.is_dir()}
    if actual!=external_names|set(local_names) or any(not n.startswith(manifest['name']+'-') for n in external_names) or set(local_names)!={'designcraft-harness'}:raise ValueError('skill_set_mismatch')
    files={str(p.relative_to(ROOT/'skills')):hashlib.sha256(p.read_bytes()).hexdigest() for name in sorted(external_names) for p in sorted((ROOT/'skills'/name).rglob('*')) if p.is_file() and not transient_path(p.relative_to(ROOT/'skills'))}
    if files!=provenance['skillFileSha256']:raise ValueError('snapshot_drift')
    for name in sorted(external_names):
        validate_invocation_policy(ROOT/'skills'/name,name=='designcraft-use')
        if (ROOT/'skills'/name/'SKILL.md').stat().st_size>7500:raise ValueError('skill_host_byte_budget_exceeded:'+name)
    for item in local['skills']:
        if item.get('path')!=f"skills/{item.get('name')}":raise ValueError('local_skill_path_invalid')
        skill=ROOT/item['path'];text=(skill/'SKILL.md').read_text(encoding='utf-8')
        if item.get('owner')!='designcraft-plugin' or item.get('kind')!='plugin-local' or not text.startswith('---\n') or f"name: {item['name']}\n" not in text or 'description:' not in text:raise ValueError('local_skill_invalid')
        if len(text.encode('utf-8'))>7500:raise ValueError('skill_host_byte_budget_exceeded:'+item['name'])
        validate_local_skill_references(skill)
        validate_invocation_policy(skill,False)
    validate_host_platform_evidence(matrix)
    return {'plugin':manifest['name'],'skills':len(actual),'externalSkills':len(external_names),'localSkills':len(local_names),'snapshot':'PASS','hostManifest':'PASS' if host_manifest else 'NOT_PRESENT','sourceRelease':'UNPUBLISHED','hostAcceptance':'NOT_RUN'}

if __name__=='__main__':print(json.dumps(validate(),ensure_ascii=False))
