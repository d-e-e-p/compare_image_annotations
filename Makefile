# 
# Makefile for compare_image_annotations 
#

clean:
	echo TODO

test:
	./compare_image_annotations.py --img tests/data/img/ --out tests/data/out/ --xml tests/data/xml/* --verbose


package:
	echo TODO

.PHONY: all
