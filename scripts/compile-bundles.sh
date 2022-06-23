#!/bin/bash

echo "This script compiles all cosinnus JS/LESS bundles. Call this script from your wechange directory (the one containing 'manage.py'), like this: '../cosinnus-core/scripts/compile-static-bundles.sh'"

# less
./manage.py collectstatic --noinput
../cosinnus-core/node_modules/.bin/lessc --clean-css ./static-collected/less/cosinnus.less ../cosinnus-core/cosinnus/static/css/cosinnus.css
echo "Built cosinnus/static/css/cosinnus.css."

cd ../cosinnus-core/
# run 'npm install' in this folder the first time you do this!
npm run production
echo "Built cosinnus/static/js/client.js."

cd ./cosinnus_conference/frontend/
# run 'npm install' in this folder the first time you do this!
npm run build
echo "Built cosinnus_conference/static/conference/main.js."

