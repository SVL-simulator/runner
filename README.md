# Scenic scenarios runner for LGSL Simulator


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

## Known issues/limitations

* You have to go inside the specific scenario folder.
