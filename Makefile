COMPOSE_PROJECT_NAME=scenic_runner
export COMPOSE_PROJECT_NAME

COMPOSE=docker-compose -f docker/docker-compose-dev.yml


SCENIC_LGSVL_IMAGE=scenic_runner_devenv:latest
export SCENIC_LGSVL_IMAGE

BUILD_REF=dev-`git describe --always --tag`
export BUILD_REF

build-base:
	docker build -f docker/Dockerfile -t local/scenic_runner_base .

build-devenv: build-base
	docker build -f docker/Dockerfile.devenv --build-arg BASE_IMAGE=local/scenic_runner_base -t local/scenic_runner_devenv .

build:
	${COMPOSE} build

shell:
	./scripts/scenic_lgsvl.sh

env:
	./scripts/scenic_lgsvl.sh env

run-help:
	./scripts/scenic_lgsvl.sh run --help

devenv:
	${COMPOSE} run --rm devenv /bin/bash

cleanup:
	${COMPOSE} rm

flake8:
	${COMPOSE} run --rm devenv flake8 runner

test:
	${COMPOSE} run --rm devenv pytest -s -v runner/tests

submodules-pull-master:
	git submodule init
	git submodule update
	git submodule foreach git checkout master
	git submodule foreach git pull
	git status
