COMPOSE_PROJECT_NAME=scenic_runner
export COMPOSE_PROJECT_NAME

COMPOSE=docker-compose -f docker/docker-compose-dev.yml


SCENIC_LGSVL_IMAGE=scenic_runner_devenv:latest
export SCENIC_LGSVL_IMAGE

build:
	export BUILD_REF=dev-`git describe --always --tag` && \
	${COMPOSE} build

shell:
	./scripts/scenic_lgsvl.sh

devenv:
	${COMPOSE} run --rm devenv /bin/bash

cleanup:
	${COMPOSE} rm
