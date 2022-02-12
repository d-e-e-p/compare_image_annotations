# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


import datetime

bd = datetime.datetime.now()
auth = "deep@tensorfield.ag"
vers = "2.0"

# Write version info into _constants.py resource file
with open('lib/constants.py', 'w') as f:
    f.write(f'VERSION    = "{vers}"\n')
    f.write(f'BUILD_DATE = "{bd}"  \n')
    f.write(f'AUTHOR     = "{auth}"\n')




a = Analysis(['compare_image_annotations.py'],
             pathex=[],
             binaries=[],
             datas=[('resources/fonts', 'resources/fonts'), ('resources/json', 'resources/json')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='compare_image_annotations',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True , icon='resources/icons/tf.ico')
