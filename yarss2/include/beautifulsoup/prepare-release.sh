# A script to automatically create and test source and wheel
# distributions of Beautiful Soup.

# Recommend you run these steps one at a time rather than just running
# the script.

# If you screwed up on the test server and have to create a "a" or "b"
# release the second time, add the '--pre' argument to pip install to
# find the 'prerelease'.

# Make sure tests pass
./test-all-versions

rm -rf build dist

# Run this in a Python 2 env and a Python 3 env to make both sdist and
# wheels.
python setup.py sdist bdist_wheel

# Run this in Python 3 env.
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
twine upload dist/*

# Old instructions:


# Create the 2.x source distro and wheel
python setup.py sdist bdist_wheel

# Upload the 2.x source distro and wheel to pypi test
# python setup.py register -r test
python setup.py sdist bdist_wheel upload -r test

# Try 2.x install from pypi test
rm -rf ../py2-install-test-virtualenv
virtualenv -p /usr/bin/python2.7 ../py2-install-test-virtualenv
source ../py2-install-test-virtualenv/bin/activate
pip install --pre -i https://pypi.python.org/pypi beautifulsoup4
echo "EXPECT HTML ON LINE BELOW"
(cd .. && python -c "from bs4 import _s; print(_s('<a>foo', 'html.parser'))")
# That should print '<a>foo</a>'
deactivate
rm -rf ../py2-install-test-virtualenv

# Try 3.x source install from pypi test
rm -rf ../py3-source-install
virtualenv -p /usr/bin/python3 ../py3-source-install
source ../py3-source-install/bin/activate
pip3 install -i https://testpypi.python.org/pypi beautifulsoup4
echo "EXPECT HTML ON LINE BELOW"
(cd .. && python -c "from bs4 import _s; print(_s('<a>foo', 'html.parser'))")
# That should print '<a>foo</a>'

# Create and upload a Python 3 wheel from within a virtual environment
# that has the Python 3 version of the code.
pip install wheel
python3 setup.py bdist_wheel upload -r test

deactivate
rm -rf ../py3-source-install

# Make sure setup.py works on 2.x
rm -rf ../py2-install-test-virtualenv
virtualenv -p /usr/bin/python2.7 ../py2-install-test-virtualenv
source ../py2-install-test-virtualenv/bin/activate
python setup.py install
echo "EXPECT HTML ON LINE BELOW"
(cd .. && python -c "from bs4 import _s; print(_s('<a>foo', 'html.parser'))")
echo
# That should print '<a>foo</a>'
deactivate
rm -rf ../py2-install-test-virtualenv
echo

# Make sure setup.py works on 3.x
rm -rf ../py3-install-test-virtualenv
virtualenv -p /usr/bin/python3 ../py3-install-test-virtualenv
source ../py3-install-test-virtualenv/bin/activate
python setup.py install
echo "EXPECT HTML ON LINE BELOW"
(cd .. && python -c "from bs4 import _s; print(_s('<a>foo', 'html.parser'))")
# That should print '<a>foo</a>'
deactivate
rm -rf ../py3-install-test-virtualenv
echo

# Make sure the 2.x wheel installs properly
rm -rf ../py2-install-test-virtualenv
virtualenv -p /usr/bin/python2.7 ../py2-install-test-virtualenv
source ../py2-install-test-virtualenv/bin/activate
pip install --upgrade setuptools
pip install dist/beautifulsoup4-4.*-py2-none-any.whl -e .[html5lib]
echo "EXPECT HTML ON LINE BELOW"
(cd .. && python -c "from bs4 import _s; print(_s('<a>foo', 'html5lib'))")
# That should print '<html><head></head><body><a>foo</a></body></html>'
deactivate
rm -rf ../py2-install-test-virtualenv

echo
# Make sure the 3.x wheel installs properly
rm -rf ../py3-install-test-virtualenv
virtualenv -p /usr/bin/python3 ../py3-install-test-virtualenv
source ../py3-install-test-virtualenv/bin/activate
pip3 install --upgrade setuptools
pip3 install dist/beautifulsoup4-4.*-py3-none-any.whl -e .[html5lib]
echo "EXPECT HTML ON LINE BELOW"
(cd .. && python -c "from bs4 import _s; print(_s('<a>foo', 'html5lib'))")
# That should print '<html><head></head><body><a>foo</a></body></html>'
deactivate
rm -rf ../py3-install-test-virtualenv

################

Do the release for real.

twine upload dist/*

# Register the project and upload the source distribution and Python 2 wheel.
# python setup.py register
# python setup.py sdist bdist_wheel upload

# Create a Python 3 environment and install Beautiful Soup
# from the source distribution that was just uploaded
#rm -rf ../py3-source-install
#virtualenv -p /usr/bin/python3 ../py3-source-install
#source ../py3-source-install/bin/activate
#pip install -i https://pypi.python.org/pypi beautifulsoup4
#echo "EXPECT HTML ON LINE BELOW"
#(cd .. && python -c "from bs4 import _s; print(_s('<a>foo', 'html.parser'))")
# That should print '<a>foo</a>'

# Create and upload a Python 3 wheel from within a virtual environment
# that has the Python 3 version of the code.
#pip install wheel
#python3 setup.py bdist_wheel upload

# Remove the Python 3 virtual environment.
#deactivate
#rm -rf ../py3-source-install


################

To test, after release:

rm -rf ../py2-install-test-virtualenv
virtualenv -p /usr/bin/python2.7 ../py2-install-test-virtualenv
source ../py2-install-test-virtualenv/bin/activate
pip install beautifulsoup4
echo "EXPECT HTML ON LINE BELOW"
(cd .. && python -c "from bs4 import _s; print(_s('<a>foo', 'html.parser'))")
# That should print '<a>foo</a>'
deactivate
rm -rf ../py2-install-test-virtualenv


rm -rf ../py3-install-test-virtualenv
virtualenv -p /usr/bin/python3 ../py3-install-test-virtualenv
source ../py3-install-test-virtualenv/bin/activate
pip install beautifulsoup4
echo "EXPECT HTML ON LINE BELOW"
(cd .. && python -c "from bs4 import _s; print(_s('<a>foo', 'html.parser'))")
# That should print '<a>foo</a>'
deactivate
rm -rf ../py3-install-test-virtualenv
