"""正式技能源锁的离线内容与在线引用分层校验。"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_lock", ROOT / "scripts/release_lock.py")
release_lock = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_lock)


class ReleaseLockContract(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        files = {
            "skills/designcraft-use/SKILL.md": "# use\n",
            "skills/designcraft-cli/SKILL.md": "# cli\n",
        }
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files}
        canonical = json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()
        lock = {
            "schemaVersion": 1,
            "repository": "https://github.com/example/designcraft-skills",
            "releaseTag": "v1.2.3",
            "commitSha": "a" * 40,
            "sourceVersion": "1.2.3",
            "skills": ["designcraft-cli", "designcraft-use"],
            "files": hashes,
            "contentSha256": hashlib.sha256(canonical).hexdigest(),
        }
        return temp, root, lock

    def test_offline_content_pass_does_not_claim_online_trust(self):
        temp, root, lock = self.fixture()
        with temp:
            result = release_lock.verify_release_lock(lock, root, trusted_repository=lock["repository"])
        self.assertEqual(result["offlineStatus"], "PASS")
        self.assertEqual(result["onlineStatus"], "NOT_RUN")
        self.assertFalse(result["releaseAllowed"])

    def test_matching_offline_and_online_evidence_allows_release(self):
        temp, root, lock = self.fixture()
        with temp:
            result = release_lock.verify_release_lock(
                lock, root, trusted_repository=lock["repository"],
                resolved_repository=lock["repository"], resolved_commit=lock["commitSha"],
            )
        self.assertEqual((result["offlineStatus"], result["onlineStatus"]), ("PASS", "PASS"))
        self.assertTrue(result["releaseAllowed"])

    def test_schema_file_declares_exact_lock_contract(self):
        schema = json.loads((ROOT / "schemas/source-release-lock.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$id"], "urn:designcraft:source-release-lock:1")
        self.assertTrue(schema["additionalProperties"] is False)
        self.assertEqual(set(schema["required"]), {
            "schemaVersion", "repository", "releaseTag", "commitSha", "sourceVersion",
            "skills", "files", "contentSha256",
        })

    def test_repointed_tag_is_rejected_by_online_resolution(self):
        temp, root, lock = self.fixture()
        with temp:
            result = release_lock.verify_release_lock(
                lock, root, trusted_repository=lock["repository"],
                resolved_repository=lock["repository"], resolved_commit="b" * 40,
            )
        self.assertEqual(result["onlineStatus"], "FAIL")
        self.assertIn("resolved_commit_mismatch", result["errors"])
        self.assertFalse(result["releaseAllowed"])

    def test_wrong_repository_is_rejected_even_when_commit_matches(self):
        temp, root, lock = self.fixture()
        with temp:
            result = release_lock.verify_release_lock(
                lock, root, trusted_repository="https://github.com/trusted/designcraft-skills",
                resolved_repository=lock["repository"], resolved_commit=lock["commitSha"],
            )
        self.assertEqual(result["offlineStatus"], "FAIL")
        self.assertIn("trusted_repository_mismatch", result["errors"])
        self.assertFalse(result["releaseAllowed"])

    def test_content_digest_mismatch_is_rejected_offline(self):
        temp, root, lock = self.fixture()
        with temp:
            lock["contentSha256"] = "0" * 64
            result = release_lock.verify_release_lock(lock, root, trusted_repository=lock["repository"])
        self.assertEqual(result["offlineStatus"], "FAIL")
        self.assertIn("content_digest_mismatch", result["errors"])

    def test_semver_numeric_prerelease_with_leading_zero_is_rejected(self):
        temp, root, lock = self.fixture()
        with temp:
            lock["releaseTag"] = "v1.2.3-01"
            lock["sourceVersion"] = "1.2.3-01"
            result = release_lock.verify_release_lock(lock, root, trusted_repository=lock["repository"])
        self.assertEqual(result["offlineStatus"], "FAIL")
        self.assertIn("release_tag_invalid", result["errors"])

    def test_network_unavailable_stays_unverified_and_cannot_release(self):
        temp, root, lock = self.fixture()
        with temp:
            result = release_lock.verify_release_lock(
                lock, root, trusted_repository=lock["repository"], network_error="offline",
            )
        self.assertEqual(result["onlineStatus"], "NOT_VERIFIED_NETWORK_UNAVAILABLE")
        self.assertFalse(result["releaseAllowed"])

    def test_remote_tag_resolution_uses_peeled_commit_for_annotated_tag(self):
        commit = "c" * 40
        runner = Mock(return_value=subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=f'{"d" * 40}\trefs/tags/v1.2.3\n{commit}\trefs/tags/v1.2.3^{{}}\n', stderr="",
        ))
        result = release_lock.resolve_remote_tag(
            "https://github.com/example/designcraft-skills", "v1.2.3", runner=runner,
        )
        self.assertEqual(result, {"status": "PASS", "commitSha": commit, "errors": []})
        self.assertEqual(runner.call_args.args[0][-2:], ["refs/tags/v1.2.3", "refs/tags/v1.2.3^{}"])

    def test_remote_lightweight_tag_resolves_to_its_commit(self):
        commit = "e" * 40
        runner = Mock(return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout=f'{commit}\trefs/tags/v1.2.3\n', stderr="",
        ))
        result = release_lock.resolve_remote_tag(
            "https://github.com/example/designcraft-skills", "v1.2.3", runner=runner,
        )
        self.assertEqual(result["commitSha"], commit)

    def test_remote_tag_missing_and_network_failure_are_distinct(self):
        missing = Mock(return_value=subprocess.CompletedProcess(args=[], returncode=2, stdout="", stderr=""))
        result = release_lock.resolve_remote_tag(
            "https://github.com/example/designcraft-skills", "v1.2.3", runner=missing,
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("release_tag_not_found", result["errors"])

        network = Mock(side_effect=subprocess.TimeoutExpired(cmd="git ls-remote", timeout=20))
        result = release_lock.resolve_remote_tag(
            "https://github.com/example/designcraft-skills", "v1.2.3", runner=network,
        )
        self.assertEqual(result["status"], "NOT_VERIFIED_NETWORK_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
