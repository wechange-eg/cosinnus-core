#!/bin/bash
if [[ "$1" == "-a" ]]; then
    LOCALE_ARGS="-a"
    echo "Using -a: Making message files (PO-files) for ALL available locales."
else
    LOCALE_ARGS="--locale de --locale en"
    echo "Making message (PO-files) for default locales: de and en."
fi
echo "Call this script from your wechange directory (the one containing 'manage.py'), like this: '../cosinnus-core/scripts/makemessages.sh'"
echo 

django-admin makemessages --no-wrap --no-location --ignore=node_modules/* --ignore=wagtailadmin/* ${LOCALE_ARGS}
echo "Made project message files".
echo 

cd ../cosinnus-core/
django-admin makemessages --no-wrap --no-location --ignore=node_modules/* --ignore=wagtailadmin/* ${LOCALE_ARGS}
echo "Made cosinnus-core message files".
