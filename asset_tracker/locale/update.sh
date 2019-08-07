#!/bin/bash

BLUE="\033[0;36m"
RED="\033[0;31m"
RESET_TEXT="\033[0m"

# In macOS, readlink is replaced by greadlink.
if [[ "$OSTYPE" == "darwin"* ]]; then
    readlink() {
        greadlink "$@"
    }
    export -f readlink
fi

# Required programs.
missing_programs=0
for program in dirname pybabel readlink
do
    if ! (hash ${program} 2>/dev/null); then
        echo -e "${BLUE}${program} is missing.${RESET_TEXT}"
        ((missing_programs++))
    fi
done

# Stop execution if a required program is missing.
if [[ "$missing_programs" -ne 0 ]]; then
    echo -e "${BLUE}Aborting.${RESET_TEXT}"
    exit 1
fi

SCRIPT=$(readlink -f "${BASH_SOURCE[0]}")
SCRIPTPATH=$(dirname "${SCRIPT}")

cd "${SCRIPTPATH}"/.. || exit
pybabel extract -F locale/babel.ini -o locale/messages.pot --sort-output .
pybabel update -i locale/messages.pot -d locale --previous --no-fuzzy-matching

echo -e "${BLUE}ADD translations in locale/fr/LC_MESSAGES/messages.po then RUN ${RED}pybabel compile -d locale${BLUE}.${RESET_TEXT}"
