#!/usr/bin/env python

import os
import codecs
from setuptools import setup, find_packages

from cosinnus import VERSION as COSINNUS_VERSION


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
data_files = []
root_dir = os.path.dirname(__file__)
if root_dir != '':
    os.chdir(root_dir)

packages = [
    "ajax_forms",
    "announcements",
    "cosinnus",
    "cosinnus_cloud",
    "cosinnus_conference",
    "cosinnus_etherpad",
    "cosinnus_event",
    "cosinnus_exchange",
    "cosinnus_file",
    "cosinnus_marketplace",
    "cosinnus_message",
    "cosinnus_note",
    "cosinnus_notifications",
    "cosinnus_oauth_client",
    "cosinnus_organization",
    "cosinnus_poll",
    "cosinnus_stream",
    "cosinnus_todo",
    "cosinnus_frontend",
    "postman",
    "rest_framework_rdf",
    "suit_overextends",
    "wagtail_overextends",
    "locale",
]

for package in packages:
    for dirpath, dirnames, filenames in os.walk(package):
        # Ignore PEP 3147 cache dirs and those whose names start with '.'
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != '__pycache__']
        data_files.append([dirpath, [os.path.join(dirpath, f) for f in filenames if not f.endswith(".py")]])

data_files.extend([
    "nunjucks.config.js",
    "package.json",
])

setup(
    name='cosinnus',
    version=COSINNUS_VERSION,
    description='cosinnus core application',
    long_description=read('README'),
    author='wechange eG',
    author_email='support@wechange.de',
    packages=find_packages(exclude=["tests"]),
    data_files=data_files,
    install_requires=[
        # please mirror all changes in the requirements.txt for local installs!
        'Django>=3.2.14,<3.3',
        'MarkupSafe==1.1',
        'Pillow==8.4.0',
        'Celery==4.2.0',
        'dataclasses',
        
        'beautifulsoup4==4.8.1',
        'chardet==3.0.4',
        'django-allauth==0.42.0',
        'django-annoying==0.7.6',
        'django-appconf==1.0.3',
        'django-bootstrap3-datetimepicker-3==2.6.0',
        'django-bootstrap3==21.1',
        'django-classy-tags==2.0.0',
        'django-countries==7.2.1',
        'django-cron==0.5.0',
        'django-embed-video==0.6',
        'django-el-pagination==2.1.2',
        'django-extensions==3.1.5',
        'django-extra-views==0.14.0',
        'django-filter==21.1',
        'django-haystack==3.1.1',
        'django-honeypot==0.9.0',
        'django-ical==1.7.1',
        'django-mailbox==4.8.2',
        'django-modelcluster==5.2',
        'django-model-utils==1.5.0',
        'django-mptt==0.8.7',
        'django-oauth-toolkit==1.3.2',
        'django-otp==1.1.1',
        'django-phonenumber-field==1.1.0',
        'django-polymorphic==0.7.2',
        'django-reverse-admin==2.9.4',
        'django-sekizai==2.0.0',
        'django-simple-captcha==0.5.14',
        'django-taggit==1.5.1',
        'django-timezone-field==4.2.1',
        'django-two-factor-auth==1.14.0',
        'django-widget-tweaks==1.4.9',
        'djangorestframework==3.12.4',
        'djangorestframework-csv==2.1.1',
        'djangorestframework-jwt==1.11.0',
        'dnspython==1.15.0',
        'drf-extra-fields==3.4.0',
        'drf-yasg==1.20.0',
        'easy-thumbnails==2.8',
        'ecdsa==0.13.3',
        'geopy==1.11.0',
        'jsonfield==3.1.0',
        'lxml==4.9.1',
        'html5lib',
        'html2text==2016.9.19',
        'numpy==1.22.4',
        'oauthlib==3.0.1',
        'paramiko==2.11.0',
        'pycountry==20.7.3',
        'pycrypto==2.6.1',
        'raven==6.9.0',
        'redis==2.10.6',
        'requests==2.20.0',
        'requests-oauthlib==0.8.0',
        'rocketchat-API==0.6.26',
        'six==1.12.0',
        'sqlparse==0.2.2',
        'sentry-sdk==1.4.2',
        'python-dateutil==2.4.1',
        'urllib3==1.24.2',
        'pytz==2018.5',
        'PyJWT==1.7.1',
        'rdflib==5.0.0',
        'python-memcached==1.59',
        'qrcode==6.1',
        'Unidecode==0.4.21',
        'XlsxWriter==1.3.7',
        'django-cors-headers<3.11.0',

        # wagtail
        'wagtail==2.15.1',
        'django-compressor==3.1',
        
        # virus file scan validator
        'clamd==1.0.2',
        'django-clamd==0.4.0',

        # requirements for BigBlueButton integration
        'django-jalali==4.0.0',
        'django-bigbluebutton==0.1.0',

        # requirements loaded in from github
        'django-awesome-avatar @ git+https://github.com/wechange-eg/django-awesome-avatar.git@django2#egg=django-awesome-avatar',
        'django-filer @ git+https://github.com/wechange-eg/django-filer.git@django-update-3-2#egg=django-filer',
        'django-multiform @ git+https://github.com/wechange-eg/django-multiform.git@master#egg=django-multiform',
        'django-djajax @ git+https://github.com/wechange-eg/django-djajax.git@django-update-3-2#egg=django-djajax',
        'django_select2 @ git+https://github.com/wechange-eg/django-select2.git@django-update-3-2#egg=django-select2',
        'django-osm-field @ git+https://github.com/wechange-eg/django-osm-field.git@django-update-3-2#egg=django-osm-field',
        'markdown2 @ git+https://github.com/wechange-eg/python-markdown2.git@master#egg=markdown2',
        'pydkim @ git+https://github.com/wechange-eg/pydkim.git@master#egg=pydkim',
        'django-suit @ git+https://github.com/wechange-eg/django-suit.git@main#egg=django-suit',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Framework :: Django',
    ],
    zip_safe=False,
    include_package_data=True
)
