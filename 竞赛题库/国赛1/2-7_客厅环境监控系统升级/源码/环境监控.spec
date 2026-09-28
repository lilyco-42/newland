# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/源码/2-7_客厅环境监控/环境监控.py'],
    pathex=[],
    binaries=[],
    datas=[('D:/源码/2-7_客厅环境监控/images', 'images'), ('D:/源码/2-7_客厅环境监控/KRoom.txt', '.'), ('D:/源码/2-7_客厅环境监控/nle_cloud.py', '.'), ('D:/源码/2-7_客厅环境监控/make_images.py', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='环境监控',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
