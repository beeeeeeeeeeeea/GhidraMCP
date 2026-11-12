# AGENTS.md

ghidraMCP is two halves: a Python MCP server (`ghidra-mcp`) and a Java Ghidra extension. In GUI mode Python never calls Ghidra APIs; it sends loopback HTTP requests to the extension. Headless mode loads Ghidra in-process via PyGhidra but still serves the same Java HTTP backend.

## Architecture

- `src/ghidra_mcp/` — MCP side: `cli.py` (startup, GUI vs headless), `server.py` (FastMCP tools), `backend.py` (HTTP client/envelope), `headless.py` (PyGhidra/JVM lifecycle).
- `extension/src/main/java/com/lauriewired/` — `GhidraMCPPlugin` (GUI) and `HeadlessBackend` both construct `BackendHttpServer`, which routes to `GhidraAnalysisService`. All Ghidra analysis/annotation logic belongs there, not in the plugin or Python.
- Adding or changing a tool touches three layers: a method in `GhidraAnalysisService`, a route in `BackendHttpServer.registerRoutes()`, and a `@mcp.tool()` in `server.py`.
- Mutations must go through `GhidraAnalysisService.write()` (opens a Ghidra transaction and routes to the Swing thread in GUI mode). List endpoints must use `Page.Builder`/`Page.of`; `Page.MAX_LIMIT` is 2000 and pagination counts all matches while materializing only the requested window.
- Wire format is `{success:true,data:...}` or `{success:false,error:{code,message}}`. `backend.py` raises `BackendError`, `server.py` converts it to `ToolError("[CODE] message")`. POST params are form-encoded; GET params are query args; `None` params are dropped. Error codes are the stable contract (`McpException`).
- `bridge_mcp_ghidra.py` is a legacy shim that must keep working; it is shipped in releases.
- `get_current_address`/`get_current_function` are registered only when `/health` reports `gui_context`. If the backend is unreachable at startup, capabilities are `None` and every tool is registered.

## Commands

- Run server: `uv run ghidra-mcp` (GUI mode expects Ghidra + the extension on `127.0.0.1:8080`).
- Unit tests (no Ghidra needed): `uv run pytest`; single test: `uv run pytest tests/test_backend.py::test_unreachable_backend`.
- Full CI test command: `uv run --extra headless pytest -v`.
- Build extension (Java 21, Ghidra 12.1.4):
  `export GHIDRA_INSTALL_DIR=/path/to/ghidra_12.1.4_PUBLIC` then
  `cd extension && $GHIDRA_INSTALL_DIR/support/gradle/gradlew buildExtension`.
  CI uses Gradle 8.14 and plain `gradle buildExtension`. Output: `extension/dist/*.zip`, jar at `extension/build/libs/GhidraMCP.jar`.
- Any Java change requires rebuilding the extension before headless runs or packaging pick it up.

## Testing quirks

- `tests/test_headless_integration.py` is skipped unless `GHIDRA_INSTALL_DIR` is set **and** `extension/build/libs/GhidraMCP.jar` exists (or `GHIDRA_MCP_EXTENSION_JAR` points at one). It exercises both ELF and PE fixtures.
- The stdio subprocess test is skipped on Windows. Don't "fix" it by relaxing the POSIX-path assumption.
- Unit tests use `fake_backend` from `tests/conftest.py`; prefer it over a real Ghidra for backend/server tests. The fake backend only understands the documented envelope.
- To change integration fixtures, edit `tests/fixtures/sample.c` and run `tests/fixtures/build_fixtures.sh` (uses zig via `uvx`, no system compiler needed). Tests expect symbols like `add_numbers`, `mul_numbers`, `compute`, `checksum` and the `fixture-secret` string.
- The backend is loopback-only and returns 403 for requests with an `Origin` header or a non-loopback `Host`; tests assert this and GET on a POST route returns 405.
- Backend read timeout defaults to 90 s and must stay above `GhidraAnalysisService.DECOMPILE_TIMEOUT_SECONDS` (60 s).
- Headless stdio redirects fd 1 to stderr so JVM output can't corrupt MCP framing. Never `print()` on the stdio path; log to stderr.

## Constraints

- Ghidra **12.1.4** and Java 21 are pinned in the README and CI. Python requires >=3.10; `.python-version` is 3.13; PyGhidra supports 3.10–3.13.
- Ghidra project APIs hang if called off the thread that started the JVM. `HeadlessSession.start/load/run/close` must stay on the main thread; the MCP server runs on another thread and only calls `request_stop()`. Don't move Ghidra work into the MCP thread.
- Version `2.0.0` is duplicated in `pyproject.toml`, `src/ghidra_mcp/__init__.py`, and `BackendHttpServer.VERSION`; bump all three together.
- Do not commit Gradle output (`extension/build`, `extension/dist`, `extension/lib`, `.gradle`) or Ghidra projects (`*.gpr`, `*.rep/`); see `.gitignore`.
