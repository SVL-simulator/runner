#!/bin/bash

set -u

if [ "${#@}" == "0" ]; then
    echo $(basename $0) DOCKER_TAG [DOCKER_RUNNER_IMAGE [BUNDLE_FLAVOR]]
    exit 1
fi

set -e
set -x
set -o pipefail

R=$(readlink -f $(dirname $0))

DOCKER_TAG=${1}
DOCKER_RUNNER_IMAGE=${2:-auto-gitlab.lgsvl.net:4567/hdrp/scenarios/runner}
BUNDLE_FLAVOR=${3:-scenic}

DIST_IMAGES='runner'
DIST_NAME=lgsvlsimulator-scenarios-$DOCKER_TAG
DIST_PATH=$(pwd)/dist/$DIST_NAME

PUBLIC_IMAGE=lgsvl/simulator-scenarios-runner

case "${BUNDLE_FLAVOR}" in
    "scenic"|"python-api")
        ;;
    *)
        echo "E: Unknown bundle flavor '${BUNDLE_FLAVOR}'"
        exit 1
        ;;
esac


function save_docker_images {
    mkdir -p $DIST_PATH/docker
    ${R}/save_docker_image.sh ${DOCKER_RUNNER_IMAGE} $DOCKER_TAG $PUBLIC_IMAGE $DIST_PATH/docker
}

function copy_scripts {
    copy_scripts_${BUNDLE_FLAVOR}

    # TestCase runtime
    cp ./scripts/install-testcase-runtime-${BUNDLE_FLAVOR}.sh $DIST_PATH/install-testcase-runtime.sh
}

function copy_scripts_scenic {
    cp ./scripts/scenic_lgsvl.sh $DIST_PATH/scenic_lgsvl.sh
    ${R}/update-docker-image-ref.sh $DIST_PATH/scenic_lgsvl.sh ${PUBLIC_IMAGE}:$DOCKER_TAG
}

function copy_scripts_python-api {
    cp ./scripts/scenic_lgsvl.sh $DIST_PATH/lgsvl_scenario.sh
    ${R}/update-docker-image-ref.sh $DIST_PATH/lgsvl_scenario.sh ${PUBLIC_IMAGE}:$DOCKER_TAG
}

function copy_scenarios {
    mkdir -p $DIST_PATH/scenarios
    copy_scenarios_${BUNDLE_FLAVOR}
}

function copy_scenarios_scenic {
    test -d scenarios/Scenic || (echo "E: Can't find Scenic scenarios"; exit 1)
    cp -r scenarios/Scenic/* $DIST_PATH/scenarios
    cp -r scenarios/Python/SampleTestCases $DIST_PATH/scenarios
}

function copy_scenarios_python-api {
    test -d scenarios/Python || (echo "E: Can't find Python scenarios"; exit 1)
    cp -r scenarios/Python/* $DIST_PATH/scenarios
}

function copy_docs {
    copy_docs_${BUNDLE_FLAVOR}
}

function copy_docs_scenic {
    cp -r docs/Scenic $DIST_PATH/docs
}

function copy_docs_python-api {
    cp -r docs/Python $DIST_PATH/docs
}

function show_tree() {
    TREE=$(which tree || true)

    if [ -x "${TREE}" ]; then
        ${TREE} -a $DIST_NAME | tee $DIST_NAME-content.txt
    else
        echo "W: Can't generate dist content list: tree is not installed"
    fi
}

function make_zip() {
    rm -f $DIST_NAME.zip || true
    zip -r $DIST_NAME.zip $DIST_NAME
}

rm -rf $DIST_PATH
mkdir -p $DIST_PATH

save_docker_images
copy_scripts
copy_scenarios
copy_docs

# Some housekeeping
find $DIST_PATH -name '.git*' | xargs rm -rf

pushd $DIST_PATH/..

if [ -z "${FAST_RELEASE:-}" ]; then
    make_zip
fi
show_tree

