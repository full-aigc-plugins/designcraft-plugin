"""只读校验插件发行元数据、包摘要、市场引用和当前验收证据。"""
import argparse
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
import re

NUMERIC = r"(?:0|[1-9][0-9]*)"
NON_NUMERIC = r"(?:[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
PRERELEASE = rf"(?:{NUMERIC}|{NON_NUMERIC})"
SEMVER = re.compile(rf"{NUMERIC}\.{NUMERIC}\.{NUMERIC}(?:-{PRERELEASE}(?:\.{PRERELEASE})*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?")
SHA256 = re.compile(r"[0-9a-f]{64}")
REQUIRED_EVIDENCE = ("sourceRelease", "ci", "nativeRuntime", "hostDiscovery", "modelDispatch", "creativeAcceptance")


def validate_release_candidate(*, release, manifest, host_manifest, package_path, marketplace, acceptance, evidence_root):
    """比较所有发行身份与当前候选摘要；本函数不创建、提交或发布任何产物。"""
    errors = []
    if not isinstance(release, dict) or set(release) != {
        "schemaVersion", "packageName", "packageVersion", "packageTag", "packageSha256", "sourceLockSha256",
    } or type(release.get("schemaVersion")) is not int or release.get("schemaVersion") != 1:
        errors.append("release_record_invalid")
        release = release if isinstance(release, dict) else {}

    name = release.get("packageName")
    version = release.get("packageVersion")
    tag = release.get("packageTag")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        errors.append("package_name_invalid")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        errors.append("package_version_invalid")
    if not isinstance(tag, str) or not tag.startswith("v") or not SEMVER.fullmatch(tag[1:]) or (isinstance(version, str) and tag != f"v{version}"):
        errors.append("package_tag_version_mismatch")

    package = Path(package_path)
    if package.is_symlink() or not package.is_file():
        package_sha = None
        errors.append("package_artifact_missing_or_unsafe")
    else:
        package_sha = hashlib.sha256(package.read_bytes()).hexdigest()
    if not isinstance(release.get("packageSha256"), str) or not SHA256.fullmatch(release["packageSha256"]) or release["packageSha256"] != package_sha:
        errors.append("package_digest_mismatch")
    if not isinstance(release.get("sourceLockSha256"), str) or not SHA256.fullmatch(release["sourceLockSha256"]):
        errors.append("source_lock_digest_invalid")

    for label, value in (("portable", manifest), ("host", host_manifest)):
        if not isinstance(value, dict) or value.get("name") != name or value.get("version") != version:
            errors.append(f"{label}_manifest_identity_mismatch")

    expected_market = {"name": name, "version": version, "tag": tag, "packageSha256": package_sha}
    if not isinstance(marketplace, dict) or any(marketplace.get(key) != value for key, value in expected_market.items()):
        errors.append("marketplace_reference_mismatch")

    if not isinstance(acceptance, dict):
        errors.append("acceptance_evidence_missing")
        acceptance = {}
    evidence_base = Path(evidence_root).resolve()
    for layer in REQUIRED_EVIDENCE:
        record = acceptance.get(layer)
        if not isinstance(record, dict):
            errors.append(f"acceptance_evidence_missing_or_not_pass:{layer}")
            continue
        report_path = record.get("reportPath")
        if not isinstance(report_path, str):
            errors.append(f"acceptance_report_path_invalid:{layer}")
            continue
        relative = PurePosixPath(report_path)
        if relative.is_absolute() or ".." in relative.parts or "\\" in report_path:
            errors.append(f"acceptance_report_path_invalid:{layer}")
            continue
        candidate = evidence_base.joinpath(*relative.parts)
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(evidence_base)
            if candidate.is_symlink() or not candidate.is_file():
                raise ValueError("unsafe_report")
            report_bytes = candidate.read_bytes()
            report = json.loads(report_bytes)
        except (OSError, ValueError, json.JSONDecodeError):
            errors.append(f"acceptance_report_unavailable_or_unsafe:{layer}")
            continue
        actual_report_sha = hashlib.sha256(report_bytes).hexdigest()
        if not isinstance(record.get("reportSha256"), str) or not SHA256.fullmatch(record["reportSha256"]):
            errors.append(f"acceptance_report_digest_invalid:{layer}")
        elif record["reportSha256"] != actual_report_sha:
            errors.append(f"acceptance_report_digest_mismatch:{layer}")
        if not isinstance(report, dict) or report.get("status") != "PASS":
            errors.append(f"acceptance_evidence_missing_or_not_pass:{layer}")
            continue
        if report.get("layer") != layer:
            errors.append(f"acceptance_report_layer_mismatch:{layer}")
        if report.get("candidatePackageSha256") != package_sha:
            errors.append(f"acceptance_evidence_stale:{layer}")
        if layer == "sourceRelease" and report.get("sourceLockSha256") != release.get("sourceLockSha256"):
            errors.append("acceptance_source_lock_report_mismatch")

    errors = list(dict.fromkeys(errors))
    return {
        "status": "PASS" if not errors else "FAIL",
        "packageSha256": package_sha,
        "errors": errors,
        "releaseAllowed": not errors,
    }


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--host-manifest", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--marketplace", required=True, type=Path)
    parser.add_argument("--acceptance", required=True, type=Path)
    parser.add_argument("--evidence-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = validate_release_candidate(
            release=_read_json(args.release), manifest=_read_json(args.manifest),
            host_manifest=_read_json(args.host_manifest), package_path=args.package,
            marketplace=_read_json(args.marketplace), acceptance=_read_json(args.acceptance),
            evidence_root=args.evidence_root,
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        result = {"status": "FAIL", "packageSha256": None, "errors": [str(error)], "releaseAllowed": False}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["releaseAllowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
