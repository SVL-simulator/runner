#!/bin/bash

set -eu

SIMULATOR_DIR=${1:-$(pwd)}
BUNDLE_ROOT_DIR=$(readlink -f $(dirname $0))

function usage {
    echo "Usage: $(basename $0) /path/to/lgsvlsimulator/folder"
    exit 1
}

SUPPORTED_RUNTIMES='pythonAPI pythonApi'
WRAPPER_SCRIPT=lgsvl_scenario.sh

if [ ! -x ${SIMULATOR_DIR}/simulator ]; then
    echo "Can't find simulator on ${SIMULATOR_DIR}"
    echo
    usage
fi

for runtime in ${SUPPORTED_RUNTIMES}; do
    echo "Setup ${runtime} runtime in ${SIMULATOR_DIR}"
    mkdir -p ${SIMULATOR_DIR}/TestCaseRunner/${runtime}
    ln -fs ${BUNDLE_ROOT_DIR}/${WRAPPER_SCRIPT} ${SIMULATOR_DIR}/TestCaseRunner/${runtime}/run
done
