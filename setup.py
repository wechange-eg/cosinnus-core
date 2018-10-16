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
        # please mirror all changes in the requirements.txt for local installs!
        'Django==1.8.18',
        'MarkupSafe==0.18',
        'Pillow==5.2.0',
        'Celery==4.2.0',
        
        'django-annoying==0.7.6',
        'django-appconf==1.0.2',
        'django-bootstrap3-datetimepicker==2.2.0',
        'django-classy-tags==0.4',
        'django-cron==0.5.0',
        'django-embed-video==0.6',
        'django-endless-pagination==2.0',
        'django-extra-views==0.6.3',
        'django-filer==0.9.12',
        'django-filter==1.1.0',
        'django-haystack==2.7.0',
        'django-honeypot==0.6.0',
        'django-model-utils==1.5.0',
        'django-phonenumber-field==1.1.0',
        'django-polymorphic==0.7.2',
        'django-rest-swagger==0.3.10',
        'django-sekizai==0.8.2',
        'django-simple-captcha==0.5.7',
        'django-suit==0.2.15',
        'django-taggit',
        'django-widget-tweaks==1.3',
        'djangorestframework==3.6.4',
        'dnspython==1.15.0',
        'easy-thumbnails==1.4',
        'ecdsa==0.10',
        'jsonfield==1.0.0',
        'jsonfield==1.0.0',
        'html5lib',
        'html2text==2016.9.19',
        'numpy==1.14.5',
        'oauthlib==2.0.2',
        'paramiko',
        'pycrypto==2.6.1',
        'pydkim==0.3',
        'redis==2.10.6',
        'requests<3.0',
        'requests-oauthlib==0.8.0',
        'six==1.11.0',
        'sqlparse==0.1.10',
        #########'wsgiref==0.1.2',
        'python-dateutil==2.4.1',
        'python-memcached',
        
        # wagtail
        'wagtail==1.4.6',
        'django-overextends',
        'django-compressor',
        'django-modelcluster',
        
        # requirements loaded in from github
        'django-awesome-avatar',
        'django-bootstrap3',
        'django-multiform',
        'django-djajax',
        'django_select2',
        'django-osm-field',
        'markdown2',
        'pydkim',
        'wagtail-modeltranslation',
    ],
    dependency_links=[
        'git+git://github.com/sinnwerkstatt/django-awesome-avatar.git@master#egg=django-awesome-avatar',
        'git+git://github.com/Markush2010/django-bootstrap3.git@46a84044e89937ebe6128b2a8c560f141741a70e#egg=django-bootstrap3',
        'git+git://github.com/sinnwerkstatt/django-multiform.git@master#egg=django-multiform',
        'git+git://github.com/saschan/django-djajax.git@master#egg=django-djajax',
        'git+git://github.com/sinnwerkstatt/django-select2.git@master#egg=Django-Select2',
        'git+git://github.com/sinnwerkstatt/django-osm-field.git@master#egg=django-osm-field',
        'git+git://github.com/wechange-eg/python-markdown2.git@master#egg=markdown2',
        'git+git://github.com/wechange-eg/pydkim.git@master#egg=pydkim',
        'git+git://github.com/saschan/wagtail-modeltranslation.git@translatable-streamfields#egg=wagtail-modeltranslation',
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
