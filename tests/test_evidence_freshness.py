"""Layered delivery evidence becomes stale when any bound identity changes."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('evidence_freshness',ROOT/'scripts/evidence_freshness.py')
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class EvidenceFreshness(unittest.TestCase):
    def fixture(self,root):
        (root/'skills/demo/scripts').mkdir(parents=True)
        (root/'scripts').mkdir()
        (root/'tests').mkdir()
        (root/'evidence').mkdir()
        (root/'.github/workflows').mkdir(parents=True)
        (root/'.github/workflows/ci.yml').write_text('matrix: [3.11, 3.12, 3.13]')
        (root/'plugin.json').write_text(json.dumps({'version':'0.1.0'}))
        (root/'project-status.json').write_text(json.dumps({'offlineTests':'PASS','packageValidation':'PASS','ci':'NOT_RUN','nativeInstallation':'NOT_RUN','targetPlatformAcceptance':'NOT_RUN','hostDiscovery':'NOT_RUN','modelDispatch':'NOT_RUN','creativeAcceptance':'NOT_RUN','published':False}))
        (root/'support-matrix.json').write_text(json.dumps({'offline':{'status':'PASS'},'ci':{'status':'NOT_RUN'},'nativeRuntime':{'status':'NOT_RUN'},'host':{'discovery':'NOT_RUN','modelDispatch':'NOT_RUN'},'creativeAcceptance':'NOT_RUN','release':'UNPUBLISHED'}))
        (root/'scripts/plugin.py').write_text('plugin source')
        (root/'candidate-source.json').write_text(json.dumps({'sourceVersion':'0.2.1'}))
        (root/'skills/demo/scripts/runtime.lock.json').write_text(json.dumps({'artifact':'designcraft-cli','resolvedVersion':'0.2.1','artifacts':{'darwin-arm64':{'binarySha256':'a'*64}}}))
        (root/'tests/input.py').write_text('test input')
        (root/'evidence/report.json').write_text('{"status":"PASS"}')

    def manifest(self,root):
        record=MODULE.create_record(root,record_id='offline',layer='offline',status='PASS',run_id=str(uuid.uuid4()),observed_at='2026-10-08T00:00:00Z',input_paths=['tests/input.py'],artifact_paths=['evidence/report.json'],environment={'os':'macOS','python':'3.14.3'})
        return {'schemaVersion':1,'records':[record,{'id':'native','layer':'native','status':'NOT_RUN'}]}

    def test_current_evidence_passes_and_unrun_layers_stay_unrun(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            manifest=self.manifest(root)
            result=MODULE.evaluate_manifest(root,manifest,environment={'os':'macOS','python':'3.14.3'})
            self.assertEqual(result,{'offline':'PASS','native':'NOT_RUN'})

    def test_source_lock_runtime_input_artifact_and_environment_changes_stale_evidence(self):
        mutations=(
            ('scripts/plugin.py','plugin source'),
            ('candidate-source.json','source lock'),
            ('skills/demo/scripts/runtime.lock.json','runtime lock'),
            ('tests/input.py','input'),
            ('evidence/report.json','artifact'),
        )
        for relative,label in mutations:
            with self.subTest(subject=label),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);self.fixture(root);manifest=self.manifest(root)
                path=root/relative;path.write_text(path.read_text()+' drift')
                result=MODULE.evaluate_manifest(root,manifest,environment={'os':'macOS','python':'3.14.3'})
                self.assertEqual(result['offline'],'STALE')
                self.assertEqual(result['native'],'NOT_RUN')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root);manifest=self.manifest(root)
            result=MODULE.evaluate_manifest(root,manifest,environment={'os':'Windows','python':'3.14.3'})
            self.assertEqual(result['offline'],'STALE')

    def test_layer_statuses_must_match_project_and_support_matrix(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            statuses={'offline-tests':'PASS','package-validation':'PASS','native-runtime':'NOT_RUN','ci':'NOT_RUN','host':'NOT_RUN','target-platform':'NOT_RUN','model-dispatch':'NOT_RUN','creative':'NOT_RUN','release':'NOT_RUN'}
            self.assertEqual(MODULE.status_mismatches(root,statuses),[])
            status_path=root/'project-status.json';project=json.loads(status_path.read_text());project['hostDiscovery']='PASS';status_path.write_text(json.dumps(project))
            self.assertIn('host.project-status.json',MODULE.status_mismatches(root,statuses))

    def test_external_ci_environment_is_verified_from_bound_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            execution_environment={'provider':'github-actions','runner':'ubuntu-latest','pythonVersions':['3.11','3.12','3.13']}
            (root/'evidence/report.json').write_text(json.dumps({'status':'success','executionEnvironment':execution_environment}))
            record=MODULE.create_record(root,'ci','ci','PASS',str(uuid.uuid4()),'2026-10-08T00:00:00Z',['.github/workflows/ci.yml'],['evidence/report.json'],execution_environment)
            record['environmentSource']='artifact'
            record['environmentArtifactPath']='evidence/report.json'
            result=MODULE.evaluate_manifest(root,{'schemaVersion':1,'records':[record]})
            self.assertEqual(result,{'ci':'PASS'})

    def test_external_environment_must_match_a_hashed_manifest_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            execution_environment={'provider':'github-actions','runner':'ubuntu-latest','pythonVersions':['3.11','3.12','3.13']}
            (root/'evidence/report.json').write_text(json.dumps({'status':'success','executionEnvironment':execution_environment}))
            record=MODULE.create_record(root,'ci','ci','PASS',str(uuid.uuid4()),'2026-10-08T00:00:00Z',['.github/workflows/ci.yml'],['evidence/report.json'],execution_environment)
            record['environmentSource']='artifact'
            record['environmentArtifactPath']='evidence/report.json'
            record['artifacts']=[]
            result=MODULE.evaluate_manifest(root,{'schemaVersion':1,'records':[record]})
            self.assertEqual(result,{'ci':'STALE'})

if __name__=='__main__':unittest.main()
