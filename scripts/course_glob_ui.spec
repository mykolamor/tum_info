# -*- mode: python ; coding: utf-8 -*-
import sys

block_cipher = None


if sys.platform.startswith('darwin'):
    a = Analysis(
        ['course_glob_ui.py'],
        pathex=[],
        binaries=[],
        datas=[('../assets/icons/grade.ico', 'assets/icons/')],
        hiddenimports=[],
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        win_no_prefer_redirects=False,
        win_private_assemblies=False,
        cipher=block_cipher,
        noarchive=False,
    )
    pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Grades',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
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
        name='Grades',
    )
    app = BUNDLE(
        coll,
        name='Grades.app',
        icon='../assets/icons/grade.icns',
        bundle_identifier='mykolamor.tum_info.grades',
    )
elif sys.platform.startswith('win32') or sys.platform.startswith('cygwin') or sys.platform.startswith('linux'):
    a = Analysis(
        ['course_glob_ui.py'],
        pathex=[],
        binaries=[],
        datas=[('../assets/icons/grade.ico', 'assets/icons/')],
        hiddenimports=[],
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        win_no_prefer_redirects=False,
        win_private_assemblies=False,
        cipher=block_cipher,
        noarchive=False,
    )
    pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='Grades',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        icon='../assets/icons/grade.ico',
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
else:
    print('Unsupported system {}.'.format(sys.platform))