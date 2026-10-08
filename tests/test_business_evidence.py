"""插件通过源端公开校验器登记 AV-01，并在原始结果改变时失效。"""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('business_harness',ROOT/'skills/designcraft-harness/scripts/harness.py')
HARNESS=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(HARNESS)

class BusinessEvidenceIntegration(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.store=HARNESS.TaskStore(self.root/'tasks')

    def tearDown(self):self.temp.cleanup()

    def fixture(self):
        root=self.root/'deliverables';root.mkdir()
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        project=root/'book.designcraft';project.write_bytes(b'editable project')
        pdf=root/'book.pdf';pdf.write_bytes(b'pdf export')
        run=str(uuid.uuid4());candidate=sha(project);dims=[{'page':1,'width':210,'height':297}]
        manifest={'schemaVersion':1,'runId':str(uuid.uuid4()),'projectArtifactId':'project',
            'artifacts':[{'id':i,'kind':kind,'path':p.name,'format':fmt,'byteCount':p.stat().st_size,'sha256':sha(p)} for i,kind,p,fmt in [('project','project',project,'designcraft'),('pdf','export',pdf,'pdf')]],
            'expectations':{'pageCount':1,'pageDimensionsMm':dims,'criticalText':['Title'],'linkedAssets':[]},
            'reopenCheck':{'status':'PASS','sessionId':run,'projectSha256':candidate,'pageCount':1,'pageDimensionsMm':dims,'criticalText':['Title'],'linkedAssets':[],'verifiedBy':'fixture','verifiedAt':'2026-10-08T00:00:00Z'}}
        mp=root/'manifest.json';mp.write_text(json.dumps(manifest))
        refs=[{'index':i,'stepRef':f'{run}:step:{i}','command':command,'paramsSha256':'a'*64} for i,command in enumerate(('preflight.run','file.exportPdf'))]
        raw={'completed':2,'results':[{'errors':0,'warnings':0,'issues':[]},{'path':'/tmp/native.pdf','bytes':pdf.stat().st_size,'pages':1,'warnings':[]}]}
        scripts=ROOT/'skills/designcraft-cli-export/scripts';lock=json.loads((scripts/'runtime.lock.json').read_text());lock_sha=sha(scripts/'runtime.lock.json')
        assessment={'contractVersion':'designcraft-business-assessment/v1','status':'PASS','steps':[{'index':i,'stepRef':ref['stepRef'],'command':ref['command'],'status':'PASS','reason':'preflight_clean' if i==0 else 'pdf_export_recorded',**({'issueCounts':{'errors':0,'warnings':0},'issues':[]} if i==0 else {})} for i,ref in enumerate(refs)]}
        receipt={'schemaVersion':2,'domain':'designcraft','runId':run,'status':'NATIVE_EXIT_ZERO_REVIEW_REQUIRED','exitCode':0,'started':True,'terminationVerified':True,'automaticReplay':False,'completeAcceptance':False,
            'inputSha256':{str(project):candidate},'inputAfterSha256':{str(project):candidate},'skillResourceSha256':{'runtime.lock.json':lock_sha},'skillResourceAfterSha256':{'runtime.lock.json':lock_sha},
            'runtimeIdentity':{'verificationStatus':'LOCKED_EXPECTATION','name':lock['artifact'],'version':lock['resolvedVersion'],'platform':'darwin-arm64','runtimeHome':'/tmp/fixture-runtime','lockSha256':lock_sha,'expectedBinarySha256':lock['artifacts']['darwin-arm64']['binarySha256']},
            'stepResultGranularity':'single-native-session','stepReferences':refs,'stepResults':[dict(ref,status='BATCH_EXIT_ZERO_REVIEW_REQUIRED',granularity='single-native-session') for ref in refs],'stdout':json.dumps(raw),'businessAssessment':assessment}
        rp=root/'receipt.json';rp.write_text(json.dumps(receipt))
        task=self.store.create('Verify current source business results','Only verify saved candidate evidence')
        task=self.store.update(task['taskId'],{'candidateSha256':candidate},task['revision'])
        task=self.store.transition(task['taskId'],'EXECUTING',task['revision'])
        task=self.store.transition(task['taskId'],'VERIFYING',task['revision'])
        return root,mp,rp,task,receipt,raw

    def test_verified_av01_uses_public_validator_and_receipt_drift_invalidates_it(self):
        root,mp,rp,task,receipt,raw=self.fixture()
        task=self.store.verify_artifact_manifest(task['taskId'],root,mp,task['revision'])
        task=self.store.verify_business(task['taskId'],root,mp,rp,task['revision'])
        self.assertEqual(self.store._fresh_evidence(task),{'AV-01','AV-02'})
        ref=next(item for item in task['evidenceRefs'] if item['kind']=='AV-01')
        proof=json.loads((self.root/'tasks'/task['taskId']/'evidence'/ref['file']).read_text())
        self.assertEqual(proof['businessReport']['result']['contractVersion'],'designcraft-business-evidence/v1')
        self.assertFalse(proof['businessReport']['result']['completeAcceptance'])
        raw['results'][1]['warnings']=['unsupported output'];receipt['stdout']=json.dumps(raw);rp.write_text(json.dumps(receipt))
        self.assertNotIn('AV-01',self.store._fresh_evidence(self.store.get(task['taskId'])))
        self.assertIn('AV-02',self.store._fresh_evidence(self.store.get(task['taskId'])))

    def test_av01_without_registered_current_av02_is_rejected(self):
        root,mp,rp,task,receipt,raw=self.fixture()
        with self.assertRaisesRegex(ValueError,'artifact_reopen_not_verified'):
            self.store.verify_business(task['taskId'],root,mp,rp,task['revision'])
        self.assertEqual(self.store.get(task['taskId'])['evidenceRefs'],[])

    def test_raw_warning_cannot_be_registered_by_reusing_pass_classification(self):
        root,mp,rp,task,receipt,raw=self.fixture()
        task=self.store.verify_artifact_manifest(task['taskId'],root,mp,task['revision'])
        raw['results'][1]['warnings']=['format loss'];receipt['stdout']=json.dumps(raw);rp.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError,'business_result_not_verified'):
            self.store.verify_business(task['taskId'],root,mp,rp,task['revision'])
        self.assertEqual([item['kind'] for item in self.store.get(task['taskId'])['evidenceRefs']],['AV-02'])

if __name__=='__main__':unittest.main()
