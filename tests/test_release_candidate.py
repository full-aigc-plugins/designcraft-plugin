"""正式发行候选的一致性和证据新鲜度门禁。"""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_candidate", ROOT / "scripts/validate_release_candidate.py")
release_candidate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_candidate)


class ReleaseCandidateContract(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        package = root / "designcraft-1.2.3.zip"
        package.write_bytes(b"fixture-package")
        package_sha = hashlib.sha256(package.read_bytes()).hexdigest()
        manifest = {"name": "designcraft", "version": "1.2.3"}
        host = {"name": "designcraft", "version": "1.2.3"}
        source_lock_sha = "a" * 64
        evidence_root = root / "evidence"
        evidence_root.mkdir()
        evidence = {}
        for key in ("sourceRelease", "ci", "nativeRuntime", "hostDiscovery", "modelDispatch", "creativeAcceptance", "evidenceFreshness"):
            report = {"layer": key, "status": "PASS", "candidatePackageSha256": package_sha}
            if key == "sourceRelease":
                report["sourceLockSha256"] = source_lock_sha
            report_bytes = json.dumps(report, sort_keys=True).encode("utf-8")
            (evidence_root / f"{key}.json").write_bytes(report_bytes)
            evidence[key] = {
                "reportPath": f"{key}.json",
                "reportSha256": hashlib.sha256(report_bytes).hexdigest(),
            }
        return temp, {
            "release": {
                "schemaVersion": 1, "packageName": "designcraft", "packageVersion": "1.2.3",
                "packageTag": "v1.2.3", "packageSha256": package_sha, "sourceLockSha256": source_lock_sha,
            },
            "manifest": manifest,
            "hostManifest": host,
            "packagePath": package,
            "evidenceRoot": evidence_root,
            "marketplace": {
                "name": "designcraft", "version": "1.2.3", "tag": "v1.2.3", "packageSha256": package_sha,
            },
            "acceptance": evidence,
        }

    def validate(self, data):
        return release_candidate.validate_release_candidate(
            release=data["release"], manifest=data["manifest"], host_manifest=data["hostManifest"],
            package_path=data["packagePath"], marketplace=data["marketplace"], acceptance=data["acceptance"],
            evidence_root=data["evidenceRoot"],
        )

    def test_matching_package_manifests_market_and_fresh_evidence_pass(self):
        temp, data = self.fixture()
        with temp:
            result = self.validate(data)
        self.assertTrue(result["releaseAllowed"])
        self.assertEqual(result["status"], "PASS")

    def test_version_or_tag_mismatch_is_rejected(self):
        for key, value in (("packageVersion", "1.2.4"), ("packageTag", "v1.2.4")):
            temp, data = self.fixture()
            with temp, self.subTest(field=key):
                data["release"][key] = value
                result = self.validate(data)
            self.assertFalse(result["releaseAllowed"])

    def test_numeric_prerelease_with_leading_zero_is_rejected(self):
        temp, data = self.fixture()
        with temp:
            data["release"]["packageVersion"] = "1.2.3-01"
            data["release"]["packageTag"] = "v1.2.3-01"
            data["manifest"]["version"] = "1.2.3-01"
            data["hostManifest"]["version"] = "1.2.3-01"
            data["marketplace"]["version"] = "1.2.3-01"
            data["marketplace"]["tag"] = "v1.2.3-01"
            result = self.validate(data)
        self.assertFalse(result["releaseAllowed"])

    def test_boolean_schema_version_is_not_accepted_as_integer_one(self):
        temp, data = self.fixture()
        with temp:
            data["release"]["schemaVersion"] = True
            result = self.validate(data)
        self.assertFalse(result["releaseAllowed"])
        self.assertIn("release_record_invalid", result["errors"])

    def test_package_digest_and_host_manifest_mismatch_are_rejected(self):
        mutations = (
            lambda data: data["release"].update(packageSha256="0" * 64),
            lambda data: data["hostManifest"].update(version="1.2.4"),
        )
        for mutate in mutations:
            temp, data = self.fixture()
            with temp:
                mutate(data)
                result = self.validate(data)
            self.assertFalse(result["releaseAllowed"])

    def test_marketplace_mismatch_and_missing_release_evidence_are_rejected(self):
        for mutate in (
            lambda data: data["marketplace"].update(packageSha256="0" * 64),
            lambda data: data["acceptance"].pop("hostDiscovery"),
        ):
            temp, data = self.fixture()
            with temp:
                mutate(data)
                result = self.validate(data)
            self.assertFalse(result["releaseAllowed"])

    def test_stale_acceptance_bound_to_an_older_package_is_rejected(self):
        temp, data = self.fixture()
        with temp:
            evidence_file = data["evidenceRoot"] / "nativeRuntime.json"
            report = json.loads(evidence_file.read_text())
            report["candidatePackageSha256"] = "c" * 64
            report_bytes = json.dumps(report, sort_keys=True).encode("utf-8")
            evidence_file.write_bytes(report_bytes)
            data["acceptance"]["nativeRuntime"]["reportSha256"] = hashlib.sha256(report_bytes).hexdigest()
            result = self.validate(data)
        self.assertFalse(result["releaseAllowed"])
        self.assertIn("acceptance_evidence_stale:nativeRuntime", result["errors"])

    def test_forged_status_without_matching_report_is_rejected(self):
        temp, data = self.fixture()
        with temp:
            (data["evidenceRoot"] / "hostDiscovery.json").write_text('{"status":"NOT_RUN"}')
            result = self.validate(data)
        self.assertFalse(result["releaseAllowed"])

    def test_evidence_path_escape_is_rejected(self):
        temp, data = self.fixture()
        with temp:
            data["acceptance"]["ci"]["reportPath"] = "../outside.json"
            result = self.validate(data)
        self.assertFalse(result["releaseAllowed"])
        self.assertIn("acceptance_report_path_invalid:ci", result["errors"])

    def test_report_from_another_acceptance_layer_cannot_be_reused(self):
        temp, data = self.fixture()
        with temp:
            report = data["evidenceRoot"] / "hostDiscovery.json"
            data["acceptance"]["ci"]["reportPath"] = "hostDiscovery.json"
            data["acceptance"]["ci"]["reportSha256"] = hashlib.sha256(report.read_bytes()).hexdigest()
            result = self.validate(data)
        self.assertFalse(result["releaseAllowed"])
        self.assertIn("acceptance_report_layer_mismatch:ci", result["errors"])

    def test_source_release_evidence_must_bind_current_source_lock(self):
        temp, data = self.fixture()
        with temp:
            data["release"]["sourceLockSha256"] = "c" * 64
            result = self.validate(data)
        self.assertFalse(result["releaseAllowed"])
        self.assertIn("acceptance_source_lock_report_mismatch", result["errors"])


if __name__ == "__main__":
    unittest.main()
