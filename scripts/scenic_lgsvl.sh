#!/bin/bash

set -eu
# set -x

SCENIC_LGSVL_IMAGE_DEFAULT=auto-gitlab.lgsvl.net:4567/hdrp/scenarios/runner:latest

# Envvar defaults
SCENARIOS_DIR=${SCENARIOS_DIR:-$(pwd)}
SIMULATOR_HOST=${SIMULATOR_HOST:-localhost}
SIMULATOR_PORT=${SIMULATOR_PORT:-8181}
BRIDGE_HOST=${BRIDGE_HOST:-localhost}
BRIDGE_PORT=${BRIDGE_PORT:-9090}
SCENIC_LGSVL_IMAGE=${SCENIC_LGSVL_IMAGE:-${SCENIC_LGSVL_IMAGE_DEFAULT}}

function load_docker_image {
    IMAGE_NAME=${1}
    TARBALL_DIR=${2}

    TARBALL_NAME=$(echo ${IMAGE_NAME} | tr '/-' '__' | tr ':' '-')

    TARBALL_PATH="${TARBALL_DIR}/${TARBALL_NAME}.tar"

    if ! docker history ${IMAGE_NAME} 2>&1 > /dev/null; then
        docker load -i ${TARBALL_PATH}
    fi
}

R=$(readlink -f "$(dirname $0)")

load_docker_image $SCENIC_LGSVL_IMAGE ${R}/docker

function run_scenic_container() {
    if [ ${#@} == 0 ]; then
        echo "I: Running interactive shell"
        ARGS=bash
    else
        ARGS=$@
    fi

    MOUNT_SCENARIOS_DIR=

    if [ "${SCENARIOS_DIR:-none}" != "none" ]; then
        MOUNT_SCENARIOS_DIR="--volume ${SCENARIOS_DIR}:/scenarios --workdir=/scenarios"
    else
        echo "W: SCENARIOS_DIR is not set. scenarios dir is not mounted"
        MOUNT_SCENARIOS_DIR='--workdir=/'
    fi

    DOCKER_USER=$(id -u):$(id -g)

    exec docker run \
        --rm --tty --interactive \
        --user=${DOCKER_USER} \
        --network=host \
        -e SIMULATOR_HOST=${SIMULATOR_HOST} \
        -e SIMULATOR_PORT=${SIMULATOR_PORT} \
        -e BRIDGE_HOST=${BRIDGE_HOST} \
        -e BRIDGE_PORT=${BRIDGE_PORT} \
        -e debian_chroot=RUN_SCENIC \
        ${MOUNT_SCENARIOS_DIR} \
        ${SCENIC_LGSVL_IMAGE} \
        ${ARGS}
}

function cmd_env() {
    echo "SIMULATOR_HOST=${SIMULATOR_HOST}"
    echo "SIMULATOR_PORT=${SIMULATOR_PORT}"
    echo "BRIDGE_HOST=${BRIDGE_HOST}"
    echo "BRIDGE_PORT=${BRIDGE_PORT}"
    echo "SCENARIOS_DIR=${SCENARIOS_DIR}"
    echo "SCENIC_LGSVL_IMAGE=${SCENIC_LGSVL_IMAGE}"
}

function cmd_pull_image() {
        echo "I: Pulling ${SCENIC_LGSVL_IMAGE}"
        docker pull ${SCENIC_LGSVL_IMAGE}
}

function cmd_help() {
    CMD=$(basename $0)

cat<<EOF
Usage: ${CMD} help|pull|env|bash|run_scenario|SHELL_COMMAND [ARGS...]

    help          - Show this message
    pull          - pull docker image
    env           - print usefull environment variables
    bash          - Run container with interactive shell
    run           - Run scenario. This subcommand has own help. See '${CMD} run --help for details'
    SHELL_COMMAND - run shell command inside the container.

Important note: command is launched in a singleshot container so scenarios shall not save any data outside /scenarios folder

ENVIRONMENT VARIABLES:

    * SIMULATOR_HOST/SIMULATOR_PORT - LGSVL Simulator hostname (default:localhost )
    * SIMULATOR_HOST/SIMULATOR_PORT - LGSVL Simulator port (default: 8181)
    * BRIDGE_HOST - ROS/Apollo bridge hostname (default:localhost)
    * BRIDGE_PORT - ROS/Apollo bridge port (default:9090)
    * SCENARIOS_DIR - host folder to be mounted as /scenarios inside the container
    * SCENIC_LGSVL_IMAGE - docker image to run

    '${CMD} env' to list current values


HOW TO GET THIS FILE

    1. Get it form the image:

        $> scenic_lgsvl.sh pull
        $> docker run --rm ${SCENIC_LGSVL_IMAGE} get_scenic_lgsvl > ~/.local/bin/scenic_lgsvl.sh
        $> chmod +x ~/.local/bin/scenic_lgsvl.sh

EOF
}

case "${1:-}" in
    "pull")
        cmd_pull_image
        ;;
    "env")
        cmd_env
        ;;
    "help")
        cmd_help
        ;;
    "run")
        shift
        run_scenic_container run $@
        ;;
    *)
        run_scenic_container $@
        ;;
esac

