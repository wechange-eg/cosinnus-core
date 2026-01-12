#!/bin/bash
# this uses https://github.com/michalpokusa/django-extended-makemessages to generate po-files that produce small diffs


# Exit on error
set -e

echo ">> Call this script from your wechange directory (the one containing 'manage.py'), "
echo ">>   like this: '../cosinnus-core/scripts/makemessages.sh'"

# --- Configuration ---
PROJECT_ROOT=$(pwd)
MANAGE_PY="$PROJECT_ROOT/manage.py"
CORE_PATH="$PROJECT_ROOT/../cosinnus-core"

# Default values as strings for easy comparison in hints
LOCALE_ARGS="-l de -l en"
SORTING_ARGS="--sort-output"

# Comprehensive array for all standard flags
BASE_FLAGS=(
    "--keep-header"
    "--no-fuzzy-matching"
    "--no-wrap"
#    "--no-obsolete"
    "--detect-aliases"
    "--show-untranslated"
    "--add-location" "file"
#    "--no-location"
    "--ignore" "wagtailadmin/*"
    "--ignore" "node_modules/*"
)

# --- Argument Handling ---

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -a)
            LOCALE_ARGS="-a"
            ;;
        --no-sort-output)
            SORTING_ARGS=""
            ;;
        *)
            echo ">> Unknown parameter: $1"
            exit 1
            ;;
    esac
    shift
done

# --- Guard Clauses ---

if [[ ! -f "$MANAGE_PY" ]]; then
    echo ">> Error: manage.py not found in $PROJECT_ROOT"
    exit 1
fi

if [[ ! -d "$CORE_PATH" ]]; then
    echo ">> Error: Core directory not found at $CORE_PATH"
    exit 1
fi

if ! python3 "$MANAGE_PY" help extendedmakemessages > /dev/null 2>&1; then
    echo ">> Error: 'extendedmakemessages' command is not available."
    exit 1
fi

# --- Notices / Hints ---

if [[ "$LOCALE_ARGS" == "-a" ]]; then
    echo ">> Status: Processing ALL locales."
else
    echo ">> Status: Processing default locales (de, en). [Hint: Use '-a' for all]"
fi

if [[ "$SORTING_ARGS" == "--sort-output" ]]; then
    echo ">> Status: Sorting enabled. [Hint: Use '--no-sort-output' to skip]"
else
    echo ">> Status: Sorting disabled."
fi

# --- Execution ---

# 1. Update Project translations
echo ">> Updating Project translations..."
python3 "$MANAGE_PY" extendedmakemessages "${BASE_FLAGS[@]}" $SORTING_ARGS $LOCALE_ARGS

# 2. Update Core translations
echo ">> Updating Cosinnus Core translations..."
cd "$CORE_PATH"
python3 "$MANAGE_PY" extendedmakemessages "${BASE_FLAGS[@]}" $SORTING_ARGS $LOCALE_ARGS

echo ">> Done."
