# Scenario runners for SVL Simulator

The scenario runners provide environments for running RandomTraffic, PythonApi or Visual Scenario Editor (VSE) scripts with the SVL Simulator.

## Requirements
- Linux operating system
- Docker
- SVL Simulator

## Building and running in developer mode

Here and below the VSE runner is used as an example.
To run in developer mode follow these steps:
1. Clone the repository
2. Run
    ```
    $ make -f Makefile.vse build
    ```
    (or `... -f Makefile.python-api ...`, `... -f Makefile.random-traffic ...` respectively)
    to build the development docker image of the desired runner
3. Run
    ```
    $ make -f Makefile.vse devenv
    ```
    to start the corresponding docker image
4. Start the SVL simulator, create and start an **API Only** simulation.
5. Run a scenario using the `run` command:
    ```
    $ run PATH_TO_SCENARIO_JSON_FILE
    ```
    *Notes:*
    - the PythonAPI runner expects a path to a python API script as an argument
    - the RandomTraffic runner does not take any arguments

## Building with arbritary Python versions

To build a `local/vse_runner_base` image with a different version of Python from the default, run:

```
    $ make -f Makefile.vse PYTHON_VERSION_TAG=<VERSION> build-base
```
(the same for the `random-traffic` and `python-api` runners)

The image will be tagged with `vse-<VERSION>` insted of `latest`.

The `local/vse_runner_devenv` image would not be affected by this setting.

## Upgrading dependencies

The versions of the dependencies are pinned by the `requirements[-<PYTHON_VERSION_TAG>].txt` files. Whenever dependencies are
changed, update them by running:

```
    $ make -f Makefile.vse [PYTHON_VERSION_TAG=<VERSION>] upgrade-base-dependencies
```

for each of the values of `PYTHON_VERSION_TAG` being used.

## Other build targets

Run
```
$ make -f Makefile.vse shell
```
to access the command shell inside the container

Run
```
$ make -f Makefile.vse env
```
to see the default environment variables of the container
(the same for the `random-traffic` and `python-api` runners).

# Tagging releases

The final change for a new release must be to set the argument of the
`get_version('<VERSION>')` call in `vse-runner/setup.py` to the new version.
Then commit this change and tag it with the new version:

    git tag -a -m <VERSION> <VERSION>
