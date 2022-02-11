# 
# Makefile for compare_image_annotations 
#
.ONESHELL: # Applies to every targets in the file!

clean:
	echo TODO

test:
	pyside6-rcc -o libs/resources.py resources.qrc
	./compare_image_annotations.py --img tests/data1/img/ --out tests/data1/out/ --xml tests/data1/xml/* --verbose

install:
	pyside6-rcc -o libs/resources.py resources.qrc
	pyinstaller --clean compare_image_annotations.spec
	echo cp -ipv dist/compare_image_annotations.exe  /g/Shared\ drives/ML/CloudFactory/TF\ CF\ Share/programs/



package:
	echo TODO

.PHONY: all
