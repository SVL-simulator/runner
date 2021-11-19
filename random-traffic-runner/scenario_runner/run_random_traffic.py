#!/usr/bin/env python3
#
# Copyright (c) 2021 LG Electronics, Inc.
#
# This software contains code licensed as described in LICENSE.
#

from datetime import datetime
import random
from environs import Env
import socket
import logging
import sys
from time import sleep

import lgsvl

'''
LGSVL__AUTOPILOT_<N>_HOST             IP address of the computer running the N-th bridge to connect to
LGSVL__AUTOPILOT_<N>_PORT             Port that the N-th bridge listens on for messages
LGSVL__AUTOPILOT_<N>_VEHICLE_CONFIG   [NOT USED] N-th vehicle configuration to be loaded in Dreamview (Capitalization and spacing must match the dropdown in Dreamview)
LGSVL__AUTOPILOT_HD_MAP               [NOT USED] HD map to be loaded in Dreamview (Capitalization and spacing must match the dropdown in Dreamview)
LGSVL__AUTOPILOT_<N>_VEHICLE_MODULES  [NOT USED] List of modules to be enabled in Dreamview for an N-th vehicle (Capitalization and space must match the sliders in Dreamview)
LGSVL__DATE_TIME                      [NOT USED] Date and time to start simulation at, format 'YYYY-mm-ddTHH:MM:SS'
LGSVL__ENVIRONMENT_CLOUDINESS         Value of clouds weather effect, clamped to [0, 1]
LGSVL__ENVIRONMENT_DAMAGE             Value of road damage effect, clamped to [0, 1]
LGSVL__ENVIRONMENT_FOG                Value of fog weather effect, clamped to [0, 1]
LGSVL__ENVIRONMENT_RAIN               Value of rain weather effect, clamped to [0, 1]
LGSVL__ENVIRONMENT_WETNESS            Value of wetness weather effect, clamped to [0, 1]
LGSVL__MAP                            Name of map to be loaded in Simulator
LGSVL__RANDOM_SEED                    Seed used to determine random factors (e.g. NPC type, color, behaviour)
LGSVL__SIMULATION_DURATION_SECS       How long to run the simulation for
LGSVL__SIMULATOR_HOST                 IP address of computer running simulator (Master node if a cluster)
LGSVL__SIMULATOR_PORT                 Port that the simulator allows websocket connections over
LGSVL__SPAWN_BICYCLES                 Wether or not to spawn bicycles
LGSVL__SPAWN_PEDESTRIANS              Whether or not to spawn pedestrians
LGSVL__SPAWN_TRAFFIC                  Whether or not to spawn NPC vehicles
LGSVL__TIME_OF_DAY                    [current:] WISE sets the simulation date and time into this envar in "mm/dd/YYYY HH:MM:SS" format
                                      [expected:] If LGSVL__DATE_TIME is not set, today's date is used and this sets the time of day to start simulation at, clamped to [0, 24]
LGSVL__TIME_STATIC                    Whether or not time should remain static (True = time is static, False = time moves forward)
LGSVL__VEHICLE_<N>                    Name of N-th EGO vehicle to be loaded in Simulator
'''

LOG_FORMAT = "[%(levelname)6s] [%(name)s] %(message)s"
INFINITE_SCENARIO_DURATION_SEC = 0
DEFAULT_SCENARIO_DURATION_SEC = INFINITE_SCENARIO_DURATION_SEC
DATE_TIME_FORMAT = "%m/%d/%Y %H:%M:%S"

DEFAULT_APOLLO_MODULES = [
    'Localization',
    'Perception',
    'Transform',
    'Routing',
    'Prediction',
    'Planning',
    'Traffic Light',
    'Control',
    'Recorder'
]


def clamp(val, min_v, max_v):
    return min(max(val, min_v), max_v)


def isSocketAlive(host, port):
    short_timeout_seconds = 2
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(short_timeout_seconds)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0


def empty_envar_error_msg(envar_name):
    return f"The '{envar_name}' environment variable is " \
        "either not set or empty, can not proceed."


def run_random_traffic(desired_duration_sec=INFINITE_SCENARIO_DURATION_SEC):
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
    log = logging.getLogger("RandomTraffic")
    log.info("RadomTraffic scenario runner started.")

    env = Env()

    sim_host_envar = "LGSVL__SIMULATOR_HOST"
    sim_port_envar = "LGSVL__SIMULATOR_PORT"
    try:
        sim_host = env.str("LGSVL__SIMULATOR_HOST")
        sim_port = env.int("LGSVL__SIMULATOR_PORT")
    except:
        log.error(f"Either {sim_host_envar} or {sim_port_envar} "
                  "environment variable is empty or not set, impossible to"
                  "connect to an LG SVL instance")
        sys.exit(1)

    log.info(f"Connecting to the LG SVL at {sim_host}:{sim_port} ...")
    if not isSocketAlive(sim_host, sim_port):
        log.info(f"No LG SVL instance listening to {sim_host}:{sim_port} has"
                 " been found, unable to run the scenario.")
        sys.exit(1)

    sim = lgsvl.Simulator(sim_host, sim_port)

    def safely_terminate(exception=None, msg=None):
        if sim:
            sim.stop()
        if msg:
            log.error(msg)
        if exception:
            log.error(f"Original exception: {str(exception)}")
        sys.exit(1)

    def safe_get_envar(getter, envar_name):
        try:
            result = getter(envar_name)
        except Exception as e:
            safely_terminate(e, empty_envar_error_msg(envar_name))
        return result

    scene_name = safe_get_envar(env.str, "LGSVL__MAP")

    rain = clamp(safe_get_envar(env.float, "LGSVL__ENVIRONMENT_RAIN"), 0, 1)
    fog = clamp(safe_get_envar(env.float, "LGSVL__ENVIRONMENT_FOG"), 0, 1)
    wetness = clamp(safe_get_envar(env.float, "LGSVL__ENVIRONMENT_WETNESS"), 0, 1)
    cloudiness = clamp(safe_get_envar(env.float, "LGSVL__ENVIRONMENT_CLOUDINESS"), 0, 1)
    damage = clamp(safe_get_envar(env.float, "LGSVL__ENVIRONMENT_DAMAGE"), 0, 1)

    log.info(f"Rain {rain}, fog {fog}, wetness {wetness}, cloudiness "
             f"{cloudiness}, damage {damage}")

    if sim.current_scene == scene_name:
        log.info(f"The '{scene_name}' was already loaded, resetting it.")
        sim.reset()
    else:
        seed_envar = "LGSVL__RANDOM_SEED"
        seed = safe_get_envar(env.int, seed_envar)
        if seed == 0:
            log.info(f"Loading scene '{scene_name}' with random seed")
            sim.load(scene_name)
        else:
            log.info(f"Loading scene '{scene_name}' with a predefined seed {seed}")
            sim.load(scene_name, seed)

    sim.weather = lgsvl.WeatherState(rain, fog, wetness, cloudiness, damage)

    # TODO: make this envar mandatory once the WISE starts sending it
    is_static_time = env.bool("LGSVL__TIME_STATIC", True)

    # TODO: use the LGSVL__DATE_TIME envar once WISE starts setting it correctly
    date_time_string = safe_get_envar(env.str, "LGSVL__TIME_OF_DAY")
    sim.set_date_time(datetime.strptime(date_time_string,
                                        DATE_TIME_FORMAT),
                      is_static_time)

    log.info(f"Simulation date/time : {sim.current_datetime},"
             f" time is static: {is_static_time}")

    spawns = sim.get_spawn()
    total_spawns = len(spawns)
    occupied_spawn_indices = set()

    ego_index = -1
    while True:
        ego_index += 1
        # Iterate through all possible Ego indices until an empty/unset
        # vehicle envar encountered. This way it is possible to set any number
        # of Ego vehicles from the WISE without an additional envar holding
        # the quantity of the vehicles.
        vehicle_config_envar = f"LGSVL__VEHICLE_{ego_index}"
        try:
            vehicle_config = env.str(vehicle_config_envar)
        except:
            if ego_index == 0:
                safely_terminate(None, empty_envar_error_msg(vehicle_config_envar))
            # If there is no envar with N-th vehicle it just means we have N-1
            # Ego vehicles in this simulation and this case is fine if at least
            # Ego0 is present.
            break

        log.info(f"Spawning ego vehicle {ego_index} : {vehicle_config}")

        if ego_index >= total_spawns:
            safely_terminate(None, f"Can not spawn ego vehicle {ego_index} : "
                             f"only {total_spawns} spawn points available on"
                             " the given map.")

        # TODO some sort of Env Variable so that user/wise
        # can select the spawning point from a list
        spawn_index = random.randrange(total_spawns)
        while spawn_index in occupied_spawn_indices:
            spawn_index = random.randrange(total_spawns)
        occupied_spawn_indices.add(spawn_index)

        state = lgsvl.AgentState()
        state.transform = spawns[spawn_index]

        ego = sim.add_agent(vehicle_config, lgsvl.AgentType.EGO, state)

        bridge_host_envar = f"LGSVL__AUTOPILOT_{ego_index}_HOST"
        bridge_port_envar = f"LGSVL__AUTOPILOT_{ego_index}_PORT"

        try:
            bridge_host = env.str(bridge_host_envar)
            bridge_port = env.int(bridge_port_envar)
        except:
            log.info(f"No {bridge_host_envar} and/or {bridge_port_envar} envar"
                     " set, this ego vehicle will not have a bridge connection.")
            continue

        bridge_connection_error_msg = f"Ego {ego_index} has failed to connect " \
            f"to an autopilot bridge at {bridge_host}:{bridge_port}. Can not proceed."

        if not isSocketAlive(bridge_host, bridge_port):
            safely_terminate(None, f"No active listener on {bridge_host}:{bridge_port}")

        log.info(f"Connecting ego vehicle {ego_index} to an autopilot bridge at "
                 f"{bridge_host}:{bridge_port} ...")
        try:
            ego.connect_bridge(bridge_host, bridge_port)
            # A short delay to ensure the bridge connection has been established
            sleep(2)
            if not ego.bridge_connected:
                safely_terminate(None, bridge_connection_error_msg)
        except Exception as e:
            safely_terminate(e, bridge_connection_error_msg)

    if safe_get_envar(env.bool, "LGSVL__SPAWN_TRAFFIC"):
        log.info("Adding random NPCs")
        sim.add_random_agents(lgsvl.AgentType.NPC)

    if safe_get_envar(env.bool, "LGSVL__SPAWN_PEDESTRIANS"):
        log.info("Adding random pedestrians")
        sim.add_random_agents(lgsvl.AgentType.PEDESTRIAN)

    # TODO: handle this envar once the bicycle support is available in Simulator
    spawn_cyclists = safe_get_envar(env.bool, "LGSVL__SPAWN_BICYCLES")

    # TODO: make this envar mandatory once the WISE starts sending it
    env_duration_sec = env.float("LGSVL__SIMULATION_DURATION_SECS",
                                 DEFAULT_SCENARIO_DURATION_SEC)

    duration = max(desired_duration_sec, env_duration_sec)

    log.info("Starting simulation scenario.")

    sim.run(duration)

    log.info("RandomTraffic scenario simulation completed.")

    sim.reset()

    return 0


if __name__ == "__main__":
    run_random_traffic()
