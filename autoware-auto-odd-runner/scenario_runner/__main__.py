#!/usr/bin/env python3
"""Scenario supervisor controller"""

import argparse
import os
import sys
import subprocess
import logging
import threading
from time import sleep

from .tier4_lgsvl_bridge import Tier4LgSvlBridgeServerThread


FORMAT = "[%(levelname)6s] [%(name)s] %(message)s"

SIMULATION_STARTUP_TIMEOUT_SEC = 120

logging.basicConfig(level=logging.DEBUG, format=FORMAT)
log = logging.getLogger("scenario_runner")


def setup_log_levels(log_level):
    log.setLevel(log_level)

    # Reset levels for some chatty modules
    logging.getLogger('matplotlib').setLevel(logging.INFO)
    logging.getLogger('websockets').setLevel(logging.INFO)
    logging.getLogger('selector_events').setLevel(logging.INFO)
    logging.getLogger('asyncio').setLevel(logging.INFO)


def parse_args():
    description = 'Run the TierIV ODD scenarios in SVL Simulator'
    scenario_file_description = 'TierIV (*.yaml) or OpenDrive (*.xosc) scenario file URL'
    lanelet_file_description = 'Lanelet2 (*.osm) HD map file URL'

    parser = argparse.ArgumentParser(os.path.basename(sys.argv[0]),
                                     description=description)

    parser.add_argument('scenario_file_url', metavar='SCENARIO_FILE_URL', type=str,
                        help=scenario_file_description)

    parser.add_argument('hd_map_file_url', metavar='HD_MAP_FILE_URL', type=str,
                        help=lanelet_file_description)

    parser.add_argument('--log-level', '-L', metavar='LEVEL', type=str,
                        default='INFO', help="Logging level")

    return parser.parse_args()


def localize_yaml_scenario(scenario_filename,
                           abs_map_filepath,
                           localized_scenario_filename):
    '''
    Replaces the 'isEgo' parameter "true" value with the "false"
    Replaces the map path with the local absolute one
    '''
    fin = open(scenario_filename, "rt")
    fout = open(localized_scenario_filename, "wt")
    for line in fin:
        if not ".osm" in line:
            # We rely on there is only 1 'true' value in a scenario and
            # it is the 'isEgo' parameter. TBD.
            fout.write(line.replace("value: 'true'", "value: 'false'"))
        else:
            # We presume there is only 1 line containing the .osm map path
            # in a scenario and it looks like:
            # '      filepath: lanelet2_map.osm'
            # so we just replace it with the known absolute path to the
            # downloaded map
            fout.write(f"      filepath: {abs_map_filepath}\n")
    fin.close()
    fout.close()


def main():
    args = parse_args()

    setup_log_levels(args.log_level.upper())

    scenario_filename = os.path.basename(args.scenario_file_url)
    hd_map_filename = os.path.basename(args.hd_map_file_url)

    if scenario_filename[-5:] not in [".yaml", ".xosc"]:
        log.error("Impossible to process scenario file of unknown type "
                  f"'{scenario_filename}', expected *.yaml or *.xosc")
        sys.exit(1)

    if hd_map_filename[-4:] != ".osm":
        log.error("Impossible to process HD map file of unknown type "
                  f"'{hd_map_filename}', expected *.osm")
        sys.exit(1)

    for url in [args.scenario_file_url, args.hd_map_file_url]:
        command = ["wget", "-nc",
                   "--tries", "0",
                   "-P", "/tmp",
                   "--read-timeout", "5",
                   url,
                   "--no-check-certificate"]
        download_status = subprocess.call(command)
        print(download_status)
        if download_status != 0:
            log.error(f"Failed to download URL '{url}'")
            sys.exit(1)

    abs_scenario_filename = f"/tmp/{scenario_filename}"
    abs_hd_map_filename = f"/tmp/{hd_map_filename}"
    abs_localized_scenario_filename = f"/tmp/localized_{scenario_filename}"

    localize_yaml_scenario(abs_scenario_filename,
                           abs_hd_map_filename,
                           abs_localized_scenario_filename)

    bridge_started_up = threading.Event()

    bridge_server_thread = Tier4LgSvlBridgeServerThread(bridge_started_up)
    bridge_server_thread.setDaemon(True)
    bridge_server_thread.start()

    for i in range(0, SIMULATION_STARTUP_TIMEOUT_SEC):
        if not bridge_server_thread.isAlive():
            logging.error("Failed to complete the bridge startup, can not proceed.")
            sys.exit(1)
        logging.info("Waiting for the bridge and LG SVL Simulator to initialize, "
                     f"{i+1} of {SIMULATION_STARTUP_TIMEOUT_SEC} seconds ...")
        sleep(1)
        if bridge_started_up.is_set():
            break

    if not bridge_started_up.is_set():
        logging.error("Failed to run ROS scenario")
        return -1

    logging.info(f"Running the ODD scenario '{scenario_filename}'...")
    ros_command = ["ros2", "launch", "scenario_test_runner", "scenario_test_runner.launch.py",
                   f'scenario:={abs_localized_scenario_filename}',
                   "launch_rviz:=false"]
    return subprocess.call(ros_command)


if __name__ == "__main__":
    sys.exit(main())
