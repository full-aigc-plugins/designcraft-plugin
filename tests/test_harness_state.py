"""Harness 状态机验证持久化、恢复限制和完成证据门禁。"""
import importlib.util
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'skills/designcraft-harness/scripts/harness.py'

class HarnessStateContract(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('designcraft_harness',SOURCE)
        self.harness=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.harness)
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'user-data'
        self.store=self.harness.TaskStore(self.root)
        self.task=self.store.create('Create a handout','Only edit the copied project')

    def tearDown(self):self.temp.cleanup()

    def test_task_lifecycle_is_persisted_and_unknown_needs_reconciliation(self):
        task=self.task
        self.assertEqual(task['state'],'PREPARED')
        task=self.store.transition(task['taskId'],'EXECUTING',expected_revision=0)
        task=self.store.transition(task['taskId'],'RECONCILING',expected_revision=1)
        with self.assertRaisesRegex(ValueError,'invalid_state_transition'):
            self.store.transition(task['taskId'],'EXECUTING',expected_revision=2)
        self.assertEqual(self.store.get(task['taskId'])['state'],'RECONCILING')

    def test_completed_requires_current_hash_bound_acceptance_evidence(self):
        artifact_root,manifest,identity=self._artifact_fixture('PASS')
        task=self.task
        task=self.store.update(task['taskId'],{'candidateSha256':identity},expected_revision=0)
        for state in ('EXECUTING','VERIFYING','REVIEW_REQUIRED'):
            task=self.store.transition(task['taskId'],state,expected_revision=task['revision'])
        with self.assertRaisesRegex(ValueError,'required_acceptance_evidence_missing'):
            self.store.transition(task['taskId'],'COMPLETED',expected_revision=task['revision'])
        evidence_dir=self.root/task['taskId']/'evidence';evidence_dir.mkdir(parents=True)
        for kind in self.harness.REQUIRED_EVIDENCE:
            if kind=='AV-02':
                task=self.store.verify_artifact_manifest(task['taskId'],artifact_root,manifest,expected_revision=task['revision'])
                continue
            if kind=='AV-03':
                review=self._page_review_fixture(artifact_root,manifest)
                task=self.store.verify_page_review(task['taskId'],artifact_root,manifest,review,expected_revision=task['revision'])
                continue
            evidence=evidence_dir/(kind+'.json')
            evidence.write_text(json.dumps({'taskId':task['taskId'],'kind':kind,'status':'PASS','candidateSha256':identity}))
            task=self.store.attach_evidence(task['taskId'],evidence.name,expected_revision=task['revision'])
        task=self.store.transition(task['taskId'],'COMPLETED',expected_revision=task['revision'])
        self.assertEqual(task['state'],'COMPLETED')

    def test_stale_or_unbound_evidence_is_rejected(self):
        task=self.store.update(self.task['taskId'],{'candidateSha256':'b'*64},expected_revision=0)
        evidence_dir=self.root/task['taskId']/'evidence';evidence_dir.mkdir(parents=True)
        evidence=evidence_dir/'page-review.json'
        evidence.write_text(json.dumps({'taskId':task['taskId'],'kind':'AV-03','status':'PASS','candidateSha256':'c'*64}))
        with self.assertRaisesRegex(ValueError,'evidence_candidate_mismatch'):
            self.store.attach_evidence(task['taskId'],evidence.name,expected_revision=task['revision'])

    def _artifact_fixture(self,reopen_status='PASS'):
        root=Path(self.temp.name)/'deliverables';root.mkdir(exist_ok=True)
        project=root/'book.designcraft';project.write_bytes(b'editable project')
        digest=hashlib.sha256(project.read_bytes()).hexdigest()
        manifest={
            'schemaVersion':1,'runId':'12345678-1234-4234-8234-123456789abc','projectArtifactId':'project',
            'artifacts':[{'id':'project','kind':'project','path':'book.designcraft','format':'designcraft','byteCount':project.stat().st_size,'sha256':digest}],
            'expectations':{'pageCount':1,'pageDimensionsMm':[{'page':1,'width':210.0,'height':297.0}],'criticalText':['Title'],'linkedAssets':[]},
            'reopenCheck':{'status':'NOT_RUN','sessionId':None,'projectSha256':None,'pageCount':None,'pageDimensionsMm':[],'criticalText':[],'linkedAssets':[],'verifiedBy':None,'verifiedAt':None}
        }
        if reopen_status=='PASS':manifest['reopenCheck']={'status':'PASS','sessionId':'fresh-session','projectSha256':digest,'pageCount':1,'pageDimensionsMm':[{'page':1,'width':210.0,'height':297.0}],'criticalText':['Title'],'linkedAssets':[],'verifiedBy':'fixture-reviewer','verifiedAt':'2026-10-08T10:00:00Z'}
        path=root/'manifest.json';path.write_text(json.dumps(manifest))
        return root,path,digest

    def _page_review_fixture(self,root,manifest,conclusion='PASS'):
        preview=root/'page-1.png';preview.write_bytes(b'preview pixels')
        brief=root/'brief.md';brief.write_text('Single page with a readable title')
        digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        artifact=json.loads(manifest.read_text())
        review={
            'schemaVersion':1,'contractVersion':'designcraft-page-review/v1','runId':artifact['runId'],
            'projectSha256':artifact['reopenCheck']['projectSha256'],'artifactManifestSha256':digest(manifest),
            'rubricVersion':'designcraft-layout-rubric/v1','basis':{'type':'task-spec','path':brief.name,'sha256':digest(brief)},
            'reviewer':{'kind':'human','identity':'reviewer-01'},'reviewedAt':'2026-10-08T10:05:00Z',
            'pages':[{'page':1,'previewPath':preview.name,'previewSha256':digest(preview),'checks':[{'criterion':criterion,'status':'PASS','note':'verified'} for criterion in ('hierarchy','whitespace','alignment','readability','cropping','crossPageConsistency')]}],
            'conclusions':{name:{'status':conclusion if name=='visual' else 'PASS','note':'checked separately'} for name in ('structure','visual','output','editability')}
        }
        path=root/'page-review.json';path.write_text(json.dumps(review));return path

    def _verifying_task(self,candidate):
        task=self.store.update(self.task['taskId'],{'candidateSha256':candidate},expected_revision=0)
        task=self.store.transition(task['taskId'],'EXECUTING',expected_revision=task['revision'])
        return self.store.transition(task['taskId'],'VERIFYING',expected_revision=task['revision'])

    def test_artifact_manifest_requires_reopened_current_candidate_before_av02_attachment(self):
        root,manifest,candidate=self._artifact_fixture('PASS');task=self._verifying_task(candidate)
        task=self.store.verify_artifact_manifest(task['taskId'],root,manifest,expected_revision=task['revision'])
        self.assertEqual(len(task['evidenceRefs']),1)
        self.assertEqual(task['evidenceRefs'][0]['kind'],'AV-02')
        self.assertIn('AV-02',self.store._fresh_evidence(task))

    def test_artifact_manifest_not_run_never_becomes_av02_pass_evidence(self):
        root,manifest,candidate=self._artifact_fixture('NOT_RUN');task=self._verifying_task(candidate)
        with self.assertRaisesRegex(ValueError,'artifact_reopen_not_verified'):
            self.store.verify_artifact_manifest(task['taskId'],root,manifest,expected_revision=task['revision'])
        self.assertEqual(self.store.get(task['taskId'])['evidenceRefs'],[])

    def test_page_review_requires_verified_av02_and_binds_current_candidate_and_preview(self):
        root,manifest,candidate=self._artifact_fixture('PASS');task=self._verifying_task(candidate);review=self._page_review_fixture(root,manifest)
        with self.assertRaisesRegex(ValueError,'artifact_reopen_not_verified'):
            self.store.verify_page_review(task['taskId'],root,manifest,review,expected_revision=task['revision'])
        task=self.store.verify_artifact_manifest(task['taskId'],root,manifest,expected_revision=task['revision'])
        task=self.store.verify_page_review(task['taskId'],root,manifest,review,expected_revision=task['revision'])
        self.assertIn('AV-03',self.store._fresh_evidence(task))
        (root/'page-1.png').write_bytes(b'changed preview')
        self.assertNotIn('AV-03',self.store._fresh_evidence(self.store.get(task['taskId'])))

    def test_page_review_not_run_and_fail_are_rejected(self):
        root,manifest,candidate=self._artifact_fixture('NOT_RUN');task=self._verifying_task(candidate);review=self._page_review_fixture(root,manifest)
        with self.assertRaisesRegex(ValueError,'artifact_reopen_not_verified'):
            self.store.verify_page_review(task['taskId'],root,manifest,review,expected_revision=task['revision'])
        root,manifest,candidate=self._artifact_fixture('PASS')
        task=self.store.verify_artifact_manifest(task['taskId'],root,manifest,expected_revision=task['revision'])
        review=self._page_review_fixture(root,manifest,conclusion='FAIL')
        with self.assertRaisesRegex(ValueError,'page_review_not_pass'):
            self.store.verify_page_review(task['taskId'],root,manifest,review,expected_revision=task['revision'])

    def test_caller_cannot_attach_fake_av03_pass_json(self):
        task=self._verifying_task('a'*64);evidence_dir=self.root/task['taskId']/'evidence';evidence_dir.mkdir(parents=True)
        evidence=evidence_dir/'fake-av03.json';evidence.write_text(json.dumps({'taskId':task['taskId'],'kind':'AV-03','status':'PASS','candidateSha256':'a'*64}))
        with self.assertRaisesRegex(ValueError,'page_review_not_verified'):
            self.store.attach_evidence(task['taskId'],evidence.name,expected_revision=task['revision'])

    def test_readiness_is_read_only_and_does_not_install_missing_cli(self):
        runtime_home=Path(self.temp.name)/'missing-runtime-home'
        report=self.harness.readiness_report(runtime_home=runtime_home)
        self.assertTrue(report['readOnly'])
        self.assertFalse(report['dispatchPrerequisitesMet'])
        self.assertEqual(report['components']['runtime']['status'],'UNAVAILABLE')
        self.assertFalse(runtime_home.exists())

    def test_readiness_requires_current_version_bound_native_capability_evidence(self):
        lock=json.loads((ROOT/'skills/designcraft-use/scripts/runtime.lock.json').read_text())
        identity=lock['artifacts']['darwin-arm64']
        evidence=Path(self.temp.name)/'command-coverage.json'
        report_data={'schemaVersion':1,'domain':'designcraft','nativeCatalogStatus':'VERIFIED','nativeCatalogIdentity':{'cliVersion':lock['resolvedVersion'],'binarySha256':identity['binarySha256'],'catalogSha256':'c'*64},'nativeCommands':[{'id':'document.save','validationStatus':'NATIVE_TESTED'}]}
        evidence.write_text(json.dumps(report_data))
        with patch.object(self.harness.platform,'system',return_value='Darwin'),patch.object(self.harness.platform,'machine',return_value='arm64'):
            report=self.harness.readiness_report(runtime_home=Path(self.temp.name)/'missing-runtime',capability_evidence=evidence,required_commands=('document.save',))
        self.assertEqual(report['components']['requestCapability']['status'],'UNAVAILABLE')
        self.assertIn('evidence_not_in_plugin_evidence_root',report['components']['requestCapability']['reason'])
        report_data['nativeCatalogIdentity']['binarySha256']='0'*64;evidence.write_text(json.dumps(report_data))
        with patch.object(self.harness.platform,'system',return_value='Darwin'),patch.object(self.harness.platform,'machine',return_value='arm64'):
            report=self.harness.readiness_report(runtime_home=Path(self.temp.name)/'missing-runtime',capability_evidence=evidence,required_commands=('document.save',))
        self.assertEqual(report['components']['requestCapability']['status'],'UNAVAILABLE')

    def test_readiness_rejects_stale_manifest_bound_native_capability_evidence(self):
        root=Path(self.temp.name)/'capability-plugin'
        shutil.copytree(ROOT,root,ignore=shutil.ignore_patterns('openspec','__pycache__','.DS_Store'))
        evidence_dir=root/'evidence';evidence_dir.mkdir(exist_ok=True)
        evidence=evidence_dir/'native-capabilities.json'
        evidence.write_text(json.dumps({'schemaVersion':1,'domain':'designcraft','nativeCatalogStatus':'VERIFIED','nativeCatalogIdentity':{'cliVersion':'0.2.1','binarySha256':'a'*64,'catalogSha256':'b'*64},'nativeCommands':[{'id':'document.save','validationStatus':'NATIVE_TESTED'}]}))
        self._record_fixture_evidence(root,[('native-capabilities','native-capabilities','evidence/native-capabilities.json')])
        evidence.write_text(evidence.read_text()+'\n')
        with patch.object(self.harness,'PACKAGE_ROOT',root):
            report=self.harness.readiness_report(capability_evidence=evidence,required_commands=('document.save',))
        self.assertEqual(report['components']['requestCapability']['status'],'UNAVAILABLE')
        self.assertEqual(report['components']['requestCapability']['reason'],'capability_evidence_not_current')

    def test_readiness_is_ready_only_for_matching_snapshot_runtime_host_and_command(self):
        fixture=Path(self.temp.name)/'ready-plugin'
        shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__','.DS_Store'))
        lock_path=fixture/'skills/designcraft-use/scripts/runtime.lock.json';lock=json.loads(lock_path.read_text())
        binary=b'locked runtime fixture';binary_sha=hashlib.sha256(binary).hexdigest();lock['artifacts']['darwin-arm64']['binarySha256']=binary_sha
        external_names=json.loads((fixture/'candidate-source.json').read_text())['bundledSourceIdentity']['skills']
        for name in external_names:
            (fixture/'skills'/name/'scripts/runtime.lock.json').write_text(json.dumps(lock,indent=2)+'\n')
        source_path=fixture/'candidate-source.json';source=json.loads(source_path.read_text())
        source['skillFileSha256']={str(path.relative_to(fixture/'skills')):hashlib.sha256(path.read_bytes()).hexdigest() for name in sorted(external_names) for path in sorted((fixture/'skills'/name).rglob('*')) if path.is_file() and '__pycache__' not in path.parts and path.name!='.DS_Store' and path.suffix not in ('.pyc','.pyo')}
        source_path.write_text(json.dumps(source,indent=2)+'\n')
        status_path=fixture/'project-status.json';status=json.loads(status_path.read_text());status['hostDiscovery']='PASS';status['modelDispatch']='PASS';status_path.write_text(json.dumps(status,indent=2)+'\n')
        matrix_path=fixture/'support-matrix.json';matrix=json.loads(matrix_path.read_text());matrix['host']['discovery']='PASS';matrix['host']['modelDispatch']='PASS';matrix['host']['testedPlatforms']=['macOS arm64'];matrix_path.write_text(json.dumps(matrix,indent=2)+'\n')
        home=Path(self.temp.name)/'runtime-home';runtime=home/'designcraft/0.2.1';runtime.mkdir(parents=True);(runtime/'designcraft-cli').write_bytes(binary)
        expected=lock['artifacts']['darwin-arm64'];(runtime/'installation.json').write_text(json.dumps(dict(expected,name='designcraft',version='0.2.1')))
        evidence_dir=fixture/'evidence';evidence_dir.mkdir(exist_ok=True)
        evidence=evidence_dir/'native-capabilities.json';evidence.write_text(json.dumps({'schemaVersion':1,'domain':'designcraft','nativeCatalogStatus':'VERIFIED','nativeCatalogIdentity':{'cliVersion':'0.2.1','binarySha256':binary_sha,'catalogSha256':'d'*64},'nativeCommands':[{'id':'document.save','validationStatus':'NATIVE_TESTED'}]}))
        self._record_fixture_evidence(fixture,[('host','host','evidence/host-proof.json'),('model-dispatch','model-dispatch','evidence/model-proof.json'),('native-capabilities','native-capabilities','evidence/native-capabilities.json')])
        with patch.object(self.harness,'PACKAGE_ROOT',fixture),patch.object(self.harness.platform,'system',return_value='Darwin'),patch.object(self.harness.platform,'machine',return_value='arm64'):
            report=self.harness.readiness_report(home,evidence,('document.save',))
        self.assertEqual(report['status'],'READY',report)
        self.assertTrue(report['dispatchPrerequisitesMet'])
        self.assertTrue(report['userAuthorizationStillRequired'])

    @staticmethod
    def _record_fixture_evidence(root,records):
        freshness_spec=importlib.util.spec_from_file_location('fixture_evidence_freshness',root/'scripts/evidence_freshness.py')
        freshness=importlib.util.module_from_spec(freshness_spec);freshness_spec.loader.exec_module(freshness)
        from datetime import datetime,timezone
        import uuid
        manifest=json.loads((root/'evidence-manifest.json').read_text())
        retained=[item for item in manifest['records'] if item.get('id') not in {record_id for record_id,_,_ in records}]
        for record_id,layer,path in records:
            artifact=root/path
            if not artifact.exists():artifact.write_text(json.dumps({'fixture':record_id}))
            retained.append(freshness.create_record(root,record_id,layer,'PASS',str(uuid.uuid4()),datetime.now(timezone.utc).isoformat(),[],[path]))
        (root/'evidence-manifest.json').write_text(json.dumps({'schemaVersion':1,'records':retained},indent=2)+'\n')

    def test_native_dispatch_blocks_write_before_public_entry_when_readiness_is_incomplete(self):
        called=Path(self.temp.name)/'called'
        script=Path(self.temp.name)/'commands.py';script.write_text(f"from pathlib import Path\nPath({str(called)!r}).write_text('called')\n")
        self.harness.EXTERNAL_COMMANDS=script
        plan=Path(self.temp.name)/'plan.json';plan.write_text(json.dumps({'domain':'designcraft','steps':[{'command':'document.save','params':{}}]}))
        task=self.store.transition(self.task['taskId'],'EXECUTING',expected_revision=0)
        with self.assertRaisesRegex(ValueError,'readiness_gate_blocked'):
            self.store.dispatch_native(task['taskId'],['run',str(plan),'--output','out'],expected_revision=task['revision'])
        self.assertFalse(called.exists())
        current=self.store.get(task['taskId'])
        self.assertEqual((current['state'],current['nativeStatus']),('EXECUTING','NOT_RUN'))

    def test_artifact_manifest_for_different_candidate_cannot_attach_av02(self):
        root,manifest,_=self._artifact_fixture('PASS');task=self._verifying_task('b'*64)
        with self.assertRaisesRegex(ValueError,'artifact_candidate_mismatch'):
            self.store.verify_artifact_manifest(task['taskId'],root,manifest,expected_revision=task['revision'])
        self.assertEqual(self.store.get(task['taskId'])['evidenceRefs'],[])

    def test_caller_cannot_attach_unverified_av02_pass_json(self):
        task=self._verifying_task('a'*64);evidence_dir=self.root/task['taskId']/'evidence';evidence_dir.mkdir(parents=True)
        evidence=evidence_dir/'fake-av02.json';evidence.write_text(json.dumps({'taskId':task['taskId'],'kind':'AV-02','status':'PASS','candidateSha256':'a'*64}))
        with self.assertRaisesRegex(ValueError,'artifact_reopen_not_verified'):
            self.store.attach_evidence(task['taskId'],evidence.name,expected_revision=task['revision'])

    def test_optimistic_revision_prevents_stale_writers_and_corruption_is_preserved(self):
        task=self.store.update(self.task['taskId'],{'nextAction':'inspect'},expected_revision=0)
        with self.assertRaisesRegex(ValueError,'task_revision_conflict'):
            self.store.update(task['taskId'],{'nextAction':'overwrite'},expected_revision=0)
        state_path=self.root/task['taskId']/'task.json';state_path.write_text('{broken')
        with self.assertRaisesRegex(ValueError,'task_state_invalid'):
            self.store.get(task['taskId'])
        self.assertEqual(state_path.read_text(),'{broken')

    def test_concurrent_writers_cannot_overwrite_each_other(self):
        task=self.task
        def write(value):
            try:return self.store.update(task['taskId'],{'nextAction':value},expected_revision=0)['nextAction']
            except ValueError as error:return str(error)
        with ThreadPoolExecutor(max_workers=2) as workers:
            results=list(workers.map(write,('first','second')))
        self.assertEqual(sum(value=='task_revision_conflict' for value in results),1)
        self.assertEqual(self.store.get(task['taskId'])['revision'],1)

    def test_plugin_cache_cannot_be_used_as_writable_task_home(self):
        with self.assertRaisesRegex(ValueError,'task_home_inside_plugin_cache'):
            self.harness.TaskStore(ROOT)
        redirect=Path(self.temp.name)/'redirect';redirect.symlink_to(ROOT,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'task_home_inside_plugin_cache'):
            self.harness.TaskStore(redirect)

    def test_symlinked_task_state_is_rejected_without_reading_outside_root(self):
        outside=Path(self.temp.name)/'outside';outside.mkdir();(outside/'task.json').write_text('{}')
        identifier='00000000-0000-4000-8000-000000000001';task_dir=self.root/identifier;task_dir.symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'task_state_invalid'):
            self.store.get(identifier)

    def test_native_dispatch_uses_public_skill_entry_and_preserves_unknown_receipt(self):
        script=Path(self.temp.name)/'commands.py';run_id='12345678-1234-4234-8234-123456789abc'
        receipt={'schemaVersion':2,'status':'UNKNOWN','reason':'native_timeout','runId':run_id,'exitCode':1,'runtimeIdentity':{'verificationStatus':'LOCKED_EXPECTATION','version':'0.2.1'},'stepResultGranularity':'single-native-session','stepReferences':[{'stepRef':run_id+':step:0','index':0,'command':'document.save','paramsSha256':'a'*64}],'stepResults':[{'stepRef':run_id+':step:0','index':0,'command':'document.save','status':'UNKNOWN','granularity':'single-native-session'}]}
        script.write_text(f'''import json,sys\nprint(json.dumps({json.dumps(receipt)}))\nraise SystemExit(1)\n''')
        self.harness.EXTERNAL_COMMANDS=script
        plan=Path(self.temp.name)/'plan.json';plan.write_text(json.dumps({'domain':'designcraft','steps':[{'command':'document.save','params':{}}]}))
        task=self.store.transition(self.task['taskId'],'EXECUTING',expected_revision=0)
        with patch.object(self.harness,'readiness_report',return_value={'status':'READY'}):
            task=self.store.dispatch_native(task['taskId'],['run',str(plan),'--output','task-output'],expected_revision=task['revision'])
        self.assertEqual((task['nativeStatus'],task['runId'],task['nextAction']),('UNKNOWN',run_id,'reconcile_native_result'))
        self.assertTrue((self.root/task['taskId']/task['nativeReceiptRef']).is_file())
        saved=json.loads((self.root/task['taskId']/task['nativeReceiptRef']).read_text())['payload']
        self.assertEqual(saved['stepResults'],receipt['stepResults'])
        task=self.store.transition(task['taskId'],'RECONCILING',expected_revision=task['revision'])
        diagnostic=self.store.reconcile(task['taskId'])
        self.assertEqual(diagnostic['stepResults'],receipt['stepResults'])
        self.assertFalse(diagnostic['resumeAllowed'])
        with self.assertRaisesRegex(ValueError,'reconciliation_checkpoint_verification_required'):
            self.store.transition(task['taskId'],'PREPARED',expected_revision=task['revision'])
        with self.assertRaisesRegex(ValueError,'reconciliation_checkpoint_verification_required'):
            self.store.transition(task['taskId'],'PREPARED',expected_revision=task['revision'],updates={'reconciledRunId':run_id,'recoveryAction':'inspect saved project before continuing','recoveryEvidence':['native receipt reviewed']})
        self.assertEqual(self.store.get(task['taskId'])['state'],'RECONCILING')

    def test_revision_reuses_authorized_scope_and_tracks_only_affected_pages(self):
        task=self.store.create('Create a handout','Only change page 3 title and recheck that page')
        task=self.store.transition(task['taskId'],'EXECUTING',expected_revision=0)
        task=self.store.transition(task['taskId'],'VERIFYING',expected_revision=task['revision'])
        task=self.store.transition(task['taskId'],'REVISION_REQUIRED',expected_revision=task['revision'])
        with self.assertRaisesRegex(ValueError,'revision_scope_required'):
            self.store.transition(task['taskId'],'PREPARED',expected_revision=task['revision'],updates={'revisionScope':'Change page 3 title'})
        task=self.store.transition(task['taskId'],'PREPARED',expected_revision=task['revision'],updates={'revisionScope':'Change page 3 title','revisionPageRefs':['page-3'],'nextAction':'execute_scoped_revision'})
        status=self.harness.render_status(task)
        self.assertEqual(status['revisionScope'],'Change page 3 title')
        self.assertEqual(status['affectedPages'],['page-3'])
        self.assertEqual(status['next_action'],'execute_scoped_revision')
        self.assertEqual(task['state'],'PREPARED')

    def test_revision_outside_existing_authorization_stays_blocked(self):
        task=self.store.transition(self.task['taskId'],'EXECUTING',expected_revision=0)
        task=self.store.transition(task['taskId'],'VERIFYING',expected_revision=task['revision'])
        task=self.store.transition(task['taskId'],'REVISION_REQUIRED',expected_revision=task['revision'])
        with self.assertRaisesRegex(ValueError,'revision_scope_exceeds_authorization'):
            self.store.transition(task['taskId'],'PREPARED',expected_revision=task['revision'],updates={'revisionScope':'Rewrite all pages','revisionPageRefs':['page-1','page-2']})
        self.assertEqual(self.store.get(task['taskId'])['state'],'REVISION_REQUIRED')

    def test_each_revision_round_requires_fresh_scope_and_page_refs(self):
        task=self.store.create('Create a handout','Only change page 3 title and change page 4 caption')
        task=self.store.transition(task['taskId'],'EXECUTING',expected_revision=0)
        task=self.store.transition(task['taskId'],'VERIFYING',expected_revision=task['revision'])
        task=self.store.transition(task['taskId'],'REVISION_REQUIRED',expected_revision=task['revision'])
        task=self.store.transition(task['taskId'],'PREPARED',expected_revision=task['revision'],updates={'revisionScope':'Change page 3 title','revisionPageRefs':['page-3']})
        task=self.store.transition(task['taskId'],'EXECUTING',expected_revision=task['revision'])
        task=self.store.transition(task['taskId'],'VERIFYING',expected_revision=task['revision'])
        task=self.store.transition(task['taskId'],'REVISION_REQUIRED',expected_revision=task['revision'])
        self.assertIsNone(task['revisionScope'])
        self.assertEqual(task['revisionPageRefs'],[])
        with self.assertRaisesRegex(ValueError,'revision_scope_required'):
            self.store.transition(task['taskId'],'PREPARED',expected_revision=task['revision'])
        task=self.store.transition(task['taskId'],'PREPARED',expected_revision=task['revision'],updates={'revisionScope':'Change page 4 caption','revisionPageRefs':['page-4']})
        self.assertEqual(task['revisionPageRefs'],['page-4'])

    def test_revision_must_record_a_scope_before_restart(self):
        task=self.store.create('Create a handout','Only adjust the heading on page three')
        task=self.store.transition(task['taskId'],'EXECUTING',expected_revision=0)
        task=self.store.transition(task['taskId'],'VERIFYING',expected_revision=task['revision'])
        task=self.store.transition(task['taskId'],'REVISION_REQUIRED',expected_revision=task['revision'])
        with self.assertRaisesRegex(ValueError,'revision_scope_required'):
            self.store.transition(task['taskId'],'PREPARED',expected_revision=task['revision'])
        task=self.store.transition(task['taskId'],'PREPARED',expected_revision=task['revision'],updates={'revisionScope':'only adjust the heading on page three','revisionPageRefs':['page-3']})
        self.assertEqual(task['revisionScope'],'only adjust the heading on page three')

    def test_unknown_receipt_version_is_not_interpreted_as_success(self):
        script=Path(self.temp.name)/'commands-legacy.py'
        script.write_text('''import json\nprint(json.dumps({"schemaVersion":99,"status":"NATIVE_EXIT_ZERO_REVIEW_REQUIRED","runId":"12345678-1234-4234-8234-123456789abc","exitCode":0}))\n''')
        self.harness.EXTERNAL_COMMANDS=script
        plan=Path(self.temp.name)/'plan.json';plan.write_text(json.dumps({'domain':'designcraft','steps':[{'command':'document.save','params':{}}]}))
        task=self.store.transition(self.task['taskId'],'EXECUTING',expected_revision=0)
        with patch.object(self.harness,'readiness_report',return_value={'status':'READY'}):
            task=self.store.dispatch_native(task['taskId'],['run',str(plan)],expected_revision=task['revision'])
        self.assertEqual((task['nativeStatus'],task['runId'],task['nextAction']),('UNKNOWN',None,'reconcile_native_result'))

    def _unknown_reconciling_task(self):
        script=Path(self.temp.name)/'commands-reconcile.py';run_id='12345678-1234-4234-8234-123456789abc'
        script.write_text(f'''import json,sys\nprint(json.dumps({{"schemaVersion":2,"status":"UNKNOWN","reason":"native_timeout","runId":"{run_id}","exitCode":1,"terminationVerified":False,"descendantsTerminationVerified":False}}))\nraise SystemExit(1)\n''')
        self.harness.EXTERNAL_COMMANDS=script
        plan=Path(self.temp.name)/'plan.json';plan.write_text(json.dumps({'domain':'designcraft','steps':[{'command':'document.save','params':{}}]}))
        task=self.store.transition(self.task['taskId'],'EXECUTING',expected_revision=0)
        with patch.object(self.harness,'readiness_report',return_value={'status':'READY'}):
            task=self.store.dispatch_native(task['taskId'],['run',str(plan)],expected_revision=task['revision'])
        return self.store.transition(task['taskId'],'RECONCILING',expected_revision=task['revision'])

    def test_reconciliation_rereads_matching_receipt_and_never_resumes_without_checkpoints(self):
        task=self._unknown_reconciling_task()
        before=(self.root/task['taskId']/'task.json').read_bytes()
        result=self.store.reconcile(task['taskId'])
        after=(self.root/task['taskId']/'task.json').read_bytes()
        self.assertEqual(result['status'],'UNKNOWN')
        self.assertEqual(result['runId'],task['runId'])
        self.assertEqual(result['receiptIdentity'],'MATCHED')
        self.assertFalse(result['resumeAllowed'])
        self.assertIn('source_checkpoint_contract_unavailable',result['blockers'])
        self.assertEqual(before,after)

    def test_reconciliation_reports_receipt_run_id_mismatch_without_mutating_task(self):
        task=self._unknown_reconciling_task()
        path=self.root/task['taskId']/task['nativeReceiptRef']
        wrapper=json.loads(path.read_text());wrapper['payload']['runId']='00000000-0000-4000-8000-000000000000';path.write_text(json.dumps(wrapper))
        result=self.store.reconcile(task['taskId'])
        self.assertEqual(result['receiptIdentity'],'MISMATCH')
        self.assertFalse(result['resumeAllowed'])
        self.assertIn('receipt_run_id_mismatch',result['blockers'])
        self.assertEqual(self.store.get(task['taskId'])['state'],'RECONCILING')

    def test_arbitrary_recovery_text_cannot_release_unknown_execution(self):
        task=self._unknown_reconciling_task()
        with self.assertRaisesRegex(ValueError,'reconciliation_checkpoint_verification_required'):
            self.store.transition(task['taskId'],'PREPARED',expected_revision=task['revision'],updates={'reconciledRunId':task['runId'],'recoveryAction':'continue','recoveryEvidence':['I looked at it']})

    def test_status_output_exposes_required_harness_fields(self):
        result=self.harness.render_status(self.task)
        self.assertTrue({'status','scope','actions','evidence','artifacts','skipped','risks','next_action'}.issubset(result))

    def test_isolated_harness_runs_from_read_only_cache_without_source_checkout(self):
        with tempfile.TemporaryDirectory(prefix='插件 缓存 ') as t:
            root=Path(t);cache=root/'插件 缓存';skill=cache/'skills/designcraft-harness'
            shutil.copytree(ROOT/'skills',cache/'skills')
            script=skill/'scripts/harness.py';script.chmod(0o444);skill.chmod(0o555);skill.parent.chmod(0o555);cache.chmod(0o555)
            task_home=root/'用户 数据'/'tasks';empty_cwd=root/'无源工作区';empty_cwd.mkdir()
            create=subprocess.run([sys.executable,'-I','-B',str(script),'--task-home',str(task_home),'new','--goal','offline task','--scope','test copied project'],cwd=empty_cwd,capture_output=True,text=True)
            self.assertEqual(create.returncode,0,create.stdout+create.stderr)
            task=json.loads(create.stdout);self.assertEqual(task['status'],'PREPARED')
            self.assertFalse((cache/'tasks').exists())
            show=subprocess.run([sys.executable,'-I','-B',str(script),'--task-home',str(task_home),'show',task['taskId']],cwd=empty_cwd,capture_output=True,text=True)
            self.assertEqual(show.returncode,0,show.stdout+show.stderr)
            self.assertEqual(json.loads(show.stdout)['taskId'],task['taskId'])
            catalog=root/'原生命令目录.json';catalog.write_text(json.dumps([{'id':'file.new','label':'New','params':'','menu':['File']}]))
            plan=root/'计划.json';plan.write_text(json.dumps({'domain':'designcraft','steps':[{'command':'file.new','params':{}}]}))
            entry=cache/'skills/designcraft-use/scripts/commands.py'
            for action,args in (('list',[]),('describe',['file.new']),('check',[str(plan)])):
                result=subprocess.run([sys.executable,'-I','-B',str(entry),action,*args,'--catalog',str(catalog)],cwd=empty_cwd,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertFalse((cache/'tasks').exists())

if __name__=='__main__':unittest.main()
