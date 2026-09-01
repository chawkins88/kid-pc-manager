# PyInstaller spec — build on Windows: pyinstaller install/windows/device-policy-agent.spec
# Output: dist/DevicePolicyHost/DevicePolicyHost.exe

import sys
from pathlib import Path

repo_root = Path(SPECPATH).resolve().parents[1]

block_cipher = None

a = Analysis(
    [str(repo_root / "agent" / "main.py")],
    pathex=[str(repo_root)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "agent.platform.windows",
        "agent.platform.linux",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "uvicorn.importer",
        "uvicorn._subprocess",
        "anyio._backends._asyncio",
        "psutil._psutil_windows" if sys.platform == "win32" else "psutil._psutil_linux",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["control_plane"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DevicePolicyHost",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # keep console for service logging via NSSM stdout redirect
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DevicePolicyHost",
)
