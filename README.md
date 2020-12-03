# Scenic scenarios runner for LGSVL Simulator


## Quick start

Download runner [script](scripts/scenic_lgsvl.sh) by this [link](scripts/scenic_lgsvl.sh?inline=false) and save it as `~/.local/bin/scenic_lgsvl.sh`

Alternatively, you can extract to from docker image:

```
mkdir -p ~/.local/bin
docker run --rm auto-gitlab.lgsvl.net:4567/hdrp/scenarios/runner:latest get_scenic_lgsvl > ~/.local/bin/scenic_lgsvl.sh
```

Make sure script is executable

```
chmod +x ~/.local/bin/scenic_lgsvl.sh
```
Check if scenic_lgsvl.sh is working with command `scenic_lgsvl.sh help`. You should get the usage information like this:

```
Usage: scenic_lgsvl.sh help|pull|env|bash|COMMAND [ARGS...]

    help - Show this message
    pull - pull docker image
    env  - print usefull environment variables
    bash - Run container with interactive shell
    COMMAND - run command inside the container.
```

Clone scenarios repo

```
git clone git@auto-gitlab.lgsvl.net:HDRP/Scenarios/scenarios.git
```

To run a specific scenario go to scenario folder:

```
cd scenarios/scenario_2_1
```

then run python script with scenic_lgsvl.sh

```
scenic_lgsvl.sh python scenario_2_1_simulator_Apollo.py
```

## Get development environment from source

* To get a fresh clone:

```
    $ git clone --recursive git@auto-gitlab.lgsvl.net:HDRP/Scenarios/runner.git
    $ cd runner
    $ make build
    $ make devenv
```

* To upadate existing workcopy:

```
    $ cd runner
    $ git submodule init &&	git submodule update
    $ make build
    $ make devenv
```

## Link development environment as simulator scenario runtime

Using `install-testcase-runtime.sh` script:

```shell
$ ./scripts/install-testcase-runtime.sh /path/to/simulator
```

By invoking make target:

```shell
$ make install-runtime-dev SIMULATOR_DIR=/path/to/simulator
```

## Known issues/limitations

* You have to go inside the specific scenario folder.
