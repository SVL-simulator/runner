# Scenario runner for SVL Simulator

The scenario runner provides an environment for running PythonApi and Visual Scenario Editor (VSE) scripts with the SVL Simulator.

## Requirements
- Linux operating system
- Docker
- SVL Simulator

## Installation with SVL Simulator binary

The release bundle for the scenario runner can be installed in the SVL Simulator binary directory.
To install follow these steps:

1. Download and extract the SVL Simulator release binary (2021.1 release or later)
2. Download and extract the scenario runner bundle
3. Open a terminal and navigate to the `scripts` directory in the extracted directory for the scenario runner:
    ```
    cd PATH_TO_SCENARIO_RUNNER/
    ```
4. Run the install script:
    ```
    ./install_scenario_runner.sh PATH_TO_SVL_SIMULATOR_BINARY copy
    ```

Once the installation is complete the scenario runner will be used when the Python API or VSE templates are selected during simulation creation.


## Building and running in developer mode
To run in developer mode follow these steps:
1. Clone the repository
2. Run `make build` to build the development docker image
3. Run `make devenv` to start the docker image
4. Start the SVL simulator, create and start an **API Only** simulation.
5. Run a scenario using the `run` command:
    ```
    run PATH_TO_SCENARIO
    ```


## Building bundle locally

1. Build a dev image as described in the previous section
2. From the repository root run:
    ```
    ./ci/make_bundle.sh dev
    ```
3. The bundle will be located in the `dist` directory of the repository and can be installed following the steps described in **Installation with SVL simulator binary**.
