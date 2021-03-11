#!/bin/bash

set -u

if [ "${#@}" == "0" ]; then
    echo $(basename $0) DOCKER_TAG [DOCKER_RUNNER_IMAGE]
    exit 1
fi

set -e
set -x
set -o pipefail

R=$(readlink -f $(dirname $0))

DOCKER_TAG=${1}
DOCKER_RUNNER_IMAGE=${2:-auto-gitlab.lgsvl.net:4567/hdrp/scenarios/runner}

DIST_IMAGES='runner'
DIST_NAME=lgsvlsimulator-scenarios-$DOCKER_TAG
DIST_PATH=$(pwd)/dist/$DIST_NAME

PUBLIC_IMAGE=lgsvl/simulator-scenarios-runner

function save_docker_images {
    mkdir -p $DIST_PATH/docker
    ${R}/save_docker_image.sh ${DOCKER_RUNNER_IMAGE} $DOCKER_TAG $PUBLIC_IMAGE $DIST_PATH/docker
}

function copy_scripts {
    cp ./scripts/scenario_runner.sh $DIST_PATH
    ${R}/update-docker-image-ref.sh $DIST_PATH/scenario_runner.sh ${PUBLIC_IMAGE}:$DOCKER_TAG

    # TestCase runtime
    cp ./scripts/install-testcase-runtime.sh $DIST_PATH/install-testcase-runtime.sh
}

function copy_docs {
    copy_docs_${BUNDLE_FLAVOR}
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
# copy_docs

# Some housekeeping
find $DIST_PATH -name '.git*' | xargs rm -rf

pushd $DIST_PATH/..

if [ -z "${FAST_RELEASE:-}" ]; then
    make_zip
fi
show_tree

