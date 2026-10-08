"""真实启动器/网关子进程接入 Harness；只替换安装器和原生程序，不运行 DesignCraft。"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('execution_handoff', ROOT / 'skills/designcraft-harness/scripts/harness.py')
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


class ExecutionHandoffContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='DesignCraft 契约 ')
        self.root = Path(self.temp.name)
        self.scripts = self.root / '独立技能/scripts'
        shutil.copytree(ROOT / 'skills/designcraft-use/scripts', self.scripts)
        self.input = self.root / 'registered.bin'
        self.input.write_bytes(b'protected original')
        self.native = self.root / 'controlled-native'
        self.log = self.root / 'invocations.jsonl'
        self.store = HARNESS.TaskStore(self.root / 'tasks')

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self, mode, steps=None):
        # 保留当前 cli.py/commands.py/command_gateway.py；受控安装器永远不下载。
        self.native.write_text(f'''#!{sys.executable}
import json,os,signal,sys
from pathlib import Path
root=Path({str(self.root)!r});mode={mode!r}
with (root/'invocations.jsonl').open('a') as stream:stream.write(json.dumps(sys.argv[1:])+'\\n')
if sys.argv[1]=='commands':
 if mode=='before-input':(root/'registered.bin').write_bytes(b'drift during discovery')
 print(json.dumps([{{'id':command,'params':'','menu':[]}} for command in ('file.new','file.open','file.saveAs','file.exportText','story.create','story.insert','document.inspect')]))
 raise SystemExit(0)
plan=[json.loads(line) for line in Path(sys.argv[2]).read_text().splitlines()]
if mode=='recovery':
 if any(step['command']=='file.saveAs' for step in plan):
  saved=Path(plan[1]['params']['path']);saved.write_bytes(b'controlled saved project')
  print(json.dumps({{'completed':2,'failedIndex':2,'failedCommand':'file.exportText','error':'controlled failure','results':[{{'index':1}},{{'path':str(saved),'bytes':saved.stat().st_size}}]}}))
  raise SystemExit(1)
 project=plan[0]['params']['path']
 print(json.dumps({{'completed':2,'results':[{{'index':1}},{{'path':project,'dirty':False,'pageCount':1,'spreads':[{{'items':[{{'id':91,'kind':'text frame','story':92}}]}}],'stories':[{{'id':92}}]}}]}}))
 raise SystemExit(0)
if mode=='input':(root/'registered.bin').write_bytes(b'changed input')
if mode=='skill':
 with (root/'独立技能/scripts/bootstrap.py').open('a') as stream:stream.write('\\n# controlled drift\\n')
if mode=='missing-input':(root/'registered.bin').unlink()
if '--in' in sys.argv:Path(sys.argv[sys.argv.index('--in')+1]).write_bytes(b'edited working copy')
if mode=='interrupt':
 print('controlled partial log',flush=True)
 os.kill(os.getppid(),signal.SIGINT)
 raise SystemExit(0)
if mode=='partial':
 print(json.dumps({{'completed':2,'failedIndex':2,'failedCommand':plan[2]['command'],'error':'controlled failure','results':[{{'id':11}},{{'id':12}}]}}))
 raise SystemExit(1)
print(json.dumps({{'completed':len(plan),'results':[{{'id':i+1}} for i in range(len(plan))]}}))
''')
        self.native.chmod(0o755)
        self.scripts.joinpath('bootstrap.py').write_text(
            "import sys\ndef install(lock,home,archive=None):\n"
            + (f" return {{'executable':{str(self.root / 'missing-native')!r} if '--result-file' in sys.argv else {str(self.native)!r}}}\n"
               if mode == 'not-started' else f" return {{'executable':{str(self.native)!r}}}\n"))
        self.plan = self.root / 'plan.json'
        self.plan.write_text(json.dumps({'domain': 'designcraft', 'steps': steps or [{'command': 'file.new', 'params': {}}]}))
        task = self.store.create('Offline execution contract', 'Only controlled fixture files')
        return self.store.transition(task['taskId'], 'EXECUTING', task['revision'])

    def dispatch(self, task, extra=()):
        with patch.object(HARNESS, 'EXTERNAL_COMMANDS', self.scripts / 'commands.py'), patch.object(HARNESS, 'readiness_report', return_value={'status': 'READY'}):
            task = self.store.dispatch_native(task['taskId'], ['run', str(self.plan), '--output', str(self.root / 'output'), '--input', str(self.input), *extra], task['revision'])
        saved = json.loads((self.root / 'tasks' / task['taskId'] / task['nativeReceiptRef']).read_text())
        return task, saved

    def test_ex05_preservation_status_and_run_identity_survive_gateway_nonzero_exit(self):
        task = self.prepare('input')
        task, saved = self.dispatch(task)
        source = json.loads((self.root / 'output/receipt.json').read_text())
        self.assertEqual(source['status'], 'INPUT_CHANGED_REVIEW_REQUIRED')
        self.assertEqual(task['nativeStatus'], source['status'])
        self.assertEqual(task['runId'], source['runId'])
        self.assertEqual(saved['payload'], source)
        self.assertEqual((saved['processExitCode'], source['exitCode']), (1, 0))
        self.assertEqual(task['nextAction'], 'reconcile_native_result')
        self.assertIn('registered_inputs_changed', task['blockers'])
        before = self.log.read_bytes()
        with patch.object(HARNESS, 'EXTERNAL_COMMANDS', self.scripts / 'commands.py'):
            with self.assertRaisesRegex(ValueError, 'native_dispatch_already_started'):
                self.store.dispatch_native(task['taskId'], ['run', str(self.plan)], task['revision'])
        self.assertEqual(self.log.read_bytes(), before)

    def test_ex05_resource_drift_survives_and_cannot_be_reported_as_ordinary_success(self):
        task, saved = self.dispatch(self.prepare('skill'))
        self.assertEqual(task['nativeStatus'], 'SKILL_CHANGED_REVIEW_REQUIRED')
        self.assertNotEqual(saved['payload']['skillResourceSha256'], saved['payload']['skillResourceAfterSha256'])
        self.assertIn('skill_resources_changed', task['blockers'])

    def test_ex05_incomplete_preservation_check_retains_source_diagnostic(self):
        task, saved = self.dispatch(self.prepare('missing-input'))
        self.assertEqual(task['nativeStatus'], 'INPUT_OR_SKILL_CHANGED_REVIEW_REQUIRED')
        self.assertIn('preservationCheckError', saved['payload'])
        self.assertIn('preservation_check_incomplete', task['blockers'])

    def test_ex01_ex02_actual_child_interrupt_stays_unknown_with_partial_logs(self):
        task, saved = self.dispatch(self.prepare('interrupt'))
        self.assertEqual(task['nativeStatus'], 'UNKNOWN')
        self.assertEqual(saved['payload']['reason'], 'user_interrupted')
        self.assertFalse(saved['payload']['terminationVerified'])
        self.assertIn('controlled partial log', saved['payload']['stdout'])
        self.assertFalse(saved['payload']['automaticReplay'])

    def test_ex01_known_launch_failure_stays_not_started(self):
        task, saved = self.dispatch(self.prepare('not-started'))
        self.assertEqual(task['nativeStatus'], 'NOT_STARTED')
        self.assertFalse(saved['payload']['started'])
        self.assertEqual(saved['payload']['reason'], 'native_launch_failed')

    def test_ex03_ex04_partial_steps_and_single_session_references_reach_harness(self):
        steps = [{'command': 'file.new', 'params': {}}, {'command': 'story.create', 'params': {}}, {'command': 'story.insert', 'params': {'story': 'step:1.id', 'text': 'Title'}}, {'command': 'document.inspect', 'params': {}}]
        task, saved = self.dispatch(self.prepare('partial', steps))
        payload = saved['payload']
        self.assertEqual(task['nativeStatus'], 'FAILED_OR_PARTIAL')
        self.assertEqual([r['status'] for r in payload['stepResults']], ['STEP_COMPLETED_REVIEW_REQUIRED', 'STEP_COMPLETED_REVIEW_REQUIRED', 'STEP_FAILED_OR_PARTIAL', 'NOT_STARTED'])
        self.assertEqual(payload['stepReferences'][2]['paramsSha256'], hashlib.sha256(json.dumps(steps[2]['params'], sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest())
        actual = [json.loads(line) for line in (self.root / 'output/native-plan.json').read_text().splitlines()]
        self.assertEqual(actual, steps)
        invocations = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual([v[0] for v in invocations], ['commands', 'script'])
        task = self.store.transition(task['taskId'], 'RECONCILING', task['revision'])
        result = self.store.reconcile(task['taskId'])
        self.assertEqual(result['stepResults'], payload['stepResults'])
        self.assertFalse(result['resumeAllowed'])

    def test_ex05_working_copy_preserves_original_and_zero_exit_needs_acceptance(self):
        task = self.prepare('success')
        project = self.root / 'source.designcraft'
        project.write_bytes(b'original project')
        task, saved = self.dispatch(task, ['--source', str(project)])
        payload = saved['payload']
        self.assertEqual(task['nativeStatus'], 'NATIVE_EXIT_ZERO_REVIEW_REQUIRED')
        self.assertEqual(task['state'], 'EXECUTING')
        self.assertEqual(project.read_bytes(), b'original project')
        self.assertEqual(Path(payload['workingCopyPath']).read_bytes(), b'edited working copy')
        self.assertNotEqual(payload['workingCopyBeforeSha256'], payload['workingCopyAfterSha256'])
        self.assertFalse(payload['completeAcceptance'])
        with self.assertRaisesRegex(ValueError, 'required_acceptance_evidence_missing'):
            task = self.store.transition(task['taskId'], 'VERIFYING', task['revision'])
            task = self.store.transition(task['taskId'], 'REVIEW_REQUIRED', task['revision'])
            self.store.transition(task['taskId'], 'COMPLETED', task['revision'])

    def test_ex05_before_edit_input_drift_creates_no_output_and_invokes_no_edit(self):
        task, saved = self.dispatch(self.prepare('before-input'))
        self.assertFalse((self.root / 'output').exists())
        self.assertIn('input_changed_before_native_edit', saved['stdout'])
        self.assertEqual(task['nativeStatus'], 'UNKNOWN')
        self.assertEqual([json.loads(line)[0] for line in self.log.read_text().splitlines()], ['commands'])

    def test_ex03_public_source_recovery_report_is_accepted_by_harness_without_replay(self):
        saved_project = self.root / 'saved.designcraft'
        steps = [{'command': 'file.open', 'params': {'path': str(self.input)}}, {'command': 'file.saveAs', 'params': {'path': str(saved_project)}}, {'command': 'file.exportText', 'params': {'path': str(self.root / 'text.txt')}}, {'command': 'document.inspect', 'params': {}}]
        task, saved = self.dispatch(self.prepare('recovery', steps))
        self.assertEqual(task['nativeStatus'], 'FAILED_OR_PARTIAL')
        self.assertIsNotNone(saved['payload']['savedProjectCheckpoint'])
        reopen_plan = self.root / 'reopen-plan.json'
        reopen_plan.write_text(json.dumps({'domain': 'designcraft', 'steps': [{'command': 'file.open', 'params': {'path': str(saved_project)}}, {'command': 'document.inspect', 'params': {}}]}))
        command = [sys.executable, '-I', '-B', str(self.scripts / 'commands.py')]
        reopened = subprocess.run([*command, 'run', str(reopen_plan), '--output', str(self.root / 'reopen'), '--input', str(saved_project)], capture_output=True, text=True)
        self.assertEqual(reopened.returncode, 0, reopened.stdout + reopened.stderr)
        original_receipt = self.root / 'output/receipt.json'
        reopen_receipt = self.root / 'reopen/receipt.json'
        recovered = subprocess.run([*command, 'recover', str(original_receipt), '--checkpoint-receipt', str(reopen_receipt)], capture_output=True, text=True)
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        recovery_path = self.root / 'recovery.json'
        recovery_path.write_text(recovered.stdout)
        report = json.loads(recovered.stdout)
        self.assertEqual(report['remainingPlan'], {'domain': 'designcraft', 'steps': [steps[-1]]})
        self.assertFalse(report['automaticExecution'])
        task = self.store.update(task['taskId'], {'checkpointRefs': [str(saved_project)]}, task['revision'])
        task = self.store.transition(task['taskId'], 'RECONCILING', task['revision'])
        before = self.log.read_bytes()
        diagnostic = self.store.reconcile(task['taskId'], recovery_report_path=recovery_path, reopen_receipt_path=reopen_receipt, reopen_plan_path=reopen_plan, original_plan_path=self.plan, saved_project_path=saved_project)
        self.assertTrue(diagnostic['planVerified'], diagnostic)
        self.assertEqual(diagnostic['remainingPlan'], report['remainingPlan'])
        self.assertFalse(diagnostic['automaticExecution'])
        self.assertIn('process_descendants_termination_unverified', diagnostic['risks'])
        self.assertEqual(self.log.read_bytes(), before)
        alias = self.root / 'directory-alias'
        alias.symlink_to(self.root, target_is_directory=True)
        arguments = {'recovery_report_path': recovery_path, 'reopen_receipt_path': reopen_receipt, 'reopen_plan_path': reopen_plan, 'original_plan_path': self.plan}
        equivalent = self.store.reconcile(task['taskId'], saved_project_path=alias / saved_project.name, **arguments)
        self.assertTrue(equivalent['planVerified'], equivalent)
        duplicate = self.root / 'different-saved.designcraft'
        duplicate.write_bytes(saved_project.read_bytes())
        rejected = self.store.reconcile(task['taskId'], saved_project_path=duplicate, **arguments)
        self.assertFalse(rejected['planVerified'])
        self.assertIn('source_recovery_checkpoint_mismatch', rejected['blockers'])
        linked = self.root / 'linked.designcraft'
        linked.symlink_to(saved_project)
        rejected = self.store.reconcile(task['taskId'], saved_project_path=linked, **arguments)
        self.assertFalse(rejected['planVerified'])
        self.assertIn('source_recovery_checkpoint_missing_or_unsafe', rejected['blockers'])
        self.assertEqual(self.log.read_bytes(), before)

    def test_preservation_status_without_evidence_or_with_contradictory_exit_is_unknown(self):
        for process_exit in (0, 1):
            with self.subTest(processExit=process_exit):
                task = self.prepare('success')
                stub = self.root / 'malformed-commands.py'
                stub.write_text('import json\nprint(json.dumps(' + repr({'schemaVersion': 2, 'status': 'INPUT_CHANGED_REVIEW_REQUIRED', 'runId': '11111111-1111-4111-8111-111111111111', 'exitCode': 0}) + '))\nraise SystemExit(' + str(process_exit) + ')\n')
                with patch.object(HARNESS, 'EXTERNAL_COMMANDS', stub), patch.object(HARNESS, 'readiness_report', return_value={'status': 'READY'}):
                    task = self.store.dispatch_native(task['taskId'], ['run', str(self.plan)], task['revision'])
                self.assertEqual(task['nativeStatus'], 'UNKNOWN')
                self.assertIsNone(task['runId'])


if __name__ == '__main__':
    unittest.main()
