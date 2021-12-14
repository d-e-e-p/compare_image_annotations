# 
# Makefile for compare_image_annotations 
#

clean:
	echo TODO

test:
	./compare_image_annotations.py --img tests/data1/img/ --out tests/data1/out/ --xml tests/data1/xml/* --verbose

build:
	pyinstaller --clean compare_image_annotations.spec


package:
	echo TODO

.PHONY: all
