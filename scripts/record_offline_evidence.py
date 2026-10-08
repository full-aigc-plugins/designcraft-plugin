"""Run the plugin's offline checks and atomically refresh their bound evidence."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from evidence_freshness import create_record, current_environment

def atomic_json(path,value):
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,prefix='.evidence-',delete=False) as stream:
            temporary=Path(stream.name)
            json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary is not None and temporary.exists():temporary.unlink()

def run(command):
    return subprocess.run(command,cwd=ROOT,capture_output=True,text=True)

def main():
    run_id=str(uuid.uuid4())
    observed_at=datetime.now(timezone.utc).isoformat()
    commands=[
        [sys.executable,'-I','-B','-m','unittest','discover','-s','tests','-v'],
        [sys.executable,'-I','-B','scripts/validate_package.py'],
    ]
    results=[run(command) for command in commands]
    report={'schemaVersion':1,'runId':run_id,'observedAt':observed_at,'environment':current_environment(),'checks':[{'command':[Path(command[0]).name,*command[1:]],'exitCode':result.returncode,'stdout':result.stdout,'stderr':result.stderr} for command,result in zip(commands,results)]}
    artifact=ROOT/'evidence/current-offline-validation.json'
    artifact.parent.mkdir(parents=True,exist_ok=True)
    atomic_json(artifact,report)
    status='PASS' if all(result.returncode==0 for result in results) else 'FAIL'
    manifest_path=ROOT/'evidence-manifest.json'
    try:manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    except FileNotFoundError:manifest={'schemaVersion':1,'records':[]}
    if manifest.get('schemaVersion')!=1 or not isinstance(manifest.get('records'),list):raise ValueError('evidence_manifest_invalid')
    refreshed={'offline-tests','package-validation'}
    records=[item for item in manifest['records'] if isinstance(item,dict) and item.get('id') not in refreshed]
    inputs=sorted(path.relative_to(ROOT).as_posix() for path in (ROOT/'tests').rglob('*.py'))
    records.extend([
        create_record(ROOT,'offline-tests','offline-tests',status,run_id,observed_at,inputs,['evidence/current-offline-validation.json'],report['environment']),
        create_record(ROOT,'package-validation','package-validation',status,run_id,observed_at,['scripts/validate_package.py','plugin.json','candidate-source.json','support-matrix.json'],['evidence/current-offline-validation.json'],report['environment']),
    ])
    existing={item.get('id') for item in records if isinstance(item,dict)}
    for record_id,layer in (('native-runtime','native'),('ci','ci'),('host','host'),('target-platform','target-platform'),('model-dispatch','model-dispatch'),('creative','creative'),('release','release')):
        if record_id not in existing:records.append({'id':record_id,'layer':layer,'status':'NOT_RUN'})
    atomic_json(manifest_path,{'schemaVersion':1,'records':records})
    print(json.dumps({'runId':run_id,'status':status,'checks':[result.returncode for result in results],'manifest':str(manifest_path)},ensure_ascii=False))
    return 0 if status=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
