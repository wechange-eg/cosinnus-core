#!/bin/bash
if [[ "$1" == "-a" ]]; then
    LOCALE_ARGS=""
    echo "Using -a: Compiling ALL available message files (locales) to MO-files."
else
    LOCALE_ARGS="--locale de --locale en"
    echo "Compiling message files to PO-files for default locales: de and en."
fi
echo "Call this script from your wechange directory (the one containing 'manage.py'), like this: '../cosinnus-core/scripts/compilemessages.sh'"
echo 


django-admin compilemessages ${LOCALE_ARGS}
echo "Compiled project message files".
echo 

cd ../cosinnus-core/
django-admin compilemessages ${LOCALE_ARGS}
echo "Compiled cosinnus-core message files".
