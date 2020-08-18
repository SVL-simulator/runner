#!/bin/bash

# set -x
set -e
set -u

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
    # check "install-testcase-runtime.sh is executible" test -x install-testcase-runtime.sh

    check "Saved docker image present (placeholder)" test -f docker/lgsvl-simulator-scenarios-runner-latest.tar-placeholder || \
    check "Saved docker image present" test -f docker/lgsvl-simulator-scenarios-runner-latest.tar

    check "File scenario_runner.sh exists" test -f scenario_runner.sh
}

echo "Checking bundle in $(pwd)"

check_common

