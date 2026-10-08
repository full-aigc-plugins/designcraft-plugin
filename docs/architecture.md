# Local delivery architecture

The independently maintained skills are the source. Each skill includes its own pinned CLI bootstrap, public argv launcher, command catalog gateway and runtime lock. A local plugin snapshot carries checksums for those skill files. It is unpublished; it must not enter the marketplace until source release pinning and host acceptance pass.

```mermaid
flowchart LR
 H[Host skill discovery: pending] --> S[Loaded standalone skill]
 S --> B[Checksummed bootstrap]
 B --> N[Pinned native CLI: execution pending]
 S --> Q[Live catalog and plan validation]
 Q --> N
 N --> A[Native projects and exports: acceptance pending]
 A --> R[Reopen and targeted revision: acceptance pending]
```

PrintCraft supplies JSON Schema. LightCraft and DesignCraft supply parameter guidance text; it must not be promoted to machine-checked schema. Plans execute in one native process. Timeouts remain unknown and never trigger automatic replay. Zero exit requires artifact inspection and creative review. Installation, host discovery, model selection and final output are separate acceptance gates.

The [OpenSpec optimization change](../openspec/changes/harden-designcraft-plugin-delivery/proposal.md) is specified and validated, with implementation tasks still open. The development candidate is available from the public [GitHub repository](https://github.com/full-aigc-plugins/designcraft-plugin) on `main`; no version tag, GitHub Release or marketplace release exists. Native installation has not been run and requires applicable authorization. Existing five plugin specifications remain authoritative for their domains; shared ArtCraft integration for these three domains is still pending.


Runtime preflight now binds the release tag and archive name to the locked binary identity and version, rejecting mismatches before runtime creation. The pinned releases remain 0.2.1.
