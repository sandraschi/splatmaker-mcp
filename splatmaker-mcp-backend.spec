# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for splatmaker-mcp backend sidecar."""

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

pkg_name = "splatmaker_mcp"

datas = [(f"src/splatmaker_mcp", "splatmaker_mcp")]
for pkg in (
    "fastmcp",
    "uvicorn",
    "pydantic",
    "starlette",
    "httpx",
):
    datas += copy_metadata(pkg)
# jsonschema format deps ship data files PyInstaller misses by default
# (frozen crash: rfc3987_syntax/syntax_rfc3987.lark not found in _MEIPASS).
datas += collect_data_files("rfc3987_syntax")

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "splatmaker_mcp.server",
    "splatmaker_mcp.__main__",
    # FastMCP 3.4+ JWT (authlib -> joserfc migration; frozen auth fails silently without these)
    "joserfc",
    "joserfc.jwk",
    "joserfc.jwt",
    # FastMCP chain + common extras (calibre parity)
    "cachetools",
    "key_value",
    "beartype",
    "websockets",
    "sqlite3",
    "jwt",
    "jsonschema",
    # stdlib C extensions (lazy imports break in onefile without eager hiddenimports)
    "_strptime",
    "_datetime",
    # mcp bootstrap before fastmcp touches it (see run_server.py eager import)
    "mcp.types",
    # jsonschema format stack (data files collected above; modules explicit)
    "rfc3987_syntax",
    "lark",
]

a = Analysis(
    ["run_server.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # torch excluded deliberately: the frozen sidecar is the control plane
    # (jobs/chat/logs/status). The GPU engine (torch+CUDA+nerfstudio, GBs, CUDA
    # DLLs that do not freeze sanely) stays in the dev venv via
    # `uv sync --extra engine`; generation from the installed app honestly
    # reports engine missing with install guidance. See Help page + release notes.
    excludes=[
        "tkinter",
        "matplotlib",
        "pandas",
        "scipy",
        "torch",
        "tensorflow",
        "playwright",
        "bitsandbytes",
        "llvmlite",
        "pyarrow",
        "pymupdf",
        "grpc",
        "numba",
        "Cython",
        "google",
        "azure",
        "boto3",
        "botocore",
        "PIL",
        "sklearn",
        "onnxruntime",
    ],
    # noarchive=True is MANDATORY: the PYZ importer is unreliable for
    # disk-extracted datas in onefile mode (difflib/statistics/pydoc class).
    noarchive=True,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="splatmaker-mcp-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # upx=False: UPX binaries do not exist on Windows and tripped-up builds
    # either fail or trigger AV on large ML-adjacent stacks.
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
