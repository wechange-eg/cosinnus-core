#!/bin/bash

echo "This script compiles all cosinnus JS bundles. Call this script from your wechange directory (the one containing 'manage.py'), like this: '../cosinnus-core/scripts/compile-static-bundles.sh'"

cd ../cosinnus-core/
# run 'npm install' in this folder the first time you do this!
npm run production
echo "Built cosinnus/static/js/client.js."

cd ./cosinnus_conference/frontend/
# run 'npm install' in this folder the first time you do this!
npm run build
echo "Built cosinnus_conference/static/conference/main.js."

