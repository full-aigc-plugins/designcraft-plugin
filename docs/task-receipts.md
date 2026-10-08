# Input identity and execution receipts

`commands.py run --input PATH` explicitly registers files or directories to preserve. DesignCraft --source and LightCraft --import inputs are also registered. Missing inputs, symlinks and special entries are rejected. Directories are limited to 100000 entries. Paths hidden inside native parameters are not automatically registered; this is evidence capture, not a filesystem sandbox.

The gateway captures plan, explicit input, runtime-lock and skill-resource identities before live catalog discovery, and rechecks inputs/resources before edits. STARTED receipts use same-directory staging, file fsync and atomic replacement. A single native session executes the plan. Exit status, partial timeout logs and post-execution identities are preserved.

NATIVE_EXIT_ZERO_REVIEW_REQUIRED still requires actual artifact, project-reopen and creative checks. FAILED_OR_PARTIAL may have side effects. UNKNOWN preserves ambiguity and forbids automatic replay. Input or skill changes after zero exit require review and return failure. Post-execution checks do not roll back writes or prove all descendant processes stopped. Unknown-worker takeover, distributed leases and full transaction recovery remain open.

`scripts/sync_local_snapshot.py` updates only a matching unpublished local plugin after verifying old snapshot hashes. Modified user snapshots, published source identities and source removals are rejected. It does not establish a release, install tools, initialize Git or adopt a specification system.

Only mocked subprocess and temporary-copy behavior has been tested; real native, host, model-dispatch and creative acceptance remain pending.

## Native parameter schema boundary

PrintCraft checks the entire schema definition before validating a parameter value. Unsupported constraints in unselected combinator branches, absent optional properties, items and additionalProperties are refused; invalid definitions cannot be swallowed as branch mismatches. Boolean schemas are supported; enum/const compare JSON numbers by value while keeping booleans distinct. Patterns use Python semantics; this is not a complete JSON Schema validator.

The JSON reader rejects explicit NaN/Infinity and exponent overflow such as 1e10000, including native-only LightCraft/DesignCraft plans. Their textual parameter guidance remains native-only; successful structural checks do not establish native execution or state validity.
