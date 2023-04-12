#!/bin/bash

echo "This script compiles all cosinnus JS bundles. Call this script from your wechange directory (the one containing 'manage.py'), like this: '../cosinnus-core/scripts/compile-bundles.sh'"

cd ../cosinnus-core/
# technically, you only need to run 'npm install' in this folder the first time you do this!
npm install
npm run production
echo "Built cosinnus/static/js/client.js."

cd ./cosinnus_conference/frontend/
# technically, you only need to run 'npm install' in this folder the first time you do this!
npm install
npm run build
echo "Built cosinnus/static/js/conference.js."

echo "Completed successfully. Remember to commit any changes to the bundle files if you want to deploy them on the server."