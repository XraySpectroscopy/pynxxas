#!/bin/bash

SCRIPT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

nxxas-convert -w "${SCRIPT_ROOT}/auto/*.*" "${SCRIPT_ROOT}/auto/converted.nx"

for script in "${SCRIPT_ROOT}/manual"/*/convert_to_nexus.py; do
    python "$script"
done
