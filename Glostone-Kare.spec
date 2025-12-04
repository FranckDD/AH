# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\ahlogo.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\appel-durgence.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\appel.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\battement-de-coeur.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\calendrier.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\custom_ctk.json', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\du-sang.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\echelle-de-poids.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\eye-off.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\eye.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\glostone-kare.ico', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\glostone-kare.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\images.jpeg', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\logo_dark.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\logo_light.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\machine.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\medical (1).png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\medical.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\seringue.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\theme.json', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\tube-a-essai.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\urgence.png', 'assets'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\gk_for_installation\\gk1.bmp', 'assets\\gk_for_installation'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\gk_for_installation\\gk2.bmp', 'assets\\gk_for_installation'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\gk_for_installation\\gk3.bmp', 'assets\\gk_for_installation'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\gk_for_installation\\gk4.bmp', 'assets\\gk_for_installation'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\gk_for_installation\\gk5.bmp', 'assets\\gk_for_installation'), ('c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\offline.db', '.')]
binaries = []
hiddenimports = ['sqlalchemy', 'psycopg2', 'redis', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'requests', 'jose', 'dotenv', 'passlib', 'passlib.handlers.bcrypt', 'bcrypt', 'view_pyqt6.*', 'controllers.*', 'repositories.*', 'managers.*', 'api_backend.backend_app.gateway', 'controller.controller_offline.auth_controller_offline', 'controller.controller_offline.auth_controller_factory', 'repositories.repo_offline.*']
tmp_ret = collect_all('view_pyqt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('controllers')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('repositories')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('managers')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('api_backend.backend_app.gateway')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main_pyqt.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='Glostone-Kare',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['c:\\Users\\DD\\Desktop\\Project Stage\\ah2_v2\\AH2\\assets\\glostone-kare.ico'],
)
