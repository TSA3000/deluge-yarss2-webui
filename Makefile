
cleanpyc:
	-find . -name "*.pyc" -delete
	-find . -name __pycache__ -exec rm -rf {} \;

buildegg: cleanpyc
	python setup.py bdist_egg
