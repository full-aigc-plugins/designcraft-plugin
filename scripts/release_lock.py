"""分离校验技能源发行锁的本地内容与在线 Git 引用。"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from urllib.parse import urlsplit


NUMERIC = r"(?:0|[1-9][0-9]*)"
NON_NUMERIC = r"(?:[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
PRERELEASE = rf"(?:{NUMERIC}|{NON_NUMERIC})"
SEMVER = re.compile(rf"{NUMERIC}\.{NUMERIC}\.{NUMERIC}(?:-{PRERELEASE}(?:\.{PRERELEASE})*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?")
HEX_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
SHA256 = re.compile(r"[0-9a-f]{64}")


def _valid_repository(value):
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return (parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username and
            not parsed.password and not parsed.query and not parsed.fragment and
            bool(parsed.path.strip("/")) and not value.endswith("/"))


def _canonical_content_digest(files):
    payload = json.dumps(files, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _collect_files(source_root, skill_names):
    root = Path(source_root).resolve()
    skill_root = root / "skills"
    if not skill_root.is_dir() or skill_root.is_symlink():
        raise ValueError("source_skills_directory_missing")
    actual_skills = sorted(path.name for path in skill_root.iterdir() if path.is_dir() and not path.is_symlink())
    if actual_skills != skill_names:
        raise ValueError("source_skill_set_mismatch")
    files = {}
    for skill_name in skill_names:
        base = skill_root / skill_name
        for path in sorted(base.rglob("*")):
            if path.is_symlink():
                raise ValueError("source_file_symlink_rejected")
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def resolve_remote_tag(repository, release_tag, *, runner=subprocess.run, timeout=20):
    """只读查询远端 tag；annotated tag 使用 peeled commit，网络错误不冒充失败或通过。"""
    if not _valid_repository(repository):
        return {"status": "FAIL", "commitSha": None, "errors": ["repository_invalid"]}
    if not isinstance(release_tag, str) or not release_tag.startswith("v") or not SEMVER.fullmatch(release_tag[1:]):
        return {"status": "FAIL", "commitSha": None, "errors": ["release_tag_invalid"]}
    base_ref = f"refs/tags/{release_tag}"
    try:
        completed = runner(
            ["git", "ls-remote", "--exit-code", repository, base_ref, f"{base_ref}^{{}}"],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "NOT_VERIFIED_NETWORK_UNAVAILABLE", "commitSha": None, "errors": ["git_ls_remote_unavailable"]}
    if completed.returncode == 2:
        return {"status": "FAIL", "commitSha": None, "errors": ["release_tag_not_found"]}
    if completed.returncode != 0:
        return {"status": "NOT_VERIFIED_NETWORK_UNAVAILABLE", "commitSha": None, "errors": ["git_ls_remote_failed"]}
    refs = {}
    for line in completed.stdout.splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2 or not HEX_SHA.fullmatch(parts[0]):
            return {"status": "FAIL", "commitSha": None, "errors": ["git_ls_remote_response_invalid"]}
        refs[parts[1]] = parts[0]
    commit = refs.get(f"{base_ref}^{{}}", refs.get(base_ref))
    if commit is None:
        return {"status": "FAIL", "commitSha": None, "errors": ["release_tag_not_found"]}
    return {"status": "PASS", "commitSha": commit, "errors": []}


def verify_release_lock(lock, source_root, *, trusted_repository=None,
                        resolved_repository=None, resolved_commit=None, network_error=None):
    """返回分层结果；只有本地内容、受信仓库和在线 tag 解析全部匹配才允许发行。"""
    errors = []
    offline_errors = []
    required = {"schemaVersion", "repository", "releaseTag", "commitSha", "sourceVersion", "skills", "files", "contentSha256"}
    if not isinstance(lock, dict) or set(lock) != required:
        offline_errors.append("release_lock_schema_invalid")
    else:
        if type(lock.get("schemaVersion")) is not int or lock["schemaVersion"] != 1:
            offline_errors.append("release_lock_schema_invalid")
        if not _valid_repository(lock.get("repository")):
            offline_errors.append("repository_invalid")
        if trusted_repository is None:
            offline_errors.append("trusted_repository_missing")
        elif not _valid_repository(trusted_repository) or lock.get("repository") != trusted_repository:
            offline_errors.append("trusted_repository_mismatch")
        if not isinstance(lock.get("releaseTag"), str) or not lock["releaseTag"].startswith("v") or not SEMVER.fullmatch(lock["releaseTag"][1:]):
            offline_errors.append("release_tag_invalid")
        if not isinstance(lock.get("sourceVersion"), str) or not SEMVER.fullmatch(lock["sourceVersion"]):
            offline_errors.append("source_version_invalid")
        if not isinstance(lock.get("commitSha"), str) or not HEX_SHA.fullmatch(lock["commitSha"]):
            offline_errors.append("commit_sha_invalid")
        if isinstance(lock.get("releaseTag"), str) and isinstance(lock.get("sourceVersion"), str) and lock["releaseTag"].startswith("v") and lock["releaseTag"][1:] != lock["sourceVersion"]:
            offline_errors.append("tag_source_version_mismatch")
        skills = lock.get("skills")
        if (not isinstance(skills, list) or not skills or any(not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) for name in skills)
                or skills != sorted(set(skills))):
            offline_errors.append("release_lock_skills_invalid")
        files = lock.get("files")
        if not isinstance(files, dict) or not files or any(not isinstance(name, str) or not isinstance(digest, str) or not SHA256.fullmatch(digest) for name, digest in files.items()):
            offline_errors.append("release_lock_files_invalid")
        else:
            for name in files:
                relative = PurePosixPath(name)
                if relative.is_absolute() or ".." in relative.parts or len(relative.parts) < 3 or relative.parts[0] != "skills" or relative.parts[1] not in (skills if isinstance(skills, list) else []):
                    offline_errors.append("release_lock_file_path_invalid")
                    break
            if not isinstance(lock.get("contentSha256"), str) or not SHA256.fullmatch(lock["contentSha256"]):
                offline_errors.append("content_digest_invalid")
            elif _canonical_content_digest(files) != lock["contentSha256"]:
                offline_errors.append("content_digest_mismatch")
            if not offline_errors:
                try:
                    actual = _collect_files(source_root, skills)
                except (OSError, ValueError) as error:
                    offline_errors.append(str(error))
                else:
                    if actual != files:
                        offline_errors.append("source_file_manifest_mismatch")

    offline_status = "PASS" if not offline_errors else "FAIL"
    if network_error:
        online_status = "NOT_VERIFIED_NETWORK_UNAVAILABLE"
    elif resolved_repository is None and resolved_commit is None:
        online_status = "NOT_RUN"
    elif resolved_repository is None or resolved_commit is None:
        online_status = "FAIL"
        errors.append("online_resolution_incomplete")
    elif not isinstance(lock, dict) or resolved_repository != lock.get("repository"):
        online_status = "FAIL"
        errors.append("resolved_repository_mismatch")
    elif resolved_commit != lock.get("commitSha"):
        online_status = "FAIL"
        errors.append("resolved_commit_mismatch")
    else:
        online_status = "PASS"

    errors = list(dict.fromkeys(offline_errors + errors))
    return {
        "offlineStatus": offline_status,
        "onlineStatus": online_status,
        "errors": errors,
        "releaseAllowed": offline_status == "PASS" and online_status == "PASS",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--trusted-repository", required=True)
    parser.add_argument("--resolve-online", action="store_true", help="使用 git ls-remote 只读解析锁定 tag")
    parser.add_argument("--resolved-repository")
    parser.add_argument("--resolved-commit")
    parser.add_argument("--network-error")
    args = parser.parse_args()
    try:
        lock = json.loads(args.lock.read_text(encoding="utf-8"))
        resolution = None
        if args.resolve_online:
            repository = lock.get("repository") if isinstance(lock, dict) else None
            release_tag = lock.get("releaseTag") if isinstance(lock, dict) else None
            resolution = resolve_remote_tag(repository, release_tag)
            if resolution["status"] == "PASS":
                resolved_repository = repository
                resolved_commit = resolution["commitSha"]
                network_error = None
            elif resolution["status"] == "NOT_VERIFIED_NETWORK_UNAVAILABLE":
                resolved_repository = resolved_commit = None
                network_error = resolution["errors"][0]
            else:
                resolved_repository = repository
                resolved_commit = None
                network_error = None
        result = verify_release_lock(
            lock, args.source_root, trusted_repository=args.trusted_repository,
            resolved_repository=args.resolved_repository if resolution is None else resolved_repository,
            resolved_commit=args.resolved_commit if resolution is None else resolved_commit,
            network_error=args.network_error if resolution is None else network_error,
        )
        if resolution is not None:
            result["errors"] = list(dict.fromkeys(result["errors"] + resolution["errors"]))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        result = {"offlineStatus": "FAIL", "onlineStatus": "NOT_RUN", "errors": [str(error)], "releaseAllowed": False}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["releaseAllowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
