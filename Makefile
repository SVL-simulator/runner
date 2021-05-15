
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

# PYTHON_VERSION_TAG is the version portion of the tag of the Python base image to be used. It can be MAJOR.MINOR.PATCH or just
# MAJOR.MINOR .
ifdef PYTHON_VERSION_TAG
RUNNER_BASE_TAG:=python-$(PYTHON_VERSION_TAG)
REQUIREMENTS_TXT:=requirements-$(PYTHON_VERSION_TAG).txt
BUILD_ARG__PYTHON_VERSION_MAJOR_MINOR:=$(shell set - $(subst ., ,$(PYTHON_VERSION_TAG)); echo --build-arg PYTHON_VERSION_MAJOR_MINOR=$$1.$$2)
# BUILD_ARG__PYTHON_VERSION_PATCH includes the leading "." unless there isn't a patch version field in PYTHON_VERSION_TAG, in
# which case the value is empty.
BUILD_ARG__PYTHON_VERSION_PATCH:=$(shell set - $(subst ., ,$(PYTHON_VERSION_TAG)); echo --build-arg PYTHON_VERSION_PATCH=$${3:+.$${3}})
BUILD_ARG__REQUIREMENTS_TXT:=--build-arg REQUIREMENTS_TXT=$(REQUIREMENTS_TXT)
else
RUNNER_BASE_TAG:=latest
# Use the defaults specified in docker/Dockerfile for PYTHON_VERSION_MAJOR_MINOR, PYTHON_VERSION_PATCH, and REQUIREMENTS_TXT.
# However, the latter is needed in this file, so extract its default from there.
REQUIREMENTS_TXT:=$(shell awk 'toupper($$1) == "ARG" && $$2 ~ /^REQUIREMENTS_TXT=/ { print gensub(/^REQUIREMENTS_TXT=/, "", 1, $$2); exit }' docker/Dockerfile)
endif

build-base:
	docker build $(DOCKER_BUILD_OPTS) -f docker/Dockerfile \
		-t local/scenario_runner_base:$(RUNNER_BASE_TAG) \
		$(BUILD_ARG__PYTHON_VERSION_MAJOR_MINOR) \
		$(BUILD_ARG__PYTHON_VERSION_PATCH) \
		$(BUILD_ARG__REQUIREMENTS_TXT) \
		.

upgrade-base-dependencies:
	touch $(REQUIREMENTS_TXT)
	docker build --pull --no-cache -f docker/Dockerfile \
		--target builder \
		-t local/scenario_runner_base_requirements \
		$(BUILD_ARG__PYTHON_VERSION_MAJOR_MINOR) \
		$(BUILD_ARG__PYTHON_VERSION_PATCH) \
		$(BUILD_ARG__REQUIREMENTS_TXT) \
		--build-arg GENERATE_REQUIREMENTS_TXT=true \
		.
	# Don't include the packages that we build.
	docker run --rm local/scenario_runner_base_requirements python3 -m pip freeze | grep -v '@ file://' > $(REQUIREMENTS_TXT)
	docker image rm local/scenario_runner_base_requirements

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
