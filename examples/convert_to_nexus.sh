#!/bin/bash

SCRIPT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Print one line for each conversion. Warnings and errors go to stderr.
convert() {
    local output="$1"
    shift
    printf "%-50s " "${output}"
    if "$@" > /dev/null; then
        echo "done"
    else
        echo "FAILED"
    fi
}

convert "auto/converted.nxs" \
    nxxas-convert -w "${SCRIPT_ROOT}/auto/*.xdi" "${SCRIPT_ROOT}/auto/converted.nxs"

for script in "${SCRIPT_ROOT}/manual"/*/convert_to_nexus.py; do
    name="$(basename "$(dirname "${script}")")"
    convert "manual/${name}/${name}.nxs" python "${script}"
done
