# 2026-10-08 evidence binding refresh

Only `openspec/changes/harden-designcraft-plugin-delivery/tasks.md` changed in the tracked product tree between the previous CI/Codex host observations and their metadata refresh. For the retained `host` and `model-dispatch` observations, input and artifact SHA-256 lists were rechecked and match byte-for-byte; plugin version, source lock, runtime lock, native version, and expected binary digest are unchanged. The records retain their original run IDs, timestamps, environments, statuses, and supporting reports. Only `bindings.pluginTreeSha256` was refreshed to cover the current tree. This is a metadata rebind of unchanged observations, not a rerun or new host acceptance. CI was subsequently rerun and recorded separately as GitHub Actions run `37794988545` on commit `3070cd138aa5c8c22b41772f4865dc0c1299aab7`.

Previous plugin tree SHA-256: `eed299503dc6d080d97fedd68322f4757e6ee5b73438b11877edfd776d8ce7c4`
Current plugin tree SHA-256: `d4ac5737f1dc85c30b1fe928e447e4297b7f607dd117a0eadf5618dc7b0e4fc9`
