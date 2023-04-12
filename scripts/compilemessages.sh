#!/bin/bash
echo "This script compiles all message PO files. Call this script from your wechange directory (the one containing 'manage.py'), like this: '../cosinnus-core/scripts/makemessages.sh'"

django-admin compilemessages
echo "Compiled project message files".

cd ../cosinnus-core/
django-admin compilemessages
echo "Compiled cosinnus-core message files".
