#!/bin/bash

# set -x
set -e
set -u

BUNDLE_FLAVOR=${1}

function print_elipsis {
    count=$1

    printf '.%.0s' $(eval "echo {1.."${count}"}")
}

function check {
    message=$1
    shift

    # echo "CMD: $@"

    echo -n "Check: ${message} ";
    print_elipsis "$((60 - ${#message}))"

    ($@ || (echo " Failed"; exit 1)) && echo " Ok"
}

function check_common {
    check "scenario_runner.sh is executible" test -x scenario_runner.sh
    check "install-testcase-runtime.sh is executible" test -x install-testcase-runtime.sh

    check "Saved docker image present (placeholder)" test -f docker/lgsvl-simulator-scenarios-runner-latest-${BUNDLE_FLAVOR}.tar-placeholder || \
    check "Saved docker image present" test -f docker/lgsvl-simulator-scenarios-runner-latest-${BUNDLE_FLAVOR}.tar

}

function check_mandatory_files {
    FILES='docs/README.md scenario_runner.sh install-testcase-runtime.sh'

    for f in $FILES; do
        check "File '$f' exists" test -f $f
    done
}

function check_python-api {
    check "lgsvl_scenario.sh is a link" test -L lgsvl_scenario.sh
    check "lgsvl_scenario.sh points to scenario_runner.sh" test $(readlink lgsvl_scenario.sh) = scenario_runner.sh
}

function check_scenic {
    check "scenic_lgsvl.sh is a link" test -L scenic_lgsvl.sh
    check "scenic_lgsvl.sh points to scenario_runner.sh" test $(readlink scenic_lgsvl.sh) = scenario_runner.sh
}

echo "Checking ${BUNDLE_FLAVOR} bundle in $(pwd)"

check_mandatory_files
check_common
check_${BUNDLE_FLAVOR}

