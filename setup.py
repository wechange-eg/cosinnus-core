#!/usr/bin/env python
import os
import codecs
import sys
from setuptools import setup, find_packages


def read(*parts):
    filename = os.path.join(os.path.dirname(__file__), *parts)
    with codecs.open(filename, encoding='utf-8') as fp:
        return fp.read()


def fullsplit(path, result=None):
    """
    Split a pathname into components (the opposite of os.path.join) in a
    platform-neutral way.
    """
    if result is None:
        result = []
    head, tail = os.path.split(path)
    if head == '':
        return [tail] + result
    if head == path:
        return result
    return fullsplit(head, [tail] + result)

# Compile the list of packages available, because setuptools doesn't have
# an easy way to do this. Taken from Django.
packages, data_files = [], []
root_dir = os.path.dirname(__file__)
if root_dir != '':
    os.chdir(root_dir)
pkgdir = 'cosinnus'

for dirpath, dirnames, filenames in os.walk(pkgdir):
    # Ignore PEP 3147 cache dirs and those whose names start with '.'
    dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != '__pycache__']
    if '__init__.py' in filenames:
        packages.append('.'.join(fullsplit(dirpath)))
    elif filenames:
        data_files.append([dirpath, [os.path.join(dirpath, f) for f in filenames]])

from cosinnus import get_version


setup(
    name='cosinnus',
    version=get_version(),
    description='cosinnus core application',
    long_description=read('README'),
    author='Sinnwerkstatt Medienagentur GmbH Berlin',
    author_email='web@sinnwerkstatt.com',
    packages=find_packages(exclude=["tests"]),
    data_files=data_files,
    install_requires=[
        'Django>=1.5, <1.7',
        'Django-Select2',
        'Pillow>=2.1.0',
        'South>=0.7',
        'django-appconf>=0.6',
        'django-awesome-avatar',
        'django-bootstrap3',
        'django-bootstrap3-datetimepicker>=2.2.0',
        'django-djajax',
        'django-filter>=0.7',
        'django-multiform',
        'django-recaptcha>=1.0.2',
        'django_select2',
        'django-taggit>=0.11',
        'django-tinymce==1.5.2',
        'djangorestframework>=2.3.0',
        'easy-thumbnails>=1.4',
        'jsonfield>=1.0.0',
    ],
    dependency_links=[
        'git+git://github.com/Markush2010/django-bootstrap3.git@develop#egg=django-bootstrap3',
        'git+http://git.sinnwerkstatt.com/mh/django-multiform.git@master#egg=django-multiform',
        'git+git://github.com/sinnwerkstatt/django-select2.git@master#egg=Django-Select2',
        'git+git://github.com/sinnwerkstatt/django-awesome-avatar.git@master#egg=django-awesome-avatar',
        'git+git://github.com/saschan/django-djajax.git@master#egg=django-djajax',
        'git+git://github.com/sinnwerkstatt/django-osm-field.git@master#egg=django-osm-field'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Framework :: Django',
    ],
    zip_safe=False,
    include_package_data=True
)
