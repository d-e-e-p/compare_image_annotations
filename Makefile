# 
# Makefile for compare_image_annotations 
#

clean:
	echo TODO

test:
	./compare_image_annotations.py --img tests/data1/img/ --out tests/data1/out/ --xml tests/data1/xml/* --verbose

install:
	pyinstaller --clean compare_image_annotations.spec
	cp -ipv dist/compare_image_annotations.exe '/g/.shortcut-targets-by-id/1_l2-tZ-8N-upGop5x8ICLbikmWLG95Ej/CWs Labelling Consistency/compare_image_annotations.exe'


package:
	echo TODO

.PHONY: all
