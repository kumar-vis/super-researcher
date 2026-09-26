# Changelog

## 0.2.0 — 2026-09-26

First public release.

- Local-first research pipeline: protocol → discovery → corpus → Atlas → publish, served by a dependency-free Python HTTP server with a vanilla-JS UI.
- Configurable Codex binary (`CODEX_BIN` env, PATH lookup, legacy .app fallback), storage root (`SUPERRESEARCHER_STORAGE_ROOT`), and keys file (`SUPERRESEARCHER_API_KEYS`).
- `superresearcher` console entry point (`superresearcher --host/--port/--version`) and `pyproject.toml` packaging; core remains 100% stdlib.
- Secrets hygiene: `api_keys.txt` git-ignored, `api_keys.example.txt` template.
- Version alignment across package, server banner, and HTTP user agents.
- 80 unit tests passing.
