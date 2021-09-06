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

import lgsvl

'''
LGSVL__AUTOPILOT_0_HOST             IP address of the computer running the bridge to connect to
LGSVL__AUTOPILOT_0_PORT             Port that the bridge listens on for messages
LGSVL__AUTOPILOT_0_VEHICLE_CONFIG   Vehicle configuration to be loaded in Dreamview (Capitalization and spacing must match the dropdown in Dreamview)
LGSVL__AUTOPILOT_HD_MAP             HD map to be loaded in Dreamview (Capitalization and spacing must match the dropdown in Dreamview)
LGSVL__AUTOPILOT_0_VEHICLE_MODULES  List of modules to be enabled in Dreamview (Capitalization and space must match the sliders in Dreamview)
LGSVL__DATE_TIME                    Date and time to start simulation at, format 'YYYY-mm-ddTHH:MM:SS'
LGSVL__ENVIRONMENT_CLOUDINESS       Value of clouds weather effect, clamped to [0, 1]
LGSVL__ENVIRONMENT_DAMAGE           Value of road damage effect, clamped to [0, 1]
LGSVL__ENVIRONMENT_FOG              Value of fog weather effect, clamped to [0, 1]
LGSVL__ENVIRONMENT_RAIN             Value of rain weather effect, clamped to [0, 1]
LGSVL__ENVIRONMENT_WETNESS          Value of wetness weather effect, clamped to [0, 1]
LGSVL__MAP                          Name of map to be loaded in Simulator
LGSVL__RANDOM_SEED                  Seed used to determine random factors (e.g. NPC type, color, behaviour)
LGSVL__SIMULATION_DURATION_SECS     How long to run the simulation for
LGSVL__SIMULATOR_HOST               IP address of computer running simulator (Master node if a cluster)
LGSVL__SIMULATOR_PORT               Port that the simulator allows websocket connections over
LGSVL__SPAWN_BICYCLES               Wether or not to spawn bicycles
LGSVL__SPAWN_PEDESTRIANS            Whether or not to spawn pedestrians
LGSVL__SPAWN_TRAFFIC                Whether or not to spawn NPC vehicles
LGSVL__TIME_OF_DAY                  If LGSVL__DATE_TIME is not set, today's date is used and this sets the time of day to start simulation at, clamped to [0, 24]
LGSVL__TIME_STATIC                  Whether or not time should remain static (True = time is static, False = time moves forward)
LGSVL__VEHICLE_0                    Name of EGO vehicle to be loaded in Simulator
'''

LOG_FORMAT = "[%(levelname)6s] [%(name)s] %(message)s"
INFINITE_SCENARIO_DURATION_SEC = 0
DEFAULT_SCENARIO_DURATION_SEC = INFINITE_SCENARIO_DURATION_SEC
DEFAULT_VEHICLE_CONFIG = "47b529db-0593-4908-b3e7-4b24a32a0f70"
DEFAULT_MAP = "BorregasAve"
DATE_TIME_FORMAT = "%m/%d/%Y %H:%M:%S"
DEFAULT_DATE_TIME = "01/01/1970 00:00:00"
DEFAULT_TIME_OF_DAY = 12.0

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

def run_random_traffic(desired_duration_sec=INFINITE_SCENARIO_DURATION_SEC):
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
    log = logging.getLogger("RandomTraffic")
    log.info("RadomTraffic scenario runner started.")

    env = Env()

    sim_host = env.str("LGSVL__SIMULATOR_HOST", "127.0.0.1")
    sim_port = env.int("LGSVL__SIMULATOR_PORT", 8181)

    log.info(f"Connecting to the LG SVL at {sim_host}:{sim_port} ...")
    if not isSocketAlive(sim_host, sim_port):
        log.info(f"No LGSVL instance listening to {sim_host}:{sim_port} has"
                  " been found, unable to run the scenario.")
        quit()

    sim = lgsvl.Simulator(sim_host, sim_port)
    scene_name = env.str("LGSVL__MAP", DEFAULT_MAP)

    rain = clamp(env.float("LGSVL__ENVIRONMENT_RAIN", 0), 0, 1)
    fog = clamp(env.float("LGSVL__ENVIRONMENT_FOG", 0), 0, 1)
    wetness = clamp(env.float("LGSVL__ENVIRONMENT_WETNESS", 0), 0, 1)
    cloudiness = clamp(env.float("LGSVL__ENVIRONMENT_CLOUDINESS", 0), 0, 1)
    damage = clamp(env.float("LGSVL__ENVIRONMENT_DAMAGE", 0), 0, 1)

    log.info(f"Rain {rain}, fog {fog}, wetness {wetness}, cloudiness "
             f"{cloudiness}, damage {damage}")

    if sim.current_scene == scene_name:
        log.info(f"The '{scene_name}' was already loaded, resetting it.")
        sim.reset()
    else:
        try:
            seed = env.int("LGSVL__RANDOM_SEED", 0)
            log.info(f"Loading scene '{scene_name}' with random seed {seed}")
            sim.load(scene_name, seed)
        except Exception:
            sim.load(scene_name)

    sim.weather = lgsvl.WeatherState(rain, fog, wetness, cloudiness, damage)

    is_static_time = env.bool("LGSVL__TIME_STATIC", True)
    date_time_string = env.str("LGSVL__DATE_TIME", DEFAULT_DATE_TIME)

    if date_time_string != DEFAULT_DATE_TIME:
        sim.set_date_time(datetime.strptime(date_time_string, DATE_TIME_FORMAT),
                          is_static_time)
    else:
        try:
            time_of_day = env.float("LGSVL__TIME_OF_DAY", DEFAULT_TIME_OF_DAY)
            time_of_day = clamp(time_of_day, 0, 24)
            log.info(f"Time of day set as a float value: {time_of_day}, "
                      "so the current date is used as a simulation date")
            sim.set_date_time(datetime.now())
            sim.set_time_of_day(time_of_day, is_static_time)
        except Exception:
            # As the cloud might send a full date+time string in the "timeOfDay"
            # parameter, this case has to handled as well
            date_time_string = env.str("LGSVL__TIME_OF_DAY", DEFAULT_DATE_TIME)
            sim.set_date_time(datetime.strptime(date_time_string,
                                                DATE_TIME_FORMAT),
                              is_static_time)

    log.info(f"Simulation date/time : {sim.current_datetime},"
             f" time is static: {is_static_time}")

    spawns = sim.get_spawn()
    total_spawns = len(spawns)
    occupied_spawn_indices = set()

    # Default vehicle for this test case is Lincoln2017MKZ_LGSVL - Apollo 6.0
    # https://wise.svlsimulator.com/vehicles/profile/73805704-1e46-4eb6-b5f9-ec2244d5951e/edit/configuration/47b529db-0593-4908-b3e7-4b24a32a0f70

    ego_index = 0
    while True:
        try:
            vehicle_config = env.str(f"LGSVL__VEHICLE_{ego_index}")
        except:
            if ego_index == 0:
                # There could not be less then 1 Ego car, so a default vehicle
                # is loaded if the envar is not set at all
                vehicle_config = DEFAULT_VEHICLE_CONFIG
            else:
                break

        log.info(f"Spawning ego vehicle {ego_index} : {vehicle_config}")

        if ego_index >= total_spawns:
            log.warning(f"Can not spawn ego vehicle {ego_index} : "
                        f"only {total_spawns} spawn points available on the given map.")
            break;

        # TODO some sort of Env Variable so that user/wise can select from list
        spawn_index = random.randrange(total_spawns)
        while spawn_index in occupied_spawn_indices:
            spawn_index = random.randrange(total_spawns)
        occupied_spawn_indices.add(spawn_index)

        state = lgsvl.AgentState()
        state.transform = spawns[spawn_index]
        ego = sim.add_agent(vehicle_config, lgsvl.AgentType.EGO, state)

        # The EGO is now looking for a bridge at the specified IP and port
        bridge_host = env.str(f"LGSVL__AUTOPILOT_{ego_index}_HOST", "127.0.0.1")
        bridge_port = env.int(f"LGSVL__AUTOPILOT_{ego_index}_PORT", 9090)

        bridge_connected = False
        if isSocketAlive(bridge_host, bridge_port):
            log.info("Connecting to an autopilot bridge at "
                     f"{bridge_host}:{bridge_port} ...")
            try:
                ego.connect_bridge(bridge_host, bridge_port)
                bridge_connected = ego.bridge_connected
            except Exception:
                bridge_connected = False

        if not bridge_connected:
            log.warning("The EGO has failed to connect to an autopilot bridge at "
                  f"{bridge_host}:{bridge_port}. The 'KeyboardControl' sensor "
                  "configuration (if available) still can be used to control the "
                  "EGO vehicle in the simulation.")

        try:
            log.info(f"Connecting to DreamView at {bridge_host}")
            dv = lgsvl.dreamview.Connection(sim, ego, bridge_host)

            autopilot_map = env.str("LGSVL__AUTOPILOT_HD_MAP", "Borregas Ave")
            log.info(f"Setting autopilot map '{autopilot_map}'")
            dv.set_hd_map(autopilot_map)

            autopilot_vehicle = env.str(
                f"LGSVL__AUTOPILOT_{ego_index}_VEHICLE_CONFIG",
                "Lincoln2017MKZ_LGSVL")
            log.info(f"Setting autopilot vehicle '{autopilot_vehicle}'")
            dv.set_vehicle(autopilot_vehicle)

            try:
                modules = env.list(
                    f"LGSVL__AUTOPILOT_{ego_index}_VEHICLE_MODULES",
                    subcast=str)
                if len(modules) == 0:
                    modules = DEFAULT_APOLLO_MODULES
            except Exception:
                modules = DEFAULT_APOLLO_MODULES

            # TODO some sort of Env Variable so that user/wise can select from list:
            destination_index = random.randrange(len(spawns[spawn_index].destinations))
            destination = spawns[spawn_index].destinations[destination_index]

            log.info("Setting up Apollo with modules:")
            for module in modules:
                log.info(f"    {module}")
            log.info(f"Destination : X {destination.position.x},"
                     f" Y {destination.position.y}")
            dv.setup_apollo(destination.position.x, destination.position.z, modules)
        except Exception:
            log.warning("Failed to establish a DreamView connection, is there an "
                        f"Apollo 6.0 instance running at {bridge_host}?")
        ego_index += 1

    if env.bool("LGSVL__SPAWN_TRAFFIC", True):
        log.info("Adding random NPCs")
        sim.add_random_agents(lgsvl.AgentType.NPC)

    if env.bool("LGSVL__SPAWN_PEDESTRIANS", True):
        log.info("Adding random pedestrians")
        sim.add_random_agents(lgsvl.AgentType.PEDESTRIAN)

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
