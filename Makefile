
COMPOSE_PROJECT_NAME=scenario_runner
export COMPOSE_PROJECT_NAME

COMPOSE:=docker-compose -f docker/docker-compose-dev.yml


SCENARIO_RUNNER_IMAGE:=scenario_runner_devenv:latest
export SCENARIO_RUNNER_IMAGE

BUILD_REF:="devenv-$(shell git describe --always --tag)"
export BUILD_REF

# To disable "docker build" from using cached base images and layers, invoke "make" with NO_BUILD_CACHE=1.
ifdef NO_BUILD_CACHE
DOCKER_BUILD_OPTS:=--pull --no-cache
endif

build-base:
	docker build $(DOCKER_BUILD_OPTS) -f docker/Dockerfile -t local/scenario_runner_base .

build-devenv: build-base
	docker build $(DOCKER_BUILD_OPTS) -f docker/Dockerfile.devenv --build-arg BASE_IMAGE=local/scenario_runner_base -t local/scenario_runner_devenv .

build: compose-build list-devenv-images

compose-build:
	${COMPOSE} build
	docker tag scenario-runner:latest auto-gitlab.lgsvl.net:4567/hdrp/scenarios/runner:dev

list-devenv-images:
	@docker images | grep -E "^REPOSITORY|^${COMPOSE_PROJECT_NAME}|hdrp/scenarios/runner|^scenario-runner"


docker-latest-rel:
	docker tag scenario-runner:latest lgsvl/simulator-scenarios-runner:latest
	docker images | grep -E 'scenario_runner' | sort

shell:
	./scripts/scenario_runner.sh

env:
	./scripts/scenario_runner.sh env

run-help:
	./scripts/scenario_runner.sh run --help

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

inspect-labels:
	docker inspect --format {{.Config.Labels}} ${SCENARIO_RUNNER_IMAGE}


version:
	./scripts/scenario_runner.sh version

bundles-fast:
	export FAST_RELEASE=1 && ./ci/make_bundle.sh latest auto-gitlab.lgsvl.net:4567/hdrp/scenarios/runner
	cd dist/lgsvlsimulator-scenarios-latest && ../../tests/check-bundle-content.sh

bundles:
	docker tag scenario-runner:latest auto-gitlab.lgsvl.net:4567/hdrp/scenarios/runner:latest
	# docker pull auto-gitlab.lgsvl.net:4567/hdrp/scenarios/runner:latest
	./ci/make_bundle.sh latest auto-gitlab.lgsvl.net:4567/hdrp/scenarios/runner

SIMULATOR_DIR?=/home/user/path/to/simulator

.check_simulator_dir:
	@test -d ${SIMULATOR_DIR} || (echo "E: Can't locate simulator dir at ${SIMULATOR_DIR}. Make sure SIMULATOR_DIR env var points to correct path"; exit 1)

install-runtime-dist: .check_simulator_dir
	./dist/lgsvlsimulator-scenarios-latest/install-testcase-runtime.sh ${SIMULATOR_DIR}
	tree ${SIMULATOR_DIR}/TestCaseRunner

install-runtime-dev: .check_simulator_dir
	./scripts/install-testcase-runtime.sh ${SIMULATOR_DIR}
	tree ${SIMULATOR_DIR}/TestCaseRunner

install-runtime-dist-copy: .check_simulator_dir
	./dist/lgsvlsimulator-scenarios-latest/install-testcase-runtime.sh ${SIMULATOR_DIR} copy
	tree ${SIMULATOR_DIR}/TestCaseRunner

push-ci-trybyild:
	git push origin -f  HEAD:ci-master && git push origin -f && git tag -f CI-TAG && git push origin -f CI-TAG
	@echo "\r\nURL https://auto-gitlab.lgsvl.net/HDRP/Scenarios/runner/pipelines"
