# -*- mode: python ; coding: utf-8 -*-

block_cipher = None




a = Analysis(['compare_image_annotations.py'],
             pathex=['.'],
             binaries=[],
             datas=[],
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
          console=True )



a.datas += [('C:\\Users\\deep\\.conda\\envs\\compare_image_annotations\\lib\\site-packages\\palettable\\colorbrewer\\data\\colorbrewer_all_schemes.csv', 'palettable\\colorbrewer\\data'), ('C:\\Users\\deep\\.conda\\envs\\compare_image_annotations\\lib\\site-packages\\palettable\\colorbrewer\\data\\colorbrewer_all_schemes.json', 'palettable\\colorbrewer\\data'), ('C:\\Users\\deep\\.conda\\envs\\compare_image_annotations\\lib\\site-packages\\palettable\\colorbrewer\\data\\colorbrewer_licence.txt', 'palettable\\colorbrewer\\data')]


