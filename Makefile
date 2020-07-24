COMPOSE_PROJECT_NAME=scenic_runner
export COMPOSE_PROJECT_NAME

COMPOSE:=docker-compose -f docker/docker-compose-dev.yml


SCENARIO_RUNNER_IMAGE:=scenic_runner_devenv:latest
export SCENARIO_RUNNER_IMAGE

BUILD_REF:="devenv-$(shell git describe --always --tag)"
export BUILD_REF

build-base:
	docker build -f docker/Dockerfile -t local/scenic_runner_base .

build-python-api:
	docker build -f docker/Dockerfile.python-api -t local/python_api_runner_base .

build-devenv: build-base
	docker build -f docker/Dockerfile.devenv --build-arg BASE_IMAGE=local/scenic_runner_base -t local/scenic_runner_devenv .

build: compose-build list-devenv-images

compose-build:
	${COMPOSE} build

list-devenv-images:
	@docker images | grep -E "^REPOSITORY|^${COMPOSE_PROJECT_NAME}"

shell:
	./scripts/scenic_lgsvl.sh

env:
	./scripts/scenic_lgsvl.sh env

run-help:
	./scripts/scenic_lgsvl.sh run --help

devenv: devenv-scenic

devenv-scenic:
	${COMPOSE} run --rm devenv-scenic /bin/bash

devenv-python-api:
	${COMPOSE} run --rm devenv-python-api /bin/bash

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

inspect-labels:
	docker inspect --format {{.Config.Labels}} ${SCENARIO_RUNNER_IMAGE}


version:
	./scripts/scenic_lgsvl.sh version

bundles-fast:
	export FAST_RELEASE=1 \
		&& ./ci/make_bundle.sh latest-scenic auto-gitlab.lgsvl.net:4567/hdrp/scenarios/runner scenic \
		&& ./ci/make_bundle.sh latest-python-api auto-gitlab.lgsvl.net:4567/hdrp/scenarios/runner python-api

bundles:
	docker pull auto-gitlab.lgsvl.net:4567/hdrp/scenarios/runner:latest-scenic
	docker pull auto-gitlab.lgsvl.net:4567/hdrp/scenarios/runner:latest-python-api
	./ci/make_bundle.sh latest-scenic auto-gitlab.lgsvl.net:4567/hdrp/scenarios/runner scenic
	./ci/make_bundle.sh latest-scenic auto-gitlab.lgsvl.net:4567/hdrp/scenarios/runner python-api

push-ci-trybyild:
	git push origin -f  HEAD:ci-master && git push origin -f && git tag -f CI-TAG && git push origin -f CI-TAG
	@echo "\r\nURL https://auto-gitlab.lgsvl.net/HDRP/Scenarios/runner/pipelines"
