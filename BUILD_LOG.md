# BUILD_LOG — splatmaker-mcp NSIS installer (running record)

## 2026-11-01 — v0.3.0 NSIS build (in progress)

### Phase 1 audit (TAURI_PRODUCTION_PITFALLS.md A–J) before building

- [x] **A ports/naming.** Side-by-side violation FOUND and fixed: backend.rs, CSP, and Tauri `API_BASE` all pointed at the dev backend port 11091 (installed app would kill/fight the dev backend). Claimed `splatmaker-native` pair via `claim_ports.py --apply` (frontend 11258, operator backend **11259**); baked 11259 into backend.rs `BACKEND_PORT`, `api.ts` `IN_TAURI` URL, tauri.conf CSP. Bundle id `com.sandraschi.splatmaker-mcp` stable. Fleet-lock NEW error is pre-existing autohotkey drift, unrelated.
- [x] **B frontend prod API.** `API_BASE` absolute to 11259 in Tauri, same-origin (Vite proxy) in dev. No relative `fetch('/api/...')` — all calls go through the `API_BASE`-prefixed helper (audited). tauri.conf CSP includes 11259. Window label `main` matches capabilities/default.json. `dist/` has no proxy — verified via build Step 0 gate (new).
- [x] **C backend CORS.** Explicit origins (dev ports, Tauri schemes) + unconditional LAN/Tailscale regex (pre-existing, kept).
- [x] **D run_server.py.** Frozen-safe: no chdir, `sys._MEIPASS` path insert. Added eager `import mcp.types` + `import _strptime` (frozen-context bootstrap). Entry kept HTTP-only (stdio lives in `__main__`).
- [x] **E PyInstaller spec.** FIXED: `noarchive=False` → `True` (MANDATORY, was a bundle-breaker), `upx=True` → `False`, hiddenimports corrected (`splatmaker_mcp.server` + `__main__`; bogus `.api/.app/.main/.tools` removed; added joserfc×3, cachetools, key_value, beartype, websockets, sqlite3, jwt, jsonschema, _strptime, _datetime, mcp.types), `copy_metadata("fastapi")` removed (not installed — crashed the freeze), `rfc3987_syntax` data files collected + hiddenimports (frozen crash found by the new smoke gate), torch excluded (sidecar = control plane; GPU engine stays in the dev venv — documented limitation, dashboard warning links Help).
- [x] **F backend.rs.** Resolves bundled backend from resources (+flat fallback triage), `MCP_PORT`/`MCP_HOST` envs (matched to what `__main__`/`run_server.py` actually honor — template `PORT`/`HOST` would have been ignored → silent dev-port bind), CREATE_NO_WINDOW, piped stdio + watch threads, operator-port free (port-kill only, no native-image kill so no self-kill risk), TCP health-check loop (30×2s) emitting `backend-status`. Added: log/Ok strings use the const (were hardcoded 11091).
- [x] **G lifecycle.** `main.rs` spawns in setup, kills child on Exit (pre-existing; kept). ExitRequested path: not separately handled — same handler covers Exit; noted, not blocking.
- [x] **H build scripts.** build.ps1 hardened: NEW Step 0 (API_BASE + CSP operator-port gate), bun-first frontend (repo standard), CSS gate wired in, frozen-binary smoke test on :11999 with /api/health assertion (caught the rfc3987 crash), ≥5 MB size gate, .env.example + install-mcp-clients.ps1 vendored into resources/, stale `target/release` shadow cleanup. `just build-native` delegates; added `just cua-nsis-test`.
- [x] **I NSIS hooks.** hooks.nsh kills both exes pre-install/pre-uninstall (pre-existing, kept + verified names match). POSTINSTALL MCP-client registration guarded by installed-file check (script now vendored, so the check passes).
- [x] **J stdio vs Tauri.** `__main__.main()` now honors `MCP_TRANSPORT`/`MCP_PORT` env (added for the MCPB launch check); frozen sidecar runs `run_server.py` (HTTP-only). No isatty hijack in this codebase (no DevNullStdout shim).

### Gaps found and fixed in this pass (not pre-existing compliance)

1. Side-by-side port violation (would have shipped an installer that kills the dev backend).
2. Spec would not freeze at all (`fastapi` metadata crash) and would crash at runtime (`rfc3987_syntax` data, noarchive/upx, wrong hiddenimports).
3. backend.rs env names did not match the Python entry points (silent dev-port bind).
4. No smoke test, no size gate, no Step 0 (all added).

### Build record

- run 1: frontend OK + CSS gate PASS; PyInstaller failed on `copy_metadata("fastapi")` (not installed). Fixed spec.
- run 2: backend.exe 52.3 MB built; smoke harness itself failed (`Start-Process -Environment` is PS7-only, script runs 5.1). Fixed to env-inherit + restore.
- run 3: smoke test caught REAL frozen crash (`rfc3987_syntax/syntax_rfc3987.lark` missing in _MEIPASS). Fixed spec (collect_data_files + hiddenimports).
- run 4: (current) full pipeline from committed tree → NSIS. See below.

### CUA smoke + release

- (pending) `just cua-nsis-test` against the installed app, then uninstall.
- (pending) attach `*-setup.exe` to the v0.3.0 GitHub release.

### Known product limitation (documented, not a defect)

The frozen sidecar excludes torch/CUDA/nerfstudio (GBs, do not freeze sanely — same call the fleet standard makes). The installed app is the full monitor/control plane (jobs, gallery, chat, logs, skills, settings, Inbox) and reports `engine verified: missing` with install guidance when asked to train. Real training stays a dev-venv flow (`just sync-engine` + start.ps1). This is stated in Help, the dashboard banner, and the release notes.
