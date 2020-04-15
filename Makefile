COMPOSE_PROJECT_NAME=scenic_runner
export COMPOSE_PROJECT_NAME

COMPOSE=docker-compose -f docker/docker-compose-dev.yml


SCENIC_LGSVL_IMAGE=scenic_runner_devenv:latest
export SCENIC_LGSVL_IMAGE

BUILD_REF=dev-`git describe --always --tag`
export BUILD_REF

build:
	${COMPOSE} build

shell:
	./scripts/scenic_lgsvl.sh

run-help:
	./scripts/scenic_lgsvl.sh run --help

devenv:
	${COMPOSE} run --rm devenv /bin/bash

cleanup:
	${COMPOSE} rm

flake8:
	${COMPOSE} run --rm devenv flake8 runner
