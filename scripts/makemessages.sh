#!/bin/bash
echo "This script generates all message PO files. Call this script from your wechange directory (the one containing 'manage.py'), like this: '../cosinnus-core/scripts/makemessages.sh'"

django-admin makemessages -a --no-wrap --no-location --ignore=node_modules/* --ignore=wagtailadmin/*
echo "Compiled project message files".

cd ../cosinnus-core/
django-admin makemessages -a --no-wrap --no-location --ignore=node_modules/* --ignore=wagtailadmin/*
echo "Compiled cosinnus-core message files".
