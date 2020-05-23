#!/bin/bash

set -eu

SIMULATOR_DIR=${1:-$(pwd)}
BUNDLE_ROOT_DIR=$(readlink -f $(dirname $0))

function usage {
    echo "Usage: $(basename $0) /path/to/lgsvlsimulator/folder"
    exit 1
}


if [ ! -x ${SIMULATOR_DIR}/simulator ]; then 
    echo "Can't find simulator on ${SIMULATOR_DIR}"
    echo
    usage
fi

echo "Setup Python API runtime in ${SIMULATOR_DIR}"

mkdir -p ${SIMULATOR_DIR}/TestCaseRunner/pythonAPI
ln -fs ${BUNDLE_ROOT_DIR}/lgsvl_scenario.sh ${SIMULATOR_DIR}/TestCaseRunner/pythonAPI/run
