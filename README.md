> Current candidate: the read-only `show` fix changes Harness executable code. Earlier CI and host/model results are historical; current candidate requalification is pending. Formal release remains gated.

# designcraft plugin — local development project

Six standalone skills are included from `designcraft-skills`, with local snapshot checksums. Unpublished. Host discovery and nine read-only model-routing cases passed on bundled Codex CLI 0.162.0-alpha.2 / gpt-6-astra / macOS arm64. Native execution, full domain workflows and creative acceptance remain open.

Validate: `python3 -I -B scripts/validate_package.py`. Tests: `python3 -I -B -m unittest discover -s tests`.

See [architecture](docs/architecture.md), the [support matrix](docs/support-matrix.zh-CN.md), the [snapshot migration guide](docs/snapshot-maintenance.zh-CN.md), and `project-status.json`. The [OpenSpec change](openspec/changes/harden-designcraft-plugin-delivery/proposal.md) is being implemented. This package has six source-owned skills and one local Harness skill; native, creative and release acceptance remain pending; host discovery and read-only routing passed only for the recorded combination. The development candidate is on the public [GitHub repository](https://github.com/full-aigc-plugins/designcraft-plugin) `main` branch; no version tag, GitHub Release or marketplace release exists.
