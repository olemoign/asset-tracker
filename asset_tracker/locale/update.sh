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
pybabel extract -F locale/babel.ini -o locale/messages.pot --omit-header --sort-output .
header='msgid ""
msgstr ""
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"

'
echo "${header}$(cat locale/messages.pot)" > locale/messages.pot
pybabel update -i locale/messages.pot -d locale --ignore-obsolete --no-fuzzy-matching --omit-header

# Copy the po files header.
cd "${SCRIPTPATH}"/en/LC_MESSAGES || exit
header_en='msgid ""
msgstr ""
"Language: en\n"
"Plural-Forms: nplurals=2; plural=(n > 1)\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"

'
echo "${header_en}$(cat messages.po)" > messages.po

cd "${SCRIPTPATH}"/fr/LC_MESSAGES || exit
header_fr='msgid ""
msgstr ""
"Language: fr\n"
"Plural-Forms: nplurals=2; plural=(n > 1)\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"

'
echo "${header_fr}$(cat messages.po)" > messages.po

echo -e "${BLUE}ADD translations in locale/fr/LC_MESSAGES/messages.po then RUN ${RED}pybabel compile -d locale${BLUE}.${RESET_TEXT}"
