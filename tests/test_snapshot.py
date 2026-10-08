"""本地插件快照合同。"""
import importlib.util
from pathlib import Path
import json
import shutil
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class SnapshotContract(unittest.TestCase):
    def record_host_evidence(self,fixture,platforms):
        project_path=fixture/'project-status.json';project=json.loads(project_path.read_text())
        project['hostDiscovery']='PASS';project_path.write_text(json.dumps(project))
        matrix_path=fixture/'support-matrix.json';matrix=json.loads(matrix_path.read_text())
        matrix['host']['discovery']='PASS';matrix['host']['testedPlatforms']=platforms;matrix_path.write_text(json.dumps(matrix))
        report_path=fixture/'evidence/host/fixture.json';report_path.parent.mkdir(parents=True,exist_ok=True)
        report_path.write_text(json.dumps({'testedPlatforms':platforms}))
        freshness_path=fixture/'scripts/evidence_freshness.py'
        spec=importlib.util.spec_from_file_location('fixture_freshness',freshness_path)
        freshness=importlib.util.module_from_spec(spec);spec.loader.exec_module(freshness)
        from datetime import datetime,timezone
        import uuid
        manifest_path=fixture/'evidence-manifest.json';manifest=json.loads(manifest_path.read_text())
        manifest['records']=[item for item in manifest['records'] if item.get('id')!='host']
        manifest['records'].append(freshness.create_record(fixture,'host','host','PASS',str(uuid.uuid4()),datetime.now(timezone.utc).isoformat(),[],['evidence/host/fixture.json']))
        manifest_path.write_text(json.dumps(manifest))

    def clear_host_acceptance(self,fixture):
        project=fixture/'project-status.json';status=json.loads(project.read_text())
        status['hostDiscovery']='NOT_RUN';status['modelDispatch']='NOT_RUN';project.write_text(json.dumps(status))
        matrix=fixture/'support-matrix.json';support=json.loads(matrix.read_text())
        support['host']['discovery']='NOT_RUN';support['host']['modelDispatch']='NOT_RUN';support['host']['testedPlatforms']=[]
        matrix.write_text(json.dumps(support))
        manifest=fixture/'evidence-manifest.json';evidence=json.loads(manifest.read_text())
        for record in evidence['records']:
            if record.get('id') in ('host','model-dispatch'):record['status']='NOT_RUN'
        manifest.write_text(json.dumps(evidence))

    def test_harness_invocation_policy_rejects_implicit_or_missing_policy(self):
        for value in ('true', '"false"', 'false\n  allow_implicit_invocation: true', None):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as temp:
                fixture=Path(temp)/'plugin';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__','.DS_Store'))
                path=fixture/'skills/designcraft-harness/agents/openai.yaml';path.parent.mkdir(exist_ok=True)
                if value is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_text('policy:\n  allow_implicit_invocation: '+value+'\n')
                spec=importlib.util.spec_from_file_location('policy_validator',fixture/'scripts/validate_package.py')
                module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
                with self.assertRaisesRegex(ValueError,'skill_invocation_policy_invalid'):
                    module.validate()

    def test_self_contained_snapshot_and_unpublished_identity(self):
        p=ROOT/'scripts/validate_package.py';spec=importlib.util.spec_from_file_location('validator',p)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        result=module.validate()
        self.assertEqual((result['skills'],result['externalSkills'],result['localSkills']),(7,6,1))
        self.assertEqual(result['hostManifest'],'PASS')

    def test_candidate_identity_is_schema_checked_and_independent_of_plugin_version(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture=Path(temp)/'plugin';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            self.clear_host_acceptance(fixture)
            p=fixture/'scripts/validate_package.py';spec=importlib.util.spec_from_file_location('candidate_validator',p)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            manifest=json.loads((fixture/'plugin.json').read_text());manifest['version']='9.4.0';(fixture/'plugin.json').write_text(json.dumps(manifest))
            matrix=fixture/'support-matrix.json';data=json.loads(matrix.read_text());data['packageVersion']='9.4.0';matrix.write_text(json.dumps(data))
            host=fixture/'.codex-plugin/plugin.json';host_data=json.loads(host.read_text());host_data['version']='9.4.0';host.write_text(json.dumps(host_data))
            self.assertEqual(module.validate()['sourceRelease'],'UNPUBLISHED')

    def test_candidate_identity_mismatch_is_rejected_before_snapshot_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture=Path(temp)/'plugin';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            p=fixture/'scripts/validate_package.py';spec=importlib.util.spec_from_file_location('candidate_validator_bad',p)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            path=fixture/'candidate-source.json';original=json.loads(path.read_text())
            mutations=(('sourceProject','another-project'),('sourceVersion','9.9.9'),('sourceStatus','published'),('releaseTag','v9.9.9'))
            for key,value in mutations:
                with self.subTest(field=key):
                    source=dict(original);source[key]=value;path.write_text(json.dumps(source))
                    with self.assertRaisesRegex(ValueError,'candidate_source_identity_mismatch'):
                        module.validate()

    def test_external_script_drift_invalidates_the_bundled_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture=Path(temp)/'plugin';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            p=fixture/'scripts/validate_package.py';spec=importlib.util.spec_from_file_location('drift_validator',p)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            script=fixture/'skills/designcraft-use/scripts/command_gateway.py';script.write_text(script.read_text()+'\n# source drift\n')
            with self.assertRaisesRegex(ValueError,'snapshot_drift'):
                module.validate()

    def test_support_matrix_rejects_unverified_host_claims_and_status_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture=Path(temp)/'plugin';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            self.record_host_evidence(fixture,['Codex CLI 0.147.0 on macOS arm64'])
            p=fixture/'scripts/validate_package.py';spec=importlib.util.spec_from_file_location('support_validator',p)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            path=fixture/'support-matrix.json';matrix=json.loads(path.read_text());matrix['host']['testedPlatforms']=['Windows x64'];path.write_text(json.dumps(matrix))
            with self.assertRaisesRegex(ValueError,'host_evidence_platform_mismatch'):
                module.validate()

    def test_host_evidence_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture=Path(temp)/'plugin';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            self.record_host_evidence(fixture,['Codex CLI 0.147.0 on macOS arm64'])
            manifest_path=fixture/'evidence-manifest.json';manifest=json.loads(manifest_path.read_text())
            record=next(item for item in manifest['records'] if item.get('id')=='host')
            record['artifacts'][0]['path']='../../outside.json';manifest_path.write_text(json.dumps(manifest))
            p=fixture/'scripts/validate_package.py';spec=importlib.util.spec_from_file_location('host_path_validator',p)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            with self.assertRaisesRegex(ValueError,'host_evidence_report_path_invalid'):
                module.validate()

    def test_nonstandard_plugin_manifest_field_and_name_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture=Path(temp)/'plugin';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            p=fixture/'scripts/validate_package.py';spec=importlib.util.spec_from_file_location('manifest_validator',p)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            path=fixture/'plugin.json';manifest=json.loads(path.read_text());manifest['skills']=[];path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'plugin_manifest_invalid'):
                module.validate()

    def test_unimplemented_host_extensions_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture=Path(temp)/'plugin';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            p=fixture/'scripts/validate_package.py';spec=importlib.util.spec_from_file_location('extension_validator',p)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            path=fixture/'plugin.json';manifest=json.loads(path.read_text());manifest['extensions']={'mcp':{'servers':{'designcraft':{}}}};path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'plugin_extension_not_implemented'):
                module.validate()

    def test_command_hook_and_mcp_declarations_without_implementations_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture=Path(temp)/'plugin';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            p=fixture/'scripts/validate_package.py';spec=importlib.util.spec_from_file_location('component_validator',p)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            path=fixture/'plugin.json';original=json.loads(path.read_text())
            for field,value in (('commands',[]),('hooks',{}),('mcpServers',{})):
                with self.subTest(field=field):
                    manifest=dict(original);manifest[field]=value;path.write_text(json.dumps(manifest))
                    with self.assertRaisesRegex(ValueError,'plugin_manifest_invalid'):
                        module.validate()

    def test_declared_icon_resource_must_exist_inside_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture=Path(temp)/'plugin';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            p=fixture/'scripts/validate_package.py';spec=importlib.util.spec_from_file_location('resource_validator',p)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            path=fixture/'plugin.json';manifest=json.loads(path.read_text())
            manifest['extensions']={'com.openai':{'interface':{'composerIcon':'./assets/missing.png'}}}
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'plugin_resource_invalid'):
                module.validate()

    def test_codex_compatibility_manifest_must_match_portable_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture=Path(temp)/'plugin';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            p=fixture/'scripts/validate_package.py';spec=importlib.util.spec_from_file_location('host_manifest_validator',p)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            host=fixture/'.codex-plugin/plugin.json';host.parent.mkdir(exist_ok=True)
            host.write_text(json.dumps({'name':'designcraft','version':'0.2.0','skills':'./skills/'}))
            with self.assertRaisesRegex(ValueError,'plugin_host_manifest_version_mismatch'):
                module.validate()

    def test_matching_codex_compatibility_manifest_and_valid_icon_are_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture=Path(temp)/'plugin';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            self.clear_host_acceptance(fixture)
            p=fixture/'scripts/validate_package.py';spec=importlib.util.spec_from_file_location('valid_host_manifest_validator',p)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            icon=fixture/'assets/composer.png';icon.parent.mkdir();icon.write_bytes(b'\x89PNG\r\n\x1a\nfixture')
            manifest_path=fixture/'plugin.json';manifest=json.loads(manifest_path.read_text())
            manifest['extensions']={'com.openai':{'interface':{'composerIcon':'./assets/composer.png'}}}
            manifest_path.write_text(json.dumps(manifest))
            host=fixture/'.codex-plugin/plugin.json';host.parent.mkdir(exist_ok=True)
            host.write_text(json.dumps({'name':'designcraft','version':'0.1.0-dev.1','skills':'./skills/','interface':{'composerIcon':'./assets/composer.png'}}))
            self.assertEqual(module.validate()['snapshot'],'PASS')

    def test_non_semver_plugin_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture=Path(temp)/'plugin';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            p=fixture/'scripts/validate_package.py';spec=importlib.util.spec_from_file_location('semver_validator',p)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            path=fixture/'plugin.json';manifest=json.loads(path.read_text());manifest['version']='dev-latest';path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'plugin_manifest_invalid'):
                module.validate()

    def test_local_harness_cannot_leak_into_the_external_source_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture=Path(temp)/'plugin';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            p=fixture/'scripts/validate_package.py';spec=importlib.util.spec_from_file_location('ownership_validator',p)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            path=fixture/'candidate-source.json';source=json.loads(path.read_text());source['bundledSourceIdentity']['skills'].append('designcraft-harness');path.write_text(json.dumps(source))
            with self.assertRaisesRegex(ValueError,'local_skill_manifest_invalid'):
                module.validate()

    def test_plugin_local_skill_cannot_ship_broken_or_cross_skill_references(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture=Path(temp)/'plugin';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            p=fixture/'scripts/validate_package.py';spec=importlib.util.spec_from_file_location('local_reference_validator',p)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            skill=fixture/'skills/designcraft-harness/SKILL.md'
            original=skill.read_text()
            for reference in ('[broken](references/missing.md)','[cross-skill](../designcraft-cli/SKILL.md)'):
                with self.subTest(reference=reference):
                    skill.write_text(original+'\n'+reference+'\n')
                    with self.assertRaisesRegex(ValueError,'plugin_local_skill_reference_invalid'):
                        module.validate()
if __name__=='__main__':unittest.main()
