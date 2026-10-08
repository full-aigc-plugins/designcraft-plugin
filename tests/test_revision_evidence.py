"""The Harness accepts AV-04 only through the source-owned revision validator."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'skills/designcraft-harness/scripts/harness.py'

class RevisionEvidenceIntegration(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('revision_harness',SOURCE)
        self.harness=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.harness)
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.store=self.harness.TaskStore(self.root/'task-home')

    def tearDown(self):self.temp.cleanup()

    def _revision_fixture(self):
        deliverables=self.root/'deliverables';deliverables.mkdir()
        brief=deliverables/'brief.md';brief.write_text('Only change the page-three headline')
        sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        sides={}
        for side in ('before','after'):
            folder=deliverables/side;folder.mkdir()
            project=folder/'book.designcraft';project.write_bytes((side+' project').encode())
            pdf=folder/'book.pdf';pdf.write_bytes((side+' pdf').encode())
            preview=folder/'page-1.png';preview.write_bytes((side+' preview').encode())
            local_brief=folder/'brief.md';local_brief.write_text(brief.read_text())
            run_id=str(uuid.uuid4())
            manifest={'schemaVersion':1,'runId':run_id,'projectArtifactId':'project','artifacts':[
                {'id':'project','kind':'project','path':project.name,'format':'designcraft','byteCount':project.stat().st_size,'sha256':sha(project)},
                {'id':'pdf','kind':'export','path':pdf.name,'format':'pdf','byteCount':pdf.stat().st_size,'sha256':sha(pdf)}],
                'expectations':{'pageCount':1,'pageDimensionsMm':[{'page':1,'width':210.0,'height':297.0}],'criticalText':['Title'],'linkedAssets':[]},
                'reopenCheck':{'status':'PASS','sessionId':side+'-session','projectSha256':sha(project),'pageCount':1,'pageDimensionsMm':[{'page':1,'width':210.0,'height':297.0}],
                    'criticalText':['Title'],'linkedAssets':[],'verifiedBy':'reviewer','verifiedAt':'2026-10-08T10:00:00Z'}}
            manifest_path=folder/'artifact-manifest.json';manifest_path.write_text(json.dumps(manifest))
            review={'schemaVersion':1,'contractVersion':'designcraft-page-review/v1','runId':run_id,'projectSha256':sha(project),
                'artifactManifestSha256':sha(manifest_path),'rubricVersion':'designcraft-layout-rubric/v1',
                'basis':{'type':'task-spec','path':local_brief.name,'sha256':sha(local_brief)},'reviewer':{'kind':'human','identity':'reviewer'},
                'reviewedAt':'2026-10-08T10:05:00Z','pages':[{'page':1,'previewPath':preview.name,'previewSha256':sha(preview),
                    'checks':[{'criterion':criterion,'status':'PASS','note':'reviewed'} for criterion in ('hierarchy','whitespace','alignment','readability','cropping','crossPageConsistency')]}],
                'conclusions':{name:{'status':'PASS','note':'reviewed'} for name in ('structure','visual','output','editability')}}
            review_path=folder/'page-review.json';review_path.write_text(json.dumps(review))
            snapshot={'schemaVersion':1,'projectSha256':sha(project),'objects':[{'id':'headline','page':1,'contentSha256':('a' if side=='before' else 'b')*64,'storyId':None}]}
            snapshot_path=folder/'revision-snapshot.json';snapshot_path.write_text(json.dumps(snapshot))
            sides[side]={'folder':folder,'project':project,'pdf':pdf,'manifest':manifest_path,'review':review_path,'snapshot':snapshot_path}
        before=sides['before'];after=sides['after']
        record={'schemaVersion':1,'contractVersion':'designcraft-revision/v1',
            'authorization':{'scope':{'type':'object','objectId':'headline'},'authorizationText':'Change the page-three headline'},
            'before':{'artifactManifestPath':'before/artifact-manifest.json','artifactManifestSha256':sha(before['manifest']),
                'pageReviewPath':'before/page-review.json','pageReviewSha256':sha(before['review']),
                'snapshotPath':'before/revision-snapshot.json','snapshotSha256':sha(before['snapshot'])},
            'after':{'artifactManifestPath':'after/artifact-manifest.json','artifactManifestSha256':sha(after['manifest']),
                'pageReviewPath':'after/page-review.json','pageReviewSha256':sha(after['review']),
                'snapshotPath':'after/revision-snapshot.json','snapshotSha256':sha(after['snapshot'])},
            'affectedPages':[1],'revalidatedExports':[{'artifactId':'pdf','format':'pdf','sha256':sha(after['pdf']),'status':'PASS'}]}
        revision=deliverables/'revision.json';revision.write_text(json.dumps(record))
        return deliverables,revision,after

    def _verifying_task(self,candidate):
        task=self.store.create('Revise the saved project','Change only the authorized headline','designcraft-cli-export')
        task=self.store.update(task['taskId'],{'candidateSha256':candidate},expected_revision=task['revision'])
        task=self.store.transition(task['taskId'],'EXECUTING',expected_revision=task['revision'])
        return self.store.transition(task['taskId'],'VERIFYING',expected_revision=task['revision'])

    def test_verified_revision_is_bound_to_task_candidate_and_freshness(self):
        root,revision,after=self._revision_fixture();candidate=hashlib.sha256(after['project'].read_bytes()).hexdigest()
        task=self._verifying_task(candidate)
        task=self.store.verify_artifact_manifest(task['taskId'],after['folder'],after['manifest'],expected_revision=task['revision'])
        task=self.store.verify_page_review(task['taskId'],after['folder'],after['manifest'],after['review'],expected_revision=task['revision'])
        task=self.store.verify_revision(task['taskId'],root,revision,expected_revision=task['revision'])
        self.assertIn('AV-04',self.store._fresh_evidence(task))
        reference=next(item for item in task['evidenceRefs'] if item['kind']=='AV-04')
        evidence=self.root/'task-home'/task['taskId']/'evidence'/reference['file']
        payload=json.loads(evidence.read_text())
        self.assertEqual(payload['revisionReport']['result']['affectedPages'],[1])
        self.assertFalse(payload['revisionReport']['result']['completeAcceptance'])
        revision.write_text(revision.read_text()+'\n')
        self.assertNotIn('AV-04',self.store._fresh_evidence(self.store.get(task['taskId'])))

    def test_invalid_revision_scope_is_not_registered_as_av04(self):
        root,revision,after=self._revision_fixture();candidate=hashlib.sha256(after['project'].read_bytes()).hexdigest()
        record=json.loads(revision.read_text());record['affectedPages']=[];revision.write_text(json.dumps(record))
        task=self._verifying_task(candidate)
        task=self.store.verify_artifact_manifest(task['taskId'],after['folder'],after['manifest'],expected_revision=task['revision'])
        task=self.store.verify_page_review(task['taskId'],after['folder'],after['manifest'],after['review'],expected_revision=task['revision'])
        with self.assertRaisesRegex(ValueError,'revision_affected_pages_mismatch'):
            self.store.verify_revision(task['taskId'],root,revision,expected_revision=task['revision'])
        self.assertNotIn('AV-04',{item['kind'] for item in self.store.get(task['taskId'])['evidenceRefs']})

if __name__=='__main__':unittest.main()
