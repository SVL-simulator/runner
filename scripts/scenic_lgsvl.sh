#!/bin/bash

set -eu
# set -x

SCENARIO_RUNNER_IMAGE_DEFAULT=auto-gitlab.lgsvl.net:4567/hdrp/scenarios/runner:latest

# Envvar defaults
SCENARIOS_DIR=${SCENARIOS_DIR:-$(pwd)}
SIMULATOR_HOST=${SIMULATOR_HOST:-localhost}
SIMULATOR_PORT=${SIMULATOR_PORT:-8181}
BRIDGE_HOST=${BRIDGE_HOST:-localhost}
BRIDGE_PORT=${BRIDGE_PORT:-9090}
SCENARIO_RUNNER_IMAGE=${SCENARIO_RUNNER_IMAGE:-${SCENARIO_RUNNER_IMAGE_DEFAULT}}

function load_docker_image {
    IMAGE_NAME=${1}
    TARBALL_DIR=${2}

    TARBALL_NAME=$(echo ${IMAGE_NAME} | tr ':/' '-')

    TARBALL_PATH="${TARBALL_DIR}/${TARBALL_NAME}.tar"

    if ! docker history ${IMAGE_NAME} > /dev/null 2>&1; then
        docker load -i ${TARBALL_PATH}
    fi
}

R=$(dirname $(readlink -f "$0"))

load_docker_image $SCENARIO_RUNNER_IMAGE ${R}/docker

DOCKER_RUN_TTY=--tty
DOCKER_RUN_ARGS=

function prepare_docker_run_args() {
    while [ -n "${1:-}" ]; do
        arg=$1
        shift

        if [[ $arg == *" "* ]]; then
            DOCKER_RUN_ARGS="${DOCKER_RUN_ARGS} '${arg}'"
        else
            DOCKER_RUN_ARGS="${DOCKER_RUN_ARGS} ${arg}"
        fi
    done
}

function run_container() {
    if [ ${#@} == 0 ]; then
        echo "I: Running interactive shell"
        prepare_docker_run_args bash
    else
        prepare_docker_run_args "$@"
    fi

    MOUNT_SCENARIOS_DIR=

    if [ "${SCENARIOS_DIR:-none}" != "none" ]; then
        MOUNT_SCENARIOS_DIR="--volume '${SCENARIOS_DIR}:/scenarios' --workdir=/scenarios"
    else
        echo "W: SCENARIOS_DIR is not set. scenarios dir is not mounted"
        MOUNT_SCENARIOS_DIR='--workdir=/'
    fi

    DOCKER_USER=$(id -u):$(id -g)

    exec bash -c "docker run \
        --rm ${DOCKER_RUN_TTY:-} --interactive \
        --user=${DOCKER_USER} \
        --network=host \
        -e SIMULATOR_HOST=${SIMULATOR_HOST} \
        -e SIMULATOR_PORT=${SIMULATOR_PORT} \
        -e BRIDGE_HOST=${BRIDGE_HOST} \
        -e BRIDGE_PORT=${BRIDGE_PORT} \
        -e debian_chroot=RUN_SCENARIO \
        ${MOUNT_SCENARIOS_DIR} \
        ${SCENARIO_RUNNER_IMAGE} \
        ${DOCKER_RUN_ARGS}"
}

function cmd_env() {
    echo "SIMULATOR_HOST=${SIMULATOR_HOST}"
    echo "SIMULATOR_PORT=${SIMULATOR_PORT}"
    echo "BRIDGE_HOST=${BRIDGE_HOST}"
    echo "BRIDGE_PORT=${BRIDGE_PORT}"
    echo "SCENARIOS_DIR=${SCENARIOS_DIR}"
    echo "SCENARIO_RUNNER_IMAGE=${SCENARIO_RUNNER_IMAGE}"
}

function cmd_pull_image() {
        echo "I: Pulling ${SCENARIO_RUNNER_IMAGE}"
        docker pull ${SCENARIO_RUNNER_IMAGE}
}

function cmd_help() {
    CMD=$(basename $0)

cat<<EOF
Usage: ${CMD} help|version|env|bash|run|SHELL_COMMAND [ARGS...]

    help          - Show this message
    version       - Version info
    env           - print usefull environment variables
    bash          - Run container with interactive shell
    run           - Run scenario. This subcommand has own help. See '${CMD} run --help for details'
    SHELL_COMMAND - run shell command inside the container.

Important note: command is launched in a singleshot container so scenarios shall not save any data outside /scenarios folder

ENVIRONMENT VARIABLES:

    * SIMULATOR_HOST - LGSVL Simulator hostname (default:localhost )
    * SIMULATOR_PORT - LGSVL Simulator port (default: 8181)
    * BRIDGE_HOST - ROS/Apollo bridge hostname (default:localhost)
    * BRIDGE_PORT - ROS/Apollo bridge port (default:9090)
    * SCENARIOS_DIR - host folder to be mounted as /scenarios inside the container

    '${CMD} env' to list current values
EOF
}

function cmd_version {
    function get_image_label {
        LABEL=$1
        docker inspect --format "{{index .Config.Labels \"com.lgsvlsimulator.scenarios_runner.${LABEL}\"}}" ${SCENARIO_RUNNER_IMAGE}
    }

    echo "Docker image: ${SCENARIO_RUNNER_IMAGE}"
    echo "Build ID:     $(get_image_label 'build_ref')"
}


function test_case_runtime()  {
    echo "Starting TestCase runtime"
    printenv | sort | grep -E '^(SIMULATOR|BRIDGE)' || true
    unset DOCKER_RUN_TTY

    SIMULATOR_TC_FILENAME=$(echo ${SIMULATOR_TC_FILENAME} | sed -E 's#^(Python|Scenic)/##')

    run_container run ${SIMULATOR_TC_FILENAME}
}


if [ -n "${SIMULATOR_TC_RUNTIME:-}" ]; then
    test_case_runtime
else
    case "${1:-}" in
        "pull")
            cmd_pull_image
            ;;
        "env")
            cmd_env
            ;;
        "help"|"--help")
            cmd_help
            ;;
        "version")
            cmd_version
            ;;
        "run")
            shift
            run_container run "$@"
            ;;
        *)
            run_container "$@"
            ;;
    esac
fi
