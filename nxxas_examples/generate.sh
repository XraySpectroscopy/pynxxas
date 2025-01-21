#!/bin/bash

SCRIPT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

nxxas-convert "${SCRIPT_ROOT}/../xdi_files/*.*" "${SCRIPT_ROOT}/../xas_beamline_data/*.*" "${SCRIPT_ROOT}/generic.h5"

for script in "${SCRIPT_ROOT}/../conversion_examples"/*/make_xas.py; do
    python "$script"
done
