#!/bin/bash

set -eu

SIMULATOR_DIR=${1:-$(pwd)}
INSTALL_MODE=${2:-link}

BUNDLE_ROOT_DIR=$(readlink -f $(dirname $0))

function usage {
    echo "Usage: $(basename $0) /path/to/lgsvlsimulator/folder"
    exit 1
}

SUPPORTED_RUNTIMES='randomTraffic RandomTraffic'
WRAPPER_SCRIPT=scenario_runner.sh

if [ ! -x ${SIMULATOR_DIR}/simulator ]; then
    echo "Can't find simulator on ${SIMULATOR_DIR}"
    echo
    usage
fi

function link_runtime {
    echo "I: Link runtime to simulator at ${SIMULATOR_DIR}"

    for runtime in ${SUPPORTED_RUNTIMES}; do
        echo "Setup ${runtime} runtime in ${SIMULATOR_DIR}"
        mkdir -p ${SIMULATOR_DIR}/TestCaseRunner/${runtime}
        ln -fs ${BUNDLE_ROOT_DIR}/${WRAPPER_SCRIPT} ${SIMULATOR_DIR}/TestCaseRunner/${runtime}/run
    done
}

function copy_runtime {
    echo "I: Copy runtime to simulator at ${SIMULATOR_DIR}"

    mkdir -p ${SIMULATOR_DIR}/TestCaseRunner/scenarioRunner
    cp ${BUNDLE_ROOT_DIR}/${WRAPPER_SCRIPT} ${SIMULATOR_DIR}/TestCaseRunner/scenarioRunner
    cp -R ${BUNDLE_ROOT_DIR}/docker ${SIMULATOR_DIR}/TestCaseRunner/scenarioRunner

    for runtime in ${SUPPORTED_RUNTIMES}; do
        echo "Setup ${runtime} runtime in ${SIMULATOR_DIR}"
        mkdir -p ${SIMULATOR_DIR}/TestCaseRunner/${runtime}
        ln -fs ../scenarioRunner/${WRAPPER_SCRIPT} ${SIMULATOR_DIR}/TestCaseRunner/${runtime}/run
    done
}

case ${INSTALL_MODE} in
    link)
        link_runtime
        ;;
    copy)
        copy_runtime
        ;;
    *)
        echo "E: Unsupported runtime install mode '${INSTALL_MODE}' specified. 'copy' or 'link' is supported"
        ;;
esac

